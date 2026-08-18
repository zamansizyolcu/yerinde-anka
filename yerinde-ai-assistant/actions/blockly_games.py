"""
actions/blockly_games.py — Blockly Games'i (Google'ın Türkçe bulmaca tabanlı
kodlama oyunları) sesle açma.

ÖNEMLİ FARK: Blockly Games, Scratch gibi bir MASAÜSTÜ uygulaması DEĞİL —
tarayıcıda çalışan statik bir web sitesi. Bloklar fare ile sürüklenerek
yapılıyor, Scratch'teki gibi bir proje DOSYASI (.sb3 gibi) üretip
manipüle etme imkânı yok. Bu yüzden bu modülün kapsamı BİLİNÇLİ olarak
sınırlı tutuldu (kullanıcıyla konuşup netleştirildi): doğru oyunu/seviyeyi
TARAYICIDA AÇMAK — öğretmenin "labirent aç" diyip öğrencilere doğru
bulmacayı anında göstermesi için.

DÜZELTME (gerçek kullanıcı testinde bulundu): Dosyaları doğrudan
"file://" ile açmak İKİ soruna yol açıyordu:
  1) Sayfanın kullandığı "/common/storage.js" gibi KÖK-GÖRELİ yollar,
     file:// altında (sunucu kökü olmadığı için) yanlış konuma (C:\\common\\)
     bakıp 404 veriyordu.
  2) Chrome, HER "file://" adresini BENZERSİZ bir güvenlik kaynağı
     sayıyor — bu da sayfalar/seviyeler arası geçişte "Unsafe attempt to
     load URL... file: URLs are treated as unique security origins"
     hatasına yol açıyordu (seviye değiştirince sayfa yenilenip 1.
     seviyeye dönmesinin sebebi buydu).
ÇÖZÜM: Oyunları KENDİ küçük yerel web sunucumuzdan (http://127.0.0.1:PORT)
sunuyoruz — internet gerekmez, sadece bilgisayarın kendi içinde, dosyalar
artık gerçek bir web sitesi gibi AYNI kaynaktan geliyor.

Oyunlar bu projeyle birlikte (blockly-games/ klasöründe) GELİYOR.
"""

from __future__ import annotations

import http.server
import platform
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

# Türkçe oyun adı -> tr/ klasöründeki HTML dosyası
GAMES = {
    "labirent": "maze.html",
    "kuş": "bird.html",
    "kus": "bird.html",
    "gölet": "pond-duck.html",
    "golet": "pond-duck.html",
    "gölet öğretici": "pond-tutor.html",
    "gölet eğitici": "pond-tutor.html",
    "kaplumbağa": "turtle.html",
    "kaplumbaga": "turtle.html",
    "bulmaca": "puzzle.html",
    "film": "movie.html",
    "müzik": "music.html",
    "muzik": "music.html",
    "hakkında": "about.html",
    "hakkinda": "about.html",
}
HUB_ALIASES = ("blockly games", "blockly oyunları", "blockly oyunlari",
               "oyun merkezi", "oyun listesi", "ana sayfa")

_server = None
_server_port: int | None = None
_server_lock = threading.Lock()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _games_folder() -> Path:
    return _project_root() / "blockly-games" / "tr"


def ensure_local_server() -> int:
    """
    blockly-games/ klasörünü bir HTTP sunucusuyla sunar (file:// kısıtlamalarını
    tamamen ortadan kaldırır). Bir kez başlar; sonraki her çağrıda AYNI portu
    döner (oturum boyunca tek sunucu, gereksiz yere ikinci bir tane açılmaz).
    """
    global _server, _server_port
    with _server_lock:
        if _server is not None and _server_port is not None:
            return _server_port

        folder = str(_project_root() / "blockly-games")

        class _QuietHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=folder, **kwargs)

            def log_message(self, *args):
                pass   # konsolu kirletme — sessiz çalış

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), _QuietHandler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()

        _server = httpd
        _server_port = port
        return port


def _game_url(html_path: str) -> str:
    """'tr/maze.html' gibi bir yolu, yerel sunucu üzerinden GERÇEK bir
    http://127.0.0.1:PORT/... adresine çevirir — artık file:// değil."""
    port = ensure_local_server()
    return f"http://127.0.0.1:{port}/tr/{html_path}"


def _open_url(url: str) -> bool:
    try:
        open_tool_url(url)
        return True
    except Exception:
        try:
            webbrowser.open(url)
            return True
        except Exception:
            return False


def open_blockly_game(name: str) -> str:
    """
    'labirent aç' → maze.html'i (artık http://127.0.0.1:PORT üzerinden)
    tarayıcıda açar. 'blockly games aç' → ana sayfayı açar.
    """
    key = (name or "").lower().strip()
    folder = _games_folder()
    if not folder.exists():
        return ("Blockly Games dosyaları bulunamadı — 'blockly-games' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")

    if key in HUB_ALIASES or not key:
        html_name, label = "index.html", "Blockly Games ana sayfası"
    else:
        html_name = GAMES.get(key)
        if not html_name:
            oyunlar = "labirent, kuş, gölet, kaplumbağa, bulmaca, film, müzik"
            return (f"'{name}' adında bir Blockly Games oyunu bilmiyorum. "
                    f"Bilinenler: {oyunlar}.")
        label = key.capitalize()

    if not (folder / html_name).exists():
        return f"'{html_name}' dosyası bulunamadı — Blockly Games klasörü eksik/bozuk olabilir."

    bridge_server.ensure_started()
    url = _game_url(html_name)
    if _open_url(url):
        return f"{label} tarayıcıda açılıyor."
    return f"{label} açılamadı — bir tarayıcı bulunamadı olabilir."


def blockly_games_kapat_command() -> str:
    """Blockly Games (labirent, kuş, gölet, kaplumbağa, bulmaca, film, müzik
    ya da ana sayfa) tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. 'blockly
    games'i kapat', 'labirent oyununu kapat', 'aracı kapat' gibi komutlarla
    tetiklenir. NOT: bazı tarayıcılar, script tarafından açılmamış
    sekmelerin kapatılmasını güvenlik nedeniyle engeller — bu durumda
    kullanıcının sekmeyi elle kapatması gerekebilir. Ayrıca 'about.html'
    (hakkında) sayfası bu köprüye bağlı değildir, oradan kapatma çalışmaz."""
    if not bridge_server.is_client_connected():
        return ("Blockly Games şu an açık değil gibi görünüyor — önce ilgili "
                "oyunu (ör. 'labirent aç') açar mısın?")
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")
