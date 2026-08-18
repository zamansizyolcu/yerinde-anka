"""
actions/office_format.py — AÇIK Word/PowerPoint belgesini sesle biçimlendirme.

Windows'ta çalışan Office'e COM ile bağlanır (PowerShell GetActiveObject):
  • yazı rengi / yazı boyutu (seçili metin varsa ona, yoksa tüm belgeye)
  • sayfa / slayt arka plan rengi
Linux'ta (LibreOffice) bu API yok — dürüst bir yönlendirme mesajı döner.
"""

from __future__ import annotations

import platform
import subprocess

_IS_WINDOWS = platform.system() == "Windows"
_CREATE_NO_WINDOW = 0x08000000 if _IS_WINDOWS else 0

# Türkçe renk adları → (R,G,B)
COLORS_TR = {
    "kırmızı": (255, 0, 0), "kirmizi": (255, 0, 0),
    "mavi": (0, 0, 255), "yeşil": (0, 176, 80), "yesil": (0, 176, 80),
    "sarı": (255, 255, 0), "sari": (255, 255, 0),
    "siyah": (0, 0, 0), "beyaz": (255, 255, 255),
    "mor": (128, 0, 128), "turuncu": (255, 165, 0),
    "pembe": (255, 105, 180), "gri": (128, 128, 128),
    "lacivert": (0, 0, 128), "kahverengi": (139, 69, 19),
    "turkuaz": (0, 206, 209), "altın": (255, 215, 0), "altin": (255, 215, 0),
    # ── Genişletilmiş palet ────────────────────────────────────────────────
    "bordo": (128, 0, 32), "vişne": (183, 30, 62), "kiremit": (178, 63, 44),
    "somon": (250, 128, 114), "şeftali": (255, 203, 164), "krem": (255, 253, 208),
    "bej": (245, 222, 179), "kum": (194, 178, 128), "hardal": (225, 173, 1),
    "limon": (255, 247, 0), "fıstık": (159, 189, 0), "zeytin": (128, 128, 0),
    "çimen": (124, 252, 0), "nane": (62, 180, 137), "petrol": (0, 128, 128),
    "camgöbeği": (0, 255, 255), "bebek mavisi": (137, 207, 240),
    "gökyüzü": (135, 206, 235), "kobalt": (0, 71, 171), "indigo": (75, 0, 130),
    "eflatun": (150, 111, 214), "lila": (200, 162, 200), "lavanta": (181, 126, 220),
    "fuşya": (255, 0, 255), "gül kurusu": (194, 122, 122), "şarap": (114, 47, 55),
    "çikolata": (123, 63, 0), "bakır": (184, 115, 51), "bronz": (205, 127, 50),
    "gümüş": (192, 192, 192), "antrasit": (41, 41, 41), "kömür": (54, 69, 79),
    "duman": (112, 128, 144), "buz": (240, 248, 255), "fildişi": (255, 255, 240),
    "açık gri": (211, 211, 211), "koyu gri": (64, 64, 64),
    "açık mavi": (173, 216, 230), "koyu mavi": (0, 0, 139),
    "açık yeşil": (144, 238, 144), "koyu yeşil": (0, 100, 0),
    "açık kırmızı": (255, 102, 102), "koyu kırmızı": (139, 0, 0),
    "mercan": (255, 127, 80), "kayısı": (251, 206, 177), "amber": (255, 191, 0),
    "yosun": (138, 154, 91), "haki": (189, 183, 107), "asker yeşili": (75, 83, 32),
    "denim": (21, 96, 189), "safir": (15, 82, 186), "menekşe": (127, 0, 255),
    "orkide": (218, 112, 214), "pudra": (255, 204, 204), "toz pembe": (255, 192, 203),
}


def _rgb_int(name: str) -> int | None:
    rgb = COLORS_TR.get((name or "").lower().strip())
    if not rgb:
        return None
    r, g, b = rgb
    return r + g * 256 + b * 65536   # Office RGB (BGR sıralı tamsayı)


def _ps(script: str) -> tuple[bool, str]:
    try:
        p = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                           timeout=20, capture_output=True, text=True,
                           creationflags=_CREATE_NO_WINDOW)
        out = (p.stdout or "").strip()
        return ("OK" in out), out
    except Exception as e:
        return False, str(e)


