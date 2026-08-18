"""
actions/pico_devre_atolyesi.py — YERİNDE Pico Devre Atölyesini tarayıcıda
açar VE (araç açıkken) sesli komutlarla canlı olarak yönetir.

3B Tasarım Stüdyosu / Robot Tasarım Atölyesi / YERİNDE Kodlama Aracı ile AYNI
köprü mimarisi (core/bridge_server.py) paylaşılır — ayrı bir sunucu/port
gerekmez, çünkü sesli komutlar zaten hangi araç o an bağlıysa ona gider.

YERİNDE Pico Devre Atölyesi; Raspberry Pi Pico / Pico W / Arduino Nano /
ESP32 DevKit V1 için, Tinkercad Circuits benzeri bir breadboard + Blockly
tabanlı blok kodlama aracıdır. Bu modül şunları sesli komuta bağlar:
  - Aracı açma
  - Kart değiştirme (Pico / Pico W / Nano / ESP32)
  - Devre elemanı ekleme (LED, direnç, buton, buzzer, potansiyometre, LDR,
    servo, ultrasonik sensör, OLED ekran, DC motor, motor sürücü, pil,
    güneş paneli)
  - Blok kod ekleme/silme (Blockly çalışma alanına)
  - Blok/Kod (Python ya da Arduino C++) görünümü arasında geçiş
  - Tema değiştirme (mavi/yeşil/krem)
  - Simülasyonu başlatma/durdurma
  - Projeyi kaydetme/açma (.yerpico dosyası, Çalışmalarım/Devre-Atolyesi)
  - Üretilen kodu (MicroPython/Arduino C++) Çalışmalarım'a kaydetme
  - Aracı kapatma
"""

from __future__ import annotations

import json
import platform
import subprocess
import time
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

_NOT_OPEN_MSG = ("YERİNDE Pico Devre Atölyesi şu an açık değil gibi görünüyor — "
                  "önce 'pico devre atölyesini aç' diyerek açar mısın?")


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "pico-devre-atolyesi" / "pico-devre-atolyesi.html"


def open_pico_devre_atolyesi() -> str:
    """'pico devre atölyesini aç' / 'devre atölyesini aç' / 'breadboard
    aracını aç' / 'pico simülatörünü aç' — Raspberry Pi Pico / Pico W /
    Arduino Nano / ESP32 için Tinkercad benzeri breadboard + blok kodlama
    aracını tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Pico Devre Atölyesi bulunamadı — 'pico-devre-atolyesi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("Pico Devre Atölyesi tarayıcıda açılıyor! Soldan bir devre elemanı "
                "ekleyip breadboard'a kablo çekebilir, Blok ya da Kod modunda "
                "programlayabilir, 'Simülasyonu Başlat' ile test edebilirsin. "
                "Artık sesli komutlarla da yönlendirebilirsin.")
    except Exception as e:
        return f"Pico Devre Atölyesi açılamadı: {e}"


def _send_or_warn(payload: dict, basari_mesaji: str) -> str:
    if bridge_server.send_command(payload):
        return basari_mesaji
    return _NOT_OPEN_MSG


# ---------------------------------------------------------------------
# Kart değiştirme
# ---------------------------------------------------------------------

_KART_HARITASI = {
    "pico": "pico", "raspberry pi pico": "pico",
    "pico w": "picow", "picow": "picow", "pico double u": "picow",
    "nano": "nano", "arduino nano": "nano",
    "esp32": "esp32", "esp 32": "esp32", "esp32 devkit": "esp32", "esp otuz iki": "esp32",
}


def pico_kart_degistir_command(kart: str) -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, kullanılan kartı
    değiştirir: Raspberry Pi Pico, Pico W, Arduino Nano ya da ESP32 DevKit V1.
    'Pico'ya geç', 'Pico W kullan', 'Nano'ya geç', 'ESP32'ye geç' gibi
    komutlarla tetiklenir."""
    key = (kart or "").strip().lower()
    board_id = _KART_HARITASI.get(key)
    if not board_id:
        return f"'{kart}' tanıdık bir kart değil — Pico, Pico W, Nano ya da ESP32 diyebilirsin."
    return _send_or_warn({"action": "switch_board", "board": board_id}, f"{kart} kartına geçiyorum!")


