"""
Bahçe kamerası (Yoosee YS-09 / Xiongmai DVRIP, port 34567) akış yöneticisi.

GardenCamStreamer, actions/webcam_stream.py'deki WebcamStreamer ile aynı
arayüzü sunar (is_active, get_latest_frame, start, stop, last_error) ve ek
olarak wake() (uyku modundan uyandırma) ile ptz(direction) destekler.

dvrip kütüphanesi cihazın login yanıtındaki 'AdminToken' alanını tanımaz;
bu alan yok sayılacak şekilde Object._end_ lenient yapılmadan önce dvrip
sınıfları oluşturulmamalıdır. Bu nedenle tüm dvrip içe aktarımları ve
mesaj sınıfları _init_dvrip() içinde, yama uygulandıktan SONRA oluşturulur.
"""
from __future__ import annotations

import io
import socket
import threading
import time
from types import SimpleNamespace
from typing import Optional

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import pyaudio as _pyaudio_mod
    _pyaudio = _pyaudio_mod
except Exception:  # pragma: no cover
    _pyaudio = None

from app_config import get_app_config_value

DIRECTION_COMMANDS = {
    "left": "DirectionLeft",
    "right": "DirectionRight",
    "up": "DirectionUp",
    "down": "DirectionDown",
    "center": "DirectionCenter",
    "stop": "DirectionStop",
}

# Çapraz hareket: DVRIP tek komut bilmez — sırayla iki eksen komutu gönderilir
# (yönlere göre: önce yatay, sonra dikey). Sıra önemli değil; PTZ motoru
# iki komutu üst üste yorumlayıp çapraz hareket eder.
DIAGONAL_COMMANDS = {
    "up_left":  ("DirectionLeft",  "DirectionUp"),
    "up_right": ("DirectionRight", "DirectionUp"),
    "down_left": ("DirectionLeft",  "DirectionDown"),
    "down_right": ("DirectionRight", "DirectionDown"),
}

# Bu kamera ailesinde (çift sensörlü Yoosee/Xiongmai) DirectionStop TANINMIYOR:
# Ret=100 döner ama motor durmaz. Yalnızca PAN (sağ/sol) durdurulabiliyor — o da
# eksene dik DirectionUp komutuyla (doğrulandı). TILT (yukarı/aşağı) için hiçbir
# komut çalışmıyor (DirectionStop, DirectionLeft, DirectionRight denendi, kamera
# sola kaymaya devam etti); bu yüzden tilt için fren YOK — bırakınca kamera
# doğal olarak dönmeye devam eder, kullanıcı ters yöne sürükleyerek durdurur.
_BRAKE_FOR = {
    "left":  ("DirectionUp",),
    "right": ("DirectionUp",),
    "up":    (),
    "down":  (),
    "up_left":    ("DirectionUp",),
    "up_right":   ("DirectionUp",),
    "down_left":  ("DirectionUp",),
    "down_right": ("DirectionUp",),
}


