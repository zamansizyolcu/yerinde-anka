"""
core/remote_server.py — YERİNDE masaüstünü, aynı ağdaki (ya da VPN ile
uzaktan bağlanan) bir TELEFON UYGULAMASINDAN kontrol etmeyi sağlayan
uzaktan erişim sunucusu.

Özellikler:
  - Yazılı/sesli mesajla komut  -> {"type":"text","text":"..."}
  - CANLI EKRAN AKTARIMI        -> telefondan {"type":"screen_on"} gönderilince
    masaüstü ekranı JPEG olarak binary frame ile yayınlanır
    ({"type":"screen_off"} ile kapatılır).
  - DOKUNMATİK FARE KONTROLÜ    -> {"type":"mouse",...} mesajları ile
    telefon dokunmatiki masaüstü faresi gibi kullanılır.

Kullandığı dış kütüphaneler (projenin requirements.txt'sinde zaten var):
  - mss        : ekran görüntüsü yakalama (X11/Windows)
  - Pillow     : JPEG sıkıştırma
  - pyautogui  : fare hareketi/tıklama/kaydırma (X11/Windows)

Wayland oturumlarında (mss/pyautogui çalışmaz) bunun yerine sistem
araçları kullanılır: 'grim' ekran yakalama, 'ydotool' fare kontrolü.
Oturum tespiti _is_wayland() ile yapılır; X11/Windows yolları aynen korunur.

core/bridge_server.py ile AYNI ham WebSocket (RFC 6455) uygulamasını temel
alır — dış kütüphane gerekmez — ama:
  - Farklı bir portta (8766) ve 0.0.0.0'da dinler (bridge_server sadece
    127.0.0.1'de dinler, çünkü o SADECE aynı bilgisayardaki tarayıcı
    sekmeleri içindir; bu sunucu ise BAŞKA bir cihazdan - telefondan -
    erişilebilmesi gerekir).
  - Bir PIN ile kimlik doğrulaması ekler (yerel ağda/VPN'de başkalarının
    izinsiz bağlanıp YERİNDE'yi kontrol etmesini engellemek için).

Akış:
  1) Masaüstü YERİNDE başladığında ensure_started(ui) çağrılır.
  2) Telefon uygulaması ws://<bilgisayarın-ip'si>:8766/ adresine bağlanır,
     İLK mesaj olarak {"type":"auth","pin":"123456"} gönderir.
  3) PIN doğruysa {"type":"auth_ok","mode":"gemini"|"ollama"} döner;
     yanlışsa {"type":"auth_fail"} döner ve o istemci hiçbir komut
     gönderemez.
  4) Doğrulanmış telefon {"type":"text","text":"..."} gönderir ->
     ui.on_text_command(text) çağrılır. Bu, hangi mod aktifse (Gemini
     Live / eski Ollama / yeni V3 çekirdek) FARK ETMEKSİZİN çalışan,
     YERİNDE'nin zaten var olan tek giriş noktasıdır.
  5) Asistanın nihai yanıtı hazır olduğunda (ui.write_log ile "YERİNDE: "
     önekiyle yazıldığında — ui.py'deki kanca bunu yakalar), TÜM
     doğrulanmış telefon istemcilerine {"type":"response","text":"..."}
     olarak yayınlanır.

Telefon -> Masaüstü MESAJLARI (doğrulama sonrası):
  - {"type":"text","text":"..."}          : metin komutu
  - {"type":"screen_on"}                  : canlı ekran akışını başlat
  - {"type":"screen_off"}                 : canlı ekran akışını durdur
  - {"type":"mouse","action":"move","x":..,"y":..}
  - {"type":"mouse","action":"down","x":..,"y":..,"button":"left|right|middle"}
  - {"type":"mouse","action":"up",  "x":..,"y":..,"button":"left|right|middle"}
  - {"type":"mouse","action":"click","x":..,"y":..,"button":"left|right|middle"}
  - {"type":"mouse","action":"scroll","x":..,"y":..,"delta":N}   # N>0 yukarı
  - {"type":"mouse","action":"hscroll","delta":N}                # N>0 sağa

Masaüstü -> Telefon MESAJLARI:
  - {"type":"auth_ok"|"auth_fail"|"response"|"error"|"screen_meta",...}
  - binary frame: 4 bayt sıra numarası (big-endian) + JPEG verisi
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import random
import socket
import struct
import threading
import time

HOST = "0.0.0.0"
PORT = 8766
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_CAPTURE_FPS = 8          # ekran akışı: saniyedeki kare sayısı
_CAPTURE_MAX_WIDTH = 1280  # çok büyük ekranlarda JPEG'i küçült

_server_thread: threading.Thread | None = None
_server_socket: socket.socket | None = None
_client_lock = threading.Lock()
_authed_clients: set = set()  # sadece PIN'i doğru giren istemciler buraya eklenir
_screen_clients: set = set()  # canlı ekran isteyen istemciler
_send_locks: dict = {}        # conn -> threading.Lock (yazma karışmasını önler)
_capture_thread: threading.Thread | None = None
_capture_stop = threading.Event()
_screen_meta: tuple | None = None  # (genişlik, yükseklik) - tam masaüstü boyutu
_started = False
_ui_ref = None


# ---------------------------------------------------------------------
# PIN yönetimi
# ---------------------------------------------------------------------

def get_or_create_pin() -> str:
    """Kaydedilmiş bir PIN varsa onu döner; yoksa rastgele 6 haneli yeni
    bir PIN üretip kaydeder."""
    from app_config import get_app_config_value, save_app_config
    pin = str(get_app_config_value("remote_pin", "") or "").strip()
    if not (pin.isdigit() and len(pin) == 6):
        pin = f"{random.randint(0, 999999):06d}"
        save_app_config({"remote_pin": pin})
    return pin


def regenerate_pin() -> str:
    """Yeni, rastgele bir PIN üretir ve kaydeder (ör. 'PIN'imi biri mi
    öğrendi, yenilemek istiyorum' durumunda)."""
    from app_config import save_app_config
    pin = f"{random.randint(0, 999999):06d}"
    save_app_config({"remote_pin": pin})
    return pin


def get_local_ip() -> str:
    """Bu bilgisayarın yerel ağdaki IP adresini bulmaya çalışır (telefon
    uygulamasına hangi adrese bağlanacağını söylemek için). Gerçek bir
    bağlantı KURMAZ, sadece işletim sisteminin yönlendirme tablosundan
    hangi arayüzün kullanılacağını sorar."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ---------------------------------------------------------------------
# Ham WebSocket (RFC 6455) — core/bridge_server.py ile aynı mantık
# ---------------------------------------------------------------------

def _compute_accept_key(client_key: str) -> str:
    sha1 = hashlib.sha1((client_key + _GUID).encode("utf-8")).digest()
    return base64.b64encode(sha1).decode("utf-8")


def _parse_handshake_headers(request_bytes: bytes) -> dict:
    headers: dict[str, str] = {}
    text = request_bytes.decode("utf-8", errors="ignore")
    for line in text.split("\r\n")[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip().lower()] = v.strip()
    return headers


def _recv_handshake(conn: socket.socket) -> bytes:
    conn.settimeout(5.0)
    data = b""
    try:
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
    except OSError:
        pass
    return data


def _do_handshake(conn: socket.socket) -> bool:
    try:
        raw = _recv_handshake(conn)
        if not raw:
            return False
        headers = _parse_handshake_headers(raw)
        key = headers.get("sec-websocket-key")
        if not key:
            return False
        accept = _compute_accept_key(key)
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        )
        conn.sendall(response.encode("utf-8"))
        conn.settimeout(None)
        return True
    except Exception:
        return False


def encode_text_frame(payload: str) -> bytes:
    data = payload.encode("utf-8")
    length = len(data)
    if length <= 125:
        header = struct.pack("!BB", 0x81, length)
    elif length <= 65535:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + data


def encode_binary_frame(payload: bytes) -> bytes:
    """Tek bir ham WebSocket BINARY (opcode 0x2) çerçevesi üretir."""
    length = len(payload)
    if length <= 125:
        header = struct.pack("!BB", 0x82, length)
    elif length <= 65535:
        header = struct.pack("!BBH", 0x82, 126, length)
    else:
        header = struct.pack("!BBQ", 0x82, 127, length)
    return header + payload


def decode_frame(conn: socket.socket):
    header = conn.recv(2)
    if len(header) < 2:
        return None, None
    b1, b2 = header[0], header[1]
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    length = b2 & 0x7F
    if length == 126:
        ext = conn.recv(2)
        if len(ext) < 2:
            return None, None
        length = struct.unpack("!H", ext)[0]
    elif length == 127:
        ext = conn.recv(8)
        if len(ext) < 8:
            return None, None
        length = struct.unpack("!Q", ext)[0]
    mask_key = conn.recv(4) if masked else b""
    payload = b""
    while len(payload) < length:
        chunk = conn.recv(length - len(payload))
        if not chunk:
            break
        payload += chunk
    if masked and payload:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def _get_conn_lock(conn: socket.socket) -> threading.Lock:
    with _client_lock:
        lock = _send_locks.get(conn)
        if lock is None:
            lock = threading.Lock()
            _send_locks[conn] = lock
        return lock


def _send_frame(conn: socket.socket, frame: bytes) -> bool:
    """Kilidi koruyarak tek bir ham çerçeve gönderir (birden fazla iş parçacığı
    aynı anda yazarsa baytlar karışabilir — bu yüzden kilit gerekli)."""
    with _get_conn_lock(conn):
        try:
            conn.sendall(frame)
            return True
        except OSError:
            return False


def _send_json(conn: socket.socket, obj: dict) -> bool:
    return _send_frame(conn, encode_text_frame(json.dumps(obj, ensure_ascii=False)))


# ---------------------------------------------------------------------
# Fare kontrolü (pyautogui / Wayland'de ydotool)
# ---------------------------------------------------------------------

def _is_wayland() -> bool:
    """Wayland oturumunda mı? pyautogui/mss X11/Windows'a bağımlıdır;
    Wayland'de ydotool/grim gibi gerçek Wayland araçları kullanılmalı."""
    import os
    import platform as _platform
    if _platform.system() == "Windows":
        return False
    return bool(os.environ.get("WAYLAND_DISPLAY")) or \
        os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def _handle_mouse(msg: dict) -> None:
    """Telefonun gönderdiği dokunmatik-fare mesajını gerçek fare olayına
    çevirir. Koordinatlar TAM masaüstü ekran boyutuna göre mutlaktır."""
    action = str(msg.get("action", "")).lower()
    x = msg.get("x")
    y = msg.get("y")
    button = str(msg.get("button", "left")).lower()
    if button not in ("left", "right", "middle"):
        button = "left"

    if _is_wayland():
        _handle_mouse_wayland(action, x, y, button, msg)
        return

    import pyautogui
    pyautogui.FAILSAFE = False

    def _move():
        if x is not None and y is not None:
            pyautogui.moveTo(int(x), int(y), duration=0)

    if action == "move":
        _move()
    elif action == "down":
        _move()
        pyautogui.mouseDown(button=button)
    elif action == "up":
        _move()
        pyautogui.mouseUp(button=button)
    elif action == "click":
        _move()
        pyautogui.click(button=button)
    elif action == "dblclick":
        _move()
        pyautogui.doubleClick(button=button)
    elif action == "scroll":
        _move()
        try:
            delta = int(msg.get("delta", 0) or 0)
        except (TypeError, ValueError):
            delta = 0
        pyautogui.scroll(delta)
    elif action == "hscroll":
        try:
            delta = int(msg.get("delta", 0) or 0)
        except (TypeError, ValueError):
            delta = 0
        pyautogui.hscroll(delta)


def _handle_mouse_wayland(action: str, x, y, button: str, msg: dict) -> None:
    """Wayland: fare olayları ydotool ile gönderilir. mouse_control.py'nin
    KANITLANMIŞ ydotool yardımcılarını yeniden kullanır (mutlak konum,
    tıklama, dikey kaydırma). ydotool basılı tutmayı (down) desteklemediği
    için sürükleme yerine tıklama yapılır."""
    try:
        from actions.mouse_control import (
            _ydotool_move_absolute, _ydotool_click, _ydotool_scroll)
    except Exception:
        return  # ydotool yoksa sessizce geç
    btn = {"left": 272, "right": 273, "middle": 274}.get(button, 272)

    def _move():
        if x is not None and y is not None:
            _ydotool_move_absolute(int(x), int(y))

    if action == "move":
        _move()
    elif action == "down":
        _move()
        _ydotool_click(btn)
    elif action == "up":
        pass  # ydotool ayrı mouseUp desteklemez
    elif action == "click":
        _move()
        _ydotool_click(btn)
    elif action == "dblclick":
        _move()
        _ydotool_click(btn)
        time.sleep(0.08)
        _ydotool_click(btn)
    elif action == "scroll":
        try:
            delta = int(msg.get("delta", 0) or 0)
        except (TypeError, ValueError):
            delta = 0
        _move()
        _ydotool_scroll(delta)
    elif action == "hscroll":
        pass  # ydotool yatay kaydırma desteklemez


# ---------------------------------------------------------------------
# Canlı ekran akışı (mss + Pillow)
# ---------------------------------------------------------------------

def _get_full_screen_size() -> tuple:
    """Birincil monitörün TAM çözünürlüğünü döner (koordinat haritalaması
    bunun üzerinden yapılır). Wayland'de swaymsg/hyprctl/wlr-randr kullanılır."""
    if _is_wayland():
        try:
            from actions.mouse_control import _screen_size_wayland
            return _screen_size_wayland()
        except Exception:
            return _screen_meta or (1920, 1080)
    try:
        import mss
        with mss.mss() as sct:
            mon = sct.monitors[1]
            return int(mon["width"]), int(mon["height"])
    except Exception:
        return _screen_meta or (1920, 1080)


def _jpeg_frame_payload(img) -> bytes | None:
    """PIL görüntüsünü küçültüp JPEG binary frame'e çevirir (başarısızsa None)."""
    try:
        from PIL import Image
        w, h = img.size
        if w > _CAPTURE_MAX_WIDTH:
            nh = int(h * _CAPTURE_MAX_WIDTH / w)
            img = img.resize((_CAPTURE_MAX_WIDTH, nh), Image.BILINEAR)
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=60, optimize=True)
        seq = struct.pack("!I", time.time_ns() & 0xFFFFFFFF)
        return encode_binary_frame(seq + buf.getvalue())
    except Exception:
        return None


