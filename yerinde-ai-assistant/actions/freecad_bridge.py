"""
actions/freecad_bridge.py — Açık FreeCAD'in İÇİNDE Python betiği çalıştırma
(3D CAD tasarımı için — masa/mekanik parça/vb. modelleme).

Nasıl çalışır?
  • FreeCAD'i BİZ açarsak (open_app "freecad"/"free cad"), yanına küçük bir
    dinleyici betik ARGÜMAN olarak verilir: FreeCAD'in resmi, belgelenen
    "komut satırından .FCMacro/.py çalıştırma" özelliği kullanılır — Blender'ın
    '--python' bayrağının FreeCAD karşılığı. GUI açık kalır, betik hemen çalışır.
  • Dinleyici, 127.0.0.1:5960'ta bekler; gelen Python kodunu FreeCAD'in Qt ana
    döngüsünde (QTimer, ana pencereye "parent" bağlı — makro betiği bitse de
    çöp toplanmaz) çalıştırır — nesne ANINDA sahnede belirir.
  • "masa çiz" dendiğinde üretilen FreeCAD kodu bu sokete gönderilir.
  • Köprüsüz açılmışsa (elle açtıysan): kod bir .FCMacro olarak kaydedilir ve
    YENİ bir FreeCAD penceresinde çalıştırılır; log'a "canlı mod için
    FreeCAD'i YERINDE ile aç" notu düşer.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0
BASE_DIR = Path(__file__).resolve().parent.parent
PORT = 5960  # Blender köprüsü 5959 kullanıyor — çakışmasın diye farklı port

_LISTENER = r'''
# YERINDE FreeCAD koprusu — gelen Python kodunu ana Qt dongusunde calistirir.
# Bu dosya 'freecad bu_dosya.FCMacro' seklinde komut satiri argumaniyla
# calistirilir (FreeCAD'in resmi, belgelenen "komut satirindan makro
# calistirma" yontemi) — GUI acik kalir, betik calisir, pencere normal kalir.
import FreeCAD as App
import FreeCADGui as Gui
import socket, threading, queue, traceback

PORT = 5960
_q = queue.Queue()

def _serve():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", PORT)); s.listen(4)
    except Exception:
        print("[YERINDE] FreeCAD kopru soketi acilamadi - FreeCAD normal calisiyor.")
        traceback.print_exc()
        return
    while True:
        conn, _ = s.accept()
        data = b""
        while True:
            part = conn.recv(65536)
            if not part: break
            data += part
            if data.endswith(b"\x00"): data = data[:-1]; break
        _q.put((conn, data.decode("utf-8", "replace")))

threading.Thread(target=_serve, daemon=True).start()

try:
    from PySide2 import QtCore
except Exception:
    try:
        from PySide6 import QtCore
    except Exception:
        from PySide import QtCore

def _pump():
    try:
        while True:
            conn, code = _q.get_nowait()
            try:
                ns = {"App": App, "FreeCAD": App, "Gui": Gui, "FreeCADGui": Gui,
                      "__name__": "__main__"}
                for modname in ("Part", "Sketcher", "Draft", "PartDesign", "Mesh"):
                    try:
                        ns[modname] = __import__(modname)
                    except Exception:
                        pass
                exec(compile(code, "<yerinde>", "exec"), ns)
                try:
                    if App.ActiveDocument is not None:
                        App.ActiveDocument.recompute()
                    Gui.updateGui()
                except Exception:
                    pass
                conn.sendall(b"OK")
            except Exception:
                conn.sendall(("HATA:\n" + traceback.format_exc()[-800:]).encode("utf-8"))
            finally:
                conn.close()
    except queue.Empty:
        pass

# KRITIK: QTimer'i ana pencereye "parent" olarak bagliyoruz. Bu makro betigi
# calisip bitince yerel degiskenler cop toplanabilir - ama Qt'nin C++ nesne
# agacinda ana pencerenin COCUGU olarak kayitli oldugu icin QTimer, ana
# pencere acik oldugu surece YASAMAYA DEVAM EDER (Python referans sayimindan
# bagimsiz - bu, ayri bir test ortaminda dogrulanmistir).
_timer = QtCore.QTimer(Gui.getMainWindow())
_timer.timeout.connect(_pump)
_timer.start(200)

print("[YERINDE] FreeCAD koprusu hazir (127.0.0.1:%d)" % PORT)
'''


def _clean_env() -> dict:
    """KRİTİK: FreeCAD da (Blender gibi) KENDİ gömülü Python'unu kullanır.
    Bizim venv'imizin PYTHONHOME/PYTHONPATH/VIRTUAL_ENV değişkenleri FreeCAD'e
    sızınca yanlış Python kütüphanelerini yüklemeye çalışıp çökebilir."""
    env = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "VIRTUAL_ENV",
                "PYTHONEXECUTABLE", "LD_PRELOAD", "LD_LIBRARY_PATH",
                "OMP_NUM_THREADS", "KMP_DUPLICATE_LIB_OK"):
        env.pop(key, None)
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        parts = [p for p in env.get("PATH", "").split(os.pathsep)
                 if not p.startswith(venv)]
        env["PATH"] = os.pathsep.join(parts)
    return env


def _listener_path() -> Path:
    """Betiği ev dizinine yazar (Blender köprüsüyle aynı desen): snap/flatpak
    kurulumu proje klasörünü okuyamayabilir; ev dizini her zaman erişilebilir."""
    try:
        d = Path.home() / ".yerinde"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "freecad_listener.FCMacro"
    except Exception:
        p = BASE_DIR / "freecad_listener.FCMacro"
    if not p.exists() or p.read_text(encoding="utf-8") != _LISTENER:
        p.write_text(_LISTENER, encoding="utf-8")
    return p


def find_freecad() -> list[str] | None:
    """FreeCAD başlatma KOMUTUNU (liste) döner — flatpak/snap dahil."""
    if _IS_WINDOWS:
        import glob
        for pat in (r"C:\Program Files\FreeCAD*\bin\FreeCAD.exe",
                    r"C:\Program Files (x86)\FreeCAD*\bin\FreeCAD.exe"):
            hits = sorted(glob.glob(pat), reverse=True)
            if hits:
                return [hits[0]]
        w = shutil.which("freecad") or shutil.which("FreeCAD")
        return [w] if w else None

    # Linux: PATH → bilinen yollar → snap → flatpak
    w = shutil.which("freecad") or shutil.which("FreeCAD") or shutil.which("freecad-daily")
    if w:
        return [w]
    import glob
    for pat in ("/usr/bin/freecad", "/usr/local/bin/freecad",
                str(Path.home() / ".local/bin/freecad"),
                "/opt/freecad*/bin/freecad", "/snap/bin/freecad"):
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return [hits[0]]
    for app_id in ("org.freecad.FreeCAD", "org.freecadweb.FreeCAD"):  # yeni → eski flatpak adı
        try:
            r = subprocess.run(["flatpak", "info", app_id],
                               capture_output=True, timeout=5)
            if r.returncode == 0:
                return ["flatpak", "run", app_id]
        except Exception:
            pass
    return None


def is_bridge_alive(timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=timeout):
            return True
    except Exception:
        return False


def launch_freecad_with_bridge() -> str:
    """FreeCAD'i köprü betiğiyle açar (open_app 'freecad/free cad' bunu kullanır)."""
    if is_bridge_alive():
        return "FreeCAD zaten köprüyle açık."
    cmd = find_freecad()
    if not cmd:
        return ("FreeCAD bulunamadı. PATH'te, /opt'ta, snap'te ya da flatpak'te "
                "(org.freecad.FreeCAD) arandı — kurulumunu kontrol et.")
    log_path = Path(tempfile.gettempdir()) / "yerinde_freecad.log"
    listener = _listener_path()

    def _spawn(extra):
        log_f = open(log_path, "w")
        kwargs = dict(stdout=log_f, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL, close_fds=True,
                      env=_clean_env())
        if _IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd + extra, **kwargs)
        try:
            log_f.close()
        except Exception:
            pass
        return proc

    try:
        # FreeCAD'in resmi, belgelenen yöntemi: .FCMacro dosyasını doğrudan
        # komut satırı argümanı olarak vermek — GUI açılır, betik hemen çalışır.
        proc = _spawn([str(listener)])
    except Exception as e:
        return f"FreeCAD açılamadı: {e}"

    for _ in range(75):  # ~15 sn bekle
        if is_bridge_alive():
            return "FreeCAD açıldı (canlı komut köprüsü hazır — 'masa çiz' diyebilirsin)."
        if proc.poll() is not None:
            break
        time.sleep(0.2)

    if proc.poll() is not None:
        reason = ""
        try:
            lines = [l for l in log_path.read_text(errors="replace").splitlines() if l.strip()]
            reason = lines[-1][:150] if lines else ""
        except Exception:
            pass
        try:
            _spawn([])
        except Exception as e:
            return f"FreeCAD açılamadı: {e}"
        return ("FreeCAD açıldı (canlı çizim köprüsü bu kurulumda çalışmadı"
                + (f" — sebep: {reason}" if reason else "")
                + f"; ayrıntı: {log_path}). 'Masa çiz' dersen betik ayrı bir "
                  "FreeCAD penceresinde çalıştırılır.")

    return (f"FreeCAD başlatıldı ama köprü yanıt vermedi (ayrıntı: {log_path}). "
            "Birkaç saniye sonra tekrar komut verebilirsin.")


