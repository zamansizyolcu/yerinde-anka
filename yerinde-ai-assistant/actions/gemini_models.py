"""
Gemini API'den GERÇEK ZAMANLI SES (Live API) ile uyumlu modelleri listeler.
AYARLAR panelindeki 'GEMİNİ MODELİ' seçici bunu kullanır.

Not: main.py'deki client.aio.live.connect() SADECE 'bidiGenerateContent'
destekleyen modellerle çalışır — normal sohbet modelleri (ör. sade
"gemini-2.5-flash") bu listede OLMAMALI, aksi halde sesli bağlantı kurulamaz.
Bu yüzden Google'ın models.list() uç noktasından dönen supported_actions
alanına bakıp sadece Live API'yi destekleyenleri süzüyoruz.

ÖNEMLİ — ÇEVİRİYE ÖZEL MODELLER HARİÇ TUTULUYOR:
"gemini-3.5-live-translate-preview" gibi modeller teknik olarak
bidiGenerateContent destekliyor (yani Live API uyumlu görünüyor) ama bunlar
genel sohbet modeli DEĞİL — Google'ın kendi belgelerine göre bu model SADECE
gerçek zamanlı ses çevirisi için tasarlanmış ve "no tool use or system
instructions" (araç kullanımı ya da sistem talimatı YOK) kısıtlaması var.
YERİNDE her bağlantıda system_instruction + onlarca araç (function
declarations) gönderdiği için bu modelle bağlanmaya çalışmak sunucu
tarafında "1011 internal error" ile sonuçlanıyor. Bu yüzden ismi
'translate' geçen modeller listeden otomatik çıkarılıyor.

İnternet yoksa ya da API anahtarı henüz girilmemişse, bilinen (Temmuz 2026
itibarıyla güncel) Live API modellerinden oluşan sabit bir yedek liste
döndürülür — böylece seçici yine de boş kalmaz.
"""

from __future__ import annotations

# İnternet erişimi olmadan / API anahtarı geçersizken gösterilecek yedek liste.
# Google zaman zaman yeni Live modelleri çıkarıp eskilerini emekliye ayırıyor;
# bu yüzden mümkün olduğunda yukarıdaki dinamik liste (list_live_models)
# tercih edilir, bu sadece son çare yedektir.
# NOT: Çeviriye özel modeller (ör. gemini-3.5-live-translate-preview)
# BİLEREK burada YOK — yukarıdaki modül docstring'ine bakın.
FALLBACK_LIVE_MODELS = [
    "models/gemini-2.5-flash-native-audio-latest",
    "models/gemini-live-2.5-flash-preview-native-audio-09-2025",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "models/gemini-3.1-flash-live-preview",
]

# Ad bu alt dizgelerden birini içeriyorsa model dinamik listeden de çıkarılır
# (araç/sistem talimatı desteklemeyen özel amaçlı Live modelleri).
_EXCLUDED_NAME_SUBSTRINGS = ("translate",)


def list_live_models(api_key: str, timeout: float = 8.0) -> list[str]:
    """
    Gemini Live API (client.aio.live.connect) ile uyumlu VE bu uygulamanın
    ihtiyaç duyduğu araç/sistem-talimatı desteğine sahip modelleri döner.
    Başarısız olursa (ağ yok / anahtar geçersiz) boş liste döner — çağıran
    taraf bu durumda FALLBACK_LIVE_MODELS'e düşmeli.
    """
    api_key = (api_key or "").strip()
    if not api_key:
        return []
    try:
        from google import genai  # type: ignore[reportMissingImports]

        client = genai.Client(api_key=api_key)
        names: list[str] = []
        for m in client.models.list():
            actions = list(getattr(m, "supported_actions", None) or [])
            if "bidiGenerateContent" not in actions:
                continue
            name = getattr(m, "name", "") or ""
            if not name:
                continue
            if any(bad in name.lower() for bad in _EXCLUDED_NAME_SUBSTRINGS):
                continue
            names.append(name)
        return sorted(set(names))
    except Exception:
        return []


def list_live_models_with_fallback(api_key: str, timeout: float = 8.0) -> tuple[list[str], bool]:
    """
    (model_listesi, dinamik_mi) döner. dinamik_mi False ise sabit yedek
    listenin kullanıldığı, çağıran tarafın kullanıcıya belirtmesi gerektiği
    anlamına gelir (ör. "çevrimdışı/yedek liste gösteriliyor").
    """
    models = list_live_models(api_key, timeout=timeout)
    if models:
        return models, True
    return list(FALLBACK_LIVE_MODELS), False
