"""
Basit hava durumu ozeti — uzaktaki bir servis uzerinden calisir.
Alp Ünlü tarafından yapılmıştır — @alppunlu

Varsayilan konum:
- YERINDE_WEATHER_LOCATION env varsa onu kullanir
- yoksa Edirne varsayilir
"""

from __future__ import annotations

import os

import requests


# ── Konum yapılandırması: il / ilçe / köy ───────────────────────────────────
DEFAULT_LOCATION = {
    "il": "Edirne",
    "ilce": "Lalapaşa",
    "koy": "Vaysal Köyü",
}


def get_location() -> dict:
    """config'ten il/ilçe/köy okur; yoksa varsayılan (Edirne/Lalapaşa/Vaysal)."""
    try:
        from app_config import get_app_config_value
        return {
            "il": str(get_app_config_value("weather_il", DEFAULT_LOCATION["il"])
                      or DEFAULT_LOCATION["il"]),
            "ilce": str(get_app_config_value("weather_ilce", DEFAULT_LOCATION["ilce"])
                        or DEFAULT_LOCATION["ilce"]),
            "koy": str(get_app_config_value("weather_koy", DEFAULT_LOCATION["koy"])
                       or DEFAULT_LOCATION["koy"]),
        }
    except Exception:
        return dict(DEFAULT_LOCATION)


