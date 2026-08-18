"""
Uygulama açma — CachyOS (Arch Linux) sürümü. Birkaç aşamalı arama yapar:
  1) Kullanıcının AYARLAR'dan elle kaydettiği özel yol
  2) PATH üzerinde ara (shutil.which) — bilinen takma adlarla
  3) .desktop dosyalarında ara (XDG uygulama dizinleri + Flatpak/Snap) —
     kurulu HERHANGİ bir uygulama için genel çözüm, tıpkı bir uygulama
     menüsünün yaptığı gibi; Exec= satırını okuyup gerçek komutu bulur
  4) Flatpak uygulama kimliğiyle ara (`flatpak run <id>`)
  5) Son çare: xdg-open ile ham adı denemek

NOT (Windows sürümüyle FARK): Windows sürümü Program Files/Başlat Menüsü
kısayollarını (.lnk) tarar; CachyOS'ta bunun karşılığı .desktop dosyalarını
taramaktır (bkz. _resolve_via_desktop_files) — işlevsel olarak eşdeğer bir
genel çözüm, sadece platforma özgü mekanizma farklı.
"""

from __future__ import annotations

import configparser
import glob
import os
import shutil
import subprocess
from pathlib import Path

from app_config import get_app_config_value, save_app_config

_IS_WINDOWS = False  # bu dosya yalnızca CachyOS/Linux için kullanılır


# ══ Kullanıcının AYARLAR'dan elle seçtiği uygulama yolları ══════════════════
# config'te "custom_app_paths": {"uygulama_adı_küçük_harf": "tam/yol"}
def get_custom_app_paths() -> dict:
    return dict(get_app_config_value("custom_app_paths", {}) or {})


def _get_custom_app_path(normalized_name: str) -> str | None:
    return get_custom_app_paths().get(normalized_name)


def set_custom_app_path(app_name: str, path: str) -> str:
    """AYARLAR > 📁 UYGULAMA YOLLARI penceresinden çağrılır."""
    key = (app_name or "").strip().lower()
    if not key:
        return "Uygulama adı boş olamaz."
    if not path or not Path(path).exists():
        return f"Dosya bulunamadı: {path}"
    paths = get_custom_app_paths()
    paths[key] = str(path)
    save_app_config({"custom_app_paths": paths})
    return f"'{app_name}' için özel yol kaydedildi: {path}"


def remove_custom_app_path(app_name: str) -> str:
    key = (app_name or "").strip().lower()
    paths = get_custom_app_paths()
    if key in paths:
        del paths[key]
        save_app_config({"custom_app_paths": paths})
        return f"'{app_name}' için kayıtlı özel yol silindi."
    return f"'{app_name}' için kayıtlı özel yol yoktu."


# ── HTML/web tabanlı araçlar (akış şeması, çarkıfelek, satranç, yerinde kodlama
#    aracı vb.) ──────────────────────────────────────────────────────────────
# Bunlar çalıştırılabilir DEĞİL — tarayıcıda AÇILMASI gereken dosyalar.
_WEB_FILE_EXTS = {".html", ".htm", ".url"}


def is_web_file(path: str) -> bool:
    return Path(path).suffix.lower() in _WEB_FILE_EXTS