def save_freecad_project(name: str = "") -> str:
    """Açık FreeCAD belgesini 'Çalışmalarım/FreeCAD' klasörüne .FCStd olarak kaydeder."""
    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("FreeCAD")
    base = (name or "tasarim").strip().replace("/", "-") or "tasarim"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.FCStd"
    if not is_bridge_alive():
        return ("Kaydedebilmem için FreeCAD'i benim açmam gerekiyor "
                "('freecad aç' de) — şu an açık pencereye bağlı değilim.")
    code = (
        "if App.ActiveDocument is None:\n"
        "    App.newDocument('Tasarim')\n"
        "App.ActiveDocument.recompute()\n"
        f"App.ActiveDocument.saveAs(r'{target}')\n"
    )
    result = send_code(code)
    if "çalıştırıldı" in result:
        return f"FreeCAD tasarımı kaydedildi: {target.name} (Çalışmalarım/FreeCAD klasörü)."
    return f"Kaydedilemedi — {result}"


def send_code(code: str, timeout: float = 30.0) -> str:
    """FreeCAD kodunu açık FreeCAD'e gönderir; köprü yoksa yeni pencerede çalıştırır."""
    if not code.strip():
        return "Çalıştırılacak kod boş."
    if is_bridge_alive():
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=timeout) as s:
                s.sendall(code.encode("utf-8") + b"\x00")
                s.settimeout(timeout)
                resp = s.recv(4096).decode("utf-8", "replace")
            return ("Kod FreeCAD içinde çalıştırıldı — sahneye bak!" if resp == "OK"
                    else f"FreeCAD kodu çalıştırırken hata verdi: {resp}")
        except Exception as e:
            return f"FreeCAD köprüsüne gönderilemedi: {e}"
    cmd = find_freecad()
    if not cmd:
        return "FreeCAD bulunamadı."
    from actions.code_tools import ensure_workspace_folder
    path = ensure_workspace_folder("FreeCAD") / f"yerinde_{int(time.time())}.FCMacro"
    full_code = "import FreeCAD as App\nimport FreeCADGui as Gui\n" + code
    path.write_text(full_code, encoding="utf-8")
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                  "env": _clean_env(), "close_fds": True}
        if _IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd + [str(path)], **kwargs)
        return (f"Betik yeni FreeCAD penceresinde çalıştırıldı ({path.name}). "
                "Açık pencerede canlı çizim için FreeCAD'i 'freecad aç' diyerek "
                "YERINDE üzerinden aç.")
    except Exception as e:
        return f"Betik kaydedildi ({path}) ama FreeCAD başlatılamadı: {e}"


