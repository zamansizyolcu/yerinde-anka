"""
Çevrimdışı konuşma tanıma (STT) — internet KAPALIYKEN bile çalışır.

Öncelik sırası:
  1) faster-whisper (Whisper modeli, tamamen yerel, Türkçe'de yüksek doğruluk)
  2) Vosk (daha hafif, daha düşük doğruluk ama daha az kaynak kullanır)

İkisi de kurulu değilse anlaşılır bir hata mesajı döner.

Kayıt stratejisi: enerji tabanlı basit bir VAD (Voice Activity Detection).
Mikrofonda ses seviyesi eşik değerini aşınca kayıt başlar, art arda bir
süre sessizlik olunca kayıt biter — böylece kullanıcı konuşmayı bitirince
otomatik olarak metne çevrilir.
"""

from __future__ import annotations

import io
import json
import queue
import time
import wave

from app_config import get_app_config_value

SAMPLE_RATE = 16000
CHANNELS = 1

_whisper_model = None
_vosk_model = None
_vosk_recognizer = None


class OfflineSTTError(RuntimeError):
    pass


def _get_stt_choice() -> tuple[str, str]:
    """
    Ayarlar panelindeki liste seçiciden gelen "stt_choice" değerini okur:
    "whisper:small" / "whisper:medium" / "whisper:large-v3" / "vosk"
    (name, whisper_model_size) döner. Eski ayarlarla (ollama_stt_engine +
    whisper_model_size) geriye dönük uyumludur.
    """
    choice = str(get_app_config_value("stt_choice", "") or "").strip().lower()
    if choice.startswith("whisper:"):
        return "whisper", choice.split(":", 1)[1] or "small"
    if choice == "vosk":
        return "vosk", "small"

    # Geriye dönük uyumluluk (eski iki-yönlü ayar anahtarları)
    engine = str(get_app_config_value("ollama_stt_engine", "whisper") or "whisper").lower()
    model_size = str(get_app_config_value("whisper_model_size", "small") or "small")
    return ("vosk" if engine == "vosk" else "whisper"), model_size


def _get_engine_preference() -> str:
    """'whisper' ya da 'vosk' (hangisi tercih ediliyor)."""
    engine, _ = _get_stt_choice()
    return engine


def _record_utterance(timeout: float = 15.0, silence_ms: int = 1100,
                       start_threshold: float = 0.02, min_speech_ms: int = 250) -> bytes:
    """
    Basit enerji tabanlı VAD ile mikrofondan bir cümle kaydeder.
    16-bit PCM, mono, 16kHz ham bayt döner (WAV başlığı yok).
    """
    try:
        import sounddevice as sd
        import numpy as np
    except ImportError as e:
        raise OfflineSTTError(
            "sounddevice / numpy yüklü değil. Kurulum: pip install sounddevice numpy"
        ) from e

    q: "queue.Queue[bytes]" = queue.Queue()

    def callback(indata, frames, time_info, status):
        q.put(bytes(indata))

    frames_per_block = 1024
    buffer = bytearray()
    speaking = False
    silence_accum_ms = 0
    speech_accum_ms = 0
    start = time.time()

    with sd.RawInputStream(
        samplerate=SAMPLE_RATE, blocksize=frames_per_block, dtype="int16",
        channels=CHANNELS, callback=callback,
    ):
        while time.time() - start < timeout:
            try:
                chunk = q.get(timeout=0.5)
            except queue.Empty:
                continue

            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            rms = float(np.sqrt(np.mean(samples ** 2))) if len(samples) else 0.0
            block_ms = (len(chunk) / 2) / SAMPLE_RATE * 1000

            if rms > start_threshold:
                speaking = True
                silence_accum_ms = 0
                speech_accum_ms += block_ms
                buffer.extend(chunk)
            elif speaking:
                silence_accum_ms += block_ms
                buffer.extend(chunk)
                if silence_accum_ms >= silence_ms and speech_accum_ms >= min_speech_ms:
                    break

    return bytes(buffer)


def _pcm_to_wav_bytes(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def _transcribe_with_whisper(pcm: bytes) -> str:
    global _whisper_model
    from faster_whisper import WhisperModel

    if _whisper_model is None:
        _, model_size = _get_stt_choice()
        _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")

    import numpy as np
    audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    segments, _info = _whisper_model.transcribe(audio, language="tr", beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text


def preload_stt():
    """
    Seçili STT motorunu (Whisper öncelikli) önceden yükler — açılışta bir kez
    çağrılırsa, kullanıcının İLK sesli komutundaki model yükleme gecikmesi
    (birkaç saniye sürebilir) ortadan kalkar.
    """
    global _whisper_model, _vosk_model
    engine, model_size = _get_stt_choice()
    if engine != "vosk":
        try:
            from faster_whisper import WhisperModel
            if _whisper_model is None:
                _whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
            return
        except ImportError:
            pass
    try:
        import vosk
        if _vosk_model is None:
            model_path = str(get_app_config_value("vosk_model_path", "vosk-model") or "vosk-model")
            _vosk_model = vosk.Model(model_path)
    except Exception:
        pass


def _transcribe_with_vosk(pcm: bytes) -> str:
    global _vosk_model, _vosk_recognizer
    import vosk

    if _vosk_model is None:
        model_path = str(get_app_config_value("vosk_model_path", "vosk-model") or "vosk-model")
        _vosk_model = vosk.Model(model_path)

    recognizer = vosk.KaldiRecognizer(_vosk_model, SAMPLE_RATE)
    recognizer.AcceptWaveform(pcm)
    result = json.loads(recognizer.FinalResult())
    return (result.get("text") or "").strip()


def listen_and_transcribe(timeout: float = 15.0) -> str:
    """
    Mikrofonu dinler, konuşma bitince tercih edilen motorla (Whisper öncelikli,
    yoksa Vosk) metne çevirir. Her ikisi de yoksa OfflineSTTError fırlatır.
    """
    pcm = _record_utterance(timeout=timeout)
    if not pcm:
        return ""

    preference = _get_engine_preference()
    engines = ["whisper", "vosk"] if preference != "vosk" else ["vosk", "whisper"]

    last_error = None
    for engine in engines:
        try:
            if engine == "whisper":
                return _transcribe_with_whisper(pcm)
            else:
                return _transcribe_with_vosk(pcm)
        except ImportError as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    raise OfflineSTTError(
        "Çevrimdışı konuşma tanıma için ne faster-whisper ne de vosk kullanılabildi. "
        "Kurulum: pip install faster-whisper  (önerilen) ya da pip install vosk sounddevice "
        f"— ve bir Türkçe model indir. Son hata: {last_error}"
    )
