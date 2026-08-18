"""
backend/bridge.py — Tkinter ana thread'ini ASLA kilitlemeyen asyncio köprüsü.

Mimari kural:
  • Tüm backend işi, kendi thread'inde dönen TEK bir asyncio event-loop'ta yaşar.
  • GUI → backend:  bridge.submit(coro)              (thread-safe, Future döner)
  • backend → GUI:  ui.emit("on_log", "...")         (root.after ile ana thread'e)

Böylece Whisper/YOLO/Ollama ne kadar ağır çalışırsa çalışsın arayüz donmaz.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


class AsyncioBridge:
    """Arka planda yaşayan tek asyncio loop. GUI thread'inden coroutine gönderilir."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run, name="yerinde-async", daemon=True)
        self._started = threading.Event()

    def _run(self) -> None:
        asyncio.set_event_loop(self.loop)
        self._started.set()
        self.loop.run_forever()

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()
            self._started.wait(timeout=5)

    def submit(self, coro: Coroutine) -> concurrent.futures.Future:
        """Herhangi bir thread'den (GUI dahil) coroutine çalıştırır."""
        return asyncio.run_coroutine_threadsafe(coro, self.loop)

    async def to_thread(self, fn: Callable, *args, **kwargs) -> Any:
        """Bloklayan (CPU/IO ağır) işi worker thread'e taşır — loop'u tıkamaz."""
        return await asyncio.to_thread(fn, *args, **kwargs)

    def stop(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)


@dataclass
class UICallbacks:
    """
    GUI'nin backend'e verdiği kancalar. Her biri GUI ana thread'inde çalıştırılır.
    Mevcut ui.py'deki karşılıkları:
      on_state          → ui.set_state("LISTENING"/"THINKING"/"SPEAKING"/"IDLE")
      on_log            → ui.write_log(...)         (sağ Konuşma paneli, SYS satırı)
      on_user_text      → ui.write_log(f"Siz: ...")
      on_assistant_text → ui.write_log(f"YERINDE: ...")
      on_frame          → ui.update_webcam_preview(jpeg_bytes)  (YOLO kutulu kare)
      on_camera_state   → ui.set_webcam_active(bool)
    """
    on_state: Callable[[str], None] = lambda s: None
    on_log: Callable[[str], None] = lambda m: None
    on_user_text: Callable[[str], None] = lambda t: None
    on_assistant_text: Callable[[str], None] = lambda t: None
    on_frame: Callable[[bytes], None] = lambda b: None
    on_camera_state: Callable[[bool], None] = lambda a: None
    _tk_root: Any = field(default=None, repr=False)

    def bind_tk(self, root) -> None:
        """Tkinter root'u ver — tüm emit'ler root.after(0, ...) ile ana thread'e sarılır."""
        self._tk_root = root

    def emit(self, name: str, *args) -> None:
        fn = getattr(self, name, None)
        if fn is None:
            return
        if self._tk_root is not None:
            try:
                self._tk_root.after(0, lambda: fn(*args))
                return
            except Exception:
                pass  # pencere kapanıyorsa sessizce düş
        try:
            fn(*args)
        except Exception:
            pass
