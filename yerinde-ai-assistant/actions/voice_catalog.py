"""
actions/voice_catalog.py — 3 ERKEK + 3 KADIN Türkçe ses profili.

Aynı katalog HEM çevrimiçi (Gemini) HEM çevrimdışı (Ollama) modda kullanılır:
her profil, platformda gerçekten çalışan bir motora eşlenir.

  • Piper (varsa)  → en doğal Türkçe ses (kadın: dfki-medium)
  • espeak-ng      → tr+f1..f3 (kadın) / tr+m1..m3 (erkek) varyantları:
                     her platformda kurulabilir, 6 farklı ses garantisi verir
  • Windows SAPI   → sistemde Türkçe ses varsa (Tolga vb.) tercih edilir

Profil değerleri TTSManager ve actions/tts.py tarafından doğrudan anlaşılır:
  "espeak:tr+m3" | "sapi:<isim>" | "piper:<yol>" | "xtts:<ref.wav>" | "chattts"
"""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"
BASE_DIR = Path(__file__).resolve().parent.parent

# (etiket, cinsiyet, espeak varyantı)
CATALOG = [
    ("👩 Kadın 1 — Yumuşak",  "kadın", "tr+f2"),
    ("👩 Kadın 2 — Berrak",   "kadın", "tr+f3"),
    ("👩 Kadın 3 — Sıcak",    "kadın", "tr+f4"),
    ("👨 Erkek 1 — Derin",    "erkek", "tr+m1"),
    ("👨 Erkek 2 — Net",      "erkek", "tr+m3"),
    ("👨 Erkek 3 — Genç",     "erkek", "tr+m5"),
]


def _sapi_turkish_voices() -> list[str]:
    """Windows'ta kurulu Türkçe SAPI seslerinin adları."""
    if not _IS_WINDOWS:
        return []
    try:
        from actions.tts import get_available_voices
        # get_available_voices() Linux'ta espeak-ng string satırları,
        # Windows'ta dict listesi döndürebilir.
        voices = get_available_voices()
        result = []
        for v in voices:
            if isinstance(v, dict):
                name = v.get("name", "")
                culture = str(v.get("culture", "")).lower()
                if "tr" in culture or "turk" in name.lower():
                    result.append(name)
            elif isinstance(v, str) and v.strip():
                parts = v.split()
                if len(parts) >= 2:
                    variant = parts[1]
                    if "tr" in variant.lower():
                        result.append(variant)
        return result
    except Exception:
        return []


def list_voices() -> list[dict]:
    """
    Arayüzün SES listesinde gösterilecek 6 profil (+ varsa Piper/SAPI).
    Her öğe: {"label": ..., "value": ..., "gender": ...}
    """
    out: list[dict] = []

    # Piper (en doğal) — kurulu ses modelleri
    voices_dir = BASE_DIR / "voices"
    if voices_dir.exists():
        for onnx in sorted(voices_dir.glob("*.onnx")):
            kadin = "dfki" in onnx.stem.lower() or "female" in onnx.stem.lower()
            out.append({"label": f"🧠 {onnx.stem} (Piper, {'kadın' if kadin else 'erkek'})",
                        "value": f"piper:{onnx}",
                        "gender": "kadın" if kadin else "erkek"})

    # Windows'ta kurulu Türkçe SAPI sesleri
    for name in _sapi_turkish_voices():
        out.append({"label": f"🪟 {name} (Windows)", "value": f"sapi:{name}",
                    "gender": "?"})

    # 6 sabit profil (espeak-ng) — her sistemde aynı seçenekler
    espeak_ok = bool(shutil.which("espeak-ng") or shutil.which("espeak"))
    for label, gender, variant in CATALOG:
        suffix = "" if espeak_ok else "  (espeak-ng kurulmalı)"
        out.append({"label": label + suffix, "value": f"espeak:{variant}",
                    "gender": gender})
    return out


def default_for(gender: str = "kadın") -> str:
    for label, g, variant in CATALOG:
        if g == gender:
            return f"espeak:{variant}"
    return "auto"
