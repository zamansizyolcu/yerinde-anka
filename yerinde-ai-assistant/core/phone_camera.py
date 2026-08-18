"""
core/phone_camera.py — Telefonun çektiği fotoğrafı, aktif modun görüş
motoruyla (Gemini Vision ya da Ollama VL) analiz eder.

core/remote_server.py'deki 'camera' mesaj türü burayı çağırır. Böylece telefon
kamerası, masaüstünün webcam'ı ile aynı analiz yeteneğini paylaşır:
  • model_provider == "gemini"  → google-genai (Gemini Vision)
  • model_provider == "ollama"  → Ollama vision modeli (qwen2-vl / llama3.2-vision)
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path


def analyze_phone_image(jpeg_bytes: bytes, prompt: str = "") -> str:
    """Telefon kamerasından gelen JPEG kareyi analiz edip Türkçe metin döner."""
    from app_config import get_model_provider

    prompt = (prompt or "").strip()
    try:
        if get_model_provider() == "ollama":
            return _analyze_ollama(jpeg_bytes, prompt)
        return _analyze_gemini(jpeg_bytes, prompt)
    except Exception as exc:
        return f"Telefon kamerası analizi başarısız: {exc}"


def _analyze_gemini(jpeg_bytes: bytes, prompt: str) -> str:
    """Gemini Vision (masaüstü webcam analiziyle aynı istemci/model zinciri)."""
    from actions.document_tools import analyze_image_file

    fd, name = tempfile.mkstemp(suffix=".jpg")
    try:
        with Path(name).open("wb") as f:
            f.write(jpeg_bytes)
        return analyze_image_file(name, prompt)
    finally:
        try:
            Path(name).unlink()
        except OSError:
            pass


def _analyze_ollama(jpeg_bytes: bytes, prompt: str) -> str:
    """Ollama VL (V3 çekirdeğin ModelRouter.analyze_image yolu)."""
    from app_config import get_app_config_value
    from backend.config import Settings
    from backend.ollama_client import OllamaClient
    from backend.model_router import ModelRouter

    settings = Settings()
    settings.vision_model = (
        str(get_app_config_value("ollama_vision_model", "") or "").strip()
        or settings.vision_model
    )
    client = OllamaClient(
        host=settings.ollama_host,
        num_ctx=settings.num_ctx,
        keep_alive=settings.keep_alive,
    )
    router = ModelRouter(settings, client)

    async def _run() -> str:
        return await router.analyze_image(prompt, jpeg_bytes)

    return asyncio.run(_run())