# ---------------------------------------------------------------------
# Devre elemanı ekleme
# ---------------------------------------------------------------------

_BILESEN_HARITASI = {
    "led": "led", "ışık diyotu": "led",
    "direnç": "resistor", "direnc": "resistor",
    "buton": "button", "düğme": "button", "dugme": "button",
    "buzzer": "buzzer", "öten": "buzzer", "ötücü": "buzzer", "vızıldayıcı": "buzzer",
    "potansiyometre": "potentiometer", "potansiyometer": "potentiometer",
    "ışık sensörü": "ldr", "isik sensoru": "ldr", "ldr": "ldr",
    "servo": "servo", "servo motor": "servo",
    "ultrasonik": "ultrasonic", "ultrasonik sensör": "ultrasonic", "mesafe sensörü": "ultrasonic", "mesafe sensoru": "ultrasonic",
    "oled": "oled_display", "oled ekran": "oled_display", "ekran": "oled_display",
    "dc motor": "dc_motor", "redüktörlü motor": "dc_motor", "reduktorlu motor": "dc_motor", "motor": "dc_motor",
    "motor sürücü": "motor_driver", "motor surucu": "motor_driver", "motor sürücüsü": "motor_driver",
    "pil": "battery", "batarya": "battery",
    "güneş paneli": "solar_panel", "gunes paneli": "solar_panel",
}


def pico_bilesen_ekle_command(bilesen: str) -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard'a (ya da
    serbest alana) yeni bir devre elemanı ekler — sanki sol paletten
    sürükleyip bırakmış gibi. LED, direnç, buton, buzzer, potansiyometre,
    ışık sensörü (LDR), servo motor, ultrasonik sensör, OLED ekran, DC motor,
    motor sürücü, pil ya da güneş paneli eklenebilir. 'LED ekle', 'direnç
    ekle', 'servo motor ekle', 'pil ekle' gibi komutlarla tetiklenir."""
    key = (bilesen or "").strip().lower()
    comp_type = _BILESEN_HARITASI.get(key)
    if not comp_type:
        return (f"'{bilesen}' tanıdık bir devre elemanı değil — LED, direnç, buton, buzzer, "
                "potansiyometre, ışık sensörü, servo, ultrasonik, OLED ekran, DC motor, "
                "motor sürücü, pil ya da güneş paneli diyebilirsin.")
    return _send_or_warn({"action": "add_component", "componentType": comp_type}, f"{bilesen.capitalize()} ekliyorum!")


def pico_bilesen_sil_command(bilesen: str = "") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest
    alandaki bir devre elemanını (ve ona bağlı tüm kabloları) siler.
    'bilesen' verilirse (led, direnç, buton, buzzer, potansiyometre, ışık
    sensörü, servo, ultrasonik, oled, dc motor, motor sürücü, pil, güneş
    paneli) o türden EN SON EKLENEN öğe silinir; verilmezse SON EKLENEN
    devre elemanı (türü ne olursa olsun) silinir. 'LED'i sil', 'son eklenen
    direnci sil', 'son eklenen devre elemanını sil' gibi komutlarla
    tetiklenir. DİKKAT: bir kodlama BLOĞUNU silmekle (pico_blok_sil_command)
    KARIŞTIRILMAMALIDIR — bu, breadboard üzerindeki FİZİKSEL bir devre
    elemanını siler."""
    key = (bilesen or "").strip().lower()
    payload = {"action": "delete_component"}
    if key:
        comp_type = _BILESEN_HARITASI.get(key)
        if not comp_type:
            return (f"'{bilesen}' tanıdık bir devre elemanı değil — LED, direnç, buton, buzzer, "
                    "potansiyometre, ışık sensörü, servo, ultrasonik, OLED ekran, DC motor, "
                    "motor sürücü, pil ya da güneş paneli diyebilirsin.")
        payload["componentType"] = comp_type
        return _send_or_warn(payload, f"{bilesen.capitalize()} siliniyor!")
    return _send_or_warn(payload, "Son eklenen devre elemanını siliyorum!")


def pico_bilesen_dondur_command(bilesen: str = "") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest
    alandaki bir devre elemanını döndürür — sanki özellik panelindeki
    '↻ Döndür' düğmesine basmış gibi. Breadboard'a takılan elemanlar (LED,
    direnç, buton, buzzer, potansiyometre, LDR) sadece 0/180 derece arasında
    aynalanır (yönü değişir); serbest duran elemanlar (servo, ultrasonik,
    OLED, DC motor, motor sürücü, pil, güneş paneli) 90 derecelik adımlarla
    tam döner. 'bilesen' verilirse o türden EN SON EKLENEN öğe döndürülür;
    verilmezse SON EKLENEN devre elemanı (türü ne olursa olsun) döndürülür.
    'LED'i döndür', 'son eklenen direnci döndür', 'servoyu döndür' gibi
    komutlarla tetiklenir."""
    key = (bilesen or "").strip().lower()
    payload = {"action": "rotate_component"}
    if key:
        comp_type = _BILESEN_HARITASI.get(key)
        if not comp_type:
            return (f"'{bilesen}' tanıdık bir devre elemanı değil — LED, direnç, buton, buzzer, "
                    "potansiyometre, ışık sensörü, servo, ultrasonik, OLED ekran, DC motor, "
                    "motor sürücü, pil ya da güneş paneli diyebilirsin.")
        payload["componentType"] = comp_type
        return _send_or_warn(payload, f"{bilesen.capitalize()} döndürülüyor!")
    return _send_or_warn(payload, "Son eklenen devre elemanını döndürüyorum!")


