"""
backend/vision_engine.py — KAMERA düğmesi arkasındaki görü katmanı.

İki mod tek sınıfta:
  • Canlı takip: YOLO11 her karede nesne tespiti yapar, kutulu kareyi JPEG
    olarak UI'a basar (on_frame → animasyonun üstündeki panel).
  • Derin analiz: Kullanıcı "bu ne?" dediğinde en güncel HAM kare alınır ve
    ModelRouter.analyze_image ile VL modeline (Qwen2-VL) gönderilir.

YOLO bloklayıcıdır → kendi thread'inde döner; UI'a köprü üzerinden yazar.
ultralytics kurulu değilse zarifçe 'sadece önizleme' moduna düşer.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from .config import Settings

# COCO sınıf adları → Türkçe (kamera görüntüsünde "person" değil "insan" yazsın)
COCO_TR = {
    "person": "insan", "bicycle": "bisiklet", "car": "araba", "motorcycle": "motosiklet",
    "airplane": "uçak", "bus": "otobüs", "train": "tren", "truck": "kamyon",
    "boat": "tekne", "traffic light": "trafik ışığı", "fire hydrant": "yangın musluğu",
    "stop sign": "dur tabelası", "parking meter": "parkmetre", "bench": "bank",
    "bird": "kuş", "cat": "kedi", "dog": "köpek", "horse": "at", "sheep": "koyun",
    "cow": "inek", "elephant": "fil", "bear": "ayı", "zebra": "zebra", "giraffe": "zürafa",
    "backpack": "sırt çantası", "umbrella": "şemsiye", "handbag": "el çantası",
    "tie": "kravat", "suitcase": "valiz", "frisbee": "frizbi", "skis": "kayak",
    "snowboard": "snowboard", "sports ball": "top", "kite": "uçurtma",
    "baseball bat": "beyzbol sopası", "baseball glove": "beyzbol eldiveni",
    "skateboard": "kaykay", "surfboard": "sörf tahtası", "tennis racket": "tenis raketi",
    "bottle": "şişe", "wine glass": "kadeh", "cup": "bardak", "fork": "çatal",
    "knife": "bıçak", "spoon": "kaşık", "bowl": "kase", "banana": "muz", "apple": "elma",
    "sandwich": "sandviç", "orange": "portakal", "broccoli": "brokoli", "carrot": "havuç",
    "hot dog": "sosisli", "pizza": "pizza", "donut": "donut", "cake": "pasta",
    "chair": "sandalye", "couch": "koltuk", "potted plant": "saksı bitkisi",
    "bed": "yatak", "dining table": "masa", "toilet": "klozet", "tv": "televizyon",
    "laptop": "dizüstü", "mouse": "fare", "remote": "kumanda", "keyboard": "klavye",
    "cell phone": "telefon", "microwave": "mikrodalga", "oven": "fırın",
    "toaster": "ekmek kızartıcı", "sink": "lavabo", "refrigerator": "buzdolabı",
    "book": "kitap", "clock": "saat", "vase": "vazo", "scissors": "makas",
    "teddy bear": "oyuncak ayı", "hair drier": "saç kurutma", "toothbrush": "diş fırçası",
}


def tr_label(name: str) -> str:
    return COCO_TR.get(str(name).lower(), str(name))


class VisionEngine:
    def __init__(self, settings: Settings,
                 on_frame: Callable[[bytes], None],
                 on_state: Callable[[bool], None],
                 on_log: Callable[[str], None]):
        self.s = settings
        self.on_frame = on_frame          # kutulu JPEG → UI önizleme
        self.on_state = on_state          # kamera aktif/pasif → UI düğme durumu
        self.on_log = on_log
        self._active = False
        self._lock = threading.Lock()
        self._latest_raw: bytes | None = None   # VL analizi için HAM kare
        self._thread: threading.Thread | None = None
        self._yolo = None
        self._yolo_lock = threading.Lock()      # _load_yolo/annotate farklı thread'lerden çağrılır
        self.last_error: str | None = None      # WebcamStreamer uyumluluğu

    # ── Durum ────────────────────────────────────────────────────────────────
    @property
    def is_active(self) -> bool:
        return self._active

    def latest_frame(self) -> bytes | None:
        """VL analizinde kullanılacak en güncel ham JPEG (kutusuz)."""
        with self._lock:
            return self._latest_raw

    # V2 ToolExecutor, WebcamStreamer arayüzünü bekler — birebir uyumluluk:
    def get_latest_frame(self) -> bytes | None:
        return self.latest_frame()

    # ── Yaşam döngüsü ────────────────────────────────────────────────────────
    def start(self) -> str:
        """WebcamStreamer uyumlu: 'ok' | 'already_active' döner."""
        with self._lock:
            if self._active:
                return "already_active"
            self._active = True
            self.last_error = None
        self._thread = threading.Thread(target=self._run, name="yerinde-vision", daemon=True)
        self._thread.start()
        self.on_state(True)
        return "ok"

    def stop(self) -> None:
        """Kapatır. İDEMPOTENT: hem 'kamerayı kapat' komutu HEM DE arka plan
        yakalama thread'i kendi finally'sinde bunu çağırıyor (kamera fiziksel
        olarak koptuğunda thread kendiliğinden temizlensin diye). İkisi de
        çağırırsa on_state(False)/UI günlüğü İKİ KEZ tetiklenip 'kamera kapatıldı'
        mesajının iki kez söylenmesine yol açıyordu — sadece GERÇEK
        aktif→pasif geçişinde bir kez bildir."""
        with self._lock:
            was_active = self._active
            self._active = False
            self._latest_raw = None
        if was_active:
            self.on_state(False)

    # ── YOLO tembel yükleme ──────────────────────────────────────────────────
    def set_detection(self, enabled: bool) -> str:
        """Nesne algılamayı (YOLO) açar/kapatır — kamera akışı devam eder."""
        self.s.yolo_enabled = bool(enabled)
        try:
            from app_config import save_app_config
            save_app_config({"yolo_enabled": bool(enabled)})
        except Exception:
            pass
        durum = "açıldı" if enabled else "kapatıldı"
        self.on_log(f"SYS: Nesne algılama {durum}.")
        return f"Nesne algılama {durum}."

    def _load_yolo(self):
        if self._yolo is not None:
            return self._yolo
        with self._yolo_lock:
            if self._yolo is not None:
                return self._yolo
            return self._load_yolo_unlocked()

    def _load_yolo_unlocked(self):
        """Asıl yükleme — kilidi _load_yolo tutar, birden çok thread güvenli."""
        try:
            from ultralytics import YOLO
            self._yolo = YOLO(self.s.yolo_model)
            self.on_log(f"SYS: YOLO11 yüklendi ({self.s.yolo_model}) — canlı nesne takibi aktif.")
        except Exception as e:
            self._yolo = False  # denendi, yok
            self.on_log(f"UYARI: YOLO11 yüklenemedi ({e}) — kamera sadece önizleme modunda. "
                        "Kurulum: pip install ultralytics")
        return self._yolo

    # ── Harici JPEG'e YOLO (bahçe kamerası önizlemesi) ──────────────────────
    def annotate(self, jpeg: bytes) -> bytes | None:
        """Bahçe kamerası gibi HARİCİ bir JPEG karesini YOLO ile kutular.

        Aynı yüklenmiş YOLO örneğini paylaşır; açıksa kutuları TÜRKÇE
        etiketler. Kapalıysa ya da YOLO kullanılamıyorsa ham kareyi döner
        (asla None olmaz) — önizleme bozulmaz."""
        import cv2
        import numpy as np
        try:
            frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return jpeg
        if frame is None:
            return jpeg
        display = frame
        if self.s.yolo_enabled:
            yolo = self._load_yolo()
            if yolo:
                try:
                    results = yolo.predict(frame, conf=self.s.yolo_conf, verbose=False)
                    display = self._draw_boxes_tr(frame.copy(), results[0], cv2)
                except Exception:
                    display = frame
        ok, buf = cv2.imencode(".jpg", display, [cv2.IMWRITE_JPEG_QUALITY, 72])
        return buf.tobytes() if ok else jpeg

    # ── Türkçe etiketli kutu çizimi ─────────────────────────────────────────
    def _draw_boxes_tr(self, frame, result, cv2):
        """Ultralytics'in kendi plot()'u İngilizce yazar ('person'); kutuları
        biz çizip etiketleri Türkçeye çeviriyoruz ('insan %92')."""
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return frame
        for b in boxes:
            try:
                x1, y1, x2, y2 = [int(v) for v in b.xyxy[0].tolist()]
                cls_id = int(b.cls[0].item())
                conf = float(b.conf[0].item())
            except Exception:
                continue
            label = f"{tr_label(names.get(cls_id, cls_id))} %{int(conf * 100)}"
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 212, 192), 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 8)),
                          (x1 + tw + 6, y1), (0, 212, 192), -1)
            cv2.putText(frame, label, (x1 + 3, max(12, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
        return frame

    # ── Ana döngü ────────────────────────────────────────────────────────────
    def _run(self) -> None:
        try:
            import cv2
        except ImportError:
            self.last_error = "opencv-python yüklü değil"
            self.on_log("ERR: opencv-python yüklü değil — kamera açılamadı.")
            self.stop()
            return

        cap = cv2.VideoCapture(self.s.camera_index)
        if not cap.isOpened():
            self.last_error = "Kamera açılamadı (bağlı ve izinli mi?)"
            self.on_log("ERR: Kamera açılamadı (bağlı ve izinli mi?).")
            self.stop()
            return

        yolo = self._load_yolo() if self.s.yolo_enabled else None
        enc = [cv2.IMWRITE_JPEG_QUALITY, 72]

        try:
            while True:
                with self._lock:
                    if not self._active:
                        break
                ok, frame = cap.read()
                if not ok:
                    break

                # Boyutlandır + aynala
                h, w = frame.shape[:2]
                if max(h, w) > 640:
                    sc = 640 / max(h, w)
                    frame = cv2.resize(frame, (int(w * sc), int(h * sc)))
                frame = cv2.flip(frame, 1)

                # HAM kareyi sakla (VL analizi bunun üstünden yapılır)
                ok_raw, raw_buf = cv2.imencode(".jpg", frame, enc)
                if ok_raw:
                    with self._lock:
                        self._latest_raw = raw_buf.tobytes()

                # YOLO11 tespit + kutu çizimi (varsa)
                display = frame
                if yolo and self.s.yolo_enabled:
                    try:
                        results = yolo.predict(frame, conf=self.s.yolo_conf,
                                               verbose=False)
                        display = self._draw_boxes_tr(frame.copy(), results[0], cv2)
                    except Exception:
                        pass

                ok_disp, disp_buf = cv2.imencode(".jpg", display, enc)
                if ok_disp:
                    self.on_frame(disp_buf.tobytes())

                time.sleep(0.01)
        finally:
            cap.release()
            self.stop()
