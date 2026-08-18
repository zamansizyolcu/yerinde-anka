"""
Medya oynatma — CachyOS (Arch Linux) için YouTube, Spotify URI scheme.
Apple Music desteği bu sürümde bulunmamaktadır.
"""

from __future__ import annotations

import shutil
import subprocess
import urllib.parse

from actions.browser import browser_control

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def _copy_to_clipboard(text: str) -> tuple[bool, str]:
    if HAS_PYPERCLIP:
        try:
            pyperclip.copy(text)
            return True, "ok"
        except Exception as exc:
            return False, f"Panoya kopyalanamadı: {exc}"
    # wl-copy (Wayland) / xclip (X11) yedeği
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), check=True, timeout=5)
                return True, "ok"
            except Exception as exc:
                return False, f"Panoya kopyalanamadı: {exc}"
    return False, "Panoya kopyalama aracı bulunamadı (wl-copy/xclip kur)."


def _spotify_installed() -> bool:
    return shutil.which("spotify") is not None


def _play_youtube(query: str) -> str:
    return browser_control("play_youtube", query=query)


def _play_spotify(query: str, autoplay: bool = True) -> str:
    encoded_query = urllib.parse.quote(query.strip())
    search_url = f"spotify:search:{encoded_query}"
    try:
        if _spotify_installed():
            subprocess.Popen(
                ["spotify", "--uri", search_url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        elif shutil.which("xdg-open"):
            subprocess.run(["xdg-open", search_url], timeout=10)
        else:
            return "Spotify açılamadı: ne 'spotify' ne de 'xdg-open' bulunamadı."
    except Exception as exc:
        return f"Spotify açılamadı: {exc}"
    return f"Spotify'da '{query}' araması açıldı."


def play_media(query: str, provider: str = "auto", autoplay: bool = True) -> str:
    if not query or not query.strip():
        return "Çalınacak içerik belirtilmedi."

    normalized_provider = (provider or "auto").strip().lower()
    if normalized_provider in {"yt", "youtube music"}:
        normalized_provider = "youtube"
    elif normalized_provider in {"apple music", "music", "apple_music"}:
        # Apple Music bu sürümde yok, YouTube'a yönlendir
        return _play_youtube(query)

    if normalized_provider == "spotify":
        return _play_spotify(query, autoplay=autoplay)
    if normalized_provider == "youtube":
        return _play_youtube(query)

    # auto: Spotify URI dene, yoksa YouTube
    result = _play_spotify(query, autoplay=autoplay)
    if "açılamadı" not in result:
        return result
    return _play_youtube(query)
