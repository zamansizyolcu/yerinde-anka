"""
TTS (Text-to-Speech) — CachyOS (Arch Linux) için espeak-ng / spd-say kullanır.
Tamamen çevrimdışı çalışır. Kurulum: sudo pacman -S espeak-ng speech-dispatcher
"""

import shutil
import subprocess
import threading

_current_proc = None
_proc_lock = threading.Lock()


def _pick_engine() -> str | None:
    for engine in ("espeak-ng", "espeak", "spd-say"):
        if shutil.which(engine):
            return engine
    return None


def speak_text(text: str, on_done=None, blocking: bool = False, voice_variant: str | None = None):
    """
    Metni sesli olarak okur (espeak-ng / spd-say — tamamen yerel).
    on_done: okuma bitince çağrılacak fonksiyon (opsiyonel)
    blocking: True ise bitene kadar bekler
    voice_variant: espeak-ng ses varyantı, örn. "tr+m3" (erkek) / "tr+f3" (kadın).
                   Belirtilmezse düz "tr" kullanılır.
    """
    global _current_proc

    if not text or not text.strip():
        if on_done:
            on_done()
        return

    max_len = 500
    if len(text) > max_len:
        text = text[:max_len] + "..."

    engine = _pick_engine()
    espeak_voice = voice_variant or "tr"

    def _run():
        global _current_proc
        proc = None
        try:
            if engine in ("espeak-ng", "espeak"):
                proc = subprocess.Popen(
                    [engine, "-v", espeak_voice, text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            elif engine == "spd-say":
                proc = subprocess.Popen(
                    ["spd-say", "-l", "tr", "-w", text],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            if proc:
                with _proc_lock:
                    _current_proc = proc
                proc.wait(timeout=60)
            # engine yoksa sessizce geç — kullanıcı ekrandaki metni okuyabilir.
        except Exception:
            pass
        finally:
            with _proc_lock:
                if _current_proc is proc:
                    _current_proc = None
        if on_done:
            on_done()

    if blocking:
        _run()
    else:
        threading.Thread(target=_run, daemon=True).start()


def stop_speaking():
    """Şu anda okunmakta olan metni hemen susturur (varsa)."""
    global _current_proc
    with _proc_lock:
        proc = _current_proc
        _current_proc = None
    if proc and proc.poll() is None:
        try:
            proc.terminate()
        except Exception:
            pass


def get_available_voices() -> list[str]:
    """espeak-ng'nin desteklediği Türkçe ses varyantlarını listeler."""
    try:
        result = subprocess.run(
            ["espeak-ng", "--voices=tr"],
            capture_output=True, text=True, timeout=10,
        )
        lines = [line.strip() for line in result.stdout.splitlines()[1:] if line.strip()]
        return lines
    except Exception:
        return []
