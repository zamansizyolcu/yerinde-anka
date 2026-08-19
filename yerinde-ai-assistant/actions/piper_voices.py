"""
Ayarlar panelindeki "SES" seçici için kullanılabilir tüm çevrimdışı ses
seçeneklerini listeler: hem yerel Piper ses modelleri (voices/ klasörü)
hem de espeak-ng ses varyantları.

Her seçenek şu formatta bir "value" taşır (config'e böyle yazılır):
  "piper:<tam_dosya_yolu>"   → o Piper modeli kullanılır
  "espeak:<varyant>"         → o espeak-ng ses varyantı
  "auto"                     → otomatik (Piper varsa o, yoksa espeak-ng)
"""

from __future__ import annotations

import json
from pathlib import Path

from actions.tts import get_available_voices as _get_sapi_voices

BASE_DIR = Path(__file__).resolve().parent.parent


def load_voices() -> list[dict]:
    """
    voices/ klasöründeki .onnx + .onnx.json çiftlerini yükler.
    Her model için dict döner: {name, path, config, sample_rate}
    """
    voices = []
    voices_dir = BASE_DIR / "voices"
    if not voices_dir.exists():
        return voices

    for onnx_path in sorted(voices_dir.glob("*.onnx")):
        json_path = onnx_path.with_suffix(".onnx.json")
        sample_rate = 22050  # varsayılan
        config = {}
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                sample_rate = (config.get("audio") or {}).get("sample_rate", 22050)
            except (json.JSONDecodeError, OSError):
                pass
        voices.append({
            "name": onnx_path.stem,
            "path": str(onnx_path),
            "config": config,
            "sample_rate": sample_rate,
        })
    return voices


def list_voice_options() -> list[dict]:
    options = [{"label": "Otomatik (Piper varsa o, yoksa sistem sesi)", "value": "auto"}]

    # Piper ses modelleri — JSON'dan sample_rate ile
    for v in load_voices():
        label = f"🧠 {v['name']}  ({v['sample_rate']}Hz, Piper nöral)"
        options.append({"label": label, "value": f"piper:{v['path']}"})

    # espeak-ng ses varyantları (Linux)
    for line in _get_sapi_voices():
        if not line or not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        variant = parts[1]
        label = f"🔊 {variant}  (sistem sesi)"
        options.append({"label": label, "value": f"espeak:{variant}"})

    # Ses klonlama (XTTS-v2)
    _own = BASE_DIR / "voices" / "kendi_sesim.wav"
    if _own.exists():
        options.append({"label": "🎙 KENDİ SESİM (klonlama, XTTS-v2)",
                        "value": f"xtts:{_own}"})

    options.append({"label": "🗣 ChatTTS (doğal sohbet)", "value": "chattts"})

    # 3 erkek + 3 kadın sabit profil (espeak-ng tabanlı)
    try:
        from actions.voice_catalog import CATALOG
        import shutil as _sh
        _ok = bool(_sh.which("espeak-ng") or _sh.which("espeak"))
        for _label, _g, _variant in CATALOG:
            options.append({"label": _label + ("" if _ok else "  (espeak-ng gerekli)"),
                            "value": f"espeak:{_variant}"})
    except Exception:
        pass

    return options
