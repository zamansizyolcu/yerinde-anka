"""
backend/system_controller.py — Sistemin kalbi.

Akış şeması:

  [Vosk Wake]──"yerinde"──▶ _on_wake ──▶ UI: "Dinliyor..."
        │                        │
        │ (pause)                ▼
        │              [Faster-Whisper STT] ──metin──▶ UI: "Siz: ..."
        │                        │
        │                        ▼
        │                 [ModelRouter.classify]  (Gemma 2)
        │                   │      │       │          │
        │                 chat   code    vision   camera_on/off
        │                   │      │       │          │
        │               Gemma2  Qwen-  Qwen2-VL   VisionEngine
        │                        Coder  (+YOLO      (YOLO11 canlı)
        │                        │       karesi)
        │                        ▼
        │                 [TTSManager.speak]  (Piper/ChatTTS/F5)
        │ (resume) ◀──────────── done
        ▼
   tekrar bekler

GUI entegrasyonu MIMARI_ENTEGRASYON.md içinde — özet:
  controller = SystemController(settings, callbacks); controller.start()
  KAMERA düğmesi  → controller.toggle_camera()
  DUR düğmesi     → controller.interrupt()
  GÖNDER kutusu   → controller.submit_text("...")
  Panel değişimi  → controller.settings.update_from_gui(...)
"""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from .bridge import AsyncioBridge, UICallbacks
from .config import Settings
from .habits import HabitLearner
from .model_router import ModelRouter
from .ollama_client import OllamaClient
from .stt_engine import FasterWhisperSTT
from .tts_manager import TTSManager
from .vision_engine import VisionEngine
from .wake_word import VoskWakeWord

_CHAT_SYSTEM = (
    "Sen YERINDE'sin — tamamen yerel çalışan Türkçe kişisel asistan. "
    "Kısa, doğal ve net konuş. Sesli okunacağın için madde işareti ve "
    "markdown kullanma."
)


