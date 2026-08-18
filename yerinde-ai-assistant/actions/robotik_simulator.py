"""
actions/robotik_simulator.py — Robotik ve Devre Simülatörünü tarayıcıda açar.

Satranç / Çin Daması araçlarıyla AYNI mimari: sıfırdan yazılmış, tek dosyalık,
bağımsız HTML — dış sunucu/dosya bağımlılığı yok. Ortaokul/lise seviyesine
uygun, basit anlaşılır bir elektronik devre ve mikrodenetleyici (Arduino Uno,
ESP32, Raspberry Pi Pico, Pico W) simülatörü — engelden kaçan, ışık takip
eden ve çizgi izleyen robot senaryolarını canlı 2D animasyonla, devre şeması
ve örnek kodla birlikte gösterir. Simülasyon mantığı (sensörler, hareket)
kapsamlı testlerle doğrulanmıştır.
"""

from __future__ import annotations

import platform
import subprocess
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "robotik-simulator" / "robotik-simulator.html"


def open_robotik_simulator() -> str:
    """'robotik simülatörünü aç' / 'devre simülatörü aç' / 'robot simülasyonu aç'
    — tek dosyalık robotik/devre simülatörünü tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Robotik simülatör bulunamadı — 'robotik-simulator' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("Robotik ve Devre Simülatörü tarayıcıda açılıyor! Bir kart "
                "(Arduino Uno, ESP32, Raspberry Pi Pico veya Pico W) ve bir robot "
                "türü seçip devre şemasını, örnek kodu ve canlı simülasyonu "
                "izleyebilirsin.")
    except Exception:
        try:
            webbrowser.open(url)
            return "Robotik ve Devre Simülatörü tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def robotik_simulator_kapat_command() -> str:
    """Robotik ve Devre Simülatörü tarayıcıda AÇIKKEN, o sekmeyi kapatmayı
    dener. 'robotik simülatörü kapat', 'aracı kapat' gibi komutlarla
    tetiklenir. NOT: bazı tarayıcılar, script tarafından açılmamış
    sekmelerin kapatılmasını güvenlik nedeniyle engeller — bu durumda
    kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return ("Robotik ve Devre Simülatörü şu an açık değil gibi görünüyor — "
                "önce 'robotik simülatörünü aç' diyerek açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
