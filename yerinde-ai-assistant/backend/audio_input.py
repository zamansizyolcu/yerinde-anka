"""
backend/audio_input.py — Linux'ta (özellikle Pardus/Debian) mikrofon seçimi.

Sorun: PortAudio, ALSA'daki tüm sanal aygıtları (rear/center_lfe/side, jack,
oss...) yoklarken korkutucu hatalar basar ve bazen VARSAYILAN aygıt olarak
kayıt yapamayan bir çıkışı seçer → asistan hiç ses duymaz. Bu modül:
  1) ALSA'nın stderr gürültüsünü susturur (yalnızca Linux, best-effort),
  2) ÇALIŞAN bir giriş aygıtını akıllıca seçer: pulse → pipewire → default →
     sysdefault → giriş kanalı olan ilk aygıt; her adayı gerçekten test eder.
"""

from __future__ import annotations

import contextlib
import os
import platform
import queue
import shutil
import subprocess
import threading
import time

_IS_LINUX = platform.system() == "Linux"
_IS_WINDOWS = platform.system() == "Windows"
_alsa_muted = False
_cached_device: int | None | str = "unset"


def mute_alsa_errors() -> None:
    """ALSA'nın 'Unknown PCM', 'jack server is not running' vb. korkutucu ama
    zararsız stderr mesajlarını kapatır."""
    global _alsa_muted
    if _alsa_muted or not _IS_LINUX:
        return
    try:
        from ctypes import CDLL, CFUNCTYPE, c_char_p, c_int
        handler_t = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
        _mute_alsa_errors_handler = handler_t(lambda *a: None)
        CDLL("libasound.so.2").snd_lib_error_set_handler(_mute_alsa_errors_handler)
        # Referans kaybolmasın (GC ederse segfault olabilir)
        globals()["_alsa_handler_ref"] = _mute_alsa_errors_handler
        _alsa_muted = True
    except Exception:
        pass


@contextlib.contextmanager
def suppress_native_stderr():
    """mute_alsa_errors() SADECE ALSA'nın kendi C hata-yakalayıcısından
    geçen mesajları susturur — ama JACK sunucusuna bağlanma denemesi
    ('connect(2) call to .../jack_0 failed', 'attempt to connect to server
    failed') ALSA'nın hata mekanizmasından GEÇMİYOR, doğrudan işletim
    sistemi seviyesinde stderr'e (dosya tanıtıcısı 2) yazılıyor — bu yüzden
    ALSA'nın hata yakalayıcısı bunu hiç göremiyor. Bunu susturmanın tek
    güvenilir yolu, dosya tanıtıcısını GEÇİCİ olarak /dev/null'a
    yönlendirmek. Sadece riskli çağrının (ör. PyAudio()) etrafında, kısa
    süreliğine kullanılır — sürekli açık bırakılmaz, yoksa gerçek Python
    hataları/traceback'ler de gizlenir."""
    if not _IS_LINUX:
        yield
        return
    try:
        stderr_fd = 2
        saved_fd = os.dup(stderr_fd)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, stderr_fd)
        os.close(devnull_fd)
    except Exception:
        yield
        return
    try:
        yield
    finally:
        try:
            os.dup2(saved_fd, stderr_fd)
            os.close(saved_fd)
        except Exception:
            pass


def pick_input_device(samplerate: int = 16000, log=lambda m: None):
    """
    Kayıt yapabilen bir giriş aygıtı indeksi döner (None = PortAudio
    varsayılanı kullan). Sonuç önbelleklenir. Pardus'ta 'hiç duymuyor'
    sorununun ana çözümü: pulse/pipewire köprü aygıtını açıkça seçmek.
    """
    global _cached_device
    if _cached_device != "unset":
        return _cached_device

    mute_alsa_errors()
    try:
        import sounddevice as sd
    except ImportError:
        _cached_device = None
        return None

    def works(dev) -> bool:
        try:
            sd.check_input_settings(device=dev, samplerate=samplerate,
                                    channels=1, dtype="int16")
            return True
        except Exception:
            return False

    candidates: list[tuple[int, str]] = []
    try:
        for idx, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) > 0:
                candidates.append((idx, str(info.get("name", "")).lower()))
    except Exception:
        candidates = []

    # Öncelik sırası: pulse > pipewire > default > sysdefault > diğerleri
    def rank(name: str) -> int:
        for i, key in enumerate(("pulse", "pipewire", "default", "sysdefault")):
            if key in name:
                return i
        return 9

    candidates.sort(key=lambda c: rank(c[1]))

    # Önce PortAudio varsayılanı (Windows/mac'te genelde doğrudur)
    if not _IS_LINUX and works(None):
        _cached_device = None
        return None

    for idx, name in candidates:
        if works(idx):
            _cached_device = idx
            log(f"SYS: Mikrofon seçildi → [{idx}] {name}")
            return idx

    if works(None):          # son çare: varsayılan
        _cached_device = None
        return None

    _cached_device = None
    log("UYARI: Kayıt yapabilen mikrofon bulunamadı. 'python3 -m sounddevice' "
        "ile aygıtları listeleyip pavucontrol'den giriş aygıtını kontrol et.")
    return None


