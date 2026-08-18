"""
actions/whatsapp_call.py — WhatsApp sesli/görüntülü arama.

DÜRÜST DURUM: WhatsApp arama başlatmak için resmi bir API/komut satırı arayüzü
sunmaz. Yapılabilecek en sağlam şey:
  1) Kişinin sohbetini 'whatsapp://send?phone=...' bağlantısıyla AÇMAK (güvenilir),
  2) Arama düğmesine TIKLAMAK (otomasyon).

Düğmenin ekrandaki yeri kuruluma/pencere boyutuna göre değiştiği için konumu
TAHMİN ETMİYORUZ — bir kez ÖĞRETİYORSUN:

    "whatsapp sesli arama düğmesini öğret"     → 5 sn içinde imleci düğmenin
    "whatsapp görüntülü arama düğmesini öğret"   üzerine götür, konumu kaydeder.

Sonrasında: "annemi ara" / "annemle görüntülü konuş" çalışır.

BU SÜRÜMDE DÜZELTİLEN İKİ GERÇEK SORUN:
  1) MUTLAK PİKSEL yerine PENCEREYE GÖRE ORANSAL konum kaydediliyor —
     WhatsApp penceresi taşınsa/yeniden boyutlansa bile tıklama doğru yere
     gidiyor (eskiden pencere hareket edince tıklama boşa gidiyordu).
  2) Wayland'de (Pardus/CachyOS) tıklama artık GERÇEKTEN çalışıyor —
     eskiden bu dosya kendi ham pyautogui.click()'ini kullanıyordu, bu da
     Wayland'de sessizce hiçbir şey yapmıyordu (mouse_control.py'de
     düzelttiğimiz AYNI hatanın bir kopyası, ayrı bir kod yolunda).

Not: WhatsApp MASAÜSTÜ uygulaması gerekir (WhatsApp Web'de arama yoktur).
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
import urllib.parse
import webbrowser

from actions.whatsapp import _find_contact, _normalize_phone
from actions.mouse_control import (_is_wayland, _ydotool_move_absolute,
                                   _ydotool_click, _BTN_LEFT)

_IS_WINDOWS = platform.system() == "Windows"

_CFG_KEYS = {"voice": "wa_call_voice_xy", "video": "wa_call_video_xy"}
_TR = {"voice": "sesli", "video": "görüntülü"}


def _cfg_get(key, default=None):
    try:
        from app_config import get_app_config_value
        return get_app_config_value(key, default)
    except Exception:
        return default


def _cfg_set(key, value):
    try:
        from app_config import save_app_config
        save_app_config({key: value})
    except Exception:
        pass


def _open_chat(phone: str) -> bool:
    """Kişinin sohbetini WhatsApp masaüstü uygulamasında açar."""
    url = f"whatsapp://send?phone={urllib.parse.quote(phone.lstrip('+'))}"
    try:
        if _IS_WINDOWS:
            import os
            os.startfile(url)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", url],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        return True
    except Exception:
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False


# ══ WhatsApp penceresini bulma (taşınma/boyut değişikliğine dayanıklı olmak için) ══
def _find_whatsapp_window_rect() -> tuple[int, int, int, int] | None:
    """(sol, üst, genişlik, yükseklik) döner; bulunamazsa None."""
    if _is_wayland():
        # Hyprland (CachyOS'ta yaygın bir pencere yöneticisi): 'hyprctl
        # clients -j' tüm pencerelerin konum/boyutunu JSON olarak verir.
        if shutil.which("hyprctl"):
            try:
                out = subprocess.run(["hyprctl", "clients", "-j"],
                                     capture_output=True, text=True, timeout=5).stdout
                import json
                for c in json.loads(out):
                    if "whatsapp" in (c.get("title") or "").lower():
                        x, y = c.get("at", [0, 0])
                        w, h = c.get("size", [0, 0])
                        if w > 100 and h > 100:
                            return (int(x), int(y), int(w), int(h))
            except Exception:
                pass
        # Sway (wlroots tabanlı Wayland): get_tree'deki 'rect' alanı.
        if shutil.which("swaymsg"):
            try:
                out = subprocess.run(["swaymsg", "-t", "get_tree"],
                                     capture_output=True, text=True, timeout=5).stdout
                import json
                def _find_win(node):
                    if "whatsapp" in (node.get("name") or "").lower():
                        return node.get("rect")
                    for child in node.get("nodes", []) + node.get("floating_nodes", []):
                        found = _find_win(child)
                        if found:
                            return found
                    return None
                rect = _find_win(json.loads(out))
                if rect:
                    w, h = rect.get("width", 0), rect.get("height", 0)
                    if w > 100 and h > 100:
                        return (int(rect.get("x", 0)), int(rect.get("y", 0)), int(w), int(h))
            except Exception:
                pass
        # KDE Plasma (Wayland): kdotool getwindowgeometry çıktısı
        # "Position: X,Y\nGeometry: WxH" biçimindedir.
        if shutil.which("kdotool"):
            try:
                ids = subprocess.run(["kdotool", "search", "--name", "whatsapp"],
                                     capture_output=True, text=True, timeout=5).stdout.split()
                if ids:
                    out = subprocess.run(["kdotool", "getwindowgeometry", ids[-1]],
                                         capture_output=True, text=True, timeout=5).stdout
                    pos, geo = None, None
                    for line in out.splitlines():
                        if line.strip().startswith("Position:"):
                            pos = line.split(":", 1)[1].strip().split(",")
                        elif line.strip().startswith("Geometry:"):
                            geo = line.split(":", 1)[1].strip().split("x")
                    if pos and geo and len(pos) == 2 and len(geo) == 2:
                        x, y = float(pos[0]), float(pos[1])
                        w, h = float(geo[0]), float(geo[1])
                        if w > 100 and h > 100:
                            return (int(x), int(y), int(w), int(h))
            except Exception:
                pass
        return None

    if _IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            found = []

            def callback(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if "whatsapp" in buf.value.lower():
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w, h = rect.right - rect.left, rect.bottom - rect.top
                    if w > 100 and h > 100:   # simge durumundaki/gizli pencereleri ele
                        found.append((rect.left, rect.top, w, h))
                        return False
                return True

            EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(EnumProc(callback), 0)
            return found[0] if found else None
        except Exception:
            return None

    # Linux: wmctrl -lG → "id masaüstü x y genişlik yükseklik host başlık..."
    if shutil.which("wmctrl"):
        try:
            out = subprocess.run(["wmctrl", "-lG"], capture_output=True,
                                 text=True, timeout=5).stdout
            for line in out.splitlines():
                if "whatsapp" in line.lower():
                    parts = line.split(None, 7)
                    if len(parts) >= 6:
                        x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                        if w > 100 and h > 100:
                            return (x, y, w, h)
        except Exception:
            pass
    return None


def _active_window_has_whatsapp() -> bool | None:
    """Aktif pencere WhatsApp mı? Belirlenemezse None (Wayland'de genelde)."""
    try:
        from actions.window_safety import active_window_title
        title = active_window_title()
        if title is None:
            return None
        return "whatsapp" in title.lower()
    except Exception:
        return None


def _safe_click(x: int, y: int) -> tuple[bool, str]:
    """Wayland'de ydotool, X11/Windows'ta pyautogui — mouse_control.py'nin
    KANITLANMIŞ Wayland mantığını yeniden kullanır (tekrar yazmıyoruz)."""
    if _is_wayland():
        ok1, err1 = _ydotool_move_absolute(x, y)
        if not ok1:
            return False, f"imleç taşınamadı: {err1}"
        time.sleep(0.05)
        ok2, err2 = _ydotool_click(_BTN_LEFT)
        return ok2, (err2 if not ok2 else "")
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(x, y)
        return True, ""
    except Exception as e:
        return False, str(e)


# ══ Düğme konumunu öğretme ══════════════════════════════════════════════════
def calibrate_call_button(kind: str = "voice", seconds: int = 5,
                          on_log=lambda m: None) -> str:
    """
    Kullanıcı imleci arama düğmesinin üzerine götürür; süre dolunca konum
    kaydedilir. Pencere bulunabiliyorsa ORANSAL (pencereye göre yüzde),
    bulunamıyorsa (nadir) eski mutlak piksel biçimine düşülür.
    """
    kind = "video" if str(kind).lower().startswith("g") or kind == "video" else "voice"
    try:
        import pyautogui
    except ImportError:
        return "Bunun için pyautogui gerekli: pip install pyautogui"

    on_log(f"SYS: 🎯 WhatsApp'ı aç, bir sohbete gir ve imleci {_TR[kind]} arama "
           f"düğmesinin ÜZERİNE götür — {seconds} saniye sayıyorum...")
    for i in range(seconds, 0, -1):
        on_log(f"SYS: {i}...")
        time.sleep(1)
    x, y = pyautogui.position()

    rect = _find_whatsapp_window_rect()
    if rect:
        wx, wy, ww, wh = rect
        rel_x = (x - wx) / ww
        rel_y = (y - wy) / wh
        if 0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0:
            _cfg_set(_CFG_KEYS[kind], {"rel": [rel_x, rel_y]})
            return (f"{_TR[kind].capitalize()} arama düğmesi öğrenildi (pencereye göre "
                    f"%{rel_x*100:.0f}, %{rel_y*100:.0f}) — pencere taşınsa/boyutu "
                    "değişse bile artık doğru yeri bulur. Artık 'annemi ara' diyebilirsin.")
        # imleç WhatsApp penceresinin DIŞINDA kaldıysa (başka ekran vb.)
        on_log("UYARI: İmleç WhatsApp penceresinin dışında görünüyor, mutlak "
              "konum olarak kaydediyorum (pencere taşınırsa yeniden öğretmen gerekebilir).")
    _cfg_set(_CFG_KEYS[kind], {"abs": [int(x), int(y)]})
    return (f"{_TR[kind].capitalize()} arama düğmesi öğrenildi ({x}, {y}). "
            "Artık 'annemi ara' diyebilirsin.")


# ══ Arama ═══════════════════════════════════════════════════════════════════
def whatsapp_call(contact: str, kind: str = "voice", on_log=lambda m: None) -> str:
    kind = "video" if kind == "video" else "voice"

    match = _find_contact(contact)
    if not match:
        return (f"'{contact}' kişisini bulamadım. Önce numarasını kaydet: "
                "'whatsapp kişisi kaydet' komutuyla ekleyebilirsin.")
    phone = _normalize_phone(match.get("value", ""))
    name = match.get("display_name", contact)

    saved = _cfg_get(_CFG_KEYS[kind])
    if not saved:
        return (f"{_TR[kind].capitalize()} arama düğmesinin yerini bilmiyorum. "
                f"Bir kez öğretmen yeterli: 'whatsapp {_TR[kind]} arama düğmesini "
                "öğret' de, WhatsApp'ta imleci düğmenin üzerine götür.")

    if not _open_chat(phone):
        return "WhatsApp masaüstü uygulaması açılamadı (kurulu mu?)."

    on_log(f"SYS: 📞 {name} sohbeti açılıyor, {_TR[kind]} arama başlatılıyor...")

    # Sabit 3.5 sn beklemek yerine, pencere GERÇEKTEN belirene kadar (en fazla
    # ~5 sn) aktif şekilde dene — yavaş bilgisayarlarda eskiden pencere daha
    # açılmadan tıklanmaya çalışılıyordu.
    rect = None
    for _ in range(20):
        rect = _find_whatsapp_window_rect()
        if rect:
            break
        time.sleep(0.25)
    if not rect:
        time.sleep(1.5)   # pencere hâlâ bulunamadıysa son bir şans için bekle

    # Kaydedilmiş konumu (oransal ya da mutlak) gerçek tıklama noktasına çevir
    if isinstance(saved, dict) and "rel" in saved and rect:
        wx, wy, ww, wh = rect
        click_x = int(wx + saved["rel"][0] * ww)
        click_y = int(wy + saved["rel"][1] * wh)
    elif isinstance(saved, dict) and "abs" in saved:
        click_x, click_y = saved["abs"]
    elif isinstance(saved, (list, tuple)) and len(saved) == 2:
        # Eski (önceki sürümden kalma) mutlak piksel biçimi — geriye dönük uyumluluk
        click_x, click_y = int(saved[0]), int(saved[1])
    else:
        return "Kayıtlı arama düğmesi konumu bozuk görünüyor — yeniden öğretir misin?"

    # Mümkünse WhatsApp'ın gerçekten önde olduğunu doğrula (Wayland'de bu
    # kontrol genelde mümkün değil — o durumda temkinli davranıp devam ederiz,
    # çünkü zaten öncesinde chat açma adımı WhatsApp'ı öne getirmiş olmalı).
    focused = _active_window_has_whatsapp()
    if focused is False:
        on_log("UYARI: WhatsApp önde görünmüyor — yine de deniyorum "
              "(pencereyi manuel öne getirmen gerekebilir).")

    ok, err = _safe_click(click_x, click_y)
    if not ok:
        return f"Arama düğmesine tıklanamadı: {err}"

    return (f"{name} {_TR[kind]} olarak aranıyor. (Çalışmazsa: WhatsApp penceresini "
            f"büyük/normal boyutta tutup 'whatsapp {_TR[kind]} arama düğmesini öğret' "
            "ile konumu tazele.)")
