"""
actions/video_atolyesi.py — YERİNDE'nin Video Atölyesini (kırpma,
birleştirme, ses çıkarma/ekleme, sıkıştırma, biçim/oran hazır ayarları
ve ekran/kamera kaydını tek sayfada toplayan web aracı) tarayıcıda açar.

Blockly Games'teki gibi "file://" üzerinden AÇILAMAZ — tarayıcılar bazı
Web API'lerini (özellikle ekran paylaşımı/kayıt) file:// kaynağında
kısıtlar. Bu yüzden araç, blockly_games.py ile AYNI mimariyle, kendi
küçük yerel HTTP sunucusuyla (http://127.0.0.1:PORT) sunulur. Sunucu
YERİNDE ile AYNI süreçte (arka plan thread'i olarak) çalışır — aracın
kendi (bağımsız kullanım için hazırlanmış) sunucu.py + başlat/durdur
betikleri burada GEREKMEZ, YERİNDE kapanınca thread de kendiliğinden
sona erer.
"""

from __future__ import annotations

import http.server
import platform
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

_server = None
_server_port: int | None = None
_server_lock = threading.Lock()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _tool_folder() -> Path:
    return _project_root() / "video-atolyesi"


def ensure_local_server() -> int:
    """video-atolyesi/ klasörünü bir HTTP sunucusuyla sunar (file://
    kısıtlarını ortadan kaldırır). Bir kez başlar; sonraki her çağrıda
    AYNI portu döner (oturum boyunca tek sunucu)."""
    global _server, _server_port
    with _server_lock:
        if _server is not None and _server_port is not None:
            return _server_port

        folder = str(_tool_folder())

        class _QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=folder, **kwargs)

            def log_message(self, *args):
                pass  # konsolu kirletme — sessiz çalış

            def do_POST(self):
                # video-atolyesi.html, sekme kapanırken/yenilenirken
                # navigator.sendBeacon('/__shutdown__') gönderir (bağımsız
                # kullanımda sunucuyu kapatmak için). YERİNDE içinde sunucu
                # uygulamayla birlikte yaşadığından burada GERÇEKTEN
                # kapatmıyoruz — isteği sessizce 200 ile kabul ediyoruz ki
                # tarayıcı konsolunda 404 görünmesin.
                if self.path == "/__shutdown__":
                    self.send_response(200)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), _QuietHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()

        _server = httpd
        _server_port = port
        return port


def _open_url(url: str) -> bool:
    try:
        open_tool_url(url)
        return True
    except Exception:
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False


