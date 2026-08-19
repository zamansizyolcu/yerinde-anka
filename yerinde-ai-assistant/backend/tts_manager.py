"""
backend/tts_manager.py — Üç motorlu, kesilebilir, kuyruklu ses katmanı.

Seçim mantığı (GUI'deki "SES" profili + mesaj türü):
  speak(text, kind="notify")  → HER ZAMAN Piper (milisaniyelik gecikme;
                                 "Sistem hazır", "Kamera açılıyor" gibi bildirimler)
  speak(text, kind="chat")    → voice_profile'a göre:
        "piper"        → Piper
        "chattts"      → ChatTTS (doğal tonlama; model tembel yüklenir)
        "xtts:<ref.wav>" → Coqui XTTS-v2 (ses klonlama; model tembel yüklenir,
                            aynen ChatTTS gibi in-process — ayrı sunucu YOK)

Tasarım notları:
  • Tüm konuşmalar tek bir asyncio.Queue'dan sırayla çalınır (üst üste binmez).
  • stop() → kuyruk boşaltılır + çalan süreç öldürülür (DUR düğmesi).
  • Ses düzeyi: WAV örnekleri numpy ile ölçeklenir → her motorda tutarlı.
  • Çalma her platformda ÖLDÜRÜLEBİLİR alt süreçle yapılır (winsound değil!).
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from .config import Settings

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


class TTSManager:
    def __init__(self, settings: Settings, on_log=lambda m: None):
        self.s = settings
        self.on_log = on_log
        self._queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self._current_proc: Optional[subprocess.Popen] = None
        self._proc_lock = threading.Lock()
        self._chattts = None            # tembel yüklenir
        self._xtts = None                # tembel yüklenir (Coqui XTTS-v2)
        self._consumer_task: Optional[asyncio.Task] = None
        self._interrupted = asyncio.Event()
        self._piper_fallback_warned = False  # aynı uyarıyı her cümlede tekrarlama
        self._piper_last_error: str | None = None  # piper'ın GERÇEK hata çıktısı

    # ── Dış API ──────────────────────────────────────────────────────────────
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Tüketici görevini başlatır. NOT: Bu metod GUI thread'inden çağrılır,
        loop ise backend thread'inde koşar — loop.create_task() thread-safe
        DEĞİLDİR; run_coroutine_threadsafe kullanmak zorunludur."""
        if self._consumer_task is None:
            self._consumer_task = asyncio.run_coroutine_threadsafe(
                self._consumer(), loop)

    async def speak(self, text: str, kind: str = "chat") -> None:
        """Kuyruğa ekler; sırası gelince çalınır. kind: 'notify' | 'chat'"""
        if text and text.strip():
            await self._queue.put((text.strip(), kind))

    def stop(self) -> None:
        """DUR düğmesi: kuyruğu boşalt + çalan sesi ANINDA kes (thread-safe)."""
        self._interrupted.set()
        try:
            while True:
                self._queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        with self._proc_lock:
            proc = self._current_proc
            self._current_proc = None
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

    # ── Kuyruk tüketicisi ────────────────────────────────────────────────────
    async def _consumer(self) -> None:
        while True:
            text, kind = await self._queue.get()
            self._interrupted.clear()
            try:
                wav = await self._synthesize(text, kind)
                if wav and not self._interrupted.is_set():
                    wav = await asyncio.to_thread(self._apply_volume, wav)
                    await asyncio.to_thread(self._play_wav_blocking, wav)
            except Exception as e:
                self.on_log(f"UYARI: TTS hatası — {e}")
            finally:
                self._queue.task_done()

    # ── Motor seçimi ─────────────────────────────────────────────────────────
    async def _synthesize(self, text: str, kind: str) -> Optional[Path]:
        profile = (self.s.voice_profile or "auto").lower()

        if kind == "notify":
            # Bildirimlerde hız kritik — ama kullanıcı açıkça SAPI/espeak
            # sesi seçtiyse bildirimlerde de ONUN sesi kullanılır (aksi halde
            # 'Türkçe ses seçtim ama İngilizce konuşuyor' karmaşası doğar).
            if profile.startswith("sapi:"):
                return await asyncio.to_thread(self._sapi, text, profile.split(":", 1)[1])
            if profile.startswith("espeak:"):
                return await asyncio.to_thread(self._espeak, text, profile.split(":", 1)[1])
            return await asyncio.to_thread(self._piper_or_platform, text)

        if profile.startswith("xtts:"):
            return await asyncio.to_thread(self._xtts_synth, text, profile.split(":", 1)[1])
        if profile == "chattts":
            return await asyncio.to_thread(self._chattts_synth, text)
        if profile.startswith("piper:"):
            wav = await asyncio.to_thread(self._piper, text,
                                          voice_path=profile.split(":", 1)[1])
            if wav is not None:
                return wav
            # ÖNCEDEN: "auto"/varsayılan profilde Piper sessizce başarısız olup
            # doğrudan espeak-ng'ye düşülüyordu — kullanıcı hiçbir uyarı görmeden
            # aniden İngilizce/aksanlı bir sesle karşılaşıyordu. Artık nedenini
            # (piper bulunamadı / ses modeli eksik / gerçek hata) net şekilde
            # bir kez logluyoruz.
            self._warn_piper_fallback_once()
            return await asyncio.to_thread(self._piper_or_platform, text)
        if profile.startswith("sapi:"):
            return await asyncio.to_thread(self._sapi, text,
                                           profile.split(":", 1)[1])
        if profile.startswith("espeak:"):
            return await asyncio.to_thread(self._espeak, text,
                                           profile.split(":", 1)[1])
        # "piper" ya da "auto"
        return await asyncio.to_thread(self._piper_or_platform, text)

    def _piper_or_platform(self, text: str) -> Optional[Path]:
        """Piper varsa onu; yoksa Windows'ta SAPI'ye, Linux'ta espeak'e düşer."""
        wav = self._piper(text)
        if wav is not None:
            return wav
        if _IS_WINDOWS:
            return self._sapi(text, voice_name=None)
        return self._espeak(text, variant="tr")

    def _warn_piper_fallback_once(self) -> None:
        if self._piper_fallback_warned:
            return
        self._piper_fallback_warned = True
        binary_found = bool(shutil.which(self.s.piper_binary) or Path(self.s.piper_binary).exists())
        # Proje piper binary kontrolü
        proj_piper = Path(__file__).resolve().parent.parent / "piper" / "piper"
        if not binary_found and proj_piper.exists():
            binary_found = True
        # Python piper modülü kontrolü
        if not binary_found:
            try:
                import piper  # noqa: F401
                binary_found = True
            except ImportError:
                pass
        voice_found = Path(self.s.piper_voice).exists()
        if not binary_found:
            reason = f"piper çalıştırılabilir dosyası bulunamadı (aranan: '{self.s.piper_binary}')"
        elif not voice_found:
            reason = f"ses modeli bulunamadı (aranan: '{self.s.piper_voice}')"
        elif self._piper_last_error:
            reason = f"piper çalıştırılamadı — {self._piper_last_error}"
        else:
            reason = "piper çalıştırılamadı (binary bulundu ama başarısız oldu)"
        self.on_log(
            f"UYARI: Piper TTS kullanılamıyor — {reason}. espeak-ng sistem "
            "sesine düşülüyor (İngilizce/aksanlı çıkabilir). Çözüm: "
            "'pip install piper-tts' ile kur (venv aktifken — kurulum.sh bunu "
            "zaten otomatik yapar) ve voices/ klasöründe bir Türkçe ses "
            "modelinin (.onnx + .json) bulunduğundan emin ol."
        )

    # ── Piper (yerel binary, milisaniyelik) ─────────────────────────────────
    def _piper(self, text: str, voice_path: str | None = None) -> Optional[Path]:
        # Piper binary arama: PATH → proje/piper/ → python3 -m piper
        binary = shutil.which(self.s.piper_binary)
        if not binary:
            # Proje kökündeki piper binary
            proj_piper = Path(__file__).resolve().parent.parent / "piper" / "piper"
            if proj_piper.exists():
                binary = str(proj_piper)
            else:
                # Python piper modülü (pip install piper-tts)
                try:
                    import piper  # noqa: F401
                    binary = "python3"
                except ImportError:
                    binary = self.s.piper_binary
        voice = voice_path or self.s.piper_voice
        if not Path(voice).exists():
            return None
        out = Path(tempfile.mktemp(prefix="yerinde-tts-", suffix=".wav"))
        try:
            if binary == "python3":
                cmd = ["python3", "-m", "piper",
                       "--model", voice, "--output_file", str(out)]
            else:
                cmd = [binary, "--model", voice, "--output_file", str(out)]
            proc = subprocess.run(
                cmd,
                input=text.encode("utf-8"), capture_output=True, timeout=60,
                creationflags=_CREATE_NO_WINDOW,
            )
            if proc.returncode == 0 and out.exists():
                self._piper_last_error = None
                return out
            # piper ÇALIŞTI (bulundu, izin sorunu yok) ama başarısız oldu -
            # genelde eksik/uyumsuz bir bağımlılık (onnxruntime, espeak-ng
            # veri dosyaları) ya da bozuk bir ses modeli olduğunda olur.
            # stderr'i saklayıp kullanıcıya GERÇEK sebebi gösteriyoruz -
            # "başarısız oldu" tek başına yeterli teşhis bilgisi vermiyordu.
            stderr_txt = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
            self._piper_last_error = stderr_txt[-300:] if stderr_txt else f"çıkış kodu {proc.returncode} (çıktı üretmedi)"
            return None
        except FileNotFoundError:
            self._piper_last_error = "çalıştırılabilir dosya bulunamadı"
            return None
        except OSError as e:
            # İzin sorunu (ör. exec biti eksik) ya da başka bir OS seviyesi
            # hata — bunu da yakalayıp aynı teşhis yoluna sokuyoruz.
            self._piper_last_error = str(e)
            return None

    # ── Windows SAPI → WAV (kadın/erkek sistem sesleri) ─────────────────────
    def _sapi(self, text: str, voice_name: str | None) -> Optional[Path]:
        if not _IS_WINDOWS:
            return self._espeak(text, "tr")
        out = Path(tempfile.mktemp(prefix="yerinde-tts-", suffix=".wav"))
        safe = text.replace("'", "''")
        select = ""
        if voice_name:
            select = f"try {{ $s.SelectVoice('{voice_name.replace(chr(39), chr(39)*2)}') }} catch {{}}; "
        # SelectVoice başarısız olursa PowerShell 'VOICE_FAIL' basar — sessizce
        # İngilizce varsayılana düşmek yerine kullanıcıya nedenini söyleriz.
        if voice_name:
            select = (f"try {{ $s.SelectVoice('{voice_name.replace(chr(39), chr(39)*2)}') }} "
                      "catch { Write-Output 'VOICE_FAIL' }; ")
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"{select}$s.SetOutputToWaveFile('{out}'); "
            f"$s.Speak('{safe}'); $s.Dispose()"
        )
        try:
            proc = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                                  timeout=60, capture_output=True, text=True,
                                  creationflags=_CREATE_NO_WINDOW)
            if voice_name and "VOICE_FAIL" in (proc.stdout or ""):
                self.on_log(
                    f"UYARI: '{voice_name}' sesi seçilemedi — Windows varsayılan "
                    "sesiyle okunuyor (aksanlı olabilir). Ayarlar>Konuşma'dan "
                    "kurulan yeni nesil sesler bu API'de görünmez; garantili "
                    "Türkçe için Piper kullan (voices/ klasöründe modeli hazır).")
            return out if out.exists() and out.stat().st_size > 44 else None
        except Exception:
            return None

    # ── espeak-ng → WAV (Linux; tr+f3 kadın / tr+m3 erkek varyantları) ──────
    def _espeak(self, text: str, variant: str) -> Optional[Path]:
        binary = shutil.which("espeak-ng") or shutil.which("espeak")
        if not binary:
            self.on_log("UYARI: espeak-ng yok (sudo apt/pacman ile kur) — ses üretilemedi.")
            return None
        out = Path(tempfile.mktemp(prefix="yerinde-tts-", suffix=".wav"))
        try:
            subprocess.run([binary, "-v", variant or "tr", "-w", str(out), text],
                           timeout=60, capture_output=True)
            return out if out.exists() and out.stat().st_size > 44 else None
        except Exception:
            return None

    # ── ChatTTS (doğal sohbet tonu, tembel yükleme) ─────────────────────────
    def _chattts_synth(self, text: str) -> Optional[Path]:
        try:
            if self._chattts is None:
                import ChatTTS
                self._chattts = ChatTTS.Chat()
                self._chattts.load(compile=False)
                self.on_log("SYS: ChatTTS yüklendi (doğal sohbet sesi).")
            import numpy as np
            import soundfile as sf
            wavs = self._chattts.infer([text])
            out = Path(tempfile.mktemp(prefix="yerinde-tts-", suffix=".wav"))
            sf.write(str(out), np.asarray(wavs[0]).squeeze(), 24000)
            return out
        except ModuleNotFoundError as e:
            if e.name and e.name.split(".")[0] == "ChatTTS":
                self.on_log("UYARI: ChatTTS kurulu değil (pip install ChatTTS soundfile) "
                           "— yedek sese düşülüyor.")
            else:
                self.on_log(f"UYARI: ChatTTS'in bir bağımlılığı eksik ('{e.name}' bulunamadı: "
                           f"pip install {e.name}) — yedek sese düşülüyor.")
            return self._piper_or_platform(text)
        except Exception as e:
            self.on_log(f"UYARI: ChatTTS hata verdi ({e}) — yedek sese düşülüyor.")
            return self._piper_or_platform(text)

    # ── Coqui XTTS-v2 (ses klonlama — in-process, ayrı sunucu YOK) ──────────
    @staticmethod
    def _xtts_error_hint(e: Exception) -> str:
        """
        Bilinen bir uyumsuzluğu tanır ve KESİN çözümü döner; tanımazsa ham
        hatayı döner.

        1) 'isin_mps_friendly': coqui-tts'in gevşek bıraktığı
           'transformers>=4.57' sınırı yüzünden pip'in transformers 5.x
           çekmesinden kaynaklanır — 5.x bu fonksiyonu kaldırdı (doğrulanmış:
           github.com/idiap/coqui-ai-TTS issue #558, bakımcı önerisi: 4.57.6).

        2) 'torchcodec paketi eksik': PyTorch 2.9'dan itibaren ses IO işlemleri
           torchaudio'dan ayrı bir pakete (torchcodec) taşındı — coqui-tts'in
           kendi hata mesajının önerdiği çözüm doğru ve yeterli.

        3) 'libtorchcodec yüklenemedi' (paket kurulu ama DLL/so açılamıyor):
           Windows'ta YAYGIN ve kısmen çözülmemiş bir sorun (bkz. meta-pytorch/
           torchcodec issue #912, #1108, #1143, #1147, #1233 — hepsi aynı
           belirtiyi gösteriyor). Genelde FFmpeg'in 'full-shared' (paylaşılan
           DLL'li) sürümü eksik ya da PATH'te değil.
        """
        msg = str(e)
        if "isin_mps_friendly" in msg:
            return ("coqui-tts, transformers 5.x ile uyumsuz (bilinen sorun: "
                    "'isin_mps_friendly' transformers 5.x'te kaldırıldı). Çözüm:\n"
                    "   pip install \"transformers==4.57.6\"")
        if "could not load libtorchcodec" in msg.lower() or "libtorchcodec_core" in msg:
            return ("torchcodec kurulu ama native DLL'i yüklenemiyor — Windows'ta "
                    "bilinen bir sorun (FFmpeg eksik/yanlış türde). Çözüm:\n"
                    "   1) FFmpeg'in 'full-shared' Windows derlemesini indir\n"
                    "      (ör. gyan.dev/ffmpeg/builds — 'full_build-shared')\n"
                    "   2) İçindeki 'bin' klasörünü PATH'e ekle\n"
                    "   3) Terminali TAMAMEN kapatıp yeniden aç (PATH güncellensin), tekrar dene\n"
                    "   Çözülmezse sorun değil — yedek sesle (Piper/ChatTTS) sorunsuz "
                    "çalışmaya devam ederim; ses klonlama isteğe bağlı bir özellik.")
        if "torchcodec" in msg.lower():
            return ("PyTorch 2.9+ ses IO için ayrı 'torchcodec' paketi istiyor. Çözüm:\n"
                    "   pip install coqui-tts[codec]\n"
                    "   (olmazsa doğrudan: pip install torchcodec)")
        return msg

    def _xtts_synth(self, text: str, ref_wav: str) -> Optional[Path]:
        """
        Referans WAV ile ses klonlar. ChatTTS ile aynı desen: model tembel
        yüklenir ve aynı Python sürecinde çalışır — F5-TTS'in eski HTTP
        sunucusu (ayrı süreç başlatma, sağlık kontrolü, port yönetimi)
        tamamen kalktı; kurulum ve bakım çok daha basit.
        """
        ref = Path(ref_wav)
        if not ref.exists():
            self.on_log(f"UYARI: XTTS referans sesi yok: {ref} — yedek sese düşülüyor.")
            return self._piper_or_platform(text)
        try:
            if self._xtts is None:
                import os
                # XTTS-v2'nin lisans onay istemi stdin bekler; arka planda
                # çalıştığımız için burada sessizce kabul ediyoruz (Coqui
                # Public Model License — ticari olmayan kullanım).
                os.environ.setdefault("COQUI_TOS_AGREED", "1")
                from TTS.api import TTS
                self.on_log("SYS: Coqui XTTS-v2 yükleniyor (ilk sefer model "
                           "inebilir, birkaç dakika sürebilir)...")
                self._xtts = TTS(self.s.xtts_model)
                self.on_log("SYS: Coqui XTTS-v2 hazır — artık kendi sesinle konuşacağım.")
            out = Path(tempfile.mktemp(prefix="yerinde-tts-", suffix=".wav"))
            self._xtts.tts_to_file(text=text, speaker_wav=str(ref),
                                   language="tr", file_path=str(out))
            return out
        except ModuleNotFoundError as e:
            # KRİTİK: eskiden her ImportError "kurulu değil" diye yorumlanıyordu.
            # coqui-tts KURULU olsa bile 'from TTS.api import TTS' içindeki bir
            # ALT bağımlılık (en sık: torch) eksikse yine ImportError/
            # ModuleNotFoundError fırlar — ve kullanıcıya YALAN söylenmiş olurdu
            # ("kurulu değil" derken paket aslında kuruluydu). e.name, TAM OLARAK
            # hangi modülün bulunamadığını verir; ona göre doğru mesajı seçiyoruz.
            top = (e.name or "").split(".")[0]
            if top in ("TTS", "coqui_tts", ""):
                self.on_log("UYARI: Coqui XTTS-v2 kurulu değil (pip install coqui-tts) "
                            "— yedek sese düşülüyor.")
            else:
                self.on_log(f"UYARI: coqui-tts kurulu ama bir bağımlılığı eksik "
                            f"('{top}' bulunamadı). Muhtemel çözüm: pip install {top} "
                            f"— (XTTS-v2 çalışması için genelde 'torch' gerekir, ayrıca "
                            f"kurulmamış olabilir). Şimdilik yedek sese düşülüyor.")
            return self._piper_or_platform(text)
        except Exception as e:
            self.on_log(f"UYARI: XTTS hata verdi ({self._xtts_error_hint(e)}) — "
                        "yedek sese düşülüyor.")
            return self._piper_or_platform(text)

    def preload_xtts(self) -> None:
        """AYARLAR'daki 'XTTS MODELİNİ YÜKLE' düğmesi için: modeli önceden
        indirip belleğe yükler ki 'sesimi kaydet' sonrası ilk cevap beklemesin."""
        if self._xtts is not None:
            self.on_log("SYS: XTTS zaten yüklü.")
            return
        try:
            import os
            os.environ.setdefault("COQUI_TOS_AGREED", "1")
            from TTS.api import TTS
            self.on_log("SYS: Coqui XTTS-v2 indiriliyor/yükleniyor "
                       "(ilk sefer ~2 GB inebilir)...")
            self._xtts = TTS(self.s.xtts_model)
            self.on_log("SYS: Coqui XTTS-v2 hazır.")
        except ModuleNotFoundError as e:
            top = (e.name or "").split(".")[0]
            if top in ("TTS", "coqui_tts", ""):
                self.on_log("UYARI: Coqui XTTS-v2 kurulu değil — pip install coqui-tts")
            else:
                self.on_log(f"UYARI: coqui-tts kurulu ama '{top}' bulunamadı — "
                           f"pip install {top} (XTTS-v2 için genelde 'torch' gerekir).")
        except Exception as e:
            self.on_log(f"UYARI: XTTS yüklenemedi — {self._xtts_error_hint(e)}")

    # ── Oynatma öncesi 48 kHz'e yükseltme (cızırtı önleme) ──────────────────
    @staticmethod
    def _resample_for_playback(wav_path: Path) -> Path:
        """
        22.05 kHz gibi düşük hızlı WAV'ı 48 kHz'e yükseltir — CachyOS/PipeWire'da
        anlık yeniden örnekleme cızırtıya yol açıyordu. YALNIZCA standart
        kütüphane kullanır (numpy/soundfile gerekmez), böylece her kurulumda çalışır.
        """
        import array
        import wave

        try:
            with wave.open(str(wav_path), "rb") as w:
                ch, width, sr, n = (w.getnchannels(), w.getsampwidth(),
                                    w.getframerate(), w.getnframes())
                if sr >= 44100 or width != 2 or n == 0:
                    return wav_path
                raw = w.readframes(n)

            samples = array.array("h")
            samples.frombytes(raw)
            frames = len(samples) // ch
            ratio = 48000 / sr
            out_frames = int(frames * ratio)
            out = array.array("h", bytes(out_frames * ch * 2))

            for i in range(out_frames):
                src = i / ratio
                i0 = int(src)
                i1 = min(i0 + 1, frames - 1)
                frac = src - i0
                for c in range(ch):
                    a = samples[i0 * ch + c]
                    b = samples[i1 * ch + c]
                    out[i * ch + c] = int(a + (b - a) * frac)

            # Klik/çıtırtı önleme: 8 ms açılış-kapanış rampası + 60 ms sessizlik
            # (Ani başlayan/biten dalga formu hoparlörde "çıt" sesi yapıyordu.)
            ramp = int(0.008 * 48000)
            total = out_frames
            for i in range(min(ramp, total)):
                g = i / ramp
                for c in range(ch):
                    out[i * ch + c] = int(out[i * ch + c] * g)
                    j = total - 1 - i
                    out[j * ch + c] = int(out[j * ch + c] * g)
            tail = array.array("h", bytes(int(0.06 * 48000) * ch * 2))

            with wave.open(str(wav_path), "wb") as w:
                w.setnchannels(ch)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(out.tobytes() + tail.tobytes())
        except Exception:
            pass
        return wav_path

    # ── Ses düzeyi (GUI: SES DÜZEYİ %) ──────────────────────────────────────
    def _apply_volume(self, wav_path: Path) -> Path:
        vol = max(0.0, min(float(self.s.volume), 1.0))
        if abs(vol - 1.0) < 1e-3:
            return wav_path
        try:
            import numpy as np
            import soundfile as sf
            data, sr = sf.read(str(wav_path))
            sf.write(str(wav_path), data * vol, sr)
        except Exception:
            pass  # soundfile yoksa orijinal seviyede çal
        return wav_path

    # ── Çalma (öldürülebilir alt süreç — DUR anında kesebilsin) ─────────────
    def _play_wav_blocking(self, wav_path: Path) -> None:
        if _IS_WINDOWS:
            cmd = ["powershell", "-WindowStyle", "Hidden", "-Command",
                   f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync()"]
        else:
            # ÇITIRTI DÜZELTMESİ (CachyOS/PipeWire):
            # ffplay, SDL üzerinden küçük tamponla çalıyor ve PipeWire'da
            # cızırtı/kesinti yapıyordu. Sıralama artık:
            #   pw-play (PipeWire yerel) → paplay (Pulse/PipeWire) → ffplay → aplay
            # Ayrıca ses, aygıtın beklediği 48 kHz'e önceden yükseltiliyor;
            # 22.05 kHz'lik Piper/espeak çıktısının anlık yeniden örneklenmesi
            # de cızırtının bir kaynağıydı.
            wav_path = self._resample_for_playback(wav_path)
            player = next((p for p in ("pw-play", "paplay", "ffplay", "aplay")
                           if shutil.which(p)), None)
            if player == "ffplay":
                cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                       "-af", "aresample=async=1", str(wav_path)]
            elif player == "aplay":
                cmd = ["aplay", "-q", "-D", "pulse", str(wav_path)]
            elif player:
                cmd = [player, str(wav_path)]
            else:
                self.on_log("UYARI: Ses çalıcı yok (pw-play/paplay/ffplay/aplay).")
                return
        try:
            proc = subprocess.Popen(cmd, creationflags=_CREATE_NO_WINDOW,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with self._proc_lock:
                self._current_proc = proc
            proc.wait(timeout=300)
        finally:
            with self._proc_lock:
                if self._current_proc is proc:
                    self._current_proc = None
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass
