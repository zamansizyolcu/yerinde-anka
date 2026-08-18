"""
actions/office_uno.py — LibreOffice / OnlyOffice(LibreOffice çekirdekli sürümler)
için UNO köprüsü. MS Office COM'un yapabildiklerinin çoğunu burada da yapar.

Nasıl çalışır?
  soffice bir kez "--accept=socket" ile arka planda başlatılır; sonra pyuno
  ile AÇIK belgeye bağlanılıp doğrudan komut verilir (Writer/Impress/Calc).

Gereksinim (Linux):  sudo apt install libreoffice python3-uno
             (Arch):  sudo pacman -S libreoffice-fresh python-uno
Windows'ta LibreOffice kuruluysa program içindeki python-uno kullanılır;
YERINDE önce MS Office'i dener, yoksa buraya düşer.

OnlyOffice DESKTOP: kendi otomasyon API'si dışa açık değildir. OnlyOffice'i
LibreOffice biçimlerinde kullanıyorsan dosya tabanlı işlemler (PDF'e aktarma,
içerik yazma) çalışır; canlı biçimlendirme MS Office/LibreOffice gerektirir.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"
_PORT = 2002
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0


def _soffice_binary() -> str | None:
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    if _IS_WINDOWS:
        for c in (r"C:\Program Files\LibreOffice\program\soffice.exe",
                  r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"):
            if Path(c).exists():
                return c
    return None


def _ensure_uno_importable() -> bool:
    """
    KRİTİK: python3-uno / python-uno paketi SİSTEM Python'una kurulur
    (/usr/lib/python3/dist-packages). YERINDE ise venv içinde çalıştığı için
    'import uno' başarısız oluyordu — bu yüzden LibreOffice açık olsa bile
    "belge bulamadım" deniyordu. Sistem yollarını sys.path'e ekleyip tekrar
    deniyoruz (venv'i bozmadan, yalnızca uno için).
    """
    try:
        import uno  # noqa: F401
        return True
    except ImportError:
        pass

    import glob
    import sys as _sys
    candidates = []
    for pat in ("/usr/lib/python3/dist-packages",
                "/usr/lib/python3*/site-packages",
                "/usr/lib64/python3*/site-packages",
                "/usr/lib/libreoffice/program",
                "/opt/libreoffice*/program",
                "/Applications/LibreOffice.app/Contents/Resources/python-core*/lib"):
        candidates.extend(sorted(glob.glob(pat)))
    if _IS_WINDOWS:
        candidates.extend(sorted(glob.glob(r"C:\Program Files\LibreOffice\program")))

    for path in candidates:
        if path not in _sys.path:
            _sys.path.append(path)
        try:
            import uno  # noqa: F401
            return True
        except ImportError:
            continue
    return False


def available() -> bool:
    return _ensure_uno_importable() and _soffice_binary() is not None


def _connect(timeout: float = 20.0):
    """Açık LibreOffice'e bağlanır; yoksa dinleyiciyle başlatır."""
    if not _ensure_uno_importable():
        return None
    import uno
    from com.sun.star.connection import NoConnectException

    local = uno.getComponentContext()
    resolver = local.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local)
    url = (f"uno:socket,host=localhost,port={_PORT};urp;"
           "StarOffice.ComponentContext")
    try:
        return resolver.resolve(url)
    except NoConnectException:
        pass

    exe = _soffice_binary()
    if not exe:
        return None
    kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if _IS_WINDOWS:
        kwargs["creationflags"] = _CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(
        [exe, f"--accept=socket,host=localhost,port={_PORT};urp;",
         "--norestore", "--nologo"], **kwargs)

    end = time.time() + timeout
    while time.time() < end:
        try:
            return resolver.resolve(url)
        except NoConnectException:
            time.sleep(0.5)
    return None


def _desktop(ctx):
    return ctx.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", ctx)