class GardenCamStreamer:
    """Bahçe kamerası: DVRIP login + HEVC monitör akışı + PTZ kontrolü."""

    def __init__(self, host=None, port=None, username=None, password=None,
                 channel=0, on_log=None, on_state_change=None,
                 on_tool_state=None):
        self.host = host or get_app_config_value("garden_host", "192.168.1.108")
        self.port = int(port or get_app_config_value("garden_port", 34567))
        self.username = username or get_app_config_value("garden_user", "yerinde")
        self.password = password or get_app_config_value("garden_pass", "")
        self.channel = int(channel)
        self.on_log = on_log
        # Akış kendiliğinden kesildiğinde (kamera uyudu vb.) ya da otomatik
        # yeniden bağlanma başarıyla tamamlandığında çağrılır — UI'nin düğme
        # durumunu gerçek zamanlı güncelleyebilmesi için. Manuel aç/kapa'da
        # çağrılmaz (o yolu çağıran taraf zaten set_garden_active yapıyor).
        self.on_state_change = on_state_change
        # Hoparlör / iki yönlü ses durumu değişince çağrılır:
        # on_tool_state(talking, horn) — UI buton renkleri için.
        self.on_tool_state = on_tool_state

        self._active = False
        self._latest = None
        self._latest_lock = threading.Lock()
        self._ctrl_lock = threading.Lock()
        # start/stop/yeniden bağlanma adımlarını tek sıraya dizer — aynı
        # anda iki bağlantı açılmasını (çift monitör akışı) engeller.
        self._lifecycle_lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self.last_error = None

        self._cam = None
        self._sock = None
        self._mon_sock = None
        self._ka_stop = threading.Event()
        self._ka_thread = None

        # Görsel kalite parametreleri (webcam_stream.py ile aynı)
        self._jpeg_quality = 72
        self._max_dim = 640

        # Bu kamera ailesinde (Yoosee YS-09 / Xiongmai DVRIP) kodlanan karenin
        # tabanında gerçek görüntüden bağımsız düz SİYAH bir şerit geliyor
        # (sensör okuması kodlama çözünürlüğünü tam doldurmuyor) — bu da
        # önizlemede görüntünün üstten kesik, altında ise boş/siyah bir alan
        # olarak görünmesine yol açıyordu (bkz. _trim_bottom_letterbox).
        # Kare yüksekliğinin en fazla bu kadarı kırpılabilir (yanlışlıkla
        # karanlık bir SAHNEYİ kesmemek için üst sınır).
        self._letterbox_trim_max_frac = 0.25

        # Yayın tercihi: 'hd' varsayılan; batarya modunda kameranın HD vermemesi
        # durumunda SD (Extra) denenir. app_config 'garden_stream' ile değiştirilebilir.
        self._stream = str(get_app_config_value("garden_stream", "hd")).lower()

        # KeepAlive periyodu: login yanıtındaki AliveInterval'den alınır,
        # uygulama yapılandırması 'garden_keepalive' ile geçersiz kılınabilir.
        self._keepalive_interval = 20.0

        # Akış beklenmedik kesilince (güneş enerjili kamera uyudu) otomatik
        # uyandırma + yeniden bağlanma.
        self._reconnect_stop = threading.Event()
        self._reconnect_worker = None
        self._reconnect_attempts = int(get_app_config_value("garden_reconnect_attempts", 3))
        self._reconnect_sleep = float(get_app_config_value("garden_reconnect_sleep", 8.0))

        # PTZ yön tuşu basılıyken kamera sürekli döner; bırakınca durur. Güvenlik
        # için max süreden sonra da otomatik DirectionStop gönderilir (düğmeden
        # bırakma olayı kaçarsa kamera sonsuza dek dönmesin).
        self._ptz_moving = False
        self._ptz_move_deadline = 0.0
        self._ptz_last_direction = None
        self._ptz_state_lock = threading.Lock()
        self._ptz_max_move = float(get_app_config_value("garden_ptz_max_move", 10.0))
        self._flip_horizontal = bool(get_app_config_value("garden_ptz_flip_left_right", True))
        self._stop_brake = bool(get_app_config_value("garden_ptz_stop_brake", True))
        self._ptz_watchdog_stop = threading.Event()
        self._ptz_watchdog = threading.Thread(
            target=self._ptz_watchdog_loop, daemon=True)
        self._ptz_watchdog.start()

        # İki yönlü ses (TALK): kameraya konuşma. Ayrı bir sokette yaşar;
        # ana kontrol soketini PTZ/KeepAlive ile paylaşmaz.
        self._talking = False
        self._talk_lock = threading.Lock()
        self._talk_sock = None
        self._talk_conn = None
        self._talk_capture = None

        # Hoparlör (siren): kamera DVRIP ses alarm komutunu desteklemediği için
        # iki yönlü ses (OPTalk) kanalı üzerinden üretilen ton akıtılır.
        self._horn_active = False
        self._horn_thread = None

    # ------------------------------------------------------------------ arayüz

    @property
    def is_active(self):
        return self._active

    @property
    def is_talking(self):
        return self._talking

    @property
    def is_horn_active(self):
        return self._horn_active

    def _notify_tool_state(self):
        """Alarm / konuşma durumunu UI'ya bildirir (buton renkleri)."""
        if self.on_tool_state is not None:
            try:
                self.on_tool_state(self._talking, self._horn_active)
            except Exception:
                pass

    def get_latest_frame(self):
        with self._latest_lock:
            if self._latest is None:
                return None
            # WebcamStreamer gibi aynı bytes nesnesini dön (bytes immutable,
            # decode thread'i referansı değiştirir). Böylece 'is _last_sent'
            # tekrar-gönderim önlemesi de çalışır.
            return self._latest

    def start(self):
        """Canlı yayını başlat: önce uyandır, sonra monitör akışı aç."""
        with self._lifecycle_lock:
            if self._active:
                return "already_active"
            # Olası bir yeniden bağlanma işçisi bu yeni oturumdan sorumlu
            # değildir — bayrağı temizleyip bu isteğin kamerayı ele almasını
            # sağla. _reconnect_loop, her denemede _active/_stop_event'i
            # kontrol ettiği için çift akış açılmaz.
            self._reconnect_stop.clear()
            self.last_error = None
            result = self.wake()
            if result != "ok":
                return result
            try:
                self._begin_stream()
                return "ok"
            except Exception as exc:
                self.last_error = str(exc)
                self._log("Bahçe kamerası yayını başlatılamadı: %s" % exc)
                self._cleanup()
                return "error: %s" % exc

    def stop(self):
        """Akışı kapat. Cihaz enerji tasarrufu için kendi kendine uyur."""
        # Otomatik yeniden bağlanmayı da iptal et.
        self._reconnect_stop.set()
        self.talk_stop()
        with self._lifecycle_lock:
            self._stop_event.set()
            self._active = False
            # Kamera dönüyorsa durdurmaya çalış (kapatmadan önce).
            with self._ptz_state_lock:
                self._ptz_moving = False
            if self._cam is not None:
                try:
                    self._request_ptz(self._get_dvrip(), DIRECTION_COMMANDS["stop"])
                except Exception:
                    pass
            if self._thread is not None:
                self._thread.join(timeout=5.0)
                self._thread = None
            self._cleanup()
            self._log("Bahçe kamerası yayını kapatıldı (kamera uyuyabilir).")

    def wake(self):
        """Uyku modundaki kamerayı uyandır: TCP bağlantısı + login."""
        with self._ctrl_lock:
            if self._cam is not None:
                return "ok"
            return self._connect_and_login()

    def _resolve_ptz_commands(self, direction):
        """Yön adından gönderilecek DVRIP komut dizisini bulur.

        'center'/'stop' tek komuttur (kendi kendine tamamlanan/hiç hareket
        gerektirmeyen eylemler). Yönler ise sürekli harekettir; çaprazlar iki
        eksen komutuyla verilir (DVRIP tek komut bilmez).

        Kameranın sol/sağ motor yönü ters dönüyorsa ('garden_ptz_flip_left_right'
        True) sol/sağ komutları kullanıcının beklediği yönle eşleşsin diye
        takas edilir.
        """
        direction = str(direction).lower()
        if direction in ("center", "stop"):
            return (DIRECTION_COMMANDS[direction],)
        commands = DIAGONAL_COMMANDS.get(direction)
        if commands is None:
            single = DIRECTION_COMMANDS.get(direction)
            if single is None:
                self.last_error = "Bilinmeyen PTZ yönü: %s" % direction
                return None
            commands = (single,)
        if self._flip_horizontal and direction in ("left", "right"):
            return tuple("DirectionLeft" if cmd == "DirectionRight"
                         else "DirectionRight" if cmd == "DirectionLeft"
                         else cmd for cmd in commands)
        return commands

    def ptz(self, direction, move_ms=800):
        """Tek atışlık PTZ ittirmesi (sesli komut vb.): yön + otomatik durdurma.

        DVRIP 'DirectionLeft' gibi komutlar SÜREKLİ harekettir: kamera ayrıca
        DirectionStop alana dek dönmeye devam eder. Bu yüzden hareket komutunun
        ardından ~move_ms beklenir ve otomatik DirectionStop gönderilir; yoksa
        kamera "dönmesi durmuyor" denildiği gibi sonsuza dek döner. Arayüzdeki
        yön tuşları bunun yerine basılı tutma kullanır (ptz_start/ptz_stop).
        """
        commands = self._resolve_ptz_commands(direction)
        if commands is None:
            return "error: %s" % self.last_error
        if direction == "stop":
            # Kamera hiç dönmüyorsa (ve bağlantı yoksa) "durdur" için
            # uyandırmaya gerek yok. Ama kamera DÖNÜYORSA bağlantı kopsa bile
            # yeniden bağlanıp durdurma gönderilmeli; yoksa kafa sonsuza
            # dek dönmeye devam eder.
            with self._ptz_state_lock:
                moving = self._ptz_moving
                self._ptz_moving = False
            if self._cam is None and not moving:
                return "ok"
            result = self._ptz_do(self._build_stop_commands(moving=moving),
                                  move_ms=move_ms)
            return result
        # Tek atış: yön + otomatik durdurma (DirectionStop + gerekirse fren).
        commands = commands + tuple(
            self._build_stop_commands(moving=True, for_direction=direction))
        result = self._ptz_do(commands, move_ms=move_ms)
        if result == "ok" and direction not in ("center", "stop"):
            with self._ptz_state_lock:
                self._ptz_last_direction = direction
        return result

    def ptz_start(self, direction):
        """Yön tuşuna basılınca sürekli hareket başlatır (otomatik durdurmaz).

        Kamera, ayrıca DirectionStop alana dek döner; kullanıcı tuşu bırakınca
        (ptz_stop) veya güvenlik süresi dolunca durur. Kamera kapalıysa önce
        uyandırılır.
        """
        commands = self._resolve_ptz_commands(direction)
        if commands is None:
            return "error: %s" % self.last_error
        result = self._ptz_do(commands, move_ms=0)
        if result == "ok":
            with self._ptz_state_lock:
                self._ptz_moving = True
                self._ptz_move_deadline = time.time() + self._ptz_max_move
                if direction not in ("center", "stop"):
                    self._ptz_last_direction = direction
        return result

    def ptz_stop(self):
        """Yön tuşu bırakılınca / DURDUR düğmesinde hareketi keser."""
        with self._ptz_state_lock:
            moving = self._ptz_moving
            self._ptz_moving = False
        return self._ptz_do(self._build_stop_commands(moving=moving), move_ms=0)

    def _build_stop_commands(self, moving=False, for_direction=None):
        """Durdurma komut dizisi.

        Önce standart DirectionStop gönderilir. Bu kamera ailesinde DirectionStop
        tanınmadığından (garden_ptz_stop_brake=True) hareket halindeyken eksene
        dik "fren" komutu da eklenir: pan (sağ/sol) sırasında DirectionUp motoru
        durdurur (doğrulandı). Fren, kamera hareket etmiyorken gönderilmez
        (boşta DirectionUp istenmeyen yukarı hareketi başlatabilir).
        """
        cmds = [DIRECTION_COMMANDS["stop"]]
        if not (moving and self._stop_brake):
            return cmds
        d = for_direction
        if d is None:
            with self._ptz_state_lock:
                d = self._ptz_last_direction
        if d:
            cmds.extend(_BRAKE_FOR.get(d, ()))
        return cmds

    def _ptz_do(self, commands, move_ms=0.0):
        """PTZ komutlarını gönderir; bağlantı koparsa yeni bağlantıyla bir kez daha dener."""
        dvrip = self._get_dvrip()
        if dvrip is None:
            self.last_error = "dvrip kütüphanesi kurulu değil"
            return "error: %s" % self.last_error
        stop_cmd = DIRECTION_COMMANDS["stop"]
        # Komutlar düz string ya da (komut, payload_override) ikilisi olabilir.
        normalized = []
        for item in commands:
            if isinstance(item, tuple):
                normalized.append(item)
            else:
                normalized.append((item, None))
        with self._ctrl_lock:
            for attempt in (1, 2):
                close_after = False
                try:
                    if self._cam is None:
                        result = self._connect_and_login()
                        if result != "ok":
                            return result
                        close_after = True

                    delay = 0.0
                    for command, overrides in normalized:
                        if delay:
                            time.sleep(delay)
                        reply = self._request_ptz(dvrip, command, overrides=overrides)
                        status = getattr(reply, "status", None)
                        ok = getattr(status, "success", False) if status is not None else False
                        if not ok:
                            code = getattr(status, "code", "?") if status is not None else "?"
                            if command == stop_cmd:
                                # Durdurma reddedildi — hareket zaten olmuştur;
                                # tüm işlemi hata sayma, sadece uyar (alternatif
                                # yöntemler listede varsa onlar denenir).
                                self._log("UYARI: PTZ durdurma (DirectionStop) "
                                          "kabul edilmedi (Ret=%s) — alternatif "
                                          "durdurma deneniyor." % code)
                                continue
                            self.last_error = "PTZ hatası (Ret=%s)" % code
                            return "error: %s" % self.last_error
                        # Hareketten sonra, durdurma/sonraki eksen gelmeden önce
                        # motorun dönmesi için kısa bekle.
                        delay = move_ms / 1000.0 if command != stop_cmd else 0.0
                    return "ok"
                except OSError as exc:
                    # Bağlantı koptu (WinError 10053/10054, socket.timeout).
                    self._cleanup()
                    if attempt == 2:
                        self.last_error = "PTZ hatası: %s" % exc
                        self._log("PTZ hatası: %s" % exc)
                        return "error: %s" % self.last_error
                    self._log("PTZ bağlantısı koptu — yeni bağlantıyla yeniden "
                              "deneniyor (%s)" % exc)
                except Exception as exc:
                    self.last_error = "PTZ hatası: %s" % exc
                    self._log("PTZ hatası: %s" % exc)
                    return "error: %s" % self.last_error
                finally:
                    if close_after:
                        self._cleanup()
        return "ok"

    def _request_ptz(self, dvrip, command, overrides=None):
        """Tek PTZ komutunu gönderir; cevap paketi bozuksa hata saymaz."""
        payload = {
            "Channel": self.channel,
            "Command": command,
            "Step": 30,
            "Preset": 65535,
            "Pattern": "Start",
            "Point": 0,
        }
        if overrides:
            payload.update(overrides)
        request = dvrip.DoPTZ(session=self._cam.session, payload=payload)
        try:
            return self._cam.request(request)
        except dvrip.DVRIPDecodeError as exc:
            # Komut ZATEN kameraya ulaştı (sokete yazıldı); sadece cevap paketi
            # beklenen formatta değilse (ör. kamera farklı bir Name döndürürse)
            # işlemi hata sayma — hareket yine de başlamıştır.
            self._log("UYARI: PTZ cevabı okunamadı (%s) — "
                      "komut zaten gönderildi." % exc)
            return None

    def _ptz_watchdog_loop(self):
        """Güvenlik: yön tuşu basılı unutulursa kamera sonsuza dek dönmesin."""
        while not self._ptz_watchdog_stop.is_set():
            if self._ptz_moving and time.time() > self._ptz_move_deadline:
                self._log("PTZ güvenlik süresi doldu, hareket durduruluyor.")
                try:
                    self.ptz_stop()
                except Exception:
                    pass
            self._ptz_watchdog_stop.wait(1.0)

    # ------------------------------------------------------------- iç bağlantı

    def _get_dvrip(self):
        return _get_dvrip()

    def _connect_and_login(self):
        dvrip = self._get_dvrip()
        if dvrip is None:
            self.last_error = "dvrip kütüphanesi kurulu değil"
            return "error: %s" % self.last_error

        # (Yeniden) bağlanma isteği kullanıcının kamerayı kullanmak istediği
        # anlamına gelir — önceki stop()'ta set edilen bayrağı temizle. Bu
        # yapılmazsa _stop_event set kaldığı için "error: durduruldu" döner ve
        # kamera kapatılıp yeniden açılamaz ("kapanınca açılmıyor").
        self._stop_event.clear()

        attempts = int(get_app_config_value("garden_wake_attempts", 4))
        timeout = float(get_app_config_value("garden_wake_timeout", 8.0))
        sleep_between = float(get_app_config_value("garden_wake_sleep", 6.0))
        last_exc = None

        for attempt in range(1, attempts + 1):
            if self._stop_event.is_set():
                return "error: durduruldu"
            try:
                self._log("Bahçe kamerası uyandırılıyor (deneme %d/%d)..." % (attempt, attempts))
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                # DİKKAT: sock.connect() BURADA ÇAĞRILMAZ! dvrip'in
                # DVRIPClient.connect() yöntemi socket.connect()'i KENDİSİ yapar
                # (dvrip/io.py). Soketi önceden bağlarsak aynı soket üzerinde
                # ikinci connect WinError 10056 (WSAEISCONN — "yuva zaten
                # bağlı") verir ve uyandırma HER ZAMAN başarısız olurdu.
                cam = dvrip.DVRIPClient(sock)
                cam.connect((self.host, self.port), self.username, self.password)
                self._cam = cam
                self._sock = sock
                self._keepalive_interval = self._resolve_keepalive_interval(cam)
                self._log("Bahçe kamerası uyandı ve oturum açıldı.")
                return "ok"
            except Exception as exc:
                last_exc = exc
                self._log("Uyandırma denemesi başarısız (%s)" % exc)
                try:
                    sock.close()
                except Exception:
                    pass
                if attempt < attempts:
                    time.sleep(sleep_between)

        self.last_error = "Kamera uyandırılamadı (son hata: %s)" % last_exc
        return "error: %s" % self.last_error

    def _begin_stream(self):
        dvrip = self._get_dvrip()
        # HD (Main) dene; batarya modunda kameranın HD vermemesi durumunda
        # SD (Extra) akışına düş. Her iki deneme de açıkça loglanır.
        stream_choices = [("HD", dvrip.Stream.HD), ("SD", dvrip.Stream.SD)]
        if self._stream == "sd":
            stream_choices.reverse()
        last_exc = None
        for label, stream in stream_choices:
            mon_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            mon_sock.settimeout(10.0)
            try:
                mon_sock.connect((self.host, self.port))
                reader = self._cam.monitor(mon_sock, self.channel, stream)
                self._mon_sock = mon_sock
                self._log("Bahçe kamerası %s (Main) akışı açıldı." % label)
                self._active = True
                self._stop_event.clear()
                self._start_keepalive()
                self._thread = threading.Thread(
                    target=self._decode_loop, args=(reader, label), daemon=True)
                self._thread.start()
                return
            except Exception as exc:
                last_exc = exc
                try:
                    mon_sock.close()
                except Exception:
                    pass
                self._log("Bahçe kamerası %s akışı açılamadı (%s) — sonraki deneniyor." % (label, exc))
        raise last_exc

    def _start_keepalive(self):
        """Oturumu açık tut: DVRIP KeepAlive mesajı (tip 1006) periyodik gönderilir.

        DVRIP oturumları sessiz kalırsa kamera bağlantıyı düşürür — güneş
        enerjili kameralarda bu, "kamera tekrar uyudu" ile aynı belirtiyi verir.
        KeepAlive, PTZ komutuyla AYNI sokete yazar. İkisi aynı anda yazarsa
        protokol bozulur ve kamera bağlantıyı koparır (WinError 10053 —
        "kurulan bağlantı iptal edildi"). Bu yüzden KeepAlive, _ctrl_lock'ı
        kısa süreliğine alır; PTZ aktifken zaten kilidi tuttuğu için KeepAlive
        o turu atlar.

        Periyot, login yanıtındaki 'AliveInterval' değerinden alınır (kamera
        oturumu ne sıklıkta taze tutmak istediğini söyler); app_config'taki
        'garden_keepalive' ile saniye olarak geçersiz kılınabilir.
        """
        self._ka_stop.clear()
        if self._ka_thread is not None:
            return

        def _loop():
            while not self._ka_stop.is_set():
                cam = self._cam
                if cam is None:
                    return
                if self._ctrl_lock.acquire(timeout=0.05):
                    try:
                        if self._ka_stop.is_set():
                            return
                        self._send_keepalive(cam)
                    finally:
                        self._ctrl_lock.release()
                self._ka_stop.wait(self._keepalive_interval)

        self._ka_thread = threading.Thread(target=_loop, daemon=True)
        self._ka_thread.start()

    def _send_keepalive(self, cam):
        """Tek bir KeepAlive isteği (tip 1006) gönderip yanıtını okur.

        Hata durumları sessizce geçilir: kamera uyanıkken bu mesaj bir
        heartbeat'tir; asıl "akış öldü" tespitini _decode_loop yapar ve
        otomatik yeniden bağlanmayı o tetikler.
        """
        dvrip = self._get_dvrip()
        if dvrip is None or not hasattr(dvrip, "KeepAlive"):
            return
        try:
            request = dvrip.KeepAlive(session=cam.session)
            cam.request(request)
        except dvrip.DVRIPDecodeError as exc:
            # Mesaj kameraya ulaştı ama yanıt beklenen formatta değil — oturum
            # muhtemelen hâlâ açık, sorun değil (ptz() ile aynı yaklaşım).
            self._log("UYARI: KeepAlive cevabı okunamadı (%s)" % exc)
        except OSError:
            # Kontrol soketi kapandı / kamera uyudu. _decode_loop bunu zaten
            # algılayıp yeniden bağlanmayı başlatacak; burada sessiz geç.
            pass
        except Exception:
            pass

    def _resolve_keepalive_interval(self, cam):
        """KeepAlive periyodunu belirler.

        Öncelik: app_config 'garden_keepalive' (>=10 sn). Değilse login
        yanıtındaki 'AliveInterval' (kameranın önerdiği aralık). O da yoksa
        20 sn varsayılan.
        """
        try:
            cfg = float(get_app_config_value("garden_keepalive", 0) or 0)
            if cfg >= 10:
                return cfg
        except (TypeError, ValueError):
            pass
        alive = getattr(getattr(cam, "_logininfo", None), "timeout", None)
        try:
            if isinstance(alive, (int, float)) and alive >= 10:
                return float(alive)
        except (TypeError, ValueError):
            pass
        return 20.0

    def _stop_keepalive(self):
        if self._ka_thread is not None:
            self._ka_stop.set()
            self._ka_thread.join(timeout=2.0)
            if self._ka_thread.is_alive():
                self._log("UYARI: KeepAlive thread'i uzun süre bloke kaldı, iptal edildi.")
            # Thread hâlâ canlı olsa bile referansı bırak: _ka_stop set
            # olduğu için eski thread bir sonraki turda çıkar; yeni oturum
            # için yeni thread _start_keepalive'de başlatılır.
            self._ka_thread = None

    # --------------------------------------------------------------- çözümleme

    def _decode_loop(self, reader, stream_label="HD"):
        dvrip = self._get_dvrip()
        container = None
        feeder = None
        try:
            fmt_errors = []
            for fmt in ("hevc", "h264"):
                try:
                    feeder = _DVRIPFeeder(reader, self._stop_event)
                    container = dvrip.av.open(feeder, format=fmt)
                    break
                except Exception as exc:
                    fmt_errors.append("%s: %r" % (fmt, exc))
                    container = None
                    feeder = None
                    continue
            if container is None:
                self.last_error = (
                    "Video akışı çözümlenemedi (%s, %s). av kütüphanesi kurulu mu? "
                    "Ayrıntı: %s" % (stream_label, " | ".join(fmt_errors),
                                     fmt_errors and fmt_errors[-1] or ""))
                self._log(self.last_error)
                return

            for frame in container.decode(video=0):
                if self._stop_event.is_set():
                    break
                try:
                    self._publish_frame(frame)
                except Exception as exc:
                    if self._stop_event.is_set():
                        break
                    self.last_error = "Kare işlenemedi: %s" % exc
                    self._log(self.last_error)
        except Exception as exc:
            if not self._stop_event.is_set():
                import traceback
                self.last_error = "Yayın kesildi (%s): %s" % (stream_label, exc)
                self._log(self.last_error)
                self._log("Yayın kesilme ayrıntısı:\n%s" % traceback.format_exc(limit=6))
        finally:
            if container is not None:
                try:
                    container.close()
                except Exception:
                    pass
            self._active = False
            if self._stop_event.is_set():
                return
            # Akış beklenmedik şekilde sona erdi (kamera uyudu, sinyal kesildi,
            # bağlantı koptu). Soketleri kapatıp otomatik yeniden bağlanmayı
            # başlat; başarı olursa on_state_change ile "streaming" bildirilir.
            self._cleanup()
            self._notify_state(False)
            self._on_stream_lost()

    def _publish_frame(self, frame):
        if cv2 is None:
            return
        img = frame.to_ndarray(format="bgr24")
        img = self._trim_bottom_letterbox(img)
        height, width = img.shape[:2]
        if max(height, width) > self._max_dim:
            scale = self._max_dim / float(max(height, width))
            img = cv2.resize(img, (int(width * scale), int(height * scale)))
        ok, buf = cv2.imencode(
            ".jpg", img,
            [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality])
        if not ok:
            return
        with self._latest_lock:
            # WebcamStreamer ile aynı tip: ham JPEG BYTE dizisi. Numpy buffer
            # saklanırsa UI önizlemesindeki 'if jpeg:' ValueError ile çöker.
            self._latest = buf.tobytes()

    def _trim_bottom_letterbox(self, img):
        """Kare tabanındaki düz SİYAH şeridi (bkz. __init__ notu) kırpar.

        UI tarafı (ui.py: _show_webcam_preview) 16:9'a getirmek için
        görüntüyü SİMETRİK ortalayarak kırpıyor — kaynak karenin tabanında
        zaten siyah bir şerit varsa bu simetrik kırpma şeridi tam
        temizleyemiyor: üstten gerçek görüntüyü keserken altta şeridin bir
        kısmını bırakıyordu ("bahçe kamerası kesik görünüyor, altta boşluk
        var" şikayeti tam olarak bu). Burada kaynağı, UI'a gitmeden ÖNCE,
        gerçek görüntüyle sınırlı hale getiriyoruz.

        Yöntem: taban satırından yukarı doğru tarayıp ortalama parlaklığı
        neredeyse tam siyah (eşik altı) olan bitişik satırları sayar ve
        kırpar. Güvenlik için en fazla '_letterbox_trim_max_frac' kadarını
        kırpar; birkaç pikselden az bir şerit gürültü sayılıp yok sayılır —
        böylece gerçekten karanlık bir sahne (gece görüşü vb.) yanlışlıkla
        kesilmez.
        """
        try:
            height = img.shape[0]
            if height < 40:
                return img
            max_trim = int(height * self._letterbox_trim_max_frac)
            if max_trim < 1:
                return img
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            row_means = gray.mean(axis=1)
            thresh = 12.0  # 0-255 üzerinden — neredeyse tam siyah
            trim = 0
            i = height - 1
            limit = height - max_trim
            while i >= limit and row_means[i] < thresh:
                trim += 1
                i -= 1
            if trim > 4:
                img = img[: height - trim, :]
            return img
        except Exception:
            return img

    # --------------------------------------------------------------- temizlik

    def _cleanup(self):
        self._stop_keepalive()
        with self._ptz_state_lock:
            self._ptz_moving = False
        try:
            if self._mon_sock is not None:
                self._mon_sock.close()
        except Exception:
            pass
        self._mon_sock = None
        try:
            if self._sock is not None:
                self._sock.close()
        except Exception:
            pass
        self._sock = None
        self._cam = None

    # ------------------------------------------------- otomatik yeniden bağlanma

    # -------------------------------------------- alarm / iki yönlü ses

    def set_horn(self, on):
        """Kamera hoparlöründen siren çalar (on=True) / durdurur (on=False).

        Bu kamera OPSoundAlarmControl komutunu desteklemiyor (Ret=102). Bunun
        yerine doğrulanmış iki yönlü ses (OPTalk) kanalı üzerinden üretilen bir
        siren tonu akıtılır; on=True iken zaten çalıyorsa "ok" döner.
        """
        if on:
            with self._talk_lock:
                if self._horn_active:
                    return "ok"
                if self._talking:
                    self._stop_talk_locked()
            self._horn_active = True
            self._horn_thread = threading.Thread(
                target=self._horn_loop, daemon=True)
            self._horn_thread.start()
            self._log("Hoparlör sireni çalmaya başladı...")
            self._notify_tool_state()
            return "ok"
        self._horn_active = False
        if self._horn_thread is not None:
            self._horn_thread.join(timeout=3.0)
            self._horn_thread = None
        self._log("Hoparlör sireni kapatıldı.")
        self._notify_tool_state()
        return "ok"

    def talk_start(self):
        """İki yönlü ses başlat: mikrofondan alınıp kameranın hoparlörüne gönderilir.

        Ayrı bir DVRIP talk bağlantısı (OPTalk) açar; bu bağlantı ana kontrol
        soketinden bağımsız olduğu için PTZ/KeepAlive ile çakışmaz.
        """
        if _pyaudio is None:
            self.last_error = "pyaudio kurulu değil, ses gönderme kapalı"
            return "error: %s" % self.last_error
        with self._talk_lock:
            if self._talking:
                return "ok"
            try:
                self._talk_open_channel()
            except Exception as exc:
                self.last_error = "Ses gönderme başlatılamadı: %s" % exc
                self._log(self.last_error)
                self._talk_close_channel()
                return "error: %s" % self.last_error
            self._talking = True
            self._talk_capture = threading.Thread(
                target=self._talk_capture_loop, daemon=True)
            self._talk_capture.start()
            self._log("İki yönlü ses başladı — kameraya konuşabilirsiniz.")
            self._notify_tool_state()
            return "ok"

    def talk_stop(self):
        """İki yönlü sesi kapatır."""
        with self._talk_lock:
            self._stop_talk_locked()

    def _stop_talk_locked(self):
        """_talk_lock zaten tutuluyorken talk oturumunu kapatır."""
        if not self._talking:
            return
        self._talking = False
        if self._talk_capture is not None:
            self._talk_capture.join(timeout=3.0)
            self._talk_capture = None
        self._talk_close_channel()
        self._log("İki yönlü ses kapatıldı.")
        self._notify_tool_state()

    def _talk_open_channel(self):
        """Talk oturumunu kurar: uyandır, ayrı soket aç, Claim + Start gönder.

        Xiongmai/XM530 protokolü (probe ile doğrulandı): CLAIM yeni açılan
        sokette, START ise ANA kontrol soketinde (self._cam) gönderilir. START
        ana soketi kullandığı için KeepAlive/PTZ ile çakışmaması adına tüm
        kurulum _ctrl_lock altında yapılır.
        """
        dvrip = self._get_dvrip()
        if dvrip is None:
            raise RuntimeError("dvrip kütüphanesi kurulu değil")
        sock = None
        conn = None
        try:
            with self._ctrl_lock:
                if self._cam is None:
                    result = self._connect_and_login()
                    if result != "ok":
                        raise RuntimeError(result)
                session = self._cam.session
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10.0)
                sock.connect((self.host, self.port))
                conn = dvrip.DVRIPClient(sock)
                conn.session = session

                claim = dvrip.TalkClaim(
                    session=session,
                    talk=dvrip.TalkParams(action=dvrip.TalkAction.CLAIM,
                                          audio=dvrip.AudioFormat(
                                              compress="G.711A",
                                              bitrate=128, samplebit=8, samplerate=8000)))
                conn.request(claim)
                start = dvrip.TalkRequest(
                    session=session,
                    talk=dvrip.TalkParams(action=dvrip.TalkAction.START,
                                          audio=dvrip.AudioFormat(
                                              compress="G.711A",
                                              bitrate=128, samplebit=8, samplerate=8000)))
                self._cam.request(start)
        except Exception:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            raise
        self._talk_sock = sock
        self._talk_conn = conn

    def _talk_close_channel(self):
        """Talk kanalını kapatır: START gibi STOP da ana sokette gönderilir."""
        if self._talk_conn is not None:
            dvrip = self._get_dvrip()
            if self._cam is not None and dvrip is not None:
                try:
                    with self._ctrl_lock:
                        stop = dvrip.TalkRequest(
                            session=self._cam.session,
                            talk=dvrip.TalkParams(action=dvrip.TalkAction.STOP,
                                                  audio=dvrip.AudioFormat(
                                                      compress="G.711A",
                                                      bitrate=128, samplebit=8,
                                                      samplerate=8000)))
                        self._cam.request(stop)
                except Exception:
                    pass
        if self._talk_sock is not None:
            try:
                self._talk_sock.close()
            except Exception:
                pass
        self._talk_sock = None
        self._talk_conn = None

    def _talk_capture_loop(self):
        """Mikrofondan 8kHz G.711 A-law alıp talk soketine yazar.

        Bloklayan mikrofondan okuma ile ağ yazımı aynı thread'de; gecikme düşük
        kalsın diye paketler 40 ms (320 örnek) aralıklarla gönderilir.
        """
        try:
            import audioop  # noqa: F401
        except Exception:
            self._log("ERR: Ses gönderme için 'audioop' gerekli.")
            self.talk_stop()
            return
        stream = None
        try:
            pa = _pyaudio.PyAudio()
            stream = pa.open(format=_pyaudio.paInt16, channels=1, rate=8000,
                             input=True, frames_per_buffer=320)
        except Exception as exc:
            self._log("ERR: Mikrofon açılamadı — %s" % exc)
            self.talk_stop()
            return
        header = b"\x00\x00\x01\xfa\x0e\x02\x40\x01"
        self._start_talk_drain(self._talk_conn)
        try:
            while self._talking and self._talk_conn is not None:
                try:
                    data = stream.read(320, exception_on_overflow=False)
                except OSError:
                    continue
                try:
                    alaw = audioop.lin2alaw(data, 2)
                except Exception:
                    continue
                self._talk_send_chunk(header + alaw)
        finally:
            try:
                stream.close()
            except Exception:
                pass
            try:
                pa.terminate()
            except Exception:
                pass

    def _talk_send_chunk(self, payload):
        """Tek bir G.711 ses paketini TALK_CU_PU_DATA (1432) olarak gönderir."""
        conn = self._talk_conn
        dvrip = self._get_dvrip()
        if conn is None or dvrip is None:
            return
        try:
            conn.number += 2
            raw = dvrip.RawTalkData(payload)
            conn.send(conn.number, raw)
        except OSError as exc:
            self._log("UYARI: Ses gönderme bağlantısı koptu (%s)" % exc)
            self.talk_stop()

    @staticmethod
    def _talk_drain_filter():
        """recv() için her paketi tüketip hiçbirini döndürmeyen filtre."""
        yield  # prime the pump
        while True:
            yield None

    def _start_talk_drain(self, conn):
        """Kameradan gelen mikrofon sesini (1433) tüketen thread başlatır.

        Okunmazsa TCP tamponu dolar, kamera ses gönderimini durdurur ve bu da
        konuşma/hoparlör akışını tıkar. Veri lokal oynatılmaz, yalnızca soket
        boş tutulur; kameranın kendi hoparlöründen dönen echo da bu şekilde
        ses çıkışına karışmaz. Soket kapanınca thread kendiliğinden biter.
        """
        if conn is None:
            return

        def _drain():
            try:
                while True:
                    conn.recv(self._talk_drain_filter())
            except Exception:
                pass

        threading.Thread(target=_drain, daemon=True).start()

    def _generate_siren_chunks(self):
        """Siren tonu üretir: 600-1000 Hz arası savaş yapan G.711 A-law parçalar.

        Kamera 8 kHz G.711 A-law aldığı için her parça 40 ms (320 örnek) olarak
        üretilir; _horn_active sıfırlanana dek akıtır.
        """
        import audioop
        import math
        rate = 8000.0
        frames = 320
        t_phase = 0.0
        tone_phase = 0.0
        while self._horn_active:
            chunk = bytearray()
            for _ in range(frames):
                freq = 800.0 + 200.0 * math.sin(t_phase)
                tone_phase += 2.0 * math.pi * freq / rate
                if tone_phase > 2.0 * math.pi:
                    tone_phase -= 2.0 * math.pi
                t_phase += 2.0 * math.pi * 0.5 / rate
                if t_phase > 2.0 * math.pi:
                    t_phase -= 2.0 * math.pi
                sample = int(12000 * math.sin(tone_phase))
                chunk += sample.to_bytes(2, "little", signed=True)
            try:
                yield audioop.lin2alaw(bytes(chunk), 2)
            except Exception:
                break

    def _horn_loop(self):
        """Arka planda talk kanalı üzerinden siren tonu akıtır.

        Kameranın mikrofonu da açıldığı için kendine gelen veri (PU->CU) bir
        drain thread ile okunup atılır; böylece soket tamponu dolmaz ve
        kameranın kendi sesini geri çalması (echo) engellenir. Yalnızca
        üretilen siren parçaları gönderilir.
        """
        import audioop  # noqa: F401
        dvrip = self._get_dvrip()
        sock = None
        conn = None
        me = threading.current_thread()
        try:
            if dvrip is None:
                raise RuntimeError("dvrip kütüphanesi kurulu değil")
            with self._talk_lock:
                with self._ctrl_lock:
                    if self._cam is None:
                        result = self._connect_and_login()
                        if result != "ok":
                            raise RuntimeError(result)
                    session = self._cam.session
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(10.0)
                    sock.connect((self.host, self.port))
                    conn = dvrip.DVRIPClient(sock)
                    conn.session = session

                    claim = dvrip.TalkClaim(
                        session=session,
                        talk=dvrip.TalkParams(action=dvrip.TalkAction.CLAIM,
                                              audio=dvrip.AudioFormat(
                                                  compress="G.711A",
                                                  bitrate=128, samplebit=8,
                                                  samplerate=8000)))
                    conn.request(claim)
                    start = dvrip.TalkRequest(
                        session=session,
                        talk=dvrip.TalkParams(action=dvrip.TalkAction.START,
                                              audio=dvrip.AudioFormat(
                                                  compress="G.711A",
                                                  bitrate=128, samplebit=8,
                                                  samplerate=8000)))
                    self._cam.request(start)
                self._start_talk_drain(conn)
                header = b"\x00\x00\x01\xfa\x0e\x02\x40\x01"
                for chunk in self._generate_siren_chunks():
                    if not self._horn_active:
                        break
                    try:
                        conn.number += 2
                        raw = dvrip.RawTalkData(header + chunk)
                        conn.send(conn.number, raw)
                    except OSError:
                        break
                if self._cam is not None:
                    try:
                        with self._ctrl_lock:
                            stop = dvrip.TalkRequest(
                                session=self._cam.session,
                                talk=dvrip.TalkParams(action=dvrip.TalkAction.STOP,
                                                      audio=dvrip.AudioFormat(
                                                          compress="G.711A",
                                                          bitrate=128, samplebit=8,
                                                          samplerate=8000)))
                            self._cam.request(stop)
                    except Exception:
                        pass
        except Exception as exc:
            self._log("UYARI: Siren bağlantısı kapandı (%s)" % exc)
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass
            # Yalnızca hâlâ bu thread yöneticiyse durumu sıfırla; kullanıcı bu
            # arada yeni bir siren başlatmışsa onun döngüsünü bozma.
            if self._horn_thread is me:
                self._horn_active = False
                self._notify_tool_state()

    def _notify_state(self, streaming):
        """Akışın beklenmedik şekilde kesildiğini/tekrar başladığını bildirir.

        Yalnızca kameranın kendi yaşam döngüsü değişikliklerinde çağrılır —
        örneğin kamera uyuduğunda ya da otomatik yeniden bağlanma akışı
        geri getirdiğinde. Manuel aç/kapa'da çağrılmaz: o yolu yöneten taraf
        (sunucu, webcam_stream) kendi set_garden_active()'ini zaten yapar.
        """
        if self.on_state_change is not None:
            try:
                self.on_state_change(streaming)
            except Exception:
                pass

    def _on_stream_lost(self):
        """Akış beklenmedik kesildiğinde uyandırma + yeniden bağlanma başlatır."""
        self._log("Bahçe kamerası akışı kesildi, kamera uyanıyor ve yeniden bağlanılıyor...")
        if self._reconnect_worker is not None and self._reconnect_worker.is_alive():
            return
        self._reconnect_worker = threading.Thread(
            target=self._reconnect_loop, daemon=True)
        self._reconnect_worker.start()

    def _reconnect_loop(self):
        """Arka planda uyandır/yeniden bağlan döngüsü.

        Her denemede _active ve _stop_event kontrol edilir; böylece kullanıcı
        bu sırada düğmeyle 'kapat' derse ya da yeni bir 'aç' isterse döngü
        kendini durdurur (yeni oturum _reconnect_stop'u temizlemiş olur ve
        start() kamerayı ele alır). _lifecycle_lock, _begin_stream'in
        yeniden bağlanmayla çakışmasını engeller.
        """
        try:
            attempts = max(1, self._reconnect_attempts)
            for i in range(attempts):
                if self._reconnect_stop.is_set() or self._stop_event.is_set():
                    return
                self._log("Yeniden bağlanma denemesi %d/%d..." % (i + 1, attempts))
                try:
                    with self._lifecycle_lock:
                        if (self._reconnect_stop.is_set()
                                or self._stop_event.is_set()):
                            return
                        if self.wake() == "ok":
                            self._begin_stream()
                            # _begin_stream başarılıysa _active=True; döngüyü
                            # buradan çık, akış tekrar kesilirse decode_loop
                            # yeniden başlatacak.
                            if self._active:
                                self._notify_state(True)
                                self._log("Bahçe kamerası akışı yeniden başladı.")
                                return
                except Exception as exc:
                    self.last_error = str(exc)
                    self._log("Yeniden bağlanma denemesi başarısız: %s" % exc)
                    self._cleanup()
                if i < attempts - 1:
                    self._reconnect_stop.wait(self._reconnect_sleep)
        finally:
            self._reconnect_worker = None

    def _log(self, message):
        if self.on_log is not None:
            try:
                self.on_log(message)
            except Exception:
                pass


