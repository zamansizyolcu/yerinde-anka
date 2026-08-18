#!/usr/bin/env python3
"""
YERINDE CachyOS — Gerçek zamanlı sesli yardımcı çekirdeği
CachyOS (Arch Linux tabanlı) ortamına uyarlanmış çalışma akışı.
"""

import asyncio
import datetime
import threading
import traceback
import os
import sys
import time
import re
import subprocess
import numpy as np
from pathlib import Path

# ── Opsiyonel bağımlılıklar (H3): eksik olsalar bile PENCERE AÇILIR ─────────
# pyaudio / google-genai YOKSA uygulama çökmez; ilgili özellik pas geçer.
try:
    import pyaudio  # type: ignore[reportMissingModuleSource]
except Exception:
    pyaudio = None

try:
    from google import genai  # type: ignore[reportMissingImports]
    from google.genai import types  # type: ignore[reportMissingImports]
except Exception:
    genai = None
    types = None

from app_config import get_app_config_value, gemini_thinking_budget
from ui import YerindeUI
from backend.habits import HabitLearner
from backend.audio_input import mute_alsa_errors, suppress_native_stderr
from backend.ip_camera import GardenCamStreamer
from memory.memory_manager import load_memory, update_memory, delete_memory, format_memory_for_prompt
from actions.open_app import open_app, close_app, set_last_opened
from actions.sys_info  import sys_info
from actions.calendar import get_calendar_events, add_calendar_event, delete_calendar_event
from actions.reminders import get_reminders, add_reminder
from actions.browser   import browser_control
from actions.shell     import shell_run
from actions.whatsapp  import send_whatsapp_message, save_whatsapp_contact
from actions.media     import play_media
from actions.weather   import get_weather_summary, get_forecast_summary
from actions.screen_vision import analyze_screen
from actions.youtube_stats import get_youtube_channel_report
from actions.media_capture import take_photo, record_video
from actions import media_capture
from actions.document_tools import analyze_document, read_document_aloud
from actions.zumre_tutanagi import zumre_tutanagi_olustur
from actions.belge_referanslari import referans_belge_kaydet
from actions.sinav_uret import sinav_olustur
from actions.yillik_plan import gunluk_plan_olustur, yillik_plan_guncelle
from actions.kulup_belgesi import kulup_calisma_plani_olustur
from actions.olcek_hazirla import olcek_hazirla
from actions.code_tools import save_python_file
from actions.type_text import type_text
from actions.system_media import system_volume, media_control, save_active_document, shutdown_assistant
from actions.office_blank import create_blank_document, normalize_kind, KINDS as OFFICE_KINDS
from actions import blender_bridge
from actions import freecad_bridge
from actions.office_format import office_format
from actions.mouse_control import mouse_control
from actions.voice_sample import record_voice_sample
from actions.keyboard_control import press_key
from actions.office_media import insert_image, word_export_pdf, excel_command, image_adjust
from actions.streaming import play_stream
from actions.whatsapp_call import whatsapp_call, calibrate_call_button
from actions import piper_dataset
from actions.scratch_bridge import scratch_command
from actions.office_show import slideshow, add_transition, add_animation, clear_effects, slide_edit
from actions.office_content import write_topic

try:
    from wakeup_listener import WakeGestureListener
except Exception:  # pyaudio yoksa veya mikrofon erisimi yoksa uygulama yine acilsin
    WakeGestureListener = None

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"


# ── WebcamStreamer ──────────────────────────────────────────────────────────

# ── Gemini ses kimliği çözümleyici ──────────────────────────────────────────
# Yapılandırmada eskiden Türkçe etiket ("Kadın 2 — Yumuşak") kalmış olabilir;
# Gemini yalnızca kendi ses kimliklerini kabul eder. Ne gelirse gelsin geçerli
# bir kimliğe çeviririz — böylece "voice is not available" hatası oluşmaz.
_GEMINI_VOICES = {"Kore", "Aoede", "Leda", "Charon", "Puck", "Fenrir",
                  "Orus", "Zephyr"}
_LABEL_TO_ID = {
    "kadın 1": "Kore", "kadın 2": "Aoede", "kadın 3": "Leda",
    "erkek 1": "Charon", "erkek 2": "Puck", "erkek 3": "Fenrir",
}


def _resolve_gemini_voice(value) -> str:
    v = str(value or "").strip()
    if v in _GEMINI_VOICES:
        return v
    low = v.lower()
    for prefix, vid in _LABEL_TO_ID.items():
        if low.startswith(prefix):
            return vid
    # Etiket içinde kimlik parantezde olabilir: "Kadın 1 — Berrak (Kore)"
    for vid in _GEMINI_VOICES:
        if vid.lower() in low:
            return vid
    return "Charon"



# ── Bağlantı hatası sınıflandırıcı ──────────────────────────────────────────
# "timed out during opening handshake" gibi AĞ hatalarına "API anahtarını
# kontrol et" demek yanlış yönlendiriyordu. Hatayı türüne göre ayırıyoruz.
def _classify_connect_error(err) -> tuple[str, str, bool]:
    """
    (tür, kullanıcıya gösterilecek mesaj, gecici_mi) döner.
    tür: "network" | "auth" | "config" | "quota" | "unknown"
    """
    text = str(err).lower()

    if any(k in text for k in ("timed out", "timeout", "handshake", "connection reset",
                               "connection closed", "temporarily unavailable",
                               "getaddrinfo", "name resolution", "network is unreachable",
                               "connectionerror", "eof occurred", "1011")):
        return ("network",
                "Bağlantı zaman aşımına uğradı (internet yavaş ya da anlık kesinti). "
                "Yeniden deniyorum — bir şey yapmana gerek yok.",
                True)

    if any(k in text for k in ("api key not valid", "api_key_invalid", "unauthorized",
                               "permission denied", "401", "403", "invalid authentication")):
        return ("auth",
                "API anahtarı geçersiz görünüyor. AYARLAR > API AYARLARI'ndan "
                "anahtarı kontrol edip yeniden gir.",
                False)

    if any(k in text for k in ("quota", "rate limit", "429", "resource exhausted")):
        return ("quota",
                "Google tarafında kota/hız sınırına takıldık. Birkaç dakika sonra "
                "otomatik olarak yeniden bağlanacağım.",
                True)

    if any(k in text for k in ("voice", "not available for model", "invalid argument",
                               "1007", "400")):
        return ("config",
                f"Model/ses ayarında bir sorun var: {err}. AYARLAR'dan sesi "
                "değiştirmeyi dene.",
                False)

    return ("unknown", f"Bağlanamadım: {err}", True)


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
        self._lock   = threading.Lock()
        self._active = False
        self._thread: threading.Thread | None = None

    @property
    def is_active(self) -> bool:
        return self._active

    def get_latest_frame(self) -> bytes | None:
        """Thread-safe, her zaman en güncel kareyi döner."""
        with self._lock:
            return self._latest

    def start(self) -> str:
        with self._lock:
            if self._active:
                return "already_active"
            self._active = True
            self._latest = None
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
            print("[Webcam] opencv-python yüklü değil.")
            with self._lock:
                self._active = False
            return

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Webcam] Kamera açılamadı.")
            with self._lock:
                self._active = False
            return

        # Isınma — sensörün otomatik pozlaması oturuncaya kadar bekle
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

                frame = cv2.flip(frame, 1)  # yatay ayna — hem UI hem AI tutarlı
                ok, buf = cv2.imencode(".jpg", frame, enc_params)
                if ok:
                    with self._lock:
                        self._latest = buf.tobytes()

                # ~33 FPS yakala → 24 FPS UI her zaman taze kare bulur
                time.sleep(0.03)
        finally:
            cap.release()
            with self._lock:
                self._active = False
                self._latest = None
            print("[Webcam] Kamera serbest bırakıldı.")


CONTROL_TOKEN_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# ── Model ───────────────────────────────────────────────────────────────────
# Varsayılan mod (final14.md H3): config/anahtar yoksa GEMINI — tıklayınca
# API anahtar ekranı gelir, çökme YOK. Ollama yalnızca menüden seçilince.
MOD_VARSAYILAN = "gemini"

# Varsayılan Live API modeli — kullanıcı AYARLAR > 'GEMİNİ MODELİ' düğmesinden
# başka bir Live modeli seçmediyse bu kullanılır.
LIVE_MODEL_DEFAULT = "models/gemini-2.5-flash-native-audio-latest"


def get_live_model() -> str:
    """AYARLAR panelinden seçilen Gemini Live modelini döner; seçim yoksa
    LIVE_MODEL_DEFAULT'a düşer.

    Güvenlik notu: 'gemini-3.5-live-translate-preview' gibi ÇEVİRİYE ÖZEL
    modeller araç kullanımını/system_instruction'ı desteklemiyor ve bu
    uygulama ikisini de her bağlantıda gönderiyor — seçilirse sunucu "1011
    internal error" ile bağlantıyı kapatır. Daha önce (listeden kaldırılmadan
    önce) kaydedilmiş böyle bir model varsa burada otomatik yok sayılır."""
    chosen = str(get_app_config_value("gemini_live_model", "") or "").strip()
    if chosen and "translate" in chosen.lower():
        return LIVE_MODEL_DEFAULT
    return chosen or LIVE_MODEL_DEFAULT

# ── Audio ───────────────────────────────────────────────────────────────────
# NOT: mute_alsa_errors() burada, pyaudio.PyAudio() örneklenmeden HEMEN ÖNCE
# çağrılıyor — çünkü PyAudio() burada MODÜL YÜKLENİRKEN (import anında)
# çalışıyor ve PortAudio'nun sanal ALSA aygıtlarını (rear/center_lfe/side,
# jack, oss, a52, usb_stream) yoklaması TAM OLARAK BU ANDA oluyor. Bu satır
# olmadan, backend/audio_input.py'deki aynı fonksiyon çok daha geç (mikrofon
# akışı ilk gerçekten açıldığında) çağrıldığı için bu ilk PyAudio() anındaki
# gürültüyü YAKALAYAMIYORDU — terminaldeki o uzun "ALSA lib pcm.c..." bloğu
# buradan geliyordu, Vosk/wake-word ile bir ilgisi YOK (zararsız, sadece
# gözü korkutuyordu).
FORMAT           = pyaudio.paInt16 if pyaudio is not None else None
CHANNELS         = 1
SEND_SAMPLE_RATE = 16000
RECV_SAMPLE_RATE = 24000
CHUNK_SIZE       = 1024
# NOT: JACK sunucusuna bağlanma denemesi ('connect(2) call to .../jack_0
# failed', 'attempt to connect to server failed') ALSA'nın hata
# yakalayıcısından GEÇMİYOR — doğrudan işletim sistemi seviyesinde stderr'e
# yazılıyor, mute_alsa_errors() bunu göremez. suppress_native_stderr() bu
# tek çağrı etrafında dosya tanıtıcısını geçici olarak /dev/null'a alır.
pya = None
if pyaudio is not None:
    mute_alsa_errors()
    with suppress_native_stderr():
        try:
            pya = pyaudio.PyAudio()
        except Exception as _exc:
            print(f"[YERINDE] pyaudio başlatılamadı (ses özelliği pas geçer): {_exc}")
            pya = None

