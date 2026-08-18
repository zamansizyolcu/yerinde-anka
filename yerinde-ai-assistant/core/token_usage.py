"""
Gemini Live API oturumlarından dönen usage_metadata'yı biriktirip GÜNLÜK bir
kullanım sayacı tutar.

ÖNEMLİ SINIRLAMA: Google'ın Gemini API'si, ücretsiz kotanın ne kadarının
KALDIĞINI döndüren herkese açık bir uç nokta SUNMUYOR (bkz.
ai.google.dev/gemini-api/docs/rate-limits — kota/hız sınırları sadece
AI Studio / Cloud Console panelinde görünür, API üzerinden sorgulanamaz).
Bu yüzden burada "kalan" değil, Google'ın HER YANITLA birlikte gönderdiği
gerçek usage_metadata'dan biriktirilen "bugüne kadar KULLANILAN" token
sayısı tutuluyor — tahmini bir sayı değil, Google'ın kendi bildirdiği rakam.
"""

from __future__ import annotations

import datetime

from app_config import get_app_config_value, save_app_config

_CONFIG_KEY = "gemini_usage_today"


def _today() -> str:
    return datetime.date.today().isoformat()


def record_usage(total_tokens: int | None) -> None:
    """Bir Live API yanıtından gelen usage_metadata.total_token_count'u
    bugünün sayacına ekler. Gün değiştiyse sayaç otomatik sıfırlanır."""
    if not total_tokens:
        return
    data = get_today_usage()
    data["tokens"] = int(data.get("tokens", 0)) + int(total_tokens)
    data["turns"] = int(data.get("turns", 0)) + 1
    save_app_config({_CONFIG_KEY: data})


def get_today_usage() -> dict:
    """{'date': 'YYYY-MM-DD', 'tokens': int, 'turns': int} döner.
    Kayıtlı veri dünden kalmaysa sıfırlanmış halde döner (henüz kaydedilmez;
    kaydetme işini record_usage yapar)."""
    today = _today()
    data = get_app_config_value(_CONFIG_KEY, {}) or {}
    if not isinstance(data, dict) or data.get("date") != today:
        return {"date": today, "tokens": 0, "turns": 0}
    return {
        "date": today,
        "tokens": int(data.get("tokens", 0)),
        "turns": int(data.get("turns", 0)),
    }


def format_today_usage() -> str:
    d = get_today_usage()
    tok = d["tokens"]
    tok_str = f"{tok/1000:.1f}b" if tok >= 1000 else str(tok)
    return f"Bugün ~{tok_str} token kullanıldı ({d['turns']} tur)"