_YON_HARITASI = {
    "sağ": "right", "sag": "right", "sağa": "right", "saga": "right",
    "sol": "left", "sola": "left",
    "yukarı": "up", "yukari": "up", "yukarıya": "up", "yukariya": "up", "üst": "up", "ust": "up", "yukarı doğru": "up",
    "aşağı": "down", "asagi": "down", "aşağıya": "down", "asagiya": "down", "alt": "down", "aşağı doğru": "down",
}


def pico_bilesen_tasi_command(bilesen: str = "", yon: str = "", miktar: str = "1") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest
    alandaki bir devre elemanını sağa, sola, yukarı ya da aşağı taşır —
    sanki elle sürükleyip bırakmış gibi. 'bilesen' verilirse o türden EN
    SON EKLENEN öğe taşınır; verilmezse SON EKLENEN devre elemanı (türü ne
    olursa olsun) taşınır. Breadboard'a takılı elemanlarda 'yukarı'/'aşağı'
    komşu satıra (a-e ya da f-j şeridi İÇİNDE, şeritler arası geçiş YOKTUR),
    'sağa'/'sola' komşu sütuna taşır; serbest duran elemanlarda dört yöne de
    serbestçe taşınabilir. 'miktar' kaç adım taşınacağını belirtir (verilmezse
    1 adım). 'LED'i sağa taşı', 'servoyu 3 birim yukarı kaydır', 'son eklenen
    devre elemanını sola taşı' gibi komutlarla tetiklenir."""
    yon_key = (yon or "").strip().lower()
    dir_value = _YON_HARITASI.get(yon_key)
    if not dir_value:
        return f"'{yon}' tanıdık bir yön değil — sağ, sol, yukarı ya da aşağı diyebilirsin."
    try:
        steps = max(1, int(str(miktar).strip() or "1"))
    except ValueError:
        steps = 1

    key = (bilesen or "").strip().lower()
    payload = {"action": "move_component", "dir": dir_value, "steps": steps}
    if key:
        comp_type = _BILESEN_HARITASI.get(key)
        if not comp_type:
            return (f"'{bilesen}' tanıdık bir devre elemanı değil — LED, direnç, buton, buzzer, "
                    "potansiyometre, ışık sensörü, servo, ultrasonik, OLED ekran, DC motor, "
                    "motor sürücü, pil ya da güneş paneli diyebilirsin.")
        payload["componentType"] = comp_type
        return _send_or_warn(payload, f"{bilesen.capitalize()} {yon} taşınıyor!")
    return _send_or_warn(payload, f"Son eklenen devre elemanını {yon} taşıyorum!")


# ---------------------------------------------------------------------
# Blok/Kod modu ve tema
# ---------------------------------------------------------------------