def _open_web_file(path: str) -> None:
    """HTML dosyasını varsayılan tarayıcıda açar — YERİNDE'nin kendi
    araçlarının (carkifelek.py, akis_semasi.py, satranc.py vb.) kullandığı
    AYNI yöntem: xdg-open, başarısız olursa webbrowser modülüne düşer."""
    p = Path(path)
    url = p.resolve().as_uri() if p.suffix.lower() != ".url" else path
    try:
        subprocess.Popen(["xdg-open", url],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception:
        import webbrowser
        webbrowser.open(url)


# ── Takma adlar → PATH'te aranacak birincil komut adı ───────────────────────
# Not: Bazı uygulamaların birden fazla olası paket adı vardır (ör. terminal,
# dosya yöneticisi, hesap makinesi kurulu masaüstü ortamına göre değişir) —
# bunlar için MULTI_CANDIDATES listesi kullanılır (aşağıda).
APP_ALIASES = {
    "chrome":            "google-chrome-stable",
    "google chrome":     "google-chrome-stable",
    "edge":              "microsoft-edge-stable",
    "microsoft edge":    "microsoft-edge-stable",
    "firefox":           "firefox",
    "spotify":           "spotify",
    "vscode":            "code",
    "vs code":           "code",
    "code":              "code",
    "discord":           "discord",
    "slack":             "slack",
    "telegram":          "telegram-desktop",
    "zoom":              "zoom",
    "notion":            "notion-app",
    "blender":           "blender",
    "tasarım":           "blender",
    "tasarim":           "blender",
    "3d":                "blender",
    "freecad":           "freecad",
    "free cad":          "freecad",
    "godot":             "godot4",
    "godot engine":      "godot4",
    "obs":               "obs",
    "obs studio":        "obs",
    "obs stüdyo":        "obs",
    "android studio":    "studio.sh",
    "visual studio":     "code",
    "unity":             "unity-editor",
    "scratch":           "scratch-desktop",
    "oyun arac":         "scratch-desktop",
    "oyun aracı":        "scratch-desktop",
    "kodlama arac":      "scratch-desktop",
    "kodlama aracı":     "scratch-desktop",
    "arduino":           "arduino-ide",
    "arduino ide":       "arduino-ide",
    "thonny":            "thonny",
    "thonny ide":        "thonny",
}

# Birden fazla olası paket/komut adı olan uygulamalar — masaüstü ortamına
# (KDE/GNOME/Hyprland vb.) göre hangisi kuruluysa o denenir.
MULTI_CANDIDATES = {
    "terminal":         ["konsole", "kitty", "alacritty", "foot", "gnome-terminal",
                          "xfce4-terminal", "xterm"],
    "cmd":              ["konsole", "kitty", "alacritty", "foot", "gnome-terminal",
                          "xfce4-terminal", "xterm"],
    "powershell":       ["konsole", "kitty", "alacritty", "foot", "gnome-terminal", "xterm"],
    "explorer":         ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm"],
    "dosya gezgini":    ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm"],
    "file explorer":    ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm"],
    "dosyalar":         ["dolphin", "nautilus", "nemo", "thunar", "pcmanfm"],
    "notepad":          ["kate", "gedit", "mousepad", "featherpad", "xed"],
    "not defteri":      ["kate", "gedit", "mousepad", "featherpad", "xed"],
    "notlar":           ["kate", "gedit", "mousepad", "featherpad", "xed"],
    "calculator":       ["kcalc", "gnome-calculator", "qalculate-gtk", "galculator"],
    "hesap makinesi":   ["kcalc", "gnome-calculator", "qalculate-gtk", "galculator"],
    "task manager":     ["plasma-systemmonitor", "ksysguard", "gnome-system-monitor", "xfce4-taskmanager"],
    "görev yöneticisi": ["plasma-systemmonitor", "ksysguard", "gnome-system-monitor", "xfce4-taskmanager"],
    "settings":         ["systemsettings", "gnome-control-center", "xfce4-settings-manager"],
    "ayarlar":          ["systemsettings", "gnome-control-center", "xfce4-settings-manager"],
    "paint":            ["kolourpaint", "gpaint", "krita"],
    "photos":           ["gwenview", "eog", "nomacs"],
    "fotoğraflar":      ["gwenview", "eog", "nomacs"],
    "music":            ["elisa", "rhythmbox", "clementine"],
    "müzik":            ["elisa", "rhythmbox", "clementine"],
    "whatsapp":         ["whatsapp-for-linux", "whatsdesk"],
    "store":            ["plasma-discover", "gnome-software"],
    "mağaza":           ["plasma-discover", "gnome-software"],
}

# ── Ofis paketi: Word/Excel/PowerPoint ───────────────────────────────────────
# CachyOS'ta genellikle LibreOffice kurulu olur; OnlyOffice de olası bir
# alternatif. Hangisi kuruluysa onu bulup açar.
OFFICE_APPS = {"word", "excel", "powerpoint", "office word", "office excel", "office powerpoint",
               "kelime işlemci", "hesap tablosu", "sunum"}

OFFICE_NORMALIZE = {
    "kelime işlemci": "word", "office word": "word",
    "hesap tablosu": "excel", "office excel": "excel",
    "sunum": "powerpoint", "office powerpoint": "powerpoint",
}

# Her ofis uygulaması için sırayla denenecek (komut, argüman) çiftleri.
# 1) LibreOffice  2) OnlyOffice
OFFICE_COMMANDS = {
    "word":       [("soffice", ["--writer"]), ("libreoffice", ["--writer"]),
                   ("onlyoffice-desktopeditors", [])],
    "excel":      [("soffice", ["--calc"]), ("libreoffice", ["--calc"]),
                   ("onlyoffice-desktopeditors", [])],
    "powerpoint": [("soffice", ["--impress"]), ("libreoffice", ["--impress"]),
                   ("onlyoffice-desktopeditors", [])],
}

OFFICE_CLOSE_HINTS = {
    "word":       ["soffice.bin", "onlyoffice-desktopeditors"],
    "excel":      ["soffice.bin", "onlyoffice-desktopeditors"],
    "powerpoint": ["soffice.bin", "onlyoffice-desktopeditors"],
}

# close_app için: takma ad -> pkill'e verilecek süreç adı deseni (pkill -f
# ile alt-dize eşleşmesi yapılır, bu yüzden joker karaktere gerek yok).
CLOSE_APP_PROCESS_HINTS = {
    "blender":        ["blender"],
    "freecad":        ["freecad", "FreeCAD"],
    "free cad":       ["freecad", "FreeCAD"],
    "godot":          ["godot"],
    "godot engine":   ["godot"],
    "obs":            ["obs"],
    "obs studio":     ["obs"],
    "obs stüdyo":     ["obs"],
    "android studio": ["studio.sh", "android-studio"],
    "visual studio":  ["code"],
    "unity":          ["unity-editor", "Unity"],
    "chrome":         ["google-chrome"],
    "firefox":        ["firefox"],
    "spotify":        ["spotify"],
    "discord":        ["discord", "Discord"],
    "vscode":         ["code"],
    "vs code":        ["code"],
    "code":           ["code"],
    "notepad":        ["kate", "gedit", "mousepad"],
    "scratch":        ["scratch-desktop"],
    "arduino":        ["arduino-ide", "arduino"],
    "arduino ide":    ["arduino-ide"],
    "thonny":         ["thonny"],
    "terminal":       [],  # kasıtlı boş — o an aktif terminali kapatmak tehlikeli
}


def _resolve_office_app(key: str) -> tuple[str, list[str]] | None:
    for cmd, args in OFFICE_COMMANDS.get(key, []):
        found = shutil.which(cmd)
        if found:
            return found, args
    return None


def _resolve_known_pattern(key: str) -> str | None:
    """Windows sürümündeki Program Files taramasının Linux karşılığı yok —
    burada PATH/.desktop araması yeterli olduğundan bu fonksiyon sadece
    geriye dönük uyumluluk için (ör. scratch_bridge.py'nin _IS_WINDOWS dalı
    hiçbir zaman Linux'ta çalışmaz) None döner."""
    return None


# ── .desktop dosyası araması (Windows'taki Başlat Menüsü taramasının Linux
#    karşılığı) — kurulu HERHANGİ bir GUI uygulaması için genel çözüm ────────
_DESKTOP_DIRS = [
    Path("/usr/share/applications"),
    Path("/usr/local/share/applications"),
    Path.home() / ".local/share/applications",
    Path("/var/lib/flatpak/exports/share/applications"),
    Path.home() / ".local/share/flatpak/exports/share/applications",
    Path("/var/lib/snapd/desktop/applications"),
]


def _parse_desktop_exec(desktop_file: Path) -> str | None:
    try:
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.read(desktop_file, encoding="utf-8")
        exec_line = cp.get("Desktop Entry", "Exec", fallback=None)
        if not exec_line:
            return None
        # %f, %F, %u, %U gibi yer tutucuları temizle
        parts = [p for p in exec_line.split() if not p.startswith("%")]
        return " ".join(parts) if parts else None
    except Exception:
        return None


def _resolve_via_desktop_files(app_name: str) -> str | None:
    """.desktop dosyaları arasında isme göre arar (dosya adında VEYA
    Name= alanında eşleşme), bulursa Exec= komutunu döndürür. Kurulu
    HERHANGİ bir uygulama için işe yarayan genel bir yöntemdir — Blender,
    OBS gibi PATH'e eklenmeyen bazı GUI programlar genelde buradan bulunur."""
    name_lower = app_name.lower().strip()
    if not name_lower:
        return None
    best_match: str | None = None
    for d in _DESKTOP_DIRS:
        if not d.exists():
            continue
        try:
            for desktop_file in d.glob("*.desktop"):
                stem_lower = desktop_file.stem.lower()
                if name_lower in stem_lower:
                    exec_cmd = _parse_desktop_exec(desktop_file)
                    if exec_cmd:
                        return exec_cmd
                    continue
                # Dosya adı eşleşmediyse Name= alanına da bak (bazı paketler
                # dosya adını uygulamanın kendi adından farklı seçer)
                try:
                    cp = configparser.ConfigParser(interpolation=None, strict=False)
                    cp.read(desktop_file, encoding="utf-8")
                    display_name = cp.get("Desktop Entry", "Name", fallback="").lower()
                    if name_lower in display_name:
                        exec_cmd = _parse_desktop_exec(desktop_file)
                        if exec_cmd and not best_match:
                            best_match = exec_cmd
                except Exception:
                    continue
        except Exception:
            continue
    return best_match


def _resolve_via_flatpak(app_name: str) -> str | None:
    """Kurulu flatpak uygulamaları arasında isme göre arar, bulursa
    'flatpak run <id>' komutunu döndürür."""
    if not shutil.which("flatpak"):
        return None
    name_lower = app_name.lower().strip()
    try:
        out = subprocess.run(
            ["flatpak", "list", "--app", "--columns=name,application"],
            capture_output=True, text=True, timeout=5,
        ).stdout
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            display_name, app_id = parts[0].strip(), parts[1].strip()
            if name_lower in display_name.lower() or name_lower in app_id.lower():
                return f"flatpak run {app_id}"
    except Exception:
        pass
    return None


_LAST_OPENED: str | None = None  # "kapat" tek başına dendiğinde hedef


def set_last_opened(name: str) -> None:
    """Office boş belge ve Blender köprüsü gibi KISAYOLLAR open_app'i atlayarak
    uygulamayı açıyor; o yollarda da son açılanı bilmemiz gerekiyor, yoksa
    "kapat" komutu 'henüz bir şey açmadım' diyor (yaşanan hata)."""
    global _LAST_OPENED
    if name:
        _LAST_OPENED = name.strip().lower()


def _launch_command(command: str) -> None:
    """Boşluk ayrılmış bir komut dizisini (ör. 'soffice --writer' ya da
    'flatpak run com.spotify.Client') ayrı, bağımsız bir süreç olarak
    başlatır — YERİNDE kapansa bile açık kalır."""
    parts = command.split()
    subprocess.Popen(parts, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def open_app(app_name: str) -> str:
    global _LAST_OPENED
    _LAST_OPENED = (app_name or '').strip().lower()
    if not app_name:
        return "Uygulama adı belirtilmedi."

    normalized = app_name.lower().strip()

    # ── Kullanıcının AYARLAR panelinden elle seçtiği özel yol — HER ŞEYDEN
    #    ÖNCE kontrol edilir.
    custom_path = _get_custom_app_path(normalized)
    if custom_path:
        p = Path(custom_path)
        if not p.exists():
            return (f"'{app_name}' için AYARLAR'da kayıtlı yol artık yok: {custom_path}\n"
                    "AYARLAR > 📁 UYGULAMA YOLLARI'ndan güncelleyebilirsin.")
        try:
            if is_web_file(str(p)):
                _open_web_file(str(p))
            else:
                subprocess.Popen([str(p)], stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            return f"{app_name} açıldı (kayıtlı özel yoldan)."
        except Exception as e:
            return f"'{app_name}' kayıtlı özel yoldan açılamadı: {e}"

    # Ofis paketi: Word/Excel/PowerPoint — LibreOffice ya da OnlyOffice,
    # hangisi kuruluysa onu bulup açar.
    office_key = OFFICE_NORMALIZE.get(normalized, normalized)
    if office_key in OFFICE_APPS:
        hit = _resolve_office_app(office_key)
        if not hit:
            return (f"'{app_name}' için ne LibreOffice ne de OnlyOffice bulunamadı. "
                    "En az birinin kurulu olması gerekiyor (sudo pacman -S libreoffice-fresh).")
        exe, args = hit
        try:
            subprocess.Popen([exe] + args, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # 1) Birden fazla olası paket adı olan uygulamalar (terminal, dosya
    #    yöneticisi, hesap makinesi vb.) — kuruluysa PATH'te ilk bulunanı dene
    if normalized in MULTI_CANDIDATES:
        for candidate in MULTI_CANDIDATES[normalized]:
            found = shutil.which(candidate)
            if found:
                try:
                    subprocess.Popen([found], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                    return f"{app_name} açıldı."
                except Exception as e:
                    return f"'{app_name}' açılamadı: {e}"

    resolved = APP_ALIASES.get(normalized, app_name)

    # 2) PATH'teki executable (bilinen takma ad ya da kullanıcının söylediği
    #    ham ad — ör. 'htop', 'gimp' gibi APP_ALIASES'de olmayan bir program)
    exe_path = shutil.which(resolved) or shutil.which(normalized.replace(" ", "-"))
    if exe_path:
        try:
            subprocess.Popen([exe_path], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # 3) .desktop dosyalarında ara (genel çözüm — çoğu kurulu GUI uygulaması için işe yarar)
    desktop_hit = _resolve_via_desktop_files(app_name) or _resolve_via_desktop_files(resolved)
    if desktop_hit:
        try:
            _launch_command(desktop_hit)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # 4) Flatpak uygulamaları arasında ara
    flatpak_hit = _resolve_via_flatpak(app_name) or _resolve_via_flatpak(resolved)
    if flatpak_hit:
        try:
            _launch_command(flatpak_hit)
            return f"{app_name} açıldı."
        except Exception as e:
            return f"'{app_name}' açılamadı: {e}"

    # 5) Son çare: xdg-open ile ham adı dene (URI şeması olabilir ihtimaline karşı)
    try:
        result = subprocess.run(["xdg-open", resolved], capture_output=True,
                                timeout=5, start_new_session=True)
        if result.returncode == 0:
            return f"{app_name} açıldı."
    except Exception:
        pass

    return (f"'{app_name}' bulunamadı. Kurulu olduğundan emin ol (pacman/AUR/flatpak) — "
            "kurulu ama standart bir konumda değilse, Ayarlar panelinden tam dosya "
            "yolunu (çalıştırılabilir dosya ya da .html) belirtmen gerekebilir.")


def _try_altf4_fallback(app_name: str) -> str | None:
    """Süreç tabanlı kapatma (pkill) hedefi BULAMADIĞINDA son çare olarak
    Alt+F4 dener — ama SADECE aktif pencerenin YERİNDE'nin kendisi olmadığı
    GÜVENLE tespit edilebiliyorsa (bkz. actions/window_safety.py). Emin
    olunamayan durumda (Wayland gibi) HİÇBİR TUŞ GÖNDERMEZ, None döner."""
    try:
        from actions.window_safety import safe_to_send_altf4
        from actions.keyboard_control import press_key
    except ImportError:
        return None
    safe, reason = safe_to_send_altf4()
    if not safe:
        return None
    r = press_key("alt_f4")
    if "basıldı" in r:
        return f"'{app_name}' işlem listesinde bulunamadı ama Alt+F4 ile kapatmayı denedim ({reason})."
    return None


def close_app(app_name: str) -> str:
    global _LAST_OPENED
    if (app_name or "").strip().lower() in ("__last__", "son uygulama", "onu", "bunu"):
        if not _LAST_OPENED:
            return "Hangi uygulamayı kapatayım? (Henüz bir şey açmadım.)"
        app_name = _LAST_OPENED
    """Sesle 'Blender'i kapat', 'OBS'i kapat', 'Godot'u kapat', 'Word'ü kapat'
    gibi komutlarla çalışan bir uygulamayı kapatır. pkill -f (alt-dize
    eşleşmesi) kullanır."""
    if not app_name:
        return "Kapatılacak uygulama adı belirtilmedi."

    normalized = app_name.lower().strip()
    office_key = OFFICE_NORMALIZE.get(normalized, normalized)
    hints = OFFICE_CLOSE_HINTS.get(office_key) or CLOSE_APP_PROCESS_HINTS.get(normalized)

    if hints is None:
        # Bilinmeyen bir uygulama adıysa, takma adı (varsa) ya da ham adı dene.
        base = APP_ALIASES.get(normalized, app_name)
        hints = [base]

    closed_any = False
    last_error = ""
    for proc_name in hints:
        if not proc_name:
            continue
        try:
            result = subprocess.run(
                ["pkill", "-f", proc_name],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                closed_any = True
            else:
                last_error = (result.stderr or result.stdout or "").strip()
        except Exception as e:
            last_error = str(e)

    if closed_any:
        return f"{app_name} kapatıldı."
    fallback = _try_altf4_fallback(app_name)
    if fallback:
        return fallback
    return f"'{app_name}' kapatılamadı — çalışmıyor olabilir. ({last_error})" if last_error else f"'{app_name}' çalışmıyor gibi görünüyor."
