"""
actions/resim_pdf_atolyesi.py — YERİNDE'nin Resim & PDF Atölyesini
(arka plan silme/fırçalama, çerçeveleme, biçim dönüştürme — JPEG/PNG/
WEBP/ICO vb. — ve PDF oluşturma işlemlerini tek sayfada toplayan web
aracı) tarayıcıda açar.

Akış şeması / çarkıfelek atölyeleri gibi TEK bağımsız HTML dosyası —
dış dosya/sunucuya bağımlı değil, bu yüzden file:// üzerinden doğrudan
açılabilir; sayfa geçişi olmadığı için Chrome'un "her file:// benzersiz
kaynaktır" kısıtlaması burada bir sorun teşkil etmez.
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
    return Path(__file__).resolve().parent.parent / "resim-pdf-atolyesi" / "resim-pdf-atolyesi.html"


def open_resim_pdf_atolyesi() -> str:
    """'resim pdf atölyesini aç' / 'resim ve pdf aracını aç' / 'fotoğraf
    düzenleme aracını aç' / 'pdf aracını aç' — resim arka planını silme/
    fırçalama, çerçeve ekleme, biçim dönüştürme (JPEG/PNG/WEBP/ICO vb.,
    toplu dönüştürme dahil) ve PDF oluşturma işlemlerini tek sayfada
    yapabileceğin aracı tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Resim & PDF Atölyesi bulunamadı — 'resim-pdf-atolyesi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return "Resim & PDF Atölyesi tarayıcıda açılıyor!"
    except Exception:
        try:
            webbrowser.open(url)
            return "Resim & PDF Atölyesi tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


_NOT_OPEN_MSG = ("Resim & PDF Atölyesi şu an açık değil gibi görünüyor — önce "
                 "'resim pdf atölyesini aç' diyerek açar mısın?")

# Kullanıcının söylediği tema adını (Türkçe ya da İngilizce) sayfanın
# anladığı tema kimliğine çevirir — diğer atölyelerdeki (kukla_kodlama,
# pico_devre_atolyesi, bilisim_robotik_atolyesi, tasarim_studyosu) tema
# komutlarıyla aynı yaklaşım. Bu eşleme olmadan, model 'mavi'/'yeşil'/'krem'
# gibi Türkçe bir kelime gönderdiğinde sayfa bunu tanımıyor ve tema hiç
# değişmiyordu (buna rağmen onay mesajı yine de "değiştirdim" diyordu).
_TEMA_HARITASI = {
    "mavi": "blue", "blue": "blue",
    "yeşil": "green", "yesil": "green", "green": "green",
    "krem": "cream", "cream": "cream",
}

