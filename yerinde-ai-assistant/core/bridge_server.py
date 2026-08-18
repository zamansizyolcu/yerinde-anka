"""
core/bridge_server.py — YERİNDE'nin Python tarafı ile tarayıcıda açık olan
3B Tasarım Stüdyosu / Robot Tasarım Atölyesi / Kukla Kodlama Atölyesi (ve
ileride benzer HTML araçları) arasında canlı komut köprüsü kurar.

Dış bir kütüphaneye ihtiyaç YOK (websockets paketi gerekmez) — Python'ın
kendi socket/threading modülleriyle minimal bir WebSocket sunucusu
(RFC 6455) çalıştırır. Diğer YERİNDE araçlarının "tek dosya, dış bağımlılık
yok" felsefesiyle tutarlıdır.

Akış:
  1) Araç (HTML) tarayıcıda açıldığında, JavaScript tarafı
     ws://127.0.0.1:8765 adresine bağlanır.
  2) YERİNDE'nin ses komutu işleyicisi (actions/tasarim_studyosu.py vb.),
     send_command() ile JSON komutlar gönderir.
  3) Sayfadaki JS bu komutları alıp ilgili işlemi (şekil ekleme, taşıma,
     boyutlandırma, renk değiştirme, STL indirme vb.) uygular.

BİRDEN FAZLA istemci (aynı anda birden fazla araç sekmesi açık olması)
DESTEKLENİR — her yeni bağlantı öncekileri KAPATMAZ, tüm bağlı istemcilere
YAYIN yapılır. Her aracın kendi JS'i, anlamadığı "action" değerlerini
sessizce yok sayar, bu yüzden yayın yapmak güvenlidir (örn. Kukla Kodlama
Atölyesi'ne "add_shape" gitse bile o kod bunu tanımadığı için hiçbir şey
yapmaz).
"""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading

HOST = "127.0.0.1"
PORT = 8765
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

_server_thread: threading.Thread | None = None
_server_socket: socket.socket | None = None
_client_lock = threading.Lock()
_clients: set[socket.socket] = set()
_started = False

# Tarayıcıdan gelen (tek yönlü degil, CEVAP niteliginde) metin mesajlarini
# yakalamak icin: request_and_wait() bir istek gonderip bu event'i bekler.
_response_lock = threading.Lock()
_response_event = threading.Event()
_response_data: str | None = None

# Tarayıcının KENDİLİĞİNDEN (Python bir şey istemeden — örn. bir düğmeye
# tıklandığında) gönderdiği tetikleyici mesajlar için: her mesajın "type"
# alanına göre kayıtlı bir geri çağırma fonksiyonu ayrı bir thread'de çağrılır.
_trigger_lock = threading.Lock()
_trigger_callbacks: dict = {}


def register_trigger(message_type: str, callback) -> None:
    """Tarayıcıdan `{"type": message_type, ...}` şeklinde bir mesaj geldiğinde
    (bu, aktif bir request_and_wait() cevabı DEĞİLSE) callback(payload) çağrılır
    — AYRI bir thread'de, böylece WebSocket okuma döngüsünü bloklamaz."""
    with _trigger_lock:
        _trigger_callbacks[message_type] = callback


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
        # ÖNEMLİ: istemciyi "bağlı" olarak ÖNCE kaydet, el sıkışma cevabını
        # SONRA gönder. Aksi halde istemci (tarayıcı) cevabı alır almaz bir
        # komut bekleyebilir; sunucu henüz kendi defterine "bağlandı" diye
        # yazmadan bu an gelirse komut sessizce kaybolurdu (yarış durumu).
        _register_client(conn)
        conn.sendall(response.encode("utf-8"))
        conn.settimeout(None)
        return True
    except Exception:
        _unregister_client(conn)
        return False


def _register_client(conn: socket.socket) -> None:
    # ESKİ bağlantıları KAPATMIYORUZ artık — birden fazla araç sekmesi aynı
    # anda bağlı kalabilsin diye (bkz. modül başındaki açıklama).
    with _client_lock:
        _clients.add(conn)