def pico_mod_degistir_command(mod: str) -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, görünümü Blok Modu
    (Blockly, sürükle-bırak) ile Kod Modu (üretilen gerçek MicroPython ya da
    Arduino C++ kodunu gösterir - hangi kart seçiliyse ona göre) arasında
    değiştirir. 'blok moduna geç', 'kod moduna geç', 'python koduna geç'
    gibi komutlarla tetiklenir."""
    key = (mod or "").strip().lower()
    if key in ("blok", "block", "blok modu", "bloklar"):
        return _send_or_warn({"action": "set_mode", "mode": "blok"}, "Blok Moduna geçiyorum!")
    if key in ("kod", "code", "kod modu", "python", "python modu", "piton"):
        return _send_or_warn({"action": "set_mode", "mode": "kod"}, "Kod Moduna geçiyorum!")
    return "'blok' ya da 'kod' diyebilirsin."


_TEMA_HARITASI = {"mavi": "blue", "yeşil": "green", "yesil": "green", "krem": "cream"}


def pico_tema_degistir_command(tema: str) -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, arayüz temasını
    değiştirir: mavi, yeşil ya da krem. 'temayı yeşil yap', 'krem temaya
    geç' gibi komutlarla tetiklenir."""
    key = (tema or "").strip().lower()
    theme_id = _TEMA_HARITASI.get(key)
    if not theme_id:
        return f"'{tema}' tanıdık bir tema değil — mavi, yeşil ya da krem diyebilirsin."
    return _send_or_warn({"action": "set_theme", "theme": theme_id}, f"Temayı {tema} yapıyorum!")


def pico_yakinlastir_command(yon: str = "in") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard görünümünü
    yakınlaştırır, uzaklaştırır ya da sıfırlar. 'yakınlaştır', 'uzaklaştır',
    'yakınlaştırmayı sıfırla' gibi komutlarla tetiklenir."""
    key = (yon or "").strip().lower()
    d = "reset"
    if key in ("in", "yakınlaştır", "yakinlastir", "büyüt", "buyut"):
        d = "in"
    elif key in ("out", "uzaklaştır", "uzaklastir", "küçült", "kucult"):
        d = "out"
    return _send_or_warn({"action": "zoom", "dir": d}, "Tamam!")


# ---------------------------------------------------------------------
# Simülasyon çalıştırma
# ---------------------------------------------------------------------

def pico_calistir_command() -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, 'Simülasyonu Başlat'
    düğmesine basılmış gibi devrenin canlı simülasyonunu başlatır.
    'simülasyonu başlat', 'devreyi çalıştır' gibi komutlarla tetiklenir."""
    return _send_or_warn({"action": "run_program"}, "Simülasyonu başlatıyorum!")


def pico_durdur_command() -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, çalışmakta olan
    simülasyonu durdurur. 'simülasyonu durdur', 'devreyi durdur' gibi
    komutlarla tetiklenir."""
    return _send_or_warn({"action": "stop_program"}, "Simülasyonu durduruyorum!")


# ---------------------------------------------------------------------
# Proje kaydetme/açma
# ---------------------------------------------------------------------

def pico_kaydet_command() -> str:
    """YERİNDE Pico Devre Atölyesindeki projeyi (seçili kart, tüm devre
    elemanları/kablolar ve Blockly programı ile birlikte) doğrudan
    Çalışmalarım/Devre-Atolyesi klasörüne bir .yerpico dosyası olarak
    kaydeder. 'devre projesini kaydet', 'projeyi çalışmalarıma kaydet'
    gibi komutlarla tetiklenir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    raw = bridge_server.request_and_wait({"action": "request_project_export"}, timeout=8.0)
    if raw is None:
        return "Araçtan proje verisi alınamadı (zaman aşımı)."
    try:
        data = json.loads(raw)
    except Exception:
        return "Proje verisi okunamadı (beklenmeyen format)."
    if not data.get("ok", True):
        return data.get("message", "Proje dışa aktarılamadı.")
    proje_json = data.get("data")
    if not proje_json:
        return "Proje verisi boş geldi."

    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Devre-Atolyesi")
    target = folder / f"devre-projem {time.strftime('%Y-%m-%d %H.%M')}.yerpico"
    try:
        target.write_text(proje_json, encoding="utf-8")
    except Exception as e:
        return f"Proje kaydedilemedi: {e}"
    return f"Proje kaydedildi: {target.name} (Çalışmalarım/Devre-Atolyesi klasörü)."


