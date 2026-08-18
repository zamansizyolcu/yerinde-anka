"""
actions/akis_semasi.py — YERİNDE'nin KENDİ akış şeması / algoritma öğretim
aracını (akis-semasi/akis-semasi.html) tarayıcıda açar.

Blockly Games'ten FARKI: bu, BAŞKASININ kodu değil — sıfırdan YAZILDI,
tek bir bağımsız HTML dosyası (dış dosya/sunucu bağımlısı değil), bu
yüzden Blockly'de yaşanan "gizli/obfuscated iç API" ya da "file:// kök-
göreli yol" sorunlarının HİÇBİRİ burada geçerli değil — tek sayfa olduğu
için sayfa geçişi de yok, dolayısıyla Chrome'un "her file:// benzersiz
kaynaktır" kısıtlaması da burada bir sorun teşkil etmiyor.

Kapsam: Sıralama/İşlem, Karar (Evet/Hayır), Döngü, Giriş/Çıkış — hepsi
tek bir sayfada, sürükle-bırak ile kutu ekleme/bağlama, adım adım
ÇALIŞTIRMA simülasyonu (değişken paneli + ekran çıktısı) ve otomatik
Python kod üretimi (basit yapılandırılmış şemalar için).
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
    return Path(__file__).resolve().parent.parent / "akis-semasi" / "akis-semasi.html"


def open_akis_semasi() -> str:
    """'algoritma oyununu aç' / 'akış şeması aracını aç' — tek dosyalık
    aracı doğrudan tarayıcıda açar (sunucu gerekmez, tek sayfa olduğu
    için file:// kısıtlamaları da devreye girmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Akış şeması aracı bulunamadı — 'akis-semasi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return "Akış şeması ve algoritma aracı tarayıcıda açılıyor."
    except Exception:
        try:
            webbrowser.open(url)
            return "Akış şeması ve algoritma aracı tarayıcıda açılıyor."
        except Exception as e:
            return f"Açılamadı: {e}"


def akis_semasi_kapat_command() -> str:
    """Akış şeması aracı tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener.
    'akış şeması aracını kapat', 'aracı kapat' gibi komutlarla tetiklenir.
    NOT: bazı tarayıcılar, script tarafından açılmamış sekmelerin
    kapatılmasını güvenlik nedeniyle engeller — bu durumda kullanıcının
    sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return ("Akış şeması aracı şu an açık değil gibi görünüyor — önce "
                "'akış şeması aracını aç' diyerek açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