def open_video_atolyesi() -> str:
    """'video atölyesini aç' / 'video düzenleme aracını aç' / 'video montaj
    aracını aç' — video kırpma, birleştirme, ses çıkarma/ekleme, sıkıştırma
    ve ekran/kamera kaydı yapabileceğin aracı tarayıcıda açar (kendi yerel
    sunucusu YERİNDE ile birlikte otomatik başlar, ayrı kurulum gerekmez)."""
    folder = _tool_folder()
    if not (folder / "video-atolyesi.html").exists():
        return ("Video Atölyesi bulunamadı — 'video-atolyesi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    port = ensure_local_server()
    url = f"http://127.0.0.1:{port}/video-atolyesi.html"
    bridge_server.ensure_started()
    if _open_url(url):
        return "Video Atölyesi tarayıcıda açılıyor!"
    return "Video Atölyesi açılamadı — bir tarayıcı bulunamadı olabilir."


_NOT_OPEN_MSG = ("Video Atölyesi şu an açık değil gibi görünüyor — önce "
                 "'video atölyesini aç' diyerek açar mısın?")

# eylem -> kullanıcıya söylenecek Türkçe onay cümlesi.
_EYLEM_MESAJLARI = {
    "tema": "Temayı değiştiriyorum!",
    "kapat": "Kapatmayı deniyorum!",
    "kirpma_modu": "Kırpma modunu ayarlıyorum!",
    "hiz": "Hızı ayarlıyorum!",
    "donus": "Döndürmeyi ayarlıyorum!",
    "fade_giris": "Başlangıç geçişini ayarlıyorum!",
    "fade_cikis": "Bitiş geçişini ayarlıyorum!",
    "metin": "Metni ayarlıyorum!",
    "metin_konum": "Metin konumunu ayarlıyorum!",
    "kirp_ac_kapa": "Kırpma alanını açıp kapatıyorum!",
    "kirp_sifirla": "Kırpmayı sıfırlıyorum!",
    "kirp_9_16": "9:16 hikaye oranını uyguluyorum!",
    "kirp_1_1": "1:1 kare oranını uyguluyorum!",
    "kirp_16_9": "16:9 yatay oranını uyguluyorum!",
    "disa_aktar": "Videoyu dışa aktarıyorum!",
    "devam_et": "Sonuçla düzenlemeye devam ediyorum!",
    "sikistir_kalite": "Sıkıştırma kalitesini ayarlıyorum!",
    "sikistir": "Dosyayı küçültüyorum!",
    "ses_ayir": "Sesi ayırıyorum!",
    "sessiz_indir": "Sessiz kopyayı indiriyorum!",
    "ses_modu": "Ses modunu ayarlıyorum!",
    "ses_uygula": "Ses dosyasını uyguluyorum!",
    "kuyruga_ekle": "Açık videoyu birleştirme sırasına ekliyorum!",
    "birlestir": "Sırayı birleştirip dışa aktarıyorum!",
    "slayt_cozunurluk": "Çıkış çözünürlüğünü ayarlıyorum!",
    "slayt_gecis": "Geçiş efektini ayarlıyorum!",
    "slayt_olustur": "Slayt videosunu oluşturuyorum!",
    "kayit_modu": "Kayıt modunu ayarlıyorum!",
    "kayit_gecikme": "Başlama gecikmesini ayarlıyorum!",
    "kaynak_sec": "Kaynak seçim penceresini açıyorum!",
    "kaydi_baslat": "Kaydı başlatıyorum!",
    "kaydi_duraklat": "Kaydı duraklatıyorum/devam ettiriyorum!",
    "kaydi_durdur": "Kaydı durduruyorum!",
    "kayit_vazgec": "Kayıt hazırlığından vazgeçiyorum!",
    "kamera_ac_kapa": "Kamerayı açıp kapatıyorum!",
    "mikrofon_ac_kapa": "Mikrofonu açıp kapatıyorum!",
    "kaydi_donustur": "Kaydı dönüştürüyorum!",
    "duzenleyiciye_gonder": "Kaydı düzenleyiciye gönderiyorum!",
}


def video_atolyesi_ayar_command(sekme: str, eylem: str, deger: str = "") -> str:
    """Video Atölyesi tarayıcıda AÇIKKEN, içindeki bir sekmeye (Düzenleyici/
    Slayt/Kayıt) geçer VE o sekmedeki bir AYARI değiştirir ya da bir işlemi
    tetikler — sanki kullanıcı ilgili kutuyu/düğmeyi kendi tıklamış gibi.
    DİKKAT: bu, video_atolyesi_command'dan (aracı SADECE AÇAN komut) TAMAMEN
    FARKLI — burada araç zaten açık olmalı ve amaç İÇİNDEKİ bir ayarı
    değiştirmek/bir işlemi başlatmak.

    'sekme': 'editor' (Düzenleyici), 'slides' (Slayt Oluştur) ya da 'record'
    (Kayıt) — hangi sekmeye geçileceği (ve o an hangi sekmedeysen otomatik
    oraya geçilir).

    'eylem' (sekmeye göre gruplanmış):
      DÜZENLEYİCİ — kirpma_modu(deger:'keep'|'remove'), hiz(deger:'0.5'|
      '0.75'|'1'|'1.25'|'1.5'|'2'), donus(deger:'0'|'90cw'|'90ccw'|'180'),
      fade_giris(deger:'true'|'false'), fade_cikis(deger:'true'|'false'),
      metin(deger: eklenecek metin), metin_konum(deger:'top'|'middle'|
      'bottom'), kirp_ac_kapa, kirp_sifirla, kirp_9_16, kirp_1_1, kirp_16_9,
      disa_aktar, devam_et, sikistir_kalite(deger:'high'|'medium'|'low'),
      sikistir, ses_ayir, sessiz_indir, ses_modu(deger:'replace'|'mix'),
      ses_uygula, kuyruga_ekle, birlestir.
      SLAYT — slayt_cozunurluk(deger:'1280:720'|'1920:1080'|'720:1280'|
      '1080:1920'), slayt_gecis(deger:'true'|'false'), slayt_olustur.
      KAYIT — kayit_modu(deger:'screen'|'camera'|'both'|'audio'),
      kayit_gecikme(deger:'0'|'3'|'5'), kaynak_sec, kaydi_baslat,
      kaydi_duraklat, kaydi_durdur, kayit_vazgec, kamera_ac_kapa,
      mikrofon_ac_kapa, kaydi_donustur, duzenleyiciye_gonder.
      HER SEKMEDE — tema(deger:'blue'|'green'|'cream').

    NOT: dosya seçme (video/ses/görsel açma) tarayıcı güvenliği nedeniyle
    sesle YAPILAMAZ — kullanıcı dosyayı önce elle sürükleyip bırakmalı ya da
    seçmelidir; bu araç sadece o AÇIK dosya üzerindeki ayarları/işlemleri
    sesle kontrol eder."""
    payload = {"action": "video_atolyesi_ayar", "sekme": sekme, "eylem": eylem}
    if deger:
        payload["deger"] = deger
    mesaj = _EYLEM_MESAJLARI.get(eylem, "Ayarlıyorum!")
    if bridge_server.send_command(payload):
        return mesaj
    return _NOT_OPEN_MSG