def _random_design() -> str:
    """Açık sunuma, kurulu Office temalarından (.thmx) RASTGELE birini uygular."""
    if not _IS_WINDOWS:
        try:
            from actions import office_uno
            if office_uno.available():
                r = office_uno.random_design()
                if r:
                    return r
        except Exception:
            pass
        return ("Tasarım uygulayamadım — LibreOffice Impress açık mı? "
                "(OnlyOffice tema değişimini dışarıdan desteklemiyor.)")
    script = (
        "try { "
        "$p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
        "$pres=$p.ActivePresentation; "
        "$dirs=@('C:\\Program Files\\Microsoft Office\\root\\Document Themes 16',"
        "'C:\\Program Files (x86)\\Microsoft Office\\root\\Document Themes 16',"
        "'C:\\Program Files\\Microsoft Office\\Document Themes 16'); "
        "$t=Get-ChildItem -Path $dirs -Filter *.thmx -ErrorAction SilentlyContinue "
        "| Get-Random; "
        "if ($t) { $pres.ApplyTemplate($t.FullName); "
        "Write-Output ('OK:'+$t.BaseName) } "
        "else { Write-Output 'NO:tema dosyası bulunamadı' } } "
        "catch { Write-Output ('NO:'+$_.Exception.Message) }"
    )
    ok, out = _ps(script)
    if ok:
        name = out.split("OK:", 1)[-1].strip() or "Office teması"
        return f"Rastgele tasarım uygulandı: {name}. Beğenmezsen 'tasarım seç' de, başkasını denerim."
    return ("Tasarım uygulanamadı — açık bir PowerPoint sunumu var mı? "
            "(Tasarımlar sunumda geçerlidir; Word sayfasında kullanılamaz.)")


def _uno_fallback(action: str, color_name: str, size):
    """MS Office yoksa LibreOffice (UNO) ile aynı işi dener."""
    try:
        from actions import office_uno
        if not office_uno.available():
            return None
        rgb = COLORS_TR.get((color_name or "").lower().strip())
        return office_uno.format_text(action, rgb=rgb, size=size)
    except Exception:
        return None