# ── Tool tanımları — paylaşılan modülden ────────────────────────────────────
from tool_defs import TOOL_DECLARATIONS


def get_api_key() -> str:
    return str(get_app_config_value("gemini_api_key", "") or "")


def load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "Sen YERINDE'sin — CachyOS'ta çalışan kişisel AI asistanı. "
            "Türkçe konuş. Kısa ve net yanıtlar ver. "
            "Araçları kullanarak görevleri tamamla, asla taklit etme."
        )


class YerindeLive:
    def __init__(self, ui: YerindeUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._music_proc    = None
        self._webcam_streamer = WebcamStreamer()
        self._webcam_streamer.on_log = lambda m: self.ui.write_log(m)
        self.webcam = self._webcam_streamer      # toggle_detection buradan erişir

        self._garden_streamer = GardenCamStreamer(
            on_log=lambda m: self.ui.write_log(m),
            on_state_change=self._on_garden_state_change,
            on_tool_state=self._on_garden_tool_state)
        self.garden = self._garden_streamer

        self.ui.on_text_command  = self._on_text_command
        self.ui.on_pause_toggle  = self._on_pause_toggle
        self.ui.on_effects_state_change = self._on_effects_state_change
        self.ui.on_webcam_toggle = self._on_webcam_toggle_ui
        self.ui.on_garden_toggle = self._on_garden_toggle_ui
        self.ui.on_garden_wake   = self._on_garden_wake
        self.ui.on_garden_ptz    = self._on_garden_ptz
        self.ui.on_garden_ptz_start = self._on_garden_ptz_start
        self.ui.on_garden_ptz_stop  = self._on_garden_ptz_stop
        self.ui.on_garden_horn   = self._on_garden_horn
        self.ui.on_garden_talk   = self._on_garden_talk
        self.ui.on_yolo_toggle = lambda enabled: self._webcam_streamer.set_detection(enabled)
        self.ui.on_stop_speaking = self._on_stop_speaking
        self.ui.on_camera_photo = lambda: take_photo(self._camera_capture_source())
        self.ui.on_camera_record_toggle = lambda starting: (
            media_capture.recorder.start(self._camera_capture_source()) if starting
            else media_capture.recorder.stop())
        self.ui.on_camera_pause_toggle = lambda pausing: (
            media_capture.recorder.pause() if pausing
            else media_capture.recorder.resume())
        self._paused             = False

        # Gemini (çevrim içi) modunda geçen her tur da, çevrim dışı moddaki
        # gibi yerel eğitim verisine (memory/habits.json) yazılsın diye:
        self._habits = HabitLearner("memory/habits.json")
        self._last_typed_text = ""  # sesli değil, yazıyla gönderilen son komut

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused
        if paused:
            self._stop_music()

    def _on_effects_state_change(self, enabled: bool):
        if not enabled:
            self._stop_music()

    def _on_webcam_toggle_ui(self, activate: bool):
        if activate:
            # Tek önizleme paneli — webcam açılırken bahçe kamerası kapanır.
            if self._garden_streamer.is_active:
                self._garden_streamer.stop()
                self.ui.set_garden_active(False)
            status = self._webcam_streamer.start()
            self.ui.set_webcam_active(status == "ok" or status == "already_active")
        else:
            self._webcam_streamer.stop()
            self.ui.set_webcam_active(False)

    def _on_garden_toggle_ui(self, activate: bool):
        if activate:
            # Tek önizleme paneli — bahçe kamerası açılırken webcam kapanır.
            if self._webcam_streamer.is_active:
                self._webcam_streamer.stop()
                self.ui.set_webcam_active(False)
            status = self._garden_streamer.start()
            self.ui.set_garden_active(status == "ok" or status == "already_active")
        else:
            self._garden_streamer.stop()
            self.ui.set_garden_active(False)

    def _camera_capture_source(self):
        """FOTO/VİDEO/DURAKLAT düğmeleri ve 'fotoğraf çek'/'video kaydet'
        sesli komutları için: o an hangi kamera akışı canlıysa (bahçe
        kamerası ya da webcam) onu döndürür. GardenCamStreamer,
        WebcamStreamer ile birebir aynı arayüzü (is_active/get_latest_frame)
        sunar, bu yüzden take_photo/record_video hangi kaynağı aldığını
        bilmeden ikisiyle de çalışır. İki kamera da kapalıysa webcam
        döner — bu durumda take_photo/record_video kendi geçici bağlantısını
        açmayı dener ve webcam bağlı değilse anlaşılır bir hata mesajı verir.
        """
        if self._garden_streamer.is_active:
            return self._garden_streamer
        return self._webcam_streamer

    def _on_garden_state_change(self, streaming: bool):
        """Kamera kendi kendine akışı kesti/geri getirdi — düğmeyi güncelle.

        Arka plan thread'inden gelir; Tkinter dokunuşları ana thread'de olmalı.
        Yalnızca kamera kaynaklı yaşam döngüsü değişimlerinde çağrılır
        (manuel aç/kapa zaten set_garden_active'i kendisi yapar).
        """
        try:
            self.ui.root.after(0, lambda: self.ui.set_garden_active(streaming))
        except Exception:
            pass

    def _on_garden_tool_state(self, talking, horn):
        """Alarm / konuşma butonlarının rengini backend durumuna göre günceller."""
        try:
            self.ui.root.after(0, lambda: self.ui.set_garden_tool_state(
                horn_on=horn, talking=talking))
        except Exception:
            pass

    def _on_garden_wake(self) -> str:
        result = self._garden_streamer.wake()
        if result == "ok":
            return "Bahçe kamerası uyandırıldı."
        return result

    def _on_garden_ptz(self, direction: str) -> str:
        labels = {
            "left": "sola", "right": "sağa", "up": "yukarı",
            "down": "aşağı", "center": "ortaya", "stop": "durdu",
        }
        result = self._garden_streamer.ptz(direction)
        if result == "ok":
            return f"Bahçe kamerası {labels.get(direction, direction)} döndürüldü."
        return result

    def _on_garden_ptz_start(self, direction: str) -> str:
        result = self._garden_streamer.ptz_start(direction)
        if result == "ok":
            return f"Bahçe kamerası {direction} yönünde dönüyor (bırakınca durur)."
        return result

    def _on_garden_ptz_stop(self) -> str:
        result = self._garden_streamer.ptz_stop()
        if result == "ok":
            return "Bahçe kamerası durdu."
        return result

    def _on_garden_horn(self) -> str:
        on = not getattr(self, "_garden_horn_on", False)
        result = self._garden_streamer.set_horn(on)
        if result == "ok":
            self._garden_horn_on = on
            return "Alarm çalıyor." if on else "Alarm durduruldu."
        return result

    def _on_garden_talk(self) -> str:
        if getattr(self, "_garden_talking", False):
            self._garden_talking = False
            self._garden_streamer.talk_stop()
            return "İki yönlü ses kapatıldı."
        result = self._garden_streamer.talk_start()
        if result == "ok":
            self._garden_talking = True
            return "Kameraya konuşuyorsunuz — tekrar tıklayınca kapanır."
        return result

    def _on_stop_speaking(self):
        """'DUR' düğmesi: YERINDE konuşurken veya düşünürken hemen susturur."""
        self._stop_music()
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(self._interrupt_audio(), self._loop)
        else:
            self.set_speaking(False)
        self.ui.write_log("SYS: Konuşma durduruldu.")

    def _focus_ui_section_for_tool(self, tool_name: str, args: dict):
        if tool_name == "sys_info":
            query = str(args.get("query", "")).strip().lower()
            if query in {"time", "saat", "zaman", "date", "tarih"}:
                self.ui.focus_panel("time", duration_ms=5200)
            else:
                self.ui.focus_panel("system", duration_ms=5200)
        elif tool_name == "get_weather":
            self.ui.focus_panel("weather", duration_ms=5600)

    def _on_text_command(self, text: str):
        if self._paused:
            return
        self.ui.write_log(f"Siz: {text}")
        if not self._loop or not self.session:
            self.ui.write_log("ERR: YERINDE bağlantısı henüz hazır değil.")
            return
        self._last_typed_text = text.strip()
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    async def _interrupt_audio(self):
        try:
            if self.audio_in_queue:
                while not self.audio_in_queue.empty():
                    try:
                        self.audio_in_queue.get_nowait()
                    except Exception:
                        break
            if self.session:
                await self.session.send_realtime_input(audio_stream_end=True)
            self.set_speaking(False)
        except Exception:
            pass

    def _stop_music(self):
        proc = self._music_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        self._music_proc = None

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        else:
            self.ui.set_state("LISTENING")

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.ui.write_debug(f"{tool_name}: {short}", level="ERROR")
        self.ui.set_state("ERROR")

    @staticmethod
    def _result_looks_like_error(result) -> bool:
        text = str(result or "").strip().lower()
        if not text:
            return False
        error_markers = (
            "hata",
            "error",
            "alinamadi",
            "alınamadı",
            "bulunamadi",
            "bulunamadı",
            "acilamadi",
            "açılamadı",
            "tamamlanamadi",
            "tamamlanamadı",
            "gecersiz",
            "geçersiz",
            "izin gerekiyor",
            "izin gerekli",
            "baglanti",
            "bağlantı",
            "gerekli.",
        )
        return any(marker in text for marker in error_markers)

    @staticmethod
    def _should_play_success_sfx(tool_name: str, args: dict, result) -> bool:
        action_tools = {
            "open_app",
            "close_app",
            "add_calendar_event",
            "add_reminder",
            "delete_calendar_event",
            "remove_calendar_event",
        }
        if tool_name in action_tools:
            return True

        if tool_name == "send_whatsapp_message":
            text = str(result or "").lower()
            if bool(args.get("send_now", False)):
                return "gönderildi" in text or "gonderildi" in text
            return False

        return False

    @staticmethod
    def _clean_transcript_text(text: str) -> tuple[str, bool]:
        raw = str(text or "")
        had_noise = False
        if CONTROL_TOKEN_RE.search(raw):
            had_noise = True
            raw = CONTROL_TOKEN_RE.sub(" ", raw)
        cleaned = []
        for ch in raw:
            if ch in "\n\r\t" or ord(ch) >= 32:
                cleaned.append(ch)
            else:
                had_noise = True
        normalized = " ".join("".join(cleaned).split())
        return normalized.strip(), had_noise

    def _build_config(self) -> types.LiveConnectConfig:
        import datetime
        memory  = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p   = load_system_prompt()
        now     = datetime.datetime.now()
        time_ctx = f"[ŞU ANKİ ZAMAN]\n{now.strftime('%A, %d %B %Y — %H:%M')}\n\n"

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_resolve_gemini_voice(
                            get_app_config_value("voice", "Charon"))
                    )
                )
            ),
            # ÖNEMLİ: native-audio modeli varsayılan olarak "thinking" (dahili
            # muhakeme) YAPIYOR — konuşmadan önce sessizce düşünüyor. Bu hem
            # ilk sesli yanıtı GECİKTİRİYOR ("bağlandı ama çıktı geç geldi"
            # şikayetinin sebebi budur) hem de SDK konsoluna zararsız ama
            # kafa karıştırıcı bir uyarı bastırıyor: "there are non-data
            # parts in the response: ['thought'], ...". thinking_budget=0
            # ile düşünmeyi tamamen kapatıyoruz → hem gecikme azalır hem
            # uyarı bir daha çıkmaz.
            thinking_config=types.ThinkingConfig(thinking_budget=gemini_thinking_budget()),
        )

    async def _send_tool_responses(self, fn_responses):
        """Araç yanıtlarını Gemini'ye SÜRÜMDEN BAĞIMSIZ gönderir.
        Yeni google-genai sürümleri düz liste kabul etmiyor ('Could not convert
        input (type list)') ve bu hata yakalanmayınca süreç SIGSEGV ile ölüyordu."""
        if not fn_responses:
            return

        # google-genai'nin yeni sürümlerinde (Python 3.13/3.14 ile gelen)
        # t_tool_response() LİSTE kabul etmiyor; TEK FunctionResponse ya da tek
        # dict bekliyor. Bu yüzden ÖNCE tek tek gönderiyoruz; eski sürümler için
        # liste gönderimi yedekte duruyor.
        errors = []
        try:
            for fr in fn_responses:
                await self.session.send_tool_response(function_responses=fr)
            return
        except Exception as e:
            errors.append(e)

        try:  # eski sürümler: liste kabul eder
            await self.session.send_tool_response(function_responses=fn_responses)
            return
        except Exception as e:
            errors.append(e)

        try:  # bazı sürümler: hazır LiveClientToolResponse nesnesi
            payload = types.LiveClientToolResponse(function_responses=list(fn_responses))
            await self.session.send_tool_response(payload)
            return
        except Exception as e:
            errors.append(e)

        try:  # son çare: dict'e çevirip tek tek
            for fr in fn_responses:
                d = fr.model_dump() if hasattr(fr, "model_dump") else dict(fr)
                await self.session.send_tool_response(function_responses=d)
            return
        except Exception as e:
            errors.append(e)

        self.ui.write_log(f"UYARI: Araç yanıtı gönderilemedi ({errors[0]}). "
                          "Komut çalıştı ama modele bildirilemedi.")

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})
        print(f"[YERINDE] 🔧 {name} {args}")
        self.ui.set_state("THINKING")

        loop   = asyncio.get_event_loop()
        result = "Tamam."
        had_exception = False

        try:
            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                    print(f"[Memory] 💾 {cat}/{key} = {val}")
                result = "ok"

            elif name == "delete_memory":
                result = delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            elif name == "open_app":
                _app_l = normalize_kind(str(args.get("app_name", "")))
                if _app_l in ("blender", "tasarım", "tasarim", "3d"):
                    # DİKKAT: burada 'return result' vardı — düz METİN dönüyordu,
                    # oysa _execute_tool types.FunctionResponse dönmeli. Bu yüzden
                    # Blender açıldıktan sonra araç yanıtı gönderilemiyor ve oturum
                    # bozuluyordu ("Could not convert input (type str)").
                    set_last_opened("blender")
                    result = await loop.run_in_executor(
                        None, blender_bridge.launch_blender_with_bridge)
                    _blank = None
                    _skip_open = True
                elif _app_l in ("freecad", "free cad"):
                    set_last_opened("freecad")
                    result = await loop.run_in_executor(
                        None, freecad_bridge.launch_freecad_with_bridge)
                    _blank = None
                    _skip_open = True
                else:
                    _skip_open = False
                _blank = None if not locals().get("_skip_open") else _blank
                if _app_l in OFFICE_KINDS:
                    _blank = await loop.run_in_executor(
                        None, lambda: create_blank_document(_app_l))
                if _skip_open:
                    pass                          # Blender köprüyle zaten açıldı
                elif _blank:
                    set_last_opened(_app_l)       # "kapat" hedefi bilinsin
                    result = _blank               # boş belge doğrudan açıldı
                else:
                    r = await loop.run_in_executor(
                        None, lambda: open_app(args.get("app_name", "")))
                    result = r or f"{args.get('app_name')} açıldı."

            elif name == "close_app":
                r = await loop.run_in_executor(
                    None, lambda: close_app(args.get("app_name", "")))
                result = r or f"{args.get('app_name')} kapatıldı."

            elif name == "sys_info":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: sys_info(args.get("query", "all")))
                result = r or "Bilgi alındı."

            elif name == "get_forecast":
                r = await loop.run_in_executor(
                    None, lambda: get_forecast_summary(int(args.get("days", 7) or 7)))
                result = r

            elif name == "get_weather":
                self._focus_ui_section_for_tool(name, args)
                r = await loop.run_in_executor(
                    None, lambda: get_weather_summary(args.get("location") or None))
                result = r or "Hava durumu bilgisi alindi."

            elif name == "get_calendar_events":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_calendar_events(
                        args.get("query", "today"),
                        int(args.get("limit", 6) or 6),
                    ),
                )
                result = r or "Takvim bilgisi alindi."

            elif name == "add_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("end_iso", ""),
                        args.get("notes", ""),
                        args.get("location", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Takvim etkinligi eklendi."

            elif name == "delete_calendar_event":
                r = await loop.run_in_executor(
                    None,
                    lambda: delete_calendar_event(
                        args.get("title", ""),
                        args.get("start_iso", ""),
                        args.get("calendar_name", ""),
                        bool(args.get("delete_all_matches", False)),
                    ),
                )
                result = r or "Takvim etkinligi silindi."

            elif name == "get_reminders":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_reminders(
                        args.get("query", "upcoming"),
                        int(args.get("limit", 8) or 8),
                        args.get("list_name", ""),
                    ),
                )
                result = r or "Animsatici bilgisi alindi."

            elif name == "add_reminder":
                r = await loop.run_in_executor(
                    None,
                    lambda: add_reminder(
                        args.get("title", ""),
                        args.get("due_iso", ""),
                        args.get("notes", ""),
                        args.get("list_name", ""),
                        args.get("priority", ""),
                        bool(args.get("all_day", False)),
                    ),
                )
                result = r or "Animsatici eklendi."

            elif name == "browser_control":
                r = await loop.run_in_executor(
                    None, lambda: browser_control(
                        args.get("action"),
                        args.get("url"),
                        args.get("query")
                    ))
                result = r or "Tamam."

            elif name == "shell_run":
                r = await loop.run_in_executor(
                    None, lambda: shell_run(args.get("command", "")))
                result = r or "Komut çalıştırıldı."

            elif name == "toggle_webcam":
                action = str(args.get("action", "start")).strip().lower()
                if action == "start":
                    status = self._webcam_streamer.start()
                    if status == "ok":
                        self.ui.set_webcam_active(True)
                        result = (
                            "Webcam akışı başlatıldı. "
                            "Artık kameranı görüyorum — dilediğin zaman soru sorabilirsin."
                        )
                    elif status == "already_active":
                        result = "Webcam zaten açık, görüntü alıyorum."
                    else:
                        result = "Webcam başlatılamadı: opencv-python yüklü değil."
                else:
                    self._webcam_streamer.stop()
                    self.ui.set_webcam_active(False)
                    result = "Webcam akışı durduruldu."

            elif name == "toggle_garden_cam":
                action = str(args.get("action", "start")).strip().lower()
                if action == "start":
                    # Bahçe kamerası uykuda olabilir; açma uyandırmayı da içerir.
                    if self._webcam_streamer.is_active:
                        self._webcam_streamer.stop()
                        self.ui.set_webcam_active(False)
                    status = await loop.run_in_executor(
                        None, self._garden_streamer.start)
                    if status == "ok":
                        self.ui.set_garden_active(True)
                        result = (
                            "Bahçe kamerası açıldı. "
                            "Bahçenin canlı görüntüsünü alıyorum — dilediğin "
                            "zaman yön değiştirmemi isteyebilirsin."
                        )
                    elif status == "already_active":
                        self.ui.set_garden_active(True)
                        result = "Bahçe kamerası zaten açık, görüntü alıyorum."
                    else:
                        result = ("Bahçe kamerası açılamadı — güneş enerjili "
                                  "kamera uykuda olabilir. Lütfen önce 'bahçe "
                                  "kamerasını uyandır' komutunu dene. (%s)" % status)
                else:
                    await loop.run_in_executor(None, self._garden_streamer.stop)
                    self.ui.set_garden_active(False)
                    result = "Bahçe kamerası akışı durduruldu (kamera uyuyabilir)."

            elif name == "wake_garden_cam":
                status = await loop.run_in_executor(
                    None, self._garden_streamer.wake)
                if status == "ok":
                    result = "Bahçe kamerası uyandırıldı. Şimdi 'bahçe kamerasını aç' diyerek görüntüyü başlatabilirsin."
                else:
                    result = "Bahçe kamerası uyandırılamadı. Kamera uykuda ve ulaşılamıyor olabilir. (%s)" % status

            elif name == "garden_ptz":
                direction = str(args.get("direction", "")).strip().lower()
                status = await loop.run_in_executor(
                    None, lambda: self._garden_streamer.ptz(direction))
                labels = {
                    "left": "sola", "right": "sağa", "up": "yukarı",
                    "down": "aşağı", "center": "ortaya", "stop": "durdu",
                }
                if status == "ok":
                    result = "Bahçe kamerası %s döndürüldü." % labels.get(direction, direction)
                else:
                    result = status

            elif name == "garden_ptz_start":
                direction = str(args.get("direction", "")).strip().lower()
                status = await loop.run_in_executor(
                    None, lambda: self._garden_streamer.ptz_start(direction))
                if status == "ok":
                    await loop.run_in_executor(None, self._garden_streamer.ptz_stop)
                    result = "Bahçe kamerası %s yönüne döndürüldü." % direction
                else:
                    result = status

            elif name == "garden_ptz_stop":
                status = await loop.run_in_executor(
                    None, self._garden_streamer.ptz_stop)
                result = "Bahçe kamerası durdu." if status == "ok" else status

            elif name == "garden_horn":
                on = not getattr(self, "_garden_horn_on", False)
                status = await loop.run_in_executor(
                    None, lambda: self._garden_streamer.set_horn(on))
                if status == "ok":
                    self._garden_horn_on = on
                    result = "Alarm çalıyor." if on else "Alarm durduruldu."
                else:
                    result = status

            elif name == "garden_talk":
                if getattr(self, "_garden_talking", False):
                    self._garden_talking = False
                    await loop.run_in_executor(None, self._garden_streamer.talk_stop)
                    result = "İki yönlü ses kapatıldı."
                else:
                    status = await loop.run_in_executor(
                        None, self._garden_streamer.talk_start)
                    if status == "ok":
                        self._garden_talking = True
                        result = "Kameraya konuşuyorsunuz — tekrar deyince kapanır."
                    else:
                        result = status

            elif name == "play_media":
                r = await loop.run_in_executor(
                    None,
                    lambda: play_media(
                        args.get("query", ""),
                        args.get("provider", "auto"),
                        bool(args.get("autoplay", True)),
                    ),
                )
                result = r or "Medya oynatma başlatıldı."

            elif name == "get_youtube_channel_report":
                r = await loop.run_in_executor(
                    None,
                    lambda: get_youtube_channel_report(
                        args.get("query", "overview"),
                        args.get("handle", ""),
                        int(args.get("video_limit", 6) or 6),
                    ),
                )
                result = r or "YouTube kanal raporu alindi."

            elif name == "analyze_screen":
                r = await loop.run_in_executor(
                    None,
                    lambda: analyze_screen(
                        args.get("query", "Ekranda ne var?"),
                        args.get("target", "active_window"),
                    ),
                )
                result = r or "Ekran analizi tamamlandi."

            elif name == "send_whatsapp_message":
                r = await loop.run_in_executor(
                    None,
                    lambda: send_whatsapp_message(
                        args.get("message", ""),
                        args.get("phone_number", ""),
                        args.get("recipient_name", ""),
                        bool(args.get("send_now", False)),
                        args.get("app_target", "auto"),
                    ),
                )
                result = r or "WhatsApp işlemi tamamlandı."

            elif name == "save_whatsapp_contact":
                r = await loop.run_in_executor(
                    None,
                    lambda: save_whatsapp_contact(
                        args.get("display_name", ""),
                        args.get("phone_number", ""),
                        args.get("aliases", ""),
                    ),
                )
                result = r or "WhatsApp kişisi kaydedildi."

            elif name == "take_photo":
                r = await loop.run_in_executor(
                    None, lambda: take_photo(self._camera_capture_source()))
                result = r or "Fotoğraf çekildi."

            elif name == "record_video":
                r = await loop.run_in_executor(
                    None, lambda: record_video(args.get("seconds", 5),
                                               self._camera_capture_source()))
                result = r or "Video kaydedildi."

            elif name == "zumre_tutanagi_olustur":
                r = await loop.run_in_executor(
                    None, lambda: zumre_tutanagi_olustur(
                        args.get("donem_turu", ""),
                        args.get("toplanti_tarihi", ""),
                        args.get("toplanti_saati", ""),
                        args.get("toplanti_no", ""),
                        args.get("ders_yili", ""),
                        args.get("ek_talimat", ""),
                        args.get("dosya_yolu", ""),
                        args.get("ders", "")))
                result = r or "Zümre tutanağı hazırlandı."

            elif name == "referans_belge_kaydet":
                r = await loop.run_in_executor(
                    None, lambda: referans_belge_kaydet(
                        args.get("tur", ""), args.get("dosya_yolu", "")))
                result = r or "Referans kaydedildi."

            elif name == "sinav_olustur":
                r = await loop.run_in_executor(
                    None, lambda: sinav_olustur(
                        args.get("ders", "bilişim"),
                        args.get("sinif", "5"),
                        args.get("sinav_no", "1"),
                        args.get("senaryo_no", "1"),
                        args.get("donem", "2"),
                        args.get("soru_sayisi", 0),
                        args.get("konu_kapsam", ""),
                        args.get("ek_talimat", ""),
                        args.get("ksdt_dosya_yolu", ""),
                        args.get("yillik_plan_dosya_yolu", ""),
                        args.get("soru_tipi", "karışık")))
                result = r or "Sınav hazırlandı."

            elif name == "yillik_plan_guncelle":
                r = await loop.run_in_executor(
                    None, lambda: yillik_plan_guncelle(
                        args.get("ders", "bilişim"),
                        args.get("sinif", "5"),
                        args.get("egitim_yili", ""),
                        args.get("dosya_yolu", "")))
                result = r or "Yıllık plan güncellendi."

            elif name == "gunluk_plan_olustur":
                r = await loop.run_in_executor(
                    None, lambda: gunluk_plan_olustur(
                        args.get("ders", "bilişim"),
                        args.get("sinif", "5"),
                        args.get("hafta_no", ""),
                        args.get("konu_arama", ""),
                        args.get("ek_talimat", ""),
                        args.get("yillik_plan_dosya_yolu", "")))
                result = r or "Günlük plan hazırlandı."

            elif name == "kulup_calisma_plani_olustur":
                r = await loop.run_in_executor(
                    None, lambda: kulup_calisma_plani_olustur(
                        args.get("egitim_yili", ""),
                        args.get("katilimci_toplam", ""),
                        args.get("katilimci_kiz", ""),
                        args.get("katilimci_erkek", ""),
                        args.get("danisman_adi", ""),
                        bool(args.get("etkinlikleri_yenile", False)),
                        args.get("ek_talimat", ""),
                        args.get("dosya_yolu", "")))
                result = r or "Kulüp çalışma planı hazırlandı."

            elif name == "olcek_hazirla":
                r = await loop.run_in_executor(
                    None, lambda: olcek_hazirla(
                        args.get("ders", "bilişim"),
                        args.get("sinif", "5/A"),
                        args.get("donem", ""),
                        args.get("egitim_yili", ""),
                        args.get("ogrenciler", ""),
                        args.get("puantaj_dosya_yolu", ""),
                        args.get("dosya_yolu", "")))
                result = r or "Ölçek hazırlandı."

            elif name == "analyze_document":
                r = await loop.run_in_executor(
                    None, lambda: analyze_document(
                        args.get("file_path", ""), args.get("query", "")))
                result = r or "Belge analiz edildi."

            elif name == "read_document_aloud":
                r = await loop.run_in_executor(
                    None, lambda: read_document_aloud(args.get("file_path", "")))
                result = r or "Belge sesli okundu."

            elif name == "system_volume":
                r = await loop.run_in_executor(None, lambda: system_volume(
                    str(args.get("action", "")), int(args.get("step", 10) or 10)))
                result = r

            elif name == "media_control":
                r = await loop.run_in_executor(None, lambda: media_control(str(args.get("action", ""))))
                result = r

            elif name == "arkaplan_command":
                if not self.ui:
                    result = "Arayüz bağlantısı yok."
                else:
                    raw = str(args.get("mod", "")).strip().lower()
                    mod = {"açık": "acik", "acik": "acik", "aydınlık": "acik",
                           "koyu": "koyu", "karanlık": "koyu",
                           "sade": "sade", "normal": "sade", "normale": "sade"}.get(raw, raw)
                    if mod in ("acik", "koyu"):
                        result = self.ui.set_bg_image_builtin(mod)
                    elif mod == "sade":
                        result = self.ui.clear_bg_image_voice()
                    else:
                        result = "Tanımadığım bir arkaplan modu — 'açık', 'koyu' ya da 'sade' diyebilirsin."

            elif name == "tema_command":
                result = self.ui.set_theme_by_voice(str(args.get("mod", ""))) if self.ui else "Arayüz bağlantısı yok."

            elif name == "save_active_document":
                r = await loop.run_in_executor(None, save_active_document)
                result = r

            elif name == "office_format":
                r = await loop.run_in_executor(None, lambda: office_format(
                    str(args.get("action", "")), str(args.get("value", ""))))
                result = r

            elif name == "mouse_control":
                r = await loop.run_in_executor(None, lambda: mouse_control(
                    str(args.get("action", "")), str(args.get("direction", "")),
                    int(args.get("amount", 0) or 0)))
                result = r

            elif name == "record_voice_sample":
                r = await loop.run_in_executor(None, lambda: record_voice_sample(
                    int(args.get("seconds", 10) or 10), on_log=self.ui.write_log))
                result = r

            elif name == "insert_image":
                r = await loop.run_in_executor(None, lambda: insert_image(str(args.get("source", ""))))
                result = r

            elif name == "whatsapp_call":
                r = await loop.run_in_executor(None, lambda: whatsapp_call(
                    str(args.get("contact", "")), str(args.get("kind", "voice")),
                    on_log=self.ui.write_log))
                result = r

            elif name == "calibrate_whatsapp":
                r = await loop.run_in_executor(None, lambda: calibrate_call_button(
                    str(args.get("kind", "voice")), on_log=self.ui.write_log))
                result = r

            elif name == "play_stream":
                r = await loop.run_in_executor(None, lambda: play_stream(
                    str(args.get("service", "")), str(args.get("query", ""))))
                result = r

            elif name == "scratch_command":
                r = await loop.run_in_executor(None, lambda: scratch_command(
                    str(args.get("action", "")), str(args.get("value", "")),
                    str(args.get("text", "")), str(args.get("times", "")),
                    str(args.get("key", ""))))
                result = r

            elif name == "blockly_command":
                from actions.blockly_games import open_blockly_game
                r = await loop.run_in_executor(
                    None, lambda: open_blockly_game(str(args.get("key", ""))))
                result = r

            elif name == "blockly_games_kapat_command":
                from actions.blockly_games import blockly_games_kapat_command
                result = blockly_games_kapat_command()

            elif name == "akis_command":
                from actions.akis_semasi import open_akis_semasi
                result = open_akis_semasi()

            elif name == "akis_semasi_kapat_command":
                from actions.akis_semasi import akis_semasi_kapat_command
                result = akis_semasi_kapat_command()

            elif name == "carkifelek_command":
                from actions.carkifelek import open_carkifelek
                result = open_carkifelek()

            elif name == "carkifelek_kapat_command":
                from actions.carkifelek import carkifelek_kapat_command
                result = carkifelek_kapat_command()

            elif name == "satranc_command":
                from actions.satranc import open_satranc
                result = open_satranc()

            elif name == "satranc_kapat_command":
                from actions.satranc import satranc_kapat_command
                result = satranc_kapat_command()

            elif name == "cin_damasi_command":
                from actions.cin_damasi import open_cin_damasi
                result = open_cin_damasi()

            elif name == "cin_damasi_kapat_command":
                from actions.cin_damasi import cin_damasi_kapat_command
                result = cin_damasi_kapat_command()

            elif name == "robotik_simulator_command":
                from actions.robotik_simulator import open_robotik_simulator
                result = open_robotik_simulator()

            elif name == "robotik_simulator_kapat_command":
                from actions.robotik_simulator import robotik_simulator_kapat_command
                result = robotik_simulator_kapat_command()

            elif name == "tasarim_studyosu_command":
                from actions.tasarim_studyosu import open_tasarim_studyosu
                result = open_tasarim_studyosu()

            elif name == "robot_tasarim_command":
                from actions.robot_tasarim import open_robot_tasarim_araci
                result = open_robot_tasarim_araci()

            elif name == "donanim_atolyesi_command":
                from actions.donanim_atolyesi import open_donanim_atolyesi
                result = open_donanim_atolyesi()

            elif name == "donanim_anladim_command":
                from actions.donanim_atolyesi import anladim_command
                result = anladim_command()

            elif name == "donanim_parca_ekle_command":
                from actions.donanim_atolyesi import parca_ekle_command
                result = parca_ekle_command(args.get("parca", ""))

            elif name == "donanim_parca_sok_command":
                from actions.donanim_atolyesi import parca_sok_command
                result = parca_sok_command(args.get("parca", ""))

            elif name == "donanim_tema_command":
                from actions.donanim_atolyesi import tema_command
                result = tema_command(args.get("tema", ""))

            elif name == "resim_pdf_command":
                from actions.resim_pdf_atolyesi import open_resim_pdf_atolyesi
                result = open_resim_pdf_atolyesi()

            elif name == "resim_pdf_ayar_command":
                from actions.resim_pdf_atolyesi import resim_pdf_ayar_command
                result = resim_pdf_ayar_command(
                    args.get("arac", ""), args.get("eylem", ""), str(args.get("deger", "")))

            elif name == "video_atolyesi_command":
                from actions.video_atolyesi import open_video_atolyesi
                result = open_video_atolyesi()

            elif name == "video_atolyesi_ayar_command":
                from actions.video_atolyesi import video_atolyesi_ayar_command
                result = video_atolyesi_ayar_command(
                    args.get("sekme", ""), args.get("eylem", ""), str(args.get("deger", "")))

            elif name == "kukla_kodlama_command":
                from actions.kukla_kodlama import open_kukla_kodlama_atolyesi
                result = open_kukla_kodlama_atolyesi()

            elif name == "kukla_calistir_command":
                from actions.kukla_kodlama import kukla_calistir_command
                result = kukla_calistir_command()

            elif name == "kukla_durdur_command":
                from actions.kukla_kodlama import kukla_durdur_command
                result = kukla_durdur_command()

            elif name == "kukla_ekle_command":
                from actions.kukla_kodlama import kukla_ekle_command
                result = kukla_ekle_command(args.get("isim", ""))

            elif name == "kukla_sec_command":
                from actions.kukla_kodlama import kukla_sec_command
                result = kukla_sec_command(args.get("tanim", ""))

            elif name == "kukla_mod_degistir_command":
                from actions.kukla_kodlama import kukla_mod_degistir_command
                result = kukla_mod_degistir_command(args.get("mod", ""))

            elif name == "kukla_tema_command":
                from actions.kukla_kodlama import kukla_tema_command
                result = kukla_tema_command(args.get("tema", ""))

            elif name == "kukla_kapat_command":
                from actions.kukla_kodlama import kukla_kapat_command
                result = kukla_kapat_command()

            elif name == "kukla_zemin_dokusu_command":
                from actions.kukla_kodlama import kukla_zemin_dokusu_command
                result = kukla_zemin_dokusu_command(args.get("doku", ""))

            elif name == "kukla_kaydet_command":
                from actions.kukla_kodlama import kukla_kaydet_command
                result = kukla_kaydet_command()

            elif name == "kukla_ac_command":
                from actions.kukla_kodlama import kukla_ac_command
                result = kukla_ac_command(args.get("dosya_adi", ""))

            elif name == "karakter_blok_ekle_command":
                from actions.kukla_kodlama import karakter_blok_ekle_command
                result = karakter_blok_ekle_command(args.get("blok", ""), str(args.get("deger", "")))

            elif name == "karakter_blok_sil_command":
                from actions.kukla_kodlama import karakter_blok_sil_command
                result = karakter_blok_sil_command()

            elif name == "bilisim_robotik_atolyesi_command":
                from actions.bilisim_robotik_atolyesi import open_bilisim_robotik_atolyesi
                result = open_bilisim_robotik_atolyesi()

            elif name == "bilisim_robotik_unite_gec_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_unite_gec_command
                result = bilisim_robotik_unite_gec_command(args.get("unite", ""))

            elif name == "bilisim_robotik_tema_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_tema_command
                result = bilisim_robotik_tema_command(args.get("tema", ""))

            elif name == "bilisim_robotik_kapat_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_kapat_command
                result = bilisim_robotik_kapat_command()

            elif name == "bilisim_labirent_komut_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_komut_command
                result = bilisim_labirent_komut_command(args.get("komut", ""), args.get("labirent", "1"))

            elif name == "bilisim_labirent_calistir_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_calistir_command
                result = bilisim_labirent_calistir_command(args.get("labirent", "1"))

            elif name == "bilisim_labirent_geri_al_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_geri_al_command
                result = bilisim_labirent_geri_al_command(args.get("labirent", "1"))

            elif name == "bilisim_labirent_temizle_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_temizle_command
                result = bilisim_labirent_temizle_command(args.get("labirent", "1"))

            elif name == "bilisim_kart_cevir_command":
                from actions.bilisim_robotik_atolyesi import bilisim_kart_cevir_command
                result = bilisim_kart_cevir_command(args.get("kart_no", ""))

            elif name == "bilisim_quiz_cevapla_command":
                from actions.bilisim_robotik_atolyesi import bilisim_quiz_cevapla_command
                result = bilisim_quiz_cevapla_command(args.get("secenek", ""))

            elif name == "bilisim_ilerlemeyi_sifirla_command":
                from actions.bilisim_robotik_atolyesi import bilisim_ilerlemeyi_sifirla_command
                result = bilisim_ilerlemeyi_sifirla_command()

            elif name == "bilisim_web_ekle_command":
                from actions.bilisim_robotik_atolyesi import bilisim_web_ekle_command
                result = bilisim_web_ekle_command(args.get("eleman", ""))

            elif name == "pico_devre_atolyesi_command":
                from actions.pico_devre_atolyesi import open_pico_devre_atolyesi
                result = open_pico_devre_atolyesi()

            elif name == "pico_kart_degistir_command":
                from actions.pico_devre_atolyesi import pico_kart_degistir_command
                result = pico_kart_degistir_command(args.get("kart", ""))

            elif name == "pico_bilesen_ekle_command":
                from actions.pico_devre_atolyesi import pico_bilesen_ekle_command
                result = pico_bilesen_ekle_command(args.get("bilesen", ""))

            elif name == "pico_bilesen_sil_command":
                from actions.pico_devre_atolyesi import pico_bilesen_sil_command
                result = pico_bilesen_sil_command(args.get("bilesen", ""))

            elif name == "pico_bilesen_dondur_command":
                from actions.pico_devre_atolyesi import pico_bilesen_dondur_command
                result = pico_bilesen_dondur_command(args.get("bilesen", ""))

            elif name == "pico_bilesen_tasi_command":
                from actions.pico_devre_atolyesi import pico_bilesen_tasi_command
                result = pico_bilesen_tasi_command(
                    args.get("bilesen", ""), args.get("yon", ""), str(args.get("miktar", "1")))

            elif name == "pico_kablo_sil_command":
                from actions.pico_devre_atolyesi import pico_kablo_sil_command
                result = pico_kablo_sil_command(
                    args.get("bilesen1", ""), args.get("pin1", ""),
                    args.get("bilesen2", ""), args.get("pin2", ""))

            elif name == "pico_blok_ekle_command":
                from actions.pico_devre_atolyesi import pico_blok_ekle_command
                result = pico_blok_ekle_command(
                    args.get("blok", ""), str(args.get("pin", "")), str(args.get("pin2", "")),
                    str(args.get("deger", "")), str(args.get("yon", "")), str(args.get("birim", "")))

            elif name == "pico_blok_sil_command":
                from actions.pico_devre_atolyesi import pico_blok_sil_command
                result = pico_blok_sil_command()

            elif name == "pico_mod_degistir_command":
                from actions.pico_devre_atolyesi import pico_mod_degistir_command
                result = pico_mod_degistir_command(args.get("mod", ""))

            elif name == "pico_tema_degistir_command":
                from actions.pico_devre_atolyesi import pico_tema_degistir_command
                result = pico_tema_degistir_command(args.get("tema", ""))

            elif name == "pico_yakinlastir_command":
                from actions.pico_devre_atolyesi import pico_yakinlastir_command
                result = pico_yakinlastir_command(args.get("yon", ""))

            elif name == "pico_calistir_command":
                from actions.pico_devre_atolyesi import pico_calistir_command
                result = pico_calistir_command()

            elif name == "pico_durdur_command":
                from actions.pico_devre_atolyesi import pico_durdur_command
                result = pico_durdur_command()

            elif name == "pico_kaydet_command":
                from actions.pico_devre_atolyesi import pico_kaydet_command
                result = pico_kaydet_command()

            elif name == "pico_ac_command":
                from actions.pico_devre_atolyesi import pico_ac_command
                result = pico_ac_command(args.get("dosya_adi", ""))

            elif name == "pico_kodu_indir_command":
                from actions.pico_devre_atolyesi import pico_kodu_indir_command
                result = pico_kodu_indir_command()

            elif name == "pico_bagla_command":
                from actions.pico_devre_atolyesi import pico_bagla_command
                result = pico_bagla_command(
                    args.get("bilesen1", ""), args.get("pin1", ""),
                    args.get("bilesen2", ""), args.get("pin2", ""))

            elif name == "pico_seri_monitor_command":
                from actions.pico_devre_atolyesi import pico_seri_monitor_command
                result = pico_seri_monitor_command(args.get("durum", "ac"))

            elif name == "pico_kapat_command":
                from actions.pico_devre_atolyesi import pico_kapat_command
                result = pico_kapat_command()

            elif name == "tasarim_tema_command":
                from actions.tasarim_studyosu import tasarim_tema_command
                result = tasarim_tema_command(args.get("tema", ""))

            elif name == "tasarim_kapat_command":
                from actions.tasarim_studyosu import tasarim_kapat_command
                result = tasarim_kapat_command()

            elif name == "tasarim_ekle_sekil_command":
                from actions.tasarim_studyosu import ekle_sekil_command
                result = ekle_sekil_command(args.get("sekil", ""))

            elif name == "tasarim_robot_parca_ekle_command":
                from actions.tasarim_studyosu import robot_parca_ekle_command
                result = robot_parca_ekle_command(args.get("parca", ""))

            elif name == "tasarim_renk_command":
                from actions.tasarim_studyosu import renk_command
                result = renk_command(args.get("renk", ""))

            elif name == "tasarim_malzeme_command":
                from actions.tasarim_studyosu import malzeme_command
                result = malzeme_command(args.get("malzeme", ""))

            elif name == "tasarim_doku_uygula_command":
                from actions.tasarim_studyosu import doku_uygula_command
                result = doku_uygula_command(args.get("doku", ""))

            elif name == "tasarim_tasi_command":
                from actions.tasarim_studyosu import tasi_command
                result = tasi_command(args.get("yon", ""))

            elif name == "tasarim_boyutlandir_command":
                from actions.tasarim_studyosu import boyutlandir_command
                result = boyutlandir_command(args.get("yon", ""), args.get("eksen"))

            elif name == "tasarim_dondur_command":
                from actions.tasarim_studyosu import dondur_command
                result = dondur_command(args.get("yon", ""))

            elif name == "tasarim_donusu_baslat_command":
                from actions.tasarim_studyosu import donusu_baslat_command
                result = donusu_baslat_command(args.get("eksen", "y"))

            elif name == "tasarim_donusu_durdur_command":
                from actions.tasarim_studyosu import donusu_durdur_command
                result = donusu_durdur_command()

            elif name == "tasarim_yorunge_baslat_command":
                from actions.tasarim_studyosu import yorunge_baslat_command
                result = yorunge_baslat_command(args.get("eksen", "y"))

            elif name == "tasarim_yorunge_durdur_command":
                from actions.tasarim_studyosu import yorunge_durdur_command
                result = yorunge_durdur_command()

            elif name == "tasarim_nesne_sec_command":
                from actions.tasarim_studyosu import nesne_sec_command
                result = nesne_sec_command(args.get("tanim", ""), args.get("renk", ""))

            elif name == "tasarim_stl_kaydet_command":
                from actions.tasarim_studyosu import stl_kaydet_command
                result = stl_kaydet_command(args.get("isim", ""))

            elif name == "tasarim_stl_ac_command":
                from actions.tasarim_studyosu import stl_ac_command
                result = stl_ac_command(args.get("dosya_adi", ""))

            elif name == "tasarim_glb_kaydet_command":
                from actions.tasarim_studyosu import glb_kaydet_command
                result = glb_kaydet_command(args.get("isim", ""))

            elif name == "tasarim_glb_ac_command":
                from actions.tasarim_studyosu import glb_ac_command
                result = glb_ac_command(args.get("dosya_adi", ""))

            elif name == "tasarim_glb_indir_command":
                from actions.tasarim_studyosu import glb_indir_command
                result = glb_indir_command()

            elif name == "tasarim_nesne_ortala_command":
                from actions.tasarim_studyosu import nesne_ortala_command
                result = nesne_ortala_command()

            elif name == "tasarim_kopyala_command":
                from actions.tasarim_studyosu import kopyala_command
                result = kopyala_command()

            elif name == "tasarim_kenar_yumusat_command":
                from actions.tasarim_studyosu import kenar_yumusat_command
                result = kenar_yumusat_command(args.get("miktar", ""))

            elif name == "tasarim_birlestir_command":
                from actions.tasarim_studyosu import birlestir_command
                result = birlestir_command()

            elif name == "tasarim_birlestirmeyi_geri_al_command":
                from actions.tasarim_studyosu import birlestirmeyi_geri_al_command
                result = birlestirmeyi_geri_al_command()

            elif name == "tasarim_nesne_sil_command":
                from actions.tasarim_studyosu import nesne_sil_command
                result = nesne_sil_command()

            elif name == "tasarim_delik_yap_command":
                from actions.tasarim_studyosu import delik_yap_command
                result = delik_yap_command()

            elif name == "tasarim_kati_yap_command":
                from actions.tasarim_studyosu import kati_yap_command
                result = kati_yap_command()

            elif name == "tasarim_delikleri_uygula_command":
                from actions.tasarim_studyosu import delikleri_uygula_command
                result = delikleri_uygula_command()

            elif name == "tasarim_stl_indir_command":
                from actions.tasarim_studyosu import stl_indir_command
                result = stl_indir_command()

            elif name == "tasarim_temizle_command":
                from actions.tasarim_studyosu import sahneyi_temizle_command
                result = sahneyi_temizle_command()

            elif name == "tasarim_blendere_aktar_command":
                from actions.tasarim_studyosu import blendere_aktar_command
                result = blendere_aktar_command(args.get("isim", ""))

            elif name == "tasarim_blend_ac_command":
                from actions.tasarim_studyosu import blend_dosyasi_ac_command
                result = blend_dosyasi_ac_command(args.get("dosya_adi", ""))

            elif name == "obs_kayit_baslat_command":
                from actions.obs_kayit import start_recording
                result = start_recording()

            elif name == "obs_kayit_duraklat_command":
                from actions.obs_kayit import pause_recording
                result = pause_recording()

            elif name == "obs_kayit_devam_command":
                from actions.obs_kayit import resume_recording
                result = resume_recording()

            elif name == "obs_kayit_bitir_command":
                from actions.obs_kayit import stop_recording
                result = stop_recording()

            elif name == "egitim_baslat_command":
                from actions.model_egitimi import egitim_baslat_command
                result = egitim_baslat_command()

            elif name == "egitim_verisi_command":
                from backend.habits import HabitLearner
                _hl = HabitLearner("memory/habits.json")
                _action = str(args.get("action", "stats")).lower()
                _me_dir = Path(__file__).resolve().parent / "model-egitimi"
                _me_dir.mkdir(parents=True, exist_ok=True)
                if _action == "export":
                    result = _hl.export_dataset(_me_dir / "egitim_verisi.jsonl")
                elif _action == "import":
                    _candidates = sorted(_me_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
                    _name_key = str(args.get("dosya_adi", "")).strip().lower()
                    _matches = [p for p in _candidates if _name_key and _name_key in p.stem.lower()]
                    _chosen = _matches[0] if _matches else (_candidates[0] if _candidates else None)
                    if _chosen is None:
                        result = ("model-egitimi klasöründe hiç .jsonl dosyası "
                                 "bulunamadı — önce içe aktarılacak dosyayı oraya koyar mısın?")
                    else:
                        result = _hl.import_dataset(_chosen)
                else:
                    _stats = _hl.dataset_stats()
                    _rotalar = ", ".join(f"{k}: {v}" for k, v in _stats["rotalar"].items()) or "yok"
                    result = (f"Şu ana kadar {_stats['toplam_olay']} etkileşim kaydedildi, "
                             f"{_stats['egitime_uygun']} tanesi eğitime uygun. Rotalar: {_rotalar}.")

            elif name == "blockly_solve":
                from actions.blockly_solver import solve_maze_level
                try:
                    _level = int(args.get("level", 1))
                except Exception:
                    _level = 1
                r = await loop.run_in_executor(
                    None, lambda: solve_maze_level(_level, use_alt=bool(args.get("alt"))))
                result = r

            elif name == "blockly_describe":
                from actions.blockly_solver import describe_maze_level
                try:
                    _level2 = int(args.get("level", 1))
                except Exception:
                    _level2 = 1
                result = describe_maze_level(_level2, use_alt=bool(args.get("alt")))

            elif name == "piper_dataset":
                def _pd():
                    action = str(args.get("action", "status")).lower()
                    idx = args.get("index")
                    log = self.ui.write_log
                    if action == "record":
                        idx0 = int(idx) - 1 if idx else None
                        return piper_dataset.record_sentence(idx0, on_log=log)
                    if action == "status":
                        return piper_dataset.dataset_status()
                    if action == "package":
                        return piper_dataset.package_dataset(on_log=log)
                    if action == "redo":
                        if not idx:
                            return "Hangi cümleyi tekrar kaydedeyim?"
                        return piper_dataset.redo_sentence(int(idx) - 1)
                    if action == "reset":
                        return piper_dataset.reset_dataset()
                    return "Eğitim seti komutunu anlamadım."
                r = await loop.run_in_executor(None, _pd)
                result = r

            elif name == "mic_test":
                from backend.stt_engine import mic_test
                r = await loop.run_in_executor(
                    None, lambda: mic_test(int(args.get("seconds", 3) or 3),
                                           on_log=self.ui.write_log))
                result = r

            elif name == "toggle_detection":
                want = str(args.get("action", "start")).lower() != "stop"
                try:
                    from app_config import save_app_config
                    save_app_config({"yolo_enabled": want})
                except Exception:
                    pass
                cam = getattr(self, "webcam", None)
                if cam is not None and hasattr(cam, "set_detection"):
                    result = cam.set_detection(want)
                else:
                    result = ("Nesne algılama " + ("açıldı" if want else "kapatıldı") + ".")

            elif name == "slideshow":
                r = await loop.run_in_executor(None, lambda: slideshow(str(args.get("action", ""))))
                result = r

            elif name == "slide_edit":
                r = await loop.run_in_executor(None, lambda: slide_edit(str(args.get("action", ""))))
                result = r

            elif name == "add_transition":
                r = await loop.run_in_executor(None, lambda: add_transition(
                    str(args.get("name", "rastgele")), bool(args.get("all_slides", True))))
                result = r

            elif name == "add_animation":
                r = await loop.run_in_executor(None, lambda: add_animation(
                    str(args.get("name", "solarak")), bool(args.get("all_slides", True))))
                result = r

            elif name == "clear_effects":
                r = await loop.run_in_executor(None, lambda: clear_effects(str(args.get("what", "all"))))
                result = r

            elif name == "write_topic":
                r = await loop.run_in_executor(None, lambda: write_topic(
                    str(args.get("topic", "")), str(args.get("target", "auto"))))
                result = r

            elif name == "image_adjust":
                r = await loop.run_in_executor(None, lambda: image_adjust(
                    str(args.get("action", "")), str(args.get("value", ""))))
                result = r

            elif name == "word_export_pdf":
                r = await loop.run_in_executor(None, lambda: word_export_pdf(str(args.get("name", ""))))
                result = r

            elif name == "excel_command":
                r = await loop.run_in_executor(None, lambda: excel_command(
                    str(args.get("action", "")), str(args.get("value", ""))))
                result = r

            elif name == "press_key":
                r = await loop.run_in_executor(None, lambda: press_key(
                    str(args.get("key", "")), int(args.get("times", 1) or 1)))
                result = r

            elif name == "save_blender_project":
                r = await loop.run_in_executor(
                    None, lambda: blender_bridge.save_blender_project(str(args.get("name", ""))))
                result = r

            elif name == "blender_scene":
                r = await loop.run_in_executor(
                    None, lambda: blender_bridge.scene_command(str(args.get("action", ""))))
                result = r

            elif name == "blender_exec":
                r = await loop.run_in_executor(
                    None, lambda: blender_bridge.send_code(str(args.get("code", ""))))
                result = r

            elif name == "save_freecad_project":
                r = await loop.run_in_executor(
                    None, lambda: freecad_bridge.save_freecad_project(str(args.get("name", ""))))
                result = r

            elif name == "freecad_scene":
                r = await loop.run_in_executor(
                    None, lambda: freecad_bridge.scene_command(str(args.get("action", ""))))
                result = r

            elif name == "freecad_exec":
                r = await loop.run_in_executor(
                    None, lambda: freecad_bridge.send_code(str(args.get("code", ""))))
                result = r

            elif name == "shutdown_assistant":
                result = shutdown_assistant(ui=self.ui)

            elif name == "type_text":
                r = await loop.run_in_executor(
                    None, lambda: type_text(args.get("text", "")))
                result = r or "Yazıldı."

            elif name == "save_python_file":
                r = await loop.run_in_executor(
                    None, lambda: save_python_file(
                        args.get("filename", ""), args.get("code", ""),
                        args.get("project_name", "")))
                result = r or "Dosya kaydedildi."

            else:
                result = f"Bilinmeyen araç: {name}"

        except Exception as e:
            result = f"Hata: {e}"
            had_exception = True
            traceback.print_exc()
            self.speak_error(name, e)

        tool_failed = self._result_looks_like_error(result)
        if tool_failed:
            if not had_exception:
                self.ui.set_state("ERROR")
        elif self._should_play_success_sfx(name, args, result):
            self.ui.play_success_sfx()

        if not tool_failed and not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[YERINDE] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(audio=msg)

    async def _stream_webcam_frames(self):
        """
        Webcam aktifken her 1.5s'de EN GÜNCEL kareyi session'a gönderir.
        Queue'suz 'latest frame' yaklaşımı: model hep şimdiki görüntüyü görür.
        """
        _last_sent: bytes | None = None
        while True:
            if self._garden_streamer.is_active:
                jpeg = self._garden_streamer.get_latest_frame()
            elif self._webcam_streamer.is_active:
                jpeg = self._webcam_streamer.get_latest_frame()
            else:
                await asyncio.sleep(0.2)
                continue

            if jpeg is None or jpeg is _last_sent:
                await asyncio.sleep(0.2)
                continue

            _last_sent = jpeg
            try:
                await self.session.send_realtime_input(
                    video={"data": jpeg, "mime_type": "image/jpeg"}
                )
            except Exception as e:
                print(f"[Webcam] Frame gönderilemedi: {e}")

            # 1.5 saniye bekle — model her zaman taze kare alır
            await asyncio.sleep(1.5)

    async def _update_ui_webcam_preview(self):
        """UI önizlemesini ~24 FPS günceller. AI akışından bağımsız."""
        frame_interval = 1.0 / 24.0   # ~0.0417 sn → 24 FPS
        while True:
            if self._garden_streamer.is_active:
                jpeg = self._garden_streamer.get_latest_frame()
                if jpeg:
                    self.ui.update_webcam_preview(jpeg)
            elif self._webcam_streamer.is_active:
                jpeg = self._webcam_streamer.get_latest_frame()
                if jpeg:
                    self.ui.update_webcam_preview(jpeg)
            await asyncio.sleep(frame_interval)

    async def _listen_audio(self):
        if pya is None:
            print("[YERINDE] 🎤 pyaudio yok — sesli mod pas geçiliyor")
            self.ui.write_log("SES: pyaudio yok, mikrofon kapalı")
            return
        print("[YERINDE] 🎤 Mikrofon başladı")
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS,
            rate=SEND_SAMPLE_RATE, input=True,
            frames_per_buffer=CHUNK_SIZE,
        )
        try:
            while True:
                data = await asyncio.to_thread(
                    stream.read, CHUNK_SIZE, exception_on_overflow=False)
                with self._speaking_lock:
                    yerinde_speaking = self._is_speaking
                if not yerinde_speaking and not self.ui.muted and not self._paused:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
        except Exception as e:
            print(f"[YERINDE] ❌ Mikrofon: {e}")
            raise
        finally:
            stream.close()

    async def _receive_audio(self):
        print("[YERINDE] 👂 Alım başladı")
        out_buf, in_buf = [], []
        output_noise = False
        output_noise_samples = []
        try:
            while True:
                async for response in self.session.receive():
                    if response.usage_metadata:
                        from core.token_usage import record_usage
                        record_usage(getattr(response.usage_metadata, "total_token_count", None))

                    if response.data:
                        self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            raw_txt = sc.output_transcription.text.strip()
                            if raw_txt:
                                txt, had_noise = self._clean_transcript_text(raw_txt)
                                if had_noise:
                                    output_noise = True
                                    if len(output_noise_samples) < 4:
                                        output_noise_samples.append(raw_txt)
                                if txt:
                                    out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self.ui.mark_user_activity(True)

                        if sc.turn_complete:
                            # Sentinel: ses kuyrugundaki tum chunk'lar calindiktan
                            # sonra SPEAKING -> LISTENING gecisi yapilsin (yanki onlenir).
                            self.audio_in_queue.put_nowait(None)

                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"Siz: {full_in}")
                            in_buf = []

                            full_out = " ".join(out_buf).strip()

                            # Eğitim verisi: sesli giriş yoksa (yazıyla gönderilmişse)
                            # son yazılı komutu kullan; bir kez kullanınca temizle.
                            _instr = full_in or self._last_typed_text
                            self._last_typed_text = ""
                            if _instr and full_out:
                                self._habits.record(
                                    "chat", _instr, response=full_out,
                                    source="gemini_live",
                                )

                            if full_out:
                                self.ui.write_log(f"YERINDE: {full_out}")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Kısmen filtrelenen ses transcripti: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                            elif output_noise:
                                self.ui.write_log("ERR: YERINDE sesli yanıtını çözümlerken bir hata oluştu.")
                                if output_noise_samples:
                                    self.ui.write_debug(
                                        "Filtrelenen ham transcript: " + " | ".join(output_noise_samples),
                                        level="WARN",
                                    )
                                self.ui.set_state("ERROR")
                            out_buf = []
                            output_noise = False
                            output_noise_samples = []

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[YERINDE] 📞 {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self._send_tool_responses(fn_responses)

        except Exception as e:
            print(f"[YERINDE] ❌ Alım: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[YERINDE] 🔊 Ses çalma başladı")
        stream = None
        proc = None
        upsampled = False
        try:
            dev = pya.get_default_output_device_info()
            self.ui.write_debug(
                f"SES: çıkış cihazı={dev.get('name', '?')} "
                f"({dev.get('defaultSampleRate', '?')} Hz)"
            )
        except Exception as e:
            self.ui.write_debug(f"SES: çıkış cihazı okunamadı ({e})", level="WARN")
        try:
            # Yol 1: 24kHz pyaudio (varsayılan)
            # final33 §4: ÇIKIŞ stream KESİN — rate=24000, channels=1,
            # paInt16, frames_per_buffer=4096 (GİRİŞ mikrofon 16000 kalır).
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT, channels=CHANNELS,
                rate=RECV_SAMPLE_RATE, output=True,
                frames_per_buffer=4096,
            )
            self.ui.write_debug("SES: yol=1 pyaudio 24kHz (buffer=4096)")
        except Exception as e1:
            self.ui.write_debug(f"SES: 24kHz açılamadı ({e1})", level="WARN")
            try:
                # Yol 2: 48kHz pyaudio + 2x numpy örnekleme
                stream = await asyncio.to_thread(
                    pya.open,
                    format=FORMAT, channels=CHANNELS,
                    rate=RECV_SAMPLE_RATE * 2, output=True,
                    frames_per_buffer=4096,
                )
                upsampled = True
                self.ui.write_debug("SES: yol=2 pyaudio 48kHz (2x upsample, buffer=4096)")
            except Exception as e2:
                self.ui.write_debug(f"SES: 48kHz de açılamadı ({e2})", level="WARN")
                # Yol 3: aplay subprocess yedeği
                try:
                    proc = subprocess.Popen(
                        ["aplay", "-q", "-f", "S16_LE", "-r", "24000", "-c", "1"],
                        stdin=subprocess.PIPE,
                    )
                    self.ui.write_debug("SES: yol=3 aplay 24kHz")
                except Exception as e3:
                    self.ui.write_debug(f"SES: aplay de açılamadı ({e3})", level="ERROR")
        if stream is None and proc is None:
            raise RuntimeError("Hiçbir ses çıkış yolu açılamadı")
        try:
            while True:
                # final33 §4 UNDERRUN: kuyruk ~100ms boşsa dijital sessizlik
                # yaz — PortAudio tamponu boşalıp çıtlama/kopma olmasın.
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(), timeout=0.1)
                except asyncio.TimeoutError:
                    with self._speaking_lock:
                        speaking_now = self._is_speaking
                    if speaking_now:
                        silence = b"\x00" * 4096
                        if upsampled:
                            silence = np.repeat(
                                np.frombuffer(silence, np.int16), 2).tobytes()
                        if stream is not None:
                            await asyncio.to_thread(stream.write, silence)
                        elif proc is not None:
                            await asyncio.to_thread(proc.stdin.write, silence)
                    continue
                if chunk is None:
                    # turn_complete sentinel — tum ses calindi, dinlemeye gec
                    self.set_speaking(False)
                    continue
                self.set_speaking(True)
                if upsampled:
                    chunk = np.repeat(np.frombuffer(chunk, np.int16), 2).tobytes()
                if stream is not None:
                    await asyncio.to_thread(stream.write, chunk)
                else:
                    await asyncio.to_thread(proc.stdin.write, chunk)
        except Exception as e:
            print(f"[YERINDE] ❌ Ses: {e}")
            raise
        finally:
            self.set_speaking(False)
            if stream is not None:
                stream.close()
            elif proc is not None:
                try:
                    proc.stdin.close()
                    proc.wait()
                except Exception:
                    pass

    async def run(self):
        connect_attempts = 0
        while True:
            # Duraklatılmışsa bağlanma, bekle
            if self._paused:
                await asyncio.sleep(1)
                continue

            try:
                # Client'ı her bağlanışta yeniden oluştur ve anahtarı tazeden oku.
                # Böylece yeni girilen API anahtarı anında geçerli olur; ilk
                # deneme başarısız olsa bile otomatik tekrar (3sn) kendini onarır.
                client = genai.Client(
                    api_key=get_api_key(),
                    http_options={"api_version": "v1alpha"}
                )
                print("[YERINDE] 🔌 Bağlanıyor...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=get_live_model(), config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=10)

                    print("[YERINDE] ✅ Bağlandı.")
                    connect_attempts = 0          # başarılı bağlantı → sayaç sıfırla
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: YERINDE hazır. Dinliyorum...")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._stream_webcam_frames())
                    tg.create_task(self._update_ui_webcam_preview())

            except Exception as e:
                print(f"[YERINDE] ⚠️ {e}")
                traceback.print_exc()
                self.set_speaking(False)
                # Webcam akışını durdur — yeni session'da yeniden başlayacak
                if self._webcam_streamer.is_active:
                    self._webcam_streamer.stop()
                    self.ui.set_webcam_active(False)
                if self._garden_streamer.is_active:
                    self._garden_streamer.stop()
                    self.ui.set_garden_active(False)

                connect_attempts += 1
                kind, message, transient = _classify_connect_error(e)

                # Kalıcı hatalar (geçersiz anahtar, hatalı ses ayarı): hemen söyle.
                if not transient:
                    self.ui.write_log(f"ERR: {message}")
                    self.ui.set_state("ERROR")
                    await asyncio.sleep(8)
                    continue

                # Geçici hatalar (ağ/zaman aşımı/kota): sessizce, artan aralıklarla
                # yeniden dene. Kullanıcıyı yalnızca 3. denemeden sonra bilgilendir
                # ve o zaman bile "yeniden deniyorum" de — yanlış yere yönlendirme.
                delay = min(2 * (2 ** (connect_attempts - 1)), 20)   # 2,4,8,16,20...
                if connect_attempts <= 2:
                    self.ui.set_state("INITIALISING")
                    print(f"[YERINDE] 🔄 Yeniden bağlanıyor ({connect_attempts}) — {kind}")
                elif connect_attempts == 3:
                    self.ui.set_state("INITIALISING")
                    self.ui.write_log(f"SYS: {message}")
                else:
                    self.ui.set_state("INITIALISING")
                    if connect_attempts % 5 == 0:      # her 5 denemede bir hatırlat
                        self.ui.write_log(
                            f"SYS: Bağlantı hâlâ kurulamadı ({kind}). "
                            f"{delay} saniyede tekrar deneyeceğim.")
                print(f"[YERINDE] 🔄 {delay} sn sonra tekrar ({connect_attempts}. deneme)")
                await asyncio.sleep(delay)


def _harden_native_libs():
    """torch (coqui-tts) + OpenCV + Tkinter aynı süreçte OpenMP'yi iki kez yükleyince
    Linux'ta SIGSEGV oluyor ('ultralytics/coqui-tts kurunca çöküyor' sorunu)."""
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    try:
        import cv2
        cv2.setNumThreads(0)
    except Exception:
        pass


def _enable_crash_log():
    """
    Ani kapanmaların (segfault dahil) izini bırak: ~/.yerinde/cokme.log
    Böylece bir daha çökerse sebebi elimizde olur.
    """
    try:
        import faulthandler
        from pathlib import Path as _P
        d = _P.home() / ".yerinde"
        d.mkdir(parents=True, exist_ok=True)
        f = open(d / "cokme.log", "a", buffering=1)
        faulthandler.enable(file=f, all_threads=True)

        import threading as _th
        import traceback as _tb

        def _thread_hook(args):
            _tb.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=f)
        _th.excepthook = _thread_hook

        def _hook(exc_type, exc, tb):
            _tb.print_exception(exc_type, exc, tb, file=f)
            _tb.print_exception(exc_type, exc, tb)
        sys.excepthook = _hook
    except Exception:
        pass


