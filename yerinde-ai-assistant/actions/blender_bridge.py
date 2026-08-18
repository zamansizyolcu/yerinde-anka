"""
actions/blender_bridge.py — Açık Blender'ın İÇİNDE bpy betiği çalıştırma.

Nasıl çalışır?
  • Blender'ı BİZ açarsak (open_app "blender"/"tasarım"), yanında küçük bir
    dinleyici betik yüklenir: 127.0.0.1:5959'da bekler, gelen Python kodunu
    Blender'ın ana döngüsünde (bpy.app.timers) çalıştırır — nesne ANINDA
    sahnede belirir.
  • "masa çiz" dendiğinde üretilen bpy kodu bu sokete gönderilir.
  • Blender köprüsüz açılmışsa (elle açtıysan): kod bir .py olarak kaydedilir
    ve 'blender --python betik.py' ile YENİ pencerede çalıştırılır; log'a
    "canlı mod için Blender'ı YERINDE ile aç" notu düşer.
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
PORT = 5959

_LISTENER = r'''
# YERINDE Blender köprüsü — gelen bpy kodunu ana döngüde çalıştırır.
import bpy, socket, threading, queue, traceback
_q = queue.Queue()

def _serve():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 5959)); s.listen(4)
    except Exception:
        print("[YERINDE] Kopru soketi acilamadi - Blender normal calisiyor.")
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

def _pump():
    try:
        while True:
            conn, code = _q.get_nowait()
            try:
                exec(compile(code, "<yerinde>", "exec"), {"bpy": bpy, "__name__": "__main__"})
                conn.sendall(b"OK")
            except Exception:
                conn.sendall(("HATA:\n" + traceback.format_exc()[-800:]).encode("utf-8"))
            finally:
                conn.close()
    except queue.Empty:
        pass
    return 0.2

def _skip_splash():
    """Blender acilis ekranini otomatik gec ve 'Genel' duzenini yukle.
    (Kullanici her seferinde 'Genel'e tiklamak zorunda kalmasin.)"""
    try:
        bpy.context.preferences.view.show_splash = False
        try:
            bpy.ops.wm.save_userpref()      # bir daha hic gosterilmesin
        except Exception:
            pass
        # Ana dosyayi yeniden yukle: splash kapanir, Genel duzeni acilir
        bpy.ops.wm.read_homefile(use_empty=False)
        print("[YERINDE] Acilis ekrani gecildi - Genel duzen hazir.")
    except Exception:
        traceback.print_exc()
    return None                              # timer bir kez calissin

try:
    threading.Thread(target=_serve, daemon=True).start()
    bpy.app.timers.register(_skip_splash, first_interval=0.5)
    bpy.app.timers.register(_pump, persistent=True)
    print("[YERINDE] Blender koprusu hazir (127.0.0.1:5959)")
except Exception:
    traceback.print_exc()
    print("[YERINDE] Kopru baslatilamadi; Blender normal modda devam ediyor.")
'''


def _clean_env() -> dict:
    """
    KRİTİK: Blender KENDİ gömülü Python'unu kullanır. Bizim venv'imizin
    PYTHONHOME/PYTHONPATH/VIRTUAL_ENV değişkenleri Blender'a sızınca Blender
    yanlış Python kütüphanelerini yüklemeye çalışıp ÇÖKÜYOR (Linux'ta yaşanan
    "blender açılınca her şey bozuluyor" sorununun ana sebebi).
    LD_PRELOAD ve LD_LIBRARY_PATH de temizleniyor (OpenMP/torch çakışması).
    """
    env = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP", "VIRTUAL_ENV",
                "PYTHONEXECUTABLE", "LD_PRELOAD", "LD_LIBRARY_PATH",
                "OMP_NUM_THREADS", "KMP_DUPLICATE_LIB_OK"):
        env.pop(key, None)
    # venv'in bin dizinini PATH'ten çıkar
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        parts = [p for p in env.get("PATH", "").split(os.pathsep)
                 if not p.startswith(venv)]
        env["PATH"] = os.pathsep.join(parts)
    return env


def _listener_path() -> Path:
    """Betigi ev dizinine yazar: snap/flatpak ile paketlenmis Blender proje
    klasorunu okuyamayabilir; ev dizini her zaman erisilebilir."""
    try:
        d = Path.home() / ".yerinde"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "blender_listener.py"
    except Exception:
        p = BASE_DIR / "blender_listener.py"
    if not p.exists() or p.read_text(encoding="utf-8") != _LISTENER:
        p.write_text(_LISTENER, encoding="utf-8")
    return p


def find_blender() -> list[str] | None:
    """Blender başlatma KOMUTUNU (liste) döner — flatpak/snap dahil.
    Eski sürüm yalnızca PATH'e bakıyordu; CachyOS/Pardus'ta flatpak ya da
    /opt kurulumları 'uygulama bulunamadı' hatasının sebebiydi."""
    if _IS_WINDOWS:
        import glob
        for pat in (r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
                    r"C:\Program Files\Blender*\blender.exe"):
            hits = sorted(glob.glob(pat), reverse=True)
            if hits:
                return [hits[0]]
        w = shutil.which("blender")
        return [w] if w else None

    # Linux: PATH → bilinen yollar → snap → flatpak
    w = shutil.which("blender")
    if w:
        return [w]
    import glob
    for pat in ("/usr/bin/blender", "/usr/local/bin/blender",
                str(Path.home() / ".local/bin/blender"),
                "/opt/blender*/blender", "/snap/bin/blender"):
        hits = sorted(glob.glob(pat), reverse=True)
        if hits:
            return [hits[0]]
    try:
        r = subprocess.run(["flatpak", "info", "org.blender.Blender"],
                           capture_output=True, timeout=5)
        if r.returncode == 0:
            return ["flatpak", "run", "org.blender.Blender"]
    except Exception:
        pass
    return None


def is_bridge_alive(timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=timeout):
            return True
    except Exception:
        return False


def launch_blender_with_bridge() -> str:
    """Blender'i kopru dinleyicisiyle acar (open_app 'blender/tasarim' bunu kullanir)."""
    if is_bridge_alive():
        return "Blender zaten köprüyle açık."
    cmd = find_blender()
    if not cmd:
        return ("Blender bulunamadı. PATH'te, /opt'ta, snap'te ya da flatpak'te "
                "(org.blender.Blender) arandı — kurulumunu kontrol et.")
    log_path = Path(tempfile.gettempdir()) / "yerinde_blender.log"

    def _spawn(extra):
        log_f = open(log_path, "w")
        kwargs = dict(stdout=log_f, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL, close_fds=True,
                      env=_clean_env())          # venv sızıntısı YOK
        if _IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True   # tamamen ayrı oturum
        # -noaudio: Blender açılırken ses aygıtını (ALSA/Pulse) ele geçiriyor;
        # bizim mikrofon akışımızla çakışıp YERINDE'nin çökmesine yol açabiliyordu
        # (Linux'ta yaşanan "Blender açılınca uygulama kapanıyor" sorunu).
        proc = subprocess.Popen(cmd + ["-noaudio"] + extra, **kwargs)
        try:
            log_f.close()        # tanıtıcıyı bizde tutma
        except Exception:
            pass
        return proc

    try:
        proc = _spawn(["--python", str(_listener_path())])
    except Exception as e:
        return f"Blender açılamadı: {e}"

    for _ in range(75):                       # ~15 sn bekle
        if is_bridge_alive():
            return "Blender açıldı (canlı komut köprüsü hazır — 'masa çiz' diyebilirsin)."
        if proc.poll() is not None:           # SUREC OLDU (Pardus'ta yasanan durum)
            break
        time.sleep(0.2)

    if proc.poll() is not None:
        # Kopru betigiyle acilamiyor: sebebi logdan oku, KOPRUSUZ tekrar ac ki
        # kullanici en azindan Blender'i kullanabilsin.
        reason = ""
        try:
            lines = [l for l in log_path.read_text(errors="replace").splitlines() if l.strip()]
            reason = lines[-1][:150] if lines else ""
        except Exception:
            pass
        try:
            _spawn([])
        except Exception as e:
            return f"Blender açılamadı: {e}"
        return ("Blender açıldı (canlı çizim köprüsü bu kurulumda çalışmadı"
                + (f" — sebep: {reason}" if reason else "")
                + f"; ayrıntı: {log_path}). 'Masa çiz' dersen betik ayrı bir "
                  "Blender penceresinde çalıştırılır.")

    return (f"Blender başlatıldı ama köprü yanıt vermedi (ayrıntı: {log_path}). "
            "Birkaç saniye sonra tekrar komut verebilirsin.")


