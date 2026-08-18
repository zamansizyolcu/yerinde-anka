"""
actions/tasarim_studyosu.py — 3B Tasarım Stüdyosunu tarayıcıda açar VE
(araç açıkken) sesli komutlarla canlı olarak yönetir.

Satranç / Çin Daması / Robotik Simülatör araçlarıyla AYNI mimari: tek dosyalık,
bağımsız HTML — dış sunucu/dosya bağımlılığı yok (Three.js motoru dosyanın
içine gömülü). Kullanıcı temel şekillerden (küp, silindir, küre, koni,
piramit, simit) basit bir 3 boyutlu tasarım oluşturabilir, delik açabilir,
var olan bir STL dosyasını açıp üzerinde çalışmaya devam edebilir ve
sonucu STL formatında indirip 3B yazıcıda basabilir.

CANLI SESLİ KONTROL: Araç açıldığında core/bridge_server.py içindeki minimal
WebSocket sunucusu da başlatılır (dış kütüphane gerekmez). Tarayıcıdaki sayfa
buna otomatik bağlanır; buradaki komut fonksiyonları bridge_server.send_command()
ile sayfaya JSON komutlar gönderir (şekil ekle, taşı, boyutlandır, döndür,
renklendir, delik yap/uygula, STL indir, sahneyi temizle). Araç açık değilse
(bağlı istemci yoksa) kullanıcıya önce aracı açması gerektiği söylenir.
"""

from __future__ import annotations

import base64
import json
import platform
import subprocess
import time
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

_NOT_OPEN_MSG = "3B Tasarım Stüdyosu şu an açık değil gibi görünüyor — önce 'tasarım stüdyosunu aç' diyerek açar mısın?"

_RENK_HARITASI = {
    "kırmızı": "#e53935", "kirmizi": "#e53935",
    "mavi": "#3b82f6",
    "yeşil": "#43a047", "yesil": "#43a047",
    "sarı": "#fdd835", "sari": "#fdd835",
    "turuncu": "#fb8c00",
    "mor": "#8e24aa",
    "pembe": "#ec4899",
    "siyah": "#222222",
    "beyaz": "#f5f5f5",
    "gri": "#9e9e9e",
    "kahverengi": "#795548",
    "camgöbeği": "#00bcd4", "camgobegi": "#00bcd4", "turkuaz": "#00bcd4",
}

_SEKIL_HARITASI = {
    "küp": "box", "kup": "box", "kutu": "box",
    "silindir": "cylinder",
    "küre": "sphere", "kure": "sphere", "top": "sphere",
    "koni": "cone",
    "piramit": "pyramid",
    "simit": "torus", "halka": "torus", "torus": "torus",
    "dişli": "gear", "disli": "gear", "dişli çark": "gear", "disli cark": "gear",
    "ultrasonik": "ultrasonik", "mesafe sensörü": "ultrasonik", "mesafe sensoru": "ultrasonik",
    "pir": "pirSensor", "hareket sensörü": "pirSensor", "hareket sensoru": "pirSensor",
}

_ROBOT_PARCA_HARITASI = {
    "gövde": "govde", "govde": "govde",
    "tekerlek": "tekerlek",
    "eklem": "eklemTop", "küresel eklem": "eklemTop", "kuresel eklem": "eklemTop",
    "kol": "kol", "kol parçası": "kol", "kol parcasi": "kol",
    "dişli": "disliCark", "disli": "disliCark", "dişli çark": "disliCark", "disli cark": "disliCark",
    "motor": "motor",
    "sensör": "sensor", "sensor": "sensor",
    "ultrasonik": "ultrasonikSensor", "mesafe sensörü": "ultrasonikSensor", "mesafe sensoru": "ultrasonikSensor",
    "pir": "pirSensor", "hareket sensörü": "pirSensor", "hareket sensoru": "pirSensor",
    "ışık sensörü": "isikSensoru", "isik sensoru": "isikSensoru", "ışık": "isikSensoru", "isik": "isikSensoru",
}

_MALZEME_HARITASI = {
    "düz": "duz", "duz": "duz", "renk": "duz",
    "ahşap": "ahsap", "ahsap": "ahsap", "tahta": "ahsap",
    "metal": "metal", "metalik": "metal",
    "plastik": "plastik",
    "cam": "cam",
}

