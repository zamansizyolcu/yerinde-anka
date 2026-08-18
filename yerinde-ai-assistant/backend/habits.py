"""
backend/habits.py — Kullanıcı alışkanlıklarından öğrenme.

Ne öğrenir?
  • Hangi uygulamalar, hangi saat dilimlerinde açılıyor (sabah/öğle/akşam/gece)
  • En sık verilen komut türleri (rota bazında sayaç)
  • Son kullanılan uygulamalar

Nasıl kullanılır?
  • record(route, text, app)      → her istekten sonra çağrılır (kalıcı JSON)
  • prompt_summary()              → sohbet sistem promptuna eklenecek 1-2
                                    cümlelik Türkçe özet ("Kullanıcı akşamları
                                    genelde Blender açar...")
  • resolve_usual_app()           → "her zamanki uygulamayı aç" komutunda,
                                    bulunulan saat dilimine göre en olası
                                    uygulamayı döner
  • top_apps(n)                   → genel en sık n uygulama

Veri, projenin memory/habits.json dosyasında tutulur; şema sürümlüdür ve
bozuk dosyada sessizce sıfırdan başlar (asistanı asla çökertmez).
"""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from pathlib import Path

_SLOTS = ["gece", "sabah", "öğle", "akşam"]   # 0-6, 6-12, 12-18, 18-24


