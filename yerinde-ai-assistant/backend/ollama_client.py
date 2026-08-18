"""
backend/ollama_client.py — Tüm Ollama modelleri için tek asenkron istemci.

requests bloklayıcıdır; her çağrı asyncio.to_thread ile worker'a taşınır,
böylece event-loop hiç tıkanmaz. Gemma2 (router/sohbet), Qwen2.5-Coder ve
Qwen2-VL aynı istemciyi paylaşır — model adı parametredir.

KARARLILIK/PERFORMANS notları:
  • Her istek için yeni bir requests.post yerine kalıcı bir requests.Session
    kullanılıyor — TCP bağlantısı (localhost'a bile olsa) yeniden kurulmak
    yerine korunuyor, bu da özellikle zayıf/gömülü donanımda (Orange Pi gibi)
    her turda küçük ama kümülatif bir gecikmeyi ortadan kaldırıyor.
  • Ollama servisi az önce başlamışsa / kısa süreliğine meşgulse bağlantı
    anlık olarak reddedilebiliyor (ConnectionError) — bunun için kısa
    aralıklarla birkaç kez otomatik yeniden deneme eklendi; kullanıcı bunu
    "bağlanamadı" hatası olarak GÖRMEZ, işlem sessizce tekrar dener.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import requests


class OllamaError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(f"Ollama {status}: {message}")


class OllamaClient:
    def __init__(self, host: str, num_ctx: int = 8192, keep_alive: str = "30m",
                 timeout: float = 180.0):
        self.host = host.rstrip("/")
        self.num_ctx = num_ctx
        self.keep_alive = keep_alive
        self.timeout = timeout
        # Kalıcı bağlantı havuzu: aynı Ollama sunucusuna yapılan ardışık
        # isteklerde TCP el sıkışmasını tekrarlamaz (bkz. yukarıdaki not).
        self._session = requests.Session()

    # ── Düşük seviye ─────────────────────────────────────────────────────────
    def _post_sync(self, path: str, payload: dict, retries: int = 2) -> dict:
        """
        POST atar; Ollama servisi anlık olarak meşgulse/yeni başlıyorsa
        (ConnectionError — bağlantı reddedildi) kısa bir bekleme ile birkaç
        kez daha dener. BİLEREK sadece ConnectionError'da yeniden dener,
        Timeout'ta DENEMEZ: model zaten (yavaş da olsa) çalışıyor olabilir —
        böyle bir anda ikinci bir istek daha göndermek zayıf donanımda
        (Orange Pi gibi) yükü ikiye katlayıp durumu daha da kötüleştirebilir.
        Gerçek bir hata (400/500 vb.) hemen OllamaError olarak yükseltilir.
        """
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self._session.post(
                    f"{self.host}{path}", json=payload, timeout=self.timeout)
                break
            except requests.exceptions.ConnectionError as e:
                last_exc = e
                if attempt < retries:
                    time.sleep(0.6 * (attempt + 1))  # 0.6s, 1.2s ...
                    continue
                raise
        else:
            raise last_exc  # pragma: no cover — for-else güvenlik ağı

        if resp.status_code >= 400:
            try:
                msg = resp.json().get("error", resp.text)
            except Exception:
                msg = resp.text
            raise OllamaError(resp.status_code, msg)
        return resp.json()

    async def chat(self, model: str, messages: list[dict],
                   images_b64: list[str] | None = None,
                   options: dict | None = None) -> str:
        """
        /api/chat — son kullanıcı mesajına istenirse görüntü(ler) iliştirir
        (VL modelleri için). Yanıtın düz metnini döner.
        """
        msgs = [dict(m) for m in messages]
        if images_b64 and msgs and msgs[-1]["role"] == "user":
            msgs[-1]["images"] = images_b64

        payload = {
            "model": model,
            "messages": msgs,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_ctx": self.num_ctx, **(options or {})},
        }
        data = await asyncio.to_thread(self._post_sync, "/api/chat", payload)
        return (data.get("message", {}).get("content") or "").strip()

    async def warmup(self, model: str) -> None:
        """Modeli belleğe önceden yükler (ilk yanıt gecikmesini yok eder)."""
        try:
            await asyncio.to_thread(
                self._post_sync, "/api/generate",
                {"model": model, "prompt": "", "keep_alive": self.keep_alive},
            )
        except Exception:
            pass  # tanılama SystemController'da yapılır

    async def list_models(self) -> list[str]:
        def _get() -> Any:
            r = self._session.get(f"{self.host}/api/tags", timeout=5)
            r.raise_for_status()
            return r.json()
        try:
            data = await asyncio.to_thread(_get)
            return sorted(m.get("name", "") for m in data.get("models", []) if m.get("name"))
        except Exception:
            return []

    @staticmethod
    def encode_image(jpeg_bytes: bytes) -> str:
        return base64.b64encode(jpeg_bytes).decode("ascii")