class SystemController:
    """Tüm motorların sahibi ve tek yaşam-döngüsü noktası.

    V2 entegrasyon kancaları (opsiyonel — verilirse eski 25 araç aynen çalışır):
      tool_executor : core.tool_executor.ToolExecutor örneği
                      (open_app, get_weather, sys_info, take_photo, ...)
      intent_fn     : core.intent_parser.detect_intent
                      (net komutları LLM'e sormadan yakalar)
    """

    def __init__(self, settings: Settings, ui: UICallbacks,
                 tool_executor=None,
                 intent_fn: Optional[Callable] = None,
                 habits_path: str = "memory/habits.json"):
        self.s = settings
        self.ui = ui
        self.bridge = AsyncioBridge()
        self.tools = tool_executor
        self.intent_fn = intent_fn
        self.habits = HabitLearner(habits_path)

        self.client = OllamaClient(settings.ollama_host,
                                   num_ctx=settings.num_ctx,
                                   keep_alive=settings.keep_alive)
        self.router = ModelRouter(settings, self.client)
        self.stt = FasterWhisperSTT(settings.whisper_model_size, settings.stt_language)
        self.tts = TTSManager(settings, on_log=lambda m: ui.emit("on_log", m))
        self.vision = VisionEngine(
            settings,
            on_frame=lambda b: ui.emit("on_frame", b),
            on_state=lambda a: ui.emit("on_camera_state", a),
            on_log=lambda m: ui.emit("on_log", m),
        )
        self.wake = VoskWakeWord(settings.vosk_model_path, settings.wake_word,
                                 on_wake=self._on_wake_threadsafe,
                                 on_died=self._on_wake_died,
                                 on_text=self._on_vosk_text)
        self._busy = asyncio.Lock()
        self._running = True    # shutdown() False yapar; runner bekleme döngüsü buna bakar
        self._continuous_mode = False   # wake-word yoksa eski 'sürekli dinle' düzeni

    # ══ Yaşam döngüsü ═══════════════════════════════════════════════════════
    def start(self) -> None:
        """GUI açılışında bir kez çağır. Ana thread'i bloklamaz."""
        self.bridge.start()
        self.tts.start(self.bridge.loop)
        self.bridge.submit(self._startup())

    def shutdown(self) -> None:
        self._running = False
        self.wake.stop()
        self.vision.stop()
        self.tts.stop()
        self.bridge.stop()

    @staticmethod
    def _check_numpy() -> str | None:
        """
        İki AYRI numpy sorununu tespit eder:

        1) 'Unable to compare versions for numpy>=1.17 ... found=None' —
           numpy'nin sürüm bilgisi (dist-info) bozulmuş, genelde coqui-tts /
           ultralytics kurulumu SIRASINDA yarıda kalmış bir işlemden kaynaklanır.

        2) DAHA SİNSİ OLANI: coqui-tts kurulumu numpy'yi DÜŞÜRDÜĞÜNDE (ör.
           2.x → 1.26), daha önce numpy 2.x'e göre DERLENMİŞ paketler (cv2,
           torch, ultralytics) artık uyuşmuyor olabilir — "was compiled using
           NumPy 1.x" / "size changed" gibi ikili (ABI) uyumsuzluk hataları.
           Bu, numpy'nin kendisi bozuk olmasa bile ortaya çıkar; bu yüzden
           numpy'yi KULLANAN paketleri de gerçekten import ederek doğruluyoruz.
        """
        try:
            import numpy  # noqa: F401
        except Exception as e:
            return (f"NumPy yüklenemiyor ({e}). Çözüm: "
                    "pip install --force-reinstall --no-cache-dir \"numpy<2\"")
        try:
            from importlib.metadata import version
            v = version("numpy")
            if not v:
                raise ValueError("boş sürüm")
        except Exception:
            return ("NumPy kurulu ama sürüm bilgisi bozuk (bunu 'found=None' hatası "
                    "olarak görüyorsun). Çözüm — sanal ortam içindeyken:\n"
                    "   pip install --force-reinstall --no-cache-dir \"numpy<2\"")

        # ABI uyumsuzluğu taraması: numpy'yi kullanan her paketi TEK TEK
        # içe aktarmayı dene; hangisi patlarsa AÇIKÇA onu söyle (kör bir
        # "numpy bozuk" mesajı yerine tam olarak neyi yeniden kurman
        # gerektiğini biliriz).
        abi_hints = ("numpy.core.multiarray", "was compiled using numpy",
                     "size changed", "binary incompatibility", "numpy.dtype size",
                     "numpy._core")
        for pkg, hint in (("cv2", "opencv-python"), ("torch", "torch"),
                         ("ultralytics", "ultralytics")):
            try:
                __import__(pkg)
            except Exception as e:
                msg = str(e).lower()
                # Gerçekten kurulu değilse (ABI hatası DEĞİL) sessizce geç.
                if f"no module named '{pkg}" in msg or "no module named" in msg and pkg in msg:
                    continue
                if any(h in msg for h in abi_hints):
                    return (f"NumPy sürümü değişti (muhtemelen coqui-tts kurulumu "
                            f"numpy'yi düşürdü) ve '{pkg}' ({hint}) artık eski "
                            f"numpy ABI'sine göre derlenmiş durumda uyuşmuyor: {e}\n"
                            f"Çözüm — sanal ortam içindeyken:\n"
                            f"   pip install --force-reinstall --no-cache-dir {hint}")
                return f"'{pkg}' yüklenirken beklenmedik hata: {e}"
        return None

    async def _startup(self) -> None:
        self.ui.emit("on_state", "IDLE")
        self.ui.emit("on_log", "SYS: YERINDE çekirdeği başlatılıyor...")

        # Bozuk NumPy kurulumu tüm çevrimdışı modu düşürüyordu — önce teşhis et.
        numpy_problem = await self.bridge.to_thread(self._check_numpy)
        if numpy_problem:
            self.ui.emit("on_log", f"ERR: {numpy_problem}")

        # Modelleri ısıt + STT'yi önden yükle (ilk komut gecikmesi = 0).
        # Her biri AYRI korunur: biri patlarsa diğerleri çalışmaya devam eder.
        async def _safe(coro, ad):
            try:
                return await coro
            except Exception as e:
                self.ui.emit("on_log", f"UYARI: {ad} başlatılamadı — {e}")
                return None

        if self.s.intent_only:
            self.ui.emit("on_log", "SYS: SADECE KOMUT MODU açık — yapay zekâ "
                                   "kullanılmıyor, komutlar anında çalışır.")
            stt_ok = await _safe(self.bridge.to_thread(self.stt.preload),
                                 "Konuşma tanıma")
        else:
            # Hangi model hangi role atanmış — açıkça logla. "Küçük model
            # seçtim ama yine de bekliyorum" şikâyetlerinin en sık sebebi,
            # SOHBET (chat_model / classify) ve KOD (coder_model) modellerinin
            # AYRI iki ayar olması: kullanıcı küçük modeli sadece "Ollama kod
            # modeli" olarak seçip genel "Ollama modeli"ni değiştirmeden
            # bırakabiliyor — o zaman HER mesaj (kod olsun olmasın) hâlâ
            # ağır sohbet modeliyle sınıflandırılıp yanıtlanıyor.
            self.ui.emit(
                "on_log",
                f"SYS: 🧠 Aktif modeller — Sohbet/sınıflandırma: {self.s.chat_model} "
                f"| Kod: {self.s.coder_model} | Görü: {self.s.vision_model}")

            # Isıtma: sadece sohbet modeli değil, kod ve görü modelleri de
            # (farklıysa) önceden belleğe alınır — aksi halde bu modellerin
            # İLK kullanımı (bir kod isteği ya da kamera analizi) Ollama'nın
            # diskten model yükleme süresi kadar (zayıf donanımda onlarca
            # saniye) bekletir, model küçük olsa bile.
            warm_targets = {self.s.chat_model, self.s.coder_model, self.s.vision_model}
            warmups = [self.client.warmup(m) for m in warm_targets]
            results = await asyncio.gather(
                *[_safe(w, f"Ollama ({m})") for w, m in zip(warmups, warm_targets)],
                _safe(self.bridge.to_thread(self.stt.preload), "Konuşma tanıma"),
            )
            stt_ok = results[-1]
        if not stt_ok:
            self.ui.emit("on_log",
                         f"ERR: Konuşma tanıma başlatılamadı — {self.stt.last_error}. "
                         "Kur: pip install faster-whisper sounddevice numpy")
        else:
            try:
                from .audio_input import pick_input
                await self.bridge.to_thread(
                    pick_input, lambda m: self.ui.emit("on_log", m))
                self.ui.emit("on_log",
                             f"SYS: Konuşma tanıma hazır (Whisper-{self.s.whisper_model_size}).")
            except Exception as e:
                self.ui.emit("on_log", f"ERR: Mikrofon seçilemedi — {e}")

        # Ses kurulum teşhisi — 'seçtim ama aksanlı konuşuyor' durumunu
        # daha ilk saniyede açıklar:
        self._diagnose_voice()

        if not self.s.wake_enabled:
            await self._switch_to_continuous(
                "Uyandırma kelimesi AYARLARDAN kapalı")
        elif self.wake.start():
            self.ui.emit("on_log",
                         f"SYS: Hazır — '{self.s.wake_word.capitalize()}' diyerek beni uyandırabilirsin.")
        else:
            # Kararlılık yedeği: Vosk modeli yoksa asistan SAĞIR KALMAZ,
            # eski 'sürekli dinleme' düzenine döner (Pardus'ta sık senaryo).
            await self._switch_to_continuous(
                f"Wake-word kapalı ({self.wake.last_error})")
        await self.tts.speak("Sistem hazır.", kind="notify")

    def _diagnose_voice(self) -> None:
        import shutil as _sh
        from pathlib import Path as _P
        prof = (self.s.voice_profile or "auto").lower()
        piper_ok = bool(_sh.which(self.s.piper_binary) or _P(self.s.piper_binary).exists())
        if prof.startswith("piper:") or prof in ("auto", "piper"):
            if not piper_ok:
                self.ui.emit("on_log",
                    "UYARI: Piper kurulu değil — Türkçe doğal ses için "
                    "github.com/rhasspy/piper sürümlerinden indirip proje "
                    "içindeki 'piper' klasörüne koy (ses modeli voices/ içinde hazır). "
                    "Şimdilik sistem sesine düşülüyor; aksanlı çıkabilir.")
            elif not _P(self.s.piper_voice).exists():
                self.ui.emit("on_log",
                    f"UYARI: Piper ses modeli bulunamadı: {self.s.piper_voice}")

    async def _continuous_listen_loop(self) -> None:
        """Wake-word yoksa: sürekli dinle → çevir → işle (V2 davranışı)."""
        last_err = None
        while self._running:
            if self._busy.locked() or self.tts._queue.qsize() > 0:
                await asyncio.sleep(0.3)
                continue
            try:
                self.ui.emit("on_state", "LISTENING")
                # NOT: _wake_cycle() (tetik kelimeli yol) her denemeden önce
                # "Dinliyorum..." yazıyordu, bu sürekli-dinleme döngüsünde bu
                # satır hiç yoktu — kullanıcı konuştuğunda hiçbir onay
                # görmüyordu. Aynı bildirimi buraya da ekliyoruz.
                self.ui.emit("on_log", "SYS: Dinliyorum...")
                text = await self.bridge.to_thread(
                    self.stt.listen_and_transcribe, self.s.listen_timeout_s)
                last_err = None
            except Exception as e:
                if str(e) != last_err:          # aynı hatayı tekrar tekrar basma
                    last_err = str(e)
                    self.ui.emit("on_log", f"ERR: Mikrofon/STT — {e}")
                await asyncio.sleep(3)
                continue
            if text:
                self.ui.emit("on_user_text", text)
                await self._handle_request(text)
            elif getattr(type(self.stt), "_last_peak", 0) >= 0.008 and \
                    getattr(self.stt, "last_capture_sec", 0) <= 0.8:
                peak = type(self.stt)._last_peak
                th = type(self.stt)._last_threshold
                hint = (f"SYS: Ses seviyesi eşiğin altında kaldı (seviye {peak:.3f}, "
                        f"eşik {th:.3f}) — mikrofona yaklaş ya da Windows/sistem "
                        "ayarlarından mikrofon kazancını yükselt.")
                if getattr(self, "_last_hint", "") != hint:
                    self._last_hint = hint
                    self.ui.emit("on_log", hint)
            elif getattr(self.stt, "last_capture_sec", 0) > 0.8:
                # Ses GELDİ ama çözümlenemedi — kullanıcıya görünür teşhis
                self.ui.emit("on_log",
                             f"SYS: {self.stt.last_capture_sec:.1f} sn ses algılandı ama "
                             "söz çözümlenemedi (çok kısık/uzak olabilir — biraz daha "
                             "yüksek sesle ya da mikrofona yakın dene).")

    # ══ GUI'nin çağırdığı dış API ═══════════════════════════════════════════
    def submit_text(self, text: str) -> None:
        """Sağ paneldeki yazı kutusu / GÖNDER düğmesi."""
        self.bridge.submit(self._handle_request(text))

    def toggle_camera(self) -> None:
        """KAMERA düğmesi — sesli 'kamerayı aç' ile aynı motoru kullanır."""
        if self.vision.is_active:
            self.vision.stop()
            self.bridge.submit(self.tts.speak("Kamera kapatıldı.", kind="notify"))
        else:
            self.bridge.submit(self._camera_on())

    def toggle_detection(self, enabled: bool | None = None) -> str:
        """YOLO nesne algılamayı aç/kapat (düğme ve sesli komut buraya bağlı)."""
        new_val = (not self.s.yolo_enabled) if enabled is None else bool(enabled)
        return self.vision.set_detection(new_val)

    def interrupt(self) -> None:
        """DUR düğmesi — konuşmayı ve sırada bekleyenleri anında keser."""
        self.tts.stop()
        self.ui.emit("on_state", "IDLE")
        self.ui.emit("on_log", "SYS: Konuşma durduruldu.")

    # ══ Wake → dinle → yönlendir zinciri ════════════════════════════════════
    def _on_wake_threadsafe(self) -> None:
        # Vosk thread'inden gelir → asyncio dünyasına güvenli geçiş
        self.bridge.submit(self._wake_cycle())

    def _on_vosk_text(self, text: str) -> bool:
        """
        Wake-word motoru bir cümle duydu ama içinde 'yerinde' YOK.
        Doğrudan bir sistem komutuysa (sunum aç, kamerayı kapat, sesi kıs...)
        ANINDA çalıştır — kullanıcı her seferinde 'Yerinde' demek zorunda
        kalmasın. Komut değilse False dön (sohbet için tetik kelime beklenir).
        """
        if not self.intent_fn or not self.tools:
            return False
        try:
            if self.intent_fn(text) is None:
                return False
        except Exception:
            return False
        self.ui.emit("on_user_text", text)
        # KRİTİK DÜZELTME: komut çalışırken (ve TTS onayı konuşurken)
        # mikrofonu duraklatıyoruz — yoksa Vosk sürekli dinlemeye devam
        # ediyor, hoparlörden gelen KENDİ TTS onayını ("Boş belge açıldı...")
        # duyup komutu İKİNCİ KEZ tetikleyebiliyordu. Bu, Office
        # uygulamalarının 'ikişer açılması' şikayetinin kök nedeniydi —
        # wake_cycle'da (tetik kelimeli yol) bu koruma zaten vardı, burada
        # (hızlı/tetiksiz yol) hiç yoktu.
        self.wake.pause()
        self.bridge.submit(self._run_fastpath_then_resume(text))
        return True

    async def _run_fastpath_then_resume(self, text: str) -> None:
        try:
            await self._handle_request(text)
        finally:
            self.wake.resume()   # mikrofonu tetikleyiciye geri ver

    def _on_wake_died(self, reason: str) -> None:
        """Wake thread'i çalışırken ölürse (mikrofon koptu, sürücü hatası...):
        asistan sağır kalmasın — sürekli dinleme moduna otomatik geç."""
        if not self._running or self._continuous_mode:
            return
        self.bridge.submit(self._switch_to_continuous(
            f"Wake-word durdu ({reason})"))

    async def _switch_to_continuous(self, why: str) -> None:
        if self._continuous_mode:
            return
        self._continuous_mode = True
        self.ui.emit("on_log",
                     f"UYARI: {why}. Sürekli dinleme moduna geçildi — "
                     "tetik kelimesiz, doğrudan konuşabilirsin.")
        self.bridge.loop.create_task(self._continuous_listen_loop())

    async def _wake_cycle(self) -> None:
        try:
            self.ui.emit("on_state", "LISTENING")
            self.ui.emit("on_log", "SYS: Dinliyorum...")
            if getattr(self.wake, "last_wake_diag", ""):
                self.ui.emit("on_log", self.wake.last_wake_diag)
            text = await self.bridge.to_thread(
                self.stt.listen_and_transcribe, self.s.listen_timeout_s)
            if text:
                self.ui.emit("on_user_text", text)
                await self._handle_request(text)
            elif getattr(type(self.stt), "_last_peak", 0) >= 0.008 and \
                    getattr(self.stt, "last_capture_sec", 0) <= 0.8:
                peak = type(self.stt)._last_peak
                th = type(self.stt)._last_threshold
                hint = (f"SYS: Ses seviyesi eşiğin altında kaldı (seviye {peak:.3f}, "
                        f"eşik {th:.3f}) — mikrofona yaklaş ya da Windows/sistem "
                        "ayarlarından mikrofon kazancını yükselt.")
                if getattr(self, "_last_hint", "") != hint:
                    self._last_hint = hint
                    self.ui.emit("on_log", hint)
            elif getattr(self.stt, "last_capture_sec", 0) > 0.8:
                # Ses GELDİ ama çözümlenemedi — kullanıcıya görünür teşhis
                self.ui.emit("on_log",
                             f"SYS: {self.stt.last_capture_sec:.1f} sn ses algılandı ama "
                             "söz çözümlenemedi (çok kısık/uzak olabilir — biraz daha "
                             "yüksek sesle ya da mikrofona yakın dene).")
            else:
                self.ui.emit("on_state", "IDLE")
        finally:
            self.wake.resume()   # mikrofonu tetikleyiciye geri ver

    # ══ Ana yönlendirme ═════════════════════════════════════════════════════
    async def _handle_request(self, text: str) -> None:
        async with self._busy:                       # istekleri sırala
            self.ui.emit("on_state", "THINKING")
            try:
                # 0) "Her zamanki uygulamayı aç" — alışkanlıklardan çözülür
                low = text.lower()
                if self.tools and "her zamanki" in low and ("aç" in low or "başlat" in low):
                    usual = self.habits.resolve_usual_app()
                    if usual:
                        result = await self.bridge.to_thread(
                            self.tools.execute, "open_app", {"app_name": usual})
                        self.habits.record("tool:open_app", text, app=usual)
                        await self._say(str(result))
                        return
                    await self._say("Henüz alışkanlıklarını öğrenmedim — birkaç uygulama açtıktan sonra tekrar dene.")
                    return

                # 1) Deterministik niyet (V2 intent_parser) — LLM'siz, %100 güvenilir
                if self.intent_fn and self.tools:
                    intent = None
                    try:
                        intent = self.intent_fn(text)
                    except Exception:
                        pass
                    if intent:
                        tool_name, tool_args = intent
                        if tool_name == "blender_draw":
                            # "masa çiz" → Qwen-Coder bpy üretir → açık Blender'da çalıştırılır
                            await self._blender_draw(tool_args.get("instruction", text))
                            return
                        if tool_name == "freecad_draw":
                            # "freecad'de mil tasarla" → Qwen-Coder FreeCAD kodu üretir →
                            # açık FreeCAD'de çalıştırılır
                            await self._freecad_draw(tool_args.get("instruction", text))
                            return
                        self.ui.emit("on_log", f"SYS: 🔧 {tool_name}({tool_args})")
                        result = await self.bridge.to_thread(
                            self.tools.execute, tool_name, tool_args)
                        self.habits.record(f"tool:{tool_name}", text,
                                           app=tool_args.get("app_name"),
                                           response=str(result),
                                           tool_args=tool_args, source="intent")
                        await self._say(str(result))
                        return

                # 2) SADECE KOMUT MODU: yapay zekâ hiç devreye girmez.
                # Sistem görevleri (uygulama açma, fare, klavye, ses, Office,
                # kamera) intent_parser ile zaten LLM'siz çalışıyor; bu mod
                # sohbet/LLM katmanını tamamen kapatır — anında yanıt, sıfır
                # model yükü. (Ollama kurulu olmasa bile asistan çalışır.)
                if self.s.intent_only:
                    self.habits.record("intent_miss", text, source="intent_only")
                    await self._say("Bu bir sistem komutu değil. Sadece komut "
                                    "modundayım — sohbet için ayarlardan bu modu "
                                    "kapatabilirsin.")
                    return

                # 3) LLM yönlendirmesi
                route = await self.router.classify(text)
                self.habits.record(route, text)

                if route == "camera_on":
                    await self._camera_on()

                elif route == "camera_off":
                    self.vision.stop()
                    await self._say("Kamera kapatıldı.", notify=True)

                elif route == "vision":
                    await self._handle_vision(text)

                elif route == "code":
                    await self._handle_code(text)

                else:  # chat — sistem promptu alışkanlık özetiyle zenginleşir
                    system = _CHAT_SYSTEM
                    habits = self.habits.prompt_summary()
                    if habits:
                        system = system + "\n\n" + habits
                    answer = await self.router.chat(text, system)
                    self.habits.record("chat", text, response=answer, source="llm")
                    await self._say(answer)

            except Exception as e:
                self.ui.emit("on_log", f"ERR: {e}")
                self.ui.emit("on_state", "IDLE")

    # ── Rota işleyicileri ────────────────────────────────────────────────────
    async def _camera_on(self) -> None:
        await self.tts.speak("Kamera açılıyor.", kind="notify")
        self.vision.start()
        self.ui.emit("on_log", "SYS: 📷 Kamera aktif — YOLO11 canlı nesne takibi başladı.")
        self.ui.emit("on_state", "IDLE")

    async def _handle_vision(self, text: str) -> None:
        frame = self.vision.latest_frame()
        if frame is None:
            # Kamera kapalıysa aç, bir kare oluşmasını bekle
            self.vision.start()
            for _ in range(30):
                await asyncio.sleep(0.1)
                frame = self.vision.latest_frame()
                if frame:
                    break
        if frame is None:
            await self._say("Kameradan görüntü alamadım.")
            return
        answer = await self.router.analyze_image(text, frame)
        await self._say(answer)

    async def _blender_draw(self, instruction: str) -> None:
        self.ui.emit("on_log", f"SYS: 🧠 Blender betiği üretiliyor ({self.s.coder_model})...")
        prompt = (f"Blender bpy ile şunu oluşturan Python kodu yaz: {instruction}. "
                  "Kod mevcut sahneye nesne EKLESİN (sahneyi silme), import bpy ile başlasın, "
                  "kullanıcı etkileşimi/print gerektirmesin.")
        block = await self.router.generate_code(prompt)
        self.ui.emit("on_assistant_text", f"[bpy]\n{block.code}")
        if self.tools:
            result = await self.bridge.to_thread(
                self.tools.execute, "blender_exec", {"code": block.code})
            self.habits.record("tool:blender_exec", instruction, app="blender")
            await self._say(str(result))
        else:
            await self._say("Kod hazır, ekrana yazdım.")

    async def _freecad_draw(self, instruction: str) -> None:
        self.ui.emit("on_log", f"SYS: 🧠 FreeCAD betiği üretiliyor ({self.s.coder_model})...")
        prompt = (f"FreeCAD Python API'siyle (App/FreeCAD, Part, Sketcher, Draft, "
                  f"PartDesign modülleri hazır) şunu oluşturan kod yaz: {instruction}. "
                  "Belge yoksa App.newDocument(...) ile bir tane oluştur, Part.makeBox/"
                  "makeCylinder/makeSphere gibi parametrik geometri kullan, sonunda "
                  "App.ActiveDocument.recompute() çağır. Kullanıcı etkileşimi/print "
                  "gerektirmesin.")
        block = await self.router.generate_code(prompt)
        self.ui.emit("on_assistant_text", f"[freecad]\n{block.code}")
        if self.tools:
            result = await self.bridge.to_thread(
                self.tools.execute, "freecad_exec", {"code": block.code})
            self.habits.record("tool:freecad_exec", instruction, app="freecad")
            await self._say(str(result))
        else:
            await self._say("Kod hazır, ekrana yazdım.")

    async def _handle_code(self, text: str) -> None:
        self.ui.emit("on_log", f"SYS: 🧠 Kod görevi {self.s.coder_model} modeline devredildi...")
        block = await self.router.generate_code(text)
        self.ui.emit("on_assistant_text",
                     f"[{block.language}]\n{block.code}")
        # Kod sesli OKUNMAZ — kısa özet söylenir (kodu satır satır dinlemek işkence olur)
        summary = block.explanation or f"{block.language} kodun hazır, ekrana yazdım."
        await self._say(summary[:280])
        # İstenirse çalıştırmaya hazır: block.code → save/exec katmanına verilebilir

    async def _say(self, text: str, notify: bool = False) -> None:
        self.ui.emit("on_assistant_text", text)
        self.ui.emit("on_state", "SPEAKING")
        await self.tts.speak(text, kind="notify" if notify else "chat")
        await self.tts._queue.join()     # sırası bitene dek SPEAKING kalsın
        self.ui.emit("on_state", "IDLE")
