"""
Ayarlar panelindeki "SES" seçici için kullanılabilir tüm çevrimdışı ses
seçeneklerini listeler: hem yerel Piper ses modelleri (voices/ klasörü)
hem de Windows'un yerleşik SAPI sesleri (genelde en az bir erkek + bir
kadın ses olur; Türkçe dil paketi kuruluysa Türkçe SAPI sesleri de çıkar).

Her seçenek şu formatta bir "value" taşır (config'e böyle yazılır):
  "piper:<tam_dosya_yolu>"   → o Piper modeli kullanılır
  "sapi:<ses_adı>"          → o Windows SAPI sesi kullanılır
  "auto"                     → otomatik (Piper varsa o, yoksa SAPI varsayılanı)
"""

from __future__ import annotations

from pathlib import Path

from actions.tts import get_available_voices as _get_sapi_voices

BASE_DIR = Path(__file__).resolve().parent.parent


def list_voice_options() -> list[dict]:
    options = [{"label": "Otomatik (Piper varsa o, yoksa sistem sesi)", "value": "auto"}]

    voices_dir = BASE_DIR / "voices"
    if voices_dir.exists():
        for onnx_path in sorted(voices_dir.glob("*.onnx")):
            label = f"🧠 {onnx_path.stem}  (Piper, nöral)"
            options.append({"label": label, "value": f"piper:{onnx_path}"})

    for voice in _get_sapi_voices():
        name = voice.get("name", "")
        if not name:
            continue
        gender = voice.get("gender", "")
        gender_tr = {"Male": "Erkek", "Female": "Kadın"}.get(gender, gender)
        culture = voice.get("culture", "")
        label = f"🔊 {name}" + (f"  ({gender_tr}, {culture})" if gender_tr else "")
        options.append({"label": label, "value": f"sapi:{name}"})

    # Ses klonlama seçenekleri (Coqui XTTS-v2) + doğal sohbet sesi

    from pathlib import Path as _P

    _own = _P(__file__).resolve().parent.parent / 'voices' / 'kendi_sesim.wav'

    if _own.exists():

        options.append({"label": "🎙 KENDİ SESİM (klonlama, XTTS-v2)",
                        "value": "xtts:" + str(_own)})

    options.append({"label": "🗣 ChatTTS (doğal sohbet)", "value": "chattts"})

    # 3 erkek + 3 kadın sabit profil (espeak-ng tabanlı, her sistemde aynı)
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
