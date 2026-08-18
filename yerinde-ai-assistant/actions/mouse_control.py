"""
actions/mouse_control.py — Sesle fare kontrolü.

YÖN SORUNU (ÇÖZÜLDÜ): Bağıl hareket (moveRel / mousemove_relative) bazı Linux
masaüstlerinde (Wayland/XWayland, çoklu ekran) beklenmedik yönde
uygulanabiliyordu. X11/Windows tarafında İMLECİN KONUMU OKUNUP hedef nokta
hesaplanıyor ve MUTLAK konuma taşınıyor — yön her sistemde kesin doğru.

WAYLAND SORUNU (ÇÖZÜLDÜ): Önceki sürüm yalnızca 'ydotool kurulu mu?' diye
kontrol ediyor, ama tıklama/kaydırma/hareket işlemlerinde ydotool'u HİÇ
ÇAĞIRMIYORDU — pyautogui/xdotool'a düşüyor, onlar da Wayland'de sessizce
hiçbir şey yapmıyordu. Yani "kurulu" göründüğü hâlde fare gerçekte hiç
çalışmıyordu. Şimdi Wayland'de HER eylem (hareket/tıklama/kaydırma)
gerçekten ydotool ile yapılıyor; ydotool'un kendi çıkış koduna bakılıp
başarısızlıkta dürüst bir hata veriliyor (sessizce "başarılı" denmiyor).

WAYLAND "SOL ÜST KÖŞEYE TAKILMA" SORUNU (ÇÖZÜLDÜ): 'ydotool mousemove
--absolute' komutu, ydotool'un kendi projesinde bilinen bir kusur/tutarsızlık
içeriyor — bazı sürüm/derleme kombinasyonlarında girilen piksel koordinatı
ne olursa olsun imleci ekranın SOL ÜST KÖŞESİNE gönderiyor ya da eksende
yanlış ölçekle (ör. yarım çözünürlük) hareket ettiriyor (bkz. ydotool
GitHub #250, #158, #138). Önceki sürümümüz her hareket komutunda "varsayılan
ekran ortası" + yön vektörü ile MUTLAK bir hedef hesaplayıp --absolute
gönderiyordu; --absolute bozuksa sonuç hep aynı (yanlış) köşeye gidip
"takılı" kalıyordu. Artık yön komutları (sağa/sola/yukarı/aşağı) --absolute
KULLANMIYOR — bunun yerine imleci mevcut konumuna göre BAĞIL (relative)
olarak `ydotool mousemove -x <dx> -y <dy>` ile hareket ettiriyor; bu, ydotool
ekosisteminde --absolute'e göre çok daha güvenilir çalışıyor. "Ortala"
(center) komutu için önce büyük bir bağıl "aşırı hareket" ile imleç sol üst
köşeye (0,0) sabitlenir (ekran sınırının dışına çıkamayacağı için işletim
sistemi otomatik olarak köşede durdurur), sonra gerçek ekran çözünürlüğü
(wlr-randr/swaymsg/hyprctl ile) tespit edilmeye çalışılıp yarısı kadar bağıl
hareket ile ortaya gidilir; tespit başarısız olursa 1920×1080 varsayımıyla
en iyi tahmin yapılır.
"""

from __future__ import annotations

import platform
import shutil
import subprocess

from core.input_backend import (
    BTN_LEFT, BTN_MIDDLE, BTN_RIGHT, YDOTOOL_MISSING_TR,
    is_wayland as _ib_is_wayland, ydotool_click as _ib_click,
    ydotool_move_absolute as _ib_move_abs, ydotool_move_relative as _ib_move_rel,
    ydotool_scroll as _ib_scroll, ydotool_available,
)

_IS_WINDOWS = platform.system() == "Windows"
_MOVE_STEP = 200      # "götür" adımı (piksel)
_SCROLL_STEP = 5

# Yerel adlar (core/remote_server.py bu isimleri içe aktarıyor — korunur)
_BTN_LEFT, _BTN_RIGHT, _BTN_MIDDLE = BTN_LEFT, BTN_RIGHT, BTN_MIDDLE

# Yön sözcükleri (LLM İngilizce de gönderebilir)
_DIRS = {
    "sağa": (1, 0), "sağ": (1, 0), "right": (1, 0),
    "sola": (-1, 0), "sol": (-1, 0), "left": (-1, 0),
    "yukarı": (0, -1), "yukari": (0, -1), "yukarıya": (0, -1), "up": (0, -1),
    "aşağı": (0, 1), "asagi": (0, 1), "aşağıya": (0, 1), "down": (0, 1),
}


def _is_wayland() -> bool:
    """Tespit core/input_backend.py'de (aifinal.md §2)."""
    return _ib_is_wayland()


def _wayland_warning() -> str:
    return YDOTOOL_MISSING_TR