# Robot parçaları (ROBOT_PARTS anahtarları) sahnede hangi TEMEL şekil
# türüyle (SHAPE_DEFS) oluşturulmuş olarak tutuluyor - sesle "gövdeyi seç"
# gibi bir komutta, o parçanın ALTINDA yatan temel türü bulmak için.
_ROBOT_PARCA_TEMEL_TUR = {
    "govde": "box", "tekerlek": "cylinder", "eklemTop": "sphere", "kol": "box",
    "disliCark": "gear", "motor": "cylinder", "sensor": "cone",
    "ultrasonikSensor": "ultrasonik", "pirSensor": "pirSensor", "isikSensoru": "cylinder",
}

# Hazir doku (resim) on ayarlari - app.js icindeki PRESET_TEXTURES nesnesinin
# anahtarlarina karsilik gelir.
_DOKU_HARITASI = {
    "ahşap": "ahsap", "ahsap": "ahsap", "tahta": "ahsap",
    "halı": "hali_desenli", "hali": "hali_desenli", "halı desenli": "hali_desenli", "hali desenli": "hali_desenli",
    "halı tüylü": "hali_tuylu", "hali tuylu": "hali_tuylu", "tüylü halı": "hali_tuylu", "tuylu hali": "hali_tuylu",
    "minder": "minder",
    "koltuk": "koltuk",
    "deri": "deri",
    "duvar": "duvar", "taş": "duvar", "tas": "duvar", "taş duvar": "duvar",
    "kiremit": "kiremit_duz", "kiremit düz": "kiremit_duz", "düz kiremit": "kiremit_duz",
    "eski kiremit": "kiremit", "kiremit eski": "kiremit", "yıpranmış kiremit": "kiremit",
}


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "3b-tasarim-studyosu" / "3b-tasarim-studyosu.html"


def open_tasarim_studyosu() -> str:
    """'3 boyutlu tasarım stüdyosunu aç' / '3B tasarım aracını aç' /
    'stl tasarım aracını aç' / 'nesne tasarlama aracını aç'
    — tek dosyalık 3B tasarım stüdyosunu tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("3B Tasarım Stüdyosu bulunamadı — '3b-tasarim-studyosu' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    bridge_server.register_trigger("blender_export_trigger", _handle_export_trigger)
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("3B Tasarım Stüdyosu tarayıcıda açılıyor! Soldan bir şekil seçip "
                "ekleyebilir, seçtiğin nesnenin konumunu, boyutunu, döndürmesini "
                "ve rengini düzenleyebilir, delik açıp STL olarak indirebilirsin. "
                "Artık sesli komutlarla da yönlendirebilirsin.")
    except Exception:
        try:
            webbrowser.open(url)
            return "3B Tasarım Stüdyosu tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"


def _send_or_warn(payload: dict, basari_mesaji: str) -> str:
    if bridge_server.send_command(payload):
        return basari_mesaji
    return _NOT_OPEN_MSG


def tasarim_tema_command(tema: str) -> str:
    """3B Tasarım Stüdyosu YA DA Robot Tasarım Atölyesi tarayıcıda AÇIKKEN
    (ikisi de aynı köprüyü paylaşır, hangisi açıksa o etkilenir), arayüz
    temasını değiştirir: mavi, yeşil ya da krem. 'temayı yeşil yap', 'krem
    temaya geç' gibi komutlarla tetiklenir."""
    haritalar = {"mavi": "blue", "yeşil": "green", "yesil": "green", "krem": "cream"}
    key = (tema or "").strip().lower()
    theme_id = haritalar.get(key)
    if not theme_id:
        return f"'{tema}' tanıdık bir tema değil — mavi, yeşil ya da krem diyebilirsin."
    return _send_or_warn({"action": "set_theme", "theme": theme_id}, f"Temayı {tema} yapıyorum!")


