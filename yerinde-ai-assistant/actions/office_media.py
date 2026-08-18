"""
actions/office_media.py — Office'e resim ekleme, internetten resim indirme,
Word → PDF, Excel sesli komutları (toplama, otomatik puan tablosu).

Windows'ta açık Office uygulamalarına COM (PowerShell GetActiveObject) ile
bağlanır. Linux'ta (LibreOffice) bu uzaktan-komut API'si olmadığı için
dürüst bir yönlendirme mesajı döner — resim İNDİRME kısmı her platformda çalışır.
"""

from __future__ import annotations

import platform
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

import requests

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

_UA = {"User-Agent": "YERINDE/1.0 (kisisel asistan; egitim amacli)"}


def _ps(script: str, timeout: int = 30) -> tuple[bool, str]:
    try:
        p = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=timeout, capture_output=True, text=True,
                           creationflags=_CREATE_NO_WINDOW)
        out = (p.stdout or "").strip()
        return out.startswith("OK"), out
    except Exception as e:
        return False, str(e)


# ══ İnternetten resim indirme (API anahtarı GEREKMEZ) ═══════════════════════
def download_image(query: str) -> Path | None:
    """
    Openverse (açık lisanslı görseller) → Wikimedia Commons sırasıyla dener.
    İkisi de anahtarsızdır ve serbestçe kullanılabilir görseller döndürür.
    """
    q = urllib.parse.quote(query.strip())

    # 1) Openverse
    try:
        r = requests.get(
            f"https://api.openverse.org/v1/images/?q={q}&page_size=5&license_type=commercial",
            headers=_UA, timeout=15)
        if r.status_code == 200:
            for item in r.json().get("results", []):
                url = item.get("url")
                if url:
                    img = requests.get(url, headers=_UA, timeout=20)
                    if img.status_code == 200 and len(img.content) > 4000:
                        return _save_tmp(img.content, url)
    except Exception:
        pass

    # 2) Wikimedia Commons
    try:
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               f"&generator=search&gsrnamespace=6&gsrlimit=5&gsrsearch={q}"
               "&prop=imageinfo&iiprop=url&iiurlwidth=1280")
        r = requests.get(api, headers=_UA, timeout=15)
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            for info in page.get("imageinfo", []):
                url = info.get("thumburl") or info.get("url")
                if url and url.lower().endswith((".jpg", ".jpeg", ".png")):
                    img = requests.get(url, headers=_UA, timeout=20)
                    if img.status_code == 200 and len(img.content) > 4000:
                        return _save_tmp(img.content, url)
    except Exception:
        pass
    return None


def _save_tmp(data: bytes, url: str) -> Path:
    ext = ".png" if url.lower().endswith(".png") else ".jpg"
    path = Path(tempfile.mktemp(prefix="yerinde-img-", suffix=ext))
    path.write_bytes(data)
    return path


# ══ Office'e resim ekleme ═══════════════════════════════════════════════════
def insert_image(source: str) -> str:
    """
    source: dosya yolu VEYA arama sorgusu ("kedi", "İstanbul manzarası").
    Açık PowerPoint slaydına, o yoksa açık Word belgesine ekler.
    """
    source = (source or "").strip()
    if not source:
        return "Hangi resmi ekleyeyim? Örn: 'sunuma kedi resmi ekle'."

    path = Path(source)
    downloaded = False
    if not path.exists():
        img = download_image(source)
        if img is None:
            return (f"'{source}' için internette uygun resim bulamadım. "
                    "Farklı bir kelime dener misin?")
        path, downloaded = img, True

    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.insert_image(str(path))
                if r:
                    return r + (" (İnternetten indirdim.)" if downloaded else "")
        except Exception:
            pass
        return (f"Resim indirildi ({path}) ama belgeye ekleyemedim — LibreOffice "
                "açık mı? Kurulum: sudo apt install libreoffice python3-uno")

    # 1) PowerPoint (aktif slayda ortalanmış, sığdırılmış)
    pp = (
        "try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
        "$sl=$p.ActiveWindow.View.Slide; $pres=$p.ActivePresentation; "
        f"$sh=$sl.Shapes.AddPicture('{path}',0,1,0,0); "
        "$sw=$pres.PageSetup.SlideWidth; $sh2=$pres.PageSetup.SlideHeight; "
        "$max_w=$sw*0.8; $max_h=$sh2*0.7; "
        "$r=[Math]::Min($max_w/$sh.Width, $max_h/$sh.Height); "
        "if ($r -lt 1) { $sh.Width=$sh.Width*$r; $sh.Height=$sh.Height*$r }; "
        "$sh.Left=($sw-$sh.Width)/2; $sh.Top=($sh2-$sh.Height)/2; "
        "Write-Output 'OK-PP' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
    )
    ok, _ = _ps(pp)
    if ok:
        return (f"Resim sunuma eklendi ve slayda ortalandı."
                + (" (İnternetten indirdim.)" if downloaded else ""))

    # 2) Word (imlecin olduğu yere)
    wd = (
        "try { $w=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); "
        f"$null=$w.Selection.InlineShapes.AddPicture('{path}'); "
        "Write-Output 'OK-WORD' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
    )
    ok2, _ = _ps(wd)
    if ok2:
        return ("Resim belgeye eklendi."
                + (" (İnternetten indirdim.)" if downloaded else ""))

    return ("Açık bir PowerPoint ya da Word bulamadım. Önce belgeyi aç "
            f"('word aç' / 'powerpoint aç'), sonra tekrar dene. Resim burada: {path}")


