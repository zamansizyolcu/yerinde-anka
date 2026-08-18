"""
actions/bilisim_robotik_atolyesi.py — YERİNDE Bilişim ve Robotik Atölyesini
(5-6. sınıf müfredatına uygun, çevrimdışı çalışan etkileşimli ders aracı)
tarayıcıda açar VE (araç açıkken) sesle yönetir.

3B Tasarım Stüdyosu / Pico Devre Atölyesi ile AYNI köprü mimarisi
(core/bridge_server.py) paylaşılır.

Araç 8 üniteden oluşur: Giriş, Ü1 Bilgi ve Teknoloji, Ü2 Robotlar ve
Hayatımız, Ü3 Web Tasarımının Temelleri, Ü4 Çevrimiçi Ortamlar ve Ortak
Çalışma, Ü5 Dijital İçerik Üretimi, Genel Sınav, Kaynaklar. Her ünitede
çevirme kartları, eşleştirme oyunları, sıralama alıştırmaları, mini
sınavlar ve (Ü3'te) canlı önizlemeli bir HTML editörü bulunur.
"""

from __future__ import annotations

import platform
import subprocess
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

_NOT_OPEN_MSG = ("Bilişim ve Robotik Atölyesi şu an açık değil gibi görünüyor — "
                  "önce 'bilişim ve robotik atölyesini aç' diyerek açar mısın?")


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "bilisim-robotik-atolyesi" / "bilisim-robotik-atolyesi.html"


def open_bilisim_robotik_atolyesi() -> str:
    """'bilişim ve robotik atölyesini aç' / 'bilişim atölyesini aç' /
    'robotik dersini aç' / '5-6 sınıf bilişim aracını aç' — çevrimdışı
    çalışan, 5-6. sınıf müfredatına uygun etkileşimli bir bilişim ve
    robotik ders aracını tarayıcıda açar (sunucu gerekmez). İçinde bilgi/
    teknoloji, robotlar, web tasarımı, çevrimiçi ortamlar ve dijital içerik
    üzerine üniteler, çevirme kartları, eşleştirme oyunları, mini sınavlar
    ve canlı HTML editörü bulunur."""
    path = _tool_path()
    if not path.exists():
        return ("Bilişim ve Robotik Atölyesi bulunamadı — 'bilisim-robotik-atolyesi' "
                "klasörünün YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("Bilişim ve Robotik Atölyesi tarayıcıda açılıyor! Üstteki gezinme "
                "çubuğundan üniteler arasında geçebilir, çevirme kartları/"
                "eşleştirme/sıralama oyunlarıyla çalışabilir ve mini sınavları "
                "çözebilirsin. Sesli komutlarla da yönlendirebilirsin.")
    except Exception:
        try:
            webbrowser.open(url)
            return "Bilişim ve Robotik Atölyesi tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def _send_or_warn(payload: dict, basari_mesaji: str) -> str:
    if bridge_server.send_command(payload):
        return basari_mesaji
    return _NOT_OPEN_MSG


# ---------------------------------------------------------------------
# Ünite gezinme
# ---------------------------------------------------------------------

_UNITE_HARITASI = {
    "giriş": "intro", "giris": "intro", "başlangıç": "intro", "baslangic": "intro",

    "1. ünite": "u1", "birinci ünite": "u1", "1 ünite": "u1", "ünite 1": "u1",
    "bilgi": "u1", "bilgi ve teknoloji": "u1", "teknoloji": "u1",

    "2. ünite": "u2", "ikinci ünite": "u2", "2 ünite": "u2", "ünite 2": "u2",
    "robot": "u2", "robotlar": "u2", "robotlar ve hayatımız": "u2",

    "3. ünite": "u3", "üçüncü ünite": "u3", "3 ünite": "u3", "ünite 3": "u3",
    "web": "u3", "web tasarımı": "u3", "web tasarımının temelleri": "u3",

    "4. ünite": "u4", "dördüncü ünite": "u4", "4 ünite": "u4", "ünite 4": "u4",
    "çevrimiçi": "u4", "cevrimici": "u4", "çevrimiçi ortamlar": "u4",

    "5. ünite": "u5", "beşinci ünite": "u5", "5 ünite": "u5", "ünite 5": "u5",
    "içerik": "u5", "icerik": "u5", "dijital içerik": "u5",

    "sınav": "final", "sinav": "final", "final": "final", "genel sınav": "final",
    "değerlendirme": "final",

    "kaynaklar": "kaynak", "kaynak": "kaynak",
}