def tasarim_kapat_command() -> str:
    """3B Tasarım Stüdyosu YA DA Robot Tasarım Atölyesi tarayıcıda AÇIKKEN
    (ikisi de aynı köprüyü paylaşır, hangisi açıksa o etkilenir), o sekmeyi
    kapatmayı dener. 'tasarım stüdyosunu kapat', 'aracı kapat' gibi
    komutlarla tetiklenir. NOT: bazı tarayıcılar, script tarafından
    açılmamış sekmelerin kapatılmasını güvenlik nedeniyle engeller — bu
    durumda kullanıcının sekmeyi elle kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")


def ekle_sekil_command(sekil: str) -> str:
    """Tarayıcıda açık olan 3B Tasarım Stüdyosuna yeni bir temel şekil
    (küp, silindir, küre, koni, piramit, simit, dişli çark ya da genel
    sensör şekilleri) ekler."""
    key = (sekil or "").strip().lower()
    tip = _SEKIL_HARITASI.get(key)
    if not tip:
        return f"'{sekil}' tanıdık bir şekil değil — küp, silindir, küre, koni, piramit, simit ya da dişli diyebilirsin."
    return _send_or_warn({"action": "add_shape", "shape": tip}, f"{sekil.capitalize()} ekleniyor!")


def robot_parca_ekle_command(parca: str) -> str:
    """3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi'nde, hazır renk/
    ölçek/malzeme ön ayarlarıyla bir ROBOT PARÇASI ekler (gövde, tekerlek,
    eklem, kol, dişli çark, motor, sensör, ultrasonik/PIR/ışık sensörü)."""
    key = (parca or "").strip().lower()
    part_key = _ROBOT_PARCA_HARITASI.get(key)
    if not part_key:
        return (f"'{parca}' tanıdık bir robot parçası değil — gövde, tekerlek, eklem, kol, "
                "dişli, motor, sensör, ultrasonik, pir ya da ışık sensörü diyebilirsin.")
    return _send_or_warn({"action": "add_robot_part", "part": part_key}, f"{parca.capitalize()} ekleniyor!")


def renk_command(renk: str) -> str:
    """3B Tasarım Stüdyosunda seçili olan nesnenin rengini değiştirir."""
    key = (renk or "").strip().lower()
    hexcode = _RENK_HARITASI.get(key)
    if not hexcode:
        return f"'{renk}' rengini tanımıyorum — kırmızı, mavi, yeşil, sarı, turuncu, mor, pembe, siyah, beyaz veya gri diyebilirsin."
    return _send_or_warn({"action": "set_color", "color": hexcode}, f"Rengi {renk} yapıyorum!")


def malzeme_command(malzeme: str) -> str:
    """3B Tasarım Stüdyosunda seçili olan nesnenin malzemesini (düz renk,
    ahşap, metal, plastik ya da cam) değiştirir."""
    key = (malzeme or "").strip().lower()
    preset = _MALZEME_HARITASI.get(key)
    if not preset:
        return f"'{malzeme}' malzemesini tanımıyorum — düz, ahşap, metal, plastik ya da cam diyebilirsin."
    return _send_or_warn({"action": "set_material", "preset": preset}, f"Malzemeyi {malzeme} yapıyorum!")


def doku_uygula_command(doku: str) -> str:
    """3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi'nde, seçili olan
    nesneye hazır bir resim dokusu (ahşap, halı, koltuk, minder, deri,
    duvar/taş, kiremit) uygular — kullanıcının ayrıca bir resim yüklemesine
    gerek kalmaz."""
    key = (doku or "").strip().lower()
    tex_key = _DOKU_HARITASI.get(key)
    if not tex_key:
        return (f"'{doku}' tanıdık bir doku değil — ahşap, halı, koltuk, minder, "
                "deri, duvar, taş ya da kiremit diyebilirsin.")
    return _send_or_warn({"action": "apply_preset_texture", "key": tex_key}, f"{doku.capitalize()} dokusunu uyguluyorum!")


_YON_DELTA = {
    "sağ": (2, 0, 0), "sag": (2, 0, 0), "sağa": (2, 0, 0), "saga": (2, 0, 0),
    "sol": (-2, 0, 0), "sola": (-2, 0, 0),
    "yukarı": (0, 1, 0), "yukari": (0, 1, 0), "yukarıya": (0, 1, 0),
    "aşağı": (0, -1, 0), "asagi": (0, -1, 0), "aşağıya": (0, -1, 0),
    "ileri": (0, 0, -2), "öne": (0, 0, -2), "one": (0, 0, -2),
    "geri": (0, 0, 2), "arkaya": (0, 0, 2),
}


def tasi_command(yon: str) -> str:
    """3B Tasarım Stüdyosunda seçili olan nesneyi belirtilen yönde
    (sağ/sol/yukarı/aşağı/ileri/geri) bir adım taşır."""
    key = (yon or "").strip().lower()
    delta = _YON_DELTA.get(key)
    if not delta:
        return f"'{yon}' yönünü anlayamadım — sağ, sol, yukarı, aşağı, ileri veya geri diyebilirsin."
    dx, dy, dz = delta
    return _send_or_warn({"action": "move", "dx": dx, "dy": dy, "dz": dz}, f"Nesneyi {yon} taşıyorum!")


_EKSEN_HARITASI = {
    "genişlik": "x", "genislik": "x", "genişliği": "x", "genisligi": "x",
    "yükseklik": "y", "yukseklik": "y", "yüksekliği": "y", "yuksekligi": "y",
    "derinlik": "z", "derinliği": "z", "derinligi": "z",
}


def boyutlandir_command(yon: str, eksen: str | None = None) -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi büyütür ya da küçültür.
    İsteğe bağlı olarak genişlik/yükseklik/derinlik ekseni belirtilebilir;
    belirtilmezse üç eksende birden uygulanır."""
    buyut = (yon or "").strip().lower() in ("büyüt", "buyut", "büyült", "buyult")
    kucult = (yon or "").strip().lower() in ("küçült", "kucult", "küçük", "kucuk")
    if not (buyut or kucult):
        return f"'{yon}' anlaşılamadı — 'büyüt' ya da 'küçült' diyebilirsin."
    delta = 0.5 if buyut else -0.5
    eksen_key = _EKSEN_HARITASI.get((eksen or "").strip().lower())
    fiil = "büyütüyorum" if buyut else "küçültüyorum"
    if eksen_key:
        return _send_or_warn({"action": "resize", "axis": eksen_key, "delta": delta}, f"{eksen.capitalize()} {fiil}!")
    return _send_or_warn({"action": "resize_uniform", "delta": delta}, f"Nesneyi {fiil}!")


