"""
core/input_backend.py — Birleşik klavye/fare/metin girdi arka ucu (aifinal.md §2).

Oturum tespiti: XDG_SESSION_TYPE / WAYLAND_DISPLAY
  → 'wayland' | 'x11' | 'windows'

Wayland : ydotool (uinput tabanlı; compositor'dan bağımsız EN GÜVENİLİR yol —
          wtype gibi sanal klavye protokolü gerektirmez)
X11     : xdotool (yol AYNEN korunur)
Windows : bu modül yalnızca Linux içindir; Windows yolları eylem dosyalarında

Evdev tuş kodları (linux/input-event-codes.h):
  enter=28  tab=15  esc=1  space=57  ctrl=29  alt=56  shift=42  super=125
  mute=113  vol+=115  vol-=114  play=164
Fare düğmeleri: 0xC0=sol  0xC1=sağ  0xC2=orta

ydotool YOKSA çağıran taraf Türkçe yol gösterici mesajı verir
(YDOTOOL_MISSING_TR) — eski sabit "çalışmamaktadır" hatası kullanılmaz.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess

_IS_WINDOWS = platform.system() == "Windows"


# ══ Oturum tespiti ══════════════════════════════════════════════════════════
def session_type() -> str:
    """'wayland' | 'x11' | 'windows'."""
    if _IS_WINDOWS:
        return "windows"
    if os.environ.get("WAYLAND_DISPLAY") or \
            os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
        return "wayland"
    return "x11"


def is_wayland() -> bool:
    return session_type() == "wayland"


def ydotool_available() -> bool:
    return (not _IS_WINDOWS) and bool(shutil.which("ydotool"))


YDOTOOL_MISSING_TR = (
    "Wayland'de klavye/fare kontrolü için ydotool gerekiyor. Kurulum:\n"
    "  sudo pacman -S ydotool\n"
    "  sudo systemctl enable --now ydotoold\n"
    "  sudo usermod -aG uinput,input $USER   (sonra OTURUMU YENİDEN AÇ)\n"
    "Kontrol: systemctl status ydotoold  •  ls /dev/uinput  •  groups $USER"
)


# ══ Evdev kodları ═══════════════════════════════════════════════════════════
EVDEV = {
    "esc": 1, "tab": 15, "enter": 28, "ctrl": 29, "shift": 42,
    "alt": 56, "space": 57, "capslock": 58, "f2": 60, "f5": 63,
    "up": 103, "left": 105, "right": 106, "down": 108, "delete": 111,
    "mute": 113, "voldown": 114, "volup": 115, "f11": 87,
    "play": 164, "pause": 164,  # medya tuşları (play/pause aynı evdev kodu)
    "super": 125, "backspace": 14, "home": 102, "end": 107,
    "pageup": 104, "pagedown": 109,
}

# Fare düğmeleri (hex gösterim aifinal.md §2 ile aynı: 0xC0/0xC1/0xC2)
BTN_LEFT, BTN_RIGHT, BTN_MIDDLE = 0xC0, 0xC1, 0xC2


# ══ Temel yürütücü ══════════════════════════════════════════════════════════
def run_ydotool(args: list[str], timeout: int = 10) -> tuple[bool, str]:
    """ydotool'u gerçek çıkış koduyla çalıştırır → (başarı, hata).

    Soket emniyeti: YDOTOOL_SOCKET ayarlı DEĞİLSE /run/ydotool.socket
    varsayılır (yerinde-anka canlı/kurulu sistemde ydotoold sistem servisi
    orada dinler, 0660 + uinput grubu). Kullanıcı servisi kuran kurulumlar
    kendi env'ini zaten set eder — bu yalnız eksik durumda güvenliği sağlar.
    Klavye VE fare tüm ydotool çağrları bu fonksiyondan geçer."""
    if not ydotool_available():
        return False, YDOTOOL_MISSING_TR
    env = dict(os.environ)
    env.setdefault("YDOTOOL_SOCKET", "/run/ydotool.socket")
    try:
        r = subprocess.run(["ydotool"] + args, timeout=timeout,
                           capture_output=True, text=True, env=env)
        ok = r.returncode == 0
        return ok, ("" if ok else (r.stderr or r.stdout or "bilinmeyen hata").strip())
    except FileNotFoundError:
        return False, "ydotool bulunamadı"
    except Exception as e:
        return False, str(e)


# ══ Klavye ══════════════════════════════════════════════════════════════════
def ydotool_key(code: int, times: int = 1) -> tuple[bool, str]:
    """Tuşu evdev koduyla basıp bırakır: ydotool key {c}:1 {c}:0."""
    return ydotool_key_seq([f"{code}:1", f"{code}:0"] * max(1, times))


def ydotool_key_seq(seq: list[str]) -> tuple[bool, str]:
    """"kod:1/kod:0" dizisini tek ydotool key çağrısında gönderir
    (kombolar için: örn. alt+tab → 56:1 15:1 15:0 56:0)."""
    if not seq:
        return False, "boş tuş dizisi"
    return run_ydotool(["key"] + seq)


# ══ Metin ═══════════════════════════════════════════════════════════════════
def ydotool_type(text: str, key_delay_ms: int = 40) -> tuple[bool, str]:
    """Metni tuş tuş yazar (pano kullanılamadığında yedek)."""
    if not text:
        return False, "boş metin"
    return run_ydotool(["type", "--key-delay", str(key_delay_ms), text],
                       timeout=max(10, len(text)))


def xdotool_type(text: str) -> bool:
    """X11 yolu (aynen korunur): xdotool type."""
    if _IS_WINDOWS or not shutil.which("xdotool"):
        return False
    try:
        r = subprocess.run(["xdotool", "type", "--delay", "40", "--", text],
                           timeout=max(10, len(text)), capture_output=True)
        return r.returncode == 0
    except Exception:
        return False


def type_text_backend(text: str) -> tuple[bool, str]:
    """Oturuma göre metin yazar: wayland+ydotool → ydotool type; değilse xdotool."""
    if is_wayland():
        if not ydotool_available():
            return False, YDOTOOL_MISSING_TR
        return ydotool_type(text)
    ok = xdotool_type(text)
    return (True, "") if ok else (False, "xdotool çalışmadı (kurulu değil mi?)")


# ══ Fare ════════════════════════════════════════════════════════════════════
def ydotool_click(button: int = BTN_LEFT) -> tuple[bool, str]:
    """Düğmeye basıp bırakır (0xC0=sol, 0xC1=sağ, 0xC2=orta)."""
    return run_ydotool(["key", f"{button}:1", f"{button}:0"])


def ydotool_move_relative(dx: int, dy: int) -> tuple[bool, str]:
    """Bağıl fare hareketi (--absolute BİLİNEN şekilde bozuk olabilir:
    bkz. mouse_control.py dosya başlığı; yön komutlarında bağıl kullan)."""
    return run_ydotool(["mousemove", "-x", str(dx), "-y", str(dy)])


def ydotool_move_absolute(x: int, y: int) -> tuple[bool, str]:
    return run_ydotool(["mousemove", "--absolute", "-x", str(x), "-y", str(y)])


def ydotool_scroll(amount: int) -> tuple[bool, str]:
    """amount > 0: yukarı; amount < 0: aşağı."""
    ok, err = run_ydotool(["wheel", "--", str(amount)])
    if ok:
        return True, ""
    return False, f"ydotool wheel desteklenmiyor olabilir ({err}) — ydotool'u güncelle"