def _slot(hour: int) -> str:
    return _SLOTS[min(hour // 6, 3)]


class HabitLearner:
    def __init__(self, path: str | Path = "memory/habits.json",
                 max_events: int = 2000):
        self.path = Path(path)
        self.max_events = max_events
        self._lock = threading.Lock()
        self._data = self._load()

    # ── Kalıcılık ────────────────────────────────────────────────────────────
    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") == 1:
                return data
        except Exception:
            pass
        return {"version": 1, "events": []}

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._data, ensure_ascii=False),
                                 encoding="utf-8")
        except Exception:
            pass  # disk hatası asistanı düşürmesin

    # ── Öğrenme ──────────────────────────────────────────────────────────────
    def record(self, route: str, text: str = "", app: str | None = None,
               response: str = "", tool_args: dict | None = None,
               source: str = "") -> None:
        """
        Her etkileşimi EĞİTİME HAZIR biçimde kaydeder.

        Alanlar bilinçli olarak bir talimat-ayarlama (instruction tuning)
        örneğine birebir eşlenir:
            instruction → text      (kullanıcının söylediği)
            output      → response  (asistanın cevabı / araç sonucu)
            label       → route     (chat | code | vision | tool:<ad>)
            tool_args   → araç çağrısının parametreleri
        Böylece ileride kendi Türkçe dil modelini eğitmek istediğinde
        export_dataset() ile doğrudan JSONL üretebilirsin.
        """
        with self._lock:
            self._data["events"].append({
                "t": int(time.time()),
                "slot": _slot(time.localtime().tm_hour),
                "route": route,
                "app": (app or "").lower() or None,
                "text": (text or "")[:400],
                "response": (response or "")[:600],
                "tool_args": tool_args or {},
                "source": source or "",          # intent | llm | habit
                "v": 2,
            })
            self._data["events"] = self._data["events"][-self.max_events:]
            self._save()

    # ── Kendi modelini eğitmek için veri dışa aktarma ────────────────────────
    def export_dataset(self, out_path: str | Path = "memory/egitim_verisi.jsonl",
                       min_len: int = 3) -> str:
        """
        Biriken etkileşimleri JSONL olarak dışa aktarır. Her satır:
            {"instruction": "...", "input": "", "output": "...",
             "meta": {"route": "...", "tool_args": {...}, "slot": "..."}}
        Bu biçim Alpaca/ShareGPT tarzı ince ayar (LoRA/QLoRA) araçlarıyla
        doğrudan kullanılabilir — yani YERINDE kullandıkça KENDİ eğitim
        veri kümeni oluşturur.
        """
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        n = 0
        with self._lock:
            events = list(self._data["events"])
        with out.open("w", encoding="utf-8") as f:
            for e in events:
                text = (e.get("text") or "").strip()
                resp = (e.get("response") or "").strip()
                if len(text) < min_len or not resp:
                    continue
                rec = {
                    "instruction": text,
                    "input": "",
                    "output": resp,
                    "meta": {
                        "route": e.get("route", ""),
                        "tool_args": e.get("tool_args", {}),
                        "slot": e.get("slot", ""),
                        "app": e.get("app"),
                    },
                }
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
        return f"{n} örnek dışa aktarıldı: {out}"

    # ── Daha önce dışa aktarılmış veriyi geri içe aktarma ────────────────────
    def import_dataset(self, in_path: str | Path,
                       skip_duplicates: bool = True) -> str:
        """
        export_dataset() ile üretilmiş bir .jsonl dosyasını (ya da aynı
        {"instruction","input","output","meta":{...}} biçimindeki başka bir
        dosyayı — ör. başka bir bilgisayardaki YERİNDE kurulumundan alınmış)
        okuyup mevcut olay geçmişine geri ekler. Böylece birden fazla
        kurulumdan/yedeklemeden gelen veriler TEK bir eğitim kümesinde
        birleştirilebilir. Bozuk/eksik satırlar sessizce atlanır (asistanı
        çökertmez). skip_duplicates=True ise, aynı instruction+output ikilisi
        zaten varsa tekrar eklenmez.
        """
        p = Path(in_path)
        if not p.exists():
            return f"Dosya bulunamadı: {p}"

        with self._lock:
            existing_pairs = {
                (e.get("text", ""), e.get("response", ""))
                for e in self._data["events"]
            } if skip_duplicates else set()

        eklenen = 0
        atlanan = 0
        bozuk = 0
        yeni_olaylar = []
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        bozuk += 1
                        continue
                    instr = (rec.get("instruction") or "").strip()
                    out = (rec.get("output") or "").strip()
                    if not instr or not out:
                        bozuk += 1
                        continue
                    if skip_duplicates and (instr, out) in existing_pairs:
                        atlanan += 1
                        continue
                    meta = rec.get("meta") or {}
                    yeni_olaylar.append({
                        "t": int(time.time()),
                        "slot": meta.get("slot") or _slot(time.localtime().tm_hour),
                        "route": meta.get("route", ""),
                        "app": meta.get("app"),
                        "text": instr[:400],
                        "response": out[:600],
                        "tool_args": meta.get("tool_args", {}),
                        "source": "import",
                        "v": 2,
                    })
                    existing_pairs.add((instr, out))
                    eklenen += 1
        except Exception as e:
            return f"Dosya okunamadı: {e}"

        if yeni_olaylar:
            with self._lock:
                self._data["events"].extend(yeni_olaylar)
                self._data["events"] = self._data["events"][-self.max_events:]
                self._save()

        parcalar = [f"{eklenen} örnek içe aktarıldı"]
        if atlanan:
            parcalar.append(f"{atlanan} tekrar eden örnek atlandı")
        if bozuk:
            parcalar.append(f"{bozuk} bozuk/eksik satır yok sayıldı")
        return ", ".join(parcalar) + f" ({p.name})."

    def dataset_stats(self) -> dict:
        """Kaç örnek birikti, hangi rotalarda? (kendi model planlaman için)"""
        with self._lock:
            events = list(self._data["events"])
        usable = [e for e in events if (e.get("text") or "").strip()
                  and (e.get("response") or "").strip()]
        return {
            "toplam_olay": len(events),
            "egitime_uygun": len(usable),
            "rotalar": dict(Counter(e.get("route", "") for e in usable)),
            "en_sik_uygulamalar": self.top_apps(5),
        }

    # ── Sorgular ─────────────────────────────────────────────────────────────
    def top_apps(self, n: int = 3, slot: str | None = None) -> list[tuple[str, int]]:
        with self._lock:
            events = self._data["events"]
        apps = Counter(e["app"] for e in events
                       if e.get("app") and (slot is None or e.get("slot") == slot))
        return apps.most_common(n)

    def resolve_usual_app(self) -> str | None:
        """'Her zamanki uygulamayı aç' — önce şu anki saat dilimine, veri
        yoksa genel toplama bakar."""
        now_slot = _slot(time.localtime().tm_hour)
        for candidates in (self.top_apps(1, slot=now_slot), self.top_apps(1)):
            if candidates:
                return candidates[0][0]
        return None

    def route_counts(self) -> Counter:
        with self._lock:
            return Counter(e["route"] for e in self._data["events"])

    def prompt_summary(self) -> str:
        """LLM sistem promptuna eklenecek kısa alışkanlık özeti (boş olabilir)."""
        top = self.top_apps(3)
        if not top:
            return ""
        now_slot = _slot(time.localtime().tm_hour)
        slot_top = self.top_apps(1, slot=now_slot)
        parts = ["[KULLANICI ALIŞKANLIKLARI]"]
        parts.append("En sık kullandığı uygulamalar: " +
                     ", ".join(f"{a} ({c}×)" for a, c in top) + ".")
        if slot_top:
            parts.append(f"Şu an {now_slot} vakti; bu saatlerde genelde "
                         f"'{slot_top[0][0]}' kullanır.")
        parts.append("Bu bilgiyi yanıtlarını kişiselleştirmek için kullan; "
                     "kullanıcı 'her zamanki' derse bunu kastediyor olabilir.")
        return "\n".join(parts)
