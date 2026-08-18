"""
actions/office_content.py — Konu araştırıp SUNUM/BELGE içeriği yazma.

"Sunuma yapay zeka konusunu ekle" / "Word'e donanım bileşenlerini yaz" dendiğinde:

  1) ÇEVRİMİÇİ: Türkçe Wikipedia REST API'sinden (anahtar gerekmez) konunun
     özeti ve bölümleri alınır.
  2) ÇEVRİMDIŞI / bulunamazsa: yerel Ollama modeli (config'teki model) ile
     içerik JSON olarak ÜRETİLİR.
  3) İçerik, açık PowerPoint'e slaytlar (başlık + madde işaretleri) ya da
     açık Word belgesine (başlık + paragraflar) olarak YAZILIR.

Windows'ta COM (PowerShell) kullanılır; içerik geçici bir JSON dosyasına
yazılıp PowerShell tarafında okunur — böylece tırnak/Türkçe karakter
kaçış sorunları yaşanmaz.
"""

from __future__ import annotations

import json
import platform
import subprocess
import tempfile
import urllib.parse
from pathlib import Path

import requests

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0
_UA = {"User-Agent": "YERINDE/1.0 (kisisel asistan)"}


def _ps(script: str, timeout: int = 30) -> tuple[bool, str]:
    """PowerShell çalıştırır; çıktı 'OK' ile başlıyorsa başarı sayılır."""
    try:
        p = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=timeout, capture_output=True, text=True,
                           creationflags=_CREATE_NO_WINDOW)
        out = (p.stdout or "").strip()
        return out.startswith("OK"), out
    except Exception as e:
        return False, str(e)


# ══ 1) İçerik toplama ═══════════════════════════════════════════════════════
def _from_wikipedia(topic: str, max_sections: int = 5) -> dict | None:
    """Türkçe Wikipedia'dan başlık + özet + bölümler (anahtarsız)."""
    try:
        t = urllib.parse.quote(topic.strip())
        s = requests.get(
            f"https://tr.wikipedia.org/api/rest_v1/page/summary/{t}",
            headers=_UA, timeout=12)
        if s.status_code != 200:
            # Arama ile en yakın başlığı bul
            r = requests.get(
                "https://tr.wikipedia.org/w/api.php",
                params={"action": "query", "list": "search", "srsearch": topic,
                        "format": "json", "srlimit": 1},
                headers=_UA, timeout=12)
            hits = r.json().get("query", {}).get("search", [])
            if not hits:
                return None
            t = urllib.parse.quote(hits[0]["title"])
            s = requests.get(
                f"https://tr.wikipedia.org/api/rest_v1/page/summary/{t}",
                headers=_UA, timeout=12)
            if s.status_code != 200:
                return None
        data = s.json()
        title = data.get("title", topic)
        summary = data.get("extract", "")

        # Bölümler (düz metin)
        sections = []
        r2 = requests.get("https://tr.wikipedia.org/w/api.php",
                          params={"action": "parse", "page": data.get("title", topic),
                                  "prop": "wikitext", "format": "json"},
                          headers=_UA, timeout=15)
        wt = r2.json().get("parse", {}).get("wikitext", {}).get("*", "")
        import re
        for m in re.finditer(r"^==\s*([^=]+?)\s*==\s*$(.*?)(?=^==|\Z)", wt, re.M | re.S):
            head = m.group(1).strip()
            if head.lower() in ("kaynakça", "ayrıca bakınız", "dış bağlantılar", "notlar"):
                continue
            body = re.sub(r"\{\{.*?\}\}|\[\[[^\]|]*\|?|\]\]|'''?|<[^>]+>|<ref.*?</ref>",
                          "", m.group(2), flags=re.S)
            lines = [l.strip("* :") for l in body.splitlines()
                     if 40 < len(l.strip()) < 300 and not l.strip().startswith("|")]
            if lines:
                sections.append({"heading": head, "bullets": lines[:4]})
            if len(sections) >= max_sections:
                break

        if not sections and summary:
            parts = [p.strip() for p in summary.split(". ") if len(p.strip()) > 30]
            sections = [{"heading": "Genel Bakış", "bullets": parts[:4]}]
        if not sections:
            return None
        return {"title": title, "summary": summary, "sections": sections,
                "source": "Vikipedi"}
    except Exception:
        return None


def _from_ollama(topic: str, n_sections: int = 5) -> dict | None:
    """Çevrimdışı: yerel Ollama modeliyle içerik üret (JSON)."""
    try:
        from app_config import get_app_config_value
        host = str(get_app_config_value("ollama_host", "http://localhost:11434")
                   or "http://localhost:11434")
        model = str(get_app_config_value("ollama_model", "llama3.1") or "llama3.1")
        prompt = (
            f"'{topic}' konusunda Türkçe bir sunum içeriği hazırla. "
            f"SADECE şu JSON'u döndür, başka hiçbir şey yazma:\n"
            '{"title": "...", "summary": "1-2 cümle", "sections": ['
            '{"heading": "...", "bullets": ["...", "...", "..."]}]}\n'
            f"{n_sections} bölüm olsun, her bölümde 3-4 kısa madde bulunsun."
        )
        r = requests.post(f"{host}/api/chat", json={
            "model": model, "stream": False,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": 0.3},
        }, timeout=240)
        raw = r.json().get("message", {}).get("content", "")
        import re
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0))
        if data.get("sections"):
            data.setdefault("title", topic)
            data["source"] = "Yerel model"
            return data
    except Exception:
        pass
    return None


