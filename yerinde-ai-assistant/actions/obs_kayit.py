"""
actions/obs_kayit.py — OBS Studio ekran kaydını sesli komutla kontrol eder
(başlat / duraklat / devam ettir / bitir).

OBS 28+ ile "obs-websocket" sunucusu dahili gelir (ayrı eklenti kurulmaz).
Bu modül o sunucuya doğrudan WebSocket ile bağlanıp resmi obs-websocket v5
protokolünü konuşur:
  https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md

Gereken tek şey: OBS açık olsun ve Araçlar > obs-websocket Ayarları'ndan
sunucu etkin olsun (varsayılan olarak zaten etkindir, port 4455).
Eğer OBS'te bir şifre ayarlıysa, aynı şifre YERİNDE'nin config dosyasındaki
"obs_ws_password" alanına da yazılmalı (config/api_keys.json).
"""

from __future__ import annotations

import base64
import hashlib
import json
import uuid

try:
    import websocket  # "websocket-client" paketi (requirements.txt'de)
    _HAS_WS = True
except Exception:
    _HAS_WS = False


class ObsError(Exception):
    pass


def _auth_string(password: str, salt: str, challenge: str) -> str:
    """obs-websocket v5 kimlik doğrulama algoritması (SHA256 tabanlı,
    resmi protokol belgesindeki adımların birebir uygulanması):
      1) secret   = base64(sha256(şifre + tuz))
      2) yanıt    = base64(sha256(secret + meydan_okuma))
    """
    secret = base64.b64encode(
        hashlib.sha256((password + salt).encode("utf-8")).digest()
    ).decode("utf-8")
    return base64.b64encode(
        hashlib.sha256((secret + challenge).encode("utf-8")).digest()
    ).decode("utf-8")


def _send_obs_request(request_type: str, host: str, port: int, password: str,
                       timeout: float = 3.0) -> dict:
    """OBS'e tek seferlik bağlanıp (Hello -> Identify -> Request -> yanıt)
    istenen komutu gönderir, responseData sözlüğünü döndürür. Hata varsa
    ObsError fırlatır (çağıran taraf kullanıcıya uygun mesajı gösterir)."""
    if not _HAS_WS:
        raise ObsError(
            "'websocket-client' paketi kurulu değil. Kurmak için: "
            "pip install websocket-client"
        )
    url = f"ws://{host}:{port}"
    try:
        ws = websocket.create_connection(url, timeout=timeout)
    except Exception:
        raise ObsError(
            "OBS'e bağlanılamadı. OBS Studio açık mı ve Araçlar > "
            "obs-websocket Ayarları'ndan sunucu etkin mi kontrol et."
        )

    try:
        hello = json.loads(ws.recv())
        if hello.get("op") != 0:
            raise ObsError("OBS'ten beklenmeyen bir ilk mesaj geldi.")
        hello_d = hello.get("d", {})

        identify_d = {"rpcVersion": hello_d.get("rpcVersion", 1), "eventSubscriptions": 0}
        auth_info = hello_d.get("authentication")
        if auth_info:
            if not password:
                raise ObsError(
                    "OBS-WebSocket şifre istiyor ama YERİNDE ayarlarında OBS "
                    "şifresi girilmemiş (config/api_keys.json > obs_ws_password)."
                )
            identify_d["authentication"] = _auth_string(
                password, auth_info.get("salt", ""), auth_info.get("challenge", "")
            )
        ws.send(json.dumps({"op": 1, "d": identify_d}))

        identified = json.loads(ws.recv())
        if identified.get("op") != 2:
            raise ObsError(
                "OBS kimlik doğrulaması başarısız oldu — şifreyi kontrol et."
            )

        req_id = str(uuid.uuid4())
        ws.send(json.dumps({
            "op": 6,
            "d": {"requestType": request_type, "requestId": req_id},
        }))
        resp = json.loads(ws.recv())
        d = resp.get("d", {})
        status = d.get("requestStatus", {})
        if not status.get("result"):
            raise ObsError(
                f"OBS isteği reddetti: {status.get('comment') or 'bilinmeyen hata'}"
            )
        return d.get("responseData") or {}
    finally:
        try:
            ws.close()
        except Exception:
            pass


def _obs_config():
    from app_config import get_app_config_value
    host = str(get_app_config_value("obs_ws_host", "localhost") or "localhost")
    port = int(get_app_config_value("obs_ws_port", 4455) or 4455)
    password = str(get_app_config_value("obs_ws_password", "") or "")
    return host, port, password


def start_recording() -> str:
    """'ekran kaydı başlat' / 'kayıt başlat' — OBS'te kaydı başlatır."""
    host, port, password = _obs_config()
    try:
        _send_obs_request("StartRecord", host, port, password)
        return "Ekran kaydı başlatıldı."
    except ObsError as e:
        return str(e)


def pause_recording() -> str:
    """'kaydı duraklat' / 'ekran kaydını duraklat' — kaydı duraklatır."""
    host, port, password = _obs_config()
    try:
        _send_obs_request("PauseRecord", host, port, password)
        return "Kayıt duraklatıldı."
    except ObsError as e:
        return str(e)


def resume_recording() -> str:
    """'kaydı devam ettir' — duraklatılmış kaydı kaldığı yerden sürdürür."""
    host, port, password = _obs_config()
    try:
        _send_obs_request("ResumeRecord", host, port, password)
        return "Kayıt kaldığı yerden devam ediyor."
    except ObsError as e:
        return str(e)


def stop_recording() -> str:
    """'ekran kaydını bitir' / 'kaydı sonlandır' — kaydı tamamen durdurur
    ve dosyayı kaydeder."""
    host, port, password = _obs_config()
    try:
        data = _send_obs_request("StopRecord", host, port, password)
        path = data.get("outputPath")
        if path:
            return f"Ekran kaydı tamamlandı. Kayıt dosyası: {path}"
        return "Ekran kaydı tamamlandı."
    except ObsError as e:
        return str(e)
