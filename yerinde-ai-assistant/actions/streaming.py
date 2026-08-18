"""
actions/streaming.py — Film/dizi servislerinde arama ve oynatma.

Disney+, Netflix, Prime Video, YouTube, Exxen, BluTV, Gain, TOD...
Servislerin resmi "şunu oynat" API'si yok; en sağlam yol arama sayfasını
doğrudan açmaktır (giriş yapmışsan tek tıkla oynatırsın). YouTube'da ise
ilk sonucu doğrudan oynatabiliyoruz.
"""

from __future__ import annotations

import platform
import subprocess
import urllib.parse
import webbrowser

_IS_WINDOWS = platform.system() == "Windows"

SERVICES = {
    "disney":       ("Disney+",      "https://www.disneyplus.com/search?q={q}"),
    "disney plus":  ("Disney+",      "https://www.disneyplus.com/search?q={q}"),
    "disney+":      ("Disney+",      "https://www.disneyplus.com/search?q={q}"),
    "netflix":      ("Netflix",      "https://www.netflix.com/search?q={q}"),
    "prime":        ("Prime Video",  "https://www.primevideo.com/search?phrase={q}"),
    "prime video":  ("Prime Video",  "https://www.primevideo.com/search?phrase={q}"),
    "youtube":      ("YouTube",      "https://www.youtube.com/results?search_query={q}"),
    "exxen":        ("Exxen",        "https://www.exxen.com/tr/arama?q={q}"),
    "blutv":        ("BluTV",        "https://www.blutv.com/arama?q={q}"),
    "gain":         ("Gain",         "https://www.gain.tv/arama?q={q}"),
    "tod":          ("TOD",          "https://www.todtv.com.tr/arama?q={q}"),
    "mubi":         ("MUBI",         "https://mubi.com/tr/search/{q}"),
}

# Masaüstü uygulaması varsa onu açmayı dene (Windows Mağaza sürümleri)
_APP_URIS = {
    "Disney+": "disneyplus://",
    "Netflix": "netflix://",
    "Prime Video": "primevideo://",
}


def _open(url: str) -> bool:
    try:
        if _IS_WINDOWS:
            import os
            os.startfile(url)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except Exception:
        try:
            return webbrowser.open(url)
        except Exception:
            return False


def play_stream(service: str, query: str = "") -> str:
    """
    service: disney | netflix | prime | youtube | exxen | blutv | gain | tod | mubi
    query  : film/dizi adı (boş bırakılırsa servisin ana sayfası açılır)
    """
    key = (service or "").lower().strip()
    if key not in SERVICES:
        return (f"'{service}' servisini tanımıyorum. Bildiklerim: "
                + ", ".join(sorted({v[0] for v in SERVICES.values()})))
    name, url_tpl = SERVICES[key]
    q = (query or "").strip()

    if not q:
        base = url_tpl.split("/search")[0].split("/arama")[0].split("/results")[0]
        return f"{name} açıldı." if _open(base) else f"{name} açılamadı."

    url = url_tpl.format(q=urllib.parse.quote(q))
    if not _open(url):
        return f"{name} açılamadı (tarayıcı/uygulama bulunamadı)."

    if name == "YouTube":
        return f"YouTube'da '{q}' aratıldı — ilk sonuca tıklaman yeterli."
    return (f"{name}'ta '{q}' aratıldı. Sonuç listesinden filmi seçebilirsin "
            "(servisler dışarıdan doğrudan oynatmaya izin vermiyor).")
