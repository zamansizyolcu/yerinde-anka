"""
backend/stt_engine.py — Faster-Whisper ile yüksek hızlı Türkçe STT.

Tetiklemeden sonra çağrılır: enerji-VAD ile kullanıcının cümlesini kaydeder
(sessizlikte otomatik biter), Whisper'la metne çevirir. Model bir kez
yüklenir (preload) ve int8 nicemlemeyle CPU'da hızlı çalışır. transcribe
bloklayıcı olduğundan SystemController bunu asyncio.to_thread ile çağırır.
"""

from __future__ import annotations

import queue
import time

SAMPLE_RATE = 16000


class FasterWhisperSTT:
    def __init__(self, model_size: str = "small", language: str = "tr"):
        self.model_size = model_size
        self.language = language
        self._model = None
        self._vosk = None
        self.engine = "whisper"          # whisper | vosk
        self.last_error: str | None = None
        self.last_capture_sec: float = 0.0  # son dinlemede yakalanan ses süresi
        # Teşhis (sınıf düzeyi — _record_utterance staticmethod):
    _last_peak: float = 0.0
    _last_threshold: float = 0.0

    # ── Model yönetimi ───────────────────────────────────────────────────────
    def preload(self) -> bool:
        """
        Açılışta bir kez çağır. Whisper yüklenemezse (numpy/torch bozuk, paket
        yok...) SESSİZCE PES ETMEZ — Vosk'a düşer. Böylece Linux'ta 'hiç
        duymuyor' durumu oluşmaz; en azından Vosk ile komutları anlar.
        """
        try:
            from faster_whisper import WhisperModel
            if self._model is None:
                self._model = WhisperModel(self.model_size, device="cpu",
                                           compute_type="int8")
            self.engine = "whisper"
            return True
        except Exception as e:
            whisper_err = e
            self.last_error = f"Whisper yüklenemedi: {e}"

        # ── Yedek: Vosk ────────────────────────────────────────────────────
        if self._load_vosk():
            self.engine = "vosk"
            self.last_error = (f"Whisper kullanılamıyor ({whisper_err}) — VOSK ile "
                               "devam ediyorum (biraz daha basit ama çalışıyor).")
            return True
        self.last_error = (f"Ne Whisper ne Vosk yüklenebildi ({whisper_err}). "
                           "Kur: pip install faster-whisper  ya da vosk modelini "
                           "proje klasörüne koy.")
        return False

    def _load_vosk(self) -> bool:
        """Vosk modelini yükler (wake-word ile aynı model klasörü)."""
        if self._vosk is not None:
            return True
        try:
            import vosk
            vosk.SetLogLevel(-1)
            from pathlib import Path as _P
            base = _P(__file__).resolve().parent.parent
            cands = [base / "vosk-model"] + sorted(base.glob("vosk-model*"))
            for c in cands:
                if c.is_dir():
                    if not (c / "final.mdl").exists():
                        subs = [x for x in c.iterdir() if x.is_dir()]
                        if len(subs) == 1:
                            c = subs[0]
                    try:
                        self._vosk = vosk.Model(str(c))
                        return True
                    except Exception:
                        continue
        except Exception:
            pass
        return False

    def _vosk_fallback(self, pcm: bytes) -> str:
        """16 kHz PCM'i Vosk ile çözümler."""
        try:
            import json as _json
            import vosk
            rec = vosk.KaldiRecognizer(self._vosk, SAMPLE_RATE)
            rec.AcceptWaveform(pcm)
            return (_json.loads(rec.FinalResult()).get("text") or "").strip()
        except Exception:
            return ""

    def set_model_size(self, size: str) -> None:
        """GUI 'ANLAMA' seçicisi değişince çağır — model tembel yeniden yüklenir."""
        if size != self.model_size:
            self.model_size = size
            self._model = None

    # ── Kayıt (uyarlanabilir enerji-VAD) ────────────────────────────────────
    @staticmethod
    def _record_utterance(timeout: float = 12.0, silence_ms: int = 1000) -> bytes:
        """
        Kararlılık için sabit eşik yerine UYARLANABİLİR eşik kullanır:
        ilk ~0.4 sn ortam gürültüsü ölçülür, konuşma eşiği ona göre belirlenir.
        Sessiz odada hassas, gürültülü ortamda (fan/klima) yanlış tetiklenmez —
        Pardus'ta gözlenen 'hiç anlamıyor / yarıda kesiyor' sorunlarının ana
        kaynağı buydu.
        """
        import numpy as np
        from .audio_input import MicStream, resample_to_16k

        # MicStream: sounddevice sessiz kalırsa (Linux'ta 'hiç duymuyor'
        # sorununun kök nedeniydi) parec/arecord'a otomatik düşer.
        errors: list[str] = []
        mic = MicStream(samplerate=SAMPLE_RATE, blocksize=1024, log=errors.append)
        if not mic.start():
            detail = errors[-1] if errors else "bilinmeyen sebep"
            raise RuntimeError(f"Mikrofon açılamadı: {detail}")

        def _rms(chunk: bytes) -> float:
            samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
            return float(np.sqrt(np.mean(samples ** 2))) if len(samples) else 0.0

        buf = bytearray()
        speaking = False
        silence_acc = 0.0
        start = time.time()
        rate = mic.rate

        peak_rms = 0.0
        pending: bytes | None = None
        try:
            # 1) Ortam gürültüsünü ölç (~0.25 sn) — KRİTİK DÜZELTME:
            #    Kullanıcı bu pencerede ZATEN KONUŞUYORSA (eski kod bunu
            #    'gürültü' sayıp eşiği konuşmanın 3.5 katına kilitliyordu ve
            #    asistan SAĞIR kalıyordu) kalibrasyonu anında kesip o bloğu
            #    konuşmanın başı olarak tampona alıyoruz.
            noise_samples: list[float] = []
            calib_until = time.time() + 0.25
            while time.time() < calib_until:
                chunk = mic.read(timeout=0.3)
                if chunk is None:
                    break
                r = _rms(chunk)
                if r > 0.04:              # bu gürültü değil, konuşma!
                    pending = chunk
                    break
                noise_samples.append(r)
            noise_samples.sort()
            noise_floor = (noise_samples[len(noise_samples) // 2]   # medyan:
                           if noise_samples else 0.005)             # kirlenmeye dayanıklı
            # Eşikler TAVANLI: taban ne kadar kirlenirse kirlensin normal
            # konuşma (RMS ≥ ~0.05) her zaman eşiği aşabilir.
            start_threshold = min(max(0.012, noise_floor * 3.5), 0.045)
            stop_threshold = min(max(0.008, noise_floor * 2.0), 0.030)

            if pending is not None:       # kalibrasyona taşan konuşma kaybolmasın
                speaking = True
                buf.extend(pending)
                peak_rms = _rms(pending)

            # 2) Konuşmayı yakala
            while time.time() - start < timeout:
                chunk = mic.read(timeout=0.5)
                if chunk is None:
                    continue
                rms = _rms(chunk)
                peak_rms = max(peak_rms, rms)
                block_ms = (len(chunk) / 2) / rate * 1000
                if rms > start_threshold:
                    speaking = True
                    silence_acc = 0.0
                    buf.extend(chunk)
                elif speaking:
                    buf.extend(chunk)
                    if rms < stop_threshold:
                        silence_acc += block_ms
                        if silence_acc >= silence_ms:
                            break
                    else:
                        silence_acc = 0.0
        finally:
            mic.close()
        FasterWhisperSTT._last_peak = peak_rms
        FasterWhisperSTT._last_threshold = start_threshold
        return resample_to_16k(bytes(buf), rate)

    # ── Ana giriş noktası (bloklayıcı — to_thread ile çağır) ────────────────
    def listen_and_transcribe(self, timeout: float = 12.0) -> str:
        if self._model is None and not self.preload():
            raise RuntimeError(self.last_error or "STT hazır değil")

        pcm = self._record_utterance(timeout=timeout)
        self.last_capture_sec = len(pcm) / 2 / SAMPLE_RATE
        if len(pcm) < SAMPLE_RATE:  # <0.5 sn ses → gürültü, Whisper'ı yorma
            return ""

        if self.engine == "vosk" or self._model is None:
            return self._vosk_fallback(pcm)

        import numpy as np
        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=1,
            vad_filter=True,                      # Whisper'ın dahili VAD'i: sessiz
            vad_parameters={"min_silence_duration_ms": 400},  # bölümleri atar
            condition_on_previous_text=False,     # tekrar/halüsinasyonu azaltır
            initial_prompt="Türkçe günlük konuşma.",  # TR bağlam ipucu
            no_speech_threshold=0.5,
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        # Whisper'ın bilinen boş-ses halüsinasyonlarını ele
        if text.lower() in {"altyazı m.k.", "izlediğiniz için teşekkürler.",
                            "abone olmayı unutmayın."}:
            return ""
        return text


# ══ Mikrofon teşhisi ════════════════════════════════════════════════════════
def mic_test(seconds: int = 3, on_log=lambda m: None) -> str:
    """
    'Mikrofonu test et' — birkaç saniye kaydeder ve NE DUYDUĞUNU sayısal
    olarak söyler: hangi arka uç (sounddevice/parec/arecord), tepe seviye,
    çözümlenen metin. Eskiden doğrudan sd.rec() kullanıyordu — sounddevice
    hatasız ama SESSİZ kalırsa (CachyOS'ta gözlenen davranış) test de yanlış
    biçimde "hiç ses yok" derdi. Artık MicStream kullanır: sounddevice
    sessizse otomatik parec/arecord'a düşer, GERÇEK durumu raporlar.
    """
    try:
        import numpy as np
        from .audio_input import MicStream, resample_to_16k
    except ImportError as e:
        return f"Test için eksik paket: {e} (pip install numpy)"

    logs: list[str] = []
    mic = MicStream(samplerate=16000, blocksize=1024,
                    log=lambda m: (logs.append(m), on_log(m)))
    on_log(f"SYS: 🎤 {seconds} saniye konuş — dinliyorum...")
    if not mic.start():
        detail = logs[-1] if logs else "bilinmeyen sebep"
        return (f"Mikrofondan HİÇ veri alınamadı ({detail}).\n"
                "Kontrol: 'arecord -l' ile aygıtı listele; pavucontrol > Giriş "
                "Aygıtları'nda mikrofon susturulmuş olmasın; "
                "sudo apt install pulseaudio-utils alsa-utils")

    rate = mic.rate
    chunks = bytearray()
    deadline = time.time() + seconds
    while time.time() < deadline:
        c = mic.read(timeout=0.3)
        if c:
            chunks.extend(c)
    mic.close()

    pcm = bytes(chunks)
    x = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0

    lines = [f"Arka uç: {mic.backend} @ {rate} Hz",
             f"Tepe seviye: {peak:.3f} · Ortalama: {rms:.3f}"]

    if peak < 0.01:
        lines.append("SONUÇ: Hiç ses gelmiyor. Mikrofon kapalı/susturulmuş ya da "
                     "yanlış aygıt seçili. pavucontrol'den giriş aygıtını kontrol et.")
        return "\n".join(lines)
    if peak < 0.05:
        lines.append("SONUÇ: Ses ÇOK KISIK. Sistem ayarlarından mikrofon kazancını "
                     "yükselt ya da mikrofona yaklaş (eşik ~0.045).")
        return "\n".join(lines)

    lines.append("SONUÇ: Ses seviyesi yeterli ✓ — şimdi çözümlemeyi deniyorum...")
    try:
        stt = FasterWhisperSTT(model_size="base")
        if stt.preload():
            audio_pcm = resample_to_16k(pcm, rate)
            arr = np.frombuffer(audio_pcm, dtype=np.int16).astype(np.float32) / 32768.0
            if stt.engine == "vosk":
                text = stt._vosk_fallback(audio_pcm)
            else:
                segs, _ = stt._model.transcribe(arr, language="tr", beam_size=1,
                                                vad_filter=True)
                text = " ".join(sg.text.strip() for sg in segs).strip()
            lines.append(f"Duyduğum ({stt.engine}): \"{text}\"" if text
                         else f"Ses var ama söz çözümlenemedi ({stt.engine}, daha net konuş).")
        else:
            lines.append(f"Ne Whisper ne Vosk yüklenemedi: {stt.last_error}")
    except Exception as e:
        lines.append(f"Çözümleme hatası: {e}")
    return "\n".join(lines)