def research_topic(topic: str) -> dict | None:
    """Önce internet (Vikipedi), olmazsa yerel model."""
    return _from_wikipedia(topic) or _from_ollama(topic)


# ══ 2) Office'e yazma ═══════════════════════════════════════════════════════
def _write_json(data: dict) -> Path:
    p = Path(tempfile.mktemp(prefix="yerinde-icerik-", suffix=".json"))
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def write_topic(topic: str, target: str = "auto") -> str:
    """
    topic  : "yapay zeka", "donanım bileşenleri" ...
    target : auto | powerpoint | word
    """
    topic = (topic or "").strip()
    if not topic:
        return "Hangi konuyu ekleyeyim? Örn: 'sunuma yapay zeka konusunu ekle'."

    data = research_topic(topic)
    if not data:
        return (f"'{topic}' hakkında içerik bulamadım (internet ve yerel model "
                "denendi). Konuyu biraz daha açık söyler misin?")

    if not _IS_WINDOWS:
        # Önce LibreOffice'e canlı yazmayı dene
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.write_content(data)
                if r:
                    return r
        except Exception:
            pass
        # Olmazsa: içeriği dosyaya yaz, kullanıcı kopyalasın
        from actions.code_tools import ensure_workspace_folder
        out = ensure_workspace_folder() / f"{data['title']}.txt"
        lines = [data["title"], "", data.get("summary", ""), ""]
        for sec in data["sections"]:
            lines.append(sec["heading"])
            lines += [f"  • {b}" for b in sec["bullets"]]
            lines.append("")
        out.write_text("\n".join(lines), encoding="utf-8")
        return (f"'{data['title']}' içeriği hazırlandı ({data['source']}) ve "
                f"Çalışmalarım klasörüne kaydedildi: {out.name}. Otomatik yazma "
                "şimdilik Windows/Office'te çalışıyor; bu dosyadan kopyalayabilirsin.")

    jf = _write_json(data)
    n_sec = len(data["sections"])

    ps_common = (
        f"$d = Get-Content -Raw -Encoding UTF8 '{jf}' | ConvertFrom-Json; "
    )

    # ── PowerPoint: her bölüm bir slayt (başlık + maddeler) ─────────────────
    if target in ("auto", "powerpoint"):
        pp = (
            "try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
            "$pres=$p.ActivePresentation; " + ps_common +
            "$idx = $pres.Slides.Count; "
            # Başlık slaydı
            "$s = $pres.Slides.Add($idx+1, 1); "     # ppLayoutTitle
            "$s.Shapes.Item(1).TextFrame.TextRange.Text = $d.title; "
            "if ($s.Shapes.Count -ge 2) { $s.Shapes.Item(2).TextFrame.TextRange.Text = $d.summary }; "
            "$idx = $idx + 1; "
            # İçerik slaytları
            "foreach ($sec in $d.sections) { "
            "  $sl = $pres.Slides.Add($idx+1, 2); "  # ppLayoutText
            "  $sl.Shapes.Item(1).TextFrame.TextRange.Text = $sec.heading; "
            "  $body = ($sec.bullets) -join [char]13; "
            "  $sl.Shapes.Item(2).TextFrame.TextRange.Text = $body; "
            "  $idx = $idx + 1 } ; "
            "$p.ActiveWindow.View.GotoSlide($pres.Slides.Count); "
            "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok, out = _ps(pp, timeout=90)
        if ok:
            jf.unlink(missing_ok=True)
            return (f"'{data['title']}' konusu sunuma eklendi: 1 başlık + {n_sec} "
                    f"içerik slaydı ({data['source']} kaynaklı). İstersen "
                    "'tasarım seç' ve 'geçiş ekle' diyebilirsin.")

    # ── Word: başlık + paragraflar ──────────────────────────────────────────
    if target in ("auto", "word"):
        wd = (
            "try { $w=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); "
            "$doc=$w.ActiveDocument; " + ps_common +
            "$sel=$w.Selection; $sel.EndKey(6) | Out-Null; "
            "$sel.Style = 'Heading 1'; $sel.TypeText($d.title); $sel.TypeParagraph(); "
            "$sel.Style = 'Normal'; $sel.TypeText($d.summary); $sel.TypeParagraph(); "
            "foreach ($sec in $d.sections) { "
            "  $sel.Style = 'Heading 2'; $sel.TypeText($sec.heading); $sel.TypeParagraph(); "
            "  $sel.Style = 'List Paragraph'; "
            "  foreach ($b in $sec.bullets) { $sel.TypeText([char]8226 + ' ' + $b); $sel.TypeParagraph() } ; "
            "  $sel.Style = 'Normal' } ; "
            "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok2, _ = _ps(wd, timeout=90)
        if ok2:
            jf.unlink(missing_ok=True)
            return (f"'{data['title']}' konusu belgeye yazıldı: başlık, özet ve "
                    f"{n_sec} bölüm ({data['source']} kaynaklı).")

    jf.unlink(missing_ok=True)
    return ("Açık bir PowerPoint ya da Word bulamadım — önce 'powerpoint aç' "
            "ya da 'word aç' de, sonra tekrar söyle.")