def launch_blender_with_file(filepath: str) -> str:
    """Belirtilen .blend dosyasını köprü dinleyicisiyle açar (3B Tasarım
    Stüdyosu'nun 'blend dosyasını aç' komutu bunu kullanır). Mevcut
    launch_blender_with_bridge() ile AYNI mantık, sadece dosya yolu ile."""
    if is_bridge_alive():
        return ("Blender zaten köprüyle açık — önce açık pencereyi kapatıp "
                "tekrar dener misin?")
    p = Path(filepath)
    if not p.exists():
        return f"Dosya bulunamadı: {filepath}"
    cmd = find_blender()
    if not cmd:
        return ("Blender bulunamadı. PATH'te, /opt'ta, snap'te ya da flatpak'te "
                "(org.blender.Blender) arandı — kurulumunu kontrol et.")
    log_path = Path(tempfile.gettempdir()) / "yerinde_blender.log"

    def _spawn(extra):
        log_f = open(log_path, "w")
        kwargs = dict(stdout=log_f, stderr=subprocess.STDOUT,
                      stdin=subprocess.DEVNULL, close_fds=True,
                      env=_clean_env())
        if _IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd + ["-noaudio", str(p)] + extra, **kwargs)
        try:
            log_f.close()
        except Exception:
            pass
        return proc

    try:
        proc = _spawn(["--python", str(_listener_path())])
    except Exception as e:
        return f"Blender açılamadı: {e}"

    for _ in range(75):
        if is_bridge_alive():
            return f"{p.name} Blender'da açıldı (canlı komut köprüsü hazır)."
        if proc.poll() is not None:
            break
        time.sleep(0.2)

    if proc.poll() is not None:
        try:
            _spawn([])
        except Exception as e:
            return f"Blender açılamadı: {e}"
        return f"{p.name} Blender'da açıldı (bu kurulumda köprüsüz mod)."

    return f"Blender başlatıldı ama köprü yanıt vermedi ({p.name})."


