# Alp Ünlü tarafından yapılmıştır — @alppunlu
from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_PATH = CONFIG_DIR / "api_keys.json"


DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "voice": "Charon",
    # Gemini Live API (gerçek zamanlı sesli mod) için kullanılacak model.
    # Boş ("") bırakılırsa main.py'deki varsayılan (LIVE_MODEL) kullanılır.
    # AYARLAR > 'GEMİNİ MODELİ' düğmesinden seçilebilir.
    "gemini_live_model": "",
    "youtube_api_key": "",
    "youtube_channel_handle": "",
    # "gemini" (bulut, sesli gerçek zamanlı) veya "ollama" (tamamen çevrimdışı,
    # yerel Ollama sunucusu üzerinden metin tabanlı çalışır)
    "model_provider": "gemini",
    "ollama_host": "http://localhost:11434",
    "ollama_model": "llama3.1",
    # STT: Ayarlar panelindeki listeden seçilir — "whisper:small/medium/large-v3" veya "vosk"
    # (Türkçe'de en iyi doğruluk için "whisper:medium" önerilir)
    "stt_choice": "whisper:medium",
    "ollama_stt_engine": "whisper",   # geriye dönük uyumluluk
    "whisper_model_size": "medium",   # geriye dönük uyumluluk
    "vosk_model_path": "vosk-model",
    # Ollama bağlam penceresi (token) — varsayılan 2048 çok küçük kalıp
    # aracı çağırmayı 'unutmasına' yol açabiliyordu, bu yüzden büyütüldü.
    # RAM/VRAM yetersizse düşürebilirsin (ör. 4096).
    "ollama_num_ctx": 8192,
    # TTS: Piper kuruluysa (piper_binary_path/piper_voice_path ya da proje
    # kökündeki "piper/" ve "voices/" klasörleri) otomatik kullanılır;
    # değilse sistemin yerel TTS'ine (SAPI / espeak-ng) düşer.
    "piper_binary_path": "",
    "piper_voice_path": "",
    # Ayarlar panelindeki SES seçiciyle belirlenir: "auto" / "piper:<yol>" /
    # "sapi:<isim>" (Windows) / "espeak:<varyant>" (CachyOS)
    "offline_voice_choice": "auto",
    # "DOSYA YÜKLE" düğmesiyle en son seçilen dosyanın yolu
    "last_uploaded_file": "",
    # Kalıcı belge referansları kütüphanesi — "DOSYA YÜKLE" her seferinde
    # son yüklenen TEK dosyayı hatırlar (last_uploaded_file), ama zümre
    # tutanağı örneği, kazanım senaryosu, yıllık plan gibi belgeler AYNI
    # dosyayı defalarca (her yeni sınav/tutanak üretiminde) kullanmalı.
    # "bu dosyayı X olarak kaydet" dendiğinde referans_belge_kaydet burayı
    # doldurur (bkz. actions/belge_referanslari.py). Anahtar -> tam dosya yolu.
    "belge_referanslari": {},
    # TEMALAR > "ARKAPLAN RESMİ EKLE" ile seçilen özel arkaplanın dosya adı
    # (Arkaplanlar/ klasörüne kopyalanır; boşsa seçilen temanın rengi kullanılır)
    "ui_bg_image": "",
    # OBS Studio ekran kaydı kontrolü (obs-websocket v5) — OBS'te bir şifre
    # ayarlıysa aynısını buraya da yaz, aksi halde boş bırakılabilir.
    "obs_ws_host": "localhost",
    "obs_ws_port": 4455,
    "obs_ws_password": "",
    # AYARLAR panelindeki "DÜŞÜNME HIZI" düğmesiyle seçilir: "fast" | "normal" | "deep".
    # HEM Gemini (Live API thinking_budget) HEM Ollama (/api/chat "think" alanı)
    # bu TEK ayarı kullanır — model değiştiğinde ayrıca ayarlamana gerek yok.
    # "fast"  : düşünme kapalı  → en hızlı ilk yanıt (Gemini: budget=0, Ollama: think=false)
    # "normal": dengeli         → (Gemini: budget=512, Ollama: think=true)
    # "deep"  : en derin/yavaş  → (Gemini: budget=-1 otomatik, Ollama: think="high")
    # NOT: Ollama tarafında yalnızca "düşünen" modeller (qwen3, deepseek-r1,
    # gpt-oss...) bu alana tepki verir; gemma2/llama3.1 gibi düşünme
    # desteklemeyen modellerde alan sessizce yok sayılır (bkz. ollama_think_value).
    "thinking_level": "normal",
    # Bahçe kamerası (Yoosee YS-09, Xiongmai/DVRIP 34567) — güneş enerjili,
    # uyku modunda TCP timeout verir; "bahçe kamerasını aç" / "bahçe kamerasını
    # uyandır" sesli komutlarıyla uyandırılır. Ayarlar panelindeki BAHÇE KAMERA
    # alanlarından düzenlenebilir.
    "garden_host": "192.168.1.108",
    "garden_port": 34567,
    "garden_user": "yerinde",
    "garden_pass": "45923122.ye",
    "garden_channel": 0,
    "garden_wake_attempts": 4,
    "garden_wake_timeout": 8.0,
    "garden_wake_sleep": 6.0,
    # Bahçe kamerası gelişmiş kontrolleri.
    "garden_stream": "hd",               # 'hd' (Main) veya 'sd' (Extra)
    "garden_keepalive": 0,               # KeepAlive aralığı (s); 0 = kameranın AliveInterval'ı
    "garden_reconnect_attempts": 3,      # Akış beklenmedik kesilince otomatik yeniden bağlanma denemesi
    "garden_reconnect_sleep": 8.0,       # Denemeler arası bekleme (s)
    "garden_ptz_max_move": 10.0,         # Yön tuşu basılı kalınca güvenlik durdurma süresi (s)
    "garden_ptz_flip_left_right": True,  # True = kameranın sol/sağ yönleri ters dönüyorsa (bu kamera için öyle)
    # Bu kamerada DirectionStop tanınmıyor (Ret=100 döner ama motor durmaz);
    # hareket halindeyken eksene dik "fren" komutu (pan için DirectionUp) motoru
    # durduruyor. False yapılırsa yalnızca standart DirectionStop gönderilir.
    "garden_ptz_stop_brake": True,
    # Ses alarmı iki yönlü ses (OPTalk) kanalı ile çalışır.
    "garden_sound_cmd": 1565,            # OPSoundAlarmControl istek mesaj kodu
    "garden_sound_reply": 1566,          # OPSoundAlarmControl yanıt mesaj kodu
}


