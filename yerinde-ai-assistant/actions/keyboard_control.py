"""
actions/keyboard_control.py — Sesle klavye tuşu gönderme.

Desteklenen tuşlar: esc, enter, delete, backspace, tab, alt+tab, super(win)+tab,
super(win) tek başına (Başlat menüsü / uygulama başlatıcı),
ctrl+tab / ctrl+shift+tab (sekmeler arası ileri/geri geçiş),
ok tuşları (yukarı/aşağı/sol/sağ), space, home, end, pageup/pagedown,
ctrl+c / ctrl+v / ctrl+z / ctrl+a.

Windows : pyautogui → yoksa PowerShell SendKeys
Linux   : pyautogui (X11) → yoksa xdotool → Wayland'de wtype (kısıtlı)
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import time

from core.input_backend import (
    EVDEV, YDOTOOL_MISSING_TR, run_ydotool, session_type, ydotool_key_seq,
)

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


def _session_type() -> str:
    """'wayland' | 'x11' | 'windows' — tespit core/input_backend.py'de."""
    return session_type()


# Wayland için wtype tuş adları
_WTYPE = {
    "esc": "Escape", "enter": "Return", "delete": "Delete", "backspace": "BackSpace",
    "tab": "Tab", "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "space": "space", "home": "Home", "end": "End", "pageup": "Prior",
    "pagedown": "Next", "f5": "F5", "b": "b",
    "f11": "F11", "f2": "F2", "capslock": "Caps_Lock", "win": "Super_L",
}
_WTYPE_MODS = {
    "alt_tab": (["alt"], "Tab"), "alt_f4": (["alt"], "F4"),
    "win_tab": (["logo"], "Tab"), "copy": (["ctrl"], "c"), "paste": (["ctrl"], "v"),
    "undo": (["ctrl"], "z"), "select_all": (["ctrl"], "a"), "save": (["ctrl"], "s"),
    "ctrl_m": (["ctrl"], "m"), "ctrl_l": (["ctrl"], "l"), "ctrl_e": (["ctrl"], "e"),
    "ctrl_r": (["ctrl"], "r"), "ctrl_j": (["ctrl"], "j"),
    "win_d": (["logo"], "d"), "cut": (["ctrl"], "x"), "redo": (["ctrl"], "y"),
    "parent_folder": (["alt"], "Up"),
    "ctrl_tab": (["ctrl"], "Tab"), "ctrl_shift_tab": (["ctrl", "shift"], "Tab"),
}