def save_blender_project(name: str = "") -> str:
    """Acik Blender sahnesini 'Calismalarim/Blender' klasorune .blend olarak kaydeder."""
    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("Blender")
    base = (name or "tasarim").strip().replace("/", "-") or "tasarim"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.blend"
    if not is_bridge_alive():
        return ("Kaydedebilmem için Blender'ı benim açmam gerekiyor "
                "('blender aç' de) — şu an açık pencereye bağlı değilim.")
    code = "import bpy" + chr(10) + ("bpy.ops.wm.save_as_mainfile(filepath=r'%s')" % target) + chr(10)
    result = send_code(code)
    if "calistirildi" in result or "çalıştırıldı" in result:
        return f"Blender tasarımı kaydedildi: {target.name} (Çalışmalarım/Blender klasörü)."
    return f"Kaydedilemedi — {result}"


def send_code(code: str, timeout: float = 30.0) -> str:
    """bpy kodunu açık Blender'a gönderir; köprü yoksa yeni pencerede çalıştırır."""
    if not code.strip():
        return "Çalıştırılacak kod boş."
    if is_bridge_alive():
        try:
            with socket.create_connection(("127.0.0.1", PORT), timeout=timeout) as s:
                s.sendall(code.encode("utf-8") + b"\x00")
                s.settimeout(timeout)
                resp = s.recv(4096).decode("utf-8", "replace")
            return ("Kod Blender içinde çalıştırıldı — sahneye bak!" if resp == "OK"
                    else f"Blender kodu çalıştırırken hata verdi: {resp}")
        except Exception as e:
            return f"Blender köprüsüne gönderilemedi: {e}"
    # Köprü yok → betiği kaydet + yeni pencerede çalıştır
    cmd = find_blender()
    if not cmd:
        return "Blender bulunamadı."
    from actions.code_tools import ensure_workspace_folder
    path = ensure_workspace_folder("Blender") / f"yerinde_{int(time.time())}.py"
    path.write_text(code, encoding="utf-8")
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
                  "env": _clean_env(), "close_fds": True}
        if _IS_WINDOWS:
            kwargs["creationflags"] = _CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd + ["-noaudio", "--python", str(path)], **kwargs)
        return (f"Betik yeni Blender penceresinde çalıştırıldı ({path.name}). "
                "Açık pencerede canlı çizim için Blender'ı 'blender aç' diyerek "
                "YERINDE üzerinden aç.")
    except Exception as e:
        return f"Betik kaydedildi ({path}) ama Blender başlatılamadı: {e}"


