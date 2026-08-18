"""
backend/wake_word.py — Vosk ile "Yerinde" tetikleme kelimesi.

Kararlılık kuralları (yaşanmış hatalardan):
  1) start() modeli SENKRON yükler ve doğrular — model klasörü yoksa False
     döner ki SystemController anında sürekli-dinleme yedeğine geçebilsin.
     (Eski sürümde model thread içinde yükleniyor, hata sessiz kalıyor ve
     asistan 'Sistem hazır' dedikten sonra sonsuza dek SAĞIR bekliyordu.)
  2) Duraklatılınca (pause) mikrofon akışı GERÇEKTEN KAPATILIR — Whisper
     kayıt yaparken iki giriş akışı çakışmaz (Linux/ALSA'da ikinci akış
     açılamayabiliyor; Pardus'ta 'beni anlamıyor' şikayetinin bir ayağı).
  3) Döngü beklenmedik şekilde ölürse on_died çağrılır — SystemController
     sürekli-dinleme moduna düşer, asistan asla sessizce sağır kalmaz.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

SAMPLE_RATE = 16000
BLOCK = 4000  # ~0.25 sn


class VoskWakeWord:
    def __init__(self, model_path: str, wake_word: str,
                 on_wake: Callable[[], None],
                 on_died: Optional[Callable[[str], None]] = None,
                 on_text: Optional[Callable[[str], bool]] = None):
        """
        on_text: Vosk'un çözümlediği HER cümle buraya gelir. True dönerse
        (yani doğrudan bir komutsa) wake döngüsü tetiklenmez.

        NEDEN: Eskiden Vosk yalnızca "yerinde" kelimesini tanıyacak şekilde
        kısıtlıydı. Kullanıcı "sunum aç" dediğinde HİÇBİR ŞEY olmuyordu —
        önce "Yerinde" demesi gerekiyordu. Artık tam sözlükle dinliyoruz:
        tetik kelime de, doğrudan komutlar da duyuluyor.
        """
        self.model_path = model_path
        self.wake_word = wake_word.lower().strip()
        self.on_wake = on_wake
        self.on_died = on_died
        self.on_text = on_text
        self.last_wake_diag = ""   # bkz. _loop(): "X sn, tepe seviye Y" teşhisi
        self._running = False
        self._paused = threading.Event()   # set → duraklat (mikrofonu bırak)
        self._thread: threading.Thread | None = None
        self._model = None
        self.last_error: str | None = None

    # ── Yaşam döngüsü ────────────────────────────────────────────────────────
    def start(self) -> bool:
        """Modeli ŞİMDİ yükler; ancak her şey doğrulanırsa True döner."""
        if self._running:
            return True
        try:
            import vosk  # noqa: F401
        except ImportError as e:
            self.last_error = f"Eksik paket: {e} (pip install vosk)"
            return False
        # NOT: sounddevice burada ZORUNLU değil — MicStream, sounddevice
        # çalışmazsa/sessiz kalırsa parec/arecord'a otomatik düşer. Linux'ta
        # 'ne Vosk ne Whisper hiç duymuyor' şikayetinin kök nedeni, PortAudio'nun
        # hatasız ama SESSİZ kalabilmesiydi — artık bunu MicStream tespit eder.

        if not Path(self.model_path).exists():
            self.last_error = (
                f"Vosk model klasörü yok: '{self.model_path}'. "
                "İndir: https://alphacephei.com/vosk/models → "
                "vosk-model-small-tr-0.3 zip'ini aç, klasörü proje köküne "
                f"'{self.model_path}' adıyla koy."
            )
            return False

        try:
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(self.model_path)
        except Exception as e:
            # "Failed to create a model" tek başına neyin eksik/bozuk olduğunu
            # söylemiyor — klasörün GERÇEKTEN içinde ne olduğunu da logla ki
            # 'model var ama yüklenmiyor' durumunda kör kalınmasın. En sık
            # sebep: zip'in eksik/yarım indirilmesi ya da klasörün bir üst
            # seviyede iç içe açılması (vosk-model/vosk-model-small-tr-0.3/...).
            try:
                contents = ", ".join(sorted(p.name for p in Path(self.model_path).iterdir())) or "(boş)"
            except Exception:
                contents = "(klasör okunamadı)"
            self.last_error = (
                f"Vosk modeli yüklenemedi ('{self.model_path}'): {e}. "
                f"Klasördeki dosya/klasörler: {contents}. Beklenen: 'am', 'conf', "
                "'graph' (ve genelde 'ivector') alt klasörleri DOĞRUDAN bu klasörün "
                "içinde olmalı. Eğer yukarıdaki listede bunlar yoksa, ya indirme "
                "yarım kalmış ya da zip bir seviye fazla iç içe açılmış demektir — "
                "https://alphacephei.com/vosk/models adresinden modeli yeniden "
                "indirip klasörü kontrol et."
            )
            return False

        self._running = True
        self._thread = threading.Thread(target=self._run, name="yerinde-wake", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        """STT kayıt yaparken çağır — mikrofon akışı tamamen kapanır."""
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    # ── İç döngü ─────────────────────────────────────────────────────────────
    def _run(self) -> None:
        try:
            self._loop()
        except Exception as e:
            self.last_error = f"Wake-word döngüsü çöktü: {e}"
        finally:
            was_running = self._running
            self._running = False
            if was_running and self.on_died:
                try:
                    self.on_died(self.last_error or "bilinmeyen neden")
                except Exception:
                    pass

    def _loop(self) -> None:
        import vosk
        import numpy as np
        from .audio_input import MicStream, resample_to_16k

        def _log(m):
            # Wake thread'inden — SystemController henüz bağlı olmayabilir,
            # last_error'a da yazalım ki teşhis mesajı kaybolmasın.
            self.last_error = m

        while self._running:
            # Duraklatıldıysa mikrofonu HİÇ açma — STT'ye tam devret
            if self._paused.is_set():
                time.sleep(0.1)
                continue

            mic = MicStream(samplerate=SAMPLE_RATE, blocksize=BLOCK, log=_log)
            if not mic.start():
                # Mikrofondan HİÇBİR yolla veri alınamıyor (sounddevice sessiz
                # VE parec/arecord da yok/başarısız) — asistan sağır kalmasın,
                # sürekli-dinleme yedeğine düşülsün diye ölümü bildir.
                raise RuntimeError(self.last_error or "Mikrofon açılamadı")

            # TAM SÖZLÜK (grammar YOK): tetik kelime + doğrudan komutlar
            rec = vosk.KaldiRecognizer(self._model, SAMPLE_RATE)
            # NOT: "Yerinde diyorum ama geç/geç algılanıyor" şikayetlerini
            # teşhis edebilmek için, bu dinleme oturumu boyunca geçen süreyi
            # ve gözlenen tepe ses seviyesini takip ediyoruz — tetik kelime
            # algılanınca ikisini de logluyoruz. Böylece bir dahaki sefere
            # "yavaş" şikayetinde log'un kendisi zaten "X sn, tepe seviye Y"
            # diye söylüyor olacak, tahmin yürütmemize gerek kalmayacak.
            _t_session_start = time.time()
            _peak = 0.0
            try:
                while self._running and not self._paused.is_set():
                    chunk = mic.read(timeout=0.5)
                    if chunk is None:
                        continue
                    if mic.rate != SAMPLE_RATE:
                        chunk = resample_to_16k(chunk, mic.rate)
                    try:
                        samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                        if len(samples):
                            _peak = max(_peak, float(np.max(np.abs(samples))))
                    except Exception:
                        pass
                    final = rec.AcceptWaveform(chunk)
                    if final:
                        text = json.loads(rec.Result()).get("text", "").strip()
                    else:
                        text = json.loads(rec.PartialResult()).get("partial", "").strip()

                    if not text:
                        continue

                    has_wake = (self.wake_word in text
                                or self.wake_word in text.replace(" ", ""))

                    # 1) Tetik kelime → uzun cümle için Whisper'a geç
                    if has_wake:
                        elapsed = time.time() - _t_session_start
                        hint = ""
                        if _peak < 0.01:
                            hint = " — ⚠ tepe seviye çok düşük, mikrofon neredeyse hiç ses almıyor olabilir"
                        elif _peak < 0.05:
                            hint = " — ⚠ tepe seviye kısık, mikrofon kazancını yükseltmek gecikmeyi azaltabilir"
                        self.last_wake_diag = (f"SYS: 'Yerinde' algılandı ({elapsed:.1f} sn, "
                                               f"tepe ses seviyesi {_peak:.3f}){hint}")
                        self.pause()
                        try:
                            self.on_wake()
                        except Exception:
                            self.resume()
                        break

                    # 2) Tetik kelime YOK ama tamamlanmış bir cümle var →
                    #    doğrudan komut olabilir (sunum aç, kamerayı kapat...)
                    if final and self.on_text:
                        try:
                            handled = self.on_text(text)
                        except Exception:
                            handled = False
                        if handled:
                            rec = vosk.KaldiRecognizer(self._model, SAMPLE_RATE)
            finally:
                mic.close()   # mikrofon serbest (pause veya wake sonrası)