def _capture_loop() -> None:
    """Arka plan iş parçacığı: ekranı yakalar, JPEG'e sıkıştırır ve ekran
    isteyen TÜM istemcilere binary frame olarak yayınlar.

    Wayland'de mss çalışmadığı için 'grim' ile PNG yakalanır; X11/Windows'ta
    mss kullanılır."""
    global _capture_thread, _screen_meta
    from PIL import Image

    if _is_wayland():
        import shutil
        import subprocess
        _screen_meta = _get_full_screen_size()
        while not _capture_stop.is_set():
            frame_payload = None
            if shutil.which("grim"):
                try:
                    r = subprocess.run(["grim", "-"], capture_output=True, timeout=3)
                    if r.returncode == 0 and r.stdout:
                        frame_payload = _jpeg_frame_payload(
                            Image.open(io.BytesIO(r.stdout)).convert("RGB"))
                except Exception:
                    frame_payload = None
            else:
                # grim yok: yakalama yapılamıyor ama akışı sonsuza dek boş
                # tutmak yerine istemcileri beklet — kısa uyku ile dön.
                _capture_stop.wait(0.25)
                continue

            if frame_payload is not None:
                with _client_lock:
                    targets = list(_screen_clients)
                if not targets:
                    break  # kimse izlemiyor -> iş parçacığını bitir
                for c in targets:
                    if not _send_frame(c, frame_payload):
                        with _client_lock:
                            _screen_clients.discard(c)
                            _authed_clients.discard(c)
            _capture_stop.wait(1.0 / _CAPTURE_FPS)
        _capture_thread = None
        return

    try:
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            _screen_meta = (int(monitor["width"]), int(monitor["height"]))
            frame_payload = None
            while not _capture_stop.is_set():
                try:
                    shot = sct.grab(monitor)
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                    frame_payload = _jpeg_frame_payload(img)
                except Exception:
                    frame_payload = None

                if frame_payload is not None:
                    with _client_lock:
                        targets = list(_screen_clients)
                    if not targets:
                        break  # kimse izlemiyor -> iş parçacığını bitir
                    for c in targets:
                        if not _send_frame(c, frame_payload):
                            with _client_lock:
                                _screen_clients.discard(c)
                                _authed_clients.discard(c)
                _capture_stop.wait(1.0 / _CAPTURE_FPS)
    except Exception:
        pass
    finally:
        _capture_thread = None


