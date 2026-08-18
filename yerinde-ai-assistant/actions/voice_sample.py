"""
actions/voice_sample.py — "Sesimi kaydet": mikrofon örneği alıp YERINDE'nin
çevrimdışı sesi olarak ayarlar (Coqui XTTS-v2 ses klonlama profili üzerinden).

Akış: 10 sn kayıt → voices/kendi_sesim.wav → offline_voice_choice =
"xtts:voices/kendi_sesim.wav". Konuşmanın senin sesinle SENTEZLENMESİ
XTTS-v2 modeliyle AYNI SÜREÇTE yapılır (ayrı sunucu YOK) — model ilk
kullanımda tembel yüklenir; kurulu değilse YERINDE bunu loglar ve yedek
sese döner, kayıt yine saklanır.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_PATH = BASE_DIR / "voices" / "kendi_sesim.wav"


def record_voice_sample(seconds: int = 10, on_log=lambda m: None) -> str:
    seconds = max(5, min(int(seconds or 10), 30))
    try:
        from backend.audio_input import MicStream, resample_to_16k
    except ImportError as e:
        return f"Kayıt için eksik paket: {e}"

    # MicStream: sounddevice sessiz kalırsa (hata vermeden veri
    # göndermezse) otomatik olarak parec/arecord'a düşer — "sesimi
    # kaydet" dediğinde sessiz bir WAV kaydedip yanıltmasın diye.
    mic = MicStream(samplerate=16000, blocksize=1024, log=on_log)
    on_log(f"SYS: 🎙 {seconds} saniyelik kayıt başlıyor — doğal bir şeyler söyle...")
    if not mic.start():
        return "Mikrofon açılamadı — kayıt alınamadı."

    buf = bytearray()
    deadline = time.time() + seconds
    while time.time() < deadline:
        chunk = mic.read(timeout=0.3)
        if chunk:
            buf.extend(chunk)
    rate = mic.rate
    mic.close()

    if len(buf) < rate:  # <1 sn ses → muhtemelen mikrofon susturulmuş
        return ("Neredeyse hiç ses kaydedilemedi — mikrofon susturulmuş "
                "olabilir. pavucontrol'den giriş aygıtını kontrol edip tekrar dene.")

    pcm = resample_to_16k(bytes(buf), rate)  # XTTS için 16k mono yeterli
    SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(SAMPLE_PATH), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(pcm)

    # Ses profilini otomatik geçir
    try:
        from app_config import save_app_config
        save_app_config({"offline_voice_choice": f"xtts:{SAMPLE_PATH}"})
    except Exception:
        pass

    return (f"Ses örneğin kaydedildi ({SAMPLE_PATH.name}, {seconds} sn) ve "
            "çevrimdışı ses profilin 'KENDİ SESİM' olarak ayarlandı. "
            "Sesinin klonlanması için Coqui XTTS-v2 gerekir "
            "(pip install coqui-tts) — ayrı bir sunucu kurmana gerek YOK, "
            "ilk konuşmada model kendisi yüklenir; kurulu değilse yedek "
            "sesle konuşurum.")
