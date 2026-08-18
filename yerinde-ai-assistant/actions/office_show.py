"""
actions/office_show.py — Sunum gösterisi + animasyon/geçiş yönetimi (PowerPoint COM).

  • Tam ekran sunum başlat/bitir, sonraki/önceki slayt
  • Slayda GEÇİŞ efekti ekle (rastgele ya da isimli), tüm slaytlara uygula
  • Şekillere/metinlere ANİMASYON ekle (giriş efektleri)
  • Eklenen animasyon ve geçişleri TEMİZLE
"""

from __future__ import annotations

import platform
import random
import subprocess

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# PowerPoint geçiş efektleri (PpEntryEffect sabitleri)
TRANSITIONS = {
    "solma":      3844,   # Fade smoothly
    "itme":       3849,   # Push
    "kaydırma":   3850,   # Wipe
    "bölme":      3852,   # Split
    "açılma":     3853,   # Reveal
    "rastgele":   513,    # Random
    "şerit":      3857,   # Ripple/strips
    "dama":       3846,   # Checkerboard
    "büyütme":    3861,   # Zoom
    "çevirme":    3862,   # Flip
    "küp":        3868,   # Cube
    "kapı":       3865,   # Doors
}

# Giriş animasyonları (MsoAnimEffect)
ANIMATIONS = {
    "belirme":    1,    # Appear
    "solarak":    10,   # Fade
    "uçarak":     2,    # Fly in
    "büyüyerek":  23,   # Grow
    "dönerek":    18,   # Spin
    "zıplayarak": 26,   # Bounce
    "yakınlaşma": 23,
    "rastgele":   None, # aşağıda seçilir
}


def _ps(script: str, timeout: int = 30) -> tuple[bool, str]:
    try:
        p = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=timeout, capture_output=True, text=True,
                           creationflags=_CREATE_NO_WINDOW)
        out = (p.stdout or "").strip()
        return out.startswith("OK"), out
    except Exception as e:
        return False, str(e)


_PP_HEAD = ("try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
            "$pres=$p.ActivePresentation; ")
_PP_TAIL = " } catch { Write-Output ('NO:'+$_.Exception.Message) }"


def _fallback_slideshow(action: str) -> str | None:
    """PowerPoint yoksa: LibreOffice (UNO) → OnlyOffice/diğer (klavye)."""
    try:
        from actions import office_uno
        if office_uno.available():
            r = office_uno.slideshow(action)
            if r:
                return r
    except Exception:
        pass
    try:
        from actions.office_keys import slideshow_keys
        return slideshow_keys(action)
    except Exception:
        return None