def _wayland_press(key: str, times: int) -> tuple[bool, str]:
    """wtype (tercih) → ydotool ile tuş gönderir.

    (başarı, hata_mesajı) döner. ÖNEMLİ DÜZELTME: subprocess.run'ın GERÇEK
    çıkış kodu (returncode) kontrol ediliyor — önceki sürüm exception
    fırlamadığı sürece hep 'başarılı' varsayıyordu; oysa wtype/ydotool
    (daemon çalışmıyor, /dev/uinput izni yok, soket yok, compositor sanal
    klavye protokolünü desteklemiyor vb. yüzden) sessizce returncode != 0
    ile başarısız olabiliyordu ve kullanıcı 'tuşa basıldı' yalanını
    görüyordu. wtype başarısız olursa (varsa) ydotool'a düşülür."""
    errors: list[str] = []

    if shutil.which("wtype"):
        cmd = None
        if key in _WTYPE_MODS:
            mods, k = _WTYPE_MODS[key]
            cmd = ["wtype"]
            for m in mods:
                cmd += ["-M", m]
            cmd += ["-k", k]
            for m in mods:
                cmd += ["-m", m]
        elif key in _WTYPE:
            cmd = ["wtype", "-k", _WTYPE[key]]

        if cmd is not None:
            try:
                ok_all, last_err = True, ""
                for _ in range(times):
                    r = subprocess.run(cmd, timeout=10, capture_output=True, text=True)
                    if r.returncode != 0:
                        ok_all = False
                        last_err = (r.stderr or r.stdout or "bilinmeyen hata").strip()
                        break
                    time.sleep(0.05)
                if ok_all:
                    return True, ""
                errors.append(f"wtype: {last_err}")
            except Exception as e:
                errors.append(f"wtype: {e}")

    if shutil.which("ydotool"):
        # aifinal.md §2: evdev kodları core/input_backend.py EVDEV haritasından
        # (enter=28 tab=15 esc=1 space=57 ctrl=29 alt=56 shift=42 super=125...).
        codes = {k: str(v) for k, v in EVDEV.items()}
        codes.update({"b": "48"})  # tek harf (evdev 48=B)
        combos = {"alt_tab": ["56:1", "15:1", "15:0", "56:0"],
                  "alt_f4": ["56:1", "62:1", "62:0", "56:0"],
                  "win_d": ["125:1", "32:1", "32:0", "125:0"],
                  "cut": ["29:1", "45:1", "45:0", "29:0"],
                  "redo": ["29:1", "21:1", "21:0", "29:0"],
                  "parent_folder": ["56:1", "103:1", "103:0", "56:0"],
                  "ctrl_tab": ["29:1", "15:1", "15:0", "29:0"],
                  "ctrl_shift_tab": ["29:1", "42:1", "15:1", "15:0", "42:0", "29:0"]}

        seq: list[str] | None = None
        if key in combos:
            seq = combos[key] * times
        elif key in codes:
            c = codes[key]
            seq = [f"{c}:1", f"{c}:0"] * times

        if seq is not None:
            ok, err = ydotool_key_seq(seq)
            if ok:
                return True, ""
            errors.append(f"ydotool: {err}")
        else:
            errors.append("ydotool: bu tuş için kod tanımlı değil")

    if not errors:
        errors.append("wtype/ydotool kurulu değil")
    return False, " | ".join(errors)


def _kglobalaccel_invoke(component: str, shortcut: str,
                         path: str | None = None) -> tuple[bool, str]:
    """final35 — kglobalaccel kısayolunu DBus'tan tetikler (genel yardımcı).
    Yalnız okuma değil ÇAĞIRMA yapar; dönüş 'method return' ise başarılıdır."""
    if not shutil.which("dbus-send"):
        return False, "dbus-send yok"
    try:
        r = subprocess.run(
            ["dbus-send", "--session", "--print-reply",
             "--dest=org.kde.kglobalaccel",
             path or f"/component/{component}",
             "org.kde.kglobalaccel.Component.invokeShortcut",
             f'string:{shortcut}'],
            timeout=5, capture_output=True, text=True)
        if r.returncode == 0 and "method return" in r.stdout:
            return True, ""
        return False, (r.stderr or r.stdout or "bilinmeyen hata").strip()
    except Exception as e:
        return False, str(e)


# final35: "masaüstünü göster" dbus yedeği (final33) TÜM pencere yönetimi
# kısayollarına genelleştirildi. Kısayol adları bu KDE 6.29 hostta
# allShortcutInfos ile DOĞRULANDI ("Walk Through Windows", "Window Close",
# "Overview" aynen bu adlarla kayıtlı). win_d ayrı ele alınır (aşağıda).
_KGLOBALACCEL = {
    "alt_tab": ("kwin", "Walk Through Windows"),
    "alt_f4":  ("kwin", "Window Close"),
    "win_tab": ("kwin", "Overview"),
    # final36: "başlat menüsünü aç" — plasmashell launcher (canlı invoke
    # ile doğrulandı: method return)
    "win":     ("plasmashell", "activate application launcher"),
}


def _show_desktop_dbus() -> tuple[bool, str]:
    """final33 §5 — 'masaüstünü göster' dbus yedeği (ydotool yoksa/devrede
    değilse). KDE kglobalaccel kısayolunu DBus'tan tetikler; pencereler
    ydotool/uinput izinleri OLMADAN iner. Önce doğrulanmış /component/kwin
    yolu, ardından /desktop tahmini denenir (her ikisi de zararsızdır)."""
    ok, err = _kglobalaccel_invoke("kwin", "Show Desktop")
    if ok:
        return True, ""
    ok2, err2 = _kglobalaccel_invoke("kwin", "Show Desktop", path="/desktop")
    return ok2, (err2 if not ok2 else "")