def _doc():
    """Açık belgeyi döner: (doc, tür) — tür: writer | impress | calc | None"""
    ctx = _connect()
    if ctx is None:
        return None, None
    doc = _desktop(ctx).getCurrentComponent()
    if doc is None:
        return None, None
    services = {
        "writer": "com.sun.star.text.TextDocument",
        "impress": "com.sun.star.presentation.PresentationDocument",
        "calc": "com.sun.star.sheet.SpreadsheetDocument",
    }
    for kind, svc in services.items():
        try:
            if doc.supportsService(svc):
                return doc, kind
        except Exception:
            continue
    return doc, None


def _rgb(rgb: tuple[int, int, int]) -> int:
    r, g, b = rgb
    return (r << 16) + (g << 8) + b


# ══ Biçimlendirme ═══════════════════════════════════════════════════════════
def format_text(action: str, rgb: tuple[int, int, int] | None = None,
                size: float | None = None) -> str | None:
    """MS Office'teki office_format ile aynı işler. Desteklenmezse None döner."""
    doc, kind = _doc()
    if doc is None:
        return None
    try:
        if kind == "writer":
            controller = doc.getCurrentController()
            sel = controller.getSelection()
            targets = []
            try:
                if sel.getCount() > 0 and sel.getByIndex(0).getString():
                    targets = [sel.getByIndex(0)]
            except Exception:
                pass
            if not targets:            # seçim yoksa tüm paragraflar
                targets = []
                it = doc.getText().createEnumeration()
                while it.hasMoreElements():
                    targets.append(it.nextElement())

            if action == "page_color" and rgb:
                doc.getStyleFamilies().getByName("PageStyles").getByName(
                    "Standard").BackColor = _rgb(rgb)
                return "LibreOffice Writer: sayfa arka planı değiştirildi."
            for t in targets:
                if action == "font_color" and rgb:
                    t.CharColor = _rgb(rgb)
                elif action == "font_size" and size:
                    t.CharHeight = size
                elif action == "font_grow":
                    t.CharHeight = float(t.CharHeight) + 2
                elif action == "font_shrink":
                    t.CharHeight = max(6.0, float(t.CharHeight) - 2)
            return "LibreOffice Writer: yazı biçimi güncellendi."

        if kind == "impress":
            slide = doc.getCurrentController().getCurrentPage()
            if action == "page_color" and rgb:
                slide.Background.FillColor = _rgb(rgb)
                slide.Background.FillStyle = 1  # SOLID
                return "LibreOffice Impress: slayt arka planı değiştirildi."
            for i in range(slide.getCount()):
                shape = slide.getByIndex(i)
                if not hasattr(shape, "setString"):
                    continue
                try:
                    if action == "font_color" and rgb:
                        shape.CharColor = _rgb(rgb)
                    elif action == "font_size" and size:
                        shape.CharHeight = size
                    elif action == "font_grow":
                        shape.CharHeight = float(shape.CharHeight) + 2
                    elif action == "font_shrink":
                        shape.CharHeight = max(6.0, float(shape.CharHeight) - 2)
                except Exception:
                    continue
            return "LibreOffice Impress: yazı biçimi güncellendi."
    except Exception as e:
        return f"LibreOffice biçimlendirme hatası: {e}"
    return None


def new_page() -> str | None:
    doc, kind = _doc()
    if doc is None:
        return None
    try:
        if kind == "impress":
            pages = doc.getDrawPages()
            idx = doc.getCurrentController().getCurrentPage().Number  # 1-tabanlı
            pages.insertNewByIndex(idx)
            doc.getCurrentController().setCurrentPage(pages.getByIndex(idx))
            return "LibreOffice Impress: yeni slayt eklendi."
        if kind == "writer":
            text = doc.getText()
            cursor = text.createTextCursorByRange(text.getEnd())
            text.insertControlCharacter(cursor, 0, False)  # PARAGRAPH_BREAK
            cursor.BreakType = 4                            # PAGE_BEFORE
            return "LibreOffice Writer: yeni sayfa eklendi."
    except Exception as e:
        return f"LibreOffice hata: {e}"
    return None


