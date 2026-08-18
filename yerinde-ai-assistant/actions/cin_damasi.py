"""
actions/cin_damasi.py — Çin Daması oyununu tarayıcıda açar.

Satranç / çarkıfelek araçlarıyla AYNI mimari: sıfırdan yazılmış, tek dosyalık,
bağımsız HTML — dış sunucu/dosya bağımlılığı yok. Tahta geometrisi (121 delikli
klasik 6 köşeli yıldız — merkezde 61 hücrelik altıgen + 6 köşede 10'ar hücrelik
üçgen) küp koordinat sistemiyle üretilir ve kod testleriyle doğrulanmıştır
(hücre sayısı, 6 katlı simetri, çakışma yok, çoklu sıçrama zinciri, kazanma
kontrolü).
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
    return Path(__file__).resolve().parent.parent / "cin-damasi" / "cin-damasi.html"


def open_cin_damasi() -> str:
    """'çin daması aç' / 'çin daması oynamak istiyorum' — tek dosyalık çin
    daması oyununu tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Çin Daması oyunu bulunamadı — 'cin-damasi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return "Çin Daması tarayıcıda açılıyor! İki kişi ya da Yerinde'ye karşı oynayabilirsin."
    except Exception:
        try:
            webbrowser.open(url)
            return "Çin Daması tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def cin_damasi_kapat_command() -> str:
    """Çin Daması tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. 'çin
    damasını kapat', 'aracı kapat' gibi komutlarla tetiklenir. NOT: bazı
    tarayıcılar, script tarafından açılmamış sekmelerin kapatılmasını
    güvenlik nedeniyle engeller — bu durumda kullanıcının sekmeyi elle
    kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return ("Çin Daması şu an açık değil gibi görünüyor — önce 'çin daması aç' "
                "diyerek açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
