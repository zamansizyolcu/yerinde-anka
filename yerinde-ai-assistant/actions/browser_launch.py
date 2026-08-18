"""
actions/browser_launch.py — Atölye araçlarının (3B Tasarım, Robot, YERİNDE
Kodlama, Resim & PDF, Akış Şeması, Satranç, Çin Daması, Çarkıfelek, Pico
Devre, Bilişim-Robotik, Robotik Simülatör, Donanım, Video Atölyesi vb.)
HER ZAMAN AYNI tarayıcıda açılmasını sağlayan tek, paylaşılan yardımcı.

NEDEN GEREKLİ:
Bu araçların hepsi eskiden doğrudan os.startfile(url) (Windows) /
xdg-open (Linux) kullanıyordu. Bu çağrılar işletim sisteminin O AN
"varsayılan tarayıcı" olarak neyi işaretlediğine güvenir. Edge, bir dosyayı
bir kere "Edge ile aç" dedikten (ya da bazen bir Windows güncellemesinden)
sonra kullanıcıya sormadan kendini varsayılan tarayıcı yapabiliyor — bu
olduğu anda TÜM atölye araçları sessizce Chrome'dan Edge'e kayıyordu
("chrome'da güzel açılıyordu, Edge'e geçti" şikayetinin kök nedeni budur).

Bu modül, Windows'un o anki varsayılanına güvenmek yerine tercih edilen
tarayıcıyı (varsayılan: Chrome — app_config.py'deki 'preferred_browser')
KENDİ YÜKLÜ OLDUĞU YOLDAN doğrudan başlatır; böylece Windows'un varsayılan
tarayıcı ayarı sonradan ne şekilde değişirse değişsin sonuç hep aynı kalır.
Tercih edilen tarayıcı hiç kurulu değilse sessizce işletim sisteminin
varsayılanına (eski davranış) düşer — hiçbir zaman hata fırlatmaz.

Kullanım (her atölye dosyasında aynı desen):
    from actions.browser_launch import open_tool_url
    ...
    open_tool_url(url)   # url: file:// ya da http(s):// — os.startfile(url) yerine
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from app_config import get_app_config_value

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


def _windows_candidates(exe_name: str, subfolder: str) -> list[Path]:
    """%ProgramFiles%, %ProgramFiles(x86)%, %LocalAppData% altındaki olası kurulum yolları."""
    cands = []
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LocalAppData"):
        root = os.environ.get(env)
        if root:
            cands.append(Path(root) / subfolder / exe_name)
    return cands


def _find_chrome() -> str | None:
    if not _IS_WINDOWS:
        for name in ("google-chrome", "chrome", "chromium", "chromium-browser"):
            found = shutil.which(name)
            if found:
                return found
        return None
    for cand in _windows_candidates("chrome.exe", str(Path("Google") / "Chrome" / "Application")):
        if cand.exists():
            return str(cand)
    return shutil.which("chrome")


def _find_edge() -> str | None:
    if not _IS_WINDOWS:
        return shutil.which("microsoft-edge") or shutil.which("microsoft-edge-stable")
    for cand in _windows_candidates("msedge.exe", str(Path("Microsoft") / "Edge" / "Application")):
        if cand.exists():
            return str(cand)
    return shutil.which("msedge")


def _preferred_binary() -> str | None:
    """Ayarlardaki tercihe göre (varsayılan: Chrome) kurulu ilk tarayıcı ikilisini döner."""
    choice = str(get_app_config_value("preferred_browser", "chrome") or "chrome").lower()
    if choice == "system":
        return None  # kullanıcı bilinçli olarak işletim sistemi varsayılanını istiyor
    order = ("edge", "chrome") if choice == "edge" else ("chrome", "edge")
    for name in order:
        binary = _find_chrome() if name == "chrome" else _find_edge()
        if binary:
            return binary
    return None


def open_tool_url(url: str) -> None:
    """
    Bir atölye aracının URL'sini (file:// ya da http(s)://) tercih edilen
    tarayıcıda açar. Tercih edilen tarayıcı bulunamazsa ya da başlatılamazsa
    sessizce işletim sisteminin varsayılanına (os.startfile / xdg-open)
    düşer — hiçbir zaman hata fırlatmaz.
    """
    binary = _preferred_binary()
    if binary:
        try:
            subprocess.Popen([binary, url], creationflags=_CREATE_NO_WINDOW,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception:
            pass  # ikili bulundu ama başlatılamadı → sistem varsayılanına düş

    if _IS_WINDOWS:
        os.startfile(url)  # noqa: S606
    else:
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, start_new_session=True)