def insert_image(path: str) -> str | None:
    doc, kind = _doc()
    if doc is None:
        return None
    try:
        import uno
        url = uno.systemPathToFileUrl(str(Path(path).resolve()))
        if kind == "impress":
            page = doc.getCurrentController().getCurrentPage()
            shape = doc.createInstance("com.sun.star.drawing.GraphicObjectShape")
            page.add(shape)
            shape.GraphicURL = url
            from com.sun.star.awt import Size, Point
            shape.setSize(Size(12000, 9000))
            shape.setPosition(Point(
                int((page.Width - 12000) / 2), int((page.Height - 9000) / 2)))
            return "LibreOffice Impress: resim slayda eklendi ve ortalandı."
        if kind == "writer":
            graphic = doc.createInstance("com.sun.star.text.TextGraphicObject")
            graphic.GraphicURL = url
            graphic.Width, graphic.Height = 10000, 7500
            text = doc.getText()
            text.insertTextContent(text.getEnd(), graphic, False)
            return "LibreOffice Writer: resim belgeye eklendi."
    except Exception as e:
        return f"LibreOffice resim ekleme hatası: {e}"
    return None


def export_pdf(target: Path) -> str | None:
    doc, kind = _doc()
    if doc is None:
        return None
    try:
        import uno
        from com.sun.star.beans import PropertyValue
        filt = {"writer": "writer_pdf_Export", "impress": "impress_pdf_Export",
                "calc": "calc_pdf_Export"}.get(kind, "writer_pdf_Export")
        p = PropertyValue(); p.Name = "FilterName"; p.Value = filt
        doc.storeToURL(uno.systemPathToFileUrl(str(target)), (p,))
        return f"PDF olarak kaydedildi: {target.name} (LibreOffice)."
    except Exception as e:
        return f"LibreOffice PDF hatası: {e}"


# ══ Sunum gösterisi & efektler ══════════════════════════════════════════════
def slideshow(action: str) -> str | None:
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    try:
        pres = doc.getPresentation()
        if action == "start":
            pres.start()
            return "LibreOffice Impress: sunum tam ekran başladı."
        ctrl = pres.getController()
        if ctrl is None and action != "end":
            return "Sunum gösterisi açık değil — önce 'sunumu başlat' de."
        if action == "next":
            ctrl.gotoNextSlide(); return "Sonraki slayt."
        if action == "prev":
            ctrl.gotoPreviousSlide(); return "Önceki slayt."
        if action == "first":
            ctrl.gotoFirstSlide(); return "İlk slayda dönüldü."
        if action == "black":
            ctrl.blankScreen(0); return "Ekran karartıldı."
        if action == "end":
            if ctrl is not None:
                pres.end()
                return "Tam ekran sunumdan çıkıldı (Impress)."
            try:                      # gösteri yoksa sunum dosyasını kapat
                doc.close(True)
                return "Sunum kapatıldı (Impress)."
            except Exception as e:
                return f"Sunum kapatılamadı: {e}"
    except Exception as e:
        return f"LibreOffice sunum hatası: {e}"
    return None


# LibreOffice geçiş efektleri (FadeEffect sabitleri)
_UNO_TRANS = {"solma": 1, "itme": 22, "kaydırma": 8, "bölme": 12, "açılma": 16,
              "şerit": 30, "dama": 5, "büyütme": 40, "çevirme": 43, "küp": 44,
              "kapı": 13, "rastgele": 42}


