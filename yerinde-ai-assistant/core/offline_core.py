"""
core/offline_core.py — V2 arayüzü ile V3 asenkron çekirdeğin köprüsü.

main.py'nin ollama dalı artık OllamaAssistant yerine bunu çağırır:
    from core.offline_core import start_offline_core
    controller = start_offline_core(ui)     # bloklamaz

Neler bağlanır?
  • V2 config anahtarları → V3 Settings (ollama_model, offline_voice_choice,
    whisper_model_size, vosk_model_path, ollama_num_ctx, piper yolları...)
  • V2 UI kancaları (set_state/write_log/update_webcam_preview/...) → UICallbacks
  • V2 ToolExecutor (25 araç) + intent_parser → SystemController'a enjekte
    edilir; böylece uygulama açma, belge analizi, sesle yazma vb. HER ŞEY
    yeni mimaride de aynen çalışır.
  • Alışkanlık öğrenme (memory/habits.json) otomatik devrededir.
"""

from __future__ import annotations

import platform
import shutil
import threading
import time
from pathlib import Path

from app_config import get_app_config_value
from backend import Settings, UICallbacks, SystemController
from backend.ip_camera import GardenCamStreamer
from core.tool_executor import ToolExecutor
from core.intent_parser import detect_intent, get_last_correction
from actions import media_capture

BASE_DIR = Path(__file__).resolve().parent.parent
_IS_WINDOWS = platform.system() == "Windows"


def _find_piper_binary() -> str:
    """
    Piper'ı V2 ile aynı sırayla arar (V3'ün eski hali yalnızca PATH'e
    bakıyordu — proje içindeki piper/piper.exe'yi GÖRMÜYORDU, bu yüzden
    Piper kurulu olsa bile İngilizce SAPI'ye düşülüyordu):
      1) <proje>/piper/piper(.exe)
      2) <proje>/piper(.exe)
      3) PATH'teki 'piper'
    Bulunamazsa yine 'piper' döner (TTSManager loglayıp yedeğe geçer).
    """
    exe = "piper.exe" if _IS_WINDOWS else "piper"
    for cand in (BASE_DIR / "piper" / exe, BASE_DIR / exe):
        if cand.exists():
            return str(cand)
    found = shutil.which("piper")
    return found or "piper"


def _find_piper_voice() -> str:
    """Config'te yol yoksa voices/ klasöründeki ilk .onnx modeli (mutlak yol)."""
    configured = str(get_app_config_value("piper_voice_path", "") or "")
    if configured and Path(configured).exists():
        return configured
    voices_dir = BASE_DIR / "voices"
    if voices_dir.exists():
        for onnx in sorted(voices_dir.glob("*.onnx")):
            return str(onnx)
    return str(voices_dir / "tr_TR-dfki-medium.onnx")


def _looks_like_vosk(p: Path) -> bool:
    return p.is_dir() and any((p / x).exists()
                              for x in ("final.mdl", "am", "conf", "graph", "ivector"))


def _find_vosk_model() -> str:
    """
    Vosk model klasörünü esnekçe bulur — kullanıcı zip'i hangi adla açarsa
    açsın ('vosk-model-small-tr-0.3' vb.) yakalar:
      1) config'teki yol (mutlak ya da proje köküne göre)
      2) <proje>/vosk-model
      3) <proje>/vosk-model* ile başlayan HERHANGİ bir klasör
      4) bunların içinde tek alt klasör varsa bir seviye iner
    """
    configured = str(get_app_config_value("vosk_model_path", "vosk-model") or "vosk-model")
    candidates = []
    cp = Path(configured)
    candidates += [cp if cp.is_absolute() else BASE_DIR / cp, BASE_DIR / "vosk-model"]
    candidates += sorted(BASE_DIR.glob("vosk-model*"))
    seen = set()
    for cand in candidates:
        cand = cand.resolve()
        if cand in seen or not cand.is_dir():
            seen.add(cand); continue
        seen.add(cand)
        if _looks_like_vosk(cand):
            return str(cand)
        subs = [x for x in cand.iterdir() if x.is_dir()]
        if len(subs) == 1 and _looks_like_vosk(subs[0]):
            return str(subs[0])
        for sub in subs:  # zip'i içine açmış olabilir: vosk-model-.../vosk-model-...
            if sub.name.startswith("vosk-model") and _looks_like_vosk(sub):
                return str(sub)
    return configured  # bulunamadı → wake_word net hata mesajı verir


def _map_voice_profile() -> str:
    """
    V2 'offline_voice_choice' değerlerini V3 profiline çevirir.
    V2: "auto" | "piper:<yol>" | "sapi:<isim>" | "espeak:<varyant>"
    V3 ayrıca: "chattts" | "xtts:<ref.wav>"  (yeni seçenekler aynen geçer)
    """
    choice = str(get_app_config_value("offline_voice_choice", "auto") or "auto")
    return choice  # V3 TTSManager tüm bu biçimleri doğrudan anlar