def _ensure_capture_thread() -> None:
    global _capture_thread, _capture_stop
    _capture_stop.clear()
    if _capture_thread is None or not _capture_thread.is_alive():
        _capture_thread = threading.Thread(target=_capture_loop, daemon=True)
        _capture_thread.start()


def _stop_capture_thread() -> None:
    global _capture_thread
    _capture_stop.set()
    _capture_thread = None


# ---------------------------------------------------------------------
# Bağlantı yönetimi
# ---------------------------------------------------------------------

def _remove_client(conn: socket.socket) -> None:
    with _client_lock:
        _authed_clients.discard(conn)
        _screen_clients.discard(conn)
        _send_locks.pop(conn, None)
    if len(_screen_clients) == 0:
        _stop_capture_thread()


def _client_reader_loop(conn: socket.socket) -> None:
    authed = False
    try:
        while True:
            opcode, payload = decode_frame(conn)
            if opcode is None:
                break
            if opcode == 0x8:  # close
                break
            if opcode == 0x9:  # ping -> pong
                try:
                    conn.sendall(struct.pack("!BB", 0x8A, 0))
                except OSError:
                    break
                continue
            if opcode != 0x1 or not payload:
                continue
            try:
                text = payload.decode("utf-8", errors="replace")
                msg = json.loads(text)
            except Exception:
                continue
            if not isinstance(msg, dict):
                continue

            mtype = msg.get("type")

            if not authed:
                if mtype == "auth" and str(msg.get("pin", "")) == get_or_create_pin():
                    authed = True
                    with _client_lock:
                        _authed_clients.add(conn)
                    from app_config import get_model_provider
                    _send_json(conn, {"type": "auth_ok", "mode": get_model_provider()})
                else:
                    _send_json(conn, {"type": "auth_fail"})
                continue

            if mtype == "text":
                text = str(msg.get("text", "")).strip()
                if text and _ui_ref is not None:
                    try:
                        _ui_ref.on_text_command(text)
                    except Exception as e:
                        _send_json(conn, {"type": "error", "text": f"Komut işlenemedi: {e}"})

            elif mtype == "screen_on":
                w, h = _get_full_screen_size()
                _screen_meta = (w, h)
                with _client_lock:
                    _screen_clients.add(conn)
                _send_json(conn, {"type": "screen_meta", "width": w, "height": h})
                _ensure_capture_thread()

            elif mtype == "screen_off":
                with _client_lock:
                    _screen_clients.discard(conn)
                if len(_screen_clients) == 0:
                    _stop_capture_thread()

            elif mtype == "mouse":
                try:
                    _handle_mouse(msg)
                except Exception as e:
                    _send_json(conn, {"type": "error", "text": f"Fare hatası: {e}"})

            elif mtype == "key":
                # Klavye kısayolu (örn. alt_f4 → pencereyi kapat, win_d →
                # masaüstünü göster, alt_tab). keyboard_control.py Wayland'de
                # KDE/global kısayolları (kglobalaccel) veya wtype/ydotool,
                # X11'de pyautogui kullanır.
                try:
                    from actions.keyboard_control import press_key
                    result = press_key(str(msg.get("key", "") or ""))
                    if "GÖNDERİLEMEDİ" in result or "tanımıyorum" in result:
                        _send_json(conn, {
                            "type": "error",
                            "text": result.splitlines()[0],
                        })
                except Exception as e:
                    _send_json(conn, {"type": "error", "text": f"Tuş hatası: {e}"})

            elif mtype == "camera":
                # Telefonun çektiği fotoğrafı aktif görüş motoruyla analiz et
                # (Gemini Vision ya da Ollama VL). Sonuç doğrudan bu istemciye
                # döner; uzun sürebileceği için ayrı iş parçacığında çalışır.
                img_b64 = str(msg.get("image", "") or "")
                prompt = str(msg.get("prompt", "") or "")

                def _handle_camera(_img: str, _prompt: str) -> None:
                    try:
                        import base64 as _b64
                        jpeg = _b64.b64decode(_img)
                        from core.phone_camera import analyze_phone_image
                        result = analyze_phone_image(jpeg, _prompt)
                        _send_json(conn, {"type": "response", "text": result})
                    except Exception as e:
                        _send_json(conn, {"type": "error", "text": f"Kamera analizi hatası: {e}"})

                if img_b64:
                    threading.Thread(
                        target=_handle_camera, args=(img_b64, prompt), daemon=True
                    ).start()
                else:
                    _send_json(conn, {"type": "error", "text": "Görüntü verisi yok."})
    except OSError:
        pass
    finally:
        _remove_client(conn)
        try:
            conn.close()
        except OSError:
            pass


