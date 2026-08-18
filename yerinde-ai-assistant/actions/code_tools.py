"""
Kod/dosya kaydetme araçları — masaüstünde bir "Çalışmalarım" klasörü açıp
içine .py (veya başka metin tabanlı) dosyalar yazar. CachyOS sürümü.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

WORKSPACE_FOLDER_NAME = "Çalışmalarım"


def get_desktop_path() -> Path:
    """CachyOS/Linux masaüstü klasörünü bulur (xdg-user-dir ile)."""
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


def _sanitize_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name or "proje"


def ensure_workspace_folder(project_name: str = "") -> Path:
    base = get_desktop_path() / WORKSPACE_FOLDER_NAME
    if project_name:
        base = base / _sanitize_name(project_name)
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_python_file(filename: str, code: str, project_name: str = "") -> str:
    """
    Verilen Python kodunu masaüstündeki 'Çalışmalarım' klasörüne (istenirse bir
    alt proje klasörüne) .py dosyası olarak kaydeder.
    """
    if not filename:
        return "Dosya adı belirtilmedi."
    if not code or not code.strip():
        return "Kaydedilecek kod boş, hiçbir şey yazılmadı."

    filename = _sanitize_name(filename)
    if not filename.lower().endswith(".py"):
        filename += ".py"

    try:
        folder = ensure_workspace_folder(project_name)
        file_path = folder / filename
        file_path.write_text(code, encoding="utf-8")
        return f"Kaydedildi: {file_path}"
    except Exception as e:
        return f"Dosya kaydedilemedi: {e}"


def save_text_file(filename: str, content: str, project_name: str = "") -> str:
    """save_python_file ile aynı ama uzantıyı zorlamaz — herhangi bir metin dosyası için."""
    if not filename:
        return "Dosya adı belirtilmedi."
    if content is None:
        return "Kaydedilecek içerik boş."
    try:
        folder = ensure_workspace_folder(project_name)
        file_path = folder / _sanitize_name(filename)
        file_path.write_text(content, encoding="utf-8")
        return f"Kaydedildi: {file_path}"
    except Exception as e:
        return f"Dosya kaydedilemedi: {e}"