# ══ Word → PDF ══════════════════════════════════════════════════════════════
def word_export_pdf(name: str = "") -> str:
    """Açık Word belgesini 'Çalışmalarım' klasörüne PDF olarak kaydeder."""
    from actions.code_tools import ensure_workspace_folder
    if not _IS_WINDOWS:
        import time as _t
        folder = ensure_workspace_folder()
        target = folder / f"{(name or 'belge').strip() or 'belge'} {_t.strftime('%Y-%m-%d %H.%M')}.pdf"
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.export_pdf(target)
                if r:
                    return r
        except Exception:
            pass
        return ("PDF'e aktaramadım — LibreOffice açık mı? "
                "Kurulum: sudo apt install libreoffice python3-uno")
    folder = ensure_workspace_folder()
    base = (name or "belge").strip().replace("/", "-") or "belge"
    target = folder / f"{base} {time.strftime('%Y-%m-%d %H.%M')}.pdf"
    script = (
        "try { $w=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); "
        f"$w.ActiveDocument.ExportAsFixedFormat('{target}', 17); "
        "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
    )
    ok, out = _ps(script, timeout=60)
    if ok:
        return f"Belge PDF olarak kaydedildi: {target.name} (Çalışmalarım klasörü)."

    # Word yoksa: açık SUNUMU PDF'e aktar
    pp = (
        "try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
        f"$p.ActivePresentation.SaveAs('{target}', 32); "   # ppSaveAsPDF
        "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
    )
    ok2, _ = _ps(pp, timeout=90)
    if ok2:
        return f"Sunum PDF olarak kaydedildi: {target.name} (Çalışmalarım klasörü)."
    return ("PDF'e aktaramadım — açık bir Word belgesi ya da PowerPoint sunumu var mı?")


