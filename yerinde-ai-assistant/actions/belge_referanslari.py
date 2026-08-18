"""
actions/belge_referanslari.py — Kalıcı belge referans kütüphanesi.

"DOSYA YÜKLE" düğmesi her zaman sadece EN SON yüklenen dosyayı hatırlar
(last_uploaded_file) — bu, tek seferlik analizler için yeterli ama zümre
tutanağı örneği, kazanım/KSDT senaryo tablosu, yıllık plan, örnek sınav gibi
belgeler AYNI dosyanın yıl boyunca defalarca (her yeni tutanak/sınav
üretiminde) kullanılmasını gerektirir.

Akış: kullanıcı bir dosya yükler, sonra "bunu bilişim kazanım senaryosu
olarak kaydet" der -> referans_belge_kaydet() son yüklenen dosyayı adlandırılmış
bir yuvaya kaydeder. Sonraki tüm zumre_tutanagi_olustur / sinav_olustur
çağrıları, kullanıcı ayrıca bir dosya belirtmedikçe otomatik olarak bu
kayıtlı referansı kullanır.
"""

from __future__ import annotations

from pathlib import Path

from app_config import get_app_config_value, save_app_config

REFERANS_TURLERI = {
    "bilisim_zumre_ornek":        "Bilişim zümre tutanağı örneği",
    "robotik_zumre_ornek":        "Robotik zümre tutanağı örneği",
    "bilisim_kazanim_senaryosu":  "Bilişim kazanım/KSDT senaryo tablosu",
    "bilisim_yillik_plan":        "Bilişim yıllık planı",
    "robotik_yillik_plan":        "Robotik yıllık planı",
    "bilisim_sinav_ornek_5":      "Bilişim 5. sınıf örnek sınav",
    "bilisim_sinav_ornek_6":      "Bilişim 6. sınıf örnek sınav",
    "robotik_sinav_ornek_5":      "Robotik 5. sınıf örnek sınav",
    "robotik_sinav_ornek_6":      "Robotik 6. sınıf örnek sınav",
    "kulup_yillik_calisma_plani": "Kulüp yıllık çalışma planı örneği",
    "olcek_sablonu":               "Ders içi katılım / proje değerlendirme ölçeği şablonu",
    "puantaj":                     "Kişisel not/puantaj takip dosyası (sınıf sınıf)",
}

# Sesle söylenebilecek doğal takma adlar -> resmî anahtar
_ALIASLAR = {
    "bilişim zümre örneği": "bilisim_zumre_ornek",
    "bilişim zümre": "bilisim_zumre_ornek",
    "robotik zümre örneği": "robotik_zumre_ornek",
    "robotik zümre": "robotik_zumre_ornek",
    "kazanım senaryosu": "bilisim_kazanim_senaryosu",
    "bilişim kazanım senaryosu": "bilisim_kazanim_senaryosu",
    "ksdt": "bilisim_kazanim_senaryosu",
    "bilişim yıllık plan": "bilisim_yillik_plan",
    "bilişim yıllık planı": "bilisim_yillik_plan",
    "robotik yıllık plan": "robotik_yillik_plan",
    "robotik yıllık planı": "robotik_yillik_plan",
    "bilişim 5. sınıf sınav örneği": "bilisim_sinav_ornek_5",
    "bilişim 6. sınıf sınav örneği": "bilisim_sinav_ornek_6",
    "robotik 5. sınıf sınav örneği": "robotik_sinav_ornek_5",
    "robotik 6. sınıf sınav örneği": "robotik_sinav_ornek_6",
    "kulüp yıllık çalışma planı": "kulup_yillik_calisma_plani",
    "kulüp çalışma planı": "kulup_yillik_calisma_plani",
    "kulüp planı": "kulup_yillik_calisma_plani",
    "ölçek şablonu": "olcek_sablonu",
    "ders içi ve proje ölçeği": "olcek_sablonu",
    "değerlendirme ölçeği": "olcek_sablonu",
    "puantaj": "puantaj",
    "puantajım": "puantaj",
    "not listesi": "puantaj",
}


def normalize_tur(tur: str) -> str:
    t = (tur or "").strip().lower()
    if t in REFERANS_TURLERI:
        return t
    if t in _ALIASLAR:
        return _ALIASLAR[t]
    # en yakın eşleşmeyi dene (basit substring araması)
    for alias, key in _ALIASLAR.items():
        if alias in t or t in alias:
            return key
    return t


def referans_yolu(tur: str) -> Path | None:
    key = normalize_tur(tur)
    kutuphane = get_app_config_value("belge_referanslari", {}) or {}
    yol = str(kutuphane.get(key, "") or "").strip()
    if yol and Path(yol).exists():
        return Path(yol)
    return None


def referans_belge_kaydet(tur: str, dosya_yolu: str = "") -> str:
    key = normalize_tur(tur)
    if key not in REFERANS_TURLERI:
        secenekler = ", ".join(f"'{v}'" for v in REFERANS_TURLERI.values())
        return f"'{tur}' tanınmayan bir referans türü. Geçerli türler: {secenekler}."

    candidate = (dosya_yolu or "").strip()
    if not candidate:
        candidate = str(get_app_config_value("last_uploaded_file", "") or "").strip()
    if not candidate:
        return "Kaydedilecek dosya bulunamadı. Önce 'DOSYA YÜKLE' ile bir dosya yükle, sonra tekrar söyle."
    path = Path(candidate)
    if not path.exists():
        return f"Dosya bulunamadı: {path}"

    kutuphane = dict(get_app_config_value("belge_referanslari", {}) or {})
    kutuphane[key] = str(path)
    save_app_config({"belge_referanslari": kutuphane})

    etiket = REFERANS_TURLERI[key]
    return (f"'{path.name}' dosyası kalıcı olarak '{etiket}' referansı olarak kaydedildi. "
            f"Bundan sonraki ilgili işlemlerde otomatik kullanılacak — tekrar yüklemene gerek yok.")


def referans_listele() -> str:
    kutuphane = get_app_config_value("belge_referanslari", {}) or {}
    if not kutuphane:
        return "Henüz kayıtlı bir referans belge yok."
    satirlar = ["Kayıtlı referans belgeler:"]
    for key, etiket in REFERANS_TURLERI.items():
        yol = kutuphane.get(key)
        if yol and Path(yol).exists():
            satirlar.append(f"  ✓ {etiket}: {Path(yol).name}")
    eksikler = [etiket for key, etiket in REFERANS_TURLERI.items()
                if not (kutuphane.get(key) and Path(kutuphane.get(key, "")).exists())]
    if eksikler:
        satirlar.append("Henüz kayıtlı olmayanlar: " + ", ".join(eksikler))
    return "\n".join(satirlar)
