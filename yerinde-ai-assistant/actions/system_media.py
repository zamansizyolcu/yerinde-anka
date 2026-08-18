"""
actions/system_media.py — Sistem sesi, medya (çal/durdur), Ctrl+S ve
asistanı kapatma. Tek dosya, platform-farkındalıklı (Windows/Linux).

WAYLAND NOTU: pactl/amixer (ses) ve playerctl (medya) zaten görüntü
sunucusundan (X11/Wayland) bağımsız çalışır — PipeWire/PulseAudio ve MPRIS
D-Bus üzerinden konuşurlar, bu yüzden bu iki araç kuruluysa (CachyOS/Pardus'ta
varsayılan) ses/medya kontrolü Wayland'de zaten sorunsuzdur. Yalnızca bu
araçlar YOKSA devreye giren xdotool yedeği X11'e özeldi; Wayland'de aynı
yedek artık ydotool/wtype ile deneniyor (keyboard_control.py'deki KANITLANMIŞ
yaklaşımla aynı: gerçek returncode kontrol edilir, sessiz 'başarılı' yalanı
söylenmez).
"""

from __future__ import annotations

import platform
import shutil
import subprocess

from actions.mouse_control import _is_wayland

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# Windows sanal tuş kodları (keybd_event)
_VK = {"mute": 0xAD, "down": 0xAE, "up": 0xAF,
       "playpause": 0xB3, "stop": 0xB2, "next": 0xB0, "prev": 0xB1}

# Linux evdev tuş kodları (input-event-codes.h) — ydotool bunları /dev/uinput
# üzerinden GERÇEK medya tuşu olarak gönderir; compositor'dan bağımsızdır.
_EVDEV = {"mute": "113", "up": "115", "down": "114",
          "playpause": "164", "stop": "128", "next": "163", "prev": "165"}
# wtype için xkbcommon XF86 keysym adları (bazı compositor'larda desteklenir;
# ydotool başarısız olursa ikinci deneme olarak kullanılır).
_WTYPE_XF86 = {"mute": "XF86AudioMute", "up": "XF86AudioRaiseVolume",
               "down": "XF86AudioLowerVolume", "playpause": "XF86AudioPlay",
               "stop": "XF86AudioStop", "next": "XF86AudioNext",
               "prev": "XF86AudioPrev"}


def _win_send_vk(vk: int, times: int = 1) -> bool:
    script = (
        "Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;"
        "public class K{[DllImport(\"user32.dll\")]public static extern void keybd_event("
        "byte b,byte s,uint f,UIntPtr e);}' ; "
        + " ".join(f"[K]::keybd_event({vk},0,0,[UIntPtr]::Zero);"
                   f"[K]::keybd_event({vk},0,2,[UIntPtr]::Zero);" for _ in range(times))
    )
    try:
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                       timeout=10, capture_output=True, creationflags=_CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


def _send_xf86_key(name: str) -> tuple[bool, str]:
    """ydotool (öncelikli, evdev kodu) → wtype (XF86 keysym) ile ses/medya
    tuşu gönderir. X11'de bu hiç çağrılmaz (pactl/amixer/xdotool zaten
    yeterli); yalnızca Wayland'de VEYA pactl/amixer/playerctl hiçbiri
    kuruluysa yedek olarak devreye girer. (başarı, hata) döner — sessiz
    'başarılı' yalanı söylemez, gerçek returncode kontrol edilir."""
    errors = []
    if shutil.which("ydotool") and name in _EVDEV:
        code = _EVDEV[name]
        try:
            r = subprocess.run(["ydotool", "key", f"{code}:1", f"{code}:0"],
                               timeout=5, capture_output=True, text=True)
            if r.returncode == 0:
                return True, ""
            errors.append(f"ydotool: {(r.stderr or r.stdout or '').strip()}")
        except Exception as e:
            errors.append(f"ydotool: {e}")
    if shutil.which("wtype") and name in _WTYPE_XF86:
        try:
            r = subprocess.run(["wtype", "-k", _WTYPE_XF86[name]],
                               timeout=5, capture_output=True, text=True)
            if r.returncode == 0:
                return True, ""
            errors.append(f"wtype: {(r.stderr or r.stdout or '').strip()}")
        except Exception as e:
            errors.append(f"wtype: {e}")
    if not errors:
        errors.append("ydotool/wtype kurulu değil")
    return False, " | ".join(errors)


