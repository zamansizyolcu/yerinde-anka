"""
backend/config.py — Arayüzdeki sol panelin birebir yansıması.

GUI'deki her ayar (MODEL, OLLAMA MODELİ, SES, ANLAMA, ses düzeyi...) bu
dataclass'ta bir alana karşılık gelir. SystemController bu nesneyi okur;
kullanıcı panelde bir şeyi değiştirdiğinde GUI sadece bu nesneyi günceller
(update_from_gui) — backend bir sonraki işlemde yeni değeri otomatik kullanır.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    # ── Beyin / Model Router ────────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    chat_model: str = "gemma2"              # Orkestra şefi + sohbet (GUI: OLLAMA MODELİ)
    coder_model: str = "qwen2.5-coder"      # Kod/Blender/Godot üretimi
    vision_model: str = "qwen2-vl"          # Kamera nesne analizi (alternatif: llama3.2-vision)
    num_ctx: int = 8192
    keep_alive: str = "30m"

    # ── Wake word ───────────────────────────────────────────────────────────
    wake_word: str = "yerinde"
    wake_enabled: bool = True          # AYAR: "Yerinde" ile uyanma aç/kapa
    voice_shutdown_enabled: bool = True  # AYAR: "kendini kapat" sesli komutu aç/kapa
    vosk_model_path: str = "vosk-model"     # küçük TR modeli yeterli (yalnızca tetikleme)

    # ── STT (GUI: ANLAMA) ───────────────────────────────────────────────────
    whisper_model_size: str = "small"       # small / medium / large-v3
    stt_language: str = "tr"

    # ── TTS (GUI: SES) ──────────────────────────────────────────────────────
    # "piper"            → Piper (bildirimler + varsayılan)
    # "chattts"          → ChatTTS (doğal sohbet tonu)
    # "xtts:<ref.wav>"   → Coqui XTTS-v2 ses klonlama (referans wav yolu, in-process)
    voice_profile: str = "piper"
    piper_binary: str = "piper"             # PATH'te yoksa tam yol ver
    piper_voice: str = str(Path("voices") / "tr_TR-dfki-medium.onnx")
    xtts_model: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    volume: float = 0.20                    # GUI: SES DÜZEYİ %20 → 0.0–1.0

    # ── Kamera / Görü ───────────────────────────────────────────────────────
    camera_index: int = 0
    yolo_enabled: bool = True      # AYAR: nesne algılama (YOLO) aç/kapa
    intent_only: bool = False      # AYAR: SADECE KOMUT MODU — LLM hiç kullanılmaz
    yolo_model: str = "yolo11n.pt"          # ultralytics YOLO11 nano (hızlı)
    yolo_conf: float = 0.35

    # ── Bahçe kamerası (Yoosee YS-09 / Xiongmai DVRIP, port 34567) ─────────
    # Güneş enerjili; uyku modundayken TCP timeout verir, "uyandır" ile açılır.
    garden_host: str = "192.168.1.108"
    garden_port: int = 34567
    garden_user: str = "yerinde"
    garden_pass: str = "45923122.ye"
    garden_channel: int = 0              # DVRIP kanalı 0-bazlı
    garden_wake_attempts: int = 4        # uyandırma denemesi
    garden_wake_timeout: float = 8.0     # deneme başına TCP timeout (sn)
    garden_wake_sleep: float = 6.0       # denemeler arası bekleme (sn)
    garden_ptz_stop_brake: bool = True   # DirectionStop işe yaramayınca dik eksen freni gönder


    # ── Genel ───────────────────────────────────────────────────────────────
    listen_timeout_s: float = 12.0          # tetikleme sonrası azami dinleme
    extra: dict = field(default_factory=dict)

    def update_from_gui(self, **kwargs) -> None:
        """GUI panelinden gelen değişiklikleri güvenli şekilde uygular.
        Örn: settings.update_from_gui(voice_profile='chattts', volume=0.35)"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