class _DVRIPFeeder(io.RawIOBase):
    """DVRIPReader'ı PyAV'a besleyen akış. Veri yokken bloklanır."""

    def __init__(self, reader, stop_event, stale_timeout=30.0):
        super().__init__()
        self.reader = reader
        self.stop_event = stop_event
        self.stale_timeout = stale_timeout
        self._lock = threading.Lock()
        self._closed = False
        self._idle_since = time.time()

    def readable(self):
        return True

    def readinto(self, buf):
        if len(buf) == 0:
            return 0
        with self._lock:
            if self._closed:
                return 0
            # Veri gelene kadar BLOKLANIR: PyAV'a None döndürmek onu şaşırtır
            # ve akışı "anında biter" sanmasına yol açar (açılıp hemen kapanma).
            # Burada timeout'ta kısa uykuyla tekrar denenir; yalnızca durdurma
            # isteği (EOF) veya stale_timeout aşımı döngüyü bitirir.
            while not self._closed:
                if self.stop_event.is_set():
                    return 0
                try:
                    data = self.reader.readinto(buf)
                    if data and data > 0:
                        self._idle_since = time.time()
                        return data
                    return 0
                except socket.timeout:
                    if time.time() - self._idle_since > self.stale_timeout:
                        raise OSError("bahçe kamerası yayını durağan (kamera uyudu)")
                    time.sleep(0.05)
                except StopIteration:
                    return 0
                except OSError:
                    if self._closed:
                        return 0
                    raise
            return 0

    def close(self):
        with self._lock:
            self._closed = True
        super().close()