def tr_upper(text: str) -> str:
    """Türkçe büyük harf: i→İ (Python'un upper()'ı 'Edirne'yi 'EDIRNE' yapardı)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def display_location() -> dict:
    """Ekranda gösterilecek satırlar: {'baslik': 'VAYSAL KÖYÜ', 'alt': 'LALAPAŞA · EDİRNE'}"""
    loc = get_location()
    koy = (loc.get("koy") or "").strip()
    ilce = (loc.get("ilce") or "").strip()
    il = (loc.get("il") or "").strip()
    baslik = koy or ilce or il
    alt = " · ".join(x for x in (ilce, il) if x and x != baslik)
    return {"baslik": tr_upper(baslik), "alt": tr_upper(alt)}


def _query_candidates(location: str | None) -> list[str]:
    """
    Köy adları hava servisinde çoğu zaman bulunmaz; en dardan en genişe doğru
    dener: köy+ilçe+il → ilçe+il → il. Böylece ekranda köy adı yazsa bile
    veri her hâlükârda gelir (en yakın istasyondan).
    """
    if location:
        return [location.strip()]
    loc = get_location()
    koy = (loc.get("koy") or "").replace("Köyü", "").replace("köyü", "").strip()
    ilce, il = loc.get("ilce", "").strip(), loc.get("il", "").strip()
    cands = []
    if koy and ilce and il:
        cands.append(f"{koy},{ilce},{il},Turkey")
    if ilce and il:
        cands.append(f"{ilce},{il},Turkey")
    if il:
        cands.append(f"{il},Turkey")
    return cands or ["Edirne,Turkey"]


def get_weather_summary(location: str | None = None) -> str:
    env = os.environ.get("YERINDE_WEATHER_LOCATION")
    candidates = [env.strip()] if env else _query_candidates(location)
    last_err = ""
    for target in candidates:
        result = _fetch_one(target)
        if result:
            return result
        last_err = target
    return f"Hava durumu alınamadı ({last_err})."


def _fetch_one(target: str) -> str | None:
    try:
        response = requests.get(
            f"https://tr.wttr.in/{target}",
            params={"format": "j1", "lang": "tr"},
            timeout=10,
            headers={"User-Agent": "YERINDE CachyOS", "Accept-Language": "tr"},
        )
        response.raise_for_status()
        payload = response.json()
        current = (payload.get("current_condition") or [{}])[0]
        temp_c = current.get("temp_C")
        feels_like = current.get("FeelsLikeC")
        # Önce Türkçe alanını dene (lang_tr), yoksa İngilizceyi çevir
        weather_desc = ((current.get("lang_tr") or [{}])[0]).get("value", "")
        if not weather_desc:
            weather_desc = ((current.get("weatherDesc") or [{}])[0]).get("value", "")
            weather_desc = _translate_condition(weather_desc)
        humidity = current.get("humidity")

        parts = []
        if temp_c:
            parts.append(f"{temp_c} derece")
        if weather_desc:
            parts.append(weather_desc.lower())
        if feels_like and feels_like != temp_c:
            parts.append(f"hissedilen {feels_like} derece")
        if humidity:
            parts.append(f"nem yüzde {humidity}")

        if not parts:
            return None          # veri yok → bir üst kademeyi (ilçe/il) dene

        # Ekranda/seslendirmede KÖY adı görünsün (veri en yakın istasyondan gelse de).
        # Ham adları kullanıyoruz: büyük/küçük harf dönüşümü Türkçe'de bozulabiliyor.
        loc = get_location()
        yer = loc["koy"] or loc["ilce"] or loc["il"]
        alt = ", ".join(x for x in (loc["ilce"], loc["il"]) if x and x != yer)
        if alt:
            yer = f"{yer} ({alt})"
        return f"{yer} için hava durumu: " + ", ".join(parts) + "."
    except Exception:
        return None


# wttr.in bazen Türkçe alan döndürmezse İngilizce açıklamaları çevirmek için
_CONDITION_TR = {
    "sunny": "güneşli",
    "clear": "açık",
    "partly cloudy": "parçalı bulutlu",
    "cloudy": "bulutlu",
    "overcast": "kapalı",
    "mist": "puslu",
    "fog": "sisli",
    "freezing fog": "dondurucu sis",
    "patchy rain possible": "yer yer yağmur olası",
    "patchy rain nearby": "yakınlarda yer yer yağmur",
    "light rain": "hafif yağmur",
    "light rain shower": "hafif sağanak",
    "light drizzle": "hafif çisenti",
    "moderate rain": "orta şiddette yağmur",
    "heavy rain": "şiddetli yağmur",
    "torrential rain shower": "sel gibi sağanak",
    "thundery outbreaks possible": "gök gürültülü sağanak olası",
    "thunderstorm": "gök gürültülü fırtına",
    "patchy light rain with thunder": "gök gürültülü yer yer hafif yağmur",
    "moderate or heavy rain with thunder": "gök gürültülü orta/şiddetli yağmur",
    "patchy snow possible": "yer yer kar olası",
    "light snow": "hafif kar",
    "moderate snow": "orta şiddette kar",
    "heavy snow": "yoğun kar",
    "light snow showers": "hafif kar sağanağı",
    "blizzard": "kar fırtınası",
    "blowing snow": "tipi",
    "sleet": "sulu kar",
    "light sleet": "hafif sulu kar",
    "ice pellets": "buz taneleri",
    "windy": "rüzgarlı",
    "patchy light rain": "yer yer hafif yağmur",
    "patchy light drizzle": "yer yer hafif çisenti",
    "patchy light snow": "yer yer hafif kar",
    "patchy moderate snow": "yer yer orta şiddette kar",
    "patchy heavy snow": "yer yer yoğun kar",
    "patchy sleet possible": "yer yer sulu kar olası",
    "patchy freezing drizzle possible": "yer yer dondurucu çisenti olası",
    "moderate rain at times": "zaman zaman orta şiddette yağmur",
    "heavy rain at times": "zaman zaman şiddetli yağmur",
    "moderate or heavy rain shower": "orta veya şiddetli sağanak",
    "moderate or heavy snow showers": "orta veya yoğun kar sağanağı",
    "moderate or heavy sleet": "orta veya yoğun sulu kar",
    "moderate or heavy snow with thunder": "gök gürültülü orta/yoğun kar",
    "patchy light snow with thunder": "gök gürültülü yer yer hafif kar",
    "light freezing rain": "hafif dondurucu yağmur",
    "moderate or heavy freezing rain": "orta/yoğun dondurucu yağmur",
    "freezing drizzle": "dondurucu çisenti",
    "heavy freezing drizzle": "yoğun dondurucu çisenti",
    "light showers of ice pellets": "hafif buz tanesi sağanağı",
    "moderate or heavy showers of ice pellets": "orta/yoğun buz tanesi sağanağı",
    "drizzle": "çisenti",
    "rain": "yağmur",
    "snow": "kar",
    "haze": "hafif pus",
    "smoke": "dumanlı",
    "dust": "tozlu",
    "sand": "kum fırtınası",
    "tornado": "hortum",
    "hot": "çok sıcak",
    "cold": "soğuk",
}


def _translate_condition(desc: str) -> str:
    if not desc:
        return desc
    return _CONDITION_TR.get(desc.strip().lower(), desc)

# ══ 7 GÜNLÜK TAHMİN (Open-Meteo — API anahtarı gerekmez) ════════════════════
_WMO_TR = {
    0: "açık", 1: "az bulutlu", 2: "parçalı bulutlu", 3: "çok bulutlu",
    45: "sisli", 48: "kırağılı sis", 51: "hafif çisenti", 53: "çisenti",
    55: "yoğun çisenti", 56: "dondurucu çisenti", 57: "yoğun dondurucu çisenti",
    61: "hafif yağmur", 63: "yağmur", 65: "şiddetli yağmur",
    66: "dondurucu yağmur", 67: "şiddetli dondurucu yağmur",
    71: "hafif kar", 73: "kar", 75: "yoğun kar", 77: "kar taneleri",
    80: "hafif sağanak", 81: "sağanak", 82: "şiddetli sağanak",
    85: "hafif kar sağanağı", 86: "yoğun kar sağanağı",
    95: "gök gürültülü fırtına", 96: "dolulu fırtına", 99: "şiddetli dolulu fırtına",
}
_TR_GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
_coords_cache: dict | None = None


def _coords() -> tuple[float, float] | None:
    """Konumun enlem/boylamı: önce köy, sonra ilçe, sonra il aranır."""
    global _coords_cache
    if _coords_cache is not None:
        return _coords_cache.get("latlon")
    loc = get_location()
    koy = (loc.get("koy") or "").replace("Köyü", "").replace("köyü", "").strip()
    for name in (koy, loc.get("ilce", ""), loc.get("il", "")):
        if not name:
            continue
        try:
            r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                             params={"name": name, "count": 1, "language": "tr",
                                     "country": "TR"},
                             timeout=10)
            results = r.json().get("results") or []
            if results:
                latlon = (results[0]["latitude"], results[0]["longitude"])
                _coords_cache = {"latlon": latlon}
                return latlon
        except Exception:
            continue
    _coords_cache = {"latlon": None}
    return None


def get_forecast(days: int = 7) -> list[dict]:
    """
    [{'gun': 'Pzt', 'tarih': '14.07', 'max': 28, 'min': 16, 'durum': 'açık',
      'yagis': 10}, ...]  — veri alınamazsa boş liste.
    """
    days = max(1, min(int(days or 7), 7))
    latlon = _coords()
    if not latlon:
        return []
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": latlon[0], "longitude": latlon[1],
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                     "precipitation_probability_max",
            "timezone": "Europe/Istanbul", "forecast_days": days,
        }, timeout=12)
        d = r.json().get("daily") or {}
        out = []
        import datetime as _dt
        for i, iso in enumerate(d.get("time", [])[:days]):
            dt = _dt.date.fromisoformat(iso)
            out.append({
                "gun": _TR_GUNLER[dt.weekday()],
                "tarih": f"{dt.day:02d}.{dt.month:02d}",
                "max": round(d["temperature_2m_max"][i]),
                "min": round(d["temperature_2m_min"][i]),
                "durum": _WMO_TR.get(d["weather_code"][i], "—"),
                "yagis": d.get("precipitation_probability_max", [0] * days)[i] or 0,
            })
        return out
    except Exception:
        return []


def get_forecast_summary(days: int = 7) -> str:
    """Sesli okunacak/yazılacak 7 günlük özet."""
    rows = get_forecast(days)
    loc = get_location()
    yer = loc["koy"] or loc["ilce"] or loc["il"]
    if not rows:
        return f"{yer} için {days} günlük tahmin alınamadı."
    parts = [f"{r['gun']} {r['max']} derece, {r['durum']}" +
             (f", yağış ihtimali yüzde {r['yagis']}" if r["yagis"] >= 40 else "")
             for r in rows]
    return f"{yer} için {len(rows)} günlük hava durumu: " + "; ".join(parts) + "."
