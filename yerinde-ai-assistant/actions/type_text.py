"""
Sesle yazma — söylenen metni AKTİF penceredeki imlece yazar.

ÖNEMLİ (Türkçe karakter hatası): pyautogui.write() yalnızca ASCII/klavye
eşlemesi olan karakterleri yazabilir; 'ğ, ç, ş, ı, ö, ü, İ' gibi harfleri
SESSİZCE ATLAR ("hayalden gerçeğe" → "hayalden eree" gibi). Bu yüzden artık
metin PANOYA kopyalanıp Ctrl+V ile yapıştırılıyor — tüm Türkçe karakterler
harfi harfine korunur. Pano yöntemi başarısız olursa tuş tuş yazmaya düşülür.
"""

from __future__ import annotations

import platform
import subprocess
import time

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


def _set_clipboard(text: str) -> bool:
    """Metni panoya koyar (Türkçe karakterler dahil, kayıpsız)."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception:
        pass
    if _IS_WINDOWS:
        try:
            # UTF-8 güvenli: metni stdin'den okut
            p = subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command",
                 "$t = [Console]::In.ReadToEnd(); Set-Clipboard -Value $t"],
                input=text.encode("utf-8"), timeout=15,
                capture_output=True, creationflags=_CREATE_NO_WINDOW)
            return p.returncode == 0
        except Exception:
            return False
    import shutil
    for tool, cmd in (("wl-copy", ["wl-copy"]), ("xclip", ["xclip", "-selection", "clipboard"])):
        if shutil.which(tool):
            try:
                subprocess.run(cmd, input=text.encode("utf-8"), timeout=10, capture_output=True)
                return True
            except Exception:
                continue
    return False


def _is_wayland() -> bool:
    from core.input_backend import is_wayland
    return is_wayland()


def _paste() -> bool:
    """Ctrl+V gönderir. Wayland'de pyautogui/xdotool çalışmadığı için
    wtype (tercih) → ydotool kullanılır; diğer ortamlarda pyautogui."""
    if _is_wayland():
        import shutil
        if shutil.which("wtype"):
            try:
                r = subprocess.run(["wtype", "-M", "ctrl", "v", "-m", "ctrl"],
                                   timeout=10, capture_output=True)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        if shutil.which("ydotool"):
            try:
                # 29=CTRL, 47=V — input-event-codes.h
                r = subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],
                                   timeout=10, capture_output=True)
                if r.returncode == 0:
                    return True
            except Exception:
                pass
        return False
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.hotkey("ctrl", "v")
        return True
    except Exception:
        pass
    if _IS_WINDOWS:
        try:
            subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-Command",
                 "$w = New-Object -ComObject WScript.Shell; $w.SendKeys('^v')"],
                timeout=15, capture_output=True, creationflags=_CREATE_NO_WINDOW)
            return True
        except Exception:
            return False
    import shutil
    if shutil.which("xdotool"):
        try:
            subprocess.run(["xdotool", "key", "ctrl+v"], timeout=10, capture_output=True)
            return True
        except Exception:
            return False
    return False


def _type_wayland_ydotool(text: str) -> bool:
    """Wayland'de pano yolu başarısız olursa doğrudan ydotool type ile
    tuş tuş yazar (aifinal.md §2 → core/input_backend.py). ASCII dışı
    Türkçe karakterler ydotool'un keysym eşlemesiyle gönderilir; dönen
    çıkış kodu gerçek sonucu söyler."""
    from core.input_backend import ydotool_type
    ok, _err = ydotool_type(text)
    return ok


def type_text(text: str) -> str:
    if not text or not text.strip():
        return "Yazılacak metin belirtilmedi."
    text = text.strip()
    time.sleep(0.4)  # kullanıcı hedef pencereye dönebilsin

    # 1) PANO YOLU — Türkçe karakterleri kayıpsız yazar (tercih edilen)
    if _set_clipboard(text) and _paste():
        return f"Yazıldı: {text[:60]}{'…' if len(text) > 60 else ''}"

    # 2) Wayland yedeği: ydotool type (pano kullanılamadıysa)
    if _is_wayland():
        if _type_wayland_ydotool(text):
            return f"Yazıldı: {text[:60]}{'…' if len(text) > 60 else ''}"
        from core.input_backend import YDOTOOL_MISSING_TR
        return f"Yazılamadı: ydotool/uinput hazır değil.\n{YDOTOOL_MISSING_TR}"

    # 3) Yedek: tuş tuş yazma (X11/Windows; ASCII dışı harfler eksik çıkabilir)
    try:
        import pyautogui
        pyautogui.write(text, interval=0.02)
        ascii_disi = any(ord(c) > 127 for c in text)
        note = (" (Not: pano kullanılamadı; bazı Türkçe harfler eksik olabilir. "
                "Çözüm: pip install pyperclip)" if ascii_disi else "")
        return f"Yazıldı: {text[:60]}{'…' if len(text) > 60 else ''}{note}"
    except Exception as e:
        return f"Yazılamadı: {e} (pip install pyautogui pyperclip)"