def slideshow(action: str) -> str:
    """action: start | next | prev | end | first | black"""
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.slideshow((action or "").lower().strip())
                if r:
                    return r
        except Exception:
            pass
        r = _fallback_slideshow((action or "").lower().strip())
        if r:
            return r
        return ("Sunuma bağlanamadım. LibreOffice için: sudo apt install "
                "libreoffice python3-uno. OnlyOffice kullanıyorsan pencereyi "
                "öne getirip tekrar dene (klavye kısayoluyla yönetiyorum).")
    action = (action or "").lower().strip()
    body = {
        # ÖNEMLİ: PowerPoint varsayılan olarak "Sunucu Görünümü"nü (Presenter View)
        # açabiliyor; o zaman ana ekranda not/önizleme paneli kalıyor, sunum tam
        # ekran görünmüyordu. Kapatıp tam ekranı birincil ekrana zorluyoruz.
        "start": ("$s = $pres.SlideShowSettings; "
                  "try { $s.ShowPresenterView = 0 } catch {}; "
                  "try { $s.ShowType = 1 } catch {}; "        # ppShowTypeSpeaker (tam ekran)
                  "try { $s.LoopUntilStopped = 0 } catch {}; "
                  "$w = $s.Run(); "
                  "try { $w.View.State = 1 } catch {}; "      # normal (karartma yok)
                  "Write-Output 'OK'"),
        "next":  ("$pres.SlideShowWindow.View.Next(); Write-Output 'OK'"),
        "prev":  ("$pres.SlideShowWindow.View.Previous(); Write-Output 'OK'"),
        "first": ("$pres.SlideShowWindow.View.First(); Write-Output 'OK'"),
        "black": ("$v=$pres.SlideShowWindow.View; "
                  "$v.State = if ($v.State -eq 3) {1} else {3}; Write-Output 'OK'"),
        # "sunumu kapat" iki anlama gelebilir:
        #   (a) tam ekran gösteriden çık, (b) sunum dosyasını/PowerPoint'i kapat.
        # Gösteri açıksa (a), değilse (b) yapılır — kullanıcı ikisinden birini
        # bekliyor ve eskiden hiçbiri olmuyordu.
        "end":   ("$closed = 'none'; "
                  "try { $w = $pres.SlideShowWindow; if ($w) { $w.View.Exit(); "
                  "      $closed = 'show' } } catch {} ; "
                  "if ($closed -eq 'none') { "
                  "  try { $pres.Saved = $true } catch {} ; "
                  "  $pres.Close(); "
                  "  try { if ($p.Presentations.Count -eq 0) { $p.Quit() } } catch {} ; "
                  "  $closed = 'file' } ; "
                  "Write-Output ('OK:' + $closed)"),
    }.get(action)
    if not body:
        return "Sunum komutunu anlamadım (başlat / sonraki / önceki / bitir)."

    ok, out = _ps(_PP_HEAD + body + _PP_TAIL)
    if ok:
        if action == "end":
            return ("Tam ekran sunumdan çıkıldı." if out.strip().endswith("show")
                    else "Sunum kapatıldı.")
        return {"start": "Sunum tam ekran başladı.", "next": "Sonraki slayt.",
                "prev": "Önceki slayt.", "first": "İlk slayda dönüldü.",
                "black": "Ekran karartıldı/açıldı."}[action]
    if action != "start" and "SlideShowWindow" in out:
        return "Sunum gösterisi açık değil — önce 'sunumu başlat' de."

    # PowerPoint yoksa: LibreOffice (UNO) → OnlyOffice/diğer (klavye kısayolu)
    return _fallback_slideshow(action) or "Açık bir sunum bulamadım."


def _fallback_slide_edit(action: str) -> str | None:
    try:
        from actions import office_uno
        if office_uno.available():
            r = office_uno.delete_slide() if action == "delete" else office_uno.undo()
            if r:
                return r
    except Exception:
        pass
    try:
        from actions.office_keys import edit_keys
        return edit_keys(action)
    except Exception:
        return None


def slide_edit(action: str) -> str:
    """action: delete (bu slaydı sil) | undo (son işlemi geri al)"""
    if not _IS_WINDOWS:
        return _fallback_slide_edit((action or "").lower().strip()) or \
            "Sunuma bağlanamadım (LibreOffice/OnlyOffice açık mı?)."
    action = (action or "").lower().strip()
    if action == "delete":
        body = ("$sl = $p.ActiveWindow.View.Slide; $i = $sl.SlideIndex; "
                "$sl.Delete(); "
                "if ($pres.Slides.Count -ge 1) { "
                "  $t = [Math]::Min($i, $pres.Slides.Count); "
                "  $p.ActiveWindow.View.GotoSlide($t) } ; "
                "Write-Output ('OK:' + $i)")
        ok, out = _ps(_PP_HEAD + body + _PP_TAIL)
        if ok:
            idx = out.split("OK:", 1)[-1].strip()
            return (f"{idx}. slayt silindi. Yanlışlıkla sildiysen 'geri al' de, "
                    "hemen geri getiririm.")
        return _fallback_slide_edit("delete") or "Silinecek slayt bulamadım — sunum açık mı?"

    if action == "undo":
        # PowerPoint COM'da Undo yok → uygulamaya Ctrl+Z gönder
        try:
            from actions.keyboard_control import press_key
        except Exception:
            return "Geri alma aracı yüklenemedi."
        act = ("try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
               "$p.Activate(); Write-Output 'OK' } catch { Write-Output 'NO' }")
        _ps(act)
        r = press_key("undo")
        return ("Son işlem geri alındı (silinen slayt geri geldi)."
                if "basıldı" in r else f"Geri alınamadı — {r}")

    return "Slayt komutunu anlamadım (sil / geri al)."