def system_volume(action: str, step: int = 10) -> str:
    """action: up | down | mute — sistem ses düzeyini değiştirir."""
    action = (action or "").lower().strip()
    if action not in ("up", "down", "mute"):
        return "Geçersiz ses komutu (up/down/mute)."

    if _IS_WINDOWS:
        # Her medya-tuşu basışı ~%2 → step/2 basış
        ok = _win_send_vk(_VK["mute" if action == "mute" else action],
                          times=1 if action == "mute" else max(1, step // 2))
        return {"up": f"Ses %{step} artırıldı.", "down": f"Ses %{step} kısıldı.",
                "mute": "Ses kapatıldı/açıldı."}[action] if ok else "Ses değiştirilemedi."

    msg = {"up": f"Ses %{step} artırıldı.", "down": f"Ses %{step} kısıldı.",
           "mute": "Ses kapatıldı/açıldı."}[action]

    # Linux: pactl → amixer (ikisi de X11/Wayland'den bağımsız, PipeWire/ALSA
    # ile doğrudan konuşur) → yoksa (nadir) ydotool/wtype → xdotool (yalnızca X11)
    if shutil.which("pactl"):
        cmd = {"up": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"+{step}%"],
               "down": ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"-{step}%"],
               "mute": ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]}[action]
        try:
            r = subprocess.run(cmd, timeout=5, capture_output=True, text=True)
            return msg if r.returncode == 0 else f"Ses değiştirilemedi: {(r.stderr or '').strip()}"
        except Exception as e:
            return f"Ses değiştirilemedi: {e}"
    if shutil.which("amixer"):
        cmd = {"up": ["amixer", "-q", "set", "Master", f"{step}%+"],
               "down": ["amixer", "-q", "set", "Master", f"{step}%-"],
               "mute": ["amixer", "-q", "set", "Master", "toggle"]}[action]
        try:
            r = subprocess.run(cmd, timeout=5, capture_output=True, text=True)
            return msg if r.returncode == 0 else f"Ses değiştirilemedi: {(r.stderr or '').strip()}"
        except Exception as e:
            return f"Ses değiştirilemedi: {e}"
    if _is_wayland():
        ok, err = _send_xf86_key(action)
        return msg if ok else (f"Ses değiştirilemedi (Wayland). {err} — pactl/amixer "
                                "kurulumu tavsiye edilir: sudo pacman -S pipewire-pulse")
    if shutil.which("xdotool"):
        key = {"up": "XF86AudioRaiseVolume", "down": "XF86AudioLowerVolume",
               "mute": "XF86AudioMute"}[action]
        try:
            r = subprocess.run(["xdotool", "key", key], timeout=5, capture_output=True, text=True)
            return msg if r.returncode == 0 else f"Ses değiştirilemedi: {(r.stderr or '').strip()}"
        except Exception as e:
            return f"Ses değiştirilemedi: {e}"
    return "Ses aracı bulunamadı (pactl/amixer kurulu değil)."