# (araç, eylem) -> kullanıcıya söylenecek Türkçe onay cümlesi.
_EYLEM_MESAJLARI = {
    ("", "tema"): "Temayı değiştiriyorum!",
    ("", "kapat"): "Kapatmayı deniyorum!",
    ("frame", "kalinlik"): "Çerçeve kalınlığını ayarlıyorum!",
    ("frame", "renk"): "Çerçeve rengini ayarlıyorum!",
    ("frame", "stil"): "Çerçeve stilini ayarlıyorum!",
    ("frame", "radius"): "Köşe yuvarlamayı ayarlıyorum!",
    ("frame", "indir"): "PNG olarak indiriyorum!",
    ("bgremove", "mod"): "Silme modunu ayarlıyorum!",
    ("bgremove", "otomatik_sil"): "Arka planı köşelerden otomatik siliyorum!",
    ("bgremove", "tolerans"): "Renk toleransını ayarlıyorum!",
    ("bgremove", "bagli_alan"): "Ayarlıyorum!",
    ("bgremove", "firca_boyutu"): "Fırça boyutunu ayarlıyorum!",
    ("bgremove", "firca_modu"): "Fırça modunu ayarlıyorum!",
    ("bgremove", "yumusat"): "Kenar yumuşatmayı ayarlıyorum!",
    ("bgremove", "geri_al"): "Geri alıyorum!",
    ("bgremove", "sifirla"): "Sıfırlıyorum!",
    ("bgremove", "indir"): "Şeffaf PNG indiriyorum!",
    ("round", "sekil"): "Şekli ayarlıyorum!",
    ("round", "radius"): "Köşe yarıçapını ayarlıyorum!",
    ("round", "renk"): "Çerçeve rengini ayarlıyorum!",
    ("round", "daire_boyutu"): "Daire boyutunu ayarlıyorum!",
    ("round", "yakinlastir"): "Yakınlaştırmayı ayarlıyorum!",
    ("round", "konum_sifirla"): "Konumu sıfırlıyorum!",
    ("round", "indir"): "PNG indiriyorum!",
    ("round", "hepsini_indir"): "Tümünü ZIP olarak indiriyorum!",
    ("format", "hedef"): "Hedef formatı ayarlıyorum!",
    ("format", "kalite"): "Kaliteyi ayarlıyorum!",
    ("format", "hepsini_indir"): "Tümünü ZIP olarak indiriyorum!",
    ("ico", "yakinlastir"): "Yakınlaştırmayı ayarlıyorum!",
    ("ico", "konum_sifirla"): "Konumu sıfırlıyorum!",
    ("ico", "boyut_ac_kapa"): "Boyutu ayarlıyorum!",
    ("ico", "indir"): "İkon olarak indiriyorum!",
    ("merge", "duzen"): "Düzeni ayarlıyorum!",
    ("merge", "sutun"): "Sütun sayısını ayarlıyorum!",
    ("merge", "hedef_boyut"): "Hedef boyutu ayarlıyorum!",
    ("merge", "bosluk"): "Boşluğu ayarlıyorum!",
    ("merge", "opaklik"): "Opaklığı ayarlıyorum!",
    ("merge", "zemin_rengi"): "Zemin rengini ayarlıyorum!",
    ("merge", "indir"): "PNG olarak indiriyorum!",
    ("video", "kare_suresi"): "Kare başına süreyi ayarlıyorum!",
    ("video", "gecis"): "Geçiş efektini ayarlıyorum!",
    ("video", "gecis_suresi"): "Geçiş süresini ayarlıyorum!",
    ("video", "cozunurluk"): "Çözünürlüğü ayarlıyorum!",
    ("video", "format"): "Video formatını ayarlıyorum!",
    ("video", "zemin_rengi"): "Zemin rengini ayarlıyorum!",
    ("video", "ses_duzeyi"): "Ses düzeyini ayarlıyorum!",
    ("video", "olustur"): "Videoyu oluşturuyorum!",
    ("video", "iptal"): "İptal ediyorum!",
    ("video", "indir"): "Videoyu indiriyorum!",
    ("ocr", "dil"): "Dili ayarlıyorum!",
    ("ocr", "calistir"): "Metni çıkarıyorum!",
    ("ocr", "kopyala"): "Panoya kopyalıyorum!",
    ("ocr", "txt_indir"): "Metin dosyası indiriyorum!",
    ("ocr", "word_indir"): "Word belgesi indiriyorum!",
    ("pdf2img", "kalite"): "Görüntü kalitesini ayarlıyorum!",
    ("pdf2img", "hepsini_indir"): "Tüm sayfaları ZIP olarak indiriyorum!",
    ("pdf2word", "indir"): "Word olarak indiriyorum!",
}