# Kanonik tuş adı → (pyautogui tuşları, xdotool tuşu, SendKeys kodu)
KEYS = {
    "esc":       (["esc"],                 "Escape",       "{ESC}"),
    "enter":     (["enter"],               "Return",       "{ENTER}"),
    "delete":    (["delete"],              "Delete",       "{DEL}"),
    "backspace": (["backspace"],           "BackSpace",    "{BACKSPACE}"),
    "tab":       (["tab"],                 "Tab",          "{TAB}"),
    "alt_tab":   (["alt", "tab"],          "alt+Tab",      "%{TAB}"),
    "alt_f4":    (["alt", "f4"],           "alt+F4",       "%{F4}"),
    "win_tab":   (["win", "tab"],          "super+Tab",    None),
    "up":        (["up"],                  "Up",           "{UP}"),
    "down":      (["down"],                "Down",         "{DOWN}"),
    "left":      (["left"],                "Left",         "{LEFT}"),
    "right":     (["right"],               "Right",        "{RIGHT}"),
    "space":     (["space"],               "space",        " "),
    "home":      (["home"],                "Home",         "{HOME}"),
    "end":       (["end"],                 "End",          "{END}"),
    "pageup":    (["pageup"],              "Page_Up",      "{PGUP}"),
    "pagedown":  (["pagedown"],            "Page_Down",    "{PGDN}"),
    "copy":      (["ctrl", "c"],           "ctrl+c",       "^c"),
    "paste":     (["ctrl", "v"],           "ctrl+v",       "^v"),
    "undo":      (["ctrl", "z"],           "ctrl+z",       "^z"),
    "select_all":(["ctrl", "a"],           "ctrl+a",       "^a"),
    "f5":        (["f5"],                  "F5",           "{F5}"),
    "ctrl_m":    (["ctrl", "m"],           "ctrl+m",       "^m"),
    "b":         (["b"],                   "b",            "b"),
    "save":      (["ctrl", "s"],           "ctrl+s",       "^s"),
    "ctrl_l":    (["ctrl", "l"],           "ctrl+l",       "^l"),
    "ctrl_e":    (["ctrl", "e"],           "ctrl+e",       "^e"),
    "ctrl_r":    (["ctrl", "r"],           "ctrl+r",       "^r"),
    "ctrl_j":    (["ctrl", "j"],           "ctrl+j",       "^j"),
    "win_d":     (["win", "d"],            "super+d",      None),
    "win":       (["win"],                 "super",        None),
    "f11":       (["f11"],                 "F11",          "{F11}"),
    "f2":        (["f2"],                  "F2",           "{F2}"),
    "cut":       (["ctrl", "x"],           "ctrl+x",       "^x"),
    "redo":      (["ctrl", "y"],           "ctrl+y",       "^y"),
    "capslock":  (["capslock"],            "Caps_Lock",    "{CAPSLOCK}"),
    "parent_folder": (["alt", "up"],       "alt+Up",       "%{UP}"),
    "ctrl_tab":       (["ctrl", "tab"],          "ctrl+Tab",       "^{TAB}"),
    "ctrl_shift_tab": (["ctrl", "shift", "tab"], "ctrl+shift+Tab", "^+{TAB}"),
}