def bilisim_robotik_unite_gec_command(unite: str) -> str:
    """Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, gezinme çubuğundan bir
    üniteye geçer — sanki kullanıcı üstteki ünite düğmesine tıklamış gibi.
    'giriş', '1. ünite'/'bilgi ve teknoloji', '2. ünite'/'robotlar', '3.
    ünite'/'web tasarımı', '4. ünite'/'çevrimiçi ortamlar', '5. ünite'/
    'dijital içerik', 'genel sınav', 'kaynaklar' üniteleri arasından
    geçilebilir. '1. üniteye geç', 'robot ünitesini aç', 'sınava geç',
    'kaynaklara git' gibi komutlarla tetiklenir."""
    key = (unite or "").strip().lower()
    unit_id = _UNITE_HARITASI.get(key)
    if not unit_id:
        return (f"'{unite}' tanıdık bir ünite değil — giriş, 1-5. üniteler, "
                "genel sınav ya da kaynaklar diyebilirsin.")
    return _send_or_warn({"action": "go_to_unit", "unitId": unit_id}, f"{unite.capitalize()} ünitesine geçiyorum!")


# ---------------------------------------------------------------------
# Tema
# ---------------------------------------------------------------------

_TEMA_HARITASI = {"krem": "krem", "mavi": "mavi", "yeşil": "yesil", "yesil": "yesil"}


def bilisim_robotik_tema_command(tema: str) -> str:
    """Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, arayüz temasını
    değiştirir: krem, mavi ya da yeşil. 'temayı mavi yap', 'yeşil temaya
    geç' gibi komutlarla tetiklenir."""
    key = (tema or "").strip().lower()
    theme_id = _TEMA_HARITASI.get(key)
    if not theme_id:
        return f"'{tema}' tanıdık bir tema değil — krem, mavi ya da yeşil diyebilirsin."
    return _send_or_warn({"action": "set_theme", "theme": theme_id}, f"Temayı {tema} yapıyorum!")


# ---------------------------------------------------------------------
# Kapatma
# ---------------------------------------------------------------------

def bilisim_robotik_kapat_command() -> str:
    """Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, o sekmeyi kapatmayı
    dener. 'bilişim atölyesini kapat', 'aracı kapat' gibi komutlarla
    tetiklenir. NOT: bazı tarayıcılar, script tarafından açılmamış
    sekmelerin kapatılmasını güvenlik nedeniyle engeller — bu durumda
    kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")


# ---------------------------------------------------------------------
# Ünite 2 · Robotlar — labirent (blok tabanlı robot programlama)
# ---------------------------------------------------------------------

_LABIRENT_KOMUT_HARITASI = {
    "ileri": "F", "ileri git": "F", "düz git": "F", "duz git": "F",
    "sağa dön": "R", "saga don": "R", "sağa": "R", "saga": "R",
    "sola dön": "L", "sola don": "L", "sola": "L",
}


def bilisim_labirent_komut_command(komut: str, labirent: str = "1") -> str:
    """Bilişim ve Robotik Atölyesi'nin Ünite 2 (Robotlar) bölümündeki
    labirent bulmacasına bir robot komutu ekler — sanki 'İleri'/'Sağa Dön'/
    'Sola Dön' düğmesine basmış gibi. İki labirent bulmacası vardır (1 ve
    2); 'labirent' belirtilmezse ilki (1) kullanılır. 'ileri git bloğu
    ekle', 'robota sağa dön komutu ekle', '2. labirentte sola dön' gibi
    komutlarla tetiklenir."""
    key = (komut or "").strip().lower()
    kod = _LABIRENT_KOMUT_HARITASI.get(key)
    if not kod:
        return f"'{komut}' tanıdık bir robot komutu değil — ileri, sağa dön ya da sola dön diyebilirsin."
    return _send_or_warn({"action": "maze_add", "cmd": kod, "mazeNum": str(labirent)},
                         f"'{komut}' komutunu labirent robotuna ekliyorum!")


def bilisim_labirent_calistir_command(labirent: str = "1") -> str:
    """Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasındaki
    programı çalıştırır — robotun hedefe ulaşıp ulaşmadığını gösterir.
    'labirenti çalıştır', 'robotu çalıştır' gibi komutlarla tetiklenir."""
    return _send_or_warn({"action": "maze_run", "mazeNum": str(labirent)}, "Robot programını çalıştırıyorum!")


def bilisim_labirent_geri_al_command(labirent: str = "1") -> str:
    """Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasında en son
    eklenen robot komutunu geri alır. 'son komutu geri al', 'labirentte
    geri al' gibi komutlarla tetiklenir."""
    return _send_or_warn({"action": "maze_undo", "mazeNum": str(labirent)}, "Son komutu geri alıyorum!")