def pico_ac_command(dosya_adi: str = "") -> str:
    """Çalışmalarım/Devre-Atolyesi klasöründe verilen isme uyan (ya da isim
    verilmezse en son kaydedilen) bir .yerpico dosyasını bulup açık olan
    YERİNDE Pico Devre Atölyesine yükler. 'devre projemi aç', 'son
    kaydettiğim devre projesini aç' gibi komutlarla tetiklenir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG

    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Devre-Atolyesi")
    candidates = sorted(folder.glob("*.yerpico"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return "Çalışmalarım/Devre-Atolyesi klasöründe hiç .yerpico dosyası bulunamadı."

    name_key = (dosya_adi or "").strip().lower()
    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
    chosen = matches[0] if matches else candidates[0]

    try:
        raw = chosen.read_text(encoding="utf-8")
    except Exception as e:
        return f"Dosya okunamadı: {e}"
    ok = bridge_server.send_command({"action": "load_project_data", "data": raw})
    if not ok:
        return _NOT_OPEN_MSG
    return f"{chosen.name} projesini yüklüyorum!"


def pico_kodu_indir_command() -> str:
    """YERİNDE Pico Devre Atölyesindeki, o an seçili karta göre üretilen
    GERÇEK kodu (Pico/Pico W için MicroPython .py, Arduino Nano/ESP32 için
    Arduino C++ .ino) doğrudan Çalışmalarım/Devre-Atolyesi klasörüne
    kaydeder. 'kodu indir', 'python kodunu kaydet', 'arduino kodunu
    çalışmalarıma kaydet' gibi komutlarla tetiklenir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    raw = bridge_server.request_and_wait({"action": "request_code_export"}, timeout=6.0)
    if raw is None:
        return "Araçtan kod verisi alınamadı (zaman aşımı)."
    try:
        data = json.loads(raw)
    except Exception:
        return "Kod verisi okunamadı (beklenmeyen format)."
    if not data.get("ok", True):
        return data.get("message", "Kod üretilemedi.")
    code = data.get("data")
    filename = data.get("filename") or "devre_kodu.py"
    if not code:
        return "Kod verisi boş geldi."

    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Devre-Atolyesi")
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".py"
    target = folder / f"{stem} {time.strftime('%Y-%m-%d %H.%M')}{suffix}"
    try:
        target.write_text(code, encoding="utf-8")
    except Exception as e:
        return f"Kod dosyası kaydedilemedi: {e}"
    return f"Kod kaydedildi: {target.name} (Çalışmalarım/Devre-Atolyesi klasörü)."


# ---------------------------------------------------------------------
# Blok kod ekleme/silme
# ---------------------------------------------------------------------

# Blockly'deki dahili blok türü adı -> kullanıcıya gösterilecek Türkçe etiket.
_BLOK_ETIKETLERI = {
    "pico_digital_write": "dijital yaz", "pico_pwm_write": "PWM yaz",
    "pico_servo_write": "servo döndür", "pico_tone_write": "ton çal",
    "pico_tone_stop": "tonu durdur", "pico_onboard_led": "yerleşik LED",
    "pico_wait": "bekle", "pico_serial_print": "seri yazdır",
    "pico_motor_write": "motor sürücü çalıştır", "pico_display_write": "ekrana yaz",
    "pico_display_clear": "ekranı temizle",
}

# Her blok türü için hangi ALAN'ların (dropdown) ve hangi GİRİŞ'lerin
# (sayı/metin değeri) doldurulacağını belirler - pico_blok_ekle_command
# genel parametrelerini (pin/pin2/deger/yon/birim) doğru yerlere eşler.
_BLOK_SEMASI = {
    "pico_digital_write": {"fields": {"PIN": "pin", "VAL": "yon"}},
    "pico_pwm_write": {"fields": {"PIN": "pin"}, "values": {"VALUE": "deger"}},
    "pico_servo_write": {"fields": {"PIN": "pin"}, "values": {"ANGLE": "deger"}},
    "pico_tone_write": {"fields": {"PIN": "pin"}, "values": {"FREQ": "deger"}},
    "pico_tone_stop": {"fields": {"PIN": "pin"}},
    "pico_onboard_led": {"fields": {"VAL": "yon"}},
    "pico_wait": {"fields": {"UNIT": "birim"}, "values": {"TIME": "deger"}},
    "pico_serial_print": {"values": {"TEXT": "deger"}},
    "pico_motor_write": {"fields": {"IN1": "pin", "IN2": "pin2", "DIR": "yon"}},
    "pico_display_write": {"fields": {"SDA": "pin", "SCL": "pin2"}, "values": {"TEXT": "deger"}},
    "pico_display_clear": {"fields": {"SDA": "pin", "SCL": "pin2"}},
}


