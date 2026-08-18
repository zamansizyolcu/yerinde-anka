"""
actions/akademik_takvim.py — MEB akademik takvimi ve hafta/tarih hesaplama.

Kullanıcı MEB'in yayınladığı "Çalışma Takvimi" görselini paylaştıkça buraya
yeni bir yıl eklenir (AKADEMIK_TAKVIMLER sözlüğüne). Yıllık plan güncelleme
aracı, buradaki tarihlerden hareketle Pazartesi-Cuma'lık, ara tatilleri
atlayan gerçek bir hafta -> tarih listesi üretir.
"""

from __future__ import annotations

from datetime import date, timedelta

AY_ADLARI_TR = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
                "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]

# MEB'in yayınladığı resmî çalışma takvimlerinden — kullanıcı yeni bir yıl
# paylaştıkça buraya eklenir.
AKADEMIK_TAKVIMLER = {
    "2026-2027": {
        "donem1_baslangic": date(2026, 9, 14),
        "donem1_ara_tatil": (date(2026, 11, 16), date(2026, 11, 20)),
        "donem1_bitis": date(2027, 1, 22),
        "yariyil_tatili": (date(2027, 1, 25), date(2027, 2, 5)),
        "donem2_baslangic": date(2027, 2, 8),
        "donem2_ara_tatil": (date(2027, 3, 8), date(2027, 3, 12)),
        "yil_sonu": date(2027, 6, 25),
    },
}


def _ay_adi(d: date) -> str:
    return AY_ADLARI_TR[d.month - 1] if 1 <= d.month <= 12 else ""


def ay_adi_baslik(ay_str: str) -> str:
    """'KASIM' -> 'Kasım' gibi doğru Türkçe baş harf büyütme. Python'un genel
    .capitalize() metodu Türkçe I/İ çiftinde hata yapar (ör. 'KASIM'.capitalize()
    yanlışlıkla 'Kasim' üretir, 'Kasım' değil)."""
    if not ay_str:
        return ay_str
    ilk = ay_str[0]
    ilk_buyuk = "İ" if ilk == "i" else ("I" if ilk == "ı" else ilk.upper())
    kalan = ay_str[1:].replace("İ", "i").replace("I", "ı").lower()
    return ilk_buyuk + kalan


def _hafta_araliklari(baslangic: date, bitis: date, ara_tatiller: list[tuple[date, date]]) -> list[tuple[date, date]]:
    haftalar = []
    cur = baslangic
    while cur <= bitis:
        hafta_sonu = min(cur + timedelta(days=4), bitis)
        tatil_mi = any(t_bas <= cur <= t_bit or t_bas <= hafta_sonu <= t_bit
                        for t_bas, t_bit in ara_tatiller)
        if not tatil_mi:
            haftalar.append((cur, hafta_sonu))
        cur += timedelta(days=7)
    return haftalar


def hafta_takvimi(egitim_yili: str) -> list[dict] | None:
    """Döner: [{'hafta_no':1,'baslangic':date,'bitis':date,'ay':'EYLÜL'}, ...]
    Bilinmeyen bir yıl için None döner."""
    t = AKADEMIK_TAKVIMLER.get(egitim_yili)
    if not t:
        return None
    h1 = _hafta_araliklari(t["donem1_baslangic"], t["donem1_bitis"], [t["donem1_ara_tatil"]])
    h2 = _hafta_araliklari(t["donem2_baslangic"], t["yil_sonu"], [t["donem2_ara_tatil"]])
    sonuc = []
    for i, (s, e) in enumerate(h1 + h2, start=1):
        sonuc.append({"hafta_no": i, "baslangic": s, "bitis": e, "ay": _ay_adi(s)})
    return sonuc


def bilinen_yillar() -> list[str]:
    return sorted(AKADEMIK_TAKVIMLER.keys())