# ══ Excel sesli komutları ═══════════════════════════════════════════════════
def excel_command(action: str, value: str = "") -> str:
    """
    action:
      sum          → seçili aralığın altına TOPLA formülü ekler ("topla")
      average      → ortalama ekler
      score_table  → hazır PUAN TABLOSU kurar (ad, 3 sınav, ortalama, harf notu)
    """
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.calc_command((action or "").lower().strip(), value)
                if r:
                    return r
        except Exception:
            pass
        return ("Calc'a bağlanamadım — LibreOffice Calc açık mı? "
                "Kurulum: sudo apt install libreoffice python3-uno")
    action = (action or "").lower().strip()

    if action in ("sum", "average"):
        fn = "SUM" if action == "sum" else "AVERAGE"
        label = "Toplam" if action == "sum" else "Ortalama"
        script = (
            "try { $e=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); "
            "$sel=$e.Selection; $ws=$e.ActiveSheet; "
            "$r1=$sel.Row; $c1=$sel.Column; $rows=$sel.Rows.Count; "
            "$target=$ws.Cells($r1+$rows, $c1); "
            "$first=$ws.Cells($r1,$c1).Address($false,$false); "
            "$last=$ws.Cells($r1+$rows-1,$c1).Address($false,$false); "
            f"$target.Formula = '={fn}(' + $first + ':' + $last + ')'; "
            "$target.Font.Bold = $true; "
            "Write-Output ('OK:' + $target.Address($false,$false)) } "
            "catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok, out = _ps(script)
        if ok:
            cell = out.split("OK:", 1)[-1].strip()
            return f"{label} formülü {cell} hücresine eklendi."
        return ("Excel'de sayıları seçili hale getirip tekrar söyler misin? "
                "(Açık bir Excel dosyası olmalı.)")

    if action == "score_table":
        script = (
            "try { $e=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); "
            "$ws=$e.ActiveSheet; "
            "$h=@('Ad Soyad','1. Sinav','2. Sinav','3. Sinav','Ortalama','Harf Notu'); "
            "for ($i=0; $i -lt $h.Count; $i++) { "
            "  $c=$ws.Cells(1, $i+1); $c.Value2=$h[$i]; $c.Font.Bold=$true; "
            "  $c.Interior.Color = 15917529 } ; "
            "for ($r=2; $r -le 11; $r++) { "
            "  $ws.Cells($r,5).Formula = '=IFERROR(ROUND(AVERAGE(B' + $r + ':D' + $r + '),1),\"\")'; "
            "  $ws.Cells($r,6).Formula = '=IF(E' + $r + '=\"\",\"\",IF(E' + $r + '>=85,\"AA\",IF(E' + $r + '>=75,\"BA\",IF(E' + $r + '>=65,\"BB\",IF(E' + $r + '>=55,\"CB\",IF(E' + $r + '>=45,\"CC\",\"FF\"))))))' } ; "
            "$ws.Range('A1:F1').Borders.LineStyle = 1; "
            "$ws.Columns('A:F').AutoFit() | Out-Null; "
            "$ws.Cells(2,1).Select(); "
            "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok, out = _ps(script, timeout=45)
        if ok:
            return ("Puan tablosu hazır: Ad Soyad, 3 sınav, otomatik ortalama ve "
                    "harf notu (AA-FF) formülleriyle. Sadece isim ve notları yaz — "
                    "gerisini kendisi hesaplar.")
        return "Excel açık değil gibi görünüyor — önce 'excel aç' de."

    if action == "chart":
        # Seçili tablodan grafik: value = sütun|çizgi|pasta (varsayılan sütun)
        kind = {"sütun": 51, "sutun": 51, "bar": 57, "çizgi": 4, "cizgi": 4,
                "pasta": 5, "alan": 1, "dağılım": -4169}.get(
                    (value or "").lower().strip(), 51)
        script = (
            "try { $e=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); "
            "$ws=$e.ActiveSheet; $sel=$e.Selection; "
            "if ($sel.Cells.Count -lt 2) { $sel = $ws.UsedRange }; "
            "$co = $ws.Shapes.AddChart2(-1, " + str(kind) + "); "
            "$co.Chart.SetSourceData($sel); "
            "$co.Chart.HasTitle = $true; "
            "$co.Chart.ChartTitle.Text = 'Grafik'; "
            "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok, out = _ps(script, timeout=45)
        if ok:
            adi = {51: "sütun", 57: "çubuk", 4: "çizgi", 5: "pasta",
                   1: "alan", -4169: "dağılım"}[kind]
            return (f"Seçili tablodan {adi} grafiği oluşturuldu. Başka tür istersen "
                    "'pasta grafik oluştur' diyebilirsin.")
        return "Excel açık mı? Grafik için önce tabloyu seç, sonra söyle."

    if action == "select_range":
        # value: "A1:D10" ya da "A1 D10"
        rng = (value or "").upper().replace(" ", ":").replace("::", ":").strip()
        import re as _re
        if not _re.fullmatch(r"[A-Z]{1,3}\d{1,7}:[A-Z]{1,3}\d{1,7}", rng):
            return "Aralığı 'A1'den D10'a kadar seç' gibi söyler misin?"
        script = (
            "try { $e=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application'); "
            f"$e.ActiveSheet.Range('{rng}').Select(); "
            "Write-Output 'OK' } catch { Write-Output ('NO:'+$_.Exception.Message) }"
        )
        ok, _ = _ps(script)
        return f"{rng} aralığı seçildi." if ok else "Excel açık değil gibi görünüyor."

    return "Bilmediğim bir Excel komutu."

# ══ Eklenen resmi ayarlama (döndür / boyutlandır / hizala) ══════════════════
def image_adjust(action: str, value: str = "") -> str:
    """
    Son eklenen (ya da seçili) resmi ayarlar.
      rotate_right / rotate_left  → 90° döndür (value ile derece verilebilir)
      flip_h / flip_v             → yatay / dikey aynala
      bigger / smaller            → %20 büyüt / küçült
      center                      → slaytta ortala
      left / right / top / bottom → kenara hizala
      reset                       → döndürmeyi sıfırla
    """
    if not _IS_WINDOWS:
        return ("Resim ayarlama şimdilik Windows/Microsoft Office ile çalışıyor. "
                "LibreOffice'te resmi seçip köşe tutamaçlarıyla ayarlayabilirsin.")

    action = (action or "").lower().strip()
    try:
        deg = float(value)
    except Exception:
        deg = 90.0

    body = {
        "rotate_right": f"$sh.Rotation = $sh.Rotation + {deg}",
        "rotate_left":  f"$sh.Rotation = $sh.Rotation - {deg}",
        "reset":        "$sh.Rotation = 0",
        "flip_h":       "$sh.Flip(0)",
        "flip_v":       "$sh.Flip(1)",
        "bigger":       "$sh.Width = $sh.Width * 1.2; $sh.Height = $sh.Height * 1.2",
        "smaller":      "$sh.Width = $sh.Width * 0.8; $sh.Height = $sh.Height * 0.8",
        "center":       ("$sh.Left = ($pres.PageSetup.SlideWidth - $sh.Width)/2; "
                         "$sh.Top = ($pres.PageSetup.SlideHeight - $sh.Height)/2"),
        "left":         "$sh.Left = 20",
        "right":        "$sh.Left = $pres.PageSetup.SlideWidth - $sh.Width - 20",
        "top":          "$sh.Top = 20",
        "bottom":       "$sh.Top = $pres.PageSetup.SlideHeight - $sh.Height - 20",
    }.get(action)
    if not body:
        return ("Bu resim ayarını bilmiyorum. Örnek: 'resmi döndür', "
                "'resmi büyüt', 'resmi ortala', 'resmi aynala'.")

    # PowerPoint: seçili şekil yoksa slayttaki SON resmi kullan
    pp = (
        "try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
        "$pres=$p.ActivePresentation; $sl=$p.ActiveWindow.View.Slide; "
        "$sh = $null; "
        "try { if ($p.ActiveWindow.Selection.Type -eq 2) "
        "{ $sh = $p.ActiveWindow.Selection.ShapeRange.Item(1) } } catch {}; "
        "if (-not $sh) { $pics = @($sl.Shapes | Where-Object { $_.Type -eq 13 -or $_.Type -eq 11 }); "
        "if ($pics.Count -gt 0) { $sh = $pics[$pics.Count-1] } }; "
        "if (-not $sh) { Write-Output 'NO:resim yok'; exit }; "
        f"{body}; Write-Output 'OK-PP' }} catch {{ Write-Output ('NO:'+$_.Exception.Message) }}"
    )
    ok, out = _ps(pp)
    if ok:
        label = {
            "rotate_right": f"{deg:g}° sağa döndürüldü", "rotate_left": f"{deg:g}° sola döndürüldü",
            "reset": "döndürme sıfırlandı", "flip_h": "yatay aynalandı", "flip_v": "dikey aynalandı",
            "bigger": "%20 büyütüldü", "smaller": "%20 küçültüldü", "center": "ortalandı",
            "left": "sola hizalandı", "right": "sağa hizalandı",
            "top": "yukarı hizalandı", "bottom": "aşağı hizalandı",
        }[action]
        return f"Resim {label}."

    # Word: satır içi resim (InlineShape) — döndürme desteklemez, boyut çalışır
    if action in ("bigger", "smaller"):
        f = 1.2 if action == "bigger" else 0.8
        wd = ("try { $w=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); "
              "$d=$w.ActiveDocument; $n=$d.InlineShapes.Count; "
              "if ($n -lt 1) { Write-Output 'NO:resim yok'; exit }; "
              "$sh=$d.InlineShapes.Item($n); "
              f"$sh.Width = $sh.Width * {f}; $sh.Height = $sh.Height * {f}; "
              "Write-Output 'OK-WORD' } catch { Write-Output ('NO:'+$_.Exception.Message) }")
        ok2, _ = _ps(wd)
        if ok2:
            return f"Resim %{20} {'büyütüldü' if action == 'bigger' else 'küçültüldü'} (Word)."

    return ("Ayarlayacak resim bulamadım — açık sunumda/belgede resim var mı? "
            "(Resmi tıklayıp seçersen doğrudan onu ayarlarım.)")

