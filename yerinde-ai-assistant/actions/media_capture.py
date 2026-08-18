"""
Kameradan fotoğraf çekme, video kaydı ve canlı önizleme penceresi
(opencv-python kullanır — tamamen yerel, internet gerekmez).
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

CAPTURES_DIR = Path("Captures")

_preview_thread: threading.Thread | None = None
_preview_stop = threading.Event()
_preview_lock = threading.Lock()


def _ensure_dir():
    CAPTURES_DIR.mkdir(exist_ok=True)


def _grab_shared_frame(source, cv2):
    """Kamera zaten AÇIKSA (canlı önizleme akıyorsa) paylaşımlı akıştan
    (WebcamStreamer/VisionEngine, ikisi de aynı arayüzü sunar: is_active +
    get_latest_frame() → JPEG bytes) bir kare döndürür; yoksa None.

    ÖNEMLİ: Kamera zaten açıkken cv2.VideoCapture(0) ile İKİNCİ bir bağlantı
    açmaya çalışmak çoğu işletim sisteminde (Windows DirectShow, Linux V4L2)
    BAŞARISIZ olur ya da donmuş/siyah kare döner — çünkü webcam donanımı aynı
    anda yalnızca TEK bir açık bağlantıyı destekler. 'Kamera açıkken fotoğraf
    çekemedim' şikayetinin kök nedeni buydu; artık aynı akıştan kare alınıyor."""
    import numpy as np
    src = source
    if src is None or not getattr(src, "is_active", False):
        return None
    getter = getattr(src, "get_latest_frame", None) or getattr(src, "latest_frame", None)
    if not getter:
        return None
    for _ in range(20):  # ~1sn içinde ilk kare gelmiş olmalı
        jpeg = getter()
        if jpeg:
            arr = np.frombuffer(jpeg, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is not None:
                return frame
        time.sleep(0.05)
    return None


def take_photo(source=None) -> str:
    """Webcam'dan bir kare yakalayıp Captures/ klasörüne JPEG olarak kaydeder.
    Kamera zaten açıksa (source verilmişse) o akıştaki güncel kareyi kullanır;
    kapalıysa kendi geçici bağlantısını açıp hemen kapatır."""
    try:
        import cv2
    except ImportError:
        return "opencv-python paketi yüklü değil. Kurulum: pip install opencv-python"

    _ensure_dir()
    filename = CAPTURES_DIR / f"foto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

    shared = _grab_shared_frame(source, cv2)
    if shared is not None:
        cv2.imwrite(str(filename), shared)
        return f"Fotoğraf çekildi: {filename}"

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Webcam açılamadı. Kamera bağlı ve izinler açık mı?"

    try:
        for _ in range(5):  # ısınma kareleri
            cap.read()
            time.sleep(0.05)
        ok, frame = cap.read()
        if not ok:
            return "Kare yakalanamadı."
        cv2.imwrite(str(filename), frame)
        return f"Fotoğraf çekildi: {filename}"
    finally:
        cap.release()


def record_video(seconds: int = 5, source=None) -> str:
    """Webcam'dan belirtilen süre kadar video kaydeder (Captures/ klasörüne .mp4).
    Kamera zaten açıksa (source verilmişse) o akıştan kare toplar; kapalıysa
    kendi geçici bağlantısını açar."""
    try:
        import cv2
    except ImportError:
        return "opencv-python paketi yüklü değil. Kurulum: pip install opencv-python"

    try:
        seconds = max(1, min(int(seconds or 5), 60))
    except (TypeError, ValueError):
        seconds = 5

    _ensure_dir()
    filename = CAPTURES_DIR / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = 20.0

    use_shared = source is not None and getattr(source, "is_active", False)

    if use_shared:
        getter = getattr(source, "get_latest_frame", None) or getattr(source, "latest_frame", None)
        first = _grab_shared_frame(source, cv2)
        if first is None:
            use_shared = False
        else:
            h, w = first.shape[:2]
            writer = cv2.VideoWriter(str(filename), fourcc, fps, (w, h))
            writer.write(first)
            frame_interval = 1.0 / fps
            start = time.time()
            next_tick = start + frame_interval
            while time.time() - start < seconds:
                if not getattr(source, "is_active", False):
                    break  # akış bu sırada kapatıldıysa yarım kalmış dosyayı bozma
                jpeg = getter()
                if jpeg:
                    import numpy as np
                    arr = np.frombuffer(jpeg, dtype=np.uint8)
                    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if frame is not None:
                        writer.write(frame)
                sleep_for = next_tick - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                next_tick += frame_interval
            writer.release()
            return f"{seconds} saniyelik video kaydedildi: {filename}"

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Webcam açılamadı. Kamera bağlı ve izinler açık mı?"

    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
        writer = cv2.VideoWriter(str(filename), fourcc, fps, (w, h))

        start = time.time()
        while time.time() - start < seconds:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
        writer.release()
        return f"{seconds} saniyelik video kaydedildi: {filename}"
    finally:
        cap.release()


class CameraRecorder:
    """Kamera açıkken elle video kaydı: başlat / duraklat / devam / durdur.
    Paylaşımlı akıştan (WebcamStreamer/VisionEngine) kare alır — YENİ bir
    cv2.VideoCapture AÇMAZ, böylece kamera zaten açıkken de çalışır."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._lock = threading.Lock()
        self._active = False
        self._filename: Path | None = None
        self._writer = None

    @property
    def is_recording(self) -> bool:
        return self._active

    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()

    def start(self, source) -> str:
        import cv2
        with self._lock:
            if self._active:
                return "Zaten video kaydediyorum."
        if source is None or not getattr(source, "is_active", False):
            return "Önce kamerayı açmam lazım."
        first = _grab_shared_frame(source, cv2)
        if first is None:
            return "Kameradan kare alamadım, video başlatılamadı."
        _ensure_dir()
        self._filename = CAPTURES_DIR / f"video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        h, w = first.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        self._writer = cv2.VideoWriter(str(self._filename), fourcc, 20.0, (w, h))
        self._stop.clear()
        self._paused.clear()
        with self._lock:
            self._active = True
        self._thread = threading.Thread(target=self._run, args=(source,), daemon=True)
        self._thread.start()
        return "Video kaydı başladı."

    def _run(self, source) -> None:
        import cv2
        import numpy as np
        getter = getattr(source, "get_latest_frame", None) or getattr(source, "latest_frame", None)
        interval = 1.0 / 20.0
        next_tick = time.time()
        try:
            while not self._stop.is_set():
                if not getattr(source, "is_active", False):
                    break  # kamera dışarıdan (buton/sesli komut) kapatıldı
                if not self._paused.is_set() and getter:
                    jpeg = getter()
                    if jpeg:
                        arr = np.frombuffer(jpeg, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            self._writer.write(frame)
                next_tick += interval
                sleep_for = next_tick - time.time()
                time.sleep(max(0.0, sleep_for))
        finally:
            if self._writer is not None:
                self._writer.release()
            with self._lock:
                self._active = False

    def pause(self) -> str:
        if not self._active:
            return "Şu an kayıt yapmıyorum."
        self._paused.set()
        return "Video kaydı duraklatıldı."

    def resume(self) -> str:
        if not self._active:
            return "Şu an kayıt yapmıyorum."
        self._paused.clear()
        return "Video kaydına devam ediliyor."

    def toggle_pause(self) -> str:
        return self.resume() if self.is_paused else self.pause()

    def stop(self) -> str:
        if not self._active:
            return "Zaten kayıt yapmıyordum."
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        return f"Video kaydedildi: {self._filename}"


# Arayüz (KAMERA panelindeki FOTO/VİDEO/DURAKLAT düğmeleri) için tekil örnek —
# aynı anda tek bir manuel kayıt olur.
recorder = CameraRecorder()


def open_camera_preview() -> str:
    """
    Kamerayı açar ve canlı görüntüyü ayrı bir pencerede gösterir
    (Gemini/internet gerekmez — çevrimdışı modda da çalışır).
    Kullanıcı pencereyi 'q' tuşuyla ya da close_camera_preview() ile kapatabilir.
    """
    global _preview_thread

    try:
        import cv2
    except ImportError:
        return "opencv-python paketi yüklü değil. Kurulum: pip install opencv-python"

    with _preview_lock:
        if _preview_thread and _preview_thread.is_alive():
            return "Kamera zaten açık."
        _preview_stop.clear()

        def _run():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return
            window = "YERINDE Kamera (kapatmak icin 'q' bas)"
            try:
                while not _preview_stop.is_set():
                    ok, frame = cap.read()
                    if not ok:
                        break
                    cv2.imshow(window, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
            finally:
                cap.release()
                try:
                    cv2.destroyWindow(window)
                except Exception:
                    pass

        _preview_thread = threading.Thread(target=_run, daemon=True)
        _preview_thread.start()

    time.sleep(0.3)  # kameranın gerçekten açılıp açılmadığını anlamak için kısa bekleme
    return "Kamera açıldı — canlı görüntü ayrı bir pencerede."


def close_camera_preview() -> str:
    """Açık olan kamera önizleme penceresini kapatır."""
    if not (_preview_thread and _preview_thread.is_alive()):
        return "Kamera zaten kapalı."
    _preview_stop.set()
    _preview_thread.join(timeout=3)
    return "Kamera kapatıldı."