def dondur_command(yon: str) -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi döndürür. 'sağa'/'sola' yatay
    (Y ekseni, düşey eksende döner) döndürme yapar; 'yukarı'/'aşağı'/'öne'/
    'arkaya'/'dikey' ise nesneyi dikey (X ekseni) devirir."""
    key = (yon or "").strip().lower()
    if key in ("sağ", "sag", "sağa", "saga"):
        axis, degrees = "y", 45
    elif key in ("sol", "sola"):
        axis, degrees = "y", -45
    elif key in ("yukarı", "yukari", "yukarıya", "yukariya"):
        axis, degrees = "x", -45
    elif key in ("aşağı", "asagi", "aşağıya", "asagiya"):
        axis, degrees = "x", 45
    elif key in ("öne", "one"):
        axis, degrees = "x", 45
    elif key in ("arkaya", "geri"):
        axis, degrees = "x", -45
    elif key in ("dikey", "dik"):
        axis, degrees = "x", 45
    else:
        return f"'{yon}' anlaşılamadı — sağa, sola (yatay) ya da yukarı, aşağı, dikey (düşey) diyebilirsin."
    return _send_or_warn({"action": "rotate", "axis": axis, "degrees": degrees}, f"Nesneyi {yon} döndürüyorum!")


def _parse_axes(eksen: str) -> dict:
    """'x', 'y', 'z', 'xy', 'x ve z', 'hepsi' gibi ifadeleri eksen
    bayraklarına çevirir."""
    key = (eksen or "").strip().lower().replace(" ", "").replace("ve", "")
    if key in ("", "hepsi", "hepsini", "üçü", "ucu", "üçünü", "ucunu", "tümü", "tumu", "hepsindede"):
        return {"axisX": True, "axisY": True, "axisZ": True}
    return {"axisX": "x" in key, "axisY": "y" in key, "axisZ": "z" in key}


def donusu_baslat_command(eksen: str = "y") -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi KENDİ EKSENİNDE sürekli
    döndürmeye başlar (önizlemede — STL statik kalır). Eksen olarak x, y,
    z ya da bunların birkaçı/hepsi ('x ve z', 'hepsi') verilebilir."""
    axes = _parse_axes(eksen)
    if not (axes["axisX"] or axes["axisY"] or axes["axisZ"]):
        axes["axisY"] = True
    payload = {"action": "set_spin", "enabled": True}
    payload.update(axes)
    return _send_or_warn(payload, "Nesneyi kendi ekseninde döndürmeye başlıyorum!")


def donusu_durdur_command() -> str:
    """3B Tasarım Stüdyosunda seçili nesnenin kendi ekseni etrafındaki
    sürekli dönüşünü durdurur."""
    return _send_or_warn({"action": "set_spin", "enabled": False}, "Dönüşü durduruyorum!")


