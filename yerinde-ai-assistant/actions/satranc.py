"""
actions/satranc.py — Satranç oyununu tarayıcıda açar.

Akış şeması / çarkıfelek araçlarıyla AYNI mimari: sıfırdan yazılmış, tek
dosyalık, bağımsız HTML — dış sunucu/dosya bağımlılığı yok, file:// kısıtlaması
sorunu oluşmaz (tek sayfa, sayfa geçişi yok). Kural motoru resmi "perft" testleri
(başlangıç pozisyonundan derinlik 1-4 ve "Kiwipete" test pozisyonu) ile
doğrulanmıştır — rok, en passant, terfi, şah/mat/pat dahil.
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
    return Path(__file__).resolve().parent.parent / "satranc" / "satranc.html"


def open_satranc() -> str:
    """'satranç aç' / 'satranç oynamak istiyorum' — tek dosyalık satranç
    oyununu tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Satranç oyunu bulunamadı — 'satranc' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return "Satranç tarayıcıda açılıyor! İki kişi ya da Yerinde'ye karşı oynayabilirsin."
    except Exception:
        try:
            webbrowser.open(url)
            return "Satranç tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def satranc_kapat_command() -> str:
    """Satranç tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. 'satrancı
    kapat', 'aracı kapat' gibi komutlarla tetiklenir. NOT: bazı tarayıcılar,
    script tarafından açılmamış sekmelerin kapatılmasını güvenlik nedeniyle
    engeller — bu durumda kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return ("Satranç şu an açık değil gibi görünüyor — önce 'satranç aç' "
                "diyerek açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