def media_control(action: str) -> str:
    """action: playpause | stop | next | prev — çalan medyayı (Spotify,
    YouTube sekmesi, yerel oynatıcı) medya tuşlarıyla kontrol eder."""
    action = (action or "").lower().strip()
    if action not in ("playpause", "stop", "next", "prev"):
        return "Geçersiz medya komutu."

    msg = {"playpause": "Oynat/duraklat gönderildi.", "stop": "Durduruldu.",
           "next": "Sonraki parçaya geçildi.", "prev": "Önceki parçaya dönüldü."}[action]

    if _IS_WINDOWS:
        return msg if _win_send_vk(_VK[action]) else "Medya tuşu gönderilemedi."

    # Linux: playerctl (Spotify/tarayıcı MPRIS — X11/Wayland'den bağımsız,
    # D-Bus üzerinden çalışır) en doğrusu ve öncelikli.
    if shutil.which("playerctl"):
        sub = {"playpause": "play-pause", "stop": "stop",
               "next": "next", "prev": "previous"}[action]
        try:
            r = subprocess.run(["playerctl", sub], timeout=5, capture_output=True, text=True)
            if r.returncode == 0:
                return msg
        except Exception:
            pass
    if _is_wayland():
        ok, err = _send_xf86_key(action)
        if ok:
            return msg
        return (f"Medya kontrol edilemedi (Wayland). {err} — playerctl "
                "tavsiye edilir: sudo pacman -S playerctl")
    if shutil.which("xdotool"):
        key = {"playpause": "XF86AudioPlay", "stop": "XF86AudioStop",
               "next": "XF86AudioNext", "prev": "XF86AudioPrev"}[action]
        try:
            r = subprocess.run(["xdotool", "key", key], timeout=5, capture_output=True, text=True)
            if r.returncode == 0:
                return msg
        except Exception:
            pass
    return "Medya kontrol aracı yok (playerctl öneririm: pardus/cachy paket deposunda var)."


def save_active_document() -> str:
    """Aktif pencereye Ctrl+S gönderir (Word/LibreOffice/kod editörü...)."""
    if _IS_WINDOWS:
        script = ("$w=New-Object -ComObject WScript.Shell; "
                  "Start-Sleep -Milliseconds 300; $w.SendKeys('^s')")
        try:
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=10, capture_output=True,
                           creationflags=_CREATE_NO_WINDOW)
            return "Kaydet komutu (Ctrl+S) gönderildi."
        except Exception as e:
            return f"Kaydedilemedi: {e}"

    # Wayland'de xdotool sessizce "başarılı" görünüp hiçbir şey yapmayabilir
    # (bkz. keyboard_control.py) — bu yüzden Wayland'de xdotool'u ATLAYIP
    # doğrudan wtype/ydotool deneriz; returncode her adımda kontrol edilir.
    if _is_wayland():
        if shutil.which("wtype"):
            try:
                r = subprocess.run(["wtype", "-M", "ctrl", "s", "-m", "ctrl"],
                                   timeout=5, capture_output=True, text=True)
                if r.returncode == 0:
                    return "Kaydet komutu (Ctrl+S) gönderildi."
            except Exception:
                pass
        if shutil.which("ydotool"):
            try:
                # 29=KEY_LEFTCTRL, 31=KEY_S
                r = subprocess.run(["ydotool", "key", "29:1", "31:1", "31:0", "29:0"],
                                   timeout=5, capture_output=True, text=True)
                if r.returncode == 0:
                    return "Kaydet komutu (Ctrl+S) gönderildi."
            except Exception:
                pass
        return ("Kaydedilemedi (Wayland) — wtype ya da ydotool kurulu değil/çalışmıyor. "
                "Kurulum: sudo pacman -S wtype   veya   sudo pacman -S ydotool && "
                "sudo systemctl enable --now ydotool")

    for tool, cmd in (("xdotool", ["xdotool", "key", "--delay", "100", "ctrl+s"]),
                      ("wtype", ["wtype", "-M", "ctrl", "s", "-m", "ctrl"])):
        if shutil.which(tool):
            try:
                r = subprocess.run(cmd, timeout=5, capture_output=True, text=True)
                if r.returncode == 0:
                    return "Kaydet komutu (Ctrl+S) gönderildi."
            except Exception:
                continue
    return "Kaydetme aracı yok (xdotool kur)."


def shutdown_assistant(ui=None) -> str:
    """YERINDE'yi kapatır ('kendini kapat')."""
    try:
        if ui is not None and getattr(ui, "root", None) is not None:
            ui.root.after(400, ui.root.destroy)   # veda cümlesi loga düşsün
            return "Görüşmek üzere! Kapanıyorum."
    except Exception:
        pass
    import os, threading
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return "Kapanıyorum."
