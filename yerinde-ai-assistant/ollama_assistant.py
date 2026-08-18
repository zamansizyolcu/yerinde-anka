#!/usr/bin/env python3
"""
YERINDE — Çevrimdışı (Ollama) mod çekirdeği.

İnternet KAPALIYKEN bile tamamen yerelde çalışan bir konuşma döngüsü sağlar:
  1) Mikrofon → Whisper (öncelikli) ya da Vosk (yedek) → metin  [actions/offline_stt.py]
  2) Metin + araç tanımları → yerel Ollama sunucusu (http://localhost:11434)
  3) Ollama araç çağırırsa ToolExecutor ile çalıştırılır, sonuç modele geri verilir
  4) Nihai metin yanıtı → Piper (öncelikli, doğal Türkçe ses) ya da sistem TTS'i
     (yedek)  [actions/offline_tts.py]

Gerekenler:
  - Ollama kurulu ve `ollama serve` ile çalışıyor olmalı
  - Ayarlar panelinden seçilen model `ollama pull <model>` ile indirilmiş olmalı
  - STT için: pip install faster-whisper (önerilir) veya pip install vosk sounddevice
  - TTS için: Piper kuruluysa otomatik kullanılır, değilse sistemin yerel
    TTS'ine (Windows: SAPI / Linux: espeak-ng) otomatik düşer
"""

from __future__ import annotations

import datetime
import json
import threading
import time

import requests

from app_config import get_app_config_value, ollama_think_value
from core.tool_executor import ToolExecutor
from tool_defs import get_ollama_tools
from actions.offline_stt import listen_and_transcribe, OfflineSTTError
from actions.offline_tts import speak_text_offline
from actions import media_capture
from memory.memory_manager import load_memory, format_memory_for_prompt

BASE_DIR_PROMPT = "core/prompt.txt"


class OllamaChatError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"Ollama {status}: {message}")