def add_transition(name: str = "rastgele", all_slides: bool = True) -> str:
    """Slayt geçiş efekti ekler (varsayılan: tüm slaytlara)."""
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.set_transition((name or "rastgele").lower().strip())
                if r:
                    return r
        except Exception:
            pass
        return "Impress'e bağlanamadım (libreoffice + python3-uno kurulu mu?)."
    key = (name or "rastgele").lower().strip()
    if key not in TRANSITIONS:
        key = "rastgele"
    effect = TRANSITIONS[key]
    if key == "rastgele":
        effect = random.choice([v for k, v in TRANSITIONS.items() if k != "rastgele"])

    scope = "$pres.Slides" if all_slides else "@($p.ActiveWindow.View.Slide)"
    body = (f"foreach ($s in {scope}) {{ "
            f"$s.SlideShowTransition.EntryEffect = {effect}; "
            "$s.SlideShowTransition.Duration = 0.8; "
            "$s.SlideShowTransition.AdvanceOnClick = $true } ; "
            "Write-Output 'OK'")
    ok, _ = _ps(_PP_HEAD + body + _PP_TAIL, timeout=45)
    if ok:
        nerede = "tüm slaytlara" if all_slides else "bu slayda"
        return f"'{key}' geçiş efekti {nerede} eklendi."
    return "Açık bir sunum bulamadım."


def add_animation(name: str = "solarak", all_slides: bool = True) -> str:
    """Slayttaki şekillere giriş animasyonu ekler."""
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.set_animation(name)
                if r:
                    return r
        except Exception:
            pass
        return ("Öğe animasyonları LibreOffice/OnlyOffice'te dışarıdan eklenemiyor. "
                "Slayt GEÇİŞLERİ çalışıyor: 'geçiş ekle' de.")
    key = (name or "solarak").lower().strip()
    effect = ANIMATIONS.get(key)
    if effect is None:
        effect = random.choice([v for v in ANIMATIONS.values() if v])

    scope = "$pres.Slides" if all_slides else "@($p.ActiveWindow.View.Slide)"
    body = (f"foreach ($s in {scope}) {{ "
            "foreach ($sh in $s.Shapes) { "
            f"  $null = $s.TimeLine.MainSequence.AddEffect($sh, {effect}, 0, 1) "
            "} } ; Write-Output 'OK'")
    ok, _ = _ps(_PP_HEAD + body + _PP_TAIL, timeout=60)
    if ok:
        nerede = "tüm slaytlardaki" if all_slides else "bu slayttaki"
        return f"'{key}' animasyonu {nerede} öğelere eklendi."
    return "Açık bir sunum bulamadım (ya da slaytta öğe yok)."


def clear_effects(what: str = "all") -> str:
    """what: animations | transitions | all — eklenen efektleri temizler."""
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.clear_effects((what or "all").lower().strip())
                if r:
                    return r
        except Exception:
            pass
        return "Impress'e bağlanamadım (libreoffice + python3-uno kurulu mu?)."
    what = (what or "all").lower().strip()
    parts = []
    if what in ("animations", "all"):
        parts.append("foreach ($s in $pres.Slides) { "
                     "$seq = $s.TimeLine.MainSequence; "
                     "for ($i = $seq.Count; $i -ge 1; $i--) { $seq.Item($i).Delete() } }")
    if what in ("transitions", "all"):
        parts.append("foreach ($s in $pres.Slides) { "
                     "$s.SlideShowTransition.EntryEffect = 0 }")   # ppEffectNone
    body = " ; ".join(parts) + " ; Write-Output 'OK'"
    ok, _ = _ps(_PP_HEAD + body + _PP_TAIL, timeout=60)
    if ok:
        label = {"animations": "Animasyonlar", "transitions": "Geçişler",
                 "all": "Tüm animasyon ve geçişler"}[what]
        return f"{label} temizlendi."
    return "Açık bir sunum bulamadım."