def _unregister_client(conn: socket.socket) -> None:
    with _client_lock:
        _clients.discard(conn)


def encode_text_frame(payload: str) -> bytes:
    """Sunucudan istemciye METIN cercevesi (opcode 0x1). Sunucudan giden
    cerceveler RFC 6455 geregi MASKELENMEZ (maskeleme sadece istemciden
    sunucuya giden cerceveler icin zorunludur)."""
    data = payload.encode("utf-8")
    length = len(data)
    if length <= 125:
        header = struct.pack("!BB", 0x81, length)
    elif length <= 65535:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    return header + data


def decode_frame(conn: socket.socket):
    """Istemciden gelen TEK bir cerceveyi okur (parcalanmis/fragmented
    cerceveleri desteklemez — bu kullanim icin gerekmiyor). Donus:
    (opcode, payload_bytes) ya da baglanti kapandiysa (None, None)."""
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


def _client_reader_loop(conn: socket.socket) -> None:
    global _response_data
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
            if opcode == 0x1 and payload:  # metin - tarayicidan gelen cevap/veri
                try:
                    text = payload.decode("utf-8", errors="replace")
                except Exception:
                    text = None
                if text is not None:
                    handled_as_trigger = False
                    try:
                        parsed = json.loads(text)
                        msg_type = parsed.get("type") if isinstance(parsed, dict) else None
                        with _trigger_lock:
                            callback = _trigger_callbacks.get(msg_type)
                        if callback is not None:
                            handled_as_trigger = True
                            threading.Thread(target=callback, args=(parsed,), daemon=True).start()
                    except Exception:
                        pass
                    if not handled_as_trigger:
                        with _response_lock:
                            _response_data = text
                        _response_event.set()
    except OSError:
        pass
    finally:
        _unregister_client(conn)
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


def ensure_started() -> None:
    """Köprü sunucusunu (henüz başlamadıysa) arka planda başlatır. Birden
    fazla çağrılsa bile yalnızca BİR kez gerçekten sunucu açar."""
    global _server_thread, _server_socket, _started
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
        # Port zaten kullanımda olabilir (örn. sunucu başka bir nedenle zaten
        # çalışıyor) — sessizce devam ederiz.
        pass


def is_client_connected() -> bool:
    with _client_lock:
        return len(_clients) > 0


def send_command(payload: dict) -> bool:
    """TÜM bağlı istemcilere (açık her araç sekmesine) bir JSON komut
    YAYINLAR. Her istemci, anlamadığı komutları kendi tarafında sessizce
    yok sayar. En az bir istemciye başarıyla gönderilebildiyse True döner;
    hiç bağlı istemci yoksa False döner (çağıran, kullanıcıya önce aracı
    açması gerektiğini söyleyebilir)."""
    with _client_lock:
        targets = list(_clients)
    if not targets:
        return False
    frame = encode_text_frame(json.dumps(payload, ensure_ascii=False))
    any_ok = False
    for conn in targets:
        try:
            conn.sendall(frame)
            any_ok = True
        except OSError:
            _unregister_client(conn)
    return any_ok


def request_and_wait(payload: dict, timeout: float = 6.0) -> str | None:
    """Bağlı istemci(ler)e bir istek YAYINLAR ve İLK gelen metin cevabını
    bekler (örn. sahne verisini Blender'a aktarmak için). Birden fazla araç
    sekmesi açıksa, isteği yalnızca o isteği ANLAYAN araç (kendi action
    tipine göre) gerçekten yanıtlar — diğerleri sessizce yok sayar. Zaman
    aşımında ya da hiç istemci bağlı değilse None döner."""
    with _response_lock:
        _response_event.clear()
    if not send_command(payload):
        return None
    got = _response_event.wait(timeout)
    if not got:
        return None
    with _response_lock:
        return _response_data