def load_app_config() -> dict:
    config = dict(DEFAULT_CONFIG)
    try:
        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            config.update(raw)
    except Exception:
        pass
    return config


def save_app_config(updates: dict) -> dict:
    config = load_app_config()
    for key, value in (updates or {}).items():
        if value is None:
            continue
        config[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(config, indent=4, ensure_ascii=False),
        encoding="utf-8",
    )
    return config


def get_app_config_value(key: str, default=None):
    return load_app_config().get(key, default)


def has_gemini_api_key() -> bool:
    value = str(get_app_config_value("gemini_api_key", "") or "").strip()
    return bool(value)


def get_model_provider() -> str:
    """'gemini' (bulut) veya 'ollama' (çevrimdışı) döner."""
    value = str(get_app_config_value("model_provider", "gemini") or "gemini").strip().lower()
    return "ollama" if value == "ollama" else "gemini"


def is_offline_mode() -> bool:
    return get_model_provider() == "ollama"


# ── Düşünme seviyesi: "fast" / "normal" / "deep" ────────────────────────────
# GUI'de rakam (0/256/-1) yerine tek, anlaşılır bir seçenek gösterilir; bu
# fonksiyonlar o seçimi her backend'in kendi API parametresine çevirir.
THINKING_LEVELS = ("fast", "normal", "deep")


def get_thinking_level() -> str:
    lvl = str(get_app_config_value("thinking_level", "normal") or "normal").strip().lower()
    return lvl if lvl in THINKING_LEVELS else "normal"


def gemini_thinking_budget(level: str | None = None) -> int:
    """'fast'/'normal'/'deep' -> Gemini Live API thinking_budget.
    0 = kapalı (en hızlı ilk ses yanıtı), pozitif = sınırlı düşünme payı,
    -1 = otomatik/dinamik (modelin kendi kararı — en derin ama en yavaş
    olabilir; Google'ın 2.5 native-audio modellerinde AYARLANMAMIŞSA zaten
    varsayılan davranış budur)."""
    lvl = (level or get_thinking_level())
    return {"fast": 0, "normal": 512, "deep": -1}.get(lvl, 512)


def ollama_think_value(level: str | None = None):
    """'fast'/'normal'/'deep' -> Ollama /api/chat 'think' alanı.
    Yalnızca düşünme destekleyen modellerde (qwen3, deepseek-r1, gpt-oss...)
    etkilidir; desteklemeyen modeller (gemma2, llama3.1 vb.) bu alanı
    sessizce yok sayar. backend/ollama_client.py ve ollama_assistant.py,
    model bu değeri REDDEDERSE (ör. yalnızca seviye kabul eden bir modele
    bool gönderilirse) otomatik olarak alanı kaldırıp sessizce tekrar dener
    — bu yüzden burada 'yanlış' bir değer seçmek asla oturumu kilitlemez."""
    lvl = (level or get_thinking_level())
    return {"fast": False, "normal": True, "deep": "high"}.get(lvl, True)