# ══ Sahne komutları (LLM'siz, deterministik bpy) ═══════════════════════════
_SCENE_CODE = {
    # Tüm nesneleri sil (sahneyi temizle)
    "clear": (
        "import bpy\n"
        "bpy.ops.object.select_all(action='SELECT')\n"
        "bpy.ops.object.delete(use_global=False)\n"
        "for block in list(bpy.data.meshes):\n"
        "    if block.users == 0: bpy.data.meshes.remove(block)\n"
    ),
    # Seçili nesneleri sil
    "delete_selected": (
        "import bpy\n"
        "if bpy.context.selected_objects:\n"
        "    bpy.ops.object.delete(use_global=False)\n"
    ),
    # Varsayılan küpü sil
    "delete_cube": (
        "import bpy\n"
        "obj = bpy.data.objects.get('Cube') or bpy.data.objects.get('Küp')\n"
        "if obj is None:\n"
        "    for o in bpy.data.objects:\n"
        "        if o.type == 'MESH' and 'cube' in o.name.lower():\n"
        "            obj = o; break\n"
        "if obj is not None:\n"
        "    bpy.data.objects.remove(obj, do_unlink=True)\n"
    ),
    "select_all": (
        "import bpy\n"
        "bpy.ops.object.select_all(action='SELECT')\n"
    ),
}

_SCENE_MSG = {
    "clear": "Sahne temizlendi — tüm nesneler silindi.",
    "delete_selected": "Seçili nesne(ler) silindi.",
    "delete_cube": "Küp silindi.",
    "select_all": "Tüm nesneler seçildi.",
}


def scene_command(action: str) -> str:
    """action: clear | delete_selected | delete_cube | select_all
    Blender'da silme/temizleme işlemleri. Kod LLM'e sorulmadan doğrudan
    çalıştırılır — 'küpü sil', 'sahneyi temizle' her seferinde çalışsın diye."""
    action = (action or "").lower().strip()
    code = _SCENE_CODE.get(action)
    if not code:
        return "Bu Blender sahne komutunu bilmiyorum (sahneyi temizle / küpü sil)."
    if not is_bridge_alive():
        return ("Blender'ı benim açmam gerekiyor ('blender aç' de) — "
                "şu an açık pencereye bağlı değilim.")
    result = send_code(code)
    if "çalıştırıldı" in result:
        return _SCENE_MSG[action]
    return f"Yapılamadı — {result}"