_TR = {
    "esc": "Escape", "enter": "Enter", "delete": "Delete", "backspace": "Geri sil",
    "tab": "Tab", "alt_tab": "Alt+Tab", "win_tab": "Windows+Tab",
    "up": "Yukarı ok", "down": "Aşağı ok", "left": "Sol ok", "right": "Sağ ok",
    "space": "Boşluk", "home": "Home", "end": "End", "pageup": "Page Up",
    "pagedown": "Page Down", "copy": "Kopyala", "paste": "Yapıştır",
    "undo": "Geri al", "select_all": "Tümünü seç",
    "f5": "F5", "ctrl_m": "Ctrl+M", "b": "B", "save": "Kaydet",
    "ctrl_l": "Sola hizala", "ctrl_e": "Ortala",
    "ctrl_r": "Sağa hizala", "ctrl_j": "İki yana yasla",
    "win_d": "Masaüstünü göster", "win": "Windows / Başlat menüsü",
    "f11": "F11 (tam ekran)", "f2": "F2 (yeniden adlandır)",
    "cut": "Kes", "redo": "İleri al", "capslock": "Büyük harf kilidi",
    "parent_folder": "Üst klasöre git",
    "ctrl_tab": "Ctrl+Tab (sonraki sekme)", "ctrl_shift_tab": "Ctrl+Shift+Tab (önceki sekme)",
}


def press_key(key: str, times: int = 1) -> str:
    key = (key or "").lower().strip()
    if key not in KEYS:
        return f"'{key}' tuşunu tanımıyorum. Örnek: esc, enter, alt tab, yukarı ok, sil."
    times = max(1, min(int(times or 1), 20))
    combo, xdo, sendkeys = KEYS[key]
    label = _TR.get(key, key)

    time.sleep(0.25)  # kullanıcı hedef pencereye dönebilsin

    session = _session_type()

    # 0) WAYLAND: pyautogui/xdotool ÇALIŞMAZ (sessizce başarısız olur) →
    #    doğrudan wtype/ydotool kullan; yoksa DÜRÜST hata ver.
    if session == "wayland":
        ok, err = _wayland_press(key, times)
        if ok:
            return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
        # final35 zinciri (yalnız eylem katmanı; mesaj katmanı dokunulmaz):
        # 2) ydotool YOKSA/BAŞARISIZSA → KDE kglobalaccel dbus yedeği.
        #    win_d: final33'te kanıtlanmış "Show Desktop" yolu;
        #    diğer pencere kısayolları: _KGLOBALACCEL haritası.
        if key == "win_d":
            ok2, err2 = _show_desktop_dbus()
            if ok2:
                return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
            err = f"{err} | {err2}"
        elif key in _KGLOBALACCEL:
            ok2, err2 = _kglobalaccel_invoke(*_KGLOBALACCEL[key])
            if ok2:
                return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
            err = f"{err} | {err2}"
        # 3) ikisi de yoksa ESKİ Türkçe mesaj
        return (f"{label} tuşu GÖNDERİLEMEDİ (Wayland). Gerçek hata: {err}\n"
                f"{YDOTOOL_MISSING_TR}")

    # 1) pyautogui (Windows / X11)
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        for _ in range(times):
            if len(combo) == 1:
                pyautogui.press(combo[0])
            else:
                pyautogui.hotkey(*combo)
            time.sleep(0.05)
        return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
    except ImportError:
        pass
    except Exception:
        pass  # Wayland'de patlayabilir → aşağıdaki yedeklere düş

    # 2) Linux: xdotool
    if not _IS_WINDOWS and shutil.which("xdotool"):
        try:
            subprocess.run(["xdotool", "key", "--repeat", str(times), "--delay", "60", xdo],
                           timeout=10, capture_output=True)
            return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
        except Exception as e:
            return f"Tuş gönderilemedi: {e}"

    # 3) Windows: PowerShell SendKeys
    if _IS_WINDOWS and sendkeys:
        try:
            script = ("$w = New-Object -ComObject WScript.Shell; "
                      + " ".join([f"$w.SendKeys('{sendkeys}'); Start-Sleep -Milliseconds 60;"] * times))
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=15, capture_output=True,
                           creationflags=_CREATE_NO_WINDOW)
            return f"{label} tuşuna basıldı." + (f" ({times}×)" if times > 1 else "")
        except Exception as e:
            return f"Tuş gönderilemedi: {e}"

    if key in ("win_tab", "win") and _IS_WINDOWS:
        return f"{label} için pyautogui gerekli: pip install pyautogui"
    return ("Klavye aracı yok. Windows/Linux: pip install pyautogui "
            "(Linux'ta ayrıca: sudo apt install xdotool)")