# ══ Ekran/konum bilgisi ══════════════════════════════════════════════════════
def _screen_and_pos() -> tuple[int, int, int, int] | None:
    """(ekran_w, ekran_h, imleç_x, imleç_y) — bulunamazsa None."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        w, h = pyautogui.size()
        x, y = pyautogui.position()
        return int(w), int(h), int(x), int(y)
    except Exception:
        pass
    if not _IS_WINDOWS and shutil.which("xdotool"):
        try:
            out = subprocess.run(["xdotool", "getmouselocation", "--shell"],
                                 capture_output=True, text=True, timeout=5).stdout
            vals = dict(l.split("=", 1) for l in out.strip().splitlines() if "=" in l)
            x, y = int(vals["X"]), int(vals["Y"])
            geo = subprocess.run(["xdotool", "getdisplaygeometry"],
                                 capture_output=True, text=True, timeout=5).stdout.split()
            w, h = int(geo[0]), int(geo[1])
            return w, h, x, y
        except Exception:
            return None
    return None


def _screen_size_wayland() -> tuple[int, int]:
    """Wayland'de GERÇEK ekran çözünürlüğünü tespit etmeyi dener (sway,
    Hyprland, wlroots tabanlı diğer compositor'lar). Hiçbiri bulunamazsa
    standart Full HD'yi VARSAYIM olarak döner (kesin doğru olmayabilir,
    ama en iyi tahmin)."""
    import json

    if shutil.which("hyprctl"):
        try:
            out = subprocess.run(["hyprctl", "monitors", "-j"],
                                 capture_output=True, text=True, timeout=5).stdout
            mons = json.loads(out)
            focused = next((m for m in mons if m.get("focused")), mons[0] if mons else None)
            if focused:
                return int(focused["width"]), int(focused["height"])
        except Exception:
            pass

    if shutil.which("swaymsg"):
        try:
            out = subprocess.run(["swaymsg", "-t", "get_outputs", "-r"],
                                 capture_output=True, text=True, timeout=5).stdout
            outs = json.loads(out)
            active = next((o for o in outs if o.get("active")), outs[0] if outs else None)
            if active:
                return int(active["current_mode"]["width"]), int(active["current_mode"]["height"])
        except Exception:
            pass

    if shutil.which("wlr-randr"):
        try:
            out = subprocess.run(["wlr-randr"], capture_output=True, text=True, timeout=5).stdout
            import re
            m = re.search(r"(\d+)x(\d+)\s+px.*current", out)
            if not m:
                m = re.search(r"(\d+)x(\d+)@[\d.]+\s*Hz\s*\(current\)", out)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass

    return 1920, 1080  # Tespit edilemedi — varsayım


# ══ Wayland: ydotool çağrıları core/input_backend.py'ye delege (aifinal.md §2)
# İsimler korunur — core/remote_server.py bunları içe aktarıyor. ═════════════
def _ydotool_run(args: list[str]) -> tuple[bool, str]:
    from core.input_backend import run_ydotool
    return run_ydotool(args)


def _ydotool_move_absolute(x: int, y: int) -> tuple[bool, str]:
    return _ib_move_abs(x, y)


def _ydotool_move_relative(dx: int, dy: int) -> tuple[bool, str]:
    """--absolute KULLANMAZ. ydotool'un kendi projesinde --absolute'ün bazı
    sürümlerde imleci hep sol üst köşeye gönderdiği bilinen bir kusur
    olduğu için (GitHub ReimuNotMoe/ydotool #250, #158, #138), yön
    komutlarında bunun yerine güvenilir çalışan BAĞIL hareket kullanılır."""
    return _ib_move_rel(dx, dy)


def _ydotool_click(button_code: int) -> tuple[bool, str]:
    return _ib_click(button_code)


def _ydotool_scroll(amount: int) -> tuple[bool, str]:
    """amount > 0: yukarı kaydır, amount < 0: aşağı kaydır."""
    return _ib_scroll(amount)


# ══ Hareket (Windows/X11) ═══════════════════════════════════════════════════
def _move_absolute(x: int, y: int) -> bool:
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.moveTo(x, y, duration=0.12)
        return True
    except Exception:
        pass
    if not _IS_WINDOWS and shutil.which("xdotool"):
        try:
            subprocess.run(["xdotool", "mousemove", str(x), str(y)],
                           timeout=5, capture_output=True)
            return True
        except Exception:
            return False
    return False


def mouse_control(action: str, direction: str = "", amount: int = 0) -> str:
    action = (action or "").lower().strip()
    direction = (direction or "").lower().strip()
    amount = int(amount) if amount else 0

    # ── Wayland: HER eylem gerçekten ydotool ile yapılır ────────────────────
    if _is_wayland():
        if not ydotool_available():
            return _wayland_warning()
        return _mouse_control_wayland(action, direction, amount)

    # ── Windows / X11: mutlak konumlandırma (yön kesin doğru) ───────────────
    if action in ("move", "center"):
        info = _screen_and_pos()
        if not info:
            return ("Fare konumu okunamadı. Kurulum: pip install pyautogui "
                    "(Linux'ta ayrıca: sudo apt install xdotool)")
        sw, sh, cx, cy = info

        if action == "center":
            return ("İmleç ekranın ortasına alındı."
                    if _move_absolute(sw // 2, sh // 2) else "İmleç taşınamadı.")

        vec = _DIRS.get(direction)
        if not vec:
            return "Yön anlaşılamadı (sağa / sola / yukarı / aşağı)."
        step = amount or _MOVE_STEP
        tx = min(max(0, cx + vec[0] * step), sw - 1)
        ty = min(max(0, cy + vec[1] * step), sh - 1)
        if _move_absolute(tx, ty):
            return f"İmleç {direction} taşındı."
        return "İmleç taşınamadı."

    # ── Tıklama / kaydırma ──────────────────────────────────────────────────
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        if action == "left_click":
            pyautogui.click();               return "Sol tıklandı."
        if action == "right_click":
            pyautogui.click(button="right"); return "Sağ tıklandı."
        if action == "double_click":
            pyautogui.doubleClick();         return "Çift tıklandı."
        if action == "scroll_up":
            pyautogui.scroll(amount or _SCROLL_STEP);    return "Yukarı kaydırıldı."
        if action == "scroll_down":
            pyautogui.scroll(-(amount or _SCROLL_STEP)); return "Aşağı kaydırıldı."
        return "Geçersiz fare komutu."
    except ImportError:
        pass
    except Exception as e:
        if _IS_WINDOWS:
            return f"Fare kontrolü başarısız: {e}"

    if not _IS_WINDOWS and shutil.which("xdotool"):
        cmds = {
            "left_click": ["click", "1"], "right_click": ["click", "3"],
            "double_click": ["click", "--repeat", "2", "1"],
            "scroll_up": ["click", "--repeat", str(amount or _SCROLL_STEP), "4"],
            "scroll_down": ["click", "--repeat", str(amount or _SCROLL_STEP), "5"],
        }
        if action in cmds:
            subprocess.run(["xdotool"] + cmds[action], timeout=5, capture_output=True)
            return {"left_click": "Sol tıklandı.", "right_click": "Sağ tıklandı.",
                    "double_click": "Çift tıklandı.", "scroll_up": "Yukarı kaydırıldı.",
                    "scroll_down": "Aşağı kaydırıldı."}[action]
    return "Fare aracı yok (pip install pyautogui ya da xdotool kur)."


def _mouse_control_wayland(action: str, direction: str, amount: int) -> str:
    """Wayland'e özel yol: HER eylem gerçekten ydotool çağırır ve başarıyı
    ydotool'un kendi çıkış koduyla doğrular — sessizce 'başarılı' demez."""
    import time

    if action in ("move", "center"):
        if action == "center":
            # 1) Büyük bağıl "aşırı hareket" ile imleci SOL ÜST köşeye (0,0)
            #    sabitle — ekran sınırının dışına çıkamayacağı için işletim
            #    sistemi imleci otomatik olarak köşede durdurur. Bu, bozuk
            #    olabilen --absolute'e hiç ihtiyaç duymadan güvenilir bir
            #    "bilinen başlangıç noktası" verir.
            ok0, err0 = _ydotool_move_relative(-100000, -100000)
            if not ok0:
                return f"İmleç ortalanamadı ({err0})."
            sw, sh = _screen_size_wayland()
            ok, err = _ydotool_move_relative(sw // 2, sh // 2)
            return "İmleç ekranın ortasına alındı." if ok else f"İmleç taşınamadı ({err})."

        vec = _DIRS.get(direction)
        if not vec:
            return "Yön anlaşılamadı (sağa / sola / yukarı / aşağı)."
        step = amount or _MOVE_STEP
        dx, dy = vec[0] * step, vec[1] * step
        ok, err = _ydotool_move_relative(dx, dy)
        return f"İmleç {direction} taşındı." if ok else f"İmleç taşınamadı ({err})."

    if action == "left_click":
        ok, err = _ydotool_click(_BTN_LEFT)
        return "Sol tıklandı." if ok else f"Tıklanamadı ({err})."
    if action == "right_click":
        ok, err = _ydotool_click(_BTN_RIGHT)
        return "Sağ tıklandı." if ok else f"Tıklanamadı ({err})."
    if action == "double_click":
        ok1, err1 = _ydotool_click(_BTN_LEFT)
        time.sleep(0.08)
        ok2, err2 = _ydotool_click(_BTN_LEFT)
        return "Çift tıklandı." if (ok1 and ok2) else f"Çift tıklanamadı ({err1 or err2})."
    if action == "scroll_up":
        ok, err = _ydotool_scroll(amount or _SCROLL_STEP)
        return "Yukarı kaydırıldı." if ok else f"Kaydırılamadı ({err})."
    if action == "scroll_down":
        ok, err = _ydotool_scroll(-(amount or _SCROLL_STEP))
        return "Aşağı kaydırıldı." if ok else f"Kaydırılamadı ({err})."
    return "Geçersiz fare komutu."
