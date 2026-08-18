"""
Türkçe niyet algılayıcı — Ollama (çevrimdışı) modu için.

Küçük yerel modeller (llama3.1 8B dahil) bazen "Blender'ı aç" gibi net bir
komuta araç çağırmak yerine sadece "açıyorum" diye cevap verip HİÇBİR ŞEY
yapmayabiliyor. Bu modül, belirgin eylem komutlarını LLM'e hiç sormadan
regex ile yakalayıp ilgili aracı DOĞRUDAN çalıştırır — böylece uygulama
açma/kapatma, kamera, fotoğraf ve video her zaman güvenilir çalışır.

Eşleşme olmazsa None döner ve konuşma normal şekilde LLM'e gider.

YANLIŞ ANLAMA FİLTRESİ: detect_intent() önce metni OLDUĞU GİBİ dener.
Sadece hiçbir kalıpla eşleşmezse core/stt_correction.py devreye girip
("sahneyi" ⇄ "saniyeyi", "kodlama" ⇄ "kotlama" gibi) bilinen STT
karışıklıklarını düzeltir ve TEKRAR dener — böylece hâlihazırda doğru
çalışan hiçbir komutun davranışı değişmez, bu tamamen ek bir güvenlik ağıdır.
"""

from __future__ import annotations

import re

from core.stt_correction import normalize_stt_text, get_last_correction  # noqa: F401 (get_last_correction dışa aktarılıyor)

# Ses komutundaki desen adını, YERİNDE Kodlama Aracı'ndaki (Blockly) dahili
# blok türü adına çevirir — bkz. core/tool_executor.py + actions/kukla_kodlama.py
_KUKLA_BLOK_MAP = {
    "kukla_blok_ileri_open": "kukla_ileri_git",
    "kukla_blok_geri_open": "kukla_geri_git",
    "kukla_blok_sagdon_open": "kukla_sag_don",
    "kukla_blok_soldon_open": "kukla_sol_don",
    "kukla_blok_zipla_open": "kukla_zipla",
    "kukla_blok_bekle_open": "kukla_bekle_saniye",
    "kukla_blok_konus_open": "kukla_konus",
    "kukla_blok_renk_open": "kukla_renk_degistir",
    "kukla_blok_boyut_open": "kukla_boyut_degistir",
    "kukla_blok_goster_gizle_open": "kukla_goster_gizle",
    "kukla_blok_durdur_open": "kukla_tumunu_durdur",
    "kukla_blok_bayrak_open": "kukla_bayrak_tiklaninca",
    "kukla_blok_sonsuz_open": "kukla_sonsuza_kadar",
    # --- Sahne'ye özgü ve ek karakter blokları (karakter_blok_ekle_command) ---
    "kukla_blok_kenara_sektir_open": "kukla_kenara_deginde_sektir",
    "kukla_blok_x_degistir_open": "kukla_x_degistir",
    "kukla_blok_z_degistir_open": "kukla_z_degistir",
    "kukla_blok_yone_bak_open": "kukla_yone_bak",
    "kukla_blok_dusun_open": "kukla_dusun",
    "kukla_blok_boyut_ayarla_open": "kukla_boyut_ayarla",
    "kukla_blok_sonraki_kostum_open": "kukla_sonraki_kostum",
    "kukla_blok_kostum_degistir_open": "kukla_kostum_degistir",
    "kukla_blok_arkaplan_degistir_open": "kukla_arkaplan_degistir",
    "kukla_blok_sonraki_arkaplan_open": "kukla_sonraki_arkaplan",
    "kukla_blok_bip_cal_open": "kukla_bip_cal",
    "kukla_blok_ses_cal_open": "kukla_ses_cal",
    "kukla_blok_zamanlayici_sifirla_open": "kukla_zamanlayici_sifirla",
    "kukla_blok_sor_bekle_open": "kukla_sor_bekle",
    "kukla_blok_tusa_basilinca_open": "kukla_tusa_basilinca",
}

# offline desen adı -> (sekme, eylem, sabit_deger). sabit_deger None ise,
# değer regex'in 1. yakalama grubundan (m.group(1)) alınır.
_VIDEO_AYAR_MAP = {
    "video_ayar_hiz": ("editor", "hiz", None),
    "video_ayar_donus_sag": ("editor", "donus", "90cw"),
    "video_ayar_donus_sol": ("editor", "donus", "90ccw"),
    "video_ayar_donus_180": ("editor", "donus", "180"),
    "video_ayar_disa_aktar": ("editor", "disa_aktar", ""),
    "video_ayar_sikistir": ("editor", "sikistir", ""),
    "video_ayar_ses_ayir": ("editor", "ses_ayir", ""),
    "video_ayar_sessiz_indir": ("editor", "sessiz_indir", ""),
    "video_ayar_kirp_9_16": ("editor", "kirp_9_16", ""),
    "video_ayar_kirp_1_1": ("editor", "kirp_1_1", ""),
    "video_ayar_kirp_16_9": ("editor", "kirp_16_9", ""),
    "video_ayar_slayt_olustur": ("slides", "slayt_olustur", ""),
    "video_ayar_kayit_baslat": ("record", "kaydi_baslat", ""),
    "video_ayar_kayit_durdur": ("record", "kaydi_durdur", ""),
    "video_ayar_kayit_duraklat": ("record", "kaydi_duraklat", ""),
    "video_ayar_kamera_ac_kapa": ("record", "kamera_ac_kapa", ""),
    "video_ayar_mikrofon_ac_kapa": ("record", "mikrofon_ac_kapa", ""),
}

# offline desen adı -> (arac, eylem, sabit_deger).
_RESIM_AYAR_MAP = {
    "resim_ayar_git_frame": ("frame", "", ""),
    "resim_ayar_git_bgremove": ("bgremove", "", ""),
    "resim_ayar_git_round": ("round", "", ""),
    "resim_ayar_git_format": ("format", "", ""),
    "resim_ayar_git_ico": ("ico", "", ""),
    "resim_ayar_git_merge": ("merge", "", ""),
    "resim_ayar_git_video": ("video", "", ""),
    "resim_ayar_git_ocr": ("ocr", "", ""),
    "resim_ayar_git_pdf2img": ("pdf2img", "", ""),
    "resim_ayar_git_pdf2word": ("pdf2word", "", ""),
    "resim_ayar_ocr_calistir": ("ocr", "calistir", ""),
    "resim_ayar_ocr_kopyala": ("ocr", "kopyala", ""),
    "resim_ayar_bg_sifirla": ("bgremove", "sifirla", ""),
    "resim_ayar_bg_otomatik_sil": ("bgremove", "otomatik_sil", ""),
}

# Uygulama adı olarak yakalanabilecek ifade: harf/rakam/boşluk (Türkçe dahil)
_APP = r"([a-zA-ZçğıöşüÇĞİÖŞÜ0-9][a-zA-ZçğıöşüÇĞİÖŞÜ0-9 \.\+]{0,40}?)"

# Türkçe hal ekleri ('yi, 'ı, 'u vb.) — uygulama adından ayıklanır
_SUFFIX = r"(?:'?[yn]?[iıuü])?"

_OPEN_VERBS = r"(?:aç|başlat|çalıştır|getir|acar mısın|açar mısın|başlatır mısın|başlatabilir misin|açabilir misin)"
_CLOSE_VERBS = r"(?:kapat|kapa|sonlandır|durdur|kapatır mısın|kapatabilir misin)"

_CAMERA_WORDS = r"(?:kamera|webcam|web kamera)"

# Bahçe (IP/DVRIP) kamerası — 'camera_open/close' ve Video Atölyesi'nin
# 'kamera aç' jokerlerine düşmemesi için bu kalıplar _PATTERNS'te O KALIPLARDAN
# ÖNCE gelir (bkz. 371. satır).
_GARDEN_WORDS = (r"(?:bahçe\s*kameran?[ıi]?|bahçe\s*cam[ıi]?|"
                 r"güvenlik\s*kameras?[ıi]?|yoosee'?\s*y?\s*[ıi]?)")

# Türkçe yön → GardenCamStreamer.ptz() beklentisi (UI PTZ barıyla aynı anahtarlar)
_GARDEN_PTZ_MAP = {
    "sağa": "right", "sola": "left", "yukarı": "up", "aşağı": "down",
    "yukarı sağa": "up_right", "yukarı sola": "up_left",
    "aşağı sağa": "down_right", "aşağı sola": "down_left",
}