def set_transition(name: str) -> str | None:
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    try:
        import random
        eff = _UNO_TRANS.get(name, _UNO_TRANS["rastgele"])
        if name == "rastgele":
            eff = random.choice([v for k, v in _UNO_TRANS.items() if k != "rastgele"])
        pages = doc.getDrawPages()
        for i in range(pages.getCount()):
            page = pages.getByIndex(i)
            page.TransitionType = eff
            page.TransitionDuration = 0.8
        return f"LibreOffice Impress: '{name}' geçişi tüm slaytlara eklendi."
    except Exception as e:
        return f"LibreOffice geçiş hatası: {e}"


def clear_effects(what: str = "all") -> str | None:
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    try:
        pages = doc.getDrawPages()
        for i in range(pages.getCount()):
            page = pages.getByIndex(i)
            if what in ("transitions", "all"):
                page.TransitionType = 0
            if what in ("animations", "all"):
                try:
                    node = page.AnimationNode
                    while node.hasElements():
                        node.removeChild(node.createEnumeration().nextElement())
                except Exception:
                    pass
        return "LibreOffice Impress: efektler temizlendi."
    except Exception as e:
        return f"LibreOffice temizleme hatası: {e}"


# ══ İçerik yazma (konu araştırma sonucu) ════════════════════════════════════
def write_content(data: dict) -> str | None:
    doc, kind = _doc()
    if doc is None:
        return None
    try:
        if kind == "impress":
            pages = doc.getDrawPages()
            for sec in [{"heading": data["title"],
                         "bullets": [data.get("summary", "")]}] + data["sections"]:
                pages.insertNewByIndex(pages.getCount())
                page = pages.getByIndex(pages.getCount() - 1)
                try:
                    page.Layout = 1   # başlık + içerik
                except Exception:
                    pass
                shapes = [page.getByIndex(i) for i in range(page.getCount())]
                if shapes:
                    shapes[0].setString(sec["heading"])
                if len(shapes) > 1:
                    shapes[1].setString("\n".join("• " + b for b in sec["bullets"] if b))
            return (f"'{data['title']}' konusu Impress sunumuna eklendi "
                    f"({len(data['sections'])} bölüm).")
        if kind == "writer":
            text = doc.getText()
            cur = text.createTextCursorByRange(text.getEnd())
            cur.ParaStyleName = "Heading 1"
            text.insertString(cur, data["title"], False)
            text.insertControlCharacter(cur, 0, False)
            cur.ParaStyleName = "Default Paragraph Style"
            text.insertString(cur, data.get("summary", ""), False)
            text.insertControlCharacter(cur, 0, False)
            for sec in data["sections"]:
                cur.ParaStyleName = "Heading 2"
                text.insertString(cur, sec["heading"], False)
                text.insertControlCharacter(cur, 0, False)
                cur.ParaStyleName = "List Bullet"
                for b in sec["bullets"]:
                    text.insertString(cur, b, False)
                    text.insertControlCharacter(cur, 0, False)
                cur.ParaStyleName = "Default Paragraph Style"
            return f"'{data['title']}' konusu Writer belgesine yazıldı."
    except Exception as e:
        return f"LibreOffice içerik hatası: {e}"
    return None

# ══ Sunum düzenleme: slayt sil / geri al / tasarım / animasyon ══════════════
def delete_slide() -> str | None:
    """Aktif slaydı siler (Impress)."""
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    try:
        pages = doc.getDrawPages()
        if pages.getCount() <= 1:
            return "Tek slayt kaldı — silmiyorum."
        page = doc.getCurrentController().getCurrentPage()
        idx = page.Number - 1                      # 0-tabanlı
        pages.remove(page)
        nxt = min(idx, pages.getCount() - 1)
        doc.getCurrentController().setCurrentPage(pages.getByIndex(nxt))
        return f"{idx + 1}. slayt silindi (Impress). 'Geri al' dersen geri getiririm."
    except Exception as e:
        return f"LibreOffice slayt silme hatası: {e}"