# ── Model ön ayarları ───────────────────────────────────────────────────────
# HIZLI MOD: küçük modeller (3B/1.5B). 8 GB RAM'li makinelerde ve Orange Pi'de
# belirgin şekilde akıcı; sohbet kalitesi biraz düşer ama araç komutları
# (uygulama açma, fare, klavye, Office) intent_parser ile zaten LLM'siz çalışır.
MODEL_PRESETS = {
    "hizli": {   # ~3B — akıcı
        "chat":   "llama3.2:3b",
        "coder":  "qwen2.5-coder:1.5b",
        "vision": "moondream",
        "whisper": "base",
    },
    "dengeli": {  # ~7-9B — varsayılan
        "chat":   "llama3.1",
        "coder":  "qwen2.5-coder",
        "vision": "qwen2-vl",
        "whisper": "small",
    },
}


def _preset() -> dict:
    key = "hizli" if bool(get_app_config_value("fast_mode", False)) else "dengeli"
    return MODEL_PRESETS[key]


def build_settings(ui) -> Settings:
    s = Settings(
        ollama_host=str(get_app_config_value("ollama_host", "http://localhost:11434")
                        or "http://localhost:11434"),
        chat_model=str(get_app_config_value("ollama_model", _preset()["chat"])
                       or _preset()["chat"]),
        coder_model=str(get_app_config_value("ollama_coder_model", _preset()["coder"])
                        or _preset()["coder"]),
        vision_model=str(get_app_config_value("ollama_vision_model", _preset()["vision"])
                         or _preset()["vision"]),
        num_ctx=int(get_app_config_value("ollama_num_ctx", 8192) or 8192),
        wake_word=str(get_app_config_value("wake_word", "yerinde") or "yerinde"),
        vosk_model_path=_find_vosk_model(),
        wake_enabled=bool(get_app_config_value("wake_enabled", True)),
        voice_shutdown_enabled=bool(get_app_config_value("voice_shutdown_enabled", True)),
        whisper_model_size=str(get_app_config_value("whisper_model_size",
                                                   _preset()["whisper"])
                               or _preset()["whisper"]),
        voice_profile=_map_voice_profile(),
        piper_binary=str(get_app_config_value("piper_binary_path", "") or _find_piper_binary()),
        xtts_model=str(get_app_config_value(
            "xtts_model", "tts_models/multilingual/multi-dataset/xtts_v2")
            or "tts_models/multilingual/multi-dataset/xtts_v2"),
        volume=float(get_app_config_value("tts_volume", 1.0) or 1.0),
        yolo_enabled=bool(get_app_config_value("yolo_enabled", True)),
        intent_only=bool(get_app_config_value("intent_only", False)),
    )
    # Piper ses modeli: config'te yol verilmişse onu, yoksa voices/ içindeki
    # ilk .onnx (mutlak yol — çalışma dizininden bağımsız)
    s.piper_voice = _find_piper_voice()
    return s


def _make_intent_fn(on_log):
    """
    detect_intent()'i sarar: STT yanlış anlama filtresi bir düzeltme
    yaptıysa (ör. "saniyeyi temizle" → "sahneyi temizle") bunu logda
    kullanıcıya gösterir — hem şeffaflık hem de teşhis (debug) için.
    """
    def _fn(text):
        result = detect_intent(text)
        corr = get_last_correction()
        if corr:
            on_log(f"SYS: 🔤 sesi şöyle anladım: \"{corr['corrected']}\" "
                   f"(duyulan: \"{corr['original']}\")")
        return result
    return _fn


