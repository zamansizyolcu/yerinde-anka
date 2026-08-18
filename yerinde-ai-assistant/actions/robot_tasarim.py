"""
actions/robot_tasarim.py — Robot Tasarım Atölyesini tarayıcıda açar.

Bu araç, 3B Tasarım Stüdyosu ile AYNI motoru (Three.js sahne yönetimi, CSG
delik/birleştirme, kenar yumuşatma, malzeme/doku, animasyon, eklem/hiyerarşi
sistemi, Blender aktarımı) paylaşır — sadece farklı bir marka/başlıkla ve
robot parçalarına (gövde, tekerlek, eklem, kol, sensör, motor) odaklanan bir
palet ile açılır. Kullanıcıya YERİNDE içinde AYRI bir uygulama olarak görünür.

ÖNEMLİ: actions/tasarim_studyosu.py içindeki TÜM sesli komutlar (şekil ekle,
taşı, boyutlandır, döndür, kopyala, kenar yumuşat, delik yap/uygula,
birleştir/geri al, STL indir, Blender'a aktar) bu araç açıkken de OLDUĞU GİBİ
çalışır — çünkü ikisi de aynı WebSocket köprüsüne (core/bridge_server.py)
bağlanır ve aynı komut JSON'unu anlar. Bu yüzden burada SADECE 'aç' komutu
tanımlanır; geri kalan komutlar zaten paylaşılan koddadır.
"""

from __future__ import annotations

import platform
import subprocess
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "robot-tasarim-atolyesi" / "robot-tasarim-atolyesi.html"


def open_robot_tasarim_araci() -> str:
    """'robot tasarım atölyesini aç' / 'robot tasarım aracını aç' /
    '3 boyutlu robot tasarlama aracını aç' / 'robot yapma aracını aç'
    — gövde, tekerlek, eklem, kol ve sensör gibi parçalardan robot
    tasarlayabileceğin, eklemli (birlikte hareket eden) parçalar
    kurabileceğin aracı tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("Robot Tasarım Atölyesi bulunamadı — 'robot-tasarim-atolyesi' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    # Aynı tetikleyiciyi (Blender'a Aktar düğmesi vb.) burada da kaydet -
    # 3B Tasarım Stüdyosu ile birebir aynı mekanizma.
    from actions.tasarim_studyosu import _handle_export_trigger
    bridge_server.register_trigger("blender_export_trigger", _handle_export_trigger)
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("Robot Tasarım Atölyesi tarayıcıda açılıyor! Soldan gövde, tekerlek, "
                "eklem, kol parçası, sensör ya da motor ekleyebilir; özellik "
                "panelindeki 'Bağlı Olduğu Parça' ile parçaları birbirine bağlayıp "
                "eklemli bir robot kurabilirsin. Sesli komutlarla da yönlendirebilirsin.")
    except Exception:
        try:
            webbrowser.open(url)
            return "Robot Tasarım Atölyesi tarayıcıda açılıyor!"
        except Exception as e:
            return f"Açılamadı: {e}"