def yorunge_baslat_command(eksen: str = "y") -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi, sahnedeki en son eklenen
    BAŞKA nesnenin etrafında yörüngeye sokar (önizlemede). Eksen olarak
    x, y, z ya da birkaçı/hepsi verilebilir — birden fazla eksen seçilirse
    daha karmaşık ('tumbling') bir yörünge yolu oluşur."""
    axes = _parse_axes(eksen)
    if not (axes["axisX"] or axes["axisY"] or axes["axisZ"]):
        axes["axisY"] = True
    payload = {"action": "set_orbit", "enabled": True}
    payload.update(axes)
    return _send_or_warn(payload, "Nesneyi başka bir nesnenin etrafında döndürmeye başlıyorum!")


def yorunge_durdur_command() -> str:
    """3B Tasarım Stüdyosunda seçili nesnenin yörünge (başka bir nesnenin
    etrafında dönme) hareketini durdurur."""
    return _send_or_warn({"action": "set_orbit", "enabled": False}, "Yörüngeyi durduruyorum!")


def nesne_sil_command() -> str:
    """3B Tasarım Stüdyosunda o an seçili olan nesneyi siler."""
    return _send_or_warn({"action": "delete"}, "Seçili nesneyi siliyorum!")


def kopyala_command() -> str:
    """3B Tasarım Stüdyosunda o an seçili olan nesnenin bir kopyasını
    oluşturur (kopya hafifçe kaydırılmış konumda belirir)."""
    return _send_or_warn({"action": "duplicate"}, "Nesnenin kopyasını oluşturuyorum!")


_YUMUSAKLIK_HARITASI = {
    "az": 0.3, "biraz": 0.3, "hafif": 0.3,
    "orta": 0.7,
    "çok": 1.3, "cok": 1.3, "fazla": 1.3,
    "tam": 1.9, "maksimum": 1.9,
    "keskin": 0.0, "sivri": 0.0, "sıfır": 0.0,
}


def kenar_yumusat_command(miktar: str = "") -> str:
    """3B Tasarım Stüdyosunda seçili nesnenin (küp, silindir, koni ya da
    piramit) kenarlarını/köşelerini yuvarlatır. 'az/orta/çok/tam' gibi
    kabaca bir miktar ya da doğrudan bir sayı kabul eder."""
    key = (miktar or "orta").strip().lower()
    value = _YUMUSAKLIK_HARITASI.get(key)
    if value is None:
        try:
            value = float(key.replace(",", "."))
        except ValueError:
            value = 0.7
    return _send_or_warn({"action": "set_edge_round", "value": value}, "Kenarları yumuşatıyorum!")


def birlestir_command() -> str:
    """3B Tasarım Stüdyosunda sahnedeki tüm katı (delik olmayan) nesneleri
    tek bir parçada birleştirir (boolean birleşim/union)."""
    return _send_or_warn({"action": "merge_all"}, "Nesneleri birleştiriyorum!")


def birlestirmeyi_geri_al_command() -> str:
    """3B Tasarım Stüdyosunda, seçili olan nesne daha önce 'Nesneleri
    Birleştir' ile oluşturulmuş bir birleşimse, onu tekrar orijinal ayrı
    parçalarına ayırır (birleştirmeyi geri alır)."""
    return _send_or_warn({"action": "undo_merge"}, "Birleştirmeyi geri alıyorum!")


def delik_yap_command() -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi 'delik' (başka bir katı
    nesneden çıkarılacak boolean kesme aracı) olarak işaretler."""
    return _send_or_warn({"action": "set_hole", "value": True}, "Nesneyi delik yapıyorum — üzerine bindirdiğin katı nesnelerden 'Delikleri Uygula' ile çıkarabilirsin!")


def kati_yap_command() -> str:
    """3B Tasarım Stüdyosunda seçili nesneyi tekrar normal katı nesneye
    çevirir (delik işaretini kaldırır)."""
    return _send_or_warn({"action": "set_hole", "value": False}, "Nesneyi katı yapıyorum!")


def delikleri_uygula_command() -> str:
    """3B Tasarım Stüdyosunda işaretlenmiş tüm delik nesnelerini, üzerine
    bindikleri katı nesnelerden kalıcı olarak keser (boolean çıkarma)."""
    return _send_or_warn({"action": "apply_holes"}, "Delikleri uyguluyorum!")


def stl_indir_command() -> str:
    """3B Tasarım Stüdyosundaki tasarımı STL dosyası olarak indirir
    (delikler otomatik uygulanmış olarak)."""
    return _send_or_warn({"action": "export_stl"}, "Tasarımı STL olarak indiriyorum!")