def bilisim_labirent_temizle_command(labirent: str = "1") -> str:
    """Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasındaki tüm
    robot programını temizler. 'programı temizle', 'labirenti temizle'
    gibi komutlarla tetiklenir."""
    return _send_or_warn({"action": "maze_clear", "mazeNum": str(labirent)}, "Programı temizliyorum!")


# ---------------------------------------------------------------------
# Kartlar / Quiz / İlerleme / Web editörü
# ---------------------------------------------------------------------

def bilisim_kart_cevir_command(kart_no: str = "") -> str:
    """Bilişim ve Robotik Atölyesi'nde, o an açık ünitedeki bir çevirme
    kartını (terim/tanım) çevirir. 'kart_no' verilirse o sıradaki kart
    (1'den başlar) çevrilir; verilmezse henüz çevrilmemiş İLK kart
    çevrilir. 'kartı çevir', '3. kartı çevir' gibi komutlarla tetiklenir."""
    payload = {"action": "flip_card"}
    if kart_no:
        payload["cardNum"] = str(kart_no)
    return _send_or_warn(payload, "Kartı çeviriyorum!")


_SECENEK_HARITASI = {"a": 0, "b": 1, "c": 2, "d": 3, "1": 0, "2": 1, "3": 2, "4": 3,
                     "birinci": 0, "ikinci": 1, "üçüncü": 2, "ucuncu": 2, "dördüncü": 3, "dorduncu": 3}


def bilisim_quiz_cevapla_command(secenek: str) -> str:
    """Bilişim ve Robotik Atölyesi'nde, o an açık ünitedeki bir mini
    sınavın İLK CEVAPLANMAMIŞ sorusunu, verilen seçenekle (A/B/C/D ya da
    1/2/3/4) cevaplar — sanki o seçeneğe tıklamış gibi. 'A seçeneğini
    işaretle', 'ikinci seçeneği seç', 'C diyorum' gibi komutlarla
    tetiklenir."""
    key = (secenek or "").strip().lower()
    idx = _SECENEK_HARITASI.get(key)
    if idx is None:
        return f"'{secenek}' tanıdık bir seçenek değil — A, B, C, D ya da 1, 2, 3, 4 diyebilirsin."
    return _send_or_warn({"action": "quiz_answer", "optionIdx": idx}, f"'{secenek.upper()}' seçeneğini işaretliyorum!")


def bilisim_ilerlemeyi_sifirla_command() -> str:
    """Bilişim ve Robotik Atölyesi'ndeki TÜM ünite ilerlemesini (tamamlanan
    üniteler, rozetler) sıfırlar — dikkatli kullanılmalı, geri alınamaz.
    'ilerlemeyi sıfırla', 'baştan başla' gibi AÇIKÇA istendiğinde
    tetiklenir."""
    return _send_or_warn({"action": "reset_progress"}, "İlerlemeni sıfırlıyorum!")


_WEB_ELEMAN_HARITASI = {
    "başlık": "h1", "baslik": "h1",
    "paragraf": "p", "metin": "p",
    "resim": "img", "resim yeri": "img", "görsel": "img", "gorsel": "img",
    "bağlantı": "a", "baglanti": "a", "link": "a",
    "liste": "ul",
}


def bilisim_web_ekle_command(eleman: str) -> str:
    """Bilişim ve Robotik Atölyesi'nin Ünite 3 (Web Tasarımı) bölümündeki
    canlı HTML editörüne bir HTML öğesi ekler — sanki '+ Başlık'/'+
    Paragraf'/'+ Resim yeri'/'+ Bağlantı'/'+ Liste' düğmesine basmış gibi.
    Sadece Ünite 3 açıkken anlamlıdır. 'başlık ekle', 'paragraf ekle',
    'resim yeri ekle', 'bağlantı ekle', 'liste ekle' gibi komutlarla
    tetiklenir."""
    key = (eleman or "").strip().lower()
    kod = _WEB_ELEMAN_HARITASI.get(key)
    if not kod:
        return f"'{eleman}' tanıdık bir HTML öğesi değil — başlık, paragraf, resim, bağlantı ya da liste diyebilirsin."
    return _send_or_warn({"action": "insert_html_snippet", "key": kod}, f"{eleman.capitalize()} ekliyorum!")
