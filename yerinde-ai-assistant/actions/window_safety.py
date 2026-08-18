"""
actions/window_safety.py — Aktif (odaklanmış) pencerenin başlığını güvenli
şekilde tespit eder.

NEDEN VAR: Daha önce klavye yedeği, hiçbir pencere kontrolü yapmadan Esc/
Alt+F4 gönderiyordu — hedef pencere bulunamadığında bu tuşlar YERİNDE'nin
KENDİ penceresine gidiyor, asistan tam ekrandan çıkıyor ya da kapanıyordu.
Bu modül, "Alt+F4'ü güvenle gönderebilir miyim?" sorusunun cevabını verir:
aktif pencerenin YERİNDE'nin kendisi olmadığını doğrulamadan asla evet demez.
"""

from __future__ import annotations

import platform
import shutil
import subprocess

_IS_WINDOWS = platform.system() == "Windows"

# YERİNDE'nin kendi pencere başlığında geçen, OS'ler arası ortak imza.
# ui.py: self.root.title("Y.E.R.İ.N.D.E") — Türkçe büyük/küçük harf
# dönüşümündeki İ/ı sorunlarına karşı sadeleştirilmiş biçimde karşılaştırırız.
_SELF_MARKERS = ("yerinde", "y.e.r.i.n.d.e", "y.e.r.ı.n.d.e")


def _is_wayland() -> bool:
    import os
    return (not _IS_WINDOWS) and (
        bool(os.environ.get("WAYLAND_DISPLAY"))
        or os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland")


def active_window_title() -> str | None:
    """
    En üstteki (odaklanmış) pencerenin başlığını döner.
    Belirlenemezse (Wayland'de genelde güvenilir bir yol yoktur) None döner —
    çağıran taraf None'ı "güvenle bilemiyorum, riske girme" olarak yorumlamalı.
    """
    if _IS_WINDOWS:
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value or None
        except Exception:
            return None

    # Linux/Wayland: aktif pencere başlığını okumanın evrensel bir yolu yok —
    # compositor'a özel protokol/IPC gerekir. Sırasıyla en yaygın üçü denenir
    # (screen_vision.py'deki KANITLANMIŞ aynı yaklaşım, kod tekrarını önlemek
    # için değil ama bu dosyanın bağımsız/güvenlik-kritik kalması için burada
    # da uygulanır): Hyprland → Sway → KDE Plasma. Hiçbiri yoksa/eşleşmezse
    # (GNOME gibi) temkinli 'None' yoluna düşülür.
    if _is_wayland():
        # Hyprland (CachyOS'ta yaygın bir pencere yöneticisi)
        if shutil.which("hyprctl"):
            try:
                out = subprocess.run(["hyprctl", "activewindow", "-j"],
                                     capture_output=True, text=True, timeout=5).stdout
                import json
                title = (json.loads(out).get("title") or "").strip()
                if title:
                    return title
            except Exception:
                pass
        # Sway (wlroots tabanlı Wayland)
        if shutil.which("swaymsg"):
            try:
                out = subprocess.run(["swaymsg", "-t", "get_tree"],
                                     capture_output=True, text=True, timeout=5).stdout
                import json
                def _find_focused(node):
                    if node.get("focused"):
                        return node.get("name", "")
                    for child in node.get("nodes", []) + node.get("floating_nodes", []):
                        found = _find_focused(child)
                        if found:
                            return found
                    return ""
                title = _find_focused(json.loads(out)).strip()
                if title:
                    return title
            except Exception:
                pass
        # KDE Plasma: kdotool, KWin scripting üzerinden aktif pencere
        # başlığını okuyabilir.
        if shutil.which("kdotool"):
            try:
                r = subprocess.run(["kdotool", "getactivewindow", "getwindowname"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()
            except Exception:
                pass
        # Hiçbiri yok/eşleşmedi (ör. GNOME) → emin olamadığımızda temkinli
        # davranıp None dönüyoruz; ÜSTTEKİ KRİTİK GÜVENLİK KURALI gereği.
        return None

    # Linux/X11: xdotool ile güvenilir şekilde okunabilir.
    if shutil.which("xdotool"):
        try:
            r = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                               capture_output=True, text=True, timeout=5)
            return r.stdout.strip() or None if r.returncode == 0 else None
        except Exception:
            return None

    # Wayland: aktif pencere başlığını güvenilir okuyan evrensel bir CLI yok.
    # Emin olamadığımızda temkinli davranıp None dönüyoruz.
    return None


def is_yerinde_window(title: str | None) -> bool:
    """Verilen başlık YERİNDE'nin kendi penceresi mi?"""
    if not title:
        return False
    # ÖNEMLİ: Python'un .lower()'ı "İ"yi "i̇" (bileşik noktalı) yapıyor —
    # bu yüzden Türkçe harf normalizasyonunu KÜÇÜLTMEDEN ÖNCE yapıyoruz.
    t = title.replace("İ", "i").replace("ı", "i").replace("I", "i").lower()
    return any(marker in t for marker in _SELF_MARKERS)


def safe_to_send_altf4() -> tuple[bool, str]:
    """
    (güvenli_mi, sebep) döner. Yalnızca aktif pencere TESPİT EDİLEBİLİYORSA
    ve bu pencere YERİNDE'nin kendisi DEĞİLSE True döner. Belirsizlikte
    (Wayland gibi) daima False — "emin olamıyorum" diyerek tuş göndermeyi
    reddeder, kör bir tahminle YERİNDE'yi kapatma riskine girmez.
    """
    title = active_window_title()
    if title is None:
        return False, "aktif pencere tespit edilemedi (Wayland'de bu güvenli değil)"
    if is_yerinde_window(title):
        return False, "aktif pencere YERİNDE'nin kendisi — tuş gönderilmedi"
    return True, f"aktif pencere: {title}"
