"""
Çevrimdışı seslendirme (TTS) — CachyOS sürümü.

Öncelik sırası:
  1) Piper (nöral, tamamen yerel, çok daha doğal Türkçe ses)
  2) espeak-ng / spd-say (actions.tts.speak_text) — Piper kurulu değilse otomatik yedek

Piper kurulumu (opsiyonel ama önerilir):
  - AUR: yay -S piper-tts-bin   (ya da https://github.com/rhasspy/piper 'dan indir)
  - Bir Türkçe ses modeli indir (örn. tr_TR-fahrettin-medium.onnx + .json),
    proje kökündeki "voices" klasörüne koy.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from app_config import get_app_config_value
from actions.tts import speak_text as _fallback_speak_text
from actions.tts import stop_speaking as _fallback_stop_speaking

BASE_DIR = Path(__file__).resolve().parent.parent
_current_proc = None
_proc_lock = threading.Lock()


def _find_piper_binary() -> str | None:
    # 1) config'de özel yol ayarlanmış mı?
    configured = str(get_app_config_value("piper_binary_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    # 2) Python piper modülü yüklü mü? (pip install piper-tts)
    try:
        import piper  # noqa: F401
        # piper modülü varsa __file__'ı binary olarak kullan (Python modülü)
        piper_mod = Path(piper.__file__).parent / "__main__.py"
        if piper_mod.exists():
            return "python3"  # speak_text_offline'da python -m piper çağrılır
    except ImportError:
        pass
    # 3) Proje kökündeki piper binary (yerinde-ai-assistant/piper/ klasörü)
    proj_piper = BASE_DIR / "piper" / "piper"
    if proj_piper.exists():
        return str(proj_piper)
    proj_piper2 = BASE_DIR / "piper" / "piper_bin"
    if proj_piper2.exists():
        return str(proj_piper2)
    # 4) Sistem PATH'inde piper var mı?
    return shutil.which("piper")


def _find_piper_voice() -> str | None:
    configured = str(get_app_config_value("piper_voice_path", "") or "").strip()
    if configured and Path(configured).exists():
        return configured
    voices_dir = BASE_DIR / "voices"
    if voices_dir.exists():
        matches = sorted(voices_dir.glob("*.onnx"))
        if matches:
            return str(matches[0])
    return None


def _pick_audio_player() -> str | None:
    for player in ("ffplay", "paplay", "aplay", "mpg123"):
        if shutil.which(player):
            return player
    return None


def _play_wav_linux(path: Path):
    global _current_proc
    player = _pick_audio_player()
    if not player:
        return
    proc = None
    try:
        if player == "ffplay":
            cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)]
        elif player == "aplay":
            cmd = ["aplay", "-q", str(path)]
        elif player == "mpg123":
            cmd = ["mpg123", "-q", str(path)]
        else:
            cmd = ["paplay", str(path)]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with _proc_lock:
            _current_proc = proc
        proc.wait(timeout=60)
    except Exception:
        pass
    finally:
        with _proc_lock:
            if _current_proc is proc:
                _current_proc = None


def _speak_with_piper(piper_bin: str, piper_voice: str, text: str, on_done=None, blocking: bool = False):
    global _current_proc

    def _run():
        global _current_proc
        try:
            tmp = tempfile.NamedTemporaryFile(prefix="yerinde-piper-", suffix=".wav", delete=False)
            tmp_path = Path(tmp.name)
            tmp.close()

            # Python piper modülü (pip install piper-tts) → python3 -m piper
            if piper_bin == "python3":
                cmd = ["python3", "-m", "piper",
                       "--model", piper_voice, "--output_file", str(tmp_path)]
            else:
                cmd = [piper_bin, "--model", piper_voice, "--output_file", str(tmp_path)]

            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            with _proc_lock:
                _current_proc = proc
            proc.communicate(input=text.encode("utf-8"), timeout=60)
            with _proc_lock:
                if _current_proc is proc:
                    _current_proc = None

            if proc.returncode == 0 and tmp_path.exists():
                _play_wav_linux(tmp_path)
            else:
                _fallback_speak_text(text, blocking=True)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
        except Exception:
            _fallback_speak_text(text, blocking=True)
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def stop_speaking():
    """Şu anda çalan çevrimdışı sesi (Piper sentezi, WAV çalma veya espeak-ng) hemen durdurur."""
    global _current_proc
    with _proc_lock:
        proc = _current_proc
        _current_proc = None
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass
    _fallback_stop_speaking()


def speak_text_offline(text: str, on_done=None, blocking: bool = False, log_fn=None):
    """
    Metni çevrimdışı seslendirir. Ayarlar panelinden seçilen ses tercihine göre:
      - "piper:<yol>"    → o Piper ses modelini kullanır
      - "espeak:<varyant>" → o espeak-ng ses varyantını kullanır (ör. tr+f3 kadın, tr+m3 erkek)
      - "auto" (varsayılan) → Piper varsa onu, yoksa espeak-ng'nin varsayılan
        Türkçe sesini kullanır
    Hepsi tamamen yerel/çevrimdışı çalışır.
    log_fn: (opsiyonel) durum/uyarı mesajlarını iletmek için çağrılacak fonksiyon
            (örn. ui.write_log). Verilmezse mesajlar sadece konsola yazılır.
    """
    def _log(msg: str):
        if log_fn:
            log_fn(msg)
        else:
            print(msg)

    if not text or not text.strip():
        if on_done:
            on_done()
        return

    choice = str(get_app_config_value("offline_voice_choice", "auto") or "auto")

    if choice.startswith("espeak:"):
        variant = choice.split(":", 1)[1]
        _fallback_speak_text(text, on_done=on_done, blocking=blocking, voice_variant=variant)
        return

    if choice.startswith("piper:"):
        piper_path = choice.split(":", 1)[1]
        piper_bin = _find_piper_binary()
        if piper_bin and Path(piper_path).exists():
            _speak_with_piper(piper_bin, piper_path, text, on_done=on_done, blocking=blocking)
            return
        if not piper_bin:
            _log(
                "UYARI: Piper sesi seçili ama 'piper' komutu bulunamadı — espeak-ng'ye "
                "düşülüyor. Türkçe Piper sesini duymak için: yay -S piper-tts-bin"
            )
        else:
            _log("UYARI: Seçili Piper ses dosyası bulunamadı, otomatik moda dönülüyor.")

    piper_bin = _find_piper_binary()
    piper_voice = _find_piper_voice()
    if piper_bin and piper_voice:
        _speak_with_piper(piper_bin, piper_voice, text, on_done=on_done, blocking=blocking)
    else:
        _fallback_speak_text(text, on_done=on_done, blocking=blocking)


def diagnose_voice_setup() -> str | None:
    """
    Mevcut ses ayarlarını kontrol eder; Piper seçiliyken binary bulunamıyorsa
    açıklayan bir uyarı metni döner. espeak-ng Türkçe'yi yerleşik desteklediği
    için (ek dil paketi gerekmez) o senaryoda genelde sorun çıkmaz.
    """
    choice = str(get_app_config_value("offline_voice_choice", "auto") or "auto")
    piper_bin = _find_piper_binary()

    if choice.startswith("piper:") or (choice == "auto" and _find_piper_voice()):
        if not piper_bin:
            return (
                "Piper sesi seçili/mevcut ama 'piper' komutu bulunamadı — bu yüzden "
                "espeak-ng'ye düşülüyor. Türkçe Piper sesini duymak için: "
                "yay -S piper-tts-bin (ya da https://github.com/rhasspy/piper)"
            )
    return None
