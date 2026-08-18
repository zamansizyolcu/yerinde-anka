"""
actions/carkifelek.py — Çarkıfelek Bilişim Bilgi Yarışması'nı tarayıcıda açar.

Sorular, kullanıcının kendi ders anlatım sitesinden (bilgisayarinminikelleri.biz
"Temel Kavramlar" sayfası) GERÇEK içerikten çıkarıldı — uydurulmadı. Akış
şeması aracıyla AYNI mimari: sıfırdan yazılmış, tek dosyalık, bağımsız
HTML — dış sunucu/dosya bağımlılığı yok, file:// kısıtlaması sorunu
oluşmaz (tek sayfa, sayfa geçişi yok).
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
    return Path(__file__).resolve().parent.parent / "carkifelek" / "carkifelek.html"


def open_carkifelek() -> str:
    """'çarkıfelek oyununu aç' — tek dosyalık bilişim bilgi yarışmasını
    tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Çarkıfelek oyunu bulunamadı — 'carkifelek' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return "Çarkıfelek — Bilişim Bilgi Yarışması tarayıcıda açılıyor!"
    except Exception:
        try:
            webbrowser.open(url)
            return "Çarkıfelek — Bilişim Bilgi Yarışması tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def carkifelek_kapat_command() -> str:
    """Çarkıfelek tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. 'çarkıfeleği
    kapat', 'aracı kapat' gibi komutlarla tetiklenir. NOT: bazı tarayıcılar,
    script tarafından açılmamış sekmelerin kapatılmasını güvenlik nedeniyle
    engeller — bu durumda kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return ("Çarkıfelek şu an açık değil gibi görünüyor — önce 'çarkıfelek "
                "oyununu aç' diyerek açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
