"""
YERINDE kısayol yardımcıları — CachyOS (Arch Linux) sürümü.

Windows sürümü .lnk kısayolları üretiyordu; CachyOS'ta bunun karşılığı
XDG .desktop dosyalarıdır:
  - Masaüstü kısayolu  → ~/Masaüstü (veya ~/Desktop)/YERINDE.desktop
  - Açılışta başlat     → ~/.config/autostart/yerinde.desktop

Ek bağımlılık gerekmez; standart betikler ile .desktop dosyaları yazılır.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _xdg_desktop_dir() -> Path:
    """xdg-user-dir DESKTOP varsa onu, yoksa ~/Desktop veya ~/Masaüstü'nü kullanır."""
    try:
        out = subprocess.check_output(["xdg-user-dir", "DESKTOP"], text=True, timeout=3).strip()
        if out:
            return Path(out)
    except Exception:
        pass
    for name in ("Desktop", "Masaüstü"):
        candidate = Path.home() / name
        if candidate.exists():
            return candidate
    return Path.home() / "Desktop"


def _autostart_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "autostart"


def _python_exe() -> str:
    import sys
    return sys.executable


def _desktop_entry_contents() -> str:
    main_py = BASE_DIR / "main.py"
    icon_candidate = BASE_DIR / "Icon" / "yerinde.png"
    icon_line = f"Icon={icon_candidate}\n" if icon_candidate.exists() else ""
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=YERINDE\n"
        "Comment=Gerçek zamanlı sesli kişisel AI asistanı\n"
        f"Exec={_python_exe()} \"{main_py}\"\n"
        f"Path={BASE_DIR}\n"
        f"{icon_line}"
        "Terminal=false\n"
        "Categories=Utility;\n"
    )


def _write_desktop_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_desktop_entry_contents(), encoding="utf-8")
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


# ── Masaüstü kısayolu ────────────────────────────────────────────────────────
def desktop_shortcut_path() -> Path:
    return _xdg_desktop_dir() / "YERINDE.desktop"


def create_desktop_shortcut() -> Path:
    return _write_desktop_file(desktop_shortcut_path())


# ── Açılışta başlat (XDG autostart) ──────────────────────────────────────────
def startup_shortcut_path() -> Path:
    return _autostart_dir() / "yerinde.desktop"


def create_startup_shortcut() -> Path:
    return _write_desktop_file(startup_shortcut_path())


def remove_startup_shortcut() -> None:
    path = startup_shortcut_path()
    if path.exists():
        path.unlink()


if __name__ == "__main__":
    created = create_desktop_shortcut()
    print(f"Masaüstü kısayolu oluşturuldu: {created}")