def office_format(action: str, value: str = "") -> str:
    """
    action: font_color | font_size | font_grow | font_shrink | page_color
            | new_page (Word'de yeni sayfa / PowerPoint'te yeni slayt)
            | random_design (sunuma RASTGELE bir Office teması uygular)
    value : renk adı (Türkçe) ya da punto sayısı (yeni eylemlerde boş)
    Önce Word, o yoksa PowerPoint denenir.
    """
    if not _IS_WINDOWS:
        act = (action or "").lower().strip()
        size_v = None
        try:
            size_v = float(value)
        except Exception:
            pass
        try:
            from actions import office_uno
            if office_uno.available():
                if act == "random_design":
                    r = office_uno.random_design()
                elif act.startswith("align_"):
                    r = office_uno.align_text(act)
                elif act == "new_page":
                    r = office_uno.new_page()
                else:
                    color_val = (value or "").strip()
                    if act in ("font_color", "page_color") and not color_val:
                        import random
                        color_val = random.choice(
                            sorted(set(COLORS_TR) - {"kirmizi", "yesil", "sari", "altin"}))
                    rgb = COLORS_TR.get(color_val.lower())
                    r = office_uno.format_text(act, rgb=rgb, size=size_v)
                    if r and color_val != (value or "").strip():
                        r += f" (renk: {color_val})"
                if r:
                    return r
        except Exception:
            pass
        # LibreOffice yoksa (OnlyOffice): klavye ile yapılabilenleri dene
        if act in ("new_page", "align_left", "align_center", "align_right",
                   "align_justify"):
            try:
                from actions.keyboard_control import press_key
                key = {"new_page": "ctrl_m", "align_left": "ctrl_l",
                       "align_center": "ctrl_e", "align_right": "ctrl_r",
                       "align_justify": "ctrl_j"}[act]
                r = press_key(key)
                if "basıldı" in r:
                    ad = {"new_page": "Yeni sayfa/slayt eklendi",
                          "align_left": "Metin sola hizalandı",
                          "align_center": "Metin ortalandı",
                          "align_right": "Metin sağa hizalandı",
                          "align_justify": "Metin iki yana yaslandı"}[act]
                    return f"{ad} (klavye kısayoluyla)."
            except Exception:
                pass
        return ("Belgeye bağlanamadım. LibreOffice için: sudo apt install "
                "libreoffice python3-uno. OnlyOffice'te renk/tema ayarları "
                "dışarıdan yapılamıyor (dürüst sınır).")

    action = (action or "").lower().strip()
    value = (value or "").strip()
    auto_picked = False
    if action in ("font_color", "page_color") and not value:
        # Renk hiç belirtilmemiş ("arkaplan rengini DEĞİŞTİR" gibi, "mavi
        # yap" değil) — başarısız olmak yerine hoş bir renk rastgele seç.
        # Kullanıcı YANLIŞ bir renk söylediyse (aşağıdaki color is None dalı)
        # bu YİNE de net bir hata verir — sadece "hiç söylemedi" durumunda
        # otomatik seçiyoruz.
        import random
        value = random.choice(sorted(set(COLORS_TR) - {"kirmizi", "yesil", "sari", "altin"}))
        auto_picked = True
    color = _rgb_int(value)
    size = None
    try:
        size = max(6, min(200, int(value)))
    except Exception:
        pass

    if action == "random_design":
        return _random_design()
    if action.startswith("align_"):
        color, size = None, None
    if action in ("font_color", "page_color") and color is None:
        return (f"'{value}' rengini tanımadım. Bildiklerim: "
                + ", ".join(sorted(set(COLORS_TR) - {"kirmizi", "yesil", "sari", "altin"})))
    if action == "font_size" and size is None:
        return "Yazı boyutu için bir sayı söyle (örn. 'yazı boyutunu 24 yap')."

    # ── WORD ────────────────────────────────────────────────────────────────
    align_map = {"align_left": 0, "align_center": 1, "align_right": 2,
                 "align_justify": 3}
    word_body = {
        **{k: f"$t.ParagraphFormat.Alignment = {v}" for k, v in align_map.items()},
        "font_color": f"$t.Font.Color = {color}",
        "font_size": f"$t.Font.Size = {size}",
        "font_grow": "$t.Font.Grow()",
        "font_shrink": "$t.Font.Shrink()",
        "page_color": (f"$d.Background.Fill.Visible = $true; "
                       f"$d.Background.Fill.ForeColor.RGB = {color}; "
                       "$w.ActiveWindow.View.DisplayBackgrounds = $true"),
        "new_page": ("$w.Selection.EndKey(6) | Out-Null; "
                     "$w.Selection.InsertBreak(7)"),
    }[action]
    word_script = (
        "try { $w=[Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application'); "
        "$d=$w.ActiveDocument; "
        "$t = if ($w.Selection.Type -gt 1) { $w.Selection } else { $d.Content }; "
        f"{word_body}; Write-Output 'OK-WORD' }} catch {{ Write-Output ('NO:'+$_.Exception.Message) }}"
    )
    ok, out = _ps(word_script)
    if ok:
        if action == "new_page":
            return "Word'de yeni sayfa eklendi — imleç yeni sayfada."
        if action.startswith("align_"):
            nerede = {"align_left": "sola", "align_center": "ortaya",
                      "align_right": "sağa", "align_justify": "iki yana"}[action]
            return f"Metin {nerede} hizalandı."
        target = "seçili metnin" if action.startswith("font") else "sayfanın"
        suffix = f" (renk: {value})" if auto_picked else ""
        return f"Word'de {target} biçimi güncellendi{suffix}."

    # ── POWERPOINT ──────────────────────────────────────────────────────────
    pp_body = {
        **{k: f"$tr.ParagraphFormat.Alignment = {v + 1}" for k, v in align_map.items()},
        "font_color": f"$tr.Font.Color.RGB = {color}",
        "font_size": f"$tr.Font.Size = {size}",
        "font_grow": "$tr.Font.Size = $tr.Font.Size + 2",
        "font_shrink": "$tr.Font.Size = [Math]::Max(6, $tr.Font.Size - 2)",
        "page_color": (f"$sl.FollowMasterBackground = 0; "
                       f"$sl.Background.Fill.ForeColor.RGB = {color}"),
        "new_page": ("$idx = $sl.SlideIndex; "
                     "$null = $sl.Parent.Slides.Add($idx + 1, 2); "
                     "$p.ActiveWindow.View.GotoSlide($idx + 1)"),
    }[action]
    pp_script = (
        "try { $p=[Runtime.InteropServices.Marshal]::GetActiveObject('PowerPoint.Application'); "
        "$sl=$p.ActiveWindow.View.Slide; "
        "$tr = try { $p.ActiveWindow.Selection.TextRange } catch { $null }; "
        "if (-not $tr) { $tr = ($sl.Shapes | Where-Object {$_.HasTextFrame} | "
        "Select-Object -First 1).TextFrame.TextRange }; "
        f"{pp_body}; Write-Output 'OK-PP' }} catch {{ Write-Output ('NO:'+$_.Exception.Message) }}"
    )
    ok2, out2 = _ps(pp_script)
    if ok2:
        if action == "new_page":
            return "Sunuma yeni slayt eklendi — şu an o slayttasın."
        if action.startswith("align_"):
            nerede = {"align_left": "sola", "align_center": "ortaya",
                      "align_right": "sağa", "align_justify": "iki yana"}[action]
            return f"Slayttaki metin {nerede} hizalandı."
        target = "metnin" if action.startswith("font") else "slaydın"
        suffix = f" (renk: {value})" if auto_picked else ""
        return f"Sunumda {target} biçimi güncellendi{suffix}."

    size_v = None
    try:
        size_v = float(value)
    except Exception:
        pass
    r = _uno_fallback(action, value, size_v)
    if r:
        return r
    return ("Açık bir Word/PowerPoint (ya da LibreOffice) belgesi bulamadım — "
            "önce belgeyi aç (örn. 'word aç'), sonra tekrar dene.")