def pico_blok_ekle_command(blok: str, pin: str = "", pin2: str = "", deger: str = "", yon: str = "", birim: str = "") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN VE Blok Modu'ndayken,
    Blockly çalışma alanına yeni bir kodlama bloğu ekler — tıpkı sol
    menüden sürükleyip bırakmış gibi (otomatik olarak 'süresiz' döngüsünün
    içine eklenir). 'blok' Blockly'deki dahili blok türü adıdır (ör.
    'pico_digital_write'). 'dijital yaz bloğu ekle', 'PWM yaz bloğu ekle',
    'servo döndür bloğu ekle', 'bekle bloğu ekle' gibi — cümlede AÇIKÇA
    'blok/bloğu ekle' geçtiğinde bu aracı kullan."""
    sema = _BLOK_SEMASI.get(blok)
    if not sema:
        return (f"'{blok}' tanıdık bir blok türü değil — dijital yaz, PWM yaz, servo döndür, "
                "ton çal, yerleşik LED, bekle, seri yazdır, motor sürücü çalıştır, ekrana yaz "
                "ya da ekranı temizle bloklarından birini isteyebilirsin.")
    kaynak = {"pin": pin, "pin2": pin2, "deger": deger, "yon": yon, "birim": birim}
    fields = {}
    for alan, kaynak_adi in sema.get("fields", {}).items():
        v = kaynak.get(kaynak_adi)
        if v:
            fields[alan] = v.upper()  # pin adları (GP2, D13, A0) ve sabitler (HIGH/LOW/FWD/...) hep büyük harf
    values = {}
    for girisAdi, kaynak_adi in sema.get("values", {}).items():
        v = kaynak.get(kaynak_adi)
        if v:
            values[girisAdi] = v

    payload = {"action": "add_block", "blockType": blok}
    if fields:
        payload["fields"] = fields
    if values:
        payload["values"] = values
    isim = _BLOK_ETIKETLERI.get(blok, blok)
    return _send_or_warn(payload, f"'{isim}' bloğunu ekliyorum!")


def pico_blok_sil_command() -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, Blockly çalışma
    alanındaki en son eklenen kodlama bloğunu siler ('başlangıçta'/'süresiz'
    bloklarına dokunmaz). 'bloğu sil', 'son bloğu sil' gibi komutlarla
    tetiklenir."""
    return _send_or_warn({"action": "delete_block"}, "Bloğu siliyorum!")


# ---------------------------------------------------------------------
# Bağlantı (kablo) çekme
# ---------------------------------------------------------------------

