"""
Paylaşımlı canlı webcam akışı — hem Gemini modu (main.py, görüntüyü Gemini'ye
gönderir) hem de arayüzdeki canlı önizleme (hem Gemini hem Ollama modunda)
AYNI WebcamStreamer örneğini kullanır. Böylece "CANLI KAMERA" düğmesi ile
sesli "kamerayı aç" komutu her zaman aynı kamerayı kontrol eder.
"""

from __future__ import annotations

import threading
import time


def _tr_label(name):
    try:
        from backend.vision_engine import tr_label
        return tr_label(name)
    except Exception:
        return str(name)


class WebcamStreamer:
    """
    Webcam'dan sürekli kare çeker ve en güncel JPEG'i bellekte tutar.
    Queue yerine tek bir 'latest frame' yaklaşımı — eski kare birikimi olmaz.
    """

    JPEG_QUALITY = 72
    MAX_DIM      = 640
    WARMUP       = 6

    def __init__(self):
        self._latest: bytes | None = None
        self._raw: bytes | None = None      # kutusuz kare (görüntü analizi için)
        self._lock   = threading.Lock()
        self._yolo = None                   # tembel yüklenir
        self._yolo_tried = False
        try:
            from app_config import get_app_config_value
            self.detection_enabled = bool(get_app_config_value("yolo_enabled", True))
        except Exception:
            self.detection_enabled = True
        self.on_log = None                  # UI'a bilgi vermek için (opsiyonel)
        self._active = False
        self._thread: threading.Thread | None = None
        self._last_error: str | None = None

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def set_detection(self, enabled: bool) -> str:
        """Nesne algılamayı aç/kapat — kamera akışı kesilmez."""
        self.detection_enabled = bool(enabled)
        try:
            from app_config import save_app_config
            save_app_config({"yolo_enabled": bool(enabled)})
        except Exception:
            pass
        return f"Nesne algılama {'açıldı' if enabled else 'kapatıldı'}."

    def _load_yolo(self):
        if self._yolo_tried:
            return self._yolo
        self._yolo_tried = True
        try:
            from ultralytics import YOLO
            from app_config import get_app_config_value
            model = str(get_app_config_value("yolo_model", "yolo11n.pt") or "yolo11n.pt")
            self._yolo = YOLO(model)
            if self.on_log:
                self.on_log(f"SYS: YOLO11 yüklendi ({model}) — nesne algılama aktif.")
        except Exception as e:
            self._yolo = None
            if self.on_log:
                self.on_log(f"UYARI: Nesne algılama kapalı — YOLO yüklenemedi ({e}). "
                            "Kurulum: pip install ultralytics")
        return self._yolo

    def _detect(self, frame, cv2):
        yolo = self._load_yolo()
        if not yolo:
            return frame
        try:
            res = yolo.predict(frame, conf=0.35, verbose=False)[0]
            names = getattr(res, "names", {}) or {}
            for b in getattr(res, "boxes", []) or []:
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                cls_id = int(b.cls[0].item())
                conf = float(b.conf[0].item())
                label = f"{_tr_label(names.get(cls_id, cls_id))} %{int(conf * 100)}"
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 212, 192), 2)
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(frame, (x1, max(0, y1 - th - 8)), (x1 + tw + 6, y1),
                              (0, 212, 192), -1)
                cv2.putText(frame, label, (x1 + 3, max(12, y1 - 5)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        except Exception:
            pass
        return frame

    def get_latest_frame(self) -> bytes | None:
        """Thread-safe, her zaman en güncel kareyi (JPEG bytes) döner."""
        with self._lock:
            return self._latest

    def start(self) -> str:
        with self._lock:
            if self._active:
                return "already_active"
            self._active = True
            self._latest = None
            self._last_error = None
        t = threading.Thread(target=self._run, daemon=True)
        self._thread = t
        t.start()
        return "ok"

    def stop(self):
        with self._lock:
            self._active = False
            self._latest = None

    def _run(self):
        try:
            import cv2
        except ImportError:
            self._last_error = "opencv-python paketi yüklü değil."
            with self._lock:
                self._active = False
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._last_error = "Kamera açılamadı (bağlı ve izinli mi?)."
            with self._lock:
                self._active = False
            return

        for _ in range(self.WARMUP):
            cap.read()

        enc_params = [cv2.IMWRITE_JPEG_QUALITY, self.JPEG_QUALITY]

        try:
            while True:
                with self._lock:
                    if not self._active:
                        break

                ret, frame = cap.read()
                if not ret:
                    break

                h, w = frame.shape[:2]
                if max(h, w) > self.MAX_DIM:
                    s = self.MAX_DIM / max(h, w)
                    frame = cv2.resize(frame, (int(w * s), int(h * s)))

                frame = cv2.flip(frame, 1)  # yatay ayna

                # Ham kareyi sakla (görüntü analizi kutusuz görüntü ister)
                ok_raw, raw_buf = cv2.imencode(".jpg", frame, enc_params)
                if ok_raw:
                    with self._lock:
                        self._raw = raw_buf.tobytes()

                # Nesne algılama (YOLO) — açıksa kutuları TÜRKÇE etiketle çiz
                if self.detection_enabled:
                    frame = self._detect(frame, cv2)

                ok, buf = cv2.imencode(".jpg", frame, enc_params)
                if ok:
                    with self._lock:
                        self._latest = buf.tobytes()

                time.sleep(0.03)  # ~33 FPS yakala
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