def load_system_prompt() -> str:
    try:
        with open(BASE_DIR_PROMPT, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return (
            "Sen YERINDE'sin — çevrimdışı çalışan kişisel AI asistanı. "
            "Türkçe konuş. Kısa ve net yanıtlar ver. "
            "Araçları kullanarak görevleri tamamla, asla taklit etme."
        )


class OllamaAssistant:
    """Gemini yerine yerel bir Ollama modeliyle konuşan çevrimdışı çekirdek."""

    def __init__(self, ui):
        self.ui = ui
        # Paylaşımlı kamera akışı: hem sesli "kamerayı aç" komutu hem de
        # arayüzdeki KAMERA düğmesi aynı akışı kontrol eder; görüntü Gemini
        # modundaki gibi animasyonun üstünde, uygulama içinde gösterilir.
        from actions.webcam_stream import WebcamStreamer
        self._webcam_streamer = WebcamStreamer()

        # Bahçe (Yoosee/DVRIP) kamerası — paylaşımlı akış, UI önizlemesi.
        from backend.ip_camera import GardenCamStreamer
        self._garden_streamer = GardenCamStreamer(
            on_log=lambda m: self.ui.write_log(m),
            on_state_change=self._on_garden_state_change,
            on_tool_state=self._on_garden_tool_state)
        self.tools = ToolExecutor(webcam=self._webcam_streamer,
                                  garden=self._garden_streamer, ui=ui)
        self._paused = False
        self._running = False
        self.messages: list[dict] = []
        self._tools_supported = None  # None = henüz denenmedi, True/False = biliniyor
        self._stop_requested = False

        self.ui.on_pause_toggle = self._on_pause_toggle
        self.ui.on_text_command = self._on_text_command
        self.ui.on_stop_speaking = self._on_stop_speaking
        self.ui.on_webcam_toggle = self._on_webcam_toggle_ui
        self.ui.on_camera_photo = lambda: media_capture.take_photo(self._camera_capture_source())
        self.ui.on_camera_record_toggle = lambda starting: (
            media_capture.recorder.start(self._camera_capture_source()) if starting
            else media_capture.recorder.stop())
        self.ui.on_camera_pause_toggle = lambda pausing: (
            media_capture.recorder.pause() if pausing
            else media_capture.recorder.resume())

        self.ui.on_garden_toggle = self._on_garden_toggle_ui
        self.ui.on_garden_wake = self._on_garden_wake
        self.ui.on_garden_ptz = self._on_garden_ptz
        self.ui.on_garden_ptz_start = self._on_garden_ptz_start
        self.ui.on_garden_ptz_stop = self._on_garden_ptz_stop
        self.ui.on_garden_horn = self._on_garden_horn
        self.ui.on_garden_talk = self._on_garden_talk

        threading.Thread(target=self._webcam_preview_loop, daemon=True).start()

    def _camera_capture_source(self):
        """FOTO/VİDEO/DURAKLAT düğmeleri ve 'fotoğraf çek'/'video kaydet'
        sesli komutları için: o an hangi kamera akışı canlıysa (bahçe
        kamerası ya da webcam) onu döndürür."""
        if self._garden_streamer.is_active:
            return self._garden_streamer
        return self._webcam_streamer

    def _on_webcam_toggle_ui(self, activate: bool):
        """Arayüzdeki KAMERA düğmesi (veya F6) — çevrimdışı modda da çalışır."""
        if activate:
            status = self._webcam_streamer.start()
            ok = status in ("ok", "already_active")
            self.ui.set_webcam_active(ok)
            if not ok:
                err = self._webcam_streamer.last_error or "bilinmeyen hata"
                self.ui.write_log(f"ERR: Kamera açılamadı — {err}")
        else:
            self._webcam_streamer.stop()
            self.ui.set_webcam_active(False)

    def _webcam_preview_loop(self):
        """Kamera aktifken arayüz önizlemesini ~24 FPS günceller."""
        frame_interval = 1.0 / 24.0
        while True:
            try:
                if self._webcam_streamer.is_active:
                    jpeg = self._webcam_streamer.get_latest_frame()
                    if jpeg:
                        self.ui.update_webcam_preview(jpeg)
                elif self._garden_streamer.is_active:
                    jpeg = self._garden_streamer.get_latest_frame()
                    if jpeg:
                        self.ui.update_webcam_preview(jpeg)
            except Exception:
                pass
            time.sleep(frame_interval)

    def _on_garden_toggle_ui(self, activate: bool):
        """Arayüzdeki BAHÇE KAMERA düğmesi — webcam'den bağımsız çalışır."""
        if activate:
            status = self._garden_streamer.start()
            self.ui.set_garden_active(status in ("ok", "already_active"))
            if status not in ("ok", "already_active"):
                err = getattr(self._garden_streamer, "last_error", None) or status
                self.ui.write_log(f"ERR: Bahçe kamerası açılamadı — {err}")
        else:
            self._garden_streamer.stop()
            self.ui.set_garden_active(False)

    def _on_garden_state_change(self, streaming: bool):
        """Kamera kendi kendine akışı kesti/geri getirdi — düğmeyi güncelle."""
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
        return self._garden_streamer.wake()

    def _on_garden_ptz(self, direction: str) -> str:
        return self._garden_streamer.ptz(direction)

    def _on_garden_ptz_start(self, direction: str) -> str:
        return self._garden_streamer.ptz_start(direction)

    def _on_garden_ptz_stop(self) -> str:
        return self._garden_streamer.ptz_stop()

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

    def _on_pause_toggle(self, paused: bool):
        self._paused = paused

    def _on_stop_speaking(self):
        """'DUR' düğmesi: düşünmeyi/konuşmayı anında keser."""
        self._stop_requested = True
        try:
            from actions.offline_tts import stop_speaking
            stop_speaking()
        except Exception:
            pass
        self.ui.write_log("SYS: Konuşma durduruldu.")
        self.ui.set_state("LISTENING")

    def _host(self) -> str:
        return str(get_app_config_value("ollama_host", "http://localhost:11434") or "http://localhost:11434").rstrip("/")

    def _model(self) -> str:
        return str(get_app_config_value("ollama_model", "llama3.1") or "llama3.1")

    def _build_system_prompt(self) -> str:
        memory = load_memory()
        mem_str = format_memory_for_prompt(memory)
        sys_p = load_system_prompt()
        now = datetime.datetime.now()
        time_ctx = f"[ŞU ANKİ ZAMAN]\n{now.strftime('%A, %d %B %Y — %H:%M')}\n\n"
        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str + "\n\n")
        parts.append(sys_p)
        parts.append(
            "\n\nNOT: Şu anda ÇEVRİMDIŞI (yerel Ollama) moddasın. Kamerayı açıp "
            "kapatabilir, fotoğraf çekip video kaydedebilirsin (take_photo, "
            "record_video, toggle_webcam) — ama çektiğin fotoğraf/videonun içeriğini "
            "YORUMLAYAMAZSIN (görüntü analizi ve ekran analizi bu modda yok, bunlar "
            "için Gemini moduna geçmek gerekir).\n\n"
            "ÇOK ÖNEMLİ: Kullanıcı 'X'i aç', 'X'i kapat', 'fotoğraf çek', 'kamerayı aç' "
            "gibi bir EYLEM istediğinde, SADECE konuşarak 'açıyorum', 'tamam' gibi cevap "
            "VERME — mutlaka ilgili aracı (open_app, close_app, take_photo, "
            "record_video, toggle_webcam vb.) GERÇEKTEN ÇAĞIR. Bir eylemi sözle kabul "
            "edip aracı çağırmadan geçmek YASAK; kullanıcı bunu fark eder ve hiçbir şey "
            "olmamış olur. Emin değilsen bile önce aracı dene, sonra sonucu anlat."
        )
        return "\n".join(parts)

    def _trim_history(self, max_messages: int = 16):
        """
        self.messages sohbet boyunca sınırsız büyür — uzun bir oturumda her
        tur, gitgide büyüyen bu geçmişin TAMAMINI yeniden Ollama'ya
        gönderir (ve modele yeniden işletir), bu da oturum uzadıkça
        yanıtların gitgide yavaşlamasına yol açar. Sistem mesajını daima
        koru, geri kalanında sadece son `max_messages` mesajı tut.
        """
        if len(self.messages) <= max_messages + 1:
            return
        system_msg = self.messages[0]
        tail = self.messages[-max_messages:]
        # Bir "tool" mesajıyla başlamak modele bağlamsız bir sonuç gibi
        # görünür; öyleyse kesim noktasını en yakın user/assistant mesajına
        # kaydır.
        while tail and tail[0].get("role") == "tool":
            tail.pop(0)
        self.messages = [system_msg] + tail

    def _on_text_command(self, text: str):
        if self._paused or not text.strip():
            return
        self.ui.write_log(f"Siz: {text}")
        threading.Thread(target=self._handle_turn, args=(text,), daemon=True).start()

    def _chat(self, messages: list[dict], use_tools: bool = True) -> dict:
        payload = {
            "model": self._model(),
            "messages": messages,
            "stream": False,
            # Ollama'nın varsayılan bağlam penceresi (genelde 2048 token) bizim
            # sistem promptu + araç şeması + hafıza ile birlikte kolayca
            # dolup taşabilir — bu da modelin araç çağırmayı 'unutmasına' ya da
            # sadece sohbet etmesine yol açabilir. Daha geniş bir pencere isteriz.
            # NOT: tool_defs.get_ollama_tools() artık sadece ~29 çekirdek aracı
            # gönderiyor (önceden ~165 aracın TAMAMI gönderiliyordu, bu da
            # başlı başına ~30.000 token'lık gereksiz bir prompt anlamına
            # geliyordu — küçük modellerde asıl yavaşlığın kaynağı buydu).
            "options": {
                "num_ctx": int(get_app_config_value("ollama_num_ctx", 8192) or 8192),
                # Küçük modeller bazen tekrar döngüsüne girip gereğinden uzun
                # yanıt üretebiliyor; bu da "yanıt geldi ama çok geç geldi"
                # hissi yaratıyor. Makul bir tavan koyuyoruz.
                "num_predict": int(get_app_config_value("ollama_num_predict", 512) or 512),
            },
            # Modeli istekler arasında bellekte tut — her komutta modelin diskten
            # yeniden yüklenmesini (saniyeler süren gecikmeyi) önler.
            "keep_alive": "30m",
            # AYARLAR > "DÜŞÜNME HIZI" (fast/normal/deep) burada Ollama'nın
            # top-level 'think' alanına çevrilir. Yalnızca gerçekten düşünme
            # destekleyen modellerde (qwen3, deepseek-r1, gpt-oss...) etkilidir;
            # gemma2/llama3.1 gibi desteklemeyenlerde zararsızca yok sayılır.
            # Bazı modeller beklenmeyen bir 'think' türünü (ör. bool bekleyen
            # bir modele seviye string'i) 400 ile reddedebilir — bu durumda
            # _post_chat() alanı kaldırıp SESSİZCE tekrar dener.
            "think": ollama_think_value(),
        }
        if use_tools:
            payload["tools"] = get_ollama_tools()

        return self._post_chat(payload)

    def _post_chat(self, payload: dict) -> dict:
        resp = requests.post(f"{self._host()}/api/chat", json=payload, timeout=120)

        if resp.status_code >= 400:
            try:
                err_msg = resp.json().get("error", resp.text)
            except Exception:
                err_msg = resp.text

            # Model 'think' alanını hiç tanımıyor ya da farklı bir tür
            # bekliyor ("invalid think value: ..." gibi) — bu durumda
            # alanı TAMAMEN kaldırıp bir kez daha dene; kullanıcı bunu asla
            # hata olarak görmesin, model kendi varsayılan davranışına düşsün.
            if "think" in payload and "think" in err_msg.lower():
                retry_payload = {k: v for k, v in payload.items() if k != "think"}
                resp2 = requests.post(f"{self._host()}/api/chat", json=retry_payload, timeout=120)
                if resp2.status_code < 400:
                    return resp2.json()

            raise OllamaChatError(resp.status_code, err_msg)

        return resp.json()

    def _chat_with_fallback(self, messages: list[dict]) -> dict:
        """
        Önce araç (tool) tanımlarıyla dener. Model tool-calling desteklemiyorsa
        Ollama 400 döner — bu durumda otomatik olarak araçsız (düz sohbet)
        moda düşer, böylece en azından konuşma çalışmaya devam eder.
        """
        if self._tools_supported is not False:
            try:
                data = self._chat(messages, use_tools=True)
                self._tools_supported = True
                return data
            except OllamaChatError as e:
                is_tool_incompat = e.status == 400 and any(
                    kw in e.message.lower() for kw in ("tool", "function")
                )
                if is_tool_incompat:
                    self._tools_supported = False
                    self.ui.write_log(
                        f"UYARI: '{self._model()}' modeli araç (tool) çağırmayı desteklemiyor "
                        f"({e.message}). Uygulama açma/kapatma gibi özellikler bu modelle "
                        "çalışmaz — düz sohbete geçiliyor. Tool-calling destekleyen bir model "
                        "için: llama3.1, qwen2.5, mistral-nemo, firefunction-v2, command-r."
                    )
                elif e.status == 400:
                    # Araç desteğiyle ilgisiz, tek seferlik bir 400 olabilir — kalıcı olarak
                    # devre dışı bırakma, sadece bu turu araçsız dene.
                    self.ui.write_log(f"UYARI: Ollama isteği reddetti ({e.message}) — bu tur araçsız deneniyor.")
                else:
                    raise
        return self._chat(messages, use_tools=False)

    def _handle_turn(self, user_text: str):
        # ── Deterministik niyet algılama ─────────────────────────────────────
        # "Blender'ı aç", "kamerayı aç", "fotoğraf çek", "yaz ..." gibi NET
        # komutları LLM'e hiç sormadan doğrudan çalıştır. Küçük yerel modeller
        # bazen aracı çağırmak yerine sadece "açıyorum" deyip geçebiliyor —
        # bu yol o güvenilmezliği tamamen ortadan kaldırır.
        try:
            from core.intent_parser import detect_intent, get_last_correction
            intent = detect_intent(user_text)
            corr = get_last_correction()
            if corr:
                self.ui.write_log(
                    f"SYS: 🔤 sesi şöyle anladım: \"{corr['corrected']}\" "
                    f"(duyulan: \"{corr['original']}\")")
        except Exception:
            intent = None

        if intent is not None:
            tool_name, tool_args = intent
            self.ui.set_state("THINKING")
            self.ui.write_log(f"SYS: 🔧 Araç çağrıldı → {tool_name}({tool_args})")
            try:
                result = self.tools.execute(tool_name, tool_args)
            except Exception as e:
                result = f"Hata: {e}"
            result_text = str(result).strip() or "Tamamlandı."
            self.ui.write_log(f"YERINDE: {result_text}")
            self.ui.set_state("SPEAKING")
            speak_text_offline(
                result_text,
                on_done=lambda: self.ui.set_state("LISTENING"),
                blocking=True,
                log_fn=self.ui.write_log,
            )
            return

        self.ui.set_state("THINKING")
        self._stop_requested = False
        if not self.messages:
            self.messages.append({"role": "system", "content": self._build_system_prompt()})
        self.messages.append({"role": "user", "content": user_text})
        self._trim_history()

        try:
            for _ in range(4):  # ardışık en fazla 4 araç çağrısı zincirine izin ver
                if self._stop_requested:
                    self.ui.set_state("LISTENING")
                    return

                data = self._chat_with_fallback(self.messages)
                msg = data.get("message", {})
                tool_calls = msg.get("tool_calls") or []

                if self._stop_requested:
                    self.ui.set_state("LISTENING")
                    return

                if not tool_calls:
                    final_text = (msg.get("content") or "").strip()
                    self.messages.append({"role": "assistant", "content": final_text})
                    if final_text and not self._stop_requested:
                        self.ui.write_log(f"YERINDE: {final_text}")
                        self.ui.set_state("SPEAKING")
                        speak_text_offline(
                            final_text,
                            on_done=lambda: self.ui.set_state("LISTENING"),
                            blocking=True,
                            log_fn=self.ui.write_log,
                        )
                    else:
                        if final_text:
                            self.ui.write_log(f"YERINDE: {final_text}")
                        self.ui.set_state("LISTENING")
                    return

                self.messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": tool_calls})
                for call in tool_calls:
                    if self._stop_requested:
                        self.ui.set_state("LISTENING")
                        return
                    fn = call.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    print(f"[YERINDE/Ollama] 🔧 {name} {args}")
                    self.ui.write_log(f"SYS: 🔧 Araç çağrıldı → {name}({args})")
                    result = self.tools.execute(name, args)
                    self.messages.append({"role": "tool", "content": str(result)})

            self.ui.write_log("ERR: Araç çağrı zinciri çok uzadı, yanıt üretilemedi.")
            self.ui.set_state("ERROR")

        except requests.exceptions.ConnectionError:
            self.ui.write_log(
                "ERR: Ollama sunucusuna bağlanılamadı — 'ollama serve' çalışıyor mu kontrol et."
            )
            self.ui.set_state("ERROR")
        except Exception as e:
            self.ui.write_log(f"ERR: Ollama hatası — {e}")
            self.ui.set_state("ERROR")

    def _listen_loop(self):
        self.ui.write_log("SYS: YERINDE çevrimdışı modda hazır (Ollama). Dinliyorum...")
        while self._running:
            if self._paused or self.ui.muted:
                time.sleep(0.3)
                continue
            try:
                text = listen_and_transcribe()
            except OfflineSTTError as e:
                self.ui.write_log(f"ERR: {e}")
                self.ui.set_state("ERROR")
                time.sleep(3)
                continue
            except Exception as e:
                self.ui.write_debug(f"Mikrofon hatası: {e}", level="ERROR")
                time.sleep(1)
                continue

            if text:
                self.ui.write_log(f"Siz: {text}")
                self._handle_turn(text)

    def _diagnose_startup(self):
        """
        Çevrimdışı mod başlarken Ollama sunucusuna, STT ve TTS motorlarına
        hızlıca bakar ve eksik olanı NET bir şekilde loglar — böylece
        'ses çalışmıyor' durumunda kullanıcı neyin eksik olduğunu görür.
        """
        # 1) Ollama sunucusu ayakta mı?
        try:
            r = requests.get(f"{self._host()}/api/tags", timeout=3)
            r.raise_for_status()
            models = [m.get("name", "") for m in r.json().get("models", [])]
            if self._model() not in models and models:
                self.ui.write_log(
                    f"UYARI: Seçili model '{self._model()}' Ollama'da bulunamadı. "
                    f"Kurulu modeller: {', '.join(models)}. Ayarlar panelinden model seç."
                )
            elif not models:
                self.ui.write_log(
                    "UYARI: Ollama'da hiç model kurulu değil. Terminalde "
                    f"'ollama pull {self._model()}' çalıştır."
                )
        except requests.exceptions.ConnectionError:
            self.ui.write_log(
                "ERR: Ollama sunucusuna ulaşılamıyor. Bir terminalde 'ollama serve' "
                "çalıştır ve JARVIS'i yeniden başlat."
            )
        except Exception as e:
            self.ui.write_log(f"UYARI: Ollama sunucusu kontrol edilemedi — {e}")

        # 2) STT motoru kullanılabilir mi? (gerçek mikrofon açmadan, sadece import)
        stt_ok = False
        stt_problems = []
        try:
            import faster_whisper  # noqa: F401
            stt_ok = True
        except ImportError as e:
            stt_problems.append(f"faster-whisper yok ({e})")
        if not stt_ok:
            try:
                import vosk  # noqa: F401
                model_path = get_app_config_value("vosk_model_path", "vosk-model")
                from pathlib import Path
                if not Path(model_path).exists():
                    stt_problems.append(f"Vosk kurulu ama model klasörü yok: '{model_path}'")
                else:
                    stt_ok = True
            except ImportError as e:
                stt_problems.append(f"vosk yok ({e})")
        try:
            import sounddevice  # noqa: F401
        except ImportError as e:
            stt_ok = False
            stt_problems.append(f"sounddevice yok ({e}) — mikrofon açılamaz")

        if not stt_ok:
            self.ui.write_log(
                "ERR: Konuşma tanıma (STT) kullanılamıyor: " + "; ".join(stt_problems) +
                ". Kurulum: pip install faster-whisper sounddevice numpy "
                "(ya da: pip install vosk sounddevice + Türkçe Vosk modeli)."
            )
        else:
            self.ui.write_log("SYS: Konuşma tanıma (STT) hazır.")

        # 3) Seslendirme (TTS) kurulumu — aksanlı/yanlış ses çıkma sebebini önceden bildir
        try:
            from actions.offline_tts import diagnose_voice_setup
            voice_warning = diagnose_voice_setup()
            if voice_warning:
                self.ui.write_log(f"UYARI: {voice_warning}")
        except Exception:
            pass

    def _warmup(self):
        """
        İlk komuttaki uzun gecikmeyi önlemek için açılışta arka planda:
          1) Ollama modelini belleğe yükler (boş bir generate isteği)
          2) Whisper STT modelini önceden indirir/yükler
        Kullanıcı ilk konuştuğunda her şey hazır olur.
        """
        # 1) Ollama modelini ısıt
        try:
            requests.post(
                f"{self._host()}/api/generate",
                json={"model": self._model(), "prompt": "", "keep_alive": "30m"},
                timeout=180,
            )
            self.ui.write_log(f"SYS: '{self._model()}' modeli belleğe yüklendi, hazır.")
        except Exception:
            pass  # _diagnose_startup zaten bağlantı sorunlarını bildiriyor

        # 2) Whisper modelini önceden yükle
        try:
            from actions.offline_stt import preload_stt
            preload_stt()
            self.ui.write_log("SYS: Konuşma tanıma modeli önceden yüklendi.")
        except Exception:
            pass

    def run(self):
        self._running = True
        self._diagnose_startup()
        threading.Thread(target=self._warmup, daemon=True).start()
        self.ui.set_state("LISTENING")
        self._listen_loop()

    def stop(self):
        self._running = False