_DVRIP = None
_DVRIP_LOCK = threading.Lock()


def _get_dvrip():
    """dvrip içe aktarılmışsa ad alanını döner (kurulu değilse None)."""
    if _DVRIP is not None:
        return _DVRIP
    with _DVRIP_LOCK:
        if _DVRIP is not None:
            return _DVRIP
        _initialize_dvrip()
        return _DVRIP


def _initialize_dvrip():
    global _DVRIP
    try:
        import av
    except Exception:
        av = None

    try:
        # Kritik: yama, dvrip.io içe aktarılmadan ÖNCE uygulanmalıdır (sınıflar
        # bu noktadan sonra oluşturulur ve 'AdminToken' alanını yok sayar).
        import dvrip.typing as _typing

        @staticmethod
        def _lenient_end(_datum):
            return None

        _typing.Object._end_ = _lenient_end

        from dvrip.errors import DVRIPDecodeError
        from dvrip.io import DVRIPClient
        from dvrip.message import Choice, ControlMessage, ControlRequest, Session, Status
        from dvrip.monitor import Stream
        from dvrip.typing import Object, fixedmember, member, optionalmember, jsontype

        # Sınıf annotasyonları (member[Session] vb.) get_type_hints tarafından
        # modül global'larına göre çözülür; bu isimleri modül seviyesine taşı.
        globals().update({
            "av": av,
            "DVRIPClient": DVRIPClient,
            "DVRIPDecodeError": DVRIPDecodeError,
            "Choice": Choice,
            "ControlMessage": ControlMessage,
            "ControlRequest": ControlRequest,
            "Session": Session,
            "Status": Status,
            "Stream": Stream,
            "Object": Object,
            "fixedmember": fixedmember,
            "member": member,
            "optionalmember": optionalmember,
            "jsontype": jsontype,
        })

        def _json_to_dict(datum):
            if not isinstance(datum, dict):
                raise ValueError("OPPTZControl bir sözlük olmalı")
            return datum

        def _dict_to_json(obj):
            if not isinstance(obj, dict):
                raise ValueError("OPPTZControl bir sözlük olmalı")
            return obj

        class PTZReply(Object, ControlMessage):
            type = 1401
            status: member[Status] = member("Ret")
            session: member[Session] = member("SessionID")
            # Bazı Yoosee/Xiongmai kameralar PTZ cevabında Name'i
            # "OPPTZControl" dışında (hatta hiç göndermeden) döndürür.
            # Cevabı yine de çözümlemek için Name'i zorunlu tutma.
            command: optionalmember[str] = optionalmember("Name")

        class DoPTZ(Object, ControlRequest):
            type = 1400
            reply = PTZReply
            session: member[Session] = member("SessionID")
            command: fixedmember = fixedmember("Name", "OPPTZControl")
            payload: member = member("OPPTZControl",
                                     conv=(_json_to_dict, _dict_to_json))

        class KeepAliveReply(Object, ControlMessage):
            type = 1007
            session: member[Session] = member("SessionID")

        class KeepAlive(Object, ControlRequest):
            type = 1006
            reply = KeepAliveReply
            session: member[Session] = member("SessionID")

        # ------------------------------------------------ iki yönlü ses (OPTalk)

        class TalkAction(Choice):
            CLAIM = "Claim"
            START = "Start"
            STOP = "Stop"

        globals()["TalkAction"] = TalkAction

        class AudioFormat(Object):
            compress: member[str] = member("Compress")
            bitrate: member[int] = member("BitRate")
            samplebit: member[int] = member("SampleBit")
            samplerate: member[int] = member("SampleRate")

        globals()["AudioFormat"] = AudioFormat

        class TalkParams(Object):
            action: member[TalkAction] = member("Action")
            audio: member[AudioFormat] = member("Audio")

        globals()["TalkParams"] = TalkParams

        class TalkReply(Object, ControlMessage):
            # 1431 = OPTalk yanıtı (bu kamerada 1421 'OPPlayBack' döndürüyordu).
            type = 1431
            status: member[Status] = member("Ret")
            session: member[Session] = member("SessionID")
            command: fixedmember = fixedmember("Name", "OPTalk")
            talk: optionalmember[TalkParams] = optionalmember("OPTalk",
                                                              conv=jsontype(TalkParams))

        globals()["TalkReply"] = TalkReply

        class TalkRequest(Object, ControlRequest):
            # 1430 = OPTalk isteği (START/STOP ana kontrol soketinde gönderilir).
            type = 1430
            reply = TalkReply
            session: member[Session] = member("SessionID")
            command: fixedmember = fixedmember("Name", "OPTalk")
            talk: member[TalkParams] = member("OPTalk", conv=jsontype(TalkParams))

        globals()["TalkRequest"] = TalkRequest

        class TalkClaimReply(TalkReply):
            # 1435 = OPTalk CLAIM yanıtı (1425 'OPPlayBack' döndürüyordu).
            type = 1435

        globals()["TalkClaimReply"] = TalkClaimReply

        class TalkClaim(TalkRequest):
            # 1434 = OPTalk CLAIM isteği (yeni açılan sokette gönderilir).
            type = 1434
            reply = TalkClaimReply

        globals()["TalkClaim"] = TalkClaim

        class RawTalkData(ControlMessage):
            """G.711 ses çerçevesi: JSON değil, ham paket olarak gönderilir."""
            type = 1432
            __slots__ = ("_payload",)

            def __init__(self, payload):
                self._payload = payload

            def for_json(self):
                return None

            def chunks(self):
                return [self._payload]

            @classmethod
            def json_to(cls, datum):
                raise NotImplementedError("talk verisi JSON olarak çözümlenemez")

        _DVRIP = SimpleNamespace(
            av=av,
            DVRIPClient=DVRIPClient,
            DVRIPDecodeError=DVRIPDecodeError,
            Stream=Stream,
            DoPTZ=DoPTZ,
            PTZReply=PTZReply,
            KeepAlive=KeepAlive,
            KeepAliveReply=KeepAliveReply,
            TalkAction=TalkAction,
            AudioFormat=AudioFormat,
            TalkParams=TalkParams,
            TalkReply=TalkReply,
            TalkRequest=TalkRequest,
            TalkClaimReply=TalkClaimReply,
            TalkClaim=TalkClaim,
            RawTalkData=RawTalkData,
        )
    except Exception:
        _DVRIP = None