def undo() -> str | None:
    """Son işlemi geri alır (Writer/Impress/Calc)."""
    doc, _kind = _doc()
    if doc is None:
        return None
    try:
        doc.getUndoManager().undo()
        return "Son işlem geri alındı (LibreOffice)."
    except Exception as e:
        return f"LibreOffice geri alma hatası: {e}"


def random_design() -> str | None:
    """
    Sunuma rastgele bir tasarım uygular. LibreOffice'te MS Office'teki gibi
    hazır tema dosyası uygulanamıyor; bunun yerine slaytlara uyumlu bir
    RENK ŞEMASI (arka plan degradesi + başlık/metin renkleri) uygulanır.
    """
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    import random
    schemes = [
        ("Gece Mavisi", 0x0E1A2B, 0xE8F1FF, 0x4FA3FF),
        ("Orman", 0x0F1F16, 0xE2F3E8, 0x6FD08C),
        ("Amber", 0x1E1405, 0xFFF0D6, 0xF0B454),
        ("Lavanta", 0x161233, 0xEDE9FF, 0x9B8CFF),
        ("Deniz", 0x07202B, 0xDDF3F8, 0x54C7D8),
        ("Krem", 0xF5F0E6, 0x2A2A2A, 0x1F7A6F),
    ]
    name, bg, fg, accent = random.choice(schemes)
    try:
        pages = doc.getDrawPages()
        for i in range(pages.getCount()):
            page = pages.getByIndex(i)
            try:
                page.Background.FillStyle = 1      # SOLID
                page.Background.FillColor = bg
            except Exception:
                pass
            for j in range(page.getCount()):
                shape = page.getByIndex(j)
                if not hasattr(shape, "setString"):
                    continue
                try:
                    shape.CharColor = accent if j == 0 else fg
                except Exception:
                    continue
        return (f"'{name}' tasarımı uygulandı (LibreOffice Impress). "
                "Beğenmezsen 'tasarım seç' de, başkasını denerim.")
    except Exception as e:
        return f"LibreOffice tasarım hatası: {e}"


def set_animation(_name: str = "") -> str | None:
    """Impress'te öğe animasyonları uzaktan eklenemiyor — dürüst mesaj."""
    doc, kind = _doc()
    if doc is None or kind != "impress":
        return None
    return ("LibreOffice Impress öğe animasyonlarını dışarıdan eklemeye izin "
            "vermiyor (UNO bu API'yi sunmuyor). Slayt GEÇİŞLERİ çalışıyor: "
            "'geçiş ekle' de. Animasyonu Slayt > Animasyon panelinden ekleyebilirsin.")


# ══ Metin hizalama (Writer/Impress) ═════════════════════════════════════════
_ADJUST = {"align_left": 0, "align_center": 3, "align_right": 1, "align_justify": 2}


def align_text(action: str) -> str | None:
    doc, kind = _doc()
    if doc is None or action not in _ADJUST:
        return None
    val = _ADJUST[action]
    nerede = {"align_left": "sola", "align_center": "ortaya",
              "align_right": "sağa", "align_justify": "iki yana"}[action]
    try:
        if kind == "writer":
            sel = doc.getCurrentController().getSelection()
            targets = []
            try:
                if sel.getCount() > 0 and sel.getByIndex(0).getString():
                    targets = [sel.getByIndex(0)]
            except Exception:
                pass
            if not targets:
                it = doc.getText().createEnumeration()
                while it.hasMoreElements():
                    targets.append(it.nextElement())
            for t in targets:
                try:
                    t.ParaAdjust = val
                except Exception:
                    continue
            return f"Metin {nerede} hizalandı (LibreOffice Writer)."
        if kind == "impress":
            page = doc.getCurrentController().getCurrentPage()
            for i in range(page.getCount()):
                shape = page.getByIndex(i)
                if hasattr(shape, "setString"):
                    try:
                        shape.ParaAdjust = val
                    except Exception:
                        continue
            return f"Slayttaki metin {nerede} hizalandı (LibreOffice Impress)."
    except Exception as e:
        return f"LibreOffice hizalama hatası: {e}"
    return None