def _accept_loop(server_sock: socket.socket) -> None:
    while True:
        try:
            conn, _addr = server_sock.accept()
        except OSError:
            break
        if not _do_handshake(conn):
            try:
                conn.close()
            except OSError:
                pass
            continue
        threading.Thread(target=_client_reader_loop, args=(conn,), daemon=True).start()


def ensure_started(ui) -> None:
    """Uzaktan erişim sunucusunu (henüz başlamadıysa) arka planda başlatır.
    'ui' referansı, telefon mesajlarını doğru asistan örneğine (Gemini
    Live / Ollama / V3 çekirdek — hangisi aktifse) yönlendirmek için
    saklanır."""
    global _server_thread, _server_socket, _started, _ui_ref
    _ui_ref = ui
    if _started:
        return
    _started = True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT))
        sock.listen(4)
        _server_socket = sock
        _server_thread = threading.Thread(target=_accept_loop, args=(sock,), daemon=True)
        _server_thread.start()
    except OSError:
        # Port zaten kullanımda olabilir - sessizce devam.
        pass


def is_phone_connected() -> bool:
    with _client_lock:
        return len(_authed_clients) > 0


def broadcast_response(text: str) -> None:
    """Asistanın nihai yanıt metnini TÜM doğrulanmış telefon istemcilerine
    yayınlar. ui.py'nin write_log() kancası, 'YERİNDE: ...' önekli her
    satırda bunu çağırır."""
    with _client_lock:
        targets = list(_authed_clients)
    if not targets:
        return
    for conn in targets:
        if not _send_json(conn, {"type": "response", "text": text}):
            _remove_client(conn)