def stl_kaydet_command(isim: str = "") -> str:
    """3B Tasarım Stüdyosundaki tasarımı, tarayıcı indirmesi yerine
    DOĞRUDAN masaüstündeki Çalışmalarım/STL klasörüne bir .stl dosyası
    olarak kaydeder (delikler otomatik uygulanmış olarak)."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    raw = bridge_server.request_and_wait({"action": "request_stl_export"}, timeout=8.0)
    if raw is None:
        return ("Tasarım aracından STL verisi alınamadı (zaman aşımı) — "
                "aracın açık ve yanıt verir durumda olduğundan emin ol.")
    try:
        data = json.loads(raw)
    except Exception:
        return "STL verisi okunamadı (beklenmeyen format)."
    if not data.get("ok", True) and data.get("message"):
        return data["message"]
    b64 = data.get("data")
    if not b64:
        return "STL verisi boş geldi — sahnede en az bir katı şekil olduğundan emin ol."
    try:
        binary = base64.b64decode(b64)
    except Exception:
        return "STL verisi çözümlenemedi."

    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("STL")
    base = (isim or "tasarim").strip().replace("/", "-") or "tasarim"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.stl"
    try:
        target.write_bytes(binary)
    except Exception as e:
        return f"STL dosyası kaydedilemedi: {e}"
    return f"Tasarım STL olarak kaydedildi: {target.name} (Çalışmalarım/STL klasörü)."


def stl_ac_command(dosya_adi: str = "") -> str:
    """Çalışmalarım/STL klasöründe verilen isme uyan (ya da isim
    verilmezse en son kaydedilen) bir .stl dosyasını bulup, açık olan 3B
    Tasarım Stüdyosuna yükler (üzerinde çalışmaya devam edilebilir)."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG

    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("STL")
    candidates = sorted(folder.glob("*.stl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return "Çalışmalarım/STL klasöründe hiç .stl dosyası bulunamadı."

    name_key = (dosya_adi or "").strip().lower()
    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
    chosen = matches[0] if matches else candidates[0]

    try:
        binary = chosen.read_bytes()
    except Exception as e:
        return f"Dosya okunamadı: {e}"
    b64 = base64.b64encode(binary).decode("ascii")
    ok = bridge_server.send_command({"action": "load_stl_data", "data": b64, "filename": chosen.name})
    if not ok:
        return _NOT_OPEN_MSG
    return f"{chosen.name} dosyasını tasarım aracına yüklüyorum!"


def glb_indir_command() -> str:
    """3B Tasarım Stüdyosundaki tasarımı GLB dosyası olarak indirir. GLB,
    STL'den farklı olarak rengi/malzemeyi/dokuyu da saklar."""
    return _send_or_warn({"action": "export_glb"}, "Tasarımı GLB olarak indiriyorum!")


def glb_kaydet_command(isim: str = "") -> str:
    """3B Tasarım Stüdyosundaki tasarımı (renk/malzeme/doku dahil), tarayıcı
    indirmesi yerine DOĞRUDAN masaüstündeki Çalışmalarım/GLB klasörüne bir
    .glb dosyası olarak kaydeder. 'ekle', 'çalışmalarıma ekle', 'GLB'yi
    çalışmalarıma kaydet', 'dokulu dosyayı kaydet' gibi komutlarla da
    tetiklenebilir — ama DİKKAT: 'ekle' kelimesi genelde yeni bir şekil
    eklemek (ekle_sekil_command) için kullanılır; sadece kullanıcı az önce
    bir şekil eklemeyip doğrudan 'ekle' derse ve bağlamdan (az önce tasarımı
    tamamladığından) kaydetmek istediği anlaşılıyorsa bu aracı kullan."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    raw = bridge_server.request_and_wait({"action": "request_glb_export"}, timeout=8.0)
    if raw is None:
        return ("Tasarım aracından GLB verisi alınamadı (zaman aşımı) — "
                "aracın açık ve yanıt verir durumda olduğundan emin ol.")
    try:
        data = json.loads(raw)
    except Exception:
        return "GLB verisi okunamadı (beklenmeyen format)."
    if not data.get("ok", True) and data.get("message"):
        return data["message"]
    b64 = data.get("data")
    if not b64:
        return "GLB verisi boş geldi — sahnede en az bir katı şekil olduğundan emin ol."
    try:
        binary = base64.b64decode(b64)
    except Exception:
        return "GLB verisi çözümlenemedi."

    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("GLB")
    base = (isim or "tasarim").strip().replace("/", "-") or "tasarim"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.glb"
    try:
        target.write_bytes(binary)
    except Exception as e:
        return f"GLB dosyası kaydedilemedi: {e}"
    return f"Tasarım GLB olarak kaydedildi: {target.name} (Çalışmalarım/GLB klasörü)."


def glb_ac_command(dosya_adi: str = "") -> str:
    """Çalışmalarım/GLB klasöründe verilen isme uyan (ya da isim
    verilmezse en son kaydedilen) bir .glb dosyasını bulup, açık olan 3B
    Tasarım Stüdyosuna yükler (renk/malzeme/doku dahil, üzerinde
    çalışmaya devam edilebilir)."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG

    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("GLB")
    candidates = sorted(folder.glob("*.glb"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return "Çalışmalarım/GLB klasöründe hiç .glb dosyası bulunamadı."

    name_key = (dosya_adi or "").strip().lower()
    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
    chosen = matches[0] if matches else candidates[0]

    try:
        binary = chosen.read_bytes()
    except Exception as e:
        return f"Dosya okunamadı: {e}"
    b64 = base64.b64encode(binary).decode("ascii")
    ok = bridge_server.send_command({"action": "load_glb_data", "data": b64, "filename": chosen.name})
    if not ok:
        return _NOT_OPEN_MSG
    return f"{chosen.name} dosyasını tasarım aracına yüklüyorum!"


def nesne_ortala_command() -> str:
    """3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi'nde, o an SEÇİLİ olan
    nesneyi sahnenin (ekranın) tam ortasına taşır — yatay eksenlerde (X/Z)
    sıfırlar, yüksekliğini (Y) korur ki nesne yerde/tabanda kalmaya devam
    etsin. 'seçili nesneyi ekranda ortala', 'nesneyi ortala', 'ortaya al'
    gibi komutlarla tetiklenir; önce bir nesnenin seçili olması gerekir."""
    return _send_or_warn({"action": "center_selected"}, "Nesneyi ekranın ortasına taşıyorum!")


def sahneyi_temizle_command() -> str:
    """3B Tasarım Stüdyosundaki TÜM nesneleri sahneden kaldırır."""
    return _send_or_warn({"action": "clear_scene"}, "Tasarım sahnesini temizliyorum!")


def nesne_sec_command(tanim: str = "", renk: str = "") -> str:
    """3B Tasarım Stüdyosunda, verilen tanıma ve/veya renge uyan bir nesneyi
    seçer. 'son'/'ilk' (eklenme sırasına göre) ya da bir şekil/robot parçası
    adı (küp, tekerlek, gövde, dişli, vb.) kabul eder; isteğe bağlı olarak
    bir renk de belirtilebilir ('kırmızı olanı seç' gibi). Birden fazla
    eşleşme varsa en son eklenmiş olanı seçer."""
    key = (tanim or "").strip().lower()
    which = "last"
    shape_type = None
    if key in ("", "son", "sonuncu", "en son", "son eklenen", "sonraki"):
        which = "last"
    elif key in ("ilk", "ilki", "ilk eklenen"):
        which = "first"
    elif key:
        shape_type = _SEKIL_HARITASI.get(key)
        if not shape_type:
            robot_part_key = _ROBOT_PARCA_HARITASI.get(key)
            if robot_part_key:
                shape_type = _ROBOT_PARCA_TEMEL_TUR.get(robot_part_key)
        if not shape_type:
            return (f"'{tanim}' tanıdık bir nesne türü değil — bir şekil/parça adı "
                    "(küp, tekerlek, gövde, dişli, vb.), 'son' ya da 'ilk' diyebilirsin.")

    renk_key = (renk or "").strip().lower()
    hexcode = _RENK_HARITASI.get(renk_key) if renk_key else None
    if renk_key and not hexcode:
        return f"'{renk}' rengini tanımıyorum — kırmızı, mavi, yeşil, sarı, turuncu, mor, pembe, siyah, beyaz veya gri diyebilirsin."

    payload = {"action": "select_object", "which": which}
    if shape_type:
        payload["shapeType"] = shape_type
    if hexcode:
        payload["color"] = hexcode

    parcalar = []
    if renk:
        parcalar.append(renk)
    if tanim and tanim.strip().lower() not in ("", "son", "sonuncu", "en son", "son eklenen", "sonraki", "ilk", "ilki", "ilk eklenen"):
        parcalar.append(tanim)
    mesaj = (" ".join(parcalar).capitalize() + " nesneyi seçiyorum!") if parcalar else "Son eklenen nesneyi seçiyorum!"
    return _send_or_warn(payload, mesaj)


def _export_objects_to_blender(objects: list, isim: str = "") -> tuple[bool, str, int]:
    """Nesne listesinden bpy kodu üretip Blender'a gönderir ve .blend olarak
    kaydeder. (başarılı_mı, mesaj_veya_dosya_adı, atlanan_stl_sayisi) döner."""
    from actions import blender_bridge
    from actions.blender_export_bpy import generate_scene_code
    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Blender")
    base = (isim or "tasarim").strip().replace("/", "-") or "tasarim"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.blend"

    code, skipped = generate_scene_code(objects, str(target))

    if not blender_bridge.is_bridge_alive():
        acilis = blender_bridge.launch_blender_with_bridge()
        if not blender_bridge.is_bridge_alive():
            return False, f"Blender açılamadı, aktarım yapılamadı: {acilis}", skipped

    result = blender_bridge.send_code(code)
    if "çalıştırıldı" in result:
        return True, target.name, skipped
    return False, f"Blender'a aktarılamadı — {result}", skipped


def blendere_aktar_command(isim: str = "") -> str:
    """3B Tasarım Stüdyosundaki tasarımı gerçek bir Blender (.blend) dosyası
    olarak dışa aktarır: her nesneyi (şekil, konum, döndürme, boyut, renk/
    malzeme) Blender'da yeniden oluşturur, varsa 'kendi ekseninde dön' ya da
    'başka nesnenin etrafında dön' animasyonlarını gerçek Blender keyframe'
    lerine çevirir ve Çalışmalarım/Blender klasörüne kaydeder. İçe aktarılmış
    STL modelleri şu an bu aktarıma dahil edilmez."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG

    raw = bridge_server.request_and_wait({"action": "request_scene_export"}, timeout=6.0)
    if raw is None:
        return ("Tasarım aracından sahne bilgisi alınamadı (zaman aşımı) — "
                "aracın açık ve yanıt verir durumda olduğundan emin ol.")
    try:
        data = json.loads(raw)
        objects = data.get("objects", [])
    except Exception:
        return "Sahne verisi okunamadı (beklenmeyen format)."
    if not objects:
        return "Sahnede hiç nesne yok — önce birkaç şekil ekle."

    ok, name_or_msg, skipped = _export_objects_to_blender(objects, isim)
    if ok:
        msg = f"Tasarım Blender'a aktarıldı ve kaydedildi: {name_or_msg} (Çalışmalarım/Blender klasörü)."
        if skipped:
            msg += (f" Not: içe aktarılmış {skipped} STL nesnesi bu aktarıma "
                     "dahil edilemedi (henüz desteklenmiyor).")
        return msg
    return name_or_msg


def _handle_export_trigger(payload: dict) -> None:
    """Tarayıcıdaki '🧩 Blender'a Aktar' düğmesine tıklandığında (WebSocket
    üzerinden, Python bir şey İSTEMEDEN) çağrılır. Sonuç, tarayıcıya bir
    'export_result' komutu olarak geri gönderilir (ekranda bildirim/toast
    olarak gösterilsin diye) — ses çıkışı burada YOK, çünkü bu akış bir
    düğme tıklamasından geliyor, sesli komuttan değil."""
    objects = payload.get("objects") or []
    if not objects:
        bridge_server.send_command({"action": "export_result", "ok": False,
                                     "message": "Sahnede hiç nesne yok."})
        return
    ok, name_or_msg, skipped = _export_objects_to_blender(objects)
    if ok:
        msg = f"Blender'a aktarıldı: {name_or_msg}"
        if skipped:
            msg += f" ({skipped} STL nesnesi dahil edilemedi)"
        bridge_server.send_command({"action": "export_result", "ok": True, "message": msg})
    else:
        bridge_server.send_command({"action": "export_result", "ok": False, "message": name_or_msg})


def blend_dosyasi_ac_command(dosya_adi: str = "") -> str:
    """Çalışmalarım/Blender klasöründe verilen isme uyan (ya da isim
    verilmezse en son kaydedilen) bir .blend dosyasını bulup Blender'da
    canlı komut köprüsüyle açar."""
    from actions import blender_bridge
    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Blender")
    candidates = sorted(folder.glob("*.blend"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return "Çalışmalarım/Blender klasöründe hiç .blend dosyası bulunamadı."

    name_key = (dosya_adi or "").strip().lower()
    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
    chosen = matches[0] if matches else candidates[0]

    return blender_bridge.launch_blender_with_file(str(chosen))