def start_offline_core(ui) -> SystemController:
    """UI hazır olduktan sonra çağır. Ana thread'i bloklamaz; controller döner."""
    settings = build_settings(ui)

    cbs = UICallbacks(
        on_state=lambda st: ui.set_state(st),
        on_log=lambda m: ui.write_log(m),
        on_user_text=lambda t: ui.write_log(f"Siz: {t}"),
        on_assistant_text=lambda t: ui.write_log(f"YERINDE: {t}"),
        on_frame=lambda b: ui.update_webcam_preview(b),
        on_camera_state=lambda a: ui.set_webcam_active(a),
    )
    cbs.bind_tk(ui.root)

    # Bahçe kamerası (Yoosee YS-09 / DVRIP) — paylaşımlı akış, UI önizlemesi.

    def _garden_state_change(streaming):
        """Kamera kendi kendine akışı kesti/geri getirdi — düğmeyi güncelle."""
        try:
            ui.root.after(0, lambda: ui.set_garden_active(streaming))
        except Exception:
            pass

    def _garden_tool_state(talking, horn):
        """Hoparlör / konuşma butonlarının rengini backend durumuna göre günceller."""
        try:
            ui.root.after(0, lambda: ui.set_garden_tool_state(
                horn_on=horn, talking=talking))
        except Exception:
            pass

    garden = GardenCamStreamer(on_log=lambda m: ui.write_log(m),
                               on_state_change=_garden_state_change,
                               on_tool_state=_garden_tool_state)


    controller = SystemController(
        settings, cbs,
        tool_executor=ToolExecutor(garden=garden, ui=ui),
        intent_fn=_make_intent_fn(lambda m: ui.write_log(m)),
        habits_path="memory/habits.json",
    )

    # Vision motoru artık kamera akışının sahibi — ToolExecutor'daki
    # toggle_webcam çağrıları da aynı motoru kullansın:
    controller.tools.webcam = controller.vision

    # Bahçe kamerası karelerini tek önizleme panelinde göster (webcam kapalıyken)
    _start_garden_preview_loop(ui, garden, controller.vision)

    # UI kancaları
    ui.on_text_command = controller.submit_text
    ui.on_webcam_toggle = lambda _activate: controller.toggle_camera()
    ui.on_stop_speaking = controller.interrupt
    ui.on_yolo_toggle = lambda enabled: controller.toggle_detection(enabled)
    ui.on_pause_toggle = lambda paused: (controller.wake.pause() if paused
                                         else controller.wake.resume())
    # FOTO/VİDEO düğmeleri: o an hangi kamera akışı canlıysa (bahçe kamerası
    # ya da webcam) onu kullan — ToolExecutor._capture_source() zaten
    # controller.tools.garden / controller.tools.webcam (= controller.vision)
    # arasında bu seçimi yapıyor, sesli komutlarla (take_photo/record_video
    # araçları) aynı mantığı burada da tekrar kullanıyoruz.
    ui.on_camera_photo = lambda: media_capture.take_photo(controller.tools._capture_source())
    ui.on_camera_record_toggle = lambda starting: (
        media_capture.recorder.start(controller.tools._capture_source()) if starting
        else media_capture.recorder.stop())
    ui.on_camera_pause_toggle = lambda pausing: (
        media_capture.recorder.pause() if pausing
        else media_capture.recorder.resume())

    ui.on_garden_toggle = lambda activate: _garden_toggle_in_thread(
        controller, ui, activate)
    ui.on_garden_wake = lambda: controller.tools.execute("wake_garden_cam", {})
    ui.on_garden_ptz = lambda direction: controller.tools.execute(
        "garden_ptz", {"direction": direction})
    ui.on_garden_ptz_start = lambda direction: controller.tools.execute(
        "garden_ptz_start", {"direction": direction})
    ui.on_garden_ptz_stop = lambda: controller.tools.execute(
        "garden_ptz_stop", {})
    ui.on_garden_horn = lambda: controller.tools.execute("garden_horn", {})
    ui.on_garden_talk = lambda: controller.tools.execute("garden_talk", {})

    controller.start()
    return controller

def _start_garden_preview_loop(ui, garden, vision) -> None:
    """Bahçe kamerası karelerini UI önizlemesine taşır.

    YOLO açıksa kareler vision.annotate() ile kutulanıp TÜRKÇE etiketlenir.
    Deteksiyon pahalı olduğu için her karede değil periyodik olarak
    (detect_interval) çalışır; arada son kutu çizilmiş kare gösterilir ki
    önizleme akıcı kalsın ve kutular titremesin."""
    detect_interval = 0.25            # saniyede ~4 tespit (CPU dostu)
    last_detect = 0.0
    last_annotated: bytes | None = None

    def _loop():
        nonlocal last_detect, last_annotated
        while True:
            try:
                if garden.is_active:
                    jpeg = garden.get_latest_frame()
                    if jpeg:
                        if vision.s.yolo_enabled:
                            now = time.time()
                            if (last_annotated is None
                                    or now - last_detect >= detect_interval):
                                last_annotated = vision.annotate(jpeg)
                                last_detect = now
                            out = last_annotated if last_annotated is not None else jpeg
                        else:
                            last_annotated = None
                            out = jpeg
                        if out:
                            ui.update_webcam_preview(out)
                else:
                    last_annotated = None
            except Exception:
                pass
            time.sleep(0.05)
    threading.Thread(target=_loop, daemon=True).start()


def _garden_toggle_in_thread(controller, ui, activate: bool) -> None:
    """BAHÇE KAMERA düğmesi — uyandırma uzun sürebilir, UI'ı kilitleme."""
    def _run():
        action = "start" if activate else "stop"
        try:
            result = controller.tools.execute(
                "toggle_garden_cam", {"action": action})
            if result:
                ui.write_log(f"SYS: {result}")
        except Exception as e:
            ui.write_log(f"ERR: Bahçe kamerası — {e}")
    threading.Thread(target=_run, daemon=True).start()