# ── Genişletilmiş API: aygıt + çalışan örnekleme hızı birlikte seçilir ───────
_PREFERRED_RATES = (16000, 48000, 44100, 32000, 22050)
_cached_pick: dict | None = None


def pick_input(log=lambda m: None) -> dict:
    """
    Kayıt yapabilen (aygıt, örnekleme hızı) çifti döner:
        {"device": int|None, "samplerate": int}
    Bazı Pardus/PipeWire aygıtları 16 kHz'i reddeder — o durumda 48/44.1 kHz
    ile açılır ve ses resample_to_16k() ile 16 kHz'e indirilir (Vosk/Whisper
    16 kHz ister). Sonuç önbelleklenir; hiçbir kombinasyon çalışmazsa
    RuntimeError fırlatır (çağıran net hata gösterir).
    """
    global _cached_pick
    if _cached_pick is not None:
        return _cached_pick

    mute_alsa_errors()
    import sounddevice as sd

    def try_combo(dev, rate) -> bool:
        try:
            sd.check_input_settings(device=dev, samplerate=rate,
                                    channels=1, dtype="int16")
            return True
        except Exception:
            return False

    # Aday aygıtlar: pulse/pipewire/default öncelikli (bkz. pick_input_device)
    candidates: list[tuple[int | None, str]] = []
    try:
        for idx, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) > 0:
                candidates.append((idx, str(info.get("name", "")).lower()))
    except Exception:
        pass

    def rank(name: str) -> int:
        for i, key in enumerate(("pulse", "pipewire", "default", "sysdefault")):
            if key in name:
                return i
        return 9

    candidates.sort(key=lambda c: rank(c[1]))
    ordered: list[tuple[int | None, str]] = candidates + [(None, "portaudio varsayılanı")]
    if not _IS_LINUX:
        ordered = [(None, "portaudio varsayılanı")] + candidates

    for dev, name in ordered:
        for rate in _PREFERRED_RATES:
            if try_combo(dev, rate):
                _cached_pick = {"device": dev, "samplerate": rate}
                extra = "" if rate == 16000 else f" (16k desteklenmiyor → {rate} Hz'den indirgenecek)"
                log(f"SYS: Mikrofon → {name} @ {rate} Hz{extra}")
                return _cached_pick

    raise RuntimeError(
        "Kayıt yapabilen mikrofon bulunamadı. Kontrol: 'python3 -m sounddevice' "
        "ile aygıt listesi; pavucontrol > Giriş Aygıtları'nda mikrofonun "
        "susturulmuş olmadığından emin ol.")


def resample_to_16k(pcm: bytes, src_rate: int) -> bytes:
    """int16 mono PCM'i 16 kHz'e lineer interpolasyonla indirger."""
    if src_rate == 16000 or not pcm:
        return pcm
    import numpy as np
    x = np.frombuffer(pcm, dtype=np.int16)
    n_out = int(len(x) * 16000 / src_rate)
    if n_out <= 0:
        return b""
    idx = np.linspace(0, len(x) - 1, n_out)
    y = np.interp(idx, np.arange(len(x)), x.astype(np.float32))
    return y.astype(np.int16).tobytes()