# ══ Calc: toplama / ortalama / aralık seçme / grafik / puan tablosu ═════════
def calc_command(action: str, value: str = "") -> str | None:
    doc, kind = _doc()
    if doc is None or kind != "calc":
        return None
    try:
        sheet = doc.getCurrentController().getActiveSheet()
        sel = doc.getCurrentController().getSelection()

        if action == "select_range":
            rng = (value or "").upper().replace(" ", "")
            cell_range = sheet.getCellRangeByName(rng)
            doc.getCurrentController().select(cell_range)
            return f"{rng} aralığı seçildi (LibreOffice Calc)."

        if action in ("sum", "average"):
            fn = "SUM" if action == "sum" else "AVERAGE"
            label = "Toplam" if action == "sum" else "Ortalama"
            addr = sel.getRangeAddress()
            col, r1, r2 = addr.StartColumn, addr.StartRow, addr.EndRow
            target = sheet.getCellByPosition(col, r2 + 1)
            first = sheet.getCellByPosition(col, r1).AbsoluteName.split(".")[-1].replace("$", "")
            last = sheet.getCellByPosition(col, r2).AbsoluteName.split(".")[-1].replace("$", "")
            target.setFormula(f"={fn}({first}:{last})")
            return f"{label} formülü eklendi (LibreOffice Calc)."

        if action == "score_table":
            headers = ["Ad Soyad", "1. Sınav", "2. Sınav", "3. Sınav",
                       "Ortalama", "Harf Notu"]
            for i, h in enumerate(headers):
                c = sheet.getCellByPosition(i, 0)
                c.setString(h)
                c.CharWeight = 150.0          # kalın
            for r in range(1, 11):
                sheet.getCellByPosition(4, r).setFormula(
                    f"=IFERROR(ROUND(AVERAGE(B{r+1}:D{r+1}),1),\"\")")
                sheet.getCellByPosition(5, r).setFormula(
                    f'=IF(E{r+1}="","",IF(E{r+1}>=85,"AA",IF(E{r+1}>=75,"BA",'
                    f'IF(E{r+1}>=65,"BB",IF(E{r+1}>=55,"CB",IF(E{r+1}>=45,"CC","FF"))))))')
            return ("Puan tablosu hazır (LibreOffice Calc): 3 sınav, otomatik "
                    "ortalama ve harf notu formülleriyle.")

        if action == "chart":
            from com.sun.star.awt import Rectangle
            charts = sheet.getCharts()
            addr = sel.getRangeAddress()
            rect = Rectangle()
            rect.X, rect.Y, rect.Width, rect.Height = 8000, 500, 14000, 9000
            name = "YERINDE_Grafik"
            if charts.hasByName(name):
                charts.removeByName(name)
            charts.addNewByName(name, rect, (addr,), True, True)
            tur = (value or "sütun").lower()
            diagram_map = {"çizgi": "com.sun.star.chart.LineDiagram",
                           "pasta": "com.sun.star.chart.PieDiagram",
                           "alan": "com.sun.star.chart.AreaDiagram",
                           "çubuk": "com.sun.star.chart.BarDiagram",
                           "sütun": "com.sun.star.chart.BarDiagram"}
            try:
                chart_doc = charts.getByName(name).getEmbeddedObject()
                diag = chart_doc.createInstance(
                    diagram_map.get(tur, "com.sun.star.chart.BarDiagram"))
                chart_doc.setDiagram(diag)
                if tur in ("sütun", "çubuk"):
                    diag.Vertical = (tur == "sütun")
            except Exception:
                pass
            return f"Seçili tablodan {tur} grafiği oluşturuldu (LibreOffice Calc)."
    except Exception as e:
        return f"LibreOffice Calc hatası: {e}"
    return None