_PATTERNS = [
    # ── Haftalık / çok günlü hava durumu ────────────────────────────────────
    ("forecast",
     re.compile(r"(?:(\d)\s*günlük\s*hava|haftalık\s*hava|hava\s*durumu\s*tahmini|"
                r"hafta\s*sonu\s*hava|önümüzdeki\s+günler(?:de)?\s+hava)", re.IGNORECASE)),

    # ── WhatsApp arama ──────────────────────────────────────────────────────
    ("wa_cal_video", re.compile(r"(?:whatsapp\s+)?görüntülü\s+arama\s+düğmesini\s+öğret", re.IGNORECASE)),
    ("wa_cal_voice", re.compile(r"(?:whatsapp\s+)?(?:sesli\s+)?arama\s+düğmesini\s+öğret", re.IGNORECASE)),
    ("wa_video",
     re.compile(r"([\wçğıöşü]{2,25}(?:\s[\wçğıöşü]{2,25})?)\s*(?:ile|'?l[ae])?\s+"
                r"görüntülü\s*(?:ara|arama yap|konuş|görüşelim)", re.IGNORECASE)),
    ("wa_voice",
     re.compile(r"(.{2,30}?)(?:'?[iıuü])?\s*(?:whatsapp'?tan|whatsapptan)?\s*ara(?:r mısın)?$", re.IGNORECASE)),

    # ── Film/dizi servisleri ────────────────────────────────────────────────
    ("stream",
     re.compile(r"\b(disney\s*\+?(?:\s*plus)?|netflix|prime(?:\s*video)?|youtube|"
                r"exxen|blu\s*tv|gain|tod|mubi)(?:'?[a-zçğıöşü]{1,5})?\s+"
                r"(.{0,60}?)\s*(?:aç|oynat|başlat|izle|bul)\b", re.IGNORECASE)),

    # ── YERİNDE Kodlama Aracı — sesle KODLAMA BLOĞU ekleme ──────────────────
    # NOT: "5 adım git" gibi doğrudan çalıştırma komutlarıyla (hemen altındaki
    # Scratch sc_move vb. kalıplarıyla) KARIŞMASIN diye BİLEREK cümlenin
    # sonuna "blok/bloğu ekle" eklenmesini ŞART koştuk. "ileri git" tek
    # başına Scratch'e, "ileri git bloğunu ekle" bu araca gider. BU YÜZDEN
    # bu blok, aşağıdaki Scratch desenlerinden ÖNCE gelmek ZORUNDA — regex
    # arama (search) tam eşleşme değil, alt-dize eşleşmesi yaptığından
    # (ör. "sağa dön" ifadesi "sağa dön bloğunu ekle" içinde de geçer),
    # _PATTERNS listesinde önce gelen HER ZAMAN kazanır.
    ("kukla_blok_ileri_open",
     re.compile(r"(?:(\d{1,4})\s*)?(?:adım\s*)?ileri\s*git\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_geri_open",
     re.compile(r"(?:(\d{1,4})\s*)?(?:adım\s*)?geri\s*git\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_sagdon_open",
     re.compile(r"(?:(\d{1,4})\s*derece\s*)?sağa\s*dön\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_soldon_open",
     re.compile(r"(?:(\d{1,4})\s*derece\s*)?sola\s*dön\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_zipla_open",
     re.compile(r"zıpla\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_sor_bekle_open",
     re.compile(r"sor\w*\s*(?:ve\s*)?bekle\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_bekle_open",
     re.compile(r"(?:(\d{1,4})\s*saniye\s*)?bekle\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_konus_open",
     re.compile(r"konuş\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_renk_open",
     re.compile(r"renk\s*değiştir\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_boyut_open",
     re.compile(r"boyut\s*değiştir\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_goster_gizle_open",
     re.compile(r"(?:görün[üu]rl[üu]ğ\w*\s*değiştir\w*|göster\s*gizle\w*)\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_durdur_open",
     re.compile(r"tümünü\s*durdur\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_bayrak_open",
     re.compile(r"bayrağa\s*tıklan\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_sonsuz_open",
     re.compile(r"sonsuza\s*kadar\s*tekrarla\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_kenara_sektir_open",
     re.compile(r"kenara\s*değ\w*\s*sektir\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_x_degistir_open",
     re.compile(r"(?:(-?\d{1,4})\s*)?x\s*konumunu\s*değiştir\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_z_degistir_open",
     re.compile(r"(?:(-?\d{1,4})\s*)?z\s*konumunu\s*değiştir\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_yone_bak_open",
     re.compile(r"(?:(\d{1,3})\s*derece\s*)?yöne\s*bak\w*\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_dusun_open",
     re.compile(r"düşün\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_boyut_ayarla_open",
     re.compile(r"(?:(\d{1,4})\s*)?boyut\w*\s*ayarla\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_sonraki_kostum_open",
     re.compile(r"sonraki\s*kostüm\w*\s*(?:geç\w*\s*)?blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_kostum_degistir_open",
     re.compile(r"(?:(\d{1,3})\s*(?:numaralı\s*)?)?kostüm\w*\s*(?:değiştir\w*|geç\w*)\s*blo[kğ]\w*\s*ekle",
                re.IGNORECASE)),
    ("kukla_blok_arkaplan_degistir_open",
     re.compile(r"arkaplan\w*\s*değiştir\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_sonraki_arkaplan_open",
     re.compile(r"sonraki\s*arkaplan\w*\s*(?:geç\w*\s*)?blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_bip_cal_open",
     re.compile(r"bip\s*(?:sesi\s*)?çal\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_ses_cal_open",
     re.compile(r"nota\w*\s*çal\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_zamanlayici_sifirla_open",
     re.compile(r"zamanlayıcı\w*\s*sıfırla\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("kukla_blok_tusa_basilinca_open",
     re.compile(r"tuşa\s*bas\w*\s*blo[kğ]\w*\s*ekle", re.IGNORECASE)),
    ("karakter_blok_sil_open",
     re.compile(r"(?:son\s*(?:eklenen\s*)?|seçili\s*|bu\s*)?blo[kğ]\w*\s*sil", re.IGNORECASE)),

    # ── Scratch ─────────────────────────────────────────────────────────────
    ("sc_move",  re.compile(r"(?:scratch'?te\s+)?(\d{1,4})\s*adım\s*(?:git|ilerle|yürü)", re.IGNORECASE)),
    ("sc_right", re.compile(r"(\d{1,3})\s*derece\s*sağa\s*dön", re.IGNORECASE)),
    ("sc_left",  re.compile(r"(\d{1,3})\s*derece\s*sola\s*dön", re.IGNORECASE)),
    ("sc_say",   re.compile(r"scratch'?te\s+(.{1,60}?)\s*(?:de|söyle)$", re.IGNORECASE)),
    ("sc_wait",  re.compile(r"(\d{1,3})\s*saniye\s*bekle", re.IGNORECASE)),
    ("sc_size",  re.compile(r"boyutu\s*(?:yüzde\s*)?(\d{1,3})\s*yap", re.IGNORECASE)),
    ("sc_repeat", re.compile(r"(\d{1,4})\s*kere\s*tekrarla", re.IGNORECASE)),
    ("sc_forever", re.compile(r"sonsuza\s*kadar\s*tekrarla", re.IGNORECASE)),
    ("sc_if_edge", re.compile(r"eğer\s*kenara\s*değerse", re.IGNORECASE)),
    ("sc_if_key", re.compile(r"eğer\s*(\w+)\s*tuşuna\s*basılırsa", re.IGNORECASE)),
    ("sc_block_end", re.compile(r"blok\s*bitti|bloğu\s*kapat", re.IGNORECASE)),
    ("sc_show", re.compile(r"scratch'?te\s*göster|kediyi\s*göster", re.IGNORECASE)),
    ("sc_hide", re.compile(r"scratch'?te\s*gizle|kediyi\s*gizle", re.IGNORECASE)),
    ("sc_pen_down", re.compile(r"kalemi\s*indir", re.IGNORECASE)),
    ("sc_pen_up", re.compile(r"kalemi\s*kaldır", re.IGNORECASE)),
    ("sc_pen_clear", re.compile(r"kalemi\s*temizle|çizimi\s*temizle", re.IGNORECASE)),
    ("sc_pen_color", re.compile(r"kalem\s*rengini?\s*(\w+)\s*yap", re.IGNORECASE)),
    ("sc_reopen", re.compile(r"scratch'?[iı]?\s*yeniden\s*aç", re.IGNORECASE)),
    ("sc_load", re.compile(r"bilgisayar[ıi]mdan\s*yükle|kaydedilen\s*(?:scratch\s*)?dosyay[ıi]\s*(?:aç|yükle)|scratch\s*dosyas[ıi]n[ıi]\s*yükle", re.IGNORECASE)),
    ("sc_close", re.compile(r"scratch'?[iı]?\s*kapat", re.IGNORECASE)),
    ("sc_calibrate_gf", re.compile(r"(?:scratch\s*)?yeşil\s*bayra[ğk]\w*\s*öğret", re.IGNORECASE)),
    ("sc_run_gf", re.compile(r"scratch'?[iı]?\s*çalıştır|yeşil\s*bayra[ğk]\w*\s*(?:tıkla|bas)", re.IGNORECASE)),
    ("sc_add_sprite", re.compile(r"kukla\s*ekle(?:\s+(.+))?$|(.+?)\s*kuklas[ıi]n?[ıi]?\s*ekle", re.IGNORECASE)),
    ("sc_del_sprite", re.compile(r"kukla(?:y[ıi])?\s*sil(?:\s+(.+))?$|(.+?)\s*kuklas[ıi]n?[ıi]?\s*sil", re.IGNORECASE)),
    ("sc_switch_sprite", re.compile(r"(.+?)\s*kuklasına\s*geç|kuklalar\s*arasında\s*(.+?)'?[ye]\s*geç", re.IGNORECASE)),
    ("sc_draw_sprite", re.compile(r"kukla\s*çiz(?:\s*[:\-]?\s*(.+))?$", re.IGNORECASE)),
    ("sc_add_costume", re.compile(r"kostüm\s*ekle(?:\s*[:\-]?\s*(.+))?$", re.IGNORECASE)),
    ("sc_add_comment", re.compile(r"yorum\s*(?:satırı\s*)?ekle\s*[:\-]?\s*(.+)$", re.IGNORECASE)),
    ("sc_analyze", re.compile(r"(?:sb3(?:\s*dosyasını)?|scratch\s*dosyasını|kod\s*bloklarını)\s*(?:analiz\s*et|incele|kontrol\s*et|düzelt)(?:\s+(.+))?$", re.IGNORECASE)),

    # ── Blockly Games (Labirent vb.) ─────────────────────────────────────────
    ("bg_open", re.compile(r"(labirent|kuş|kus|gölet|golet|kaplumbağa|kaplumbaga|bulmaca|film|müzik|muzik|blockly\s*games?)(?:\s*oyununu)?\s*aç", re.IGNORECASE)),
    ("akis_open", re.compile(r"(?:algoritma|akış\s*şeması|akis\s*semasi)\s*(?:oyununu|aracını|aracini)?\s*aç", re.IGNORECASE)),
    ("carkifelek_open", re.compile(r"çark[ıi]?\s*felek\w*\s*(?:oyununu)?\s*aç", re.IGNORECASE)),
    ("satranc_open", re.compile(r"satran[çc]\w*\s*(?:oyununu)?\s*(?:aç|oyna\w*)", re.IGNORECASE)),
    ("cin_damasi_open", re.compile(r"[çc]in\s*damas[ıi]\w*\s*(?:oyununu)?\s*(?:aç|oyna\w*)", re.IGNORECASE)),
    ("robotik_simulator_open",
     re.compile(r"(?:robot(?:ik)?|devre|elektronik|mikrodenetleyici)\w*\s+(?:ve\s+devre\s+)?(?:simülat\w*|simulat\w*|simülasyon\w*)\w*\s*(?:aç|açar mısın|başlat)", re.IGNORECASE)),
    ("tasarim_studyosu_open",
     re.compile(
         r"(?:(?:3\s*b(?:oyutlu)?|3d|stl)\w*\s*(?:tasarım|nesne)\w*\s*(?:stüdyo\w*|aracı\w*)?\s*(?:aç|açar mısın|başlat))"
         r"|(?:nesne\s*tasarla\w*\s*(?:aracı\w*)?\s*(?:aç|açar mısın|başlat))"
         r"|(?:tasarım\s*stüdyo\w*\s*(?:aç|açar mısın|başlat))",
         re.IGNORECASE)),
    ("robot_tasarim_open",
     re.compile(
         r"(?:robot\w*\s*(?:tasarım|tasarim|tasarla\w*)\w*\s*(?:atölye\w*|atolye\w*|arac\w*|araç\w*)?"
         r"|3\s*b(?:oyutlu)?\s*robot\w*\s*(?:tasarım|tasarim|tasarla\w*)\w*"
         r"|robot\w*\s*(?:yapma|kurma)\w*\s*arac\w*)\s*(?:aç|açar mısın|başlat)",
         re.IGNORECASE)),
    ("donanim_open",
     re.compile(
         r"(?:donan[ıi]m\w*\s*(?:atölye\w*|atolye\w*|e[ğg]itim\w*\s*arac\w*|arac\w*)?"
         r"|bilgisayar\s*parça\w*\s*atölye\w*"
         r"|bilgisayar\s*montaj\w*\s*arac\w*)"
         r"\s*(?:aç|açar mısın|başlat)",
         re.IGNORECASE)),
    # NOT: 'pencereyi kapat' burada BİLEREK kullanılmıyor — o ifade zaten
    # k_alt_f4 (aktif pencereyi kapat) tarafından claim edilmiş durumda;
    # onunla çakışmasın diye daha spesifik ifadeler kullanıyoruz.
    ("donanim_skip_explain",
     re.compile(r"açıklamay[ıi]\s*(?:kapat|geç)|(?:bilgi|yardım)\s*penceresini\s*kapat", re.IGNORECASE)),
    ("donanim_tema",
     re.compile(r"atölye\s*temas[ıi]n[ıi]\s*(mavi|ye[şs]il|krem)\s*yap|(mavi|ye[şs]il|krem)\s*atölye\s*temas[ıi]na\s*ge[çc]", re.IGNORECASE)),
    # ── YERİNDE'nin GENEL arayüz teması + konuşma animasyonu (atölye_tema'dan
    #    FARKLI — o yukarıda 'atölye temasını...' gerektiriyor, bu gerektirmez) ──
    ("app_tema",
     re.compile(r"(?<!atölye )(?<!atölyesi )tema\w{0,4}\s*(a[çc][ıi]k|krem|mavi|ye[şs]il|mor|turuncu|k[ıi]rm[ıi]z[ıi]|karanl[ıi]k|sade)\s*(?:yap|çevir)"
               r"|(a[çc][ıi]k|krem|mavi|ye[şs]il|mor|turuncu|k[ıi]rm[ıi]z[ıi]|karanl[ıi]k|sade)\s*temaya\s*ge[çc]"
               r"|(?<!atölye )(?<!atölyesi )tema\w{0,4}\s*sadele[şs]tir", re.IGNORECASE)),
    # ── YERİNDE ana pencere arkaplanı (atölye araçlarının mavi/yeşil/krem
    #    temasıyla KARIŞTIRILMASIN — bu farklı, ana pencerenin kendi resmi) ──
    ("arkaplan_acik",
     re.compile(r"arkaplan\w*\s*(?:aç[ıi]k|ayd[ıi]nl[ıi]k)\w*\s*(?:yap|ol\w*|geç)?", re.IGNORECASE)),
    ("arkaplan_koyu",
     re.compile(r"arkaplan\w*\s*(?:koyu|karanl[ıi]k)\w*\s*(?:yap|ol\w*|geç)?", re.IGNORECASE)),
    ("arkaplan_sade",
     re.compile(r"arkaplan\w*\s*(?:sade\w*|normal\w*|kald[ıi]r\w*|temizle\w*)", re.IGNORECASE)),
    ("resim_pdf_open",
     re.compile(
         r"resim\s*(?:ve\s*|[-/]\s*)?pdf\w*\s*(?:atölye\w*|atolye\w*|arac\w*|araç\w*)?\s*(?:aç|açar mısın|başlat)"
         r"|fotoğraf\w*\s*düzenle\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)"
         r"|foto\s*düzenle\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)"
         r"|pdf\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)",
         re.IGNORECASE)),
    ("resim_ayar_git_frame",
     re.compile(r"çerçeve\s*ekle\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_bgremove",
     re.compile(r"arka\s*plan\w*\s*sil\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_round",
     re.compile(r"şekilli\s*çerçeve\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_format",
     re.compile(r"format\w*\s*dönüştür\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_ico",
     re.compile(r"(?:ikon|ico)\w*\s*oluştur\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_merge",
     re.compile(r"resimleri\s*birleştir\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_video",
     re.compile(r"resim\w*\s*(?:den|dan)?\s*video\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_ocr",
     re.compile(r"(?:resimden\s*yazıya|ocr)\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_pdf2img",
     re.compile(r"pdf\w*\s*(?:'yi|yi|'ı|ı)?\s*resme\s*çevir\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_git_pdf2word",
     re.compile(r"pdf\w*\s*(?:'yi|yi|'ı|ı)?\s*word\w*\s*(?:'e|e|'a|a)?\s*çevir\w*\s*(?:aracına|panel\w*)?\s*geç", re.IGNORECASE)),
    ("resim_ayar_ocr_calistir",
     re.compile(r"metni\s*çıkar", re.IGNORECASE)),
    ("resim_ayar_ocr_kopyala",
     re.compile(r"panoya\s*kopyala", re.IGNORECASE)),
    ("resim_ayar_bg_sifirla",
     re.compile(r"arka\s*plan\w*\s*sıfırla", re.IGNORECASE)),
    ("resim_ayar_bg_otomatik_sil",
     re.compile(r"arka\s*plan\w*\s*(?:otomatik\s*)?sil", re.IGNORECASE)),
    ("video_atolyesi_open",
     re.compile(
         r"video\s*(?:atölye\w*|atolye\w*)\s*(?:aç|açar mısın|başlat)"
         r"|video\s*(?:düzenleme|duzenleme|montaj)\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)"
         r"|video\s*(?:kırpma|kirpma|birleştirme|birlestirme)\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)",
         re.IGNORECASE)),
    ("video_ayar_hiz",
     re.compile(r"hız[ıi]?\s*(\d+(?:[.,]\d+)?)\s*(?:x|kat)?\s*yap", re.IGNORECASE)),
    ("video_ayar_donus_sag",
     re.compile(r"video\w*\s*(?:\d{1,3}\s*derece\s*)?sağa\s*döndür", re.IGNORECASE)),
    ("video_ayar_donus_sol",
     re.compile(r"video\w*\s*(?:\d{1,3}\s*derece\s*)?sola\s*döndür", re.IGNORECASE)),
    ("video_ayar_donus_180",
     re.compile(r"video\w*\s*180\s*derece\s*döndür", re.IGNORECASE)),
    ("video_ayar_disa_aktar",
     re.compile(r"video\w*\s*dışa\s*aktar", re.IGNORECASE)),
    ("video_ayar_sikistir",
     re.compile(r"(?:video\w*\s*sıkıştır|dosyay[ıi]\s*küçült)", re.IGNORECASE)),
    ("video_ayar_ses_ayir",
     re.compile(r"ses\w*\s*(?:ayır|çıkar)", re.IGNORECASE)),
    ("video_ayar_sessiz_indir",
     re.compile(r"sessiz\s*(?:olarak\s*)?indir", re.IGNORECASE)),
    ("video_ayar_kirp_9_16",
     re.compile(r"(?:9\s*[:/]\s*16|hikaye\s*oranı\w*)\s*(?:'\w+\s*)?kırp", re.IGNORECASE)),
    ("video_ayar_kirp_1_1",
     re.compile(r"(?:1\s*[:/]\s*1|kare\s*oranı\w*|kare\s*şeklinde)\s*(?:'\w+\s*)?kırp", re.IGNORECASE)),
    ("video_ayar_kirp_16_9",
     re.compile(r"(?:16\s*[:/]\s*9|yatay\s*oranı\w*)\s*(?:'\w+\s*)?kırp", re.IGNORECASE)),
    ("video_ayar_slayt_olustur",
     re.compile(r"slayt\s*(?:videosu\w*\s*)?oluştur", re.IGNORECASE)),
    ("video_ayar_kayit_baslat",
     re.compile(r"kayd\w*\s*başlat", re.IGNORECASE)),
    ("video_ayar_kayit_durdur",
     re.compile(r"kayd\w*\s*durdur", re.IGNORECASE)),
    ("video_ayar_kayit_duraklat",
     re.compile(r"kayd\w*\s*duraklat", re.IGNORECASE)),
    # ── Bahçe kamerası (Yoosee/DVRIP) — 'kamera aç' jokerinden ÖNCE ─────────
    # "bahçe kamerasını aç" diyen, Video Atölyesi'nin 'kamera\w*\s*aç' kalıbına
    # ve aşağıdaki camera_open/close jokerine de uyar; bu blok ONA devirmeden
    # önce yakalar.
    ("garden_open",
     re.compile(rf"\b{_GARDEN_WORDS}\w*\s+(?:aç|başlat|açar\s*mısın|açabilir\s*misin)"
                rf"|(?:aç|başlat)\s+{_GARDEN_WORDS}", re.IGNORECASE)),
    ("garden_close",
     re.compile(rf"\b{_GARDEN_WORDS}\w*\s+(?:kapat|durdur|kapatır\s*mısın|kapatabilir\s*misin)"
                rf"|(?:kapat|durdur)\s+{_GARDEN_WORDS}", re.IGNORECASE)),
    ("garden_wake",
     re.compile(rf"\b{_GARDEN_WORDS}\w*\s*(?:uyandır|uyandırır\s*mısın|uyandırabilir\s*misin|uyansın)"
                rf"|(?:uyandır)\s+{_GARDEN_WORDS}", re.IGNORECASE)),
    ("garden_ptz",
     re.compile(rf"\b(?:{_GARDEN_WORDS}\w*|kamerayı|kamerayi|onu|şunu)\s*"
                r"(yukarı\s+sağa|yukarı\s+sola|aşağı\s+sağa|aşağı\s+sola|yukarı|aşağı|sağa|sola)\s*"
                r"(?:doğru\s*)?(?:çevir|döndür|kaldır|indir|çevirir\s*misin|çevirebilir\s*misin|döndürür\s*müsün)",
                re.IGNORECASE)),
    ("video_ayar_kamera_ac_kapa",
     # NOT: burada sadece 'aç' yakalanır — 'kapat/sonlandır/durdur' bilerek
     # dahil edilmedi. Aksi halde bu (Video Atölyesi'nin ayar paneline özgü)
     # eski/dar kalıp, aşağıdaki genel 'camera_close' kalıbından ÖNCE devreye
     # girip 'kamera kapat' gibi genel komutları yanlış eyleme yönlendiriyordu
     # (kamera gerçekten kapanmıyordu). Artık 'kamera kapat/sonlandır/durdur'
     # HER ZAMAN aşağıdaki camera_close kalıbına düşer ve kamerayı düzgünce
     # sonlandırır — 'kamera sonlandır' ile birebir aynı sonucu verir.
     re.compile(r"kamera\w*\s*aç", re.IGNORECASE)),
    ("video_ayar_mikrofon_ac_kapa",
     re.compile(r"mikrofon\w*\s*(?:aç|kapat)", re.IGNORECASE)),
    ("kukla_kodlama_open",
     re.compile(
         r"kukla\s*kodlama\w*\s*(?:atölye\w*|atolye\w*|arac\w*|araç\w*)?\s*(?:aç|açar mısın|başlat)"
         r"|yerinde\s*kodlama\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)"
         r"|blok\s*kodlama\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)"
         r"|3\s*b(?:oyutlu)?\s*(?:kukla|karakter)\w*\s*(?:kodlama|programlama)\w*\s*(?:atölye\w*|atolye\w*|arac\w*|araç\w*)?\s*(?:aç|açar mısın|başlat)"
         # Sadece "kodlama aracını aç" (ön ek olmadan) — uyandırma kelimesi
         # ("yerinde") zaten ayrı bir motor tarafından tüketildiği için
         # kullanıcı genelde komutu bu kısa haliyle söylüyor.
         r"|kodlama\w*\s*arac\w*\s*(?:aç|açar mısın|başlat)",
         re.IGNORECASE)),
    # ── YERİNDE Kodlama Aracı canlı kontrol (araç açıkken) ───────────────────
    # NOT: Bu araç, GERÇEK (2B) Scratch'i sesle kontrol eden ayrı sistemden
    # (scratch_command / "kukla ekle" vb.) TAMAMEN FARKLIDIR. Çakışmayı
    # önlemek için burada BİLEREK "kukla" değil "karakter"/"program" kelimeleri
    # kullanılıyor — tool_defs.py'deki Gemini tanımlarıyla birebir aynı sözcük
    # seçimi. Böylece "kukla ekle" demeye devam edenler GERÇEK Scratch'e gider,
    # "karakter oluştur" diyenler bu araca gider — hiçbir çakışma yok.
    ("kukla_calistir_open",
     re.compile(r"(?:program\w*|karakter\w*(?:leri|ler)?)\s*(?:çalıştır|başlat)\w*",
                re.IGNORECASE)),
    ("kukla_durdur_open",
     re.compile(r"(?:program\w*|karakter\w*(?:leri|ler)?)\s*durdur\w*",
                re.IGNORECASE)),
    ("kukla_ekle_open",
     re.compile(r"(?:yeni\s*)?(?:3\s*b(?:oyutlu)?\s*)?karakter\w*\s*(?:oluştur|olustur|ekle)",
                re.IGNORECASE)),
    ("kukla_sec_open",
     re.compile(r"(son|ilk)\s*karakter\w*\s*seç", re.IGNORECASE)),
    ("kukla_mod_degistir_open",
     re.compile(r"(blok|python)\s*modu\w*\s*geç", re.IGNORECASE)),
    ("kukla_kaydet_open",
     re.compile(r"karakter\s*proje\w*\s*(?:çalışmalarıma\s*)?kaydet"
                r"|proje\w*\s*çalışmalarıma\s*kaydet", re.IGNORECASE)),
    ("kukla_ac_open",
     re.compile(r"(?:son\s*kaydettiğim\s*)?karakter\s*proje\w*\s*aç", re.IGNORECASE)),
    # ── 3B Tasarım Stüdyosu canlı kontrol (araç açıkken) ─────────────────────
    # NOT: 'sil', 'büyüt/küçült', 'döndür', 'renk' gibi genel fiiller kasıtlı
    # olarak burada YOK — bunlar Blender/diğer araçlarla çakışabilecek kadar
    # genel oldukları için sadece LLM'in (tool_defs.py açıklamalarıyla,
    # konuşma bağlamına bakarak) yönlendirmesine bırakılıyor. Burada sadece
    # başka hiçbir araçla karışma riski taşımayan, kendine özgü ifadeler var.
    ("tasarim_ekle_sekil_open",
     re.compile(r"(küp|silindir|küre|kure|koni|piramit|simit)\w*\s*(?:ekle|ekler misin|oluştur|olustur)", re.IGNORECASE)),
    ("tasarim_delik_yap_open",
     re.compile(r"(?:bunu|onu|nesneyi|seçili\w*)\s*delik\s*yap", re.IGNORECASE)),
    ("tasarim_kati_yap_open",
     re.compile(r"(?:bunu|onu|nesneyi|seçili\w*)\s*kat[ıi]\s*yap", re.IGNORECASE)),
    ("tasarim_delikleri_uygula_open",
     re.compile(r"delikleri\s*(?:uygula|kes)", re.IGNORECASE)),
    ("tasarim_stl_indir_open",
     re.compile(r"(?:stl'?\w*|tasarım\w*|tasarim\w*)\s*indir", re.IGNORECASE)),
    ("tasarim_temizle_open",
     re.compile(r"tasar[ıi]m\w*\s*(?:sahnesini|stüdyosunu)?\s*temizle", re.IGNORECASE)),
    ("obs_kayit_baslat", re.compile(r"(?:ekran\s*)?(?:kay[ıi]t|kayd)\w*\s*(?:başlat|baslat)\w*", re.IGNORECASE)),
    ("obs_kayit_duraklat", re.compile(r"(?:ekran\s*)?(?:kay[ıi]t|kayd)\w*\s*duraklat\w*", re.IGNORECASE)),
    ("obs_kayit_devam", re.compile(r"(?:ekran\s*)?(?:kay[ıi]t|kayd)\w*\s*devam\s*et\w*", re.IGNORECASE)),
    ("obs_kayit_bitir", re.compile(r"(?:ekran\s*)?(?:kay[ıi]t|kayd)\w*\s*(?:bitir|sonlandır|durdur)\w*", re.IGNORECASE)),
    ("egitim_export", re.compile(r"eğitim\s*veri\w*\s*(?:dosyasını)?\s*(?:dışa\s*aktar|oluştur|çıkar)", re.IGNORECASE)),
    ("egitim_stats", re.compile(r"(?:ne\s*kadar\s*)?eğitim\s*veri\w*\s*(?:durumu|birikti|ne\s*durumda)", re.IGNORECASE)),
    ("bg_solve", re.compile(r"labirent\w*\s*(\d+)\s*\.?\s*seviye\w*\s*(?:(alternatif|ikinci)\s*)?çöz\b(?!üm)", re.IGNORECASE)),
    ("bg_describe", re.compile(r"labirent\w*\s*(\d+)\s*\.?\s*seviye\w*(?:nin|sinin)?\s*(?:(alternatif|ikinci)\s*)?çözüm\w*\s*(?:söyle|anlat|oku)", re.IGNORECASE)),
    ("sc_clear", re.compile(r"scratch'?[iı]?\s*(?:temizle|sıfırla)", re.IGNORECASE)),

    # ── Piper eğitim seti ────────────────────────────────────────────────────
    ("pd_status",  re.compile(r"eğitim\s*set(?:i|inin)?\s*(?:durumu|kaç\s*kaldı|nerede)", re.IGNORECASE)),
    ("pd_package", re.compile(r"eğitim\s*set(?:i|ini)?\s*paketle", re.IGNORECASE)),
    ("pd_reset",   re.compile(r"eğitim\s*set(?:i|ini)?\s*sıfırla", re.IGNORECASE)),
    ("pd_redo",    re.compile(r"(\d{1,2})\.?\s*cümleyi\s*(?:tekrar\s*)?(?:kaydet|sıfırla)", re.IGNORECASE)),
    ("pd_record",  re.compile(r"eğitim\s*(?:için|seti için)?\s*ses\s*kaydet|piper\s*(?:için\s*)?eğitim\s*seti\s*kaydet", re.IGNORECASE)),

    # ── Mikrofon testi ──────────────────────────────────────────────────────
    ("mic_test", re.compile(r"mikrofonu?\s*(?:test et|dene|kontrol et)|beni\s+duyuyor\s+musun|ses(?:imi)?\s+alıyor\s+musun", re.IGNORECASE)),

    # ── Nesne algılama (YOLO) aç/kapa ───────────────────────────────────────
    ("yolo_off", re.compile(r"(?:nesne\s*(?:algılama|tanıma)|yolo|analiz)\w*\s*(?:yı|yi|ı|i)?\s*(?:kapat|durdur|pasif)", re.IGNORECASE)),
    ("yolo_on",  re.compile(r"(?:nesne\s*(?:algılama|tanıma)|yolo|analiz)\w*\s*(?:yı|yi|ı|i)?\s*(?:aç|başlat|aktif)", re.IGNORECASE)),

    # ── Kamera ──────────────────────────────────────────────────────────────
    ("camera_open",
     re.compile(rf"\b{_CAMERA_WORDS}\w*\s+(?:{_OPEN_VERBS})|(?:{_OPEN_VERBS})\s+{_CAMERA_WORDS}", re.IGNORECASE)),
    ("camera_close",
     re.compile(rf"\b{_CAMERA_WORDS}\w*\s+(?:{_CLOSE_VERBS})|(?:{_CLOSE_VERBS})\s+{_CAMERA_WORDS}", re.IGNORECASE)),

    # ── Fotoğraf / video ────────────────────────────────────────────────────
    ("take_photo",
     re.compile(r"\b(?:fotoğraf|foto|resim)\s*(?:çek|al|çeker misin|alır mısın)", re.IGNORECASE)),
    ("record_video",
     re.compile(r"(?:(\d{1,3})\s*saniye\w*\s*)?video\w*\s*(?:kaydet|çek|kayıt|başlat|al)", re.IGNORECASE)),

    # ── Asistanı kapatma (close_app'ten ÖNCE — 'kendini kapat' app değildir) ─
    ("shutdown",
     re.compile(r"\b(?:kendini|sistemi|yerinde)\s+kapat|görüşürüz kapan|kapan artık", re.IGNORECASE)),

    # ── Sistem sesi ──────────────────────────────────────────────────────────
    ("volume_down",
     re.compile(r"\bses(?:i|ini)?\s*(?:biraz\s*)?(?:kıs|azalt|düşür)", re.IGNORECASE)),
    ("volume_up",
     re.compile(r"\bses(?:i|ini)?\s*(?:biraz\s*)?(?:yükselt|art[tı]ır|aç)\b|sesi sonuna kadar aç", re.IGNORECASE)),
    ("volume_mute",
     re.compile(r"\bses(?:i|ini)?\s*(?:kapat|sustur)|sessize al", re.IGNORECASE)),

    # ── Medya kontrol (çalanı durdur/oynat/atla) ────────────────────────────
    ("media_next",
     re.compile(r"\bsonraki\s+(?:şarkı|parça|müzik)", re.IGNORECASE)),
    ("media_prev",
     re.compile(r"\bönceki\s+(?:şarkı|parça|müzik)", re.IGNORECASE)),
    ("media_playpause",
     re.compile(r"\b(?:şarkıyı|müziği|parçayı|videoyu)\s+(?:durdur|duraklat|başlat|oynat|devam ettir)|müziğe devam", re.IGNORECASE)),

    # ── Şarkı ÇALMA (YouTube/Spotify) ───────────────────────────────────────
    ("play_media",
     re.compile(r"(?:spotify|youtube)\w*['’]?\w*\s+(?:dan|den|tan|ten)?\s*(.{2,60}?)\s+(?:çal|oynat|aç)\b"
                r"|\b(.{2,60}?)\s+(?:şarkısını|parçasını|müziğini)\s+(?:çal|oynat|aç)", re.IGNORECASE)),

    # ── Sunuma/belgeye resim ekle (internetten indirme dahil) ───────────────
    ("img_insert",
     re.compile(r"(?:internetten\s+)?(.{2,40}?)\s*(?:resmi|resmini|fotoğrafı|fotografını|görselini|görseli)\s*"
                r"(?:indir(?:ip)?\s*)?(?:ve\s+)?(?:sunuma|belgeye|slayta|word'?e)?\s*(?:ekle|koy|yerleştir)", re.IGNORECASE)),
    ("img_insert2",
     re.compile(r"(?:sunuma|belgeye|slayta)\s+(?:internetten\s+)?(.{2,40}?)\s+(?:resmi|resmini|görseli|görselini|fotoğrafı|fotoğrafını)\s*(?:ekle|koy)", re.IGNORECASE)),

    # ── Sunum gösterisi ─────────────────────────────────────────────────────
    ("show_start", re.compile(r"sunum(?:u)?\s+(?:başlat|göster|oynat|tam\s*ekran\s*yap)|slayt\s+gösterisi(?:ni)?\s+başlat", re.IGNORECASE)),
    ("show_end",   re.compile(r"sunum(?:u)?\s+(?:bitir|kapat|durdur|sonlandır|çık)|"
                              r"slayt\s+gösterisini\s+(?:bitir|kapat|sonlandır)|sunumdan\s+çık", re.IGNORECASE)),
    ("show_next",  re.compile(r"sonraki\s+(?:slayt|sayfa|slayda geç)|slayd?[ıi]\s+ilerlet|ileri\s+geç", re.IGNORECASE)),
    ("show_prev",  re.compile(r"önceki\s+(?:slayt|sayfa)|slayd?[ıi]\s+geri", re.IGNORECASE)),
    ("show_first", re.compile(r"(?:ilk\s+slayda|başa)\s+dön", re.IGNORECASE)),
    ("show_black", re.compile(r"ekranı\s+karart", re.IGNORECASE)),

    # ── Slayt sil / geri al ─────────────────────────────────────────────────
    ("slide_del",  re.compile(r"(?:bu\s+)?(?:slaydı|slaytı|sayfayı)\s+sil", re.IGNORECASE)),
    ("slide_undo", re.compile(r"geri\s+al|sildiğimi?\s+geri\s+getir|geri\s+getir", re.IGNORECASE)),

    # ── Excel: grafik + aralık seçme ────────────────────────────────────────
    ("xl_chart",
     re.compile(r"(?:(sütun|çizgi|pasta|alan|çubuk)\s+)?grafi(?:k|ği)\s*(?:oluştur|çiz|yap|ekle)", re.IGNORECASE)),
    ("xl_range",
     re.compile(r"([a-zA-Z]{1,3}\s?\d{1,5})\s*(?:'den|den|dan|'dan)?\s*([a-zA-Z]{1,3}\s?\d{1,5})\s*(?:'ye|ye|'a|a|kadar)?\s*(?:kadar\s*)?seç", re.IGNORECASE)),

    # ── Hizalama ────────────────────────────────────────────────────────────
    ("al_left",   re.compile(r"(?:metni|yazıyı|sayfayı|paragrafı)?\s*sola\s+(?:daya|hizala|yasla)", re.IGNORECASE)),
    ("al_center", re.compile(r"(?:metni|yazıyı|sayfayı|paragrafı)?\s*(?:ortala|orta(?:ya)?\s+(?:daya|hizala|al))", re.IGNORECASE)),
    ("al_right",  re.compile(r"(?:metni|yazıyı|sayfayı|paragrafı)?\s*sağa\s+(?:daya|hizala|yasla)", re.IGNORECASE)),
    ("al_just",   re.compile(r"iki\s+yana\s+(?:yasla|hizala)", re.IGNORECASE)),

    # ── Animasyon / geçiş ───────────────────────────────────────────────────
    ("fx_clear",   re.compile(r"(?:animasyonları|geçişleri|efektleri)\s+(?:temizle|kaldır|sil)", re.IGNORECASE)),
    ("fx_trans",   re.compile(r"(?:(\w+)\s+)?geçiş(?:i|ler)?\s*(?:efekti)?\s*(?:ekle|uygula|koy)", re.IGNORECASE)),
    ("fx_anim",    re.compile(r"(?:(\w+)\s+)?animasyon(?:u|lar)?\s*(?:ekle|uygula|koy)", re.IGNORECASE)),

    # ── Konu araştır & yaz ──────────────────────────────────────────────────
    ("topic_write",
     re.compile(r"(?:sunuma|belgeye|word'?e|powerpoint'?e)\s+(.{3,50}?)\s*(?:konusunu|konusu|hakkında|ile ilgili)?\s*(?:yaz|ekle|araştır(?:ıp)?\s*(?:yaz|ekle))", re.IGNORECASE)),
    ("topic_write2",
     re.compile(r"(.{3,50}?)\s+(?:konusunu|hakkında bilgi)\s+(?:sunuma|belgeye|word'?e)\s*(?:yaz|ekle)", re.IGNORECASE)),

    # ── Resim ayarlama (döndür/büyüt/hizala) ────────────────────────────────
    ("img_rot_left",  re.compile(r"(?:resmi|görseli|fotoğrafı)\s+sola\s+(?:döndür|çevir)", re.IGNORECASE)),
    ("img_rot_right", re.compile(r"(?:resmi|görseli|fotoğrafı)\s+(?:sağa\s+)?(?:döndür|çevir)", re.IGNORECASE)),
    ("img_flip_h",    re.compile(r"(?:resmi|görseli|fotoğrafı)\s+(?:yatay\s+)?aynala|(?:resmi|görseli)\s+ters\s+çevir", re.IGNORECASE)),
    ("img_flip_v",    re.compile(r"(?:resmi|görseli|fotoğrafı)\s+dikey\s+aynala", re.IGNORECASE)),
    ("img_bigger",    re.compile(r"(?:resmi|görseli|fotoğrafı)\s+büyüt", re.IGNORECASE)),
    ("img_smaller",   re.compile(r"(?:resmi|görseli|fotoğrafı)\s+küçült", re.IGNORECASE)),
    ("img_center",    re.compile(r"(?:resmi|görseli|fotoğrafı)\s+ortala", re.IGNORECASE)),
    ("img_left",      re.compile(r"(?:resmi|görseli|fotoğrafı)\s+sola\s+(?:hizala|yasla|al)", re.IGNORECASE)),
    ("img_right",     re.compile(r"(?:resmi|görseli|fotoğrafı)\s+sağa\s+(?:hizala|yasla|al)", re.IGNORECASE)),
    ("img_reset",     re.compile(r"(?:resmi|görseli|fotoğrafı)\s+(?:düzelt|sıfırla)", re.IGNORECASE)),

    # ── Word → PDF ──────────────────────────────────────────────────────────
    ("word_pdf",
     re.compile(r"pdf\s*(?:olarak|hâlinde|halinde|'?[a-zçğıöşü]{1,3})?\s*(?:kaydet|çevir|dönüştür|aktar)", re.IGNORECASE)),

    # ── Excel ───────────────────────────────────────────────────────────────
    ("xl_score",
     re.compile(r"(?:otomatik\s+)?puan\s+tablosu\s*(?:oluştur|kur|hazırla|yap)?|not\s+tablosu\s*(?:oluştur|kur|yap)", re.IGNORECASE)),
    ("xl_avg",
     re.compile(r"ortalama(?:sını)?\s*(?:al|hesapla|bul)", re.IGNORECASE)),
    ("xl_sum",
     re.compile(r"^(?:bunları|şunları|sayıları)?\s*(?:topla|toplamını al|toplamı hesapla)$", re.IGNORECASE)),

    # ── Office biçimlendirme ────────────────────────────────────────────────
    ("fmt_font_color",
     re.compile(r"yaz[ıi](?:n[ıi]n)?\s+reng[ıi]n?[ıi]?\s+(\w+)\s+(?:yap|olsun)", re.IGNORECASE)),
    ("fmt_page_color",
     re.compile(r"(?:sayfa(?:n[ıi]n)?|arka\s*plan(?:[ıi]n)?)\s*reng[ıi]n?[ıi]?\s+(\w+)\s+(?:yap|olsun)", re.IGNORECASE)),
    ("fmt_page_color_any",
     re.compile(r"(?:sayfa(?:n[ıi]n)?|arka\s*plan(?:[ıi]n)?)\s*reng[ıi]n?[ıi]?\s+(?:değiştir|güncelle)", re.IGNORECASE)),
    ("fmt_font_size",
     re.compile(r"yaz[ıi](?:\s*boyutunu|\s*büyüklüğünü|\s*puntosunu)\s+(\d{1,3})\s+yap", re.IGNORECASE)),
    ("fmt_new_page",
     re.compile(r"^yeni\s+(?:sayfa|slayt)(?:\s+(?:ekle|aç|oluştur))?$", re.IGNORECASE)),
    ("fmt_design",
     re.compile(r"(?:slayt(?:a)?|sunum(?:a)?)?\s*(?:rastgele\s+)?tasarım(?:ı)?\s+(?:seç|uygula|değiştir)$", re.IGNORECASE)),
    ("fmt_grow", re.compile(r"yaz[ıi]y[ıi]\s+büyüt", re.IGNORECASE)),
    ("fmt_shrink", re.compile(r"yaz[ıi]y[ıi]\s+küçült", re.IGNORECASE)),

    # ── FreeCAD tasarımını kaydet (blender_save'DEN ÖNCE — 'tasarım' kelimesi
    #    blender_save'e de uyduğu için sıra önemli) ────────────────────────
    ("freecad_save",
     re.compile(r"free\s*cad'?\w{0,4}\s+(?:sahnesini|dosyasını|projesini|tasarımını)?\s*kaydet", re.IGNORECASE)),

    # ── Blender tasarımını kaydet (save_doc'tan ÖNCE) ───────────────────────
    ("blender_save",
     re.compile(r"(?:blender|tasarım|3d)\w*\s+(?:sahnesini|dosyasını|projesini|tasarımını)?\s*kaydet", re.IGNORECASE)),

    # ── Klavye tuşları ──────────────────────────────────────────────────────
    ("k_esc",       re.compile(r"\b(?:esc|escape|kaçış)\s*(?:tuşuna\s*)?(?:bas|tuşu)?\b", re.IGNORECASE)),
    ("k_alt_f4",    re.compile(r"\balt\s*\+?\s*f\s*4\b|pencereyi\s+kapat", re.IGNORECASE)),
    ("k_alt_tab",   re.compile(r"\balt\s*\+?\s*tab\b|pencere\s+değiştir", re.IGNORECASE)),
    ("k_win_tab",   re.compile(r"\b(?:windows|win|süper)\s*\+?\s*tab\b", re.IGNORECASE)),
    ("k_ctrl_shift_tab",
     re.compile(r"\b(?:ctrl|kontrol)\s*\+?\s*shift\s*\+?\s*tab\b|önceki\s+sekme(?:ye)?\s*(?:geç|git)?|"
                r"bir\s+önceki\s+sekme", re.IGNORECASE)),
    ("k_ctrl_tab",
     re.compile(r"\b(?:ctrl|kontrol)\s*\+?\s*tab\b|sekmeler?\s+aras[ıi]nda\s+geç|"
                r"sonraki\s+sekme(?:ye)?\s*(?:geç|git)?|sekme\s+değiştir|bir\s+sonraki\s+sekme",
                re.IGNORECASE)),
    ("k_enter",     re.compile(r"\benter\s*(?:tuşuna\s*)?(?:bas)?\b|\bgiriş tuşu\b", re.IGNORECASE)),
    ("k_delete",    re.compile(r"\bdelete\b|\bsil\s*tuşu|\btuşla\s*sil\b", re.IGNORECASE)),
    ("k_backspace", re.compile(r"\bbackspace\b|geri\s*sil", re.IGNORECASE)),
    ("k_tab",       re.compile(r"^(?:tab|sekme)(?:\s*tuşu(?:na)?)?(?:\s*bas)?$", re.IGNORECASE)),
    ("k_up",        re.compile(r"\byukarı\s*ok\b|ok\s*tuşu\s*yukarı", re.IGNORECASE)),
    ("k_down",      re.compile(r"\başağı\s*ok\b|ok\s*tuşu\s*aşağı", re.IGNORECASE)),
    ("k_left",      re.compile(r"\bsol\s*ok\b", re.IGNORECASE)),
    ("k_right",     re.compile(r"\bsağ\s*ok\b", re.IGNORECASE)),
    ("k_copy",      re.compile(r"^kopyala$", re.IGNORECASE)),
    ("k_paste",     re.compile(r"^yapıştır$", re.IGNORECASE)),
    ("k_undo",      re.compile(r"^geri\s*al$", re.IGNORECASE)),
    ("k_select_all",    re.compile(r"^(?:tümünü|hepsini)\s*seç$", re.IGNORECASE)),
    ("k_win_d",     re.compile(r"masaüstü(?:nü)?\s*göster|windows\s*\+?\s*d\b|win\s*\+?\s*d\b", re.IGNORECASE)),
    ("k_win",       re.compile(r"\bbaşlat(?:'?[ae])?\s+t[ıi]kla\w*\b"
                                r"|\bbaşlat\s*men[uü]\w*\b"
                                r"|\bbaşlat\s*(?:düğmesi|dugmesi|butonu)\w*\b"
                                r"|\b(?:windows|win|süper|super)\s*tuşuna\s*bas\w*\b"
                                r"|\bstart\s*men[uü]\w*\b", re.IGNORECASE)),
    ("k_f11",       re.compile(r"\bf\s*11\b|tam\s*ekrandan\s*çık|^tam\s*ekran\s*yap$", re.IGNORECASE)),
    ("k_f2",        re.compile(r"yeniden\s*adlandır|f\s*2\b(?!\d)", re.IGNORECASE)),
    ("k_cut",       re.compile(r"^kes$", re.IGNORECASE)),
    ("k_redo",      re.compile(r"^ileri\s*al$", re.IGNORECASE)),
    ("k_capslock",  re.compile(r"^büyük\s*yap$|büyük\s*harf(?:\s*kilidi)?|caps\s*lock", re.IGNORECASE)),
    ("k_parent_folder", re.compile(r"üst\s*klasöre?\s*git|bir\s*üst\s*klasör|üst\s*dizine?\s*git", re.IGNORECASE)),

    # ── Fare kontrolü ───────────────────────────────────────────────────────
    ("m_right", re.compile(r"\bsağ(?:a)?\s+t[ıi]kla", re.IGNORECASE)),
    ("m_double", re.compile(r"\bçift\s+t[ıi]kla", re.IGNORECASE)),
    ("m_left", re.compile(r"^(?:sol(?:a)?\s+)?t[ıi]kla$", re.IGNORECASE)),
    ("m_sdown", re.compile(r"\başağı(?:ya)?\s+kayd[ıi]r|fare\s*teker(?:i|ini|leğini)?\s*aşağı|teker(?:i|leği)?\s*aşağı\s*çevir", re.IGNORECASE)),
    ("m_sup", re.compile(r"\byukarı(?:ya)?\s+kayd[ıi]r|fare\s*teker(?:i|ini|leğini)?\s*yukarı|teker(?:i|leği)?\s*yukarı\s*çevir", re.IGNORECASE)),
    ("m_center", re.compile(r"(?:fareyi|imleci)\s+ortala", re.IGNORECASE)),
    ("m_move", re.compile(r"(?:fareyi|imleci)\s+(sağa|sola|yukarı|aşağı)", re.IGNORECASE)),

    # ── Ses örneği kaydı ────────────────────────────────────────────────────
    ("rec_voice",
     re.compile(r"sesimi\s+kaydet|kendi\s+sesimi\s+(?:kaydet|ekle)|ses\s+örneğimi\s+al", re.IGNORECASE)),

    # ── Son açılan uygulamayı kapat ("kapat" tek başına) ────────────────────
    ("close_last",
     re.compile(r"^(?:onu |bunu )?kapat$", re.IGNORECASE)),

    # ── Genel "uygulamayı kapat" (spesifik uygulama adı YOK) — close_app'in
    #   _APP joker kalıbı bunu "uygulamayı" diye SAÇMA bir isim sanıp
    #   anlamsız bir kapatma denemesi yapmasın diye ÖNCE burada yakalanır.
    ("close_generic",
     re.compile(r"^(?:şu\s+an\s*ki\s+|şu\s+anki\s+|aç[ıi]k\s+)?(?:uygulamay[ıi]|programı)\s+kapat$", re.IGNORECASE)),

    # ── Blender sahne komutları (çizimden ÖNCE) ─────────────────────────────
    ("bl_clear",  re.compile(r"sahneyi\s+(?:temizle|boşalt|sil)|her\s*şeyi\s+sil|tümünü\s+sil", re.IGNORECASE)),
    ("bl_cube",   re.compile(r"küp(?:ü|u)?\s+(?:sil|kaldır)", re.IGNORECASE)),
    ("bl_delsel", re.compile(r"seçili(?:yi|leri)?\s+sil|bunu\s+sil", re.IGNORECASE)),
    ("bl_selall", re.compile(r"blender'?d[ae]\s+(?:hepsini|tümünü)\s+seç|sahnedeki\s+her\s*şeyi\s+seç", re.IGNORECASE)),

    # ── FreeCAD'de çizim/modelleme (blender_draw'dan ÖNCE — çakışmasın) ──────
    ("freecad_draw",
     re.compile(r"^free\s*cad'?\w{0,4}\s+(.{2,60}?)\s+(?:çiz|çizer misin|modelle|modeller misin|tasarla|tasarlar mısın|3d(?:\s*olarak)?\s*(?:yap|oluştur))\s*$", re.IGNORECASE)),

    # ── Blender'da çizim/modelleme ──────────────────────────────────────────
    ("blender_draw",
     re.compile(r"^(?:blender'?d[ae]\s+)?(?!resim|fotoğraf|foto)(.{2,60}?)\s+(?:çiz|çizer misin|modelle|modeller misin|3d(?:\s*olarak)?\s*(?:yap|oluştur))\s*$", re.IGNORECASE)),

    # ── Dosyayı kaydet ──────────────────────────────────────────────────────
    ("save_doc",
     re.compile(r"^(?:dosyayı|belgeyi|bunu)?\s*kaydet(?:er misin)?\s*$", re.IGNORECASE)),

    # ── Sesle yazma (aktif pencereye klavyeden yazar) ───────────────────────
    ("type_text",
     re.compile(r"^(?:şunu|bunu)?\s*yaz(?:ar mısın)?\s*[:,]?\s+(.{2,500})$", re.IGNORECASE)),

    # ── Uygulama kapat (önce kapat — 'aç' kalıbıyla çakışmasın) ─────────────
    ("close_app",
     re.compile(rf"\b{_APP}{_SUFFIX}\s+(?:{_CLOSE_VERBS})\b", re.IGNORECASE)),

    # ── Uygulama aç ─────────────────────────────────────────────────────────
    ("open_app",
     re.compile(rf"\b{_APP}{_SUFFIX}\s+(?:{_OPEN_VERBS})\b", re.IGNORECASE)),
]

# Bu kelimeler uygulama adı DEĞİLDİR — yanlış pozitif önleme
_NOT_APPS = {
    "kamera", "kamerayı", "webcam", "video", "videoyu", "fotoğraf", "foto",
    "resim", "müzik", "müziği", "müziğ", "şarkı", "şarkıyı", "şarkıy", "sesi", "ses",
    "konuşma", "konuşmayı", "beni", "bunu", "şunu", "onu", "sen", "bana",
    "hava", "saat", "takvim", "takvimi", "anımsatıcı", "hatırlatıcı",
    "kendini", "programı", "sistemi", "yerinde", "dosyayı", "belgeyi",
    "yeni sayfa", "yeni slayt", "sayfa", "sayfayı", "slayt", "slaytı", "tasarımı",
}


def _match_patterns(t: str):
    """
    Verilen (zaten normalize edilmiş/edilmemiş) metni _PATTERNS listesine
    karşı dener. detect_intent() bunu ÖNCE orijinal metinle, sonra (gerekirse)
    STT-düzeltmesi uygulanmış metinle iki kez çağırır.
    """
    for name, pattern in _PATTERNS:
        m = pattern.search(t)
        if not m:
            continue

        if name == "forecast":
            days = 7
            if m.group(1):
                try:
                    days = max(1, min(int(m.group(1)), 7))
                except ValueError:
                    pass
            return ("get_forecast", {"days": days})
        if name in ("wa_cal_voice", "wa_cal_video"):
            return ("calibrate_whatsapp",
                    {"kind": "video" if name.endswith("video") else "voice"})
        if name in ("wa_voice", "wa_video"):
            kisi = (m.group(1) or "").strip(" ,.'\"")
            kisi = re.sub(r"^(?:whatsapp'?tan|whatsapptan|hemen|lütfen)\s+", "", kisi,
                          flags=re.IGNORECASE).strip()
            # "babamla" → "babam", "ayşe ile" → "ayşe"
            kisi = re.sub(r"\s+ile$", "", kisi, flags=re.IGNORECASE).strip()
            kisi = re.sub(r"['’]?l[ae]$", "", kisi, flags=re.IGNORECASE).strip()
            if len(kisi) < 2 or kisi.lower() in ("beni", "onu", "şunu", "bunu"):
                continue
            return ("whatsapp_call", {"contact": kisi,
                                      "kind": "video" if name == "wa_video" else "voice"})
        if name == "stream":
            svc_raw = (m.group(1) or "").lower().replace(" ", "").replace("+", "")
            svc = {"disney": "disney", "disneyplus": "disney", "netflix": "netflix",
                   "prime": "prime", "primevideo": "prime", "youtube": "youtube",
                   "exxen": "exxen", "blutv": "blutv", "gain": "gain",
                   "tod": "tod", "mubi": "mubi"}.get(svc_raw)
            if not svc:
                continue
            q = (m.group(2) or "").strip(" ,.'\"")
            q = re.sub(r"^(?:tan|ten|dan|den|da|de)\s+", "", q, flags=re.I).strip()
            return ("play_stream", {"service": svc, "query": q})
        if name == "bg_open":
            game = m.group(1)
            return ("blockly_command", {"key": game})
        if name == "akis_open":
            return ("akis_command", {})
        if name == "carkifelek_open":
            return ("carkifelek_command", {})
        if name == "satranc_open":
            return ("satranc_command", {})
        if name == "cin_damasi_open":
            return ("cin_damasi_command", {})
        if name == "robotik_simulator_open":
            return ("robotik_simulator_command", {})
        if name == "tasarim_studyosu_open":
            return ("tasarim_studyosu_command", {})
        if name == "robot_tasarim_open":
            return ("robot_tasarim_command", {})
        if name == "donanim_open":
            return ("donanim_atolyesi_command", {})
        if name == "donanim_skip_explain":
            return ("donanim_anladim_command", {})
        if name == "donanim_tema":
            renk = m.group(1) or m.group(2)
            return ("donanim_tema_command", {"tema": renk})
        if name == "app_tema":
            kelime = m.group(1) or m.group(2) or "sade"  # 'temayı sadeleştir' hiçbir grup yakalamaz
            return ("tema_command", {"mod": kelime})
        if name == "arkaplan_acik":
            return ("arkaplan_command", {"mod": "acik"})
        if name == "arkaplan_koyu":
            return ("arkaplan_command", {"mod": "koyu"})
        if name == "arkaplan_sade":
            return ("arkaplan_command", {"mod": "sade"})
        if name == "resim_pdf_open":
            return ("resim_pdf_command", {})
        if name in _RESIM_AYAR_MAP:
            arac, eylem, deger = _RESIM_AYAR_MAP[name]
            return ("resim_pdf_ayar_command", {"arac": arac, "eylem": eylem, "deger": deger})
        if name == "video_atolyesi_open":
            return ("video_atolyesi_command", {})
        if name in _VIDEO_AYAR_MAP:
            sekme, eylem, sabit_deger = _VIDEO_AYAR_MAP[name]
            if sabit_deger is not None:
                deger = sabit_deger
            else:
                try:
                    deger = (m.group(1) or "").replace(",", ".").strip()
                except IndexError:
                    deger = ""
            return ("video_atolyesi_ayar_command", {"sekme": sekme, "eylem": eylem, "deger": deger})
        if name == "kukla_kodlama_open":
            return ("kukla_kodlama_command", {})
        if name == "kukla_calistir_open":
            return ("kukla_calistir_command", {})
        if name == "kukla_durdur_open":
            return ("kukla_durdur_command", {})
        if name == "kukla_ekle_open":
            return ("kukla_ekle_command", {"isim": ""})
        if name == "kukla_sec_open":
            return ("kukla_sec_command", {"tanim": (m.group(1) or "").strip()})
        if name == "kukla_mod_degistir_open":
            return ("kukla_mod_degistir_command", {"mod": (m.group(1) or "").strip()})
        if name == "kukla_kaydet_open":
            return ("kukla_kaydet_command", {})
        if name == "kukla_ac_open":
            return ("kukla_ac_command", {"dosya_adi": ""})
        if name in _KUKLA_BLOK_MAP:
            try:
                deger = (m.group(1) or "").strip()
            except IndexError:
                deger = ""
            return ("karakter_blok_ekle_command", {"blok": _KUKLA_BLOK_MAP[name], "deger": deger})
        if name == "karakter_blok_sil_open":
            return ("karakter_blok_sil_command", {})
        if name == "tasarim_ekle_sekil_open":
            return ("tasarim_ekle_sekil_command", {"sekil": (m.group(1) or "").strip()})
        if name == "tasarim_delik_yap_open":
            return ("tasarim_delik_yap_command", {})
        if name == "tasarim_kati_yap_open":
            return ("tasarim_kati_yap_command", {})
        if name == "tasarim_delikleri_uygula_open":
            return ("tasarim_delikleri_uygula_command", {})
        if name == "tasarim_stl_indir_open":
            return ("tasarim_stl_indir_command", {})
        if name == "tasarim_temizle_open":
            return ("tasarim_temizle_command", {})
        if name == "obs_kayit_baslat":
            return ("obs_kayit_baslat_command", {})
        if name == "obs_kayit_duraklat":
            return ("obs_kayit_duraklat_command", {})
        if name == "obs_kayit_devam":
            return ("obs_kayit_devam_command", {})
        if name == "obs_kayit_bitir":
            return ("obs_kayit_bitir_command", {})
        if name == "egitim_export":
            return ("egitim_verisi_command", {"action": "export"})
        if name == "egitim_stats":
            return ("egitim_verisi_command", {"action": "stats"})
        if name == "bg_solve":
            level = m.group(1)
            use_alt = bool(m.group(2))
            return ("blockly_solve", {"level": level, "alt": "1" if use_alt else ""})
        if name == "bg_describe":
            level = m.group(1)
            use_alt = bool(m.group(2))
            return ("blockly_describe", {"level": level, "alt": "1" if use_alt else ""})

        if name.startswith("sc_"):
            if name == "sc_clear":
                return ("scratch_command", {"action": "clear", "value": "", "text": ""})
            if name == "sc_reopen":
                return ("scratch_command", {"action": "reopen", "value": "", "text": ""})
            if name == "sc_load":
                return ("scratch_command", {"action": "load", "value": "", "text": ""})
            if name == "sc_close":
                return ("scratch_command", {"action": "close", "value": "", "text": ""})
            if name == "sc_calibrate_gf":
                return ("scratch_command", {"action": "calibrate_green_flag", "value": "", "text": ""})
            if name == "sc_run_gf":
                return ("scratch_command", {"action": "run_green_flag", "value": "", "text": ""})
            if name == "sc_add_sprite":
                return ("scratch_command", {"action": "add_sprite", "key": (m.group(1) or m.group(2) or "").strip()})
            if name == "sc_del_sprite":
                return ("scratch_command", {"action": "delete_sprite", "key": (m.group(1) or m.group(2) or "").strip()})
            if name == "sc_switch_sprite":
                target = (m.group(1) or m.group(2) or "").strip()
                return ("scratch_command", {"action": "switch_sprite", "key": target})
            if name == "sc_draw_sprite":
                return ("scratch_command", {"action": "draw_sprite", "value": (m.group(1) or "").strip()})
            if name == "sc_add_costume":
                return ("scratch_command", {"action": "add_costume", "value": (m.group(1) or "").strip()})
            if name == "sc_add_comment":
                return ("scratch_command", {"action": "add_comment", "text": m.group(1).strip()})
            if name == "sc_analyze":
                return ("scratch_command", {"action": "analyze", "value": (m.group(1) or "").strip()})
            if name == "sc_say":
                return ("scratch_command", {"action": "say", "value": "",
                                            "text": m.group(1).strip()})
            if name == "sc_repeat":
                return ("scratch_command", {"action": "repeat_start", "times": m.group(1)})
            if name == "sc_forever":
                return ("scratch_command", {"action": "forever_start"})
            if name == "sc_if_edge":
                return ("scratch_command", {"action": "if_touching_edge_start"})
            if name == "sc_if_key":
                return ("scratch_command", {"action": "if_key_pressed_start", "key": m.group(1)})
            if name == "sc_block_end":
                return ("scratch_command", {"action": "block_end"})
            if name in ("sc_show", "sc_hide", "sc_pen_down", "sc_pen_up", "sc_pen_clear"):
                act = {"sc_show": "show", "sc_hide": "hide", "sc_pen_down": "pen_down",
                       "sc_pen_up": "pen_up", "sc_pen_clear": "pen_clear"}[name]
                return ("scratch_command", {"action": act})
            if name == "sc_pen_color":
                return ("scratch_command", {"action": "pen_color", "value": m.group(1)})
            act = {"sc_move": "move", "sc_right": "turn_right", "sc_left": "turn_left",
                   "sc_wait": "wait", "sc_size": "size"}[name]
            return ("scratch_command", {"action": act, "value": m.group(1), "text": ""})
        if name == "pd_status":
            return ("piper_dataset", {"action": "status"})
        if name == "pd_package":
            return ("piper_dataset", {"action": "package"})
        if name == "pd_reset":
            return ("piper_dataset", {"action": "reset"})
        if name == "pd_redo":
            return ("piper_dataset", {"action": "redo", "index": int(m.group(1))})
        if name == "pd_record":
            return ("piper_dataset", {"action": "record"})
        if name == "mic_test":
            return ("mic_test", {"seconds": 3})
        if name == "yolo_on":
            return ("toggle_detection", {"action": "start"})
        if name == "yolo_off":
            return ("toggle_detection", {"action": "stop"})
        if name == "camera_open":
            return ("toggle_webcam", {"action": "start"})
        if name == "camera_close":
            return ("toggle_webcam", {"action": "stop"})
        if name == "garden_open":
            return ("toggle_garden_cam", {"action": "start"})
        if name == "garden_close":
            return ("toggle_garden_cam", {"action": "stop"})
        if name == "garden_wake":
            return ("wake_garden_cam", {})
        if name == "garden_ptz":
            yon = (m.group(1) or "").strip()
            return ("garden_ptz", {"direction": _GARDEN_PTZ_MAP.get(yon, "right")})
        if name == "take_photo":
            return ("take_photo", {})
        if name == "type_text":
            return ("type_text", {"text": m.group(1).strip()})
        if name == "shutdown":
            return ("shutdown_assistant", {})
        if name == "volume_down":
            return ("system_volume", {"action": "down"})
        if name == "volume_up":
            return ("system_volume", {"action": "up"})
        if name == "volume_mute":
            return ("system_volume", {"action": "mute"})
        if name == "media_next":
            return ("media_control", {"action": "next"})
        if name == "media_prev":
            return ("media_control", {"action": "prev"})
        if name == "media_playpause":
            return ("media_control", {"action": "playpause"})
        if name == "play_media":
            query = (m.group(1) or m.group(2) or "").strip(" ,.")
            if query:
                platform_hint = "spotify" if "spotify" in t.lower() else (
                    "youtube" if "youtube" in t.lower() else "")
                args = {"query": query}
                if platform_hint:
                    args["provider"] = platform_hint
                return ("play_media", args)
            continue
        if name in ("img_insert", "img_insert2"):
            q = (m.group(1) or "").strip(" ,.'\"")
            # "sunuma kedi" → "kedi": hedef/yardımcı sözcükleri baştan at
            for _ in range(3):   # birden fazla ön ek olabilir: "sunuma internetten ..."
                q2 = re.sub(r"^(?:internetten|sunuma|sunumuma|belgeye|slayta|slayda|word'?e|"
                            r"bir|şu|bu|bana)\s+", "", q, flags=re.IGNORECASE).strip()
                if q2 == q:
                    break
                q = q2
            if q and q.lower() not in ("bir", "şu", "bu"):
                return ("insert_image", {"source": q})
            continue
        if name == "slide_del":
            return ("slide_edit", {"action": "delete"})
        if name == "slide_undo":
            return ("slide_edit", {"action": "undo"})
        if name == "xl_chart":
            return ("excel_command", {"action": "chart",
                                      "value": (m.group(1) or "sütun").lower()})
        if name == "xl_range":
            rng = f"{m.group(1).replace(' ', '')}:{m.group(2).replace(' ', '')}".upper()
            return ("excel_command", {"action": "select_range", "value": rng})
        if name.startswith("al_"):
            # "resmi ortala" resim ayarı, "imleci ortala" FARE komutudur → devret
            if re.search(r"\b(resmi|resim|görseli|görsel|fotoğrafı|fotoğraf|"
                         r"fare|fareyi|imleç|imleci)\b", t, re.I):
                continue
            act = {"al_left": "align_left", "al_center": "align_center",
                   "al_right": "align_right", "al_just": "align_justify"}[name]
            return ("office_format", {"action": act, "value": ""})
        if name.startswith("show_"):
            return ("slideshow", {"action": name[5:]})
        if name == "fx_clear":
            low = t.lower()
            what = ("animations" if "animasyon" in low else
                    "transitions" if "geçiş" in low else "all")
            return ("clear_effects", {"what": what})
        if name == "fx_trans":
            eff = (m.group(1) or "rastgele").strip().lower()
            from actions.office_show import TRANSITIONS as _TR
            if eff not in _TR:
                eff = "rastgele"
            return ("add_transition", {"name": eff, "all_slides": True})
        if name == "fx_anim":
            eff = (m.group(1) or "solarak").strip().lower()
            from actions.office_show import ANIMATIONS as _AN
            if eff not in _AN:
                eff = "solarak"
            return ("add_animation", {"name": eff, "all_slides": True})
        if name in ("topic_write", "topic_write2"):
            topic = (m.group(1) or "").strip(" ,.'\"")
            topic = re.sub(r"^(?:internetten|bir|şu|bu)\s+", "", topic, flags=re.IGNORECASE).strip()
            if len(topic) >= 3 and topic.lower() not in ("resim", "resmi", "fotoğraf", "görsel"):
                target = ("word" if re.search(r"word|belge", t, re.I) else
                          "powerpoint" if re.search(r"sunum|slayt|powerpoint", t, re.I) else "auto")
                return ("write_topic", {"topic": topic, "target": target})
            continue
        if name.startswith("img_") and name not in ("img_insert", "img_insert2"):
            act = {"img_rot_left": "rotate_left", "img_rot_right": "rotate_right",
                   "img_flip_h": "flip_h", "img_flip_v": "flip_v",
                   "img_bigger": "bigger", "img_smaller": "smaller",
                   "img_center": "center", "img_left": "left", "img_right": "right",
                   "img_reset": "reset"}[name]
            return ("image_adjust", {"action": act, "value": ""})
        if name == "word_pdf":
            return ("word_export_pdf", {"name": ""})
        if name == "xl_score":
            return ("excel_command", {"action": "score_table", "value": ""})
        if name == "xl_avg":
            return ("excel_command", {"action": "average", "value": ""})
        if name == "xl_sum":
            return ("excel_command", {"action": "sum", "value": ""})
        if name == "fmt_font_color":
            return ("office_format", {"action": "font_color", "value": m.group(1)})
        if name == "fmt_page_color":
            return ("office_format", {"action": "page_color", "value": m.group(1)})
        if name == "fmt_page_color_any":
            return ("office_format", {"action": "page_color", "value": ""})
        if name == "fmt_font_size":
            return ("office_format", {"action": "font_size", "value": m.group(1)})
        if name == "fmt_new_page":
            return ("office_format", {"action": "new_page", "value": ""})
        if name == "fmt_design":
            return ("office_format", {"action": "random_design", "value": ""})
        if name == "fmt_grow":
            return ("office_format", {"action": "font_grow", "value": ""})
        if name == "fmt_shrink":
            return ("office_format", {"action": "font_shrink", "value": ""})
        if name == "blender_save":
            return ("save_blender_project", {"name": ""})
        if name == "freecad_save":
            return ("save_freecad_project", {"name": ""})
        if name.startswith("k_"):
            return ("press_key", {"key": name[2:], "times": 1})
        if name == "m_right":
            return ("mouse_control", {"action": "right_click"})
        if name == "m_double":
            return ("mouse_control", {"action": "double_click"})
        if name == "m_left":
            return ("mouse_control", {"action": "left_click"})
        if name == "m_sdown":
            return ("mouse_control", {"action": "scroll_down"})
        if name == "m_sup":
            return ("mouse_control", {"action": "scroll_up"})
        if name == "m_center":
            return ("mouse_control", {"action": "center"})
        if name == "m_move":
            return ("mouse_control", {"action": "move", "direction": m.group(1).lower()})
        if name == "rec_voice":
            return ("record_voice_sample", {"seconds": 10})
        if name == "close_last":
            return ("close_app", {"app_name": "__last__"})
        if name == "close_generic":
            return ("close_app", {"app_name": "__last__"})
        if name.startswith("bl_"):
            act = {"bl_clear": "clear", "bl_cube": "delete_cube",
                   "bl_delsel": "delete_selected", "bl_selall": "select_all"}[name]
            return ("blender_scene", {"action": act})
        if name == "blender_draw":
            return ("blender_draw", {"instruction": m.group(1).strip()})
        if name == "freecad_draw":
            return ("freecad_draw", {"instruction": m.group(1).strip()})
        if name == "save_doc":
            return ("save_active_document", {})
        if name == "record_video":
            seconds = 5
            if m.groups() and m.group(1):
                try:
                    seconds = max(1, min(int(m.group(1)), 60))
                except ValueError:
                    pass
            return ("record_video", {"seconds": seconds})

        if name in ("open_app", "close_app"):
            app_raw = (m.group(1) or "").strip()
            # Hal ekini sondan ayıkla: "blender'ı" → "blender"
            app = re.sub(r"'[a-zçğıöşü]+$", "", app_raw, flags=re.IGNORECASE).strip()
            app_lower = app.lower()
            if not app or app_lower in _NOT_APPS:
                continue
            # Tek harf / çok kısa yakalamaları ele
            if len(app) < 2:
                continue
            tool = "open_app" if name == "open_app" else "close_app"
            return (tool, {"app_name": app})

    return None


def detect_intent(text: str):
    """
    Metinde net bir eylem komutu ararsa (intent, args) döner, yoksa None.
    intent ∈ {"toggle_webcam", "take_photo", "record_video", "open_app", "close_app", ...}

    STT YANLIŞ ANLAMA FİLTRESİ — sıralama ÖNEMLİ:
      1) normalize_stt_text() HER ZAMAN çağrılır (ucuzdur) — böylece
         get_last_correction() bu çağrı için her zaman GÜNCEL bilgi verir.
      2) Bir düzeltme yapıldıysa (ör. "kotlama aracını aç" → "kodlama
         aracını aç"): düzeltilmiş metin ÖNCE SADECE spesifik (open_app/
         close_app joker deseni DIŞINDAKİ) bir eşleşme için denenir. Bunun
         nedeni: "kodlama" gibi belirli bir kelime bozulduğunda, orijinal
         (bozuk) metin _PATTERNS listesinin EN SONUNDAKİ genel "her şeyi
         uygulama adı say, aç" joker desenine yanlışlıkla düşebiliyor
         (ör. "kotlama aracı" diye var olmayan bir uygulama açmaya
         çalışır) — bu, asıl doğru ve spesifik komuttan ÖNCE eşleşip onu
         hiç görünmez kılardı.
      3) Öyle bir düzeltme/özel eşleşme yoksa: orijinal metin normal
         sırayla denenir — hâlihazırda doğru çalışan HİÇBİR komutun
         davranışı bu yüzden değişmez.
      4) O da olmazsa: düzeltilmiş metin (open_app/close_app dahil) son
         kez denenir.
    """
    t = (text or "").strip()
    if not t:
        return None

    fixed = normalize_stt_text(t)

    if fixed != t:
        result = _match_patterns(fixed)
        if result is not None and result[0] not in ("open_app", "close_app"):
            return result

    result = _match_patterns(t)
    if result is not None:
        return result

    if fixed != t:
        result = _match_patterns(fixed)
        if result is not None:
            return result

    return None