# ══ MikrofonAkışı: sounddevice ÇALIŞMAZSA doğrudan parec/arecord ═══════════
class MicStream:
    """
    Tek bir mikrofon akışı soyutlaması.

    NEDEN VAR: Linux'ta (PipeWire/PulseAudio + venv karışımı) sounddevice
    (PortAudio) bazen HATA VERMEDEN sessiz kalıyor — akış açılıyor, geri
    çağırma hiç tetiklenmiyor ya da hep sıfır geliyor. Bu yüzden asistan
    "hiç duymuyor" oluyordu (CachyOS'ta gözlenen davranış).

    Bu sınıf:
      1) sounddevice ile açmayı dener,
      2) 1.5 saniye içinde GERÇEK veri gelmezse, PortAudio'yu tamamen atlayıp
         'parec' (PipeWire/Pulse) ya da 'arecord' (ALSA) alt sürecinden ham
         PCM okur. Bu yol neredeyse her Linux kurulumunda çalışır.
    """

    def __init__(self, samplerate: int = 16000, blocksize: int = 1024,
                 log=lambda m: None):
        self.rate = samplerate
        self.blocksize = blocksize
        self.log = log
        self.backend = "none"
        self._q: "queue.Queue[bytes]" = queue.Queue(maxsize=64)
        self._sd_stream = None
        self._proc = None
        self._reader = None
        self._stop = threading.Event()

    # ── Açma ────────────────────────────────────────────────────────────────
    def start(self) -> bool:
        if self._try_sounddevice():
            return True
        self.log("UYARI: Mikrofondan veri gelmiyor (sounddevice sessiz). "
                 "Doğrudan sistem kaydediciye geçiyorum...")
        self.close()
        return self._try_cli()

    def _try_sounddevice(self) -> bool:
        try:
            import sounddevice as sd
            pick = pick_input(self.log)
            dev, rate = pick["device"], pick["samplerate"]
            self.rate = rate

            def _cb(indata, frames, t, status):
                try:
                    self._q.put_nowait(bytes(indata))
                except queue.Full:
                    pass

            blocks = int(self.blocksize * rate / 16000)
            self._sd_stream = sd.RawInputStream(
                samplerate=rate, blocksize=blocks, dtype="int16",
                channels=1, callback=_cb, device=dev)
            self._sd_stream.start()
        except Exception as e:
            self.log(f"UYARI: sounddevice açılamadı ({e}).")
            return False

        # GERÇEKTEN veri geliyor mu? İLK paket gelir gelmez onaylıyoruz —
        # (çalışan sistemlerde, ör. Windows, gereksiz gecikme eklememek için)
        # ama tamamen sessiz kalırsa 1.5 sn'de pes edip yedeğe düşüyoruz.
        deadline = time.time() + 1.5
        while time.time() < deadline:
            try:
                chunk = self._q.get(timeout=0.2)
                if chunk:
                    self.backend = "sounddevice"
                    self.log(f"SYS: Mikrofon akışı açık (sounddevice @ {self.rate} Hz).")
                    return True
            except queue.Empty:
                continue
        return False

    def _try_cli(self) -> bool:
        """PortAudio'yu atla: parec (PipeWire/Pulse) → arecord (ALSA)."""
        if _IS_WINDOWS:
            return False
        candidates = []
        if shutil.which("parec"):
            candidates.append((["parec", "--format=s16le", "--rate=16000",
                                "--channels=1"], "parec"))
        if shutil.which("arecord"):
            candidates.append((["arecord", "-q", "-f", "S16_LE", "-r", "16000",
                                "-c", "1", "-t", "raw", "-D", "default"], "arecord"))
        for cmd, name in candidates:
            try:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL,
                                              bufsize=0)
            except Exception:
                continue

            self._stop.clear()

            def _read():
                nbytes = self.blocksize * 2
                while not self._stop.is_set() and self._proc.poll() is None:
                    data = self._proc.stdout.read(nbytes)
                    if not data:
                        break
                    try:
                        self._q.put_nowait(data)
                    except queue.Full:
                        pass

            self._reader = threading.Thread(target=_read, daemon=True)
            self._reader.start()

            deadline = time.time() + 2.0
            got = 0
            while time.time() < deadline:
                try:
                    got += len(self._q.get(timeout=0.2))
                    if got >= 8000:
                        self.rate = 16000
                        self.backend = name
                        self.log(f"SYS: Mikrofon akışı açık ({name} @ 16000 Hz) — "
                                 "PortAudio atlandı.")
                        return True
                except queue.Empty:
                    continue
            self.close()

        self.log("ERR: Mikrofondan hiç veri alınamıyor. Kontrol:\n"
                 "  1) pavucontrol > Giriş Aygıtları — mikrofon susturulmuş mu?\n"
                 "  2) arecord -l   (aygıt görünüyor mu?)\n"
                 "  3) sudo apt install pulseaudio-utils alsa-utils")
        return False

    # ── Okuma / kapatma ─────────────────────────────────────────────────────
    def read(self, timeout: float = 0.5) -> bytes | None:
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self) -> None:
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def close(self) -> None:
        self._stop.set()
        if self._sd_stream is not None:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception:
                pass
            self._sd_stream = None
        if self._proc is not None:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None
        self.drain()