# Her bileşen türü için Türkçe pin adı -> dahili pin id eşlemesi. "" anahtarı
# (bileşen türü belirtilmemiş) kart pini demektir; kart pini adları zaten
# GND/GP2/3V3/D13/A0 gibi doğrudan kullanılır, ayrı bir haritaya gerek yoktur.
_PIN_HARITASI = {
    "led": {"artı": "a", "arti": "a", "+": "a", "anot": "a", "a": "a",
            "eksi": "c", "-": "c", "katot": "c", "c": "c"},
    "resistor": {"a": "a", "bir": "a", "birinci": "a", "1": "a",
                 "b": "b", "iki": "b", "ikinci": "b", "öbür": "b", "obur": "b", "2": "b"},
    "button": {"a": "a1", "a1": "a1", "bir": "a1", "birinci": "a1", "sol": "a1",
               "b": "b1", "b1": "b1", "iki": "b1", "ikinci": "b1", "öbür": "b1", "obur": "b1", "sağ": "b1", "sag": "b1"},
    "buzzer": {"artı": "pos", "arti": "pos", "+": "pos", "pos": "pos",
               "eksi": "neg", "-": "neg", "neg": "neg"},
    "potentiometer": {"a": "a", "bir": "a", "birinci": "a", "uç1": "a", "uc1": "a",
                       "orta": "wiper", "wiper": "wiper", "orta uç": "wiper", "orta uc": "wiper",
                       "b": "b", "iki": "b", "ikinci": "b", "uç2": "b", "uc2": "b"},
    "ldr": {"a": "a", "bir": "a", "b": "b", "iki": "b"},
    "servo": {"sinyal": "sig", "sig": "sig", "s": "sig",
              "güç": "vcc", "guc": "vcc", "vcc": "vcc", "artı": "vcc", "arti": "vcc",
              "toprak": "gnd", "gnd": "gnd", "eksi": "gnd"},
    "ultrasonic": {"tetik": "trig", "trig": "trig", "yankı": "echo", "yanki": "echo", "echo": "echo",
                   "güç": "vcc", "guc": "vcc", "vcc": "vcc", "toprak": "gnd", "gnd": "gnd", "eksi": "gnd"},
    "oled_display": {"veri": "sda", "sda": "sda", "saat": "scl", "scl": "scl",
                      "güç": "vcc", "guc": "vcc", "vcc": "vcc", "toprak": "gnd", "gnd": "gnd", "eksi": "gnd"},
    "dc_motor": {"a": "a", "bir": "a", "b": "b", "iki": "b"},
    "motor_driver": {"in1": "in1", "in2": "in2", "in3": "in3", "in4": "in4",
                      "güç": "vcc", "guc": "vcc", "vcc": "vcc", "artı": "vcc", "arti": "vcc",
                      "toprak": "gnd", "gnd": "gnd", "eksi": "gnd",
                      "çıkış a1": "outA1", "cikis a1": "outA1", "a1 çıkışı": "outA1",
                      "çıkış a2": "outA2", "cikis a2": "outA2", "a2 çıkışı": "outA2",
                      "çıkış b1": "outB1", "cikis b1": "outB1", "b1 çıkışı": "outB1",
                      "çıkış b2": "outB2", "cikis b2": "outB2", "b2 çıkışı": "outB2"},
    "battery": {"artı": "pos", "arti": "pos", "+": "pos", "eksi": "neg", "-": "neg"},
    "solar_panel": {"artı": "pos", "arti": "pos", "+": "pos", "eksi": "neg", "-": "neg"},
}


def _cozumle_pin(bilesen: str, pin: str):
    """(bilesen_turu, pin_id) döndürür; bilesen bos ise (None, KART_PIN_ADI)
    döner. Eşleşme yoksa (False, hata_mesaji) döner."""
    bilesen_key = (bilesen or "").strip().lower()
    pin_key = (pin or "").strip().lower()
    if not bilesen_key or bilesen_key in ("kart", "board", "pico", "breadboard"):
        return None, (pin or "").strip().upper()
    comp_type = _BILESEN_HARITASI.get(bilesen_key)
    if not comp_type:
        return False, f"'{bilesen}' tanıdık bir devre elemanı değil."
    pin_map = _PIN_HARITASI.get(comp_type, {})
    pin_id = pin_map.get(pin_key)
    if not pin_id:
        # tam eşleşme yoksa, verilen ifadenin İÇİNDE bilinen bir anahtar var mı diye bak
        # (ör. "eksi bacağını" ifadesi "eksi" anahtarını içerir)
        for k, v in pin_map.items():
            if k and k in pin_key:
                pin_id = v
                break
    if not pin_id:
        secenekler = ", ".join(sorted(set(pin_map.keys())))
        return False, f"'{bilesen}' için '{pin}' tanıdık bir pin değil — {secenekler} diyebilirsin."
    return comp_type, pin_id