def main():
    _harden_native_libs()
    _enable_crash_log()

    # 3B Tasarım Stüdyosu / Robot Tasarım Atölyesi canlı komut köprüsünü
    # YERİNDE başlar başlamaz aç. Böylece bu araçlardan biri ÖNCEDEN açık
    # kalmışsa (örn. YERİNDE çöküp yeniden başladıysa, ya da kullanıcı
    # YERİNDE'yi kapatıp tekrar açtıysa), sayfa kendi yeniden bağlanma
    # döngüsüyle birkaç saniye içinde otomatik bağlanır — kullanıcının
    # tekrar "aç" demesi gerekmez. ensure_started()/register_trigger()
    # zaten güvenli şekilde birden fazla çağrılabilir (tek seferlik etki).
    try:
        from core import bridge_server as _tasarim_bridge
        from actions.tasarim_studyosu import _handle_export_trigger as _tasarim_export_trigger
        _tasarim_bridge.ensure_started()
        _tasarim_bridge.register_trigger("blender_export_trigger", _tasarim_export_trigger)
        from actions.kukla_kodlama import (
            _handle_project_export_trigger as _kukla_export_trigger,
            _handle_list_projects_trigger as _kukla_list_trigger,
            _handle_load_specific_project_trigger as _kukla_load_trigger,
        )
        _tasarim_bridge.register_trigger("project_export_trigger", _kukla_export_trigger)
        _tasarim_bridge.register_trigger("list_projects_trigger", _kukla_list_trigger)
        _tasarim_bridge.register_trigger("load_specific_project_trigger", _kukla_load_trigger)
        # Pico Devre Atölyesi de AYNI paylaşılan köprüyü kullanır - bu araç
        # kendi başına bir spontane tetikleyici (register_trigger) kaydetmez,
        # ama ensure_started() zaten çağrılmış olduğundan tarayıcıda ELLE
        # açılmış bir Pico sekmesi de YERİNDE başlar başlamaz bağlanabilir
        # (diğer üç araçla birebir aynı davranış).
    except Exception as _e:
        print(f"[YERINDE] Tasarım köprüsü başlatılamadı: {_e}")

    if os.environ.get("TERM_PROGRAM") == "vscode":
        print("[YERINDE] VS Code icinden baslatildi.")

    ui = YerindeUI()
    provider = str(get_app_config_value("model_provider", MOD_VARSAYILAN) or MOD_VARSAYILAN).lower()

    try:
        from core import remote_server
        remote_server.ensure_started(ui)
    except Exception as _e:
        print(f"[YERINDE] Uzaktan erişim sunucusu başlatılamadı: {_e}")

    def runner():
        if provider == "ollama":
            use_v3 = bool(get_app_config_value("v3_core_enabled", True))
            if not use_v3:
                print("[YERINDE] 📴 Çevrimdışı mod (V2 klasik çekirdek)...")
                try:
                    from ollama_assistant import OllamaAssistant
                    OllamaAssistant(ui).run()
                except Exception as e:
                    import traceback; traceback.print_exc()
                    ui.write_log(f"ERR: Çevrimdışı mod başlatılamadı — {e}")
                return

            print("[YERINDE] 📴 Çevrimdışı mod (V3 çekirdek) başlatılıyor...")
            try:
                import time as _t
                from core.offline_core import start_offline_core
                controller = start_offline_core(ui)   # bloklamaz
                # Çekirdek kendi thread'lerinde yaşar; bu runner thread'i
                # yalnızca yaşam döngüsünü bekler.
                while getattr(controller, "_running", True):
                    _t.sleep(0.5)
            except KeyboardInterrupt:
                print("\n🔴 Kapatılıyor...")
            except Exception as e:
                import traceback
                traceback.print_exc()
                ui.write_log(f"ERR: Çevrimdışı mod başlatılamadı — {e}")
                try:
                    ui.set_state("ERROR")
                except Exception:
                    pass
            return

        ui.wait_for_api_key()
        yerinde = YerindeLive(ui)
        try:
            asyncio.run(yerinde.run())
        except KeyboardInterrupt:
            print("\n🔴 Kapatılıyor...")

    threading.Thread(target=runner, daemon=True).start()

    # Çift alkış ile uyandırma (Windows bonus): pencereyi öne getirir. Çevresel
    # ses veya YERINDE'nin kendi sesi mikrofona girince yanlış tetiklenip pencereyi
    # sürekli öne çıkarabildiği için varsayılan KAPALI. İstersen True yap.
    ENABLE_CLAP_WAKE = False
    if ENABLE_CLAP_WAKE and WakeGestureListener is not None:
        try:
            wake_listener = WakeGestureListener(on_wake=ui.wake_up)
            wake_listener.start()
        except Exception as exc:
            print(f"[Wake] Alkış dinleyici başlatılamadı: {exc}")

    ui.root.mainloop()


if __name__ == "__main__":
    main()