def resim_pdf_ayar_command(arac: str, eylem: str, deger: str = "") -> str:
    """Resim & PDF Atölyesi tarayıcıda AÇIKKEN, sol menüden bir ARACA (panele)
    geçer VE o araçtaki bir AYARI değiştirir ya da bir işlemi tetikler —
    sanki kullanıcı ilgili kutuyu/düğmeyi kendi tıklamış gibi. DİKKAT: bu,
    resim_pdf_command'dan (aracı SADECE AÇAN komut) TAMAMEN FARKLI — burada
    araç zaten açık olmalı ve amaç İÇİNDEKİ bir ayarı değiştirmek/bir işlemi
    başlatmak. ÖNEMLİ: dosya seçme (resim/PDF açma) tarayıcı güvenliği
    nedeniyle sesle YAPILAMAZ — kullanıcı dosyayı önce elle seçmelidir; bu
    araç sadece o AÇIK dosya üzerindeki ayarları/işlemleri kontrol eder.
    GENEL (arac gerektirmez): eylem='tema' (deger: kullanıcının söylediği
    tema adı — 'mavi'/'yeşil'/'krem', olduğu gibi ver, çevirmeye çalışma),
    eylem='kapat' (aracı kapatmayı dener).

    'arac' (sol menüdeki 10 araçtan biri): frame (Çerçeve Ekle) | bgremove
    (Arka Planı Sil) | round (Şekilli Çerçeve) | format (Format Dönüştür) |
    ico (İkon/ICO Oluştur) | merge (Resimleri Birleştir) | video (Resimden
    Video) | ocr (Resimden Yazıya) | pdf2img (PDF → Resim) | pdf2word
    (PDF → Word).

    'eylem' (araca göre gruplanmış):
      frame — kalinlik(deger:4-200), renk(deger: hex ör '#2b2118'),
      stil(deger:'solid'|'double'|'mat'), radius(deger:0-150), indir.
      bgremove — mod(deger:'wand'|'brush'), otomatik_sil (fare/dokunma
      GEREKMEZ — görselin 4 köşesinden aynı anda sihirli değnek uygular;
      DÜZ/tek renge yakın arka planlarda işe yarar, karmaşık arka planlarda
      kullanıcının fırça ile elle düzeltmesi gerekebilir — bunu açıkça
      söyle), tolerans(deger:0-100), bagli_alan(deger:'true'|'false'),
      firca_boyutu(deger:4-150), firca_modu(deger:'erase'|'restore'),
      yumusat(deger:'true'|'false'), geri_al, sifirla, indir.
      round — sekil(deger:'rounded'|'circle'|'tv'|'phone'|'computer'|
      'snowglobe'), radius(deger:0-500), renk(deger:hex), daire_boyutu
      (deger:30-100), yakinlastir(deger:1-4), konum_sifirla, indir,
      hepsini_indir.
      format — hedef(deger:'png'|'jpeg'|'webp'|'bmp'), kalite(deger:10-100),
      hepsini_indir.
      ico — yakinlastir(deger:1-4), konum_sifirla, boyut_ac_kapa(deger:
      '16'|'32'|'48'|'64'|'128'|'256' — o boyutu açar/kapatır), indir.
      merge — duzen(deger:'h'|'v'|'grid'|'overlay'), sutun(deger:1-10),
      hedef_boyut(deger:120-1400), bosluk(deger:0-80), opaklik(deger:5-100),
      zemin_rengi(deger:hex), indir.
      video — kare_suresi(deger:0.5-8), gecis(deger:'none'|'fade'|'slide'|
      'zoom'), gecis_suresi(deger:0.2-3), cozunurluk(deger:'auto'|
      '1280x720'|'1920x1080'|'1080x1080'), format(deger:'mp4'|'webm'),
      zemin_rengi(deger:hex), ses_duzeyi(deger:0-100), olustur, iptal, indir.
      ocr — dil(deger:'tur'|'eng'|'tur+eng'), calistir, kopyala, txt_indir,
      word_indir.
      pdf2img — kalite(deger:'1'|'2'|'3'), hepsini_indir.
      pdf2word — indir."""
    if eylem == "tema":
        theme_id = _TEMA_HARITASI.get((deger or "").strip().lower())
        if not theme_id:
            return f"'{deger}' tanıdık bir tema değil — mavi, yeşil ya da krem diyebilirsin."
        payload = {"action": "resim_pdf_ayar", "arac": "", "eylem": "tema", "deger": theme_id}
        if bridge_server.send_command(payload):
            return f"Temayı {deger} yapıyorum!"
        return _NOT_OPEN_MSG

    payload = {"action": "resim_pdf_ayar", "arac": arac, "eylem": eylem}
    if deger:
        payload["deger"] = deger
    mesaj = _EYLEM_MESAJLARI.get((arac, eylem), "Ayarlıyorum!")
    if bridge_server.send_command(payload):
        return mesaj
    return _NOT_OPEN_MSG