def pico_bagla_command(bilesen1: str, pin1: str, bilesen2: str = "", pin2: str = "") -> str:
    """Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki iki
    ucu (bir devre elemanının belirli bir pini VE/YA DA kartın bir pini)
    birbirine bir kabloyla bağlar — sanki elle kablo çekmiş gibi. 'bilesen1'/
    'bilesen2' boş bırakılırsa (ya da 'kart' denirse) ilgili pin KARTIN
    KENDİSİNE aittir (ör. 'GND', 'GP2', '3V3', 'D13', 'A0'); bir devre elemanı
    türü verilirse (led, direnç, buton, buzzer, potansiyometre, ışık sensörü,
    servo, ultrasonik, oled, dc motor, motor sürücü, pil, güneş paneli) o
    türün EN SON EKLENEN örneğinin belirtilen ucu/pini kullanılır. Örnekler:
    'LED'in artı bacağını GP2'ye bağla' (bilesen1='led', pin1='artı',
    bilesen2='', pin2='GP2'), 'LED'in eksi ucunu GND'ye bağla', 'direncin bir
    ucunu LED'in eksi bacağına bağla' (bilesen1='direnç', pin1='a',
    bilesen2='led', pin2='eksi'), 'servo'nun sinyal pinini GP15'e bağla'.
    'bağla', 'kabloyla bağla', 'bacağını ... bağla' gibi ifadelerle
    tetiklenir."""
    tip1, sonuc1 = _cozumle_pin(bilesen1, pin1)
    if tip1 is False:
        return sonuc1
    tip2, sonuc2 = _cozumle_pin(bilesen2, pin2)
    if tip2 is False:
        return sonuc2

    payload = {"action": "connect_pins", "fromPin": sonuc1, "toPin": sonuc2}
    if tip1:
        payload["fromType"] = tip1
    if tip2:
        payload["toType"] = tip2

    parca1 = f"{bilesen1} {pin1}".strip() if bilesen1 else pin1
    parca2 = f"{bilesen2} {pin2}".strip() if bilesen2 else pin2
    return _send_or_warn(payload, f"{parca1} ile {parca2} arasına kablo çekiyorum!")


def pico_kablo_sil_command(bilesen1: str = "", pin1: str = "", bilesen2: str = "", pin2: str = "") -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest
    alandaki bir kabloyu siler. Uç bilgileri (bilesen1/pin1/bilesen2/pin2 -
    pico_bagla_command ile AYNI kurallarla: bileşen türü boşsa kart pini)
    VERİLİRSE, o iki uç arasındaki kablo bulunup silinir; hiçbir uç
    verilmezse EN SON ÇEKİLEN kablo silinir. 'son kabloyu sil', 'LED'in
    eksi bacağı ile GND arasındaki kabloyu sil' gibi komutlarla tetiklenir.
    DİKKAT: bir devre elemanının kendisini silmekle (pico_bilesen_sil_command)
    KARIŞTIRILMAMALIDIR — bu SADECE kabloyu (bağlantıyı) siler, elemanın
    kendisine dokunmaz."""
    payload = {"action": "delete_wire"}
    if bilesen1 or pin1 or bilesen2 or pin2:
        tip1, sonuc1 = _cozumle_pin(bilesen1, pin1)
        if tip1 is False:
            return sonuc1
        tip2, sonuc2 = _cozumle_pin(bilesen2, pin2)
        if tip2 is False:
            return sonuc2
        payload["fromPin"] = sonuc1
        payload["toPin"] = sonuc2
        if tip1:
            payload["fromType"] = tip1
        if tip2:
            payload["toType"] = tip2
        return _send_or_warn(payload, "Belirttiğin kabloyu siliyorum!")
    return _send_or_warn(payload, "Son eklenen kabloyu siliyorum!")


# ---------------------------------------------------------------------
# Seri Monitör
# ---------------------------------------------------------------------

def pico_seri_monitor_command(durum: str = "ac") -> str:
    """Pico Devre Atölyesi tarayıcıda AÇIKKEN, Seri Monitör panelini açar ya
    da kapatır (kod içindeki 'seri yazdır' bloklarının çıktısını gösteren
    panel). 'seri monitörü aç', 'seri port ekranını göster', 'seri monitörü
    kapat' gibi komutlarla tetiklenir."""
    key = (durum or "ac").strip().lower()
    show = key not in ("kapat", "gizle", "kapali", "kapalı", "off", "hide")
    return _send_or_warn({"action": "toggle_serial_monitor", "show": show},
                          "Seri Monitörü açıyorum!" if show else "Seri Monitörü kapatıyorum!")

def pico_kapat_command() -> str:
    """YERİNDE Pico Devre Atölyesi tarayıcıda AÇIKKEN, o sekmeyi kapatmayı
    dener. 'pico devre atölyesini kapat', 'aracı kapat' gibi komutlarla
    tetiklenir. NOT: bazı tarayıcılar, script tarafından açılmamış
    sekmelerin kapatılmasını güvenlik nedeniyle engeller — bu durumda
    kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
