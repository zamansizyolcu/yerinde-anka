"""
actions/donanim_atolyesi.py — YERİNDE Donanım Atölyesini tarayıcıda açar VE
(araç açıkken) sesli komutlarla canlı olarak yönetir.

Satranç / Çin Daması / 3B Tasarım Stüdyosu araçlarıyla AYNI mimari: tek
dosyalık, bağımsız HTML — dış sunucu/dosya bağımlılığı yok. Kullanıcı bir
bilgisayarın parçalarını (işlemci, RAM, ekran kartı, kablolar vb.) sürükleyip
anakart üzerindeki doğru yuvalara yerleştirerek bir PC montajını öğrenir;
"Bilgi" ve "Sınav" olmak üzere iki modu vardır.

CANLI SESLİ KONTROL: Araç açıldığında core/bridge_server.py içindeki minimal
WebSocket sunucusu da başlatılır (dış kütüphane gerekmez). Tarayıcıdaki sayfa
buna otomatik bağlanır; buradaki komut fonksiyonları bridge_server.send_command()
ile sayfaya JSON komutlar gönderir (açıklamayı 'anladım' olarak kapat, parça
ekle, parça sök). Araç açık değilse (bağlı istemci yoksa) kullanıcıya önce
aracı açması gerektiği söylenir.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from core import bridge_server
from actions.browser_launch import open_tool_url

_IS_WINDOWS = platform.system() == "Windows"

_NOT_OPEN_MSG = "Donanım Atölyesi şu an açık değil gibi görünüyor — önce 'donanım atölyesini aç' diyerek açar mısın?"


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "yerinde-donanim-atolyesi" / "yerinde-donanim-atolyesi.html"


def open_donanim_atolyesi() -> str:
    """'donanım atölyesini aç' / 'bilgisayar parçaları atölyesini aç' /
    'bilgisayar montajı aracını aç' / 'donanım eğitim aracını aç'
    — işlemci, RAM, ekran kartı, kablolar gibi bilgisayar parçalarını doğru
    yuvalarına yerleştirerek montajı öğrenebileceğin, 'Bilgi' ve 'Sınav'
    modları olan aracı tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Donanım Atölyesi bulunamadı — 'yerinde-donanim-atolyesi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("Donanım Atölyesi tarayıcıda açılıyor! Soldaki parçaları anakart "
                "üzerindeki doğru yuvalara sürükleyebilir, üstteki bilgi düğmesiyle "
                "her parça hakkında bilgi alabilir ya da sınav moduna geçebilirsin. "
                "Artık sesli komutlarla da yönlendirebilirsin.")
    except Exception:
        try:
            import webbrowser
            webbrowser.open(url)
            return "Donanım Atölyesi tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def _send_or_warn(payload: dict, basari_mesaji: str) -> str:
    if bridge_server.send_command(payload):
        return basari_mesaji
    return _NOT_OPEN_MSG


def anladim_command() -> str:
    """Donanım Atölyesi tarayıcıda AÇIKKEN, o an açık olan açıklama/yardım
    penceresini (parça bilgisi, yardım rehberi ya da tamamlama penceresi)
    kapatır — sanki kullanıcı 'Anladım' ya da 'Kapat' düğmesine kendi
    basmış gibi. 'anladım', 'tamam anladım', 'açıklamayı kapat' gibi
    komutlarla tetiklenir."""
    return _send_or_warn({"action": "acknowledge_explanation"}, "Tamam, kapatıyorum!")


def parca_ekle_command(parca: str = "") -> str:
    """Donanım Atölyesi tarayıcıda AÇIKKEN, bir bilgisayar parçasını (işlemci,
    soğutucu, RAM, ekran kartı, M.2 SSD, SATA SSD/HDD, SATA veri/güç kablosu,
    24-pin güç kablosu, CPU güç kablosu, kasa fanı, ön panel kabloları vb.)
    anakart üzerindeki doğru yuvasına yerleştirir. Parça adı belirtilmezse,
    sırada takılabilecek İLK parçayı ('İpucu' düğmesiyle aynı mantık) ekler.
    'parça ekle', 'işlemciyi ekle', 'ekran kartını tak' gibi komutlarla
    tetiklenir."""
    payload = {"action": "add_part"}
    if parca:
        payload["parca"] = parca
    mesaj = f"{parca.capitalize()} ekleniyor!" if parca else "Sıradaki parçayı ekliyorum!"
    return _send_or_warn(payload, mesaj)


def parca_sok_command(parca: str = "") -> str:
    """Donanım Atölyesi tarayıcıda AÇIKKEN, daha önce anakarta takılmış bir
    bilgisayar parçasını söker. Parça adı belirtilmezse, en son eklenen
    (takılan) parçayı söker. 'parça sök', 'RAM'i sök', 'ekran kartını çıkar'
    gibi komutlarla tetiklenir."""
    payload = {"action": "remove_part"}
    if parca:
        payload["parca"] = parca
    mesaj = f"{parca.capitalize()} sökülüyor!" if parca else "Son eklenen parçayı söküyorum!"
    return _send_or_warn(payload, mesaj)


_TEMA_HARITASI = {"mavi": "blue", "yeşil": "green", "yesil": "green", "krem": "cream"}


def tema_command(tema: str) -> str:
    """Donanım Atölyesi tarayıcıda AÇIKKEN, arayüz temasını değiştirir:
    mavi, yeşil ya da krem. 'temayı yeşil yap', 'krem temaya geç', 'mavi
    temaya geç' gibi komutlarla tetiklenir."""
    key = (tema or "").strip().lower()
    theme_id = _TEMA_HARITASI.get(key)
    if not theme_id:
        return f"'{tema}' tanıdık bir tema değil — mavi, yeşil ya da krem diyebilirsin."
    return _send_or_warn({"action": "set_theme", "theme": theme_id}, f"Temayı {tema} yapıyorum!")
