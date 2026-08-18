"""
actions/office_keys.py — OnlyOffice / API'siz ofis uygulamaları için klavye yedeği.

KRİTİK GÜVENLİK KURALI:
Klavye tuşları ODAKLANMIŞ pencereye gider. Eskiden ofis penceresi bulunamasa
bile tuş gönderiliyordu — bu durumda Esc/Alt+F4 YERINDE'nin KENDİ penceresine
gidiyor, asistan tam ekrandan çıkıyor ya da kapanıyordu.

Artık: önce ofis penceresi ARANIR ve ÖNE GETİRİLİR. Bulunamazsa HİÇBİR tuş
gönderilmez ve None döner (çağıran dürüst hata mesajı verir).

WAYLAND NOTU: wmctrl/xdotool pencere arama X11'e özeldir; Wayland'de (kimlik
doğrulaması gerektirmeyen, compositor'dan bağımsız evrensel bir pencere arama
protokolü olmadığından) sırasıyla Hyprland (hyprctl), Sway (swaymsg) ve KDE
Plasma (kdotool) denenir — screen_vision.py'nin ekran/pencere tespitinde
kullandığı aynı öncelik sırası. Bunların hiçbiri yoksa/eşleşmezse (ör. saf
GNOME Wayland) pencere GÜVENLE bulunamaz — bu durumda (KRİTİK GÜVENLİK KURALI
gereği) yine HİÇBİR tuş gönderilmez, dürüst hata döner.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time

from actions.mouse_control import _is_wayland

from actions.keyboard_control import press_key

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# Ofis pencerelerini tanıma
_WIN_PROCS = ["POWERPNT", "WINWORD", "EXCEL", "soffice", "DesktopEditors"]
_LINUX_PATTERNS = ["soffice", "libreoffice", "impress", "writer", "calc",
                   "onlyoffice", "desktopeditors"]

SLIDESHOW_KEYS = {
    "start": ("f5", "Sunum tam ekran başlatıldı"),
    "next":  ("right", "Sonraki slayt"),
    "prev":  ("left", "Önceki slayt"),
    "first": ("home", "İlk slayda dönüldü"),
    "end":   ("esc", "Sunum bitirildi"),
    "black": ("b", "Ekran karartıldı/açıldı"),
}

EDIT_KEYS = {
    "new_page": ("ctrl_m", "Yeni slayt eklendi"),
    "undo":     ("undo", "Son işlem geri alındı"),
    "delete":   ("delete", "Seçili slayt silindi"),
    "save":     ("save", "Kaydedildi"),
}


def _focus_office_window() -> bool:
    """Ofis penceresini öne getirir. Bulunamazsa False — tuş GÖNDERİLMEZ."""
    if _IS_WINDOWS:
        script = (
            "$w = New-Object -ComObject WScript.Shell; "
            "$procs = @('" + "','".join(_WIN_PROCS) + "'); "
            "$ok = $false; "
            "foreach ($p in $procs) { "
            "  $found = Get-Process -Name $p -ErrorAction SilentlyContinue | "
            "           Where-Object { $_.MainWindowTitle -ne '' } | Select-Object -First 1; "
            "  if ($found) { $null = $w.AppActivate($found.Id); $ok = $true; break } } ; "
            "if ($ok) { Write-Output 'OK' } else { Write-Output 'NO' }"
        )
        try:
            r = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                               capture_output=True, text=True, timeout=15,
                               creationflags=_CREATE_NO_WINDOW)
            return (r.stdout or "").strip().startswith("OK")
        except Exception:
            return False

    # Linux/Wayland: pencere arama+öne getirme evrensel değildir, compositor'a
    # özel IPC gerekir. Sırasıyla en yaygın üçü denenir (screen_vision.py'nin
    # pencere-başlığı tespitinde kullandığı KANITLANMIŞ öncelik sırasıyla
    # aynı): Hyprland → Sway → KDE Plasma (kdotool).
    if _is_wayland():
        # Hyprland (CachyOS'ta yaygın bir pencere yöneticisi): dispatch
        # focuswindow, verilen regex'e uyan İLK pencereyi öne getirir.
        if shutil.which("hyprctl"):
            regex = "(?i)(" + "|".join(_LINUX_PATTERNS) + ")"
            try:
                r = subprocess.run(["hyprctl", "dispatch", "focuswindow", f"title:{regex}"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and "ok" in (r.stdout or "").strip().lower():
                    return True
            except Exception:
                pass
        # Sway (wlroots tabanlı Wayland): kriter eşleşen pencereyi odaklar.
        if shutil.which("swaymsg"):
            regex = "(?i)(" + "|".join(_LINUX_PATTERNS) + ")"
            try:
                r = subprocess.run(["swaymsg", f'[title="{regex}"] focus'],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        # KDE Plasma: kdotool, KWin scripting üzerinden xdotool'un
        # search+windowactivate davranışını taklit eder — X11'e ihtiyaç duymaz.
        if shutil.which("kdotool"):
            for pat in _LINUX_PATTERNS:
                try:
                    r = subprocess.run(["kdotool", "search", "--name", pat],
                                       capture_output=True, text=True, timeout=5)
                    ids = [i for i in (r.stdout or "").split() if i.strip()]
                    if ids:
                        act = subprocess.run(["kdotool", "windowactivate", ids[-1]],
                                             timeout=5, capture_output=True, text=True)
                        if act.returncode == 0:
                            return True
                except Exception:
                    continue
        # Hiçbiri yok/eşleşmedi (ör. GNOME'da bu üç araç da yoksa) → pencere
        # GÜVENLE bulunamaz. KRİTİK GÜVENLİK KURALI: emin olamadığımızda tuş
        # GÖNDERİLMEZ.
        return False

    # Linux/X11: wmctrl ya da xdotool ile pencereyi bul + öne getir
    if shutil.which("wmctrl"):
        try:
            out = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True,
                                 timeout=5).stdout.lower()
            for line in out.splitlines():
                if any(p in line for p in _LINUX_PATTERNS):
                    wid = line.split()[0]
                    subprocess.run(["wmctrl", "-i", "-a", wid], timeout=5,
                                   capture_output=True)
                    return True
        except Exception:
            pass
    if shutil.which("xdotool"):
        for pat in _LINUX_PATTERNS:
            try:
                r = subprocess.run(["xdotool", "search", "--name", pat],
                                   capture_output=True, text=True, timeout=5)
                ids = [i for i in (r.stdout or "").split() if i.strip()]
                if ids:
                    subprocess.run(["xdotool", "windowactivate", ids[-1]],
                                   timeout=5, capture_output=True)
                    return True
            except Exception:
                continue
    return False


def _send(key: str, msg: str) -> str | None:
    if not _focus_office_window():
        return None          # ofis penceresi yok → ASLA tuş gönderme
    time.sleep(0.4)          # pencere öne gelsin
    r = press_key(key)
    if "basıldı" in r:
        return f"{msg} (klavye kısayoluyla — ofis penceresine gönderildi)."
    return None


def slideshow_keys(action: str) -> str | None:
    key, msg = SLIDESHOW_KEYS.get((action or "").lower(), (None, None))
    return _send(key, msg) if key else None


def edit_keys(action: str) -> str | None:
    key, msg = EDIT_KEYS.get((action or "").lower(), (None, None))
    return _send(key, msg) if key else None