# ══ Belge komutları (LLM'siz, deterministik) ═══════════════════════════════
_SCENE_CODE = {
    "clear": (
        "if App.ActiveDocument is not None:\n"
        "    App.closeDocument(App.ActiveDocument.Name)\n"
        "App.newDocument('Tasarim')\n"
    ),
    "delete_selected": (
        "sel = Gui.Selection.getSelection()\n"
        "for obj in sel:\n"
        "    App.ActiveDocument.removeObject(obj.Name)\n"
    ),
    "select_all": (
        "Gui.Selection.clearSelection()\n"
        "if App.ActiveDocument is not None:\n"
        "    for obj in App.ActiveDocument.Objects:\n"
        "        Gui.Selection.addSelection(obj)\n"
    ),
}

_SCENE_MSG = {
    "clear": "Yeni, boş bir FreeCAD belgesi açıldı.",
    "delete_selected": "Seçili nesne(ler) silindi.",
    "select_all": "Tüm nesneler seçildi.",
}


def scene_command(action: str) -> str:
    """action: clear | delete_selected | select_all"""
    action = (action or "").lower().strip()
    code = _SCENE_CODE.get(action)
    if not code:
        return "Bu FreeCAD belge komutunu bilmiyorum (yeni belge / seçiliyi sil / hepsini seç)."
    if not is_bridge_alive():
        return ("FreeCAD'i benim açmam gerekiyor ('freecad aç' de) — "
                "şu an açık pencereye bağlı değilim.")
    result = send_code(code)
    if "çalıştırıldı" in result:
        return _SCENE_MSG[action]
    return f"Yapılamadı — {result}"
