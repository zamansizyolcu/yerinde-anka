"""
Yerel Ollama sunucusunda kurulu olan modelleri listeler.
Kullanıcının bilgisayarında hangi modeller varsa (ollama pull ile indirilmiş),
bu fonksiyon onları döner — ayarlar panelindeki model seçici bunu kullanır.
"""

from __future__ import annotations

import requests


def list_installed_models(host: str = "http://localhost:11434", timeout: float = 3.0) -> list[str]:
    try:
        resp = requests.get(f"{host.rstrip('/')}/api/tags", timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        names = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        return sorted(names)
    except Exception:
        return []
