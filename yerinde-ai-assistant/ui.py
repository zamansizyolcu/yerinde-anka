"""
YERINDE Windows — UI v3
Concentric teal rings · Segmented arcs
"""

import os, time, math, random, threading
import tkinter as tk
from collections import deque
from pathlib import Path
import psutil

from PIL import Image, ImageTk, ImageDraw, ImageFont
import platform

from app_config import has_gemini_api_key, load_app_config, save_app_config, get_app_config_value
from actions.weather import get_weather_summary
from actions.sys_info import get_gpu_status

# ── Türkçe tarih adları (sistem diline bağımlı kalmamak için sabit) ──────────
TR_DAYS = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]
TR_MONTHS = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
             "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]


def tr_date_str() -> str:
    """'08 TEMMUZ 2026' biçiminde Türkçe tarih döner."""
    lt = time.localtime()
    return f"{lt.tm_mday:02d} {TR_MONTHS[lt.tm_mon - 1]} {lt.tm_year}"


def tr_day_str() -> str:
    """'ÇARŞAMBA' biçiminde Türkçe gün adı döner."""
    return TR_DAYS[time.localtime().tm_wday]

BASE_DIR = Path(__file__).resolve().parent
BGIMG_DIR = BASE_DIR / "Arkaplanlar"  # TEMALAR > Arkaplan Resmi için kalıcı depo

# Sesle tetiklenen 'açık'/'koyu' arkaplan modları için projeyle birlikte gelen
# hazır görseller — BGIMG_DIR içinde dururlar ama kullanıcının kendi seçtiği
# özel arkaplanlardan farklı olarak arkaplan temizlenirken SİLİNMEZLER (bkz.
# _clear_bg_image), aksi halde bir kere 'sade' denince kalıcı olarak kaybolup
# bir daha 'açık'/'koyu' diyince bulunamazlardı.
BUILTIN_BG_FILES = {
    "acik": "varsayilan_acik.png", "koyu": "varsayilan_koyu.png",
    "yesil": "varsayilan_yesil.png", "mor": "varsayilan_mor.png",
    "kirmizi": "varsayilan_kirmizi.png", "mavi": "varsayilan_mavi.png",
    "turuncu": "varsayilan_turuncu.png",
}

SYSTEM_NAME = "Y.E.R.İ.N.D.E"
PLATFORM_NAME = "CACHYOS"
MODEL_BADGE = f"SES ÇEKİRDEĞİ · {PLATFORM_NAME}"

# ── Renk paleti ──────────────────────────────────────────────────────────────
# ══ TEMALAR ═════════════════════════════════════════════════════════════════
# Her tema, arayüzün tüm renklerini tanımlar. AYARLAR > TEMA'dan değiştirilir.
THEMES = {
    "karanlik": {   # varsayılan: siyah + turkuaz
        "name": "Karanlık (Turkuaz)",
        "BG": "#020c0c", "PRI": "#00d4c0", "ORG": "#ff6600", "ORG2": "#ff9900",
        "MID": "#006a62", "DIM": "#0a2a28", "DIMMER": "#061414", "TEXT": "#7dfff6",
        "PANEL": "#030f0f", "GREEN": "#00ff88", "RED": "#ff3344", "MUTED": "#cc2255",
        "BLUE": "#4488ff", "GOLD": "#ffcc00",
    },
    "krem": {       # sıcak kağıt tonu — göz yormayan aydınlık tema
        "name": "Krem (Aydınlık)",
        "BG": "#f4efe4", "PRI": "#1f7a6f", "ORG": "#a8591a", "ORG2": "#b06a1f",
        "MID": "#7fa89e", "DIM": "#e5dcc9", "DIMMER": "#efe8d9", "TEXT": "#2f3a37",
        "PANEL": "#fbf7ee", "GREEN": "#1f6e44", "RED": "#b5443c", "MUTED": "#96566b",
        "BLUE": "#3a6ea5", "GOLD": "#8a611a",
    },
    "yesil": {      # adaçayı/nane — yumuşak, tatlı yeşil
        "name": "Adaçayı (Yumuşak Yeşil)",
        "BG": "#0e1a15", "PRI": "#8fd6ae", "ORG": "#e3b06b", "ORG2": "#f0cf94",
        "MID": "#4e8168", "DIM": "#1a2f26", "DIMMER": "#13241d", "TEXT": "#d9efe1",
        "PANEL": "#132520", "GREEN": "#a8e6bf", "RED": "#df8078", "MUTED": "#b07c8c",
        "BLUE": "#84b9cf", "GOLD": "#e6cb8a",
    },
    "mor": {        # GÜNCELLENDİ — kullanıcının yüklediği "mor.png" görselinden
                    # gerçek piksel analiziyle örneklendi: koyu menekşe-siyah
                    # zemin (~#0d021b), doymuş mor vurgu (~#4a166b-#b565e8).
        "name": "Lavanta (Mavi-Mor)",
        "BG": "#0d021b", "PRI": "#b565e8", "ORG": "#9d3fd1", "ORG2": "#b565e8",
        "MID": "#4a166b", "DIM": "#240a3d", "DIMMER": "#170430", "TEXT": "#e8d4f5",
        "PANEL": "#170430", "GREEN": "#7a5a9e", "RED": "#d9507a", "MUTED": "#8a6aa8",
        "BLUE": "#8060c0", "GOLD": "#d8a8f0",
    },
    "orman": {      # orman esintisi: koyu yeşil zemin, yosun-yaprak vurgular
        "name": "Orman Esintisi",
        "BG": "#0a1710", "PRI": "#79c98a", "ORG": "#d9a441", "ORG2": "#ecc673",
        "MID": "#3d6b4c", "DIM": "#152a1e", "DIMMER": "#0f2016", "TEXT": "#d6ecd8",
        "PANEL": "#102117", "GREEN": "#9fdca7", "RED": "#d97a6c", "MUTED": "#a97f6a",
        "BLUE": "#7fb6a8", "GOLD": "#e3c884",
    },
    "deniz": {      # su/deniz: derin mavi zemin, turkuaz-köpük vurgular
        "name": "Deniz (Su)",
        "BG": "#071a24", "PRI": "#5fc9d6", "ORG": "#e8955c", "ORG2": "#f2bb85",
        "MID": "#356b7a", "DIM": "#0e2d3a", "DIMMER": "#0a222c", "TEXT": "#cfeef5",
        "PANEL": "#0b2430", "GREEN": "#77dcc0", "RED": "#e2777f", "MUTED": "#9c7fa8",
        "BLUE": "#6fb4e8", "GOLD": "#f0cf8e",
    },
    "gunes": {      # GÜNCELLENDİ — kullanıcının yüklediği "turuncu.png"
                    # görselinden piksel analiziyle türetildi: neredeyse
                    # siyah kahve-turuncu zemin (~#170801), sıcak turuncu
                    # vurgu (~#5e2508 - #e8823a aralığı).
        "name": "Amber (Turuncu-Sarı)",
        "BG": "#170801", "PRI": "#e8823a", "ORG": "#c85a1e", "ORG2": "#e8823a",
        "MID": "#5e2508", "DIM": "#2a1005", "DIMMER": "#1b0a02", "TEXT": "#f5ddc0",
        "PANEL": "#200d02", "GREEN": "#c9954a", "RED": "#d9502e", "MUTED": "#a97850",
        "BLUE": "#c8955a", "GOLD": "#f0a840",
    },
    "anka": {       # YENİ — logodan: koyu orman yeşili, nane/mint taş, altın + alev turuncusu
        "name": "Anka (Yeşil-Alev)",
        "BG": "#071a13", "PRI": "#8ff0cc", "ORG": "#e8a13f", "ORG2": "#f3c877",
        "MID": "#3d6b52", "DIM": "#12291f", "DIMMER": "#0c2018", "TEXT": "#dff5e8",
        "PANEL": "#0e241b", "GREEN": "#8ff0c8", "RED": "#e05f30", "MUTED": "#b98a6a",
        "BLUE": "#6fb0c8", "GOLD": "#f0c04a",
    },
    "destek": {     # YENİ — "Destek Ekosistemi" logosundan örneklendi: adaçayı/
                    # nane yeşili yaprak halkası, sıcak turuncu yapraklar, merkezde
                    # altın-krem parıltı (elini uzatan insan figürü).
        "name": "Destek (Yaşam Halkası)",
        "BG": "#0a1713", "PRI": "#f6d9a0", "ORG": "#df6b32", "ORG2": "#f0a15c",
        "MID": "#4d6b57", "DIM": "#132821", "DIMMER": "#0e1f19", "TEXT": "#eaf5ee",
        "PANEL": "#102420", "GREEN": "#7fc9a8", "RED": "#d9603a", "MUTED": "#b98a6a",
        "BLUE": "#6fa8b0", "GOLD": "#f3c877",
    },
    "pico_mavi": {  # GÜNCELLENDİ — kullanıcının yüklediği "mavi.png"
                    # görselinden piksel analiziyle türetildi: neredeyse
                    # siyah lacivert zemin (~#000e28), gökyüzü mavisi vurgu
                    # (~#063263 - #4ab0e8 aralığı). NOT: bu artık Pico Devre
                    # Atölyesi'nin GERÇEK mavi temasıyla birebir aynı değil
                    # (isim hâlâ "Pico Mavi" ama renkler bu görselden).
        "name": "Pico Mavi",
        "BG": "#000e28", "PRI": "#4ab0e8", "ORG": "#2f7dc4", "ORG2": "#4ab0e8",
        "MID": "#0d3a70", "DIM": "#001e3d", "DIMMER": "#001830", "TEXT": "#cfe8f8",
        "PANEL": "#001830", "GREEN": "#5a9ec9", "RED": "#e0607a", "MUTED": "#6a8fae",
        "BLUE": "#4ab0e8", "GOLD": "#a8d8f0",
    },
    "pico_yesil": {  # YENİ — Pico Devre Atölyesi'nin "Yeşil" temasıyla birebir
                     # aynı renk paleti: koyu orman zemini, nane yeşili vurgu.
        "name": "Pico Yeşil",
        "BG": "#071a13", "PRI": "#8ff0cc", "ORG": "#f2a154", "ORG2": "#f5bd7e",
        "MID": "#2a4a3a", "DIM": "#1c3a2c", "DIMMER": "#0f2419", "TEXT": "#eef8f2",
        "PANEL": "#0e241b", "GREEN": "#6bc98a", "RED": "#e0604a", "MUTED": "#7d9a8a",
        "BLUE": "#6fb0c8", "GOLD": "#f0c04a",
    },
    "pico_krem": {  # YENİ — Pico Devre Atölyesi'nin "Krem" temasıyla birebir
                    # aynı renk paleti: sıcak fildişi zemin, kahve vurgu.
        "name": "Pico Krem",
        "BG": "#f3ecdc", "PRI": "#9c6b30", "ORG": "#b5651d", "ORG2": "#c47f3a",
        "MID": "#ab8f68", "DIM": "#d9c7a3", "DIMMER": "#ecdfc4", "TEXT": "#2b2013",
        "PANEL": "#fffbf2", "GREEN": "#3a7d4f", "RED": "#b23a2e", "MUTED": "#96566b",
        "BLUE": "#3a6ea5", "GOLD": "#8a611a",
    },
    "kirmizi": {  # YENİ — kullanıcının yüklediği kızıl/kehribar tonlu görselden
                  # örneklendi: koyu kahve-kızıl zemin, alevli turuncu-kırmızı vurgu.
        "name": "Kızıl (Ateş)",
        "BG": "#1a0d08", "PRI": "#e8703a", "ORG": "#c73e2e", "ORG2": "#e05a3a",
        "MID": "#6b3a28", "DIM": "#2e1810", "DIMMER": "#22120c", "TEXT": "#f5ddc8",
        "PANEL": "#241209", "GREEN": "#c98a5a", "RED": "#e0402c", "MUTED": "#a9614a",
        "BLUE": "#c87858", "GOLD": "#f0a44a",
    },
}



def _load_theme() -> dict:
    key = str(get_app_config_value("ui_theme", "karanlik") or "karanlik")
    return THEMES.get(key, THEMES["karanlik"])


_T = _load_theme()
C_BG      = _T["BG"]
C_PRI     = _T["PRI"]
C_ORG     = _T["ORG"]
C_ORG2    = _T["ORG2"]
C_MID     = _T["MID"]
C_DIM     = _T["DIM"]
C_DIMMER  = _T["DIMMER"]
C_TEXT    = _T["TEXT"]
C_PANEL   = _T["PANEL"]
C_GREEN   = _T["GREEN"]
C_RED     = _T["RED"]
C_MUTED   = _T["MUTED"]
C_BLUE    = _T["BLUE"]
C_GOLD    = _T["GOLD"]

# Orb durum renkleri
def _hex_to_rgb_tuple(hexcolor: str) -> tuple[int, int, int]:
    h = hexcolor.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# Konuşma animasyonundaki (orb/parçacık küre) renkler, artık SABİT DEĞİL —
# aktif temanın kendi GREEN/BLUE/GOLD/MUTED/RED/DIM renklerinden türetiliyor.
# Böylece hangi tema seçiliyse (ör. Pico Mavi/Yeşil/Krem), animasyon da o
# temayla uyumlu renklerde çalışır.
ORB_COLORS = {
    "LISTENING":    _hex_to_rgb_tuple(_T["GREEN"]),
    "SPEAKING":     _hex_to_rgb_tuple(_T["BLUE"]),
    "THINKING":     _hex_to_rgb_tuple(_T["GOLD"]),
    "MUTED":        _hex_to_rgb_tuple(_T["MUTED"]),
    "PAUSED":       _hex_to_rgb_tuple(_T["DIM"]),
    "ERROR":        _hex_to_rgb_tuple(_T["RED"]),
    "INITIALISING": _hex_to_rgb_tuple(_T["RED"]),
}

# ── Boyutlar ─────────────────────────────────────────────────────────────────
W_TARGET = 1540
H_TARGET = 940
LEFT_W_T = 310
RIGHT_W_T = 340
HDR_H    = 72
FOOTER_H = 26
INPUT_H  = 34
CONTROL_H = 126

# ÇEVRİMİÇİ (Gemini) sesler — Türkçe etiket ↔ Gemini ses kimliği
ONLINE_VOICES = [
    ("Kadın 1 — Berrak",  "Kore"),
    ("Kadın 2 — Yumuşak", "Aoede"),
    ("Kadın 3 — Genç",    "Leda"),
    ("Erkek 1 — Derin",   "Charon"),
    ("Erkek 2 — Canlı",   "Puck"),
    ("Erkek 3 — Güçlü",   "Fenrir"),
]
VOICES = [label for label, _ in ONLINE_VOICES]           # açılır menüde görünenler
VOICE_ID_BY_LABEL = {label: vid for label, vid in ONLINE_VOICES}
VOICE_LABEL_BY_ID = {vid: label for label, vid in ONLINE_VOICES}

# ── Font sistemi ─────────────────────────────────────────────────────────────
# Grift fontu kullanıcının sisteminde yüklü. Basliklarda daha sert bir vurgu
# icin ayri extra bold aile adini kullaniyoruz.
FONT_BODY_FAMILY = "Grift"
FONT_DISPLAY_FAMILY = "Grift Extra Bold"


def font_body(size: int):
    return (FONT_BODY_FAMILY, size)


def font_body_bold(size: int):
    return (FONT_BODY_FAMILY, size, "bold")


def font_display(size: int):
    return (FONT_DISPLAY_FAMILY, size)


STATE_HEX_COLORS = {
    "LISTENING": C_GREEN,
    "SPEAKING": C_BLUE,
    "THINKING": C_GOLD,
    "INITIALISING": C_RED,
    "ERROR": C_RED,
}


# ── SoundManager ─────────────────────────────────────────────────────────────
import subprocess as _sp

def _resolve_sfx_dir() -> Path:
    return BASE_DIR / "SFX"


_SFX_DIR = _resolve_sfx_dir()
_HUD_FILE = _SFX_DIR / "HUD.mp3"
_START_FILE = _SFX_DIR / "Start.mp3"
_THINK_FILE = _SFX_DIR / "Think.mp3"
_DONE_FILE = _SFX_DIR / "Done.mp3"
_ERROR_FILE = _SFX_DIR / "Error.mp3"

_CREATE_NO_WINDOW = getattr(_sp, "CREATE_NO_WINDOW", 0)


def _play_audio_file(path: Path, volume: float):
    """
    Windows'ta MP3'u PowerShell System.Windows.Media.MediaPlayer ile asenkron calar.
    macOS'taki 'afplay -v <vol>' davranisinin karsiligi: dosya bitince surec sonlanir,
    boylece dongusel sesler (HUD/Think) sorunsuz tekrar eder. Bir Popen nesnesi doner;
    durdurmak icin proc.terminate() yeterlidir (PowerShell olunce ses de durur).
    """
    vol = max(0.0, min(1.0, float(volume)))
    uri = str(path).replace("\\", "/")  # Windows yolu URI icin / ile
    script = (
        "Add-Type -AssemblyName presentationCore;"
        "$ErrorActionPreference='SilentlyContinue';"
        "$p=New-Object System.Windows.Media.MediaPlayer;"
        f"$p.Open([System.Uri]'{uri}');"
        f"$p.Volume={vol:.2f};"
        "$p.Play();"
        "$n=0; while(-not $p.NaturalDuration.HasTimeSpan -and $n -lt 40){Start-Sleep -Milliseconds 50; $n++};"
        "if($p.NaturalDuration.HasTimeSpan)"
        "{Start-Sleep -Milliseconds ([int]$p.NaturalDuration.TimeSpan.TotalMilliseconds + 150)}"
        "else{Start-Sleep -Seconds 5}"
    )
    return _sp.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
        stdout=_sp.DEVNULL,
        stderr=_sp.DEVNULL,
        creationflags=_CREATE_NO_WINDOW,
    )


class SoundManager:
    def __init__(self):
        self._enabled = True
        self._ambient_proc = None
        self._volume = 0.20
        self._ambient_stop = None
        self._ambient_thread = None
        self._foreground_proc = None
        self._foreground_stop = None
        self._foreground_thread = None
        self._foreground_tag = ""
        self._lock = threading.Lock()

    @staticmethod
    def _terminate_process(proc):
        if not proc or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=1.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def start_ambient(self):
        if not _HUD_FILE.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if self._foreground_proc and self._foreground_proc.poll() is None:
                return
            if self._ambient_thread and self._ambient_thread.is_alive():
                return
            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._loop_ambient,
                args=(stop_event,),
                daemon=True,
            )
            self._ambient_stop = stop_event
            self._ambient_thread = worker
        worker.start()

    def _loop_ambient(self, stop_event: threading.Event):
        while not stop_event.is_set():
            with self._lock:
                if not self._enabled or self._ambient_stop is not stop_event:
                    break
                volume = self._volume
            try:
                proc = _play_audio_file(_HUD_FILE, volume)
            except Exception:
                break

            with self._lock:
                if self._ambient_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    break
                self._ambient_proc = proc

            while proc.poll() is None and not stop_event.wait(0.2):
                pass

            if stop_event.is_set():
                self._terminate_process(proc)

            with self._lock:
                if self._ambient_proc is proc:
                    self._ambient_proc = None

            if stop_event.is_set():
                break
            time.sleep(0.2)

        with self._lock:
            if self._ambient_stop is stop_event:
                self._ambient_stop = None
            if self._ambient_thread and self._ambient_thread.ident == threading.get_ident():
                self._ambient_thread = None

    def _stop_ambient(self):
        with self._lock:
            stop_event = self._ambient_stop
            proc = self._ambient_proc
            self._ambient_stop = None
            self._ambient_thread = None
            self._ambient_proc = None
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)

    def _stop_foreground(self):
        with self._lock:
            stop_event = self._foreground_stop
            proc = self._foreground_proc
            self._foreground_stop = None
            self._foreground_thread = None
            self._foreground_proc = None
            self._foreground_tag = ""
        if stop_event:
            stop_event.set()
        self._terminate_process(proc)

    def _play_foreground(
        self,
        path: Path,
        tag: str,
        loop: bool = False,
        volume_factor: float = 1.0,
        pause_ambient: bool = True,
    ):
        if not path.exists():
            return
        with self._lock:
            if not self._enabled:
                return
            if loop and self._foreground_tag == tag and self._foreground_thread and self._foreground_thread.is_alive():
                return
            base_volume = self._volume
        if pause_ambient:
            self._stop_ambient()
        self._stop_foreground()

        stop_event = threading.Event()
        worker = threading.Thread(
            target=self._foreground_worker,
            args=(
                path,
                tag,
                stop_event,
                loop,
                max(0.0, min(1.0, base_volume * volume_factor)),
                pause_ambient,
            ),
            daemon=True,
        )
        with self._lock:
            self._foreground_stop = stop_event
            self._foreground_thread = worker
            self._foreground_tag = tag
        worker.start()

    def _foreground_worker(
        self,
        path: Path,
        tag: str,
        stop_event: threading.Event,
        loop: bool,
        volume: float,
        resume_ambient: bool,
    ):
        while not stop_event.is_set():
            try:
                proc = _play_audio_file(path, volume)
            except Exception:
                break

            with self._lock:
                if self._foreground_stop is not stop_event or not self._enabled:
                    self._terminate_process(proc)
                    break
                self._foreground_proc = proc

            while proc.poll() is None and not stop_event.wait(0.12):
                pass

            if stop_event.is_set():
                self._terminate_process(proc)

            with self._lock:
                if self._foreground_proc is proc:
                    self._foreground_proc = None

            if not loop or stop_event.is_set():
                break
            time.sleep(0.08)

        with self._lock:
            if self._foreground_stop is stop_event:
                self._foreground_stop = None
                self._foreground_thread = None
                self._foreground_tag = ""
            should_restart = resume_ambient and self._enabled and self._foreground_stop is None
        if should_restart:
            self.start_ambient()

    def play_startup(self):
        self._play_foreground(_START_FILE, tag="start", loop=False, volume_factor=0.95)

    def play_success(self):
        self._play_foreground(
            _DONE_FILE,
            tag="done",
            loop=False,
            volume_factor=0.68,
            pause_ambient=False,
        )

    def play_error(self):
        self._play_foreground(_ERROR_FILE, tag="error", loop=False, volume_factor=0.95)

    def start_thinking(self):
        self._play_foreground(
            _THINK_FILE,
            tag="think",
            loop=True,
            volume_factor=0.82,
            pause_ambient=False,
        )

    def stop_thinking(self):
        with self._lock:
            is_thinking = self._foreground_tag == "think"
        if is_thinking:
            self._stop_foreground()

    def toggle(self) -> bool:
        self.set_enabled(not self._enabled)
        return self._enabled

    def set_enabled(self, enabled: bool):
        enabled = bool(enabled)
        with self._lock:
            self._enabled = enabled
        if enabled:
            self.start_ambient()
        else:
            self._stop_ambient()
            self._stop_foreground()

    def set_volume(self, volume: float):
        with self._lock:
            self._volume = max(0.0, min(1.0, float(volume)))
            fg_tag = self._foreground_tag
            can_restart_ambient = self._enabled and not fg_tag
        if fg_tag == "think":
            self._stop_foreground()
            self.start_thinking()
        elif can_restart_ambient:
            self._stop_ambient()
            self.start_ambient()

    def stop_all(self):
        with self._lock:
            self._enabled = False
        self._stop_ambient()
        self._stop_foreground()

    def get_volume(self) -> float:
        return self._volume


# ─────────────────────────────────────────────────────────────────────────────

class YerindeUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()  # Tam render olana kadar gizle — siyah flash önlenir
        self.root.title("Y.E.R.İ.N.D.E")
        self.root.resizable(False, False)  # Tam ekran dışında boyutlandırma kapalı

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.W = min(sw - 48, W_TARGET)
        self.H = min(sh - 84, H_TARGET)
        _geo = f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}"
        self.root.geometry(_geo)
        self.root.configure(bg=C_BG)

        self._window_geometry = _geo

        # Tkinter geri çağrılarında oluşan hatalar uygulamayı KAPATMASIN
        # (Blender/YOLO/numpy gibi dış bileşenlerden gelen beklenmedik hatalar
        #  yüzünden YERINDE'nin kendini kapatması yaşanmış bir sorundu).
        def _tk_error(exc, val, tb):
            import traceback as _tb
            _tb.print_exception(exc, val, tb)
            try:
                self.write_log(f"ERR: Beklenmedik hata (uygulama açık kalıyor) — {val}")
            except Exception:
                pass
        self.root.report_callback_exception = _tk_error
        self._normal_size = (self.W, self.H)
        self._fullscreen = False
        self._resize_job = None

        self._set_layout_metrics(self.W, self.H)

        # ── State ────────────────────────────────────────────────────────────
        self.speaking        = False
        self.user_speaking   = False
        self.muted           = False
        self.paused          = False
        self.scale           = 1.0
        self.target_scale    = 1.0
        self.halo_a          = 55.0
        self.target_halo     = 55.0
        self.last_t          = time.time()
        self.tick            = 0
        self.rings_spin      = [0.0, 45.0, 90.0, 200.0]  # 4 ayrı halka
        self.pulse_r         = []
        self.status_blink    = True
        self._yerinde_state   = "INITIALISING"
        self._user_speaking_until = 0.0

        # ── Webcam ───────────────────────────────────────────────────────────
        self._webcam_active        = False
        self._garden_active        = False
        self._garden_waking        = False
        self._webcam_photo         = None
        self._cam_label: "tk.Label | None" = None
        self._cam_orb_shift        = 0.0   # orb'un anlık kayması (animasyonlu)
        self._cam_orb_shift_target = 0.0   # hedef kayma
        self._cam_orb_face         = 0.0   # orb'un anlık face boyutu (0 → FACE kullan)
        self._cam_orb_face_target  = 0.0   # hedef face boyutu
        self._weather_card = {
            "city": "Edirne",
            "primary": "--",
            "details": ["Hava durumu yükleniyor..."],
        }
        self._panel_focus = ""
        self._panel_focus_until = 0.0
        self._brief_refresh_busy = False
        self._started_at = time.time()
        self._error_hold_until = 0.0
        self._settings_open = False
        self._settings_tab = "settings"
        self._debug_entries = deque(maxlen=160)
        self._startup_sfx_played = False
        self._settings_geometry = {
            "btn_x": 14,
            "btn_y": 12,
            "btn_w": 250,
            "btn_h": 46,
            "panel_x": 14,
            "panel_y": HDR_H + 10,
            "panel_w": 320,
            # Tüm ayar satırları (en altta EĞİTİM VERİSİ dahil, satır sonu y=782) sığsın;
            # panel aşağı doğru genişler, küçük ekranlarda pencereye göre kısalır
            "panel_h": max(700, min(900, self.H - HDR_H - 10)),
        }
        self.setup_frame = None
        self.api_entry = None
        self.youtube_api_entry = None
        self.youtube_handle_entry = None

        # ── Callbacks ────────────────────────────────────────────────────────
        self.on_text_command = None
        self.on_pause_toggle = None
        self.on_stop_command = None
        self.on_voice_change = None
        self.on_effects_state_change = None
        self.on_webcam_toggle = None
        self.on_stop_speaking = None
        self.on_yolo_toggle = None
        self.on_camera_photo = None
        self.on_camera_record_toggle = None
        self.on_camera_pause_toggle = None
        self.on_garden_toggle = None
        self.on_garden_wake = None
        self.on_garden_ptz = None
        self.on_garden_ptz_start = None
        self.on_garden_ptz_stop = None
        self.on_garden_horn = None
        self.on_garden_talk = None
        self._cam_recording = False
        self._cam_rec_paused = False

        # ── Voice ────────────────────────────────────────────────────────────
        self._current_voice = self._load_voice()

        # ── Sound ────────────────────────────────────────────────────────────
        self.sound = SoundManager()

        # ── Stats ────────────────────────────────────────────────────────────
        self._stats      = {'cpu': 0.0, 'ram': 0.0, 'disk': 0.0, 'gpu': 0.0, 'gpu_name': '',
                            'battery': 100.0, 'net_up': 0.0, 'net_down': 0.0}
        self._cpu_hist   = [0.0] * 24
        self._last_net   = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._wave_yerinde = [random.randint(4, 26) for _ in range(18)]
        self._wave_user   = [random.randint(2, 10) for _ in range(18)]

        # ── Typing ───────────────────────────────────────────────────────────
        self.typing_queue = deque()
        self.is_typing    = False

        # ── Partiküller (arka plan, az sayıda) ───────────────────────────────
        self.particles = [
            {
                'x':  random.uniform(0, self.W),
                'y':  random.uniform(0, self.H),
                'vx': random.uniform(-0.15, 0.15),
                'vy': random.uniform(-0.15, 0.15),
                'r':  random.uniform(0.5, 1.8),
                'a':  random.randint(15, 70),
            }
            for _ in range(24)
        ]

        self.orb_particles = [
            {
                'angle': random.uniform(0, math.tau),
                'orbit': random.uniform(0.06, 0.98),
                'speed': random.uniform(-0.030, 0.030),
                'size': random.uniform(0.8, 2.8),
                'phase': random.uniform(0, math.tau),
                'wobble': random.uniform(0.010, 0.040),
                'depth': random.uniform(0.30, 1.00),
            }
            for _ in range(160)
        ]
        self.orb_shell_particles = [
            {
                'angle': random.uniform(0, math.tau),
                'speed': random.uniform(-0.020, 0.020),
                'size': random.uniform(1.4, 3.8),
                'phase': random.uniform(0, math.tau),
                'glow': random.uniform(0.4, 1.0),
            }
            for _ in range(84)
        ]

        # ── Canvas ───────────────────────────────────────────────────────────
        self.bg = tk.Canvas(self.root, width=self.W, height=self.H,
                            bg=C_BG, highlightthickness=0)
        self.bg.place(x=0, y=0)
        self._bg_photo = None
        self._load_bg_image()

        # ── Log ──────────────────────────────────────────────────────────────
        self.log_frame = tk.Frame(self.root, bg=C_PANEL,
                                  highlightbackground=C_MID,
                                  highlightthickness=1)
        self.log_frame.place(x=self.CHAT_X, y=self.CHAT_Y,
                             width=self.CHAT_W, height=self.CHAT_H)
        self.log_text = tk.Text(
            self.log_frame, fg=C_TEXT, bg=C_PANEL,
            insertbackground=C_TEXT, borderwidth=0,
            wrap="word", font=font_body(12), padx=12, pady=8)
        self.log_text.pack(fill="both", expand=True)
        self.log_text.configure(state="disabled")
        self.log_text.tag_config("you", foreground=C_BLUE)
        self.log_text.tag_config("ai",  foreground=C_PRI)
        self.log_text.tag_config("sys", foreground=C_GOLD)
        self.log_text.tag_config("err", foreground=C_RED)

        self._build_input_bar(self.CHAT_W)
        self._build_mute_button()
        self._build_pause_button()
        self._build_stop_button()
        self._build_webcam_button()
        self._build_camera_capture_buttons()
        self._build_garden_buttons()
        self._build_shutdown_button()
        # (Sosyal medya çubuğu kaldırıldı)
        self._build_settings_panel()
        self._build_voice_selector(self._settings_body)
        self._build_sfx_button(self._settings_body)
        self._build_api_button(self._settings_body)
        self._build_fx_slider(self._settings_body)
        self._build_autostart_button(self._settings_body)
        self._build_shortcut_button(self._settings_body)
        self._build_provider_button(self._settings_body)
        self._build_gemini_model_button(self._settings_body)
        self._build_ollama_model_button(self._settings_body)
        self._build_ollama_coder_model_button(self._settings_body)
        self._build_voice_choice_button(self._settings_body)
        self._build_stt_engine_button(self._settings_body)
        self._build_thinking_button(self._settings_body)
        self._build_upload_button(self._settings_body)
        self._build_app_paths_button(self._settings_body)
        self._build_egitim_verisi_button(self._settings_body)
        self._build_remote_access_button(self._settings_body)
        self._build_garden_settings(self._settings_body)
        self._layout_settings_controls()
        self._place_layout_widgets()

        # Orb tıklama = pause/resume
        self.bg.bind("<Button-1>", self._on_canvas_click)

        self.root.bind("<F4>",        lambda e: self._toggle_mute())
        self.root.bind("<Control-m>", lambda e: self._toggle_mute())
        self.root.bind("<Escape>",    lambda e: self._esc_action())
        self.root.bind("<F5>",        lambda e: self._toggle_pause())
        self.root.bind("<F6>",        lambda e: self._toggle_webcam_ui())
        self.root.bind("<F11>",       lambda e: self._toggle_fullscreen())
        self.root.bind("<Control-f>", lambda e: self._toggle_fullscreen())

        self._api_key_ready = has_gemini_api_key() or get_app_config_value("model_provider", "gemini") == "ollama"
        if not self._api_key_ready:
            self._show_setup_ui()

        self.root.bind("<Configure>", self._on_configure)

        self._effects_active = None
        self._sync_sound_state()
        self._kick_brief_refresh()
        # İlk render — deiconify sonrası _draw() zorunlu, macOS cached content'i atmıyor
        self.root.update_idletasks()
        self._draw()
        self.root.update()
        self._animate()
        self.root.deiconify()
        self.root.update()
        self._draw()   # pencere görünür olduktan sonra zorla çiz — siyah flash önlenir
        # Tam ekran başlat
        self._fullscreen = True
        self._enter_fullscreen()
        self.root.protocol("WM_DELETE_WINDOW", self._shutdown)

    # ── Layout & Fullscreen ───────────────────────────────────────────────────
    def _on_configure(self, event):
        if event.widget is not self.root:
            return
        w, h = event.width, event.height
        if w == self.W and h == self.H:
            return
        if not hasattr(self, "bg"):
            return
        if self._resize_job:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(80, lambda: self._resize_surface(w, h))

    def _set_layout_metrics(self, width: int, height: int):
        self.W = int(width)
        self.H = int(height)
        self.LEFT_W = min(LEFT_W_T, int(self.W * 0.22))
        self.RIGHT_W = min(RIGHT_W_T, int(self.W * 0.24))
        center_w = self.W - self.LEFT_W - self.RIGHT_W
        orb_area_h = self.H - HDR_H - CONTROL_H - FOOTER_H - 24
        self.FCX = self.LEFT_W + center_w // 2
        self.FCY = HDR_H + orb_area_h // 2 + 6
        self.FACE = min(int(orb_area_h * 0.82), int(center_w * 0.70), 520)
        self.CENTER_X0 = self.LEFT_W
        self.CENTER_X1 = self.W - self.RIGHT_W
        self.CTRL_X = self.LEFT_W + 18
        self.CTRL_Y = HDR_H + orb_area_h + 2
        self.CTRL_W = center_w - 36
        self.CHAT_PANEL_X = self.W - self.RIGHT_W + 8
        self.CHAT_PANEL_Y = HDR_H + 8
        self.CHAT_PANEL_W = self.RIGHT_W - 14
        self.CHAT_PANEL_H = self.H - HDR_H - FOOTER_H - 16
        self.CHAT_X = self.CHAT_PANEL_X + 10
        self.CHAT_Y = self.CHAT_PANEL_Y + 34
        self.CHAT_W = self.CHAT_PANEL_W - 20
        self.CHAT_H = self.CHAT_PANEL_H - 90
        self.CHAT_INPUT_Y = self.CHAT_PANEL_Y + self.CHAT_PANEL_H - INPUT_H - 10

    def _session_is_x11(self):
        """XDG_SESSION_TYPE=='x11' → True (Tk '-fullscreen' attribute'u
        X11/KWin'de çökme yapıyor; maximize yolu kullanılacak)."""
        try:
            return os.environ.get("XDG_SESSION_TYPE", "").lower() == "x11"
        except Exception:
            return False

    def _exit_fullscreen_state(self):
        """Tam ekran durumundan pencere durumuna dönüş. X11'de KWin
        maximize (zoomed) kaldırılır; diğer ortamlarda -fullscreen kapatılır."""
        if self._session_is_x11():
            try:
                self.root.state("normal")
            except Exception:
                pass
        else:
            try:
                self.root.attributes("-fullscreen", False)
            except Exception:
                pass

    def _enter_fullscreen(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.resizable(True, True)          # macOS native fullscreen için gerekli
        if self._session_is_x11():
            # final16.md §2: Tk "-fullscreen" attribute'u X11/KWin'de çökme
            # yapıyor (kesik görünüm + kapat/yeniden başlat kırığı + drkonqi
            # Qt6 abort). X11'de KWin maximize (zoomed) kullanılır — stabil.
            try:
                self.root.state("zoomed")
            except Exception:
                self.root.geometry(f"{sw}x{sh}+0+0")
        else:
            # Wayland/xwayland: mevcut -fullscreen davranışı korunur.
            self.root.attributes("-fullscreen", True)
        self._resize_surface(sw, sh)

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self._enter_fullscreen()
        else:
            self._exit_fullscreen_state()
            self.root.resizable(False, False)    # pencere modunda kilitle
            self.root.geometry(self._window_geometry)
            self._resize_surface(*self._normal_size)

    def _esc_action(self):
        """Tam ekrandaysa çık, pencere modundaysa kapat."""
        if self._fullscreen:
            self._fullscreen = False
            self._exit_fullscreen_state()
            self.root.resizable(False, False)
            self.root.geometry(self._window_geometry)
            self._resize_surface(*self._normal_size)
        else:
            self._shutdown()

    def _resize_surface(self, width: int, height: int):
        # final16.md §2: layout yeniden ölçeklemesi (tam ekran/zoomed giriş-
        # çıkışında) tek bir beklenmedik hatada uygulamayı KAPATMAMALI —
        # hata log'a yazılır, uygulama açık kalır.
        try:
            self._set_layout_metrics(width, height)
            self.bg.configure(width=self.W, height=self.H)
            self.bg.place(x=0, y=0)
            self._load_bg_image()  # yeni boyuta göre yeniden ölçekle (kırparak kapla)
            self._place_layout_widgets()
            if hasattr(self, "_social_bar"):
                self._social_bar.place(x=14, y=self.H - FOOTER_H - 52)
            for p in getattr(self, "particles", []):
                p["x"] %= self.W
                p["y"] %= self.H
            # Kamera açıksa layout değiştiğinde hedefleri ve label konumunu güncelle
            if self._webcam_active:
                cam_w, cam_h, cam_x, cam_y, shift, face = self._calc_cam_layout()
                self._cam_orb_shift_target = float(shift)
                self._cam_orb_face_target  = float(face)
                if self._cam_label is not None:
                    self._cam_label.place(x=cam_x, y=cam_y,
                                          width=cam_w, height=cam_h)
                self._place_camera_capture_buttons(cam_w, cam_x, cam_y, cam_h)
            elif self._garden_active:
                cam_w, cam_h, cam_x, cam_y, shift, face = self._calc_cam_layout()
                self._cam_orb_shift_target = float(shift)
                self._cam_orb_face_target  = float(face)
                if self._cam_label is not None:
                    self._cam_label.place(x=cam_x, y=cam_y,
                                          width=cam_w, height=cam_h)
                self._place_garden_ptz_bar(cam_w, cam_x, cam_y, cam_h)
        except Exception as _e:
            try:
                self.write_log(f"ERR: _resize_surface — {_e} (uygulama açık kalıyor)")
            except Exception:
                pass

    # ── Voice ─────────────────────────────────────────────────────────────────
    def _load_voice(self) -> str:
        """Kayıtlı Gemini ses kimliğini (Kore/Charon...) Türkçe etikete çevirir."""
        try:
            vid = str(load_app_config().get("voice", "Charon") or "Charon")
        except Exception:
            vid = "Charon"
        return VOICE_LABEL_BY_ID.get(vid, "Erkek 1 — Derin")

    # (Sosyal medya çubuğu kaldırıldı — _build_social_bar fonksiyonu artık kullanılmıyor)

    # ── Shutdown button (sağ alt, büyük) ────────────────────────────────────
    def _build_shutdown_button(self):
        BW, BH = 140, 36
        self._shutdown_canvas = tk.Canvas(
            self.root, width=BW, height=BH,
            bg=C_BG, highlightthickness=0, cursor="hand2")
        self._shutdown_canvas.bind("<Button-1>", lambda e: self._shutdown())
        self._draw_shutdown_button()

    def _draw_shutdown_button(self):
        c = self._shutdown_canvas
        BW, BH = 140, 36
        c.delete("all")
        # Köşe braket stili
        bl = 8
        for bx, by, sx, sy in [(0, 0, 1, 1), (BW, 0, -1, 1),
                                (0, BH, 1, -1), (BW, BH, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=C_RED, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=C_RED, width=2)
        c.create_text(BW//2, BH//2, text="⏻  KAPAT",
                      fill=C_RED, font=font_display(11))

    def _build_settings_panel(self):
        geo = self._settings_geometry
        self._settings_btn_canvas = tk.Canvas(
            self.root,
            width=geo["btn_w"],
            height=geo["btn_h"],
            bg=C_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_btn_canvas.place(x=geo["btn_x"], y=geo["btn_y"])
        self._settings_btn_canvas.bind("<Button-1>", lambda e: self._toggle_settings_panel())
        self._draw_settings_button()

        self._settings_panel = tk.Frame(
            self.root,
            bg=C_PANEL,
            highlightbackground=C_MID,
            highlightthickness=1,
        )
        self._settings_panel.place_forget()

        self._settings_title = tk.Label(
            self._settings_panel,
            text="AYARLAR",
            fg=C_PRI,
            bg=C_PANEL,
            font=font_display(11),
        )
        self._settings_tab_settings = tk.Canvas(
            self._settings_panel,
            width=108,
            height=28,
            bg=C_PANEL,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_tab_settings.bind("<Button-1>", lambda e: self._set_settings_tab("settings"))
        self._settings_tab_debug = tk.Canvas(
            self._settings_panel,
            width=96,
            height=28,
            bg=C_PANEL,
            highlightthickness=0,
            cursor="hand2",
        )
        self._settings_tab_debug.bind("<Button-1>", lambda e: self._set_settings_tab("debug"))
        # AYARLAR sekmesi kaydırılabilir bir Canvas içine alınıyor: küçük
        # ekranlarda panel yüksekliği tüm satırlara (en altta EĞİTİM VERİSİ
        # dahil) yetmeyebiliyor — önceden alttaki satırlar sessizce kırpılıp
        # hiç görünmüyordu. Artık fare tekerleğiyle kaydırılabiliyor.
        self._settings_scroll_canvas = tk.Canvas(
            self._settings_panel, bg=C_PANEL, highlightthickness=0
        )
        self._settings_body = tk.Frame(self._settings_scroll_canvas, bg=C_PANEL)
        self._settings_body_window = self._settings_scroll_canvas.create_window(
            (0, 0), window=self._settings_body, anchor="nw"
        )
        self._debug_body = tk.Frame(self._settings_panel, bg=C_PANEL)
        self._settings_sfx_label = tk.Label(
            self._settings_body,
            text="SES EFEKTİ",
            fg=C_MID,
            bg=C_PANEL,
            font=font_body_bold(8),
        )
        self._settings_status_primary = tk.Label(
            self._settings_body,
            text="",
            fg=C_TEXT,
            bg=C_PANEL,
            font=font_body_bold(9),
            anchor="w",
            justify="left",
        )
        self._settings_status_secondary = tk.Label(
            self._settings_body,
            text="",
            fg=C_MID,
            bg=C_PANEL,
            font=font_body(9),
            anchor="w",
            justify="left",
        )
        self._debug_text = tk.Text(
            self._debug_body,
            fg=C_TEXT,
            bg=C_DIMMER,
            insertbackground=C_TEXT,
            borderwidth=0,
            wrap="word",
            font=font_body(10),
            padx=10,
            pady=10,
            highlightthickness=1,
            highlightbackground=C_DIM,
        )
        self._debug_text.tag_config("info", foreground=C_TEXT)
        self._debug_text.tag_config("warn", foreground=C_GOLD)
        self._debug_text.tag_config("err", foreground=C_RED)
        self._debug_text.configure(state="disabled")
        self._draw_settings_tabs()
        self._render_debug_logs()
        self._refresh_settings_status()
        self._bind_settings_scroll()

    def _settings_scroll_target_active(self, event) -> bool:
        """Fare imleci AYARLAR panelinin üstündeyken mi tekerlek kaydırmalı?"""
        if not self._settings_open or self._settings_tab != "settings":
            return False
        try:
            widget = self.root.winfo_containing(event.x_root, event.y_root)
        except Exception:
            return False
        w = widget
        while w is not None:
            if w == self._settings_panel:
                return True
            w = w.master
        return False

    def _settings_scroll_by(self, units: int):
        self._settings_scroll_canvas.yview_scroll(units, "units")

    def _bind_settings_scroll(self):
        """Windows/macOS <MouseWheel> ve Linux <Button-4>/<Button-5> ile
        AYARLAR panelini kaydırır. Panel açıkken ve imleç panel üstündeyken
        etkin olur — böylece geri kalan arayüzün kaydırma/tıklama
        davranışını etkilemez."""
        def _on_wheel(event):
            if not self._settings_scroll_target_active(event):
                return
            self._settings_scroll_by(int(-1 * (event.delta / 120)))

        def _on_wheel_up(event):
            if not self._settings_scroll_target_active(event):
                return
            self._settings_scroll_by(-3)

        def _on_wheel_down(event):
            if not self._settings_scroll_target_active(event):
                return
            self._settings_scroll_by(3)

        self.root.bind_all("<MouseWheel>", _on_wheel, add="+")
        self.root.bind_all("<Button-4>", _on_wheel_up, add="+")
        self.root.bind_all("<Button-5>", _on_wheel_down, add="+")

    def _draw_settings_button(self):
        c = self._settings_btn_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        accent = C_BLUE if self._settings_open else C_MID
        inner = C_DIM if self._settings_open else C_DIMMER
        c.create_rectangle(0, 0, bw, bh, fill=inner, outline="")
        bl = 9
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1), (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx + sx * bl, by, fill=accent, width=2)
            c.create_line(bx, by, bx, by + sy * bl, fill=accent, width=2)
        c.create_text(14, 15, text="SİSTEM AYARLARI", fill=C_PRI, font=font_display(10), anchor="w")
        c.create_text(14, 33, text=MODEL_BADGE, fill=C_MID, font=font_body(9), anchor="w")
        c.create_text(bw - 14, bh // 2, text="▾" if self._settings_open else "▸",
                      fill=accent, font=font_display(14), anchor="e")

    def _toggle_settings_panel(self):
        self._settings_open = not self._settings_open
        self._draw_settings_button()
        self._place_layout_widgets()

    def _draw_settings_tabs(self):
        for key, canvas, label in (
            ("settings", self._settings_tab_settings, "AYARLAR"),
            ("debug", self._settings_tab_debug, "HATA AYIKLAMA"),
        ):
            active = self._settings_tab == key
            bw = int(canvas["width"])
            bh = int(canvas["height"])
            canvas.delete("all")
            outline = C_PRI if active else C_DIM
            fill = C_DIM if active else C_PANEL
            text_col = C_PRI if active else C_MID
            canvas.create_rectangle(0, 0, bw, bh, fill=fill, outline="")
            bl = 7
            for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1), (0, bh, 1, -1), (bw, bh, -1, -1)]:
                canvas.create_line(bx, by, bx + sx * bl, by, fill=outline, width=1)
                canvas.create_line(bx, by, bx, by + sy * bl, fill=outline, width=1)
            canvas.create_text(bw // 2, bh // 2, text=label, fill=text_col, font=font_body_bold(9))

    def _set_settings_tab(self, tab: str):
        self._settings_tab = "debug" if tab == "debug" else "settings"
        self._draw_settings_tabs()
        self._place_layout_widgets()

    def _layout_settings_controls(self):
        inner_w = self._settings_geometry["panel_w"] - 24
        self._api_canvas.place(x=0, y=2)
        self._sfx_canvas.place(x=inner_w - int(self._sfx_canvas["width"]) - 4, y=0)
        self._settings_status_primary.place(x=0, y=38, width=inner_w)
        self._settings_status_secondary.place(x=0, y=58, width=inner_w)
        self._settings_sfx_label.place(x=0, y=92)
        self._volume_label.place(x=0, y=116)
        self._volume_scale.place(x=0, y=136, width=inner_w, height=26)
        self._voice_label.place(x=0, y=178)
        self._voice_menu.place(x=88, y=172, width=inner_w - 88, height=30)
        self._autostart_canvas.place(x=0, y=196, width=inner_w, height=26)
        self._wake_toggle_canvas.place(x=0, y=224, width=inner_w, height=26)
        self._vshutdown_toggle_canvas.place(x=0, y=252, width=inner_w, height=26)
        self._v3_toggle_canvas.place(x=0, y=280, width=inner_w, height=26)
        self._yolo_toggle_canvas.place(x=0, y=308, width=inner_w, height=26)
        self._fast_toggle_canvas.place(x=0, y=336, width=inner_w, height=26)
        self._intent_toggle_canvas.place(x=0, y=364, width=inner_w, height=26)
        self._theme_canvas.place(x=0, y=392, width=inner_w, height=26)
        self._bgimg_canvas.place(x=0, y=420, width=inner_w - 40, height=26)
        self._bgimg_clear_canvas.place(x=inner_w - 34, y=420, width=34, height=26)
        self._shortcut_canvas.place(x=0, y=448, width=inner_w, height=26)
        self._provider_canvas.place(x=0, y=476, width=inner_w, height=26)
        self._gemini_model_canvas.place(x=0, y=504, width=inner_w, height=26)
        self._ollama_model_canvas.place(x=0, y=532, width=inner_w, height=26)
        self._ollama_coder_model_canvas.place(x=0, y=560, width=inner_w, height=26)
        self._voice_choice_canvas.place(x=0, y=588, width=inner_w, height=26)
        self._stt_engine_canvas.place(x=0, y=616, width=inner_w, height=26)
        self._f5_rec_canvas.place(x=0, y=644, width=inner_w, height=26)
        self._f5_load_canvas.place(x=0, y=672, width=inner_w, height=26)
        self._f5_srv_canvas.place(x=0, y=700, width=inner_w, height=26)
        self._piper_ds_canvas.place(x=0, y=728, width=inner_w, height=26)
        self._upload_canvas.place(x=0, y=756, width=inner_w - 40, height=26)
        self._upload_clear_canvas.place(x=inner_w - 34, y=756, width=34, height=26)
        self._app_paths_canvas.place(x=0, y=784, width=inner_w, height=26)
        self._egitim_verisi_canvas.place(x=0, y=812, width=inner_w, height=26)
        self._remote_access_canvas.place(x=0, y=840, width=inner_w, height=26)
        self._thinking_canvas.place(x=0, y=868, width=inner_w, height=26)

        # BAHÇE KAMERA ayarları (etiket + 4 alan) — kaydırma bölgesine dahil
        self._garden_settings_label.place(x=0, y=896, width=inner_w)
        garden_y = 920
        for row in self._garden_setting_rows:
            row.place(x=0, y=garden_y, width=inner_w, height=28)
            garden_y += 28

        # Gerçek içerik yüksekliği (en alttaki UZAKTAN ERİŞİM satırı + boşluk).
        # _settings_body artık kaydırılabilir bir Canvas içinde olduğu için
        # panel kısa kalsa bile hiçbir satır kırpılıp kaybolmuyor — tekerlekle
        # aşağı inilebiliyor.
        content_h = garden_y + 16
        self._settings_body.configure(width=inner_w, height=content_h)
        self._settings_scroll_canvas.itemconfigure(self._settings_body_window, width=inner_w)
        self._settings_scroll_canvas.configure(scrollregion=(0, 0, inner_w, content_h))

    def _refresh_settings_status(self):
        if not hasattr(self, "_settings_status_primary"):
            return
        cfg = load_app_config()
        provider = str(cfg.get("model_provider", "gemini") or "gemini").lower()
        if provider == "ollama":
            primary = f"Ollama (çevrimdışı) — model: {cfg.get('ollama_model', 'llama3.1')}"
        else:
            gemini_ready = bool(str(cfg.get("gemini_api_key", "") or "").strip())
            primary = "Gemini hazır" if gemini_ready else "Gemini API anahtarı eksik"
        self._settings_status_primary.configure(text=primary)
        self._settings_status_secondary.configure(text="")

    def write_debug(self, text: str, level: str = "INFO"):
        clean = " ".join(str(text or "").split())
        if not clean:
            return
        self.root.after(0, self._append_debug_entry, clean, level)

    def _append_debug_entry(self, text: str, level: str = "INFO"):
        stamp = time.strftime("%H:%M:%S")
        lvl = (level or "INFO").upper()
        self._debug_entries.append((lvl, f"[{stamp}] {lvl}: {text}"))
        self._render_debug_logs()

    def _render_debug_logs(self):
        if not hasattr(self, "_debug_text"):
            return
        self._debug_text.configure(state="normal")
        self._debug_text.delete("1.0", tk.END)
        if not self._debug_entries:
            self._debug_text.insert(tk.END, "Henüz not edilebilir hata yok.\n", "info")
        else:
            for level, line in self._debug_entries:
                tag = "err" if level == "ERROR" else "warn" if level == "WARN" else "info"
                self._debug_text.insert(tk.END, line + "\n", tag)
        self._debug_text.see(tk.END)
        self._debug_text.configure(state="disabled")

    def _build_api_button(self, parent=None):
        parent = parent or self.root
        bw, bh = 154, 28
        self._api_canvas = tk.Canvas(
            parent, width=bw, height=bh,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._api_canvas.bind("<Button-1>", lambda e: self._open_api_settings())
        self._draw_api_button()

    def _draw_api_button(self):
        c = self._api_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1), (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx + sx * bl, by, fill=C_BLUE, width=1)
            c.create_line(bx, by, bx, by + sy * bl, fill=C_BLUE, width=1)
        c.create_text(bw // 2, bh // 2, text="⚙ API AYARLARI",
                      fill=C_BLUE, font=font_body_bold(10))

    def _build_fx_slider(self, parent=None):
        parent = parent or self.root
        slider_w = 280
        self._volume_label = tk.Label(
            parent,
            text=f"SES DÜZEYİ  {int(self.sound.get_volume() * 100)}%",
            fg=C_PRI,
            bg=parent.cget("bg"),
            font=font_body_bold(10),
        )
        self._volume_scale = tk.Scale(
            parent,
            from_=0,
            to=100,
            orient="horizontal",
            length=slider_w,
            showvalue=False,
            resolution=1,
            troughcolor=C_DIMMER,
            bg=parent.cget("bg"),
            fg=C_TEXT,
            activebackground=C_PRI,
            highlightthickness=0,
            borderwidth=0,
            sliderlength=18,
            width=10,
            command=self._on_volume_change,
        )
        self._volume_scale.set(int(self.sound.get_volume() * 100))

    def _on_volume_change(self, value):
        try:
            volume = max(0, min(100, int(float(value))))
        except (TypeError, ValueError):
            return
        self._volume_label.configure(text=f"SES DÜZEYİ  {volume}%")
        self.sound.set_volume(volume / 100.0)

    # ── Autostart toggle ─────────────────────────────────────────────────────
    def _autostart_plist_dst(self) -> Path:
        # Windows: Başlangıç klasöründeki kısayol (macOS LaunchAgent karşılığı)
        from make_shortcut import startup_shortcut_path
        return startup_shortcut_path()

    def _build_autostart_plist(self) -> str:
        """LaunchAgent plist'ini bu makineye göre DİNAMİK üretir.
        Sabit kullanıcı yolu (örn. /Users/...) gömmez; her bilgisayarda çalışır."""
        import sys
        python_exe = sys.executable or "/usr/bin/python3"
        py_dir     = str(Path(python_exe).parent)
        main_py    = BASE_DIR / "main.py"
        out_log    = BASE_DIR / "yerinde.log"
        err_log    = BASE_DIR / "yerinde_error.log"
        home       = Path.home()
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alp.yerinde</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_exe}</string>
        <string>{main_py}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{BASE_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{out_log}</string>
    <key>StandardErrorPath</key>
    <string>{err_log}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{py_dir}:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>HOME</key>
        <string>{home}</string>
    </dict>
</dict>
</plist>
"""

    def _is_autostart_installed(self) -> bool:
        return self._autostart_plist_dst().exists()

    def _build_autostart_button(self, parent=None):
        parent = parent or self.root
        self._autostart_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._autostart_canvas.bind("<Button-1>", lambda e: self._toggle_autostart())
        self._draw_autostart_button()

        # "Yerinde" ile uyanma + sesle kapatma aç/kapa (AYARLAR)
        self._wake_toggle_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._wake_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_cfg_bool(
                "wake_enabled", "UYANDIRMA ('YERİNDE')",
                self._wake_toggle_canvas, restart_note=True))
        self._draw_cfg_toggle(self._wake_toggle_canvas, "wake_enabled",
                              "UYANDIRMA ('YERİNDE')")

        self._vshutdown_toggle_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._vshutdown_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_cfg_bool(
                "voice_shutdown_enabled", "SESLE KAPATMA",
                self._vshutdown_toggle_canvas))
        self._draw_cfg_toggle(self._vshutdown_toggle_canvas,
                              "voice_shutdown_enabled", "SESLE KAPATMA")

        # V3 ÇEKİRDEK aç/kapa (kapalıysa eski V2 çevrimdışı motoru kullanılır)
        self._v3_toggle_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                           highlightthickness=0, cursor="hand2")
        self._v3_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_cfg_bool(
                "v3_core_enabled", "V3 ÇEKİRDEK", self._v3_toggle_canvas,
                restart_note=True))
        self._draw_cfg_toggle(self._v3_toggle_canvas, "v3_core_enabled", "V3 ÇEKİRDEK")

        # NESNE ALGILAMA (YOLO) aç/kapa
        self._yolo_toggle_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                             highlightthickness=0, cursor="hand2")
        self._yolo_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_yolo())
        self._draw_cfg_toggle(self._yolo_toggle_canvas, "yolo_enabled", "NESNE ALGILAMA")

        # HIZLI MOD (3B modeller) — düşük RAM/CPU için akıcı
        self._fast_toggle_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                             highlightthickness=0, cursor="hand2")
        self._fast_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_cfg_bool(
                "fast_mode", "HIZLI MOD (3B)", self._fast_toggle_canvas,
                restart_note=True))
        self._draw_cfg_toggle(self._fast_toggle_canvas, "fast_mode", "HIZLI MOD (3B)")

        # SADECE KOMUT MODU — yapay zekâ hiç kullanılmaz
        self._intent_toggle_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                               highlightthickness=0, cursor="hand2")
        self._intent_toggle_canvas.bind(
            "<Button-1>", lambda e: self._toggle_cfg_bool(
                "intent_only", "SADECE KOMUT MODU", self._intent_toggle_canvas,
                restart_note=True))
        self._draw_cfg_toggle(self._intent_toggle_canvas, "intent_only",
                              "SADECE KOMUT MODU")

        # TEMA seçici
        self._theme_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                       highlightthickness=0, cursor="hand2")
        self._theme_canvas.bind("<Button-1>", lambda e: self._open_theme_list())
        self._draw_simple_button(self._theme_canvas, self._theme_label(), C_ORG2)

        # ARKAPLAN RESMİ ekle/sil (TEMALAR bölümü — tema rengine ek olarak
        # kendi görselini arka plana yerleştirebilme)
        self._build_bg_image_button(parent)

        # Coqui XTTS-v2: ses kaydı + var olan kaydı yükle + modeli önceden yükle
        self._f5_rec_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                        highlightthickness=0, cursor="hand2")
        self._f5_rec_canvas.bind("<Button-1>", lambda e: self._f5_record())
        self._draw_simple_button(self._f5_rec_canvas, "🎙 SES KAYDINI BAŞLAT", C_RED)

        self._f5_load_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                         highlightthickness=0, cursor="hand2")
        self._f5_load_canvas.bind("<Button-1>", lambda e: self._f5_load_existing())
        self._draw_simple_button(self._f5_load_canvas, "📂 VAR OLAN KAYDI YÜKLE", C_GOLD)

        self._f5_srv_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                        highlightthickness=0, cursor="hand2")
        self._f5_srv_canvas.bind("<Button-1>", lambda e: self._f5_start_server())
        self._draw_simple_button(self._f5_srv_canvas, "⚙ XTTS MODELİNİ YÜKLE", C_GREEN)

        # Piper ince ayar EĞİTİM SETİ sihirbazı (XTTS'e alternatif — daha
        # sağlam kurulum, ama tek seferlik kayıt yerine bir dizi cümle ister)
        self._piper_ds_canvas = tk.Canvas(parent, height=30, bg=parent.cget("bg"),
                                          highlightthickness=0, cursor="hand2")
        self._piper_ds_canvas.bind("<Button-1>", lambda e: self._open_piper_dataset_wizard())
        self._draw_simple_button(self._piper_ds_canvas, "📋 PIPER EĞİTİM SETİ HAZIRLA", C_BLUE)

    def _draw_autostart_button(self):
        c = self._autostart_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        on = self._is_autostart_installed()
        col  = C_GREEN if on else C_MID
        icon = "◉" if on else "○"
        text = f"{icon}  AÇILIŞTA BAŞLAT  {'[AÇIK]' if on else '[KAPALI]'}"
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(10))

    def _draw_simple_button(self, c, text: str, col: str):
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw // 2, bh // 2, text=text, fill=col, font=font_body_bold(9))

    def _theme_label(self) -> str:
        key = str(get_app_config_value("ui_theme", "karanlik") or "karanlik")
        return f"TEMA: {THEMES.get(key, THEMES['karanlik'])['name']}"

    def _open_theme_list(self):
        opts = [{"label": v["name"], "value": k} for k, v in THEMES.items()]
        self._simple_picker("Tema Seç", opts,
                            str(get_app_config_value("ui_theme", "karanlik")),
                            self._apply_theme,
                            extra_link=("🔮 Konuşma animasyonu stili değiştir »",
                                       self._open_orbstyle_list))

    def _open_orbstyle_list(self):
        opts = [
            {"label": "Klasik (Parçacık Küre)", "value": "klasik"},
            {"label": "Anka (Elmas + Kanat + Alev)", "value": "anka"},
            {"label": "Anka Baloncuk (İkisinin Birleşimi)", "value": "anka_baloncuk"},
            {"label": "Destek (Yaşam Halkası — logo)", "value": "destek"},
        ]
        self._simple_picker("Konuşma Animasyonu Stili", opts,
                            str(get_app_config_value("orb_style", "klasik")),
                            self._apply_orb_style)

    def _apply_orb_style(self, key: str):
        save_app_config({"orb_style": key})
        label = {"klasik": "Klasik (Parçacık Küre)",
                 "anka": "Anka (Elmas + Kanat + Alev)",
                 "anka_baloncuk": "Anka Baloncuk (İkisinin Birleşimi)",
                 "destek": "Destek (Yaşam Halkası — logo)"}.get(key, key)
        self.write_log(f"SYS: Konuşma animasyonu '{label}' olarak ayarlandı.")

    def _build_remote_access_button(self, parent=None):
        parent = parent or self.root
        self._remote_access_canvas = tk.Canvas(
            parent, height=26,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._remote_access_canvas.bind("<Button-1>", lambda e: self._open_remote_access_manager())
        self._draw_simple_button(self._remote_access_canvas, "📱 TELEFONDAN BAĞLAN", C_GOLD)

    def _open_remote_access_manager(self):
        """
        AYARLAR > '📱 TELEFONDAN BAĞLAN' düğmesi bunu açar. YERİNDE mobil
        uygulamasının (Android/iOS) bu bilgisayara bağlanması için gereken
        IP adresi, port ve PIN kodunu gösterir.
        """
        from core import remote_server

        popup = tk.Toplevel(self.root)
        popup.title("Telefondan Bağlan")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)
        w = 460

        tk.Label(popup, text="📱 Telefondan Bağlan",
                bg=C_PANEL, fg=C_PRI, font=font_body_bold(11)
                ).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(popup, text="YERİNDE mobil uygulamasını açık bu bilgisayarla "
                "AYNI Wi-Fi ağındaysan (ya da Tailscale gibi bir VPN kurduysan), "
                "aşağıdaki adres ve PIN ile bağlanabilirsin.",
                bg=C_PANEL, fg=C_MID, font=font_body(9), wraplength=w - 32,
                justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        info_frame = tk.Frame(popup, bg=C_DIMMER)
        info_frame.pack(fill="x", padx=16, pady=(0, 10))
        info_label = tk.Label(info_frame, text="", bg=C_DIMMER, fg=C_TEXT,
                              font=font_body(11), justify="left", anchor="w",
                              padx=10, pady=10)
        info_label.pack(fill="x")

        status_label = tk.Label(popup, text="", bg=C_PANEL, fg=C_MID,
                                font=font_body(9))
        status_label.pack(anchor="w", padx=16, pady=(0, 10))

        def refresh():
            ip = remote_server.get_local_ip()
            pin = remote_server.get_or_create_pin()
            info_label.configure(text=(
                f"Adres:  {ip}\n"
                f"Port:   {remote_server.PORT}\n"
                f"PIN:    {pin}"
            ))
            baglantili = remote_server.is_phone_connected()
            status_label.configure(
                text=("🟢 Bir telefon bağlı" if baglantili else "⚪ Henüz bağlı telefon yok"),
                fg=(C_GREEN if baglantili else C_MID),
            )
            popup.after(2000, refresh)

        refresh()

        btn_frame = tk.Frame(popup, bg=C_PANEL)
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        def do_regenerate():
            remote_server.regenerate_pin()
            self.write_log("SYS: Uzaktan erişim PIN'i yenilendi.")
            refresh()

        regen_canvas = tk.Canvas(btn_frame, height=30, width=w - 32, bg=C_PANEL,
                                 highlightthickness=0, cursor="hand2")
        regen_canvas.pack(side="left")
        regen_canvas.bind("<Button-1>", lambda e: do_regenerate())
        self._draw_simple_button(regen_canvas, "🔄 YENİ PIN OLUŞTUR", C_BLUE)

    # ── Uygulama yolları yöneticisi ──────────────────────────────────────────
    def _open_egitim_verisi_manager(self):
        """
        AYARLAR > '🎓 EĞİTİM VERİSİ' düğmesi bunu açar. YERİNDE kullandıkça
        arka planda biriken etkileşim verisini (HabitLearner) gösterir ve
        kendi çevrimdışı modelini eğitmek için JSONL olarak dışa aktarmanı
        sağlar.
        """
        from backend.habits import HabitLearner

        popup = tk.Toplevel(self.root)
        popup.title("Eğitim Verisi")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)
        w = 480

        tk.Label(popup, text="🎓 Eğitim Verisi (Kendi Modelini Eğitmek İçin)",
                bg=C_PANEL, fg=C_PRI, font=font_body_bold(11)
                ).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(popup, text="YERİNDE kullandıkça her etkileşim, ileride kendi "
                "çevrimdışı modelini ince ayarla (fine-tuning) eğitebilmen için "
                "arka planda kaydediliyor.",
                bg=C_PANEL, fg=C_MID, font=font_body(9), wraplength=w - 32,
                justify="left").pack(anchor="w", padx=16, pady=(0, 10))

        stats_frame = tk.Frame(popup, bg=C_DIMMER)
        stats_frame.pack(fill="x", padx=16, pady=(0, 10))
        stats_label = tk.Label(stats_frame, text="", bg=C_DIMMER, fg=C_TEXT,
                               font=font_body(10), justify="left", anchor="w",
                               padx=10, pady=10)
        stats_label.pack(fill="x")

        def refresh_stats():
            hl = HabitLearner("memory/habits.json")
            s = hl.dataset_stats()
            rotalar = ", ".join(f"{k} ({v})" for k, v in s["rotalar"].items()) or "—"
            stats_label.configure(text=(
                f"Toplam kaydedilen etkileşim: {s['toplam_olay']}\n"
                f"Eğitime uygun örnek: {s['egitime_uygun']}\n"
                f"Rotalar: {rotalar}"
            ))

        refresh_stats()

        btn_frame = tk.Frame(popup, bg=C_PANEL)
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        def _model_egitimi_dir() -> Path:
            """YERİNDE'nin KENDİ kurulum klasöründeki model-egitimi klasörü —
            Masaüstü/Çalışmalarım'da DEĞİL, doğrudan burada (script, kurulum
            dosyaları ve eğitim verisi hep AYNI yerde durur)."""
            d = Path(__file__).resolve().parent / "model-egitimi"
            d.mkdir(parents=True, exist_ok=True)
            return d

        def do_export():
            from actions.model_egitimi import model_egitimi_dir
            hl = HabitLearner("memory/habits.json")
            dst_folder = model_egitimi_dir()
            msg = hl.export_dataset(dst_folder / "egitim_verisi.jsonl")
            self.write_log(f"SYS: {msg}")
            refresh_stats()

        def do_import():
            from tkinter import filedialog
            path = filedialog.askopenfilename(
                title="İçe aktarılacak eğitim verisi (.jsonl) dosyasını seç",
                filetypes=[
                    ("JSONL dosyaları", "*.jsonl"),
                    ("Tüm dosyalar", "*.*"),
                ],
            )
            if not path:
                return
            hl = HabitLearner("memory/habits.json")
            msg = hl.import_dataset(path)
            self.write_log(f"SYS: {msg}")
            refresh_stats()

        export_canvas = tk.Canvas(btn_frame, height=30, width=w - 32 - 96, bg=C_PANEL,
                                  highlightthickness=0, cursor="hand2")
        export_canvas.pack(side="left", padx=(0, 6))
        export_canvas.bind("<Button-1>", lambda e: do_export())
        self._draw_simple_button(export_canvas, "📤 JSONL OLARAK DIŞA AKTAR", C_GOLD)

        refresh_canvas = tk.Canvas(btn_frame, height=30, width=90, bg=C_PANEL,
                                   highlightthickness=0, cursor="hand2")
        refresh_canvas.pack(side="left")
        refresh_canvas.bind("<Button-1>", lambda e: refresh_stats())
        self._draw_simple_button(refresh_canvas, "🔄 YENİLE", C_BLUE)

        btn_frame2 = tk.Frame(popup, bg=C_PANEL)
        btn_frame2.pack(fill="x", padx=16, pady=(0, 16))

        import_canvas = tk.Canvas(btn_frame2, height=30, width=w - 32, bg=C_PANEL,
                                  highlightthickness=0, cursor="hand2")
        import_canvas.pack(side="left")
        import_canvas.bind("<Button-1>", lambda e: do_import())
        self._draw_simple_button(import_canvas, "📥 JSONL'DEN İÇE AKTAR (başka bir yedekten/kurulumdan)", C_BLUE)

        tk.Label(popup, text="Kendi çevrimdışı modelini eğitip (LoRA) Ollama'da "
                "kullanabileceğin bir GGUF dosyasına çevirmek için, aşağıdaki "
                "düğme YERİNDE'nin kendi 'model-egitimi' klasöründeki hazır "
                "scripti kullanır. Gerçek eğitim internet + zaman gerektirdiği "
                "için YENİ bir terminal penceresinde çalışır (YERİNDE'yi kilitlemez). "
                "Bu işlemi sesle de tetikleyebilirsin: 'eğitimi başlat' / 'ggufa dönüştür'.",
                bg=C_PANEL, fg=C_MID, font=font_body(9), wraplength=w - 32,
                justify="left").pack(anchor="w", padx=16, pady=(4, 6))

        def do_start_training():
            from tkinter import messagebox
            from actions.model_egitimi import egitim_baslat_command
            sonuc = egitim_baslat_command()
            self.write_log(f"SYS: {sonuc}")
            if "başlattım" in sonuc:
                messagebox.showinfo("Kendi Modelini Eğit", sonuc)
            elif "İLK KEZ" in sonuc:
                messagebox.showinfo("Kendi Modelini Eğit — İlk Kurulum Gerekiyor", sonuc)
            else:
                messagebox.showwarning("Kendi Modelini Eğit", sonuc)

        train_canvas = tk.Canvas(popup, height=30, width=w - 32, bg=C_PANEL,
                                 highlightthickness=0, cursor="hand2")
        train_canvas.pack(anchor="w", padx=16, pady=(0, 16))
        train_canvas.bind("<Button-1>", lambda e: do_start_training())
        self._draw_simple_button(train_canvas, "🧠 KENDİ MODELİNİ EĞİT (GGUF'a Dönüştür)", C_GOLD)

    def _open_app_paths_manager(self):
        """
        AYARLAR > '📁 UYGULAMA YOLLARI' düğmesi bunu açar. Sesle
        çalıştıracağın uygulamalar için elle tam yol seçmeni sağlar —
        otomatik bulma yanlış/eksikse (ya da uygulama standart olmayan bir
        yere kuruluysa) burada kayıtlı yol HER ZAMAN önceliklidir.
        """
        from actions.open_app import (get_custom_app_paths, set_custom_app_path,
                                      remove_custom_app_path)

        popup = tk.Toplevel(self.root)
        popup.title("Uygulama Yolları")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)
        w = 560

        list_outer = tk.Frame(popup, bg=C_PANEL)
        list_outer.pack(fill="x", padx=16, pady=(12, 6))

        # NOT: Görünür bir kaydırma çubuğu YOK — kaydırma sadece fare
        # tekerleğiyle (dikey) ve Shift+tekerlek ile (yatay) yapılır. İçerik
        # (uzun dosya yolları) canvas'tan geniş olursa otomatik olarak yatay
        # kaydırılabilir hale gelir.
        list_canvas = tk.Canvas(list_outer, bg=C_PANEL, highlightthickness=0, height=180)
        list_canvas.pack(fill="both", expand=True)

        list_frame = tk.Frame(list_canvas, bg=C_PANEL)
        list_window = list_canvas.create_window((0, 0), window=list_frame, anchor="nw")

        def _on_list_frame_configure(_event=None):
            list_canvas.configure(scrollregion=list_canvas.bbox("all"))

        def _on_list_canvas_configure(event):
            # İçerik canvas'tan DAR ise onu canvas genişliğine uydur (boşluk
            # kalmasın); GENİŞ ise (uzun bir yol varsa) olduğu gibi bırak ki
            # yatay kaydırma anlamlı olsun.
            needed_w = list_frame.winfo_reqwidth()
            list_canvas.itemconfigure(list_window, width=max(event.width, needed_w))

        list_frame.bind("<Configure>", _on_list_frame_configure)
        list_canvas.bind("<Configure>", _on_list_canvas_configure)

        def _list_wheel_vertical(event):
            list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _list_wheel_horizontal(event):
            list_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        def _list_wheel_vertical_linux(event):
            list_canvas.yview_scroll(-3 if event.num == 4 else 3, "units")
            return "break"

        def _list_wheel_horizontal_linux(event):
            list_canvas.xview_scroll(-3 if event.num == 4 else 3, "units")
            return "break"

        def _bind_list_wheel(_e=None):
            list_canvas.bind_all("<MouseWheel>", _list_wheel_vertical)
            list_canvas.bind_all("<Shift-MouseWheel>", _list_wheel_horizontal)
            list_canvas.bind_all("<Button-4>", _list_wheel_vertical_linux)
            list_canvas.bind_all("<Button-5>", _list_wheel_vertical_linux)
            list_canvas.bind_all("<Shift-Button-4>", _list_wheel_horizontal_linux)
            list_canvas.bind_all("<Shift-Button-5>", _list_wheel_horizontal_linux)

        def _unbind_list_wheel(_e=None):
            for seq in ("<MouseWheel>", "<Shift-MouseWheel>", "<Button-4>",
                       "<Button-5>", "<Shift-Button-4>", "<Shift-Button-5>"):
                list_canvas.unbind_all(seq)

        list_canvas.bind("<Enter>", _bind_list_wheel)
        list_canvas.bind("<Leave>", _unbind_list_wheel)

        def refresh():
            for child in list_frame.winfo_children():
                child.destroy()
            paths = get_custom_app_paths()
            if not paths:
                tk.Label(list_frame, text="Henüz kayıtlı özel yol yok.",
                        bg=C_PANEL, fg=C_MID, font=font_body(9)).pack(anchor="w")
            for name, path in sorted(paths.items()):
                row = tk.Frame(list_frame, bg=C_DIMMER)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=f"{name}", bg=C_DIMMER, fg=C_PRI,
                        font=font_body_bold(10), anchor="w", width=14
                        ).pack(side="left", padx=(6, 2), pady=4)
                tk.Label(row, text=path, bg=C_DIMMER, fg=C_TEXT,
                        font=font_body(9), anchor="w").pack(side="left", padx=2, pady=4)
                delbtn = tk.Label(row, text="✕", bg=C_DIMMER, fg=C_RED,
                                  font=font_body_bold(10), cursor="hand2", padx=8)
                delbtn.pack(side="right", padx=(2, 6))
                delbtn.bind("<Button-1>", lambda e, n=name: (remove_custom_app_path(n),
                                                             refresh(),
                                                             self.write_log(f"SYS: '{n}' için özel yol silindi.")))

        refresh()

        tk.Frame(popup, bg=C_MID, height=1).pack(fill="x", padx=16, pady=(4, 10))

        add_frame = tk.Frame(popup, bg=C_PANEL)
        add_frame.pack(fill="x", padx=16, pady=(0, 14))
        tk.Label(add_frame, text="Yeni uygulama adı (sesle söyleyeceğin isim):",
                 bg=C_PANEL, fg=C_TEXT, font=font_body(9)).pack(anchor="w")
        name_entry = tk.Entry(add_frame, bg=C_DIMMER, fg=C_TEXT,
                              insertbackground=C_TEXT, font=font_body(10),
                              relief="flat")
        name_entry.pack(fill="x", pady=(4, 8), ipady=4)

        def browse_and_add():
            app_name = name_entry.get().strip()
            if not app_name:
                self.write_log("UYARI: Önce bir uygulama adı yaz (ör. 'photoshop').")
                return
            from tkinter import filedialog
            filetypes = ([("Çalıştırılabilir", "*.exe"),
                         ("Web Aracı (HTML)", "*.html *.htm"),
                         ("Tümü", "*.*")]
                        if platform.system() == "Windows" else
                        [("Web Aracı (HTML)", "*.html *.htm"), ("Tümü", "*")])
            path = filedialog.askopenfilename(title=f"'{app_name}' için dosya seç",
                                              filetypes=filetypes)
            if not path:
                return
            msg = set_custom_app_path(app_name, path)
            self.write_log(f"SYS: {msg}")
            name_entry.delete(0, "end")
            refresh()

        browse_btn = tk.Label(add_frame, text="📂 Dosya Seç ve Kaydet", bg=C_BLUE,
                              fg="#ffffff", font=font_body_bold(10), padx=14, pady=8,
                              cursor="hand2")
        browse_btn.pack(anchor="w")
        browse_btn.bind("<Button-1>", lambda e: browse_and_add())

        hint = ("Not: Kayıtlı bir yol, otomatik bulmadan HER ZAMAN önceliklidir. "
               "Uygulamayı sesle her açtığında bu tam dosya çalıştırılır. "
               ".exe uygulamalarının yanı sıra .html araçları (akış şeması, "
               "çarkıfelek, satranç, yerinde kodlama aracı vb.) da eklenebilir — "
               "bunlar otomatik olarak tarayıcıda açılır.")
        tk.Label(popup, text=hint, bg=C_PANEL, fg=C_MID, font=font_body(8),
                 wraplength=w - 32, justify="left").pack(padx=16, pady=(0, 12), anchor="w")

        try:
            self.root.update_idletasks()
            popup.update_idletasks()
            h = popup.winfo_reqheight()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - h) // 2)
            popup.geometry(f"{w}x{h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{w}x420")
        popup.after(120, lambda: popup.focus_force())

    def _apply_theme(self, key: str):
        save_app_config({"ui_theme": key})
        self._draw_simple_button(self._theme_canvas, self._theme_label(), C_ORG2)
        self.write_log(f"SYS: Tema '{THEMES[key]['name']}' seçildi — "
                       "yeniden başlatınca tüm arayüze uygulanır.")

    # ── Sesle TEMA + konuşma animasyonu kontrolü ────────────────────────────
    # NOT: Bu, 'Arkaplanlar/' klasöründeki hazır GÖRSELİ değiştiren
    # set_bg_image_builtin/clear_bg_image_voice'dan (arkaplan_command) TAMAMEN
    # AYRI bir özellik — o pencerenin arkaplan RESMİNİ değiştirir, bu ise
    # tüm arayüzün RENK TEMASINI (THEMES) ve konuşma animasyonu stilini
    # (orb_style) değiştirir. İkisi de sesle tetiklenebilir ama farklı
    # sözcüklerle: 'arkaplanı açık/koyu/sade yap' → resim; 'temayı X yap' /
    # 'X temaya geç' → renk teması. (bkz. actions/… ve tool_defs.py)
    _VOICE_THEME_MAP = {
        "acik": "krem", "açık": "krem", "krem": "krem",
        "mavi": "pico_mavi",
        "yesil": "pico_yesil", "yeşil": "pico_yesil",
        "mor": "mor",
        "turuncu": "gunes", "amber": "gunes",
        "kirmizi": "kirmizi", "kırmızı": "kirmizi",
        "karanlik": "karanlik", "karanlık": "karanlik", "sade": "karanlik",
    }

    # Her temanın, elimizde hazır görseli varsa eşleşen bir arkaplan resmiyle
    # birlikte gelir (bkz. BUILTIN_BG_FILES). Burada olmayan temalar
    # (sade/karanlık — bilerek, o zaten arkaplansız düz renk) arkaplan
    # resmini TEMİZLER, düz tema rengine
    # döner; en azından yanlış renkte bir görsel kalmamış olur.
    _THEME_TO_BG = {"krem": "acik", "pico_yesil": "yesil", "mor": "mor",
                    "kirmizi": "kirmizi", "pico_mavi": "mavi", "gunes": "turuncu"}

    def _do_restart(self):
        """YERİNDE'yi sessizce yeniden başlatır.

        NOT: Bu fonksiyon önceden os.execv kullanıyordu (POSIX'te gerçekten
        süreci aynı PID üzerinde değiştirdiği için teorik olarak güvenli
        görünüyordu). Ama pratikte 'tema değiştir' sesli komutundan sonra
        bazı kurulumlarda restart'ın güvenilmez çalıştığı bildirildi — en
        olası sebep, os.execv'in Python'ın normal temizlik yolundan (atexit,
        __del__, context manager'lar) GEÇMEMESİ: PortAudio/ALSA gibi C
        uzantılarının açtığı ses akışı tanıtıcıları (file descriptor)
        Python'ın CLOEXEC varsayılanına uymayabiliyor, bu da yeni süreç aynı
        ses cihazını açmaya çalışırken "device busy" gibi sessiz bir
        başarısızlığa yol açabiliyor — ayrıca execv başarısız olursa (ör.
        sys.argv'nin göreli yolu o anki CWD ile uyuşmazsa) hiçbir hata
        yakalanmadan Tkinter'ın after() callback'i içinde sessizce yutuluyor,
        kullanıcı hiçbir şey görmüyor.

        Windows sürümünde zaten kullanılan, platformdan bağımsız daha sağlam
        desene geçiyoruz: yeni süreci TAMAMEN BAĞIMSIZ başlatıp (BASE_DIR'den
        MUTLAK yol ile, sys.argv'ye güvenmeden), ardından eski süreçten
        os._exit(0) ile çıkıyoruz — hata olursa da artık loglanıyor."""
        import sys, subprocess
        try:
            self.sound.stop_all()
        except Exception:
            pass
        python = sys.executable
        main_py = str(BASE_DIR / "main.py")
        try:
            subprocess.Popen([python, main_py], cwd=str(BASE_DIR), close_fds=True,
                             start_new_session=True)
        except Exception as e:
            try:
                self.write_log(f"ERR: Yeniden başlatma başarısız — {e}")
            except Exception:
                pass
            return
        os._exit(0)

    def request_restart(self, delay_ms: int = 5000):
        """Sesli onay cümlesinin (TTS) bitmesi için birkaç saniye bekleyip
        YERİNDE'yi sessizce kendi kendine yeniden başlatır. root.after
        herhangi bir thread'den güvenle çağrılabilir (Tk ana thread'ine
        zamanlanır)."""
        self.write_log(f"SYS: Ayarları uygulamak için {delay_ms // 1000} "
                       "saniye içinde kendimi yeniden başlatacağım...")
        self.root.after(delay_ms, self._do_restart)

    def set_theme_by_voice(self, word: str) -> str:
        """'açık'/'krem' → Krem (Aydınlık); 'mavi' → Pico Mavi; 'yeşil' →
        Pico Yeşil; 'mor' → Lavanta (Mavi-Mor); 'turuncu' → Amber; 'kırmızı'
        → Kızıl (Ateş); 'sade'/'karanlık' → Karanlık (Turkuaz) + konuşma
        animasyonunu da birlikte ayarlar: sade/karanlıkta Klasik (1.),
        diğerlerinde Anka Baloncuk (3.). Yedi temanın altısının (karanlık
        hariç hepsinin) eşleşen hazır bir arkaplan resmi var, otomatik
        uygulanır; karanlık/sade'de ise arkaplan temizlenip düz tema
        rengine dönülür. Ayarları kaydettikten sonra birkaç saniye içinde
        kendini sessizce yeniden başlatır ki değişiklik hemen görünsün."""
        key = self._VOICE_THEME_MAP.get((word or "").strip().lower())
        if not key:
            return "Tanımadığım bir tema — 'açık', 'krem', 'mavi', 'yeşil', 'mor', 'turuncu', 'kırmızı' ya da 'sade' diyebilirsin."
        orb_key = "klasik" if key == "karanlik" else "anka_baloncuk"
        save_app_config({"ui_theme": key, "orb_style": orb_key})
        try:
            self._draw_simple_button(self._theme_canvas, self._theme_label(), C_ORG2)
        except Exception:
            pass
        bg_mod = self._THEME_TO_BG.get(key)
        try:
            if bg_mod:
                self.set_bg_image_builtin(bg_mod)
            else:
                self._clear_bg_image()
        except Exception:
            pass
        orb_label = "Klasik" if orb_key == "klasik" else "Anka Baloncuk"
        self.write_log(f"SYS: Tema '{THEMES[key]['name']}' + konuşma animasyonu "
                       f"'{orb_label}' ayarlandı.")
        self.request_restart()
        return (f"Temayı {THEMES[key]['name']} yaptım, konuşma animasyonunu da "
               f"{orb_label} olarak ayarladım — birkaç saniye içinde ayarların "
               "uygulanması için kendimi yeniden başlatacağım.")

    # ── Arkaplan resmi (TEMALAR) ──────────────────────────────────────────────
    # Kullanıcı kendi resmini arayüzün ana arka planına (self.bg canvas'ı)
    # yerleştirebilir. Resim BGIMG_DIR içine kopyalanır (orijinal dosya silinse/
    # taşınsa bile çalışmaya devam eder), config'e sadece dosya adı yazılır.
    def _bg_image_path(self):
        """Kayıtlı arkaplan resminin tam yolunu döndürür (yoksa None)."""
        name = str(get_app_config_value("ui_bg_image", "") or "")
        if not name:
            return None
        p = BGIMG_DIR / name
        return p if p.exists() else None

    def _load_bg_image(self):
        """Kayıtlı arkaplan resmini mevcut pencere boyutuna göre (kırparak/
        kaplayarak) ölçekleyip self._bg_photo içine yükler. Kayıtlı resim
        yoksa ya da açılamazsa self._bg_photo = None olur (tema rengi kalır).
        """
        path = self._bg_image_path()
        if not path:
            self._bg_photo = None
            return
        try:
            img = Image.open(path).convert("RGB")
            iw, ih = img.size
            tw, th = max(1, self.W), max(1, self.H)
            # "cover" ölçekleme: oranı bozmadan pencereyi tam kapla, taşanı kırp
            scale = max(tw / iw, th / ih)
            nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            x0 = (nw - tw) // 2
            y0 = (nh - th) // 2
            img = img.crop((x0, y0, x0 + tw, y0 + th))
            # Üzerindeki panel/metinlerin okunabilir kalması için hafif karartma
            overlay = Image.new("RGB", (tw, th), (0, 0, 0))
            img = Image.blend(img, overlay, 0.35)
            self._bg_photo = ImageTk.PhotoImage(img)
        except Exception as e:
            self._bg_photo = None
            try:
                self.write_log(f"ERR: Arkaplan resmi yüklenemedi — {e}")
            except Exception:
                pass

    def _build_bg_image_button(self, parent=None):
        parent = parent or self.root
        self._bgimg_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._bgimg_canvas.bind("<Button-1>", lambda e: self._pick_bg_image())
        self._draw_bg_image_button()

        self._bgimg_clear_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._bgimg_clear_canvas.bind("<Button-1>", lambda e: self._clear_bg_image())
        self._draw_bg_image_clear_button()

    def _draw_bg_image_button(self):
        c = self._bgimg_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("ui_bg_image", "") or "")
        label = f"🖼️ ARKAPLAN: {current}" if current else "🖼️ ARKAPLAN RESMİ EKLE"
        col = C_PRI
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=label, fill=col, font=font_body_bold(10))

    def _draw_bg_image_clear_button(self):
        c = self._bgimg_clear_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 34
        bh = int(c["height"])
        c.delete("all")
        has_img = bool(get_app_config_value("ui_bg_image", "") or "")
        col = C_RED if has_img else C_DIM
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text="✕", fill=col, font=font_body_bold(12))

    def _pick_bg_image(self):
        try:
            self._pick_bg_image_impl()
        except Exception as e:
            self.write_log(f"ERR: Arkaplan resmi seçilemedi — {e}")

    def _pick_bg_image_impl(self):
        from tkinter import filedialog
        import shutil, time as _time
        path = filedialog.askopenfilename(
            title="Arkaplan resmi seç",
            filetypes=[
                ("Resim dosyaları", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("Tüm dosyalar", "*.*"),
            ],
        )
        if not path:
            return
        src = Path(path)
        BGIMG_DIR.mkdir(parents=True, exist_ok=True)
        dest_name = f"arkaplan_{int(_time.time())}{src.suffix.lower()}"
        dest = BGIMG_DIR / dest_name
        shutil.copyfile(src, dest)
        # Eski özel arkaplan dosyasını temizle (yer kaplamasın) — ama kalıcı
        # BUILTIN_BG_FILES görsellerini asla silme (aksi halde bir renk
        # temasından özel resme geçince o rengin görseli kalıcı kaybolurdu).
        old_name = str(get_app_config_value("ui_bg_image", "") or "")
        if old_name and old_name not in BUILTIN_BG_FILES.values():
            old_path = BGIMG_DIR / old_name
            if old_path.exists() and old_path != dest:
                try:
                    old_path.unlink()
                except Exception:
                    pass
        save_app_config({"ui_bg_image": dest_name})
        self._load_bg_image()
        self._draw_bg_image_button()
        self._draw_bg_image_clear_button()
        self.write_log(f"SYS: '{src.name}' arkaplan resmi olarak ayarlandı.")

    def _clear_bg_image(self):
        old_name = str(get_app_config_value("ui_bg_image", "") or "")
        if old_name and old_name not in BUILTIN_BG_FILES.values():
            old_path = BGIMG_DIR / old_name
            if old_path.exists():
                try:
                    old_path.unlink()
                except Exception:
                    pass
        save_app_config({"ui_bg_image": ""})
        self._bg_photo = None
        self._draw_bg_image_button()
        self._draw_bg_image_clear_button()
        self.write_log("SYS: Arkaplan resmi kaldırıldı — tema rengine dönüldü.")

    # ── Sesle arkaplan kontrolü (dosya seçici GEREKMEZ) ────────────────────────
    # 'arkaplanı açık/koyu yap' / 'arkaplanı sadeleştir' gibi sesli komutlarla
    # tetiklenir (bkz. actions/arkaplan.py). Hem Gemini hem Ollama modunda
    # aynı bu metotlar çağrılır.
    def set_bg_image_builtin(self, mod: str) -> str:
        """'açık' ya da 'koyu' — projeyle birlikte gelen hazır arkaplanlardan
        birini dosya seçiciye gerek kalmadan anında uygular."""
        fname = BUILTIN_BG_FILES.get(mod)
        if not fname:
            return "Tanımadığım bir arkaplan modu — 'açık' ya da 'koyu' diyebilirsin."
        path = BGIMG_DIR / fname
        if not path.exists():
            return f"'{fname}' arkaplan dosyası bulunamadı — proje kurulumu eksik olabilir."
        save_app_config({"ui_bg_image": fname})
        self._load_bg_image()
        try:
            self._draw_bg_image_button()
            self._draw_bg_image_clear_button()
        except Exception:
            pass
        self.write_log(f"SYS: Arkaplan '{mod}' moduna geçirildi.")
        return f"Arkaplanı {mod} yaptım!"

    def clear_bg_image_voice(self) -> str:
        """'sade' ya da 'normal' — özel arkaplanı kaldırır, düz tema rengine
        döner. Var olan _clear_bg_image ile aynı işi yapar, sadece sesli
        komuttan çağrılabilecek bir dönüş metni üretir."""
        self._clear_bg_image()
        return "Arkaplanı sadeleştirdim!"

    def _simple_picker(self, title: str, options: list, current: str, on_pick,
                       extra_link: tuple | None = None):
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)
        extra_h = 34 if extra_link else 0
        w, h = 420, len(options) * 36 + 70 + extra_h
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - h) // 2)
            popup.geometry(f"{w}x{h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{w}x{h}")
        tk.Label(popup, text=title, bg=C_PANEL, fg=C_PRI,
                 font=font_body_bold(11)).pack(pady=(10, 6))
        for opt in options:
            sel = opt["value"] == current
            b = tk.Label(popup, text=("● " if sel else "○ ") + opt["label"],
                         bg=C_DIMMER if sel else C_PANEL,
                         fg=C_PRI if sel else C_TEXT,
                         font=font_body(10), anchor="w", padx=12, cursor="hand2")
            b.pack(fill="x", padx=12, pady=1)
            b.bind("<Button-1>", lambda e, v=opt["value"]: (on_pick(v), popup.destroy()))
        if extra_link:
            link_text, link_action = extra_link
            lk = tk.Label(popup, text=link_text, bg=C_PANEL, fg=C_GOLD,
                         font=font_body(9), cursor="hand2")
            lk.pack(pady=(8, 4))
            lk.bind("<Button-1>", lambda e: (popup.destroy(), link_action()))
        popup.after(120, lambda: popup.focus_force())

    # ── Piper eğitim seti sihirbazı ──────────────────────────────────────────
    def _open_piper_dataset_wizard(self):
        """
        AYARLAR > '📋 PIPER EĞİTİM SETİ HAZIRLA' düğmesi bunu açar.
        Sırayla cümle gösterir → kaydet → otomatik sıradakine geçer.
        Kayıt MicStream üzerinden (arka plan iş parçacığında) yapılır, bu
        yüzden pencere kaydederken donmaz.
        """
        from actions import piper_dataset as pd
        import threading

        popup = tk.Toplevel(self.root)
        popup.title("Piper Eğitim Seti")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)
        w, h = 520, 260
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - h) // 2)
            popup.geometry(f"{w}x{h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{w}x{h}")

        title_lbl = tk.Label(popup, text="Piper Eğitim Seti", bg=C_PANEL, fg=C_PRI,
                             font=font_body_bold(12))
        title_lbl.pack(pady=(12, 4))

        progress_lbl = tk.Label(popup, text="", bg=C_PANEL, fg=C_GOLD,
                                font=font_body_bold(10))
        progress_lbl.pack(pady=(0, 8))

        sentence_lbl = tk.Label(popup, text="", bg=C_DIMMER, fg=C_TEXT,
                                font=font_body(11), wraplength=460, justify="center",
                                padx=16, pady=14)
        sentence_lbl.pack(fill="x", padx=16)

        status_lbl = tk.Label(popup, text="", bg=C_PANEL, fg=C_MID,
                              font=font_body(9), wraplength=480, justify="center")
        status_lbl.pack(pady=(8, 4))

        btn_row = tk.Frame(popup, bg=C_PANEL)
        btn_row.pack(pady=10)

        def refresh_prompt():
            idx = pd.next_sentence_index()
            state = pd._load_state()
            done, total = len(state.get("recorded", [])), len(pd.SENTENCES)
            progress_lbl.configure(text=f"{done}/{total} cümle kaydedildi")
            if idx is None:
                sentence_lbl.configure(text="🎉 Tüm cümleler kaydedildi! "
                                            "'Paketle' ile veri kümesini dışa aktarabilirsin.")
            else:
                sentence_lbl.configure(text=f"{idx + 1}. cümle:\n\n\"{pd.SENTENCES[idx]}\"")

        def do_record():
            record_btn.configure(state="disabled") if hasattr(record_btn, "configure") else None
            status_lbl.configure(text="🎙 Dinliyorum — konuş, sessizlik olunca otomatik durur...")

            def run():
                msg = pd.record_sentence(on_log=lambda m: None)
                def apply():
                    status_lbl.configure(text=msg)
                    refresh_prompt()
                    try:
                        record_btn.configure(state="normal")
                    except Exception:
                        pass
                try:
                    popup.after(0, apply)
                except Exception:
                    apply()
            threading.Thread(target=run, daemon=True).start()

        def do_package():
            status_lbl.configure(text="📦 Paketleniyor...")
            def run():
                msg = pd.package_dataset(on_log=self.write_log)
                popup.after(0, lambda: status_lbl.configure(text=msg))
            threading.Thread(target=run, daemon=True).start()

        record_btn = tk.Label(btn_row, text="🎙 Kaydet", bg=C_RED, fg="#ffffff",
                              font=font_body_bold(10), padx=16, pady=8, cursor="hand2")
        record_btn.pack(side="left", padx=6)
        record_btn.bind("<Button-1>", lambda e: do_record())

        package_btn = tk.Label(btn_row, text="📦 Paketle", bg=C_GREEN, fg=C_BG,
                               font=font_body_bold(10), padx=16, pady=8, cursor="hand2")
        package_btn.pack(side="left", padx=6)
        package_btn.bind("<Button-1>", lambda e: do_package())

        close_btn = tk.Label(btn_row, text="✕ Kapat", bg=C_DIMMER, fg=C_TEXT,
                             font=font_body_bold(10), padx=16, pady=8, cursor="hand2")
        close_btn.pack(side="left", padx=6)
        close_btn.bind("<Button-1>", lambda e: popup.destroy())

        refresh_prompt()
        popup.after(120, lambda: popup.focus_force())

    # ── Coqui XTTS-v2 düğmeleri ──────────────────────────────────────────────
    def _f5_record(self):
        import threading
        def run():
            try:
                from actions.voice_sample import record_voice_sample
                self.write_log("SYS: 🎙 Kayıt başlıyor — 10 saniye doğal konuş...")
                msg = record_voice_sample(10, on_log=self.write_log)
                self.write_log(f"SYS: {msg}")
                self._draw_voice_choice_button()
            except Exception as e:
                self.write_log(f"ERR: Kayıt alınamadı — {e}")
        threading.Thread(target=run, daemon=True).start()

    def _f5_load_existing(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Ses kaydı seç (WAV)",
            filetypes=[("Ses dosyaları", "*.wav *.mp3 *.m4a"), ("Tümü", "*.*")])
        if not path:
            return
        try:
            import shutil
            from pathlib import Path as _P
            target = _P(__file__).resolve().parent / "voices" / "kendi_sesim.wav"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, target)
            save_app_config({"offline_voice_choice": f"xtts:{target}"})
            self._draw_voice_choice_button()
            self.write_log(f"SYS: Ses kaydı yüklendi ({_P(path).name}) ve "
                           "'KENDİ SESİM' profili olarak ayarlandı.")
        except Exception as e:
            self.write_log(f"ERR: Kayıt yüklenemedi — {e}")

    def _f5_start_server(self):
        """
        'XTTS MODELİNİ YÜKLE' düğmesi. Eskiden burada ayrı bir F5-TTS sunucu
        SÜRECİ başlatılıyordu; Coqui XTTS-v2 aynı Python sürecinde (in-process)
        çalıştığı için artık ayrı sunucuya gerek yok — bu düğme sadece modeli
        ÖNCEDEN indirip belleğe yükler ki 'sesimi kaydet' sonrası ilk cevap
        beklemesin. Yüklemezsen de sorun değil: ilk gerçek kullanımda otomatik
        yüklenir, sadece o ilk seferde birkaç dakika sürebilir.
        """
        import threading

        def run():
            try:
                import os
                os.environ.setdefault("COQUI_TOS_AGREED", "1")
                self.write_log("SYS: ⚙ Coqui XTTS-v2 indiriliyor/yükleniyor "
                               "(ilk sefer ~2 GB inebilir, birkaç dakika sürebilir)...")
                from TTS.api import TTS
                TTS("tts_models/multilingual/multi-dataset/xtts_v2")
                self.write_log("SYS: XTTS-v2 hazır — 'sesimi kaydet' dedikten "
                               "sonra ilk cevap da hızlı gelecek.")
            except ModuleNotFoundError as e:
                top = (e.name or "").split(".")[0]
                if top in ("TTS", "coqui_tts", ""):
                    self.write_log("ERR: Coqui XTTS-v2 kurulu değil — pip install coqui-tts")
                else:
                    self.write_log(f"ERR: coqui-tts kurulu ama '{top}' bulunamadı — "
                                   f"pip install {top} (XTTS-v2 için genelde 'torch' gerekir).")
            except Exception as e:
                from backend.tts_manager import TTSManager as _TM
                self.write_log(f"ERR: XTTS yüklenemedi — {_TM._xtts_error_hint(e)}")
        threading.Thread(target=run, daemon=True).start()

    def _draw_cfg_toggle(self, c, key: str, label: str):
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        on = bool(get_app_config_value(key, True))
        col  = C_GREEN if on else C_MID
        icon = "◉" if on else "○"
        text = f"{icon}  {label}  {'[AÇIK]' if on else '[KAPALI]'}"
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(10))

    def _toggle_yolo(self):
        """Nesne algılama düğmesi: config'i günceller VE çalışan görü motoruna
        anında bildirir (eskiden yalnızca config'e yazıyordu; bu yüzden kamera
        açıkken kapatma işe yaramıyordu)."""
        new_val = not bool(get_app_config_value("yolo_enabled", True))
        save_app_config({"yolo_enabled": new_val})
        self._draw_cfg_toggle(self._yolo_toggle_canvas, "yolo_enabled", "NESNE ALGILAMA")
        if getattr(self, "on_yolo_toggle", None):
            try:
                self.on_yolo_toggle(new_val)      # çalışan VisionEngine'e canlı ilet
            except Exception:
                pass
        self.write_log(f"SYS: Nesne algılama {'açıldı' if new_val else 'kapatıldı'}.")

    def _toggle_cfg_bool(self, key: str, label: str, canvas, restart_note=False):
        new_val = not bool(get_app_config_value(key, True))
        save_app_config({key: new_val})
        self._draw_cfg_toggle(canvas, key, label)
        durum = "açıldı" if new_val else "kapatıldı"
        ek = " (yeniden başlatınca etkin olur)" if restart_note else ""
        self.write_log(f"SYS: {label} {durum}{ek}.")

    def _toggle_autostart(self):
        try:
            from make_shortcut import create_startup_shortcut, remove_startup_shortcut
            if self._is_autostart_installed():
                remove_startup_shortcut()
                self.write_log("SYS: Otomatik başlatma kapatıldı.")
            else:
                create_startup_shortcut()
                self.write_log("SYS: Otomatik başlatma açıldı. Windows açılışında YERINDE başlar.")
        except Exception as exc:
            self.write_log(f"SYS: Autostart hatası — {exc}")
        finally:
            self.root.after(0, self._draw_autostart_button)

    # ── Desktop shortcut button ──────────────────────────────────────────────
    def _build_shortcut_button(self, parent=None):
        parent = parent or self.root
        self._shortcut_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._shortcut_canvas.bind("<Button-1>", lambda e: self._create_desktop_shortcut())
        self._draw_shortcut_button()

    def _draw_shortcut_button(self, state: str = "idle"):
        c = self._shortcut_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        if state == "ok":
            col, icon, label = C_GREEN, "✓", "MASAÜSTÜ KISAYOLU OLUŞTURULDU"
        elif state == "err":
            col, icon, label = C_RED,   "✕", "HATA — KISAYOL OLUŞTURULAMADI"
        else:
            col, icon, label = C_MID,   "⊞", "MASAÜSTÜNE KISAYOL EKLE"
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"{icon}  {label}",
                      fill=col, font=font_body_bold(10))

    def _create_desktop_shortcut(self):
        def _run():
            try:
                from make_shortcut import create_desktop_shortcut
                path = create_desktop_shortcut()
                self.write_log(f"SYS: Masaüstü kısayolu oluşturuldu → {path}")
                self.root.after(0, lambda: self._draw_shortcut_button("ok"))
                self.root.after(3000, lambda: self._draw_shortcut_button("idle"))
            except Exception as exc:
                self.write_log(f"SYS: Kısayol hatası — {exc}")
                self.root.after(0, lambda: self._draw_shortcut_button("err"))
                self.root.after(3000, lambda: self._draw_shortcut_button("idle"))

        threading.Thread(target=_run, daemon=True).start()

    # ── Model kaynağı: Gemini (bulut) / Ollama (çevrimdışı) ─────────────────
    def _build_provider_button(self, parent=None):
        parent = parent or self.root
        self._provider_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._provider_canvas.bind("<Button-1>", lambda e: self._toggle_model_provider())
        self._draw_provider_button()

    def _draw_provider_button(self):
        c = self._provider_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        provider = str(get_app_config_value("model_provider", "gemini") or "gemini").lower()
        if provider == "ollama":
            col, icon, label = C_GOLD, "⛁", "MODEL: OLLAMA (ÇEVRİMDIŞI)"
        else:
            col, icon, label = C_BLUE, "☁", "MODEL: GEMINI (BULUT)"
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"{icon}  {label}",
                      fill=col, font=font_body_bold(10))

    def _toggle_model_provider(self):
        current = str(get_app_config_value("model_provider", "gemini") or "gemini").lower()
        new_provider = "ollama" if current != "ollama" else "gemini"
        save_app_config({"model_provider": new_provider})
        self._draw_provider_button()
        self._refresh_settings_status()
        if new_provider == "ollama":
            self.write_log(
                "SYS: Model kaynağı ÇEVRİMDIŞI (Ollama) olarak ayarlandı. "
                "Değişikliğin etkili olması için YERINDE'yi yeniden başlat."
            )
        else:
            self.write_log(
                "SYS: Model kaynağı GEMİNİ (bulut) olarak ayarlandı. "
                "Değişikliğin etkili olması için YERINDE'yi yeniden başlat."
            )

    # ── Ollama: kurulu modeller arasında seçim ───────────────────────────────
    # ── Gemini Live modeli seçimi (gerçek zamanlı sesli mod) ─────────────────
    def _build_gemini_model_button(self, parent=None):
        parent = parent or self.root
        self._gemini_model_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._gemini_model_canvas.bind("<Button-1>", lambda e: self._cycle_gemini_model())
        self._draw_gemini_model_button()

    def _draw_gemini_model_button(self, label_override=None):
        c = self._gemini_model_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("gemini_live_model", "") or "").strip()
        if current and "translate" in current.lower():
            # Bu model araç/system_instruction desteklemiyor (1011 hatası
            # verir) — daha önce yanlışlıkla seçilmiş olabilir, otomatik
            # olarak varsayılana döndürülür.
            save_app_config({"gemini_live_model": ""})
            current = ""
        shown = current.replace("models/", "") if current else "Otomatik (varsayılan)"
        label = label_override or f"GEMİNİ MODELİ: {shown}"
        if len(label) > 40:
            label = label[:39] + "…"
        col = C_GOLD
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"✦  {label}",
                      fill=col, font=font_body_bold(10))

    def _cycle_gemini_model(self):
        """Gemini hesabında Live API (gerçek zamanlı ses) ile uyumlu modelleri
        çeker ve seçim için bir liste açar. API anahtarı girilmemişse ya da
        internet yoksa, bilinen sabit bir yedek listeye düşer."""
        try:
            from actions.gemini_models import list_live_models_with_fallback
            from core.token_usage import format_today_usage
            api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()

            self._draw_gemini_model_button(label_override="Modeller taranıyor…")
            self.root.update_idletasks()

            models, is_live = list_live_models_with_fallback(api_key)
            self._draw_gemini_model_button()
            self.write_log(
                f"SYS: {format_today_usage()} — Not: Google, ücretsiz kotanın ne kadarının "
                "kaldığını gösteren bir API sunmuyor; bu sadece gerçekten kullanılan token "
                "sayısıdır (kalan miktar değil)."
            )
            if not is_live:
                self.write_log(
                    "SYS: Gemini modelleri çekilemedi (API anahtarı boş/geçersiz ya da "
                    "internet yok) — bilinen sabit bir liste gösteriliyor. Bu liste "
                    "güncelliğini yitirmiş olabilir."
                )
            self._open_gemini_model_list(models)
        except Exception as e:
            self.write_log(f"ERR: Gemini model listesi açılamadı — {e}")

    def _open_gemini_model_list(self, models: list[str]):
        current = str(get_app_config_value("gemini_live_model", "") or "")

        def _choose(model_name: str):
            save_app_config({"gemini_live_model": model_name})
            self._draw_gemini_model_button()
            self.write_log(
                f"SYS: Gemini Live modeli '{model_name}' olarak ayarlandı — "
                "değişiklik bir sonraki sesli bağlantıda geçerli olur."
            )

        self._open_model_picker(models, current, "Gemini Live Modeli Seç", _choose)

    def _build_ollama_model_button(self, parent=None):
        parent = parent or self.root
        self._ollama_model_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._ollama_model_canvas.bind("<Button-1>", lambda e: self._cycle_ollama_model())
        self._draw_ollama_model_button()

    def _draw_ollama_model_button(self, label_override=None):
        c = self._ollama_model_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("ollama_model", "llama3.1") or "llama3.1")
        label = label_override or f"OLLAMA MODELİ: {current}"
        col = C_GOLD
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"⛃  {label}",
                      fill=col, font=font_body_bold(10))

    def _cycle_ollama_model(self):
        """Ollama sunucusundan kurulu modelleri çeker ve seçim için bir liste açar."""
        try:
            from actions.ollama_models import list_installed_models
            host = str(get_app_config_value("ollama_host", "http://localhost:11434") or "http://localhost:11434")

            self._draw_ollama_model_button(label_override="Modeller taranıyor…")
            self.root.update_idletasks()

            models = list_installed_models(host)
            if not models:
                self._draw_ollama_model_button(label_override="Ollama modeli bulunamadı (ollama serve çalışıyor mu?)")
                self.write_log(
                    "ERR: Ollama'da kurulu model bulunamadı. Önce 'ollama serve' çalıştığından "
                    "ve en az bir modelin 'ollama pull <model>' ile indirildiğinden emin ol."
                )
                return

            self._draw_ollama_model_button()
            self._open_ollama_model_list(models)
        except Exception as e:
            self.write_log(f"ERR: Model listesi açılamadı — {e}")

    def _open_ollama_model_list(self, models: list[str]):
        """Kurulu Ollama modellerini tıklanabilir bir liste olarak gösteren küçük pencere açar."""
        current = str(get_app_config_value("ollama_model", "") or "")

        def _choose(model_name: str):
            save_app_config({"ollama_model": model_name})
            self._draw_ollama_model_button()
            self.write_log(f"SYS: Ollama modeli '{model_name}' olarak ayarlandı.")

        self._open_model_picker(models, current, "Ollama Modeli Seç", _choose)

    def _open_model_picker(self, models: list[str], current: str, title: str, on_choose):
        """Kurulu Ollama modellerini tıklanabilir bir liste olarak gösteren GENEL
        popup — hem sohbet modeli hem de (aşağıdaki) kod/görü modeli seçicileri
        bunu paylaşır; tek fark hangi config anahtarına yazıldığı (on_choose)."""
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)

        row_h = 34
        max_visible = 8
        list_h = min(len(models), max_visible) * row_h
        # Popup genişliği içeriğe göre ayarlanır — Ollama modelleri kısa
        # (ör. "llama3.1:8b") ama Gemini Live model kimlikleri çok uzun
        # (ör. "models/gemini-2.5-flash-native-audio-preview-09-2025").
        # Sabit 340px'te bu isimler kırpılıp birbirinin aynı görünüyordu.
        longest = max((len(f"●  {m}") for m in models), default=20)
        popup_w = max(340, min(620, longest * 7 + 40))
        popup_h = list_h + 96
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - popup_w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - popup_h) // 2)
            popup.geometry(f"{popup_w}x{popup_h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{popup_w}x{popup_h}")
        popup.deiconify()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))
        popup.focus_force()
        # NOT: grab_set() pencere gerçekten görünür (viewable) olana kadar
        # bir gecikmeyle çağrılır — Linux/X11'de hemen çağrılırsa
        # "grab failed: window not viewable" hatası verip pencerenin
        # açılmamış gibi görünmesine yol açabiliyordu.
        popup.after(100, lambda: popup.grab_set() if popup.winfo_exists() else None)

        tk.Label(
            popup, text=title, bg=C_PANEL, fg=C_PRI,
            font=font_body_bold(11), anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 6))

        canvas_frame = tk.Frame(popup, bg=C_PANEL)
        canvas_frame.pack(fill="both", expand=True, padx=12)

        needs_scroll = len(models) > max_visible
        canvas_w = (popup_w - 24 - 22) if needs_scroll else (popup_w - 24)
        list_canvas = tk.Canvas(canvas_frame, bg=C_PANEL, highlightthickness=0,
                                 height=list_h, width=canvas_w)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=list_canvas.yview)
        inner = tk.Frame(list_canvas, bg=C_PANEL)

        inner.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=inner, anchor="nw", width=canvas_w)
        list_canvas.configure(yscrollcommand=scrollbar.set)

        if needs_scroll:
            scrollbar.pack(side="right", fill="y")
        list_canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            delta = event.delta
            if delta == 0 and hasattr(event, "num"):
                delta = -120 if event.num == 4 else 120
            list_canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        list_canvas.bind("<MouseWheel>", _on_mousewheel)     # Windows / macOS
        list_canvas.bind("<Button-4>", _on_mousewheel)        # Linux scroll up
        list_canvas.bind("<Button-5>", _on_mousewheel)        # Linux scroll down

        def _choose(model_name: str):
            on_choose(model_name)
            popup.destroy()

        for model_name in models:
            is_current = (model_name == current)
            row = tk.Frame(inner, bg=(C_DIM if is_current else C_PANEL), height=row_h)
            row.pack(fill="x")
            row.pack_propagate(False)
            prefix = "●  " if is_current else "○  "
            lbl = tk.Label(
                row, text=f"{prefix}{model_name}",
                bg=(C_DIM if is_current else C_PANEL),
                fg=(C_GOLD if is_current else C_MID),
                font=font_body_bold(10) if is_current else font_body(10),
                anchor="w", cursor="hand2",
            )
            lbl.pack(fill="both", expand=True, padx=10)
            lbl.bind("<Button-1>", lambda e, m=model_name: _choose(m))
            row.bind("<Button-1>", lambda e, m=model_name: _choose(m))

        tk.Button(
            popup, text="Kapat", command=popup.destroy,
            bg=C_PANEL, fg=C_DIM, activebackground=C_PANEL, activeforeground=C_PRI,
            borderwidth=0, cursor="hand2", font=font_body(9),
        ).pack(pady=(6, 10))

    # ── Ollama: KOD (Blender/Python) modeli — sohbetten BAĞIMSIZ seçim ───────
    # Kök neden notu: eskiden tek bir "Ollama modeli" seçici hem sohbeti hem
    # de kodu (Blender bpy dahil) üretiyordu; küçük bir sohbet modeli (ör.
    # 3B) seçildiğinde Blender kodu da o küçük modelle üretiliyordu ve bu
    # "küre çizemedim" şikayetinin en olası sebebiydi. Artık kod modeli ayrı
    # ayarlanabiliyor (boş bırakılırsa hızlı/dengeli moda göre otomatik
    # varsayılana — core/offline_core.py MODEL_PRESETS — düşer).
    def _build_ollama_coder_model_button(self, parent=None):
        parent = parent or self.root
        self._ollama_coder_model_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._ollama_coder_model_canvas.bind("<Button-1>", lambda e: self._cycle_ollama_coder_model())
        self._draw_ollama_coder_model_button()

    def _draw_ollama_coder_model_button(self, label_override=None):
        c = self._ollama_coder_model_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("ollama_coder_model", "") or "")
        shown = current if current else "Otomatik (varsayılan)"
        label = label_override or f"KOD MODELİ: {shown}"
        if len(label) > 34:
            label = label[:33] + "…"
        col = C_GREEN
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"🛠  {label}",
                      fill=col, font=font_body_bold(10))

    def _cycle_ollama_coder_model(self):
        """Blender/Python kod üretimi (ör. 'küre çiz') için AYRI bir model
        seçmeni sağlar. Küçük/genel amaçlı modeller (3B gibi) bpy kodu
        üretmekte güvenilir olmuyor — qwen2.5-coder / qwen3-coder gibi
        kod-odaklı bir model seçmen önerilir."""
        try:
            from actions.ollama_models import list_installed_models
            host = str(get_app_config_value("ollama_host", "http://localhost:11434") or "http://localhost:11434")

            self._draw_ollama_coder_model_button(label_override="Modeller taranıyor…")
            self.root.update_idletasks()

            models = list_installed_models(host)
            if not models:
                self._draw_ollama_coder_model_button(
                    label_override="Ollama modeli bulunamadı (ollama serve çalışıyor mu?)")
                self.write_log(
                    "ERR: Ollama'da kurulu model bulunamadı. Önce 'ollama serve' çalıştığından "
                    "ve en az bir kod modelinin (ör. 'ollama pull qwen2.5-coder') indirildiğinden emin ol."
                )
                return

            self._draw_ollama_coder_model_button()
            current = str(get_app_config_value("ollama_coder_model", "") or "")

            def _choose(model_name: str):
                save_app_config({"ollama_coder_model": model_name})
                self._draw_ollama_coder_model_button()
                self.write_log(
                    f"SYS: Kod modeli '{model_name}' olarak ayarlandı — "
                    "sohbet modelinden bağımsız, yalnızca Blender/kod üretiminde kullanılır."
                )

            self._open_model_picker(models, current, "Kod Modeli Seç (Blender/Python)", _choose)
        except Exception as e:
            self.write_log(f"ERR: Kod modeli listesi açılamadı — {e}")

    # ── Çevrimdışı ses seçimi (Piper / sistem sesi, kadın-erkek) ─────────────
    def _build_voice_choice_button(self, parent=None):
        parent = parent or self.root
        self._voice_choice_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._voice_choice_canvas.bind("<Button-1>", lambda e: self._open_voice_choice_list())
        self._draw_voice_choice_button()

    def _draw_voice_choice_button(self, label_override=None):
        c = self._voice_choice_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("offline_voice_choice", "auto") or "auto")
        if label_override:
            label = label_override
        elif current == "auto":
            label = "ÇEVRİMDIŞI SES: Otomatik"
        elif current.startswith("piper:"):
            label = f"ÇEVRİMDIŞI SES: {Path(current.split(':', 1)[1]).stem} (Piper)"
        elif current.startswith("sapi:"):
            label = f"ÇEVRİMDIŞI SES: {current.split(':', 1)[1]}"
        elif current.startswith("xtts:"):
            label = "ÇEVRİMDIŞI SES: 🎙 Kendi Sesim (XTTS)"
        elif current == "chattts":
            label = "ÇEVRİMDIŞI SES: ChatTTS"
        elif current.startswith("espeak:"):
            var = current.split(":", 1)[1]
            try:
                from actions.voice_catalog import CATALOG
                nice = next((lbl for lbl, _g, v in CATALOG if v == var), var)
            except Exception:
                nice = var
            label = f"ÇEVRİMDIŞI SES: {nice}"
        else:
            label = f"ÇEVRİMDIŞI SES: {current}"
        # Panele sığmayan uzun etiketleri kısalt (tam yol taşmasını önler)
        if len(label) > 34:
            label = label[:33] + "…"
        col = C_BLUE
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"🎤  {label}",
                      fill=col, font=font_body_bold(10))

    def _open_voice_choice_list(self):
        try:
            from actions.piper_voices import list_voice_options
            options = list_voice_options()
        except Exception as e:
            self.write_log(f"ERR: Ses listesi alınamadı — {e}")
            return
        current = str(get_app_config_value("offline_voice_choice", "auto") or "auto")

        popup = tk.Toplevel(self.root)
        popup.title("Çevrimdışı Ses Seç")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)

        row_h = 34
        max_visible = 8
        list_h = min(len(options), max_visible) * row_h
        popup_w = 420
        popup_h = list_h + 96
        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - popup_w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - popup_h) // 2)
            popup.geometry(f"{popup_w}x{popup_h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{popup_w}x{popup_h}")
        popup.deiconify()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))
        popup.focus_force()
        # NOT: grab_set() pencere gerçekten görünür (viewable) olana kadar
        # bir gecikmeyle çağrılır — Linux/X11'de hemen çağrılırsa
        # "grab failed: window not viewable" hatası verip pencerenin
        # açılmamış gibi görünmesine yol açabiliyordu.
        popup.after(100, lambda: popup.grab_set() if popup.winfo_exists() else None)

        tk.Label(
            popup, text="Çevrimdışı Ses Seçenekleri (Piper / Sistem Sesi)",
            bg=C_PANEL, fg=C_PRI, font=font_body_bold(11), anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 6))

        canvas_frame = tk.Frame(popup, bg=C_PANEL)
        canvas_frame.pack(fill="both", expand=True, padx=12)

        needs_scroll = len(options) > max_visible
        canvas_w = (popup_w - 24 - 22) if needs_scroll else (popup_w - 24)
        list_canvas = tk.Canvas(canvas_frame, bg=C_PANEL, highlightthickness=0,
                                 height=list_h, width=canvas_w)
        scrollbar = tk.Scrollbar(canvas_frame, orient="vertical", command=list_canvas.yview)
        inner = tk.Frame(list_canvas, bg=C_PANEL)

        inner.bind("<Configure>", lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.create_window((0, 0), window=inner, anchor="nw", width=canvas_w)
        list_canvas.configure(yscrollcommand=scrollbar.set)

        if needs_scroll:
            scrollbar.pack(side="right", fill="y")
        list_canvas.pack(side="left", fill="both", expand=True)

        def _on_mousewheel(event):
            delta = event.delta
            if delta == 0 and hasattr(event, "num"):
                delta = -120 if event.num == 4 else 120
            list_canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        list_canvas.bind("<MouseWheel>", _on_mousewheel)     # Windows / macOS
        list_canvas.bind("<Button-4>", _on_mousewheel)        # Linux scroll up
        list_canvas.bind("<Button-5>", _on_mousewheel)        # Linux scroll down

        def _choose(value: str):
            save_app_config({"offline_voice_choice": value})
            self._draw_voice_choice_button()
            self.write_log(f"SYS: Çevrimdışı ses '{value}' olarak ayarlandı.")
            try:
                from actions.offline_tts import diagnose_voice_setup
                warning = diagnose_voice_setup()
                if warning:
                    self.write_log(f"UYARI: {warning}")
            except Exception:
                pass
            popup.destroy()

        for opt in options:
            is_current = (opt["value"] == current)
            row = tk.Frame(inner, bg=(C_DIM if is_current else C_PANEL), height=row_h)
            row.pack(fill="x")
            row.pack_propagate(False)
            prefix = "●  " if is_current else "○  "
            lbl = tk.Label(
                row, text=f"{prefix}{opt['label']}",
                bg=(C_DIM if is_current else C_PANEL),
                fg=(C_GOLD if is_current else C_MID),
                font=font_body_bold(10) if is_current else font_body(10),
                anchor="w", cursor="hand2",
            )
            lbl.pack(fill="both", expand=True, padx=10)
            lbl.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))
            row.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))

        tk.Button(
            popup, text="Kapat", command=popup.destroy,
            bg=C_PANEL, fg=C_DIM, activebackground=C_PANEL, activeforeground=C_PRI,
            borderwidth=0, cursor="hand2", font=font_body(9),
        ).pack(pady=(6, 10))

    # ── Çevrimdışı konuşma tanıma (STT) motoru: Whisper / Vosk ──────────────
    def _build_stt_engine_button(self, parent=None):
        parent = parent or self.root
        self._stt_engine_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._stt_engine_canvas.bind("<Button-1>", lambda e: self._open_stt_choice_list())
        self._draw_stt_engine_button()

    STT_OPTIONS = [
        {"label": "Whisper — Küçük (hızlı, düşük doğruluk)", "value": "whisper:small"},
        {"label": "Whisper — Orta (dengeli, ÖNERİLEN)", "value": "whisper:medium"},
        {"label": "Whisper — Büyük (en doğru Türkçe, yavaş)", "value": "whisper:large-v3"},
        {"label": "Vosk (en hafif, düşük doğruluk)", "value": "vosk"},
    ]

    def _current_stt_choice(self) -> str:
        choice = str(get_app_config_value("stt_choice", "") or "").strip().lower()
        if choice:
            return choice
        # Geriye dönük uyumluluk
        engine = str(get_app_config_value("ollama_stt_engine", "whisper") or "whisper").lower()
        if engine == "vosk":
            return "vosk"
        size = str(get_app_config_value("whisper_model_size", "small") or "small")
        return f"whisper:{size}"

    def _draw_stt_engine_button(self, label_override=None):
        c = self._stt_engine_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = self._current_stt_choice()
        if label_override:
            label = label_override
        else:
            match = next((o for o in self.STT_OPTIONS if o["value"] == current), None)
            label = match["label"] if match else current
        col = C_GOLD if current == "vosk" else C_GREEN
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"👂  ANLAMA: {label}",
                      fill=col, font=font_body_bold(10))

    def _open_stt_choice_list(self):
        current = self._current_stt_choice()

        popup = tk.Toplevel(self.root)
        popup.title("Anlama (STT) Motoru Seç")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)

        row_h = 34
        options = self.STT_OPTIONS
        list_h = len(options) * row_h
        popup_w = 420
        popup_h = list_h + 96

        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - popup_w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - popup_h) // 2)
            popup.geometry(f"{popup_w}x{popup_h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{popup_w}x{popup_h}")
        popup.deiconify()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))
        popup.focus_force()
        popup.after(100, lambda: popup.grab_set() if popup.winfo_exists() else None)

        tk.Label(
            popup, text="Türkçe Anlama Motoru (çevrimdışı)", bg=C_PANEL, fg=C_PRI,
            font=font_body_bold(11), anchor="w",
        ).pack(fill="x", padx=12, pady=(12, 6))

        inner = tk.Frame(popup, bg=C_PANEL)
        inner.pack(fill="both", expand=True, padx=12)

        def _choose(value: str):
            save_app_config({"stt_choice": value})
            self._draw_stt_engine_button()
            self.write_log(f"SYS: Anlama motoru '{value}' olarak ayarlandı.")
            popup.destroy()

        for opt in options:
            is_current = (opt["value"] == current)
            row = tk.Frame(inner, bg=(C_DIM if is_current else C_PANEL), height=row_h)
            row.pack(fill="x")
            row.pack_propagate(False)
            prefix = "●  " if is_current else "○  "
            lbl = tk.Label(
                row, text=f"{prefix}{opt['label']}",
                bg=(C_DIM if is_current else C_PANEL),
                fg=(C_GOLD if is_current else C_MID),
                font=font_body_bold(10) if is_current else font_body(10),
                anchor="w", cursor="hand2",
            )
            lbl.pack(fill="both", expand=True, padx=10)
            lbl.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))
            row.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))

        tk.Button(
            popup, text="Kapat", command=popup.destroy,
            bg=C_PANEL, fg=C_DIM, activebackground=C_PANEL, activeforeground=C_PRI,
            borderwidth=0, cursor="hand2", font=font_body(9),
        ).pack(pady=(6, 10))

    # ── Düşünme Hızı: HEM Gemini HEM Ollama için TEK ortak ayar ─────────────
    # Kök neden notu: Gemini'nin native-audio modeli varsayılan olarak
    # sessizce "düşünüyordu" — bu hem ilk sesli yanıtı geciktiriyor hem de
    # SDK konsoluna zararsız bir uyarı bastırıyordu. Ollama tarafında da
    # qwen3/deepseek-r1/gpt-oss gibi "düşünen" modeller aynı şekilde
    # yavaşlayabiliyor. Kullanıcı ham sayı (0/256/-1) yerine üç anlaşılır
    # seçenekten birini seçer; app_config.gemini_thinking_budget() ve
    # app_config.ollama_think_value() bu TEK değeri her backend'in kendi API
    # parametresine çevirir (main.py / ollama_assistant.py).
    THINKING_OPTIONS = [
        {"label": "⚡ Hızlı — düşünme kapalı, en hızlı yanıt", "value": "fast"},
        {"label": "⚖️ Normal — dengeli (ÖNERİLEN)", "value": "normal"},
        {"label": "🧠 Derin Düşünme — en doğru, en yavaş", "value": "deep"},
    ]

    def _build_thinking_button(self, parent=None):
        parent = parent or self.root
        self._thinking_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._thinking_canvas.bind("<Button-1>", lambda e: self._open_thinking_choice_list())
        self._draw_thinking_button()

    def _current_thinking_level(self) -> str:
        lvl = str(get_app_config_value("thinking_level", "normal") or "normal").strip().lower()
        return lvl if lvl in ("fast", "normal", "deep") else "normal"

    def _draw_thinking_button(self, label_override=None):
        c = self._thinking_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = self._current_thinking_level()
        if label_override:
            label = label_override
        else:
            match = next((o for o in self.THINKING_OPTIONS if o["value"] == current), None)
            label = match["label"] if match else current
        col = C_GREEN
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"💭  DÜŞÜNME HIZI: {label}",
                      fill=col, font=font_body_bold(10))

    def _open_thinking_choice_list(self):
        current = self._current_thinking_level()

        popup = tk.Toplevel(self.root)
        popup.title("Düşünme Hızı Seç")
        popup.configure(bg=C_PANEL)
        popup.transient(self.root)
        popup.resizable(False, False)

        row_h = 34
        options = self.THINKING_OPTIONS
        list_h = len(options) * row_h
        popup_w = 420
        popup_h = list_h + 96

        try:
            self.root.update_idletasks()
            rx = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - popup_w) // 2)
            ry = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - popup_h) // 2)
            popup.geometry(f"{popup_w}x{popup_h}+{rx}+{ry}")
        except Exception:
            popup.geometry(f"{popup_w}x{popup_h}")
        popup.deiconify()
        popup.lift()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))
        popup.focus_force()
        popup.after(100, lambda: popup.grab_set() if popup.winfo_exists() else None)

        tk.Label(
            popup, text="Gemini VE Ollama için ortak (model 'düşünmeyi' desteklemiyorsa\n"
                        "otomatik yok sayılır)", bg=C_PANEL, fg=C_PRI,
            font=font_body_bold(10), anchor="w", justify="left",
        ).pack(fill="x", padx=12, pady=(12, 6))

        inner = tk.Frame(popup, bg=C_PANEL)
        inner.pack(fill="both", expand=True, padx=12)

        def _choose(value: str):
            save_app_config({"thinking_level": value})
            self._draw_thinking_button()
            self.write_log(f"SYS: Düşünme hızı '{value}' olarak ayarlandı.")
            popup.destroy()

        for opt in options:
            is_current = (opt["value"] == current)
            row = tk.Frame(inner, bg=(C_DIM if is_current else C_PANEL), height=row_h)
            row.pack(fill="x")
            row.pack_propagate(False)
            prefix = "●  " if is_current else "○  "
            lbl = tk.Label(
                row, text=f"{prefix}{opt['label']}",
                bg=(C_DIM if is_current else C_PANEL),
                fg=(C_GOLD if is_current else C_MID),
                font=font_body_bold(10) if is_current else font_body(10),
                anchor="w", cursor="hand2",
            )
            lbl.pack(fill="both", expand=True, padx=10)
            lbl.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))
            row.bind("<Button-1>", lambda e, v=opt["value"]: _choose(v))

        tk.Button(
            popup, text="Kapat", command=popup.destroy,
            bg=C_PANEL, fg=C_DIM, activebackground=C_PANEL, activeforeground=C_PRI,
            borderwidth=0, cursor="hand2", font=font_body(9),
        ).pack(pady=(6, 10))

    # ── Dosya yükle (PDF/Word/PowerPoint/Excel/resim analiz için) ───────────
    def _build_upload_button(self, parent=None):
        parent = parent or self.root
        self._upload_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._upload_canvas.bind("<Button-1>", lambda e: self._pick_file_to_upload())
        self._upload_canvas.bind("<Button-3>", lambda e: self._clear_uploaded_file())
        self._draw_upload_button()

        self._upload_clear_canvas = tk.Canvas(
            parent, height=30,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._upload_clear_canvas.bind("<Button-1>", lambda e: self._clear_uploaded_file())
        self._draw_upload_clear_button()

    def _build_app_paths_button(self, parent=None):
        parent = parent or self.root
        self._app_paths_canvas = tk.Canvas(
            parent, height=26,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._app_paths_canvas.bind("<Button-1>", lambda e: self._open_app_paths_manager())
        self._draw_simple_button(self._app_paths_canvas, "📁 UYGULAMA YOLLARI", C_BLUE)

    def _build_egitim_verisi_button(self, parent=None):
        parent = parent or self.root
        self._egitim_verisi_canvas = tk.Canvas(
            parent, height=26,
            bg=parent.cget("bg"), highlightthickness=0, cursor="hand2"
        )
        self._egitim_verisi_canvas.bind("<Button-1>", lambda e: self._open_egitim_verisi_manager())
        self._draw_simple_button(self._egitim_verisi_canvas, "🎓 EĞİTİM VERİSİ", C_GOLD)

    def _draw_upload_clear_button(self):
        c = self._upload_clear_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 34
        bh = int(c["height"])
        c.delete("all")
        has_file = bool(get_app_config_value("last_uploaded_file", "") or "")
        col = C_RED if has_file else C_DIM
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text="✕", fill=col, font=font_body_bold(12))

    def _draw_upload_button(self):
        c = self._upload_canvas
        bw = int(c["width"]) if int(c["width"]) > 1 else 296
        bh = int(c["height"])
        c.delete("all")
        current = str(get_app_config_value("last_uploaded_file", "") or "")
        label = f"📎 {Path(current).name}" if current else "📎 DOSYA YÜKLE"
        col = C_PRI
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=label, fill=col, font=font_body_bold(10))

    def _pick_file_to_upload(self):
        try:
            self._pick_file_to_upload_impl()
        except Exception as e:
            self.write_log(f"ERR: Dosya seçilemedi — {e}")

    def _pick_file_to_upload_impl(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Analiz edilecek dosyayı seç",
            filetypes=[
                ("Desteklenen dosyalar", "*.pdf *.docx *.pptx *.xlsx *.xlsm *.png *.jpg *.jpeg *.webp *.py *.txt *.md *.json"),
                ("PDF", "*.pdf"), ("Word", "*.docx"), ("PowerPoint", "*.pptx"),
                ("Excel", "*.xlsx *.xlsm"), ("Resim", "*.png *.jpg *.jpeg *.webp"),
                ("Python / Kod", "*.py *.js *.ts *.json *.txt *.md"),
                ("Tüm dosyalar", "*.*"),
            ],
        )
        if not path:
            return
        save_app_config({"last_uploaded_file": path})
        self._draw_upload_button()
        self._draw_upload_clear_button()
        self.write_log(
            f"SYS: '{Path(path).name}' yüklendi. "
            "Şimdi 'bu dosyayı özetle', 'bunu analiz et' ya da "
            "(PDF/Word/PowerPoint için) 'bunu sesli oku' diyebilirsin."
        )

    def _clear_uploaded_file(self):
        save_app_config({"last_uploaded_file": ""})
        self._draw_upload_button()
        self._draw_upload_clear_button()
        self.write_log("SYS: Yüklenen dosya kaldırıldı.")

    def _play_startup_sfx_once(self):
        if self._startup_sfx_played:
            return
        self._startup_sfx_played = True
        if self._effects_active:
            self.sound.play_startup()

    def _sync_sound_state(self):
        enabled = self._sfx_on and not self.paused
        self.sound.set_enabled(enabled)
        if enabled and self._yerinde_state == "THINKING":
            self.sound.start_thinking()
        if enabled != self._effects_active:
            self._effects_active = enabled
            if self.on_effects_state_change:
                threading.Thread(
                    target=self.on_effects_state_change,
                    args=(enabled,),
                    daemon=True,
                ).start()

    def _open_api_settings(self):
        self._show_setup_ui(edit_mode=self._api_key_ready)

    def _close_setup_ui(self):
        if self.setup_frame and self.setup_frame.winfo_exists():
            self.setup_frame.destroy()
        self.setup_frame = None
        self.api_entry = None
        self.youtube_api_entry = None
        self.youtube_handle_entry = None

    # ── SFX toggle ───────────────────────────────────────────────────────────
    def _build_sfx_button(self, parent=None):
        parent = parent or self.root
        BW, BH = 98, 36
        self._sfx_canvas = tk.Canvas(parent, width=BW, height=BH,
                                     bg=parent.cget("bg"), highlightthickness=0, cursor="hand2")
        self._sfx_canvas.bind("<Button-1>", lambda e: self._toggle_sfx())
        self._sfx_on = True
        self._draw_sfx_button()

    def _draw_sfx_button(self):
        c = self._sfx_canvas
        BW = int(c["width"])
        BH = int(c["height"])
        c.delete("all")
        col  = C_PRI if self._sfx_on else C_MID
        text = "♪ SFX ON"  if self._sfx_on else "♪ SFX OFF"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (BW, 0, -1, 1),
                                (0, BH, 1, -1), (BW, BH, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=1)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=1)
        c.create_text(BW//2, BH//2, text=text, fill=col, font=font_body_bold(9))

    def _toggle_sfx(self):
        self._sfx_on = not self._sfx_on
        self._draw_sfx_button()
        self._sync_sound_state()

    # ── Voice selector ───────────────────────────────────────────────────────
    def _build_voice_selector(self, parent=None):
        parent = parent or self.root
        self._voice_var = tk.StringVar(value=self._current_voice)
        self._voice_label = tk.Label(parent, text="ÇEVRİMİÇİ\nSES", fg=C_MID,
                                     bg=parent.cget("bg"), justify="left",
                                     font=font_body_bold(8))

        self._voice_menu = tk.OptionMenu(parent, self._voice_var, *VOICES,
                                         command=self._on_voice_select)
        self._voice_menu.config(
            fg=C_PRI, bg=C_PANEL, activeforeground=C_BG,
            activebackground=C_PRI, font=font_body(10),
            borderwidth=0, highlightthickness=1,
            highlightbackground=C_MID, width=12)
        self._voice_menu["menu"].config(
            fg=C_PRI, bg=C_PANEL, font=font_body(10),
            activeforeground=C_BG, activebackground=C_PRI)

    def _on_voice_select(self, voice_label: str):
        """Menüde Türkçe etiket seçilir; yapılandırmaya Gemini ses kimliği yazılır."""
        vid = VOICE_ID_BY_LABEL.get(voice_label, "Charon")
        self._current_voice = voice_label
        save_app_config({"voice": vid})
        self.write_log(f"SYS: Çevrimiçi ses '{voice_label}' seçildi.")
        if self.on_voice_change:
            threading.Thread(target=self.on_voice_change, args=(vid,), daemon=True).start()

    # ── Mute button ──────────────────────────────────────────────────────────
    def _build_mute_button(self):
        self._mute_canvas = tk.Canvas(self.root, width=126, height=36,
                                      bg=C_BG, highlightthickness=0, cursor="hand2")
        self._mute_canvas.bind("<Button-1>", lambda e: self._toggle_mute())
        self._draw_mute_button()

    def _draw_mute_button(self):
        c = self._mute_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        if self.muted:
            col, icon, lbl = C_MUTED, "🔇", " SESSİZ"
        else:
            col, icon, lbl = C_GREEN, "🎙", " CANLI"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=f"{icon}{lbl}",
                      fill=col, font=font_body_bold(11))

    def _build_pause_button(self):
        self._pause_canvas = tk.Canvas(self.root, width=126, height=36,
                                       bg=C_BG, highlightthickness=0, cursor="hand2")
        self._pause_canvas.bind("<Button-1>", lambda e: self._toggle_pause())
        self._draw_pause_button()

    def _draw_pause_button(self):
        c = self._pause_canvas
        bw = int(c["width"])
        bh = int(c["height"])
        c.delete("all")
        if self.paused:
            col, text = C_GOLD, "▶ DEVAM"
        else:
            col, text = C_BLUE, "⏸ DURAKLAT"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                               (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(11))

    # ── Stop (DUR) button — konuşurken/düşünürken hemen sustur ──────────────
    def _build_stop_button(self):
        self._stop_canvas = tk.Canvas(self.root, width=96, height=36,
                                      bg=C_BG, highlightthickness=0, cursor="hand2")
        self._stop_canvas.bind("<Button-1>", lambda e: self._stop_speaking())
        self._draw_stop_button()

    def _draw_stop_button(self):
        c = self._stop_canvas
        bw, bh = int(c["width"]), int(c["height"])
        c.delete("all")
        active = self._yerinde_state in ("SPEAKING", "THINKING")
        col = C_RED if active else C_DIM
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text="⏹ DUR", fill=col, font=font_body_bold(11))

    def _stop_speaking(self):
        if self.on_stop_speaking:
            threading.Thread(target=self.on_stop_speaking, daemon=True).start()
        else:
            self.write_log("SYS: Durdurulacak bir şey yok.")

    # ── Webcam toggle button ─────────────────────────────────────────────────
    def _build_webcam_button(self):
        self._cam_canvas = tk.Canvas(self.root, width=110, height=36,
                                     bg=C_BG, highlightthickness=0, cursor="hand2")
        self._cam_canvas.bind("<Button-1>", lambda e: self._toggle_webcam_ui())
        self._draw_webcam_button()

    def _draw_webcam_button(self):
        c = self._cam_canvas
        bw, bh = int(c["width"]), int(c["height"])
        c.delete("all")
        if self._webcam_active:
            col, text = C_RED, "◉  KAMERA AÇIK"
        else:
            col, text = C_DIM, "◎  KAMERA"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(11))

    def _toggle_webcam_ui(self):
        if self.on_webcam_toggle:
            self.on_webcam_toggle(not self._webcam_active)

    # ── Bahçe kamerası (BAHÇE KAMERASI / UYANDIR / PTZ) ──────────────────────
    # Not: buton genişliği 170 — "◉  BAHÇE KAMERASI" metni en geniş yedek
    # fontta bile ~130px; 136px'te DPI ölçeğiyle metin sağdan kesiliyordu.
    def _build_garden_buttons(self):
        self._garden_canvas = tk.Canvas(self.root, width=170, height=36,
                                        bg=C_BG, highlightthickness=0, cursor="hand2")
        self._garden_canvas.bind("<Button-1>", lambda e: self._toggle_garden_ui())
        self._draw_garden_button()

        self._garden_wake_canvas = tk.Canvas(self.root, width=170, height=36,
                                             bg=C_BG, highlightthickness=0, cursor="hand2")
        self._garden_wake_canvas.bind("<Button-1>", lambda e: self._garden_wake_click())
        self._draw_garden_wake_button()

        # Joystick tarzı PTZ: ortadan herhangi bir yöne sürükleyince o yöne
        # döner, bırakınca kendiliğinden durur. Merkez bölge = sürekli durdur.
        self._joy_active = False
        self._joy_pressed = False
        self._joy_current = None
        self._joy_stop_timer = None
        self._garden_joystick_canvas = tk.Canvas(self.root, width=160, height=160,
                                                 bg=C_BG, highlightthickness=0,
                                                 cursor="hand2")
        self._garden_joystick_canvas.bind("<ButtonPress-1>", self._garden_joy_press)
        self._garden_joystick_canvas.bind("<B1-Motion>", self._garden_joy_drag)
        self._garden_joystick_canvas.bind("<ButtonRelease-1>", self._garden_joy_release)
        self._draw_garden_joystick(0.0, 0.0)

        # Alarm / iki yönlü ses (konuşma) butonları. Işık (OPLightControl)
        # kaldırıldı — bu kamera modelinde spot ışığı desteklenmiyor.
        self._garden_tool_canvases = {}
        self._garden_horn_on = False
        self._garden_talking = False
        for tool, glyph in (("horn", "🚨 ALARM"),
                            ("talk", "🎙 KONUŞ")):
            c = tk.Canvas(self.root, width=96, height=30,
                          bg=C_BG, highlightthickness=0, cursor="hand2")
            c.bind("<Button-1>", lambda e, t=tool: self._garden_tool_click(t))
            self._garden_tool_canvases[tool] = c
        self._draw_garden_tool_buttons()

    def _draw_garden_button(self):
        c = self._garden_canvas
        bw, bh = int(c["width"]), int(c["height"])
        c.delete("all")
        if self._garden_active:
            col, text = C_GREEN, "◉  BAHÇE KAMERASI"
        elif self._garden_waking:
            col, text = C_GOLD, "◍  UYANDIRILIYOR"
        else:
            col, text = C_DIM, "◎  BAHÇE KAMERASI"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(10))

    def _draw_garden_wake_button(self):
        c = self._garden_wake_canvas
        bw, bh = int(c["width"]), int(c["height"])
        c.delete("all")
        col = C_GOLD if self._garden_waking else C_DIM
        text = "⏰ UYANDIR" if not self._garden_waking else "⏳ UYANDIRILIYOR"
        bl = 6
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(10))

    def _toggle_garden_ui(self):
        if self.on_garden_toggle:
            self.on_garden_toggle(not self._garden_active)

    def _garden_wake_click(self):
        if not self.on_garden_wake:
            self.write_log("SYS: Bu modda bahçe kamerası uyandırma bağlı değil.")
            return
        if self._garden_waking:
            return
        self._garden_waking = True
        self.root.after(0, self._draw_garden_wake_button)
        self.root.after(0, self._draw_garden_button)

        def _run():
            try:
                msg = self.on_garden_wake()
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: Bahçe kamerası uyandırılamadı — {e}")
            finally:
                self._garden_waking = False
                self.root.after(0, self._draw_garden_wake_button)
                self.root.after(0, self._draw_garden_button)
        threading.Thread(target=_run, daemon=True).start()

    def _garden_ptz_click(self, direction):
        # Kamera kapalıyken de yön tuşuna basınca kamera uyandırılıp
        # döndürülür (backend ptz() kamerayı kendisi açar). Bu yüzden burada
        # _garden_active kontrolü yapılmıyor — "uyandırılamıyor" şikayetinin
        # nedeni, kapalıyken tıklamaların sessizce yutulmasıydı.
        if not self.on_garden_ptz:
            self.write_log("SYS: Bu modda PTZ bağlı değil.")
            return

        def _run():
            try:
                msg = self.on_garden_ptz(direction)
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: PTZ hatası — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _garden_stop_click(self):
        """⏹ DURDUR — dönüşü durdurur; kamerayı KAPATMAZ."""
        if not self.on_garden_ptz:
            self.write_log("SYS: Bu modda PTZ bağlı değil.")
            return

        def _run():
            try:
                msg = self.on_garden_ptz("stop")
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: PTZ hatası — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _garden_ptz_press(self, direction):
        """Yön tuşuna basılı tutunca kamera sürekli o yöne döner."""
        if not self.on_garden_ptz_start:
            self.write_log("SYS: Bu modda PTZ bağlı değil.")
            return

        def _run():
            try:
                msg = self.on_garden_ptz_start(direction)
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: PTZ hatası — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _garden_ptz_release(self):
        """Yön tuşu bırakılınca dönüş durur."""
        if not self.on_garden_ptz_stop:
            return

        def _run():
            try:
                msg = self.on_garden_ptz_stop()
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: PTZ durdurma hatası — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _garden_tool_click(self, tool):
        """Alarm (hoparlör) ve iki yönlü ses (konuşma) butonları."""
        if tool == "horn":
            cb = self.on_garden_horn
        else:
            cb = self.on_garden_talk
        if not cb:
            self.write_log("SYS: Bu modda bahçe kamerası araçları bağlı değil.")
            return

        def _run():
            try:
                msg = cb()
                if msg:
                    self.write_log(f"SYS: {msg}")
                # Başarılıysa butonun durumunu yansıt (yanıp sönen renk).
                if not (msg or "").startswith("error"):
                    if tool == "horn":
                        self._garden_horn_on = not self._garden_horn_on
                    else:
                        self._garden_talking = not self._garden_talking
                    self.root.after(0, self._draw_garden_tool_buttons)
            except Exception as e:
                self.write_log(f"ERR: {tool} hatası — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def set_garden_tool_state(self, horn_on=None, talking=None):
        """Backend'den gelen durumla buton renklerini günceller."""
        def _apply():
            if horn_on is not None:
                self._garden_horn_on = bool(horn_on)
            if talking is not None:
                self._garden_talking = bool(talking)
            self._draw_garden_tool_buttons()
        try:
            self.root.after(0, _apply)
        except Exception:
            _apply()

    def _draw_garden_tool_buttons(self):
        for tool, c in self._garden_tool_canvases.items():
            if tool == "horn":
                col = C_GOLD if self._garden_horn_on else C_DIM
            else:
                col = C_GOLD if self._garden_talking else C_DIM
            self._draw_bracket_button(c, col, {
                "horn": "🚨 ALARM",
                "talk": "🎙 KONUŞ",
            }[tool])

    def _draw_garden_joystick(self, ox=0.0, oy=0.0):
        c = self._garden_joystick_canvas
        c.delete("all")
        w, h = int(c["width"]), int(c["height"])
        cx, cy = w / 2.0, h / 2.0
        R = 58.0
        # Pad dış çemberi + artı kılavuz çizgileri
        c.create_oval(cx - R, cy - R, cx + R, cy + R, outline=C_DIM, width=2)
        c.create_line(cx - R, cy, cx + R, cy, fill=C_DIM, width=1)
        c.create_line(cx, cy - R, cx, cy + R, fill=C_DIM, width=1)
        # Yön okları
        for glyph, dx, dy in (("◀", -1, 0), ("▲", 0, -1),
                              ("▼", 0, 1), ("▶", 1, 0)):
            c.create_text(cx + dx * (R - 13), cy + dy * (R - 13),
                          text=glyph, fill=C_BLUE, font=font_body_bold(11))
        # Merkez = sürekli durdur bölgesi
        r = 15.0
        c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=C_RED, width=2)
        c.create_text(cx, cy, text="⏹", fill=C_RED, font=font_body_bold(9))
        # Topuz (parmağı takip eder, bırakınca ortaya döner)
        kx = max(-R, min(R, ox))
        ky = max(-R, min(R, oy))
        c.create_oval(cx + kx - 20, cy + ky - 20,
                      cx + kx + 20, cy + ky + 20,
                      fill=C_BLUE, outline=C_BG, width=2)

    _JOY_DIRS8 = ("right", "down_right", "down", "down_left",
                  "left", "up_left", "up", "up_right")

    def _joy_offset(self, e):
        c = self._garden_joystick_canvas
        cx = int(c["width"]) / 2.0
        cy = int(c["height"]) / 2.0
        return e.x - cx, e.y - cy

    def _joy_direction(self, dx, dy):
        import math
        m = math.hypot(dx, dy)
        if m < 20.0:
            return None
        ang = math.degrees(math.atan2(dy, dx))
        return self._JOY_DIRS8[int(round(ang / 45.0)) % 8]

    def _joy_run(self, fn, *args):
        if fn:
            threading.Thread(target=fn, args=args, daemon=True).start()

    def _joy_center_stop_loop(self):
        if not (self._joy_active and self._joy_pressed and
                self._joy_current is None):
            self._joy_stop_timer = None
            return
        self._joy_run(self.on_garden_ptz, "stop")
        self._joy_stop_timer = self.root.after(300, self._joy_center_stop_loop)

    def _garden_joy_press(self, e):
        self._joy_active = True
        self._joy_pressed = True
        self._joy_current = None
        dx, dy = self._joy_offset(e)
        self._draw_garden_joystick(dx, dy)
        self._garden_joy_apply(dx, dy)

    def _garden_joy_drag(self, e):
        if not self._joy_active:
            return
        dx, dy = self._joy_offset(e)
        # Topuzu pad sınırında kıs
        import math
        m = math.hypot(dx, dy)
        if m > 62.0:
            dx = dx / m * 62.0
            dy = dy / m * 62.0
        self._draw_garden_joystick(dx, dy)
        self._garden_joy_apply(dx, dy)

    def _garden_joy_apply(self, dx, dy):
        direction = self._joy_direction(dx, dy)
        if direction == self._joy_current:
            return
        previous = self._joy_current
        self._joy_current = direction
        if self._joy_stop_timer is not None:
            self.root.after_cancel(self._joy_stop_timer)
            self._joy_stop_timer = None
        if direction is None:
            # Merkez bölge: kamerayı sürekli durdurmaya devam et
            self._joy_run(self.on_garden_ptz_stop)
            self._joy_stop_timer = self.root.after(300, self._joy_center_stop_loop)
            return
        if previous is not None:
            # Yön değişti: eski dönüşü kes, yenisiyle devam et
            self._joy_run(self.on_garden_ptz_stop)
        self._joy_run(self.on_garden_ptz_start, direction)

    def _garden_joy_release(self, e):
        self._joy_active = False
        self._joy_pressed = False
        if self._joy_stop_timer is not None:
            self.root.after_cancel(self._joy_stop_timer)
            self._joy_stop_timer = None
        self._joy_current = None
        self._draw_garden_joystick(0.0, 0.0)
        self._joy_run(self.on_garden_ptz_stop)

    def _place_garden_ptz_bar(self, cam_w, cam_x, cam_y, cam_h):
        js = 160
        jx = cam_x + (cam_w - js) // 2
        jy = cam_y + cam_h + 6
        self._garden_joystick_canvas.place(x=jx, y=jy, width=js, height=js)
        self._raise_widget(self._garden_joystick_canvas)
        tool_w = 96
        tool_gap = 6
        tool_total = len(self._garden_tool_canvases) * tool_w + \
            tool_gap * (len(self._garden_tool_canvases) - 1)
        tx = cam_x + (cam_w - tool_total) // 2
        ty = jy + js + 6
        for tool, c in self._garden_tool_canvases.items():
            c.place(x=tx, y=ty, width=tool_w, height=30)
            self._raise_widget(c)
            tx += tool_w + tool_gap

        # FOTO / VİDEO / DURAKLAT — alet çubuğunun (ALARM/KONUŞ) hemen altına.
        # Webcam panelindeki AYNI üç düğme; bahçe kamerası akışı da
        # WebcamStreamer ile birebir aynı arayüzü (is_active/get_latest_frame)
        # sunduğundan foto/video çekimi hiç değişiklik gerektirmeden çalışır.
        self._place_capture_buttons_at(cam_w, cam_x, ty + 30 + 6)

    def _hide_garden_ptz_bar(self):
        self._joy_active = False
        self._joy_pressed = False
        if self._joy_stop_timer is not None:
            self.root.after_cancel(self._joy_stop_timer)
            self._joy_stop_timer = None
        self._joy_current = None
        self._garden_joystick_canvas.place_forget()
        for c in self._garden_tool_canvases.values():
            c.place_forget()
        self._hide_camera_capture_buttons()

    def set_garden_active(self, active: bool):
        self._garden_active = bool(active)
        self.root.after(0, self._draw_garden_button)
        if active:
            cam_w, cam_h, cam_x, cam_y, shift, face = self._calc_cam_layout()
            self._cam_orb_shift_target = float(shift)
            self._cam_orb_face_target  = float(face)
            if self._cam_orb_face < 1.0:
                self._cam_orb_face = float(self.FACE)
            self.root.after(0, self._draw_camera_capture_buttons)
            self.root.after(0, lambda: self._place_garden_ptz_bar(
                cam_w, cam_x, cam_y, cam_h))
        else:
            self._cam_orb_shift_target = 0.0
            self._cam_orb_face_target  = float(self.FACE)
            self._webcam_photo = None
            if self._cam_label is not None:
                self._cam_label.place_forget()
            self._cam_recording = False
            self._cam_rec_paused = False
            self.root.after(0, self._draw_camera_capture_buttons)
            self.root.after(0, self._hide_garden_ptz_bar)
        self.write_log(f"SYS: Bahçe kamerası {'CANLI' if active else 'KAPALI'}")

    def _build_garden_settings(self, parent=None):
        parent = parent or self._settings_body
        self._garden_settings_label = tk.Label(
            parent, text="BAHÇE KAMERA (DVRIP — IP/PORT/KULLANICI/ŞİFRE)",
            fg=C_MID, bg=parent.cget("bg"), justify="left",
            font=font_body_bold(8), anchor="w")
        self._garden_setting_rows = []
        self._garden_entries = {}
        fields = (
            ("garden_host", "IP"),
            ("garden_port", "PORT"),
            ("garden_user", "KULLANICI"),
            ("garden_pass", "ŞİFRE"),
        )
        for key, label in fields:
            row = tk.Frame(parent, bg=parent.cget("bg"))
            tk.Label(row, text=label, fg=C_PRI, bg=parent.cget("bg"),
                     font=font_body_bold(9), width=10, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(get_app_config_value(key, "") or ""))
            ent = tk.Entry(
                row, textvariable=var,
                fg=C_TEXT, bg=C_DIMMER, insertbackground=C_TEXT,
                show="*" if key == "garden_pass" else None,
                borderwidth=0, font=font_body(10),
                highlightthickness=1, highlightbackground=C_DIM,
                highlightcolor=C_PRI)
            ent.pack(side="left", fill="x", expand=True)
            ent.bind("<FocusOut>", lambda e, k=key, v=var: self._save_garden_entry(k, v))
            ent.bind("<Return>", lambda e, k=key, v=var: self._save_garden_entry(k, v))
            self._garden_entries[key] = var
            self._garden_setting_rows.append(row)

    def _save_garden_entry(self, key: str, var):
        value = str(var.get() or "").strip()
        try:
            save_app_config({key: value})
            self.write_log(f"SYS: BAHÇE KAMERA '{key}' güncellendi.")
        except Exception as e:
            self.write_log(f"ERR: BAHÇE KAMERA ayarı kaydedilemedi — {e}")

    # ── Kamera FOTO / VİDEO / DURAKLAT düğmeleri (kamera açıkken görünür) ────
    def _build_camera_capture_buttons(self):
        self._photo_canvas = tk.Canvas(self.root, width=100, height=30,
                                       bg=C_BG, highlightthickness=0, cursor="hand2")
        self._photo_canvas.bind("<Button-1>", lambda e: self._on_camera_photo_click())
        self._record_canvas = tk.Canvas(self.root, width=100, height=30,
                                        bg=C_BG, highlightthickness=0, cursor="hand2")
        self._record_canvas.bind("<Button-1>", lambda e: self._on_camera_record_click())
        self._cam_pause_canvas = tk.Canvas(self.root, width=100, height=30,
                                           bg=C_BG, highlightthickness=0, cursor="hand2")
        self._cam_pause_canvas.bind("<Button-1>", lambda e: self._on_camera_pause_click())
        self._draw_camera_capture_buttons()

    def _draw_bracket_button(self, canvas, col, text):
        c = canvas
        bw, bh = int(c["width"]), int(c["height"])
        c.delete("all")
        bl = 5
        for bx, by, sx, sy in [(0, 0, 1, 1), (bw, 0, -1, 1),
                                (0, bh, 1, -1), (bw, bh, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)
        c.create_text(bw//2, bh//2, text=text, fill=col, font=font_body_bold(10))

    def _draw_camera_capture_buttons(self):
        self._draw_bracket_button(self._photo_canvas, C_GOLD, "📷 FOTO")
        if self._cam_recording:
            col, text = C_RED, "⏹ DURDUR"
        else:
            col, text = C_GREEN, "⏺ VİDEO"
        self._draw_bracket_button(self._record_canvas, col, text)
        if not self._cam_recording:
            col, text = C_DIM, "⏸ DURAKLAT"
        elif self._cam_rec_paused:
            col, text = C_GOLD, "▶ DEVAM"
        else:
            col, text = C_BLUE, "⏸ DURAKLAT"
        self._draw_bracket_button(self._cam_pause_canvas, col, text)

    def _run_camera_hook(self, hook, *args):
        """Kamera işlemleri (dosya yazma/kare çözme) UI thread'ini kilitlemesin
        diye arka planda çalıştırır; sonucu günlüğe yazar."""
        if not hook:
            self.write_log("SYS: Bu kamera özelliği bu modda bağlı değil.")
            return

        def _run():
            try:
                msg = hook(*args)
                if msg:
                    self.write_log(f"SYS: {msg}")
            except Exception as e:
                self.write_log(f"ERR: Kamera işlemi başarısız — {e}")
        threading.Thread(target=_run, daemon=True).start()

    def _on_camera_photo_click(self):
        if not (self._webcam_active or self._garden_active):
            self.write_log("SYS: Önce kamerayı aç.")
            return
        self._run_camera_hook(self.on_camera_photo)

    def _on_camera_record_click(self):
        if not (self._webcam_active or self._garden_active):
            self.write_log("SYS: Önce kamerayı aç.")
            return
        self._cam_recording = not self._cam_recording
        self._cam_rec_paused = False
        self._draw_camera_capture_buttons()
        self._run_camera_hook(self.on_camera_record_toggle, self._cam_recording)

    def _on_camera_pause_click(self):
        if not self._cam_recording:
            return
        self._cam_rec_paused = not self._cam_rec_paused
        self._draw_camera_capture_buttons()
        self._run_camera_hook(self.on_camera_pause_toggle, self._cam_rec_paused)

    def _toggle_mute(self):
        self.muted = not self.muted
        self._draw_mute_button()
        if self.muted:
            self.write_log("SYS: Mikrofon kapatıldı.")
        else:
            self.write_log("SYS: Mikrofon açık.")
        self._sync_sound_state()

    # ── Orb tıklama = pause ──────────────────────────────────────────────────
    def _on_canvas_click(self, event):
        dx = event.x - self.FCX
        dy = event.y - self.FCY
        if dx*dx + dy*dy <= (self.FACE * 0.40)**2:
            self._toggle_pause()

    def _toggle_pause(self):
        self.paused = not self.paused
        self._draw_pause_button()
        if self.paused:
            self.set_state("PAUSED")
            self.write_log("SYS: YERINDE duraklatıldı.")
        else:
            self.set_state("THINKING")
            self.write_log("SYS: YERINDE devam ediyor...")
        self._sync_sound_state()
        if self.on_pause_toggle:
            threading.Thread(target=self.on_pause_toggle, args=(self.paused,), daemon=True).start()

    def _shutdown(self):
        self.sound.stop_all()
        self.write_log("SYS: YERINDE kapatılıyor...")
        self.root.after(380, os._exit, 0)

    # ── Input bar ────────────────────────────────────────────────────────────
    def _build_input_bar(self, lw: int):
        x0 = self.CHAT_X
        btn_w = 76
        gap = 8
        inp_w = lw - btn_w - gap

        self._input_var   = tk.StringVar()
        self._input_entry = tk.Entry(
            self.root, textvariable=self._input_var,
            fg=C_TEXT, bg=C_DIMMER, insertbackground=C_TEXT,
            borderwidth=0, font=font_body(11),
            highlightthickness=1, highlightbackground=C_DIM,
            highlightcolor=C_PRI)
        self._input_entry.place(
            x=x0, y=self.CHAT_INPUT_Y, width=inp_w, height=INPUT_H)
        self._input_entry.bind("<Return>",   self._on_input_submit)
        self._input_entry.bind("<KP_Enter>", self._on_input_submit)

        self._send_btn = tk.Button(
            self.root, text="GÖNDER ▸",
            command=self._on_input_submit,
            fg=C_ORG, bg=C_PANEL,
            activeforeground=C_BG, activebackground=C_ORG,
            font=font_body_bold(10),
            borderwidth=0, cursor="hand2",
            highlightthickness=1, highlightbackground=C_ORG)
        self._send_btn.place(
            x=x0+inp_w+gap, y=self.CHAT_INPUT_Y,
            width=btn_w, height=INPUT_H)

    def _place_layout_widgets(self):
        self.log_frame.place(x=self.CHAT_X, y=self.CHAT_Y, width=self.CHAT_W, height=self.CHAT_H)
        gap = 10
        mute_w = 126
        pause_w = 126
        stop_w = 96
        cam_w  = 110
        shutdown_w = int(self._shutdown_canvas["width"])
        total = mute_w + pause_w + stop_w + cam_w + shutdown_w + gap * 4
        start_x = self.FCX - total // 2
        row1_y = self.CTRL_Y + 20

        self._mute_canvas.place(x=start_x, y=row1_y)
        self._pause_canvas.place(x=start_x + mute_w + gap, y=row1_y)
        self._stop_canvas.place(x=start_x + mute_w + pause_w + gap * 2, y=row1_y)
        self._cam_canvas.place(x=start_x + mute_w + pause_w + stop_w + gap * 3, y=row1_y)
        self._shutdown_canvas.place(x=start_x + mute_w + pause_w + stop_w + cam_w + gap * 4, y=row1_y)

        # İkinci kontrol satırı — bahçe kamerası (BAHÇE KAMERASI + UYANDIR)
        g_gap = 10
        g_total = 170 + 170 + g_gap
        g_start_x = self.FCX - g_total // 2
        row2_y = row1_y + 36 + 8
        self._garden_canvas.place(x=g_start_x, y=row2_y, width=170, height=36)
        self._garden_wake_canvas.place(x=g_start_x + 170 + g_gap, y=row2_y, width=170, height=36)

        geo = self._settings_geometry
        panel_x = geo["panel_x"]
        panel_y = geo["panel_y"]
        panel_w = geo["panel_w"]
        panel_h = geo["panel_h"]
        if self._settings_open:
            self._settings_panel.place(x=panel_x, y=panel_y, width=panel_w, height=panel_h)
            self._settings_panel.lift()
            self._settings_title.place(x=14, y=12)
            self._settings_tab_settings.place(x=14, y=40)
            self._settings_tab_debug.place(x=130, y=40)
            if self._settings_tab == "debug":
                self._settings_scroll_canvas.place_forget()
                self._debug_body.place(x=12, y=76, width=panel_w - 24, height=panel_h - 88)
                self._debug_text.place(x=0, y=0, width=panel_w - 24, height=panel_h - 88)
                self._debug_body.lift()
            else:
                self._debug_body.place_forget()
                self._settings_scroll_canvas.place(x=12, y=76, width=panel_w - 24, height=panel_h - 88)
                self._raise_widget(self._settings_scroll_canvas)
        else:
            self._settings_panel.place_forget()
            self._settings_title.place_forget()
            self._settings_tab_settings.place_forget()
            self._settings_tab_debug.place_forget()
            self._settings_scroll_canvas.place_forget()
            self._debug_body.place_forget()

        if hasattr(self, "_social_bar"):
            self._social_bar.place(x=14, y=self.H - FOOTER_H - 52)

        inp_w = self.CHAT_W - 84
        self._input_entry.place(x=self.CHAT_X, y=self.CHAT_INPUT_Y, width=inp_w, height=INPUT_H)
        self._send_btn.place(x=self.CHAT_X + inp_w + 8, y=self.CHAT_INPUT_Y, width=76, height=INPUT_H)

    def _on_input_submit(self, event=None):
        text = self._input_var.get().strip()
        if not text:
            return
        if self.paused:
            self.write_log("SYS: YERINDE duraklatılmış durumda. Devam etmek için pause'u kapat.")
            return
        self._input_var.set("")
        if text.lower() in ("sus", "dur", "stop", "sessiz", "kes"):
            self.write_log("SYS: ⏹ Ses kesildi.")
            if self.on_stop_command:
                threading.Thread(target=self.on_stop_command, daemon=True).start()
            return
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(text,), daemon=True).start()

    # ── State & callbacks ────────────────────────────────────────────────────
    def set_state(self, state: str):
        previous = getattr(self, "_yerinde_state", "")
        self._yerinde_state = state
        self.speaking = (state == "SPEAKING")
        if hasattr(self, "_stop_canvas"):
            self._draw_stop_button()
        if state == "THINKING":
            self.sound.start_thinking()
        elif previous == "THINKING":
            self.sound.stop_thinking()
        if state == "ERROR" and previous != "ERROR":
            self.sound.play_error()

    def set_user_speaking(self, value: bool):
        self.mark_user_activity(value)

    def mark_user_activity(self, active: bool = True):
        self.user_speaking = active
        self._user_speaking_until = time.time() + (0.9 if active else 0.0)

    def get_effects_volume(self) -> float:
        return self.sound.get_volume()

    def effects_enabled(self) -> bool:
        return bool(self._effects_active)

    def play_success_sfx(self):
        self.root.after(0, self.sound.play_success)

    def play_error_sfx(self):
        self.root.after(0, self.sound.play_error)

    def wake_up(self):
        """Çift alkışla tetiklenir — pencereyi öne getirir."""
        def _do():
            try:
                self.root.deiconify()
                self.root.attributes("-topmost", True)
                self.root.lift()
                self.root.focus_force()
                self.root.after(3000, lambda: self.root.attributes("-topmost", False))
            except Exception:
                pass
        self.root.after(0, _do)

    # ── Webcam layout hesabı ─────────────────────────────────────────────────
    def _cam_extra_below(self) -> int:
        """Kamera görüntüsünün ALTINDA duracak sabit panelin toplam
        yüksekliğini döndürür — _calc_cam_layout bu kadar yer ayırır,
        aksi halde panel (bahçe modunda: PTZ joystick + ALARM/KONUŞ alet
        çubuğu + FOTO/VİDEO/DURAKLAT düğmeleri) merkez alanın dışına taşıp
        üstten/alttan kesik görünür."""
        if self._webcam_active:
            return 30 + 6                              # yalnızca FOTO/VİDEO/DURAKLAT
        if self._garden_active:
            js = 160
            return js + 6 + 30 + 6 + 30 + 6             # joystick + alet çubuğu + düğmeler
        return 30 + 6

    def _calc_cam_layout(self):
        """Kamera paneli boyutları + orb kayma değerlerini döndürür.

        Dönen değerler: (cam_w, cam_h, cam_x, cam_y, orb_shift, orb_face)

        Kamera altında duracak panelin (webcam: FOTO/VİDEO/DURAKLAT; bahçe:
        PTZ joystick + alet çubuğu + aynı düğmeler — bkz. _cam_extra_below)
        yüksekliği burada HESABA KATILIR: dar/kısa pencerelerde kamera
        görüntüsü küçültülerek altındaki panelin ekranın dışına taşması
        (üstten/alttan kesilmesi) önlenir.
        """
        extra_below = self._cam_extra_below()
        center_w  = self.CENTER_X1 - self.CENTER_X0
        total_h   = self.CTRL_Y - HDR_H          # merkez alanın toplam yüksekliği
        max_cam_w = min(center_w - 40, 640 if self._garden_active else 580)
        # Kamera + altındaki panel + üst/alt tampon, merkez alana sığmalı —
        # sığmıyorsa kamera (oran korunarak) küçültülür. Bahçe modunda
        # tampon daha dar tutulur ki önizleme kutusu aşağı doğru uzasın.
        _pad = 12 if self._garden_active else 24
        max_cam_h = max(90, total_h - extra_below - _pad)
        if self._garden_active:
            # Bahçe kamerası kaynağı 16:9'dan daha dikey (yaklaşık 4:3) —
            # bu yüzden önizleme kutusu da alta doğru uzatılır; aksi halde
            # görüntü üstten/alttan kırpılıp sahne kesik görünür.
            cam_h = min(int(max_cam_w * 3 / 4), max_cam_h)
            cam_w = int(cam_h * 4 / 3)
        else:
            cam_h = min(int(max_cam_w * 9 / 16), max_cam_h)
            cam_w = int(cam_h * 16 / 9)
        remaining = max(0, total_h - cam_h - extra_below - 24)   # kamera+panel altında orb için kalan alan
        new_face  = max(80, min(int(remaining * 0.82),
                                 int(center_w  * 0.70), 520))
        new_cy    = HDR_H + cam_h + extra_below + 16 + remaining // 2   # orb'un yeni merkezi
        shift     = new_cy - self.FCY
        cam_x     = self.FCX - cam_w // 2
        cam_y     = HDR_H + 8
        return cam_w, cam_h, cam_x, cam_y, shift, new_face

    def set_webcam_active(self, active: bool):
        self._webcam_active = bool(active)
        self.root.after(0, self._draw_webcam_button)
        if active:
            cam_w, cam_h, cam_x, cam_y, shift, face = self._calc_cam_layout()
            self._cam_orb_shift_target = float(shift)
            self._cam_orb_face_target  = float(face)
            # İlk açılışta face'i FACE'den başlat ki animasyon doğal görünsün
            if self._cam_orb_face < 1.0:
                self._cam_orb_face = float(self.FACE)
            self.root.after(0, lambda: self._place_camera_capture_buttons(
                cam_w, cam_x, cam_y, cam_h))
        else:
            self._cam_orb_shift_target = 0.0
            # Hedef: normal FACE boyutuna geri dön. Animasyon bitince 0'a sıfırlanır
            # (_animate içinde), böylece FACE→0 geçişi görünmez.
            self._cam_orb_face_target  = float(self.FACE)
            self._webcam_photo  = None
            if self._cam_label is not None:
                self._cam_label.place_forget()
            self._cam_recording = False
            self._cam_rec_paused = False
            self.root.after(0, self._draw_camera_capture_buttons)
            self.root.after(0, self._hide_camera_capture_buttons)
        self.write_log(f"SYS: Webcam {'CANLI' if active else 'KAPALI'}")

    @staticmethod
    def _raise_widget(widget):
        """Bir widget'i pencere yığın sırasında (stacking order) en üste
        çıkarır. tk.Canvas için .tkraise() ve .lift() metotları Tkinter
        tarafından tag_raise/tag_lift'e yönlendirilir ve bir "tagOrId"
        argümanı ister; argümansız çağrılınca
        "wrong # args: should be '.!canvasN raise tagOrId ?aboveThis?'"
        hatasını fırlatır. Bunun yerine widget'ın Tk komutunu doğrudan
        çağırıyoruz — bu, hem Canvas hem de diğer widget'lar için güvenli
        çalışır.
        """
        widget.tk.call('raise', widget._w)

    def _place_camera_capture_buttons(self, cam_w, cam_x, cam_y, cam_h):
        """FOTO/VİDEO/DURAKLAT düğmelerini kamera önizlemesinin hemen altına,
        yan yana üç eşit parçaya bölerek yerleştirir."""
        self._place_capture_buttons_at(cam_w, cam_x, cam_y + cam_h + 6)

    def _place_capture_buttons_at(self, cam_w, cam_x, y):
        """FOTO/VİDEO/DURAKLAT düğmelerini verilen (cam_x, y) noktasının
        altına, yan yana üç eşit parçaya bölerek yerleştirir. Hem normal
        webcam paneli (kamera görüntüsünün hemen altı) hem de bahçe kamerası
        paneli (PTZ joystick + alet çubuğunun altı) BU metodu çağırır — aynı
        üç Canvas nesnesi (fiziksel tek webcam donanımı gibi) her iki modda
        da yeniden konumlanarak paylaşılır."""
        gap = 8
        btn_w = (cam_w - gap * 2) // 3
        self._photo_canvas.place(x=cam_x, y=y, width=btn_w, height=30)
        self._record_canvas.place(x=cam_x + btn_w + gap, y=y, width=btn_w, height=30)
        self._cam_pause_canvas.place(x=cam_x + (btn_w + gap) * 2, y=y, width=btn_w, height=30)
        # NOT: tk.Canvas için .tkraise() ve .lift() de tag_raise'e
        # yönlendirilir ve tagOrId ister (bkz. _raise_widget). Bu yüzden
        # widget'ı öne almak için _raise_widget() kullanıyoruz.
        self._raise_widget(self._photo_canvas)
        self._raise_widget(self._record_canvas)
        self._raise_widget(self._cam_pause_canvas)

    def _hide_camera_capture_buttons(self):
        self._photo_canvas.place_forget()
        self._record_canvas.place_forget()
        self._cam_pause_canvas.place_forget()

    def update_webcam_preview(self, jpeg_bytes: bytes) -> None:
        """Live webcam karesini dikdörtgen panel'de gösterir. Thread-safe."""
        self.root.after(0, lambda: self._show_webcam_preview(jpeg_bytes))

    def _show_webcam_preview(self, jpeg_bytes: bytes) -> None:
        """JPEG'i üst-orta alana dikdörtgen Label olarak basar."""
        if not (self._webcam_active or self._garden_active):
            return
        try:
            import io
            cam_w, cam_h, cam_x, cam_y, _, _ = self._calc_cam_layout()

            img   = Image.open(io.BytesIO(jpeg_bytes))
            # Oranı koru, merkez crop ile 16:9'a getir
            iw, ih  = img.size
            target_ratio = cam_w / cam_h
            src_ratio    = iw / ih
            if src_ratio > target_ratio:            # daha geniş → sol/sağ kırp
                new_w = int(ih * target_ratio)
                img   = img.crop(((iw - new_w) // 2, 0,
                                  (iw + new_w) // 2, ih))
            else:                                   # daha uzun → üst/alt kırp
                new_h = int(iw / target_ratio)
                img   = img.crop((0, (ih - new_h) // 2,
                                  iw, (ih + new_h) // 2))
            img   = img.resize((cam_w, cam_h), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)

            if self._cam_label is None:
                self._cam_label = tk.Label(
                    self.root, bg=C_BG,
                    highlightthickness=1,
                    highlightbackground=C_MID,
                )
            self._cam_label.configure(image=photo)
            self._webcam_photo = photo          # referans tut — GC koruması
            self._cam_label.place(x=cam_x, y=cam_y,
                                  width=cam_w, height=cam_h)
            # bg canvas'ın hemen üstüne taşı — settings paneli vs. üstte kalır
            self._cam_label.lift(self.bg)
        except Exception as exc:
            print(f"[UI] Webcam preview güncellenemedi: {exc}")

    def focus_panel(self, section: str, duration_ms: int = 4200):
        section = (section or "").strip().lower()
        if not section:
            return

        def _apply():
            self._panel_focus = section
            self._panel_focus_until = time.time() + max(0.8, duration_ms / 1000.0)

        self.root.after(0, _apply)

    def _state_color(self, state: str | None = None) -> str:
        effective = state or self._yerinde_state
        if effective == "PAUSED":
            return C_MID
        return STATE_HEX_COLORS.get(effective, C_PRI)

    @staticmethod
    def _state_badge_text(state: str) -> str:
        if state == "INITIALISING":
            return "BAĞLANIYOR"
        if state == "ERROR":
            return "HATA"
        return "ÇEVRİMİÇİ"

    @staticmethod
    def _state_label_tr(state: str) -> str:
        return {
            "LISTENING":     "Dinliyor",
            "SPEAKING":      "Konuşuyor",
            "THINKING":      "Düşünüyor",
            "ERROR":         "Hata",
            "PAUSED":        "Duraklatıldı",
            "INITIALISING":  "Başlıyor",
            "MUTED":         "Sessiz",
        }.get(state, str(state).title())

    # ── Log ──────────────────────────────────────────────────────────────────
    def write_log(self, text: str):
        self.typing_queue.append(text)
        tl = text.lower()
        if tl.startswith("siz:") or tl.startswith("you:"):
            self.mark_user_activity(True)
            self.set_state("THINKING")
        elif tl.startswith("err:") or "error" in tl:
            self._error_hold_until = time.time() + 8.0
            self.set_state("ERROR")
            self.write_debug(text, level="ERROR")
        elif tl.startswith("yerinde:") or tl.startswith("ai:"):
            # Hangi mod aktif olursa olsun (Gemini Live / Ollama / V3
            # çekirdek), asistanın nihai yanıtı buradan geçer — bağlı bir
            # telefon istemcisi varsa aynı metni ona da ilet.
            try:
                from core import remote_server
                _prefix_len = text.index(":") + 1
                remote_server.broadcast_response(text[_prefix_len:].strip())
            except Exception:
                pass
        if not self.is_typing:
            self._start_typing()

    def _start_typing(self):
        if not self.typing_queue:
            self.is_typing = False
            if self._yerinde_state == "ERROR" and time.time() < self._error_hold_until:
                return
            if not self.speaking:
                self.set_state("LISTENING")
            return
        self.is_typing = True
        text = self.typing_queue.popleft()
        tl   = text.lower()
        if   tl.startswith("siz:") or tl.startswith("you:"):   tag = "you"
        elif tl.startswith("yerinde:") or tl.startswith("ai:"): tag = "ai"
        elif tl.startswith("err:") or "error" in tl:           tag = "err"
        else:                                                    tag = "sys"
        self.log_text.configure(state="normal")
        self._type_char(text, 0, tag)

    def _type_char(self, text, i, tag):
        if i < len(text):
            self.log_text.insert(tk.END, text[i], tag)
            self.log_text.see(tk.END)
            self.root.after(7, self._type_char, text, i+1, tag)
        else:
            self.log_text.insert(tk.END, "\n")
            self.log_text.configure(state="disabled")
            self.root.after(20, self._start_typing)

    # ── Stats ────────────────────────────────────────────────────────────────
    def _update_stats(self):
        try:
            self._stats['cpu']  = psutil.cpu_percent()
            self._stats['ram']  = psutil.virtual_memory().percent
            self._stats['disk'] = psutil.disk_usage('/').percent
            batt = psutil.sensors_battery()
            self._stats['battery'] = batt.percent if batt else 100.0
            gpu = get_gpu_status()
            if gpu:
                self._stats['gpu'] = gpu.get('usage_pct') if gpu.get('usage_pct') is not None else 0.0
                self._stats['gpu_name'] = gpu.get('name', 'GPU')
            else:
                self._stats['gpu'] = 0.0
                self._stats['gpu_name'] = ''
            now = time.time()
            net = psutil.net_io_counters()
            dt  = now - self._last_net_t
            if dt > 0:
                self._stats['net_up']   = max(0, (net.bytes_sent - self._last_net.bytes_sent) / dt / 1024)
                self._stats['net_down'] = max(0, (net.bytes_recv - self._last_net.bytes_recv) / dt / 1024)
            self._last_net   = net
            self._last_net_t = now
            self._cpu_hist.pop(0)
            self._cpu_hist.append(self._stats['cpu'])
        except Exception:
            pass

    # ── Animation loop ───────────────────────────────────────────────────────
    def _animate(self):
        self.tick += 1
        t   = self.tick
        now = time.time()

        if self.user_speaking and now > self._user_speaking_until:
            self.user_speaking = False

        if t % 90 == 0:
            threading.Thread(target=self._update_stats, daemon=True).start()
        if t % 1800 == 1:
            self._kick_brief_refresh()

        if self.speaking and t % 3 == 0:
            self._wave_yerinde = [random.randint(6, 30) for _ in range(18)]
        if self.user_speaking and t % 3 == 0:
            self._wave_user = [random.randint(5, 24) for _ in range(18)]

        if now - self.last_t > (0.12 if self.speaking else 0.50):
            if self.paused:
                self.target_scale = random.uniform(0.58, 0.64)
                self.target_halo  = random.uniform(5, 10)
            elif self.speaking:
                self.target_scale = random.uniform(0.98, 1.10)
                self.target_halo  = random.uniform(180, 250)
            elif self.user_speaking:
                self.target_scale = random.uniform(0.88, 0.98)
                self.target_halo  = random.uniform(120, 175)
            elif self._yerinde_state in ("THINKING", "INITIALISING"):
                self.target_scale = random.uniform(0.80, 0.88)
                self.target_halo  = random.uniform(95, 145)
            else:
                self.target_scale = random.uniform(0.72, 0.80)
                self.target_halo  = random.uniform(34, 58)
            self.last_t = now

        sp          = 0.34 if self.speaking else 0.18
        self.scale  += (self.target_scale - self.scale) * sp
        self.halo_a += (self.target_halo   - self.halo_a) * sp

        # Kamera orb animasyonu — ~0.07 ease ≈ 400 ms settle @40ms frame
        _CE = 0.07
        self._cam_orb_shift += (self._cam_orb_shift_target - self._cam_orb_shift) * _CE
        self._cam_orb_face  += (self._cam_orb_face_target  - self._cam_orb_face)  * _CE
        if abs(self._cam_orb_shift_target - self._cam_orb_shift) < 0.5:
            self._cam_orb_shift = self._cam_orb_shift_target
        if abs(self._cam_orb_face_target - self._cam_orb_face) < 0.5:
            self._cam_orb_face = self._cam_orb_face_target
            # Kamera kapandıktan sonra animasyon bitince face'i temizle
            if not self._webcam_active:
                self._cam_orb_face        = 0.0
                self._cam_orb_face_target = 0.0

        if self.paused:
            spds = [0.0, 0.0, 0.0, 0.0]
        elif self.speaking:
            spds = [1.6, -1.1, 2.4, -0.7]
        else:
            spds = [0.55, -0.35, 0.90, -0.28]
        for i, spd in enumerate(spds):
            self.rings_spin[i] = (self.rings_spin[i] + spd) % 360

        # Pulse rings
        pspd  = 4.2 if self.speaking else 1.8
        limit = self.FACE * 0.68
        self.pulse_r = [r + pspd for r in self.pulse_r if r + pspd < limit]
        if len(self.pulse_r) < 3 and random.random() < (0.07 if self.speaking else 0.02):
            self.pulse_r.append(0.0)

        for p in self.particles:
            p['x'] = (p['x'] + p['vx']) % self.W
            p['y'] = (p['y'] + p['vy']) % self.H

        if t % 38 == 0:
            self.status_blink = not self.status_blink

        self._draw()
        self.root.after(40, self._animate)

    # ── Yardımcı ─────────────────────────────────────────────────────────────
    @staticmethod
    def _ac(r, g, b, a):
        f = max(0, min(255, int(a))) / 255.0
        return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    @staticmethod
    def _hex_rgb(hexcolor):
        h = hexcolor.lstrip("#")
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def _orb_rgb(self):
        state = "PAUSED" if self.paused else self._yerinde_state
        return ORB_COLORS.get(state, ORB_COLORS["LISTENING"])

    @staticmethod
    def _split_summary_lines(text: str, limit: int = 4) -> list[str]:
        raw = (text or "").strip()
        if not raw:
            return []
        raw = raw.replace(" ve ", ", ")
        parts = [part.strip(" .") for part in raw.split(",") if part.strip()]
        return parts[:limit]

    def _parse_weather_card(self, text: str) -> dict:
        from actions.weather import display_location
        loc = display_location()          # {'baslik': 'VAYSAL KÖYÜ', 'alt': 'LALAPAŞA · EDİRNE'}

        if not text or "alınamadı" in text.lower() or "alınamadi" in text.lower():
            return {
                "city": loc["baslik"],
                "region": loc["alt"],
                "primary": "--",
                "details": ["Hava durumu alınamadı."],
            }

        _prefix, _, body = text.partition(":")
        details = [part.strip(" .") for part in body.split(",") if part.strip()]
        primary = "--"
        if details:
            primary = details[0].replace(" derece", "°C")
        return {
            "city": loc["baslik"],        # KÖY adı büyük başlık
            "region": loc["alt"],         # LALAPAŞA · EDİRNE alt satır
            "primary": primary,
            "details": details[1:4] or ["Anlık veri hazır."],
        }

    def _kick_brief_refresh(self):
        if self._brief_refresh_busy:
            return
        self._brief_refresh_busy = True
        threading.Thread(target=self._refresh_brief_cards, daemon=True).start()

    def _refresh_brief_cards(self):
        try:
            weather = get_weather_summary()   # il/ilçe/köy config'ten
            self._weather_card = self._parse_weather_card(weather)
            try:
                from actions.weather import get_forecast
                self._weather_card["forecast"] = get_forecast(7)
            except Exception:
                self._weather_card["forecast"] = []
        except Exception:
            self._weather_card = {
                "city": "VAYSAL KÖYÜ",
                "region": "LALAPAŞA · EDİRNE",
                "primary": "--",
                "details": ["Hava durumu alınamadı."],
            }
        finally:
            self._brief_refresh_busy = False

    def _bar(self, c, x, y, w, h, pct, color):
        c.create_rectangle(x, y, x+w, y+h, fill=C_DIMMER, outline=C_DIM, width=1)
        fw = max(1, int(w * pct / 100))
        c.create_rectangle(x+1, y+1, x+fw, y+h-1, fill=color, outline="")

    def _sparkline(self, c, x, y, w, h, data):
        c.create_rectangle(x, y, x+w, y+h, fill=C_DIMMER, outline=C_DIM, width=1)
        n = len(data)
        if n < 2:
            return
        step = (w - 2) / (n - 1)
        h2   = h - 2
        coords = []
        for i, v in enumerate(data):
            coords.append(x + 1 + i * step)
            coords.append(y + h - 1 - int(h2 * v / 100))
        c.create_line(*coords, fill=C_PRI, width=1, smooth=True)

    def _bracket(self, c, x0, y0, pw, ph, col=None, bl=12):
        col = col or C_PRI
        for bx, by, sx, sy in [(x0, y0, 1, 1), (x0+pw, y0, -1, 1),
                                (x0, y0+ph, 1, -1), (x0+pw, y0+ph, -1, -1)]:
            c.create_line(bx, by, bx+sx*bl, by, fill=col, width=2)
            c.create_line(bx, by, bx, by+sy*bl, fill=col, width=2)

    def _draw_info_card(self, c, x0, y0, pw, ph, title, accent=C_PRI):
        focus = max(0.0, min(1.0, getattr(self, "_card_focus_boost", 0.0)))
        dimmed = bool(getattr(self, "_card_dimmed", False))
        glow = int(55 + 120 * focus)
        border = accent if focus > 0.08 else (C_DIMMER if dimmed else self._ac(*_hex_to_rgb_tuple(C_PRI), 190))
        fill = C_DIMMER if dimmed else C_PANEL
        c.create_rectangle(x0, y0, x0+pw, y0+ph, fill=fill, outline="")
        if focus > 0.08:
            for inset in range(3):
                c.create_rectangle(
                    x0-inset, y0-inset, x0+pw+inset, y0+ph+inset,
                    outline=self._ac(*ORB_COLORS["LISTENING"], max(12, glow - inset * 28)),
                    width=1,
                )
        self._bracket(c, x0, y0, pw, ph, col=border, bl=10)
        title_fill = C_MID if dimmed else accent
        line_fill = C_DIMMER if dimmed else C_DIM
        c.create_text(x0+14, y0+14, text=title, fill=title_fill,
                      font=font_display(10), anchor="w")
        c.create_line(x0+12, y0+28, x0+pw-12, y0+28, fill=line_fill)

    def _focus_boost_for(self, section: str) -> float:
        if self._panel_focus != section:
            return 0.0
        remaining = self._panel_focus_until - time.time()
        if remaining <= 0:
            return 0.0
        pulse = 0.65 + 0.35 * math.sin(self.tick * 0.12)
        return min(1.0, remaining / 4.0) * pulse

    # ── Sol panel ─────────────────────────────────────────────────────────────
    def _draw_left_panel(self, c):
        x0 = 10
        y0 = HDR_H + 10
        pw = self.LEFT_W - 18
        gap = 14
        total_h = self.H - HDR_H - FOOTER_H - 20
        card_area_h = total_h - gap * 3
        pad = 14
        bw = pw - 2 * pad

        cards = [
            ("time", 0.28, "SAAT", C_GOLD),
            ("weather", 0.34, "HAVA DURUMU · 7 GÜN", C_BLUE),
            ("system", 0.38, "SİSTEM DURUMU", C_PRI),
        ]
        any_focus_active = bool(self._panel_focus) and (self._panel_focus_until > time.time())
        weights = []
        for section, weight, _, _ in cards:
            weights.append(weight + (0.12 if self._focus_boost_for(section) > 0.08 else 0.0))
        total_weight = sum(weights)
        heights = [int(card_area_h * (weight / total_weight)) for weight in weights]
        heights[-1] += card_area_h - sum(heights)

        current_y = y0
        for (section, _, title, accent), ph in zip(cards, heights):
            focus_boost = self._focus_boost_for(section)
            dimmed = any_focus_active and focus_boost <= 0.08
            shift_x = int(14 * focus_boost)
            extra_w = int(22 * focus_boost)
            section_x = x0 + shift_x
            section_pw = pw + extra_w
            section_pad = pad + int(2 * focus_boost)
            section_bw = section_pw - 2 * section_pad
            muted_label = C_DIM if dimmed else C_MID
            muted_text = C_DIM if dimmed else C_TEXT
            muted_primary = C_DIM if dimmed else C_PRI
            muted_blue = C_DIM if dimmed else C_BLUE
            muted_green = C_DIM if dimmed else C_GREEN
            muted_gold = C_DIM if dimmed else C_GOLD
            muted_warn = C_DIM if dimmed else C_ORG2
            muted_red = C_DIM if dimmed else C_RED
            self._card_focus_boost = focus_boost
            self._card_dimmed = dimmed
            self._draw_info_card(c, section_x, current_y, section_pw, ph, title, accent=accent if not dimmed else C_DIM)

            if section == "time":
                c.create_text(section_x+section_pad, current_y+64, text=time.strftime("%H:%M"),
                              fill=muted_primary, font=font_display(36 if focus_boost > 0.08 else 34), anchor="w")
                c.create_text(section_x+section_pad, current_y+92, text=time.strftime(":%S"),
                              fill=muted_label, font=font_body_bold(13), anchor="w")
                c.create_text(section_x+section_pad, current_y+118, text=tr_date_str(),
                              fill=muted_gold, font=font_body_bold(11), anchor="w")
                c.create_text(section_x+section_pad, current_y+138, text=tr_day_str(),
                              fill=muted_text, font=font_body(10), anchor="w")

            elif section == "weather":
                c.create_text(section_x+section_pad, current_y+58, text=self._weather_card["primary"],
                              fill=muted_primary, font=font_display(30 if focus_boost > 0.08 else 28), anchor="w")
                # Köy adı (büyük) + ilçe · il (küçük)
                c.create_text(section_x+section_pad, current_y+84,
                              text=self._weather_card.get("city", ""),
                              fill=muted_label, font=font_body_bold(10), anchor="w")
                region = self._weather_card.get("region", "")
                wy = current_y + 102
                if region:
                    c.create_text(section_x+section_pad, wy, text=region,
                                  fill=muted_text, font=font_body(9), anchor="w")
                    wy += 18
                for line in self._weather_card["details"][:2]:
                    c.create_text(section_x+section_pad, wy, text=f"• {line}", fill=muted_text,
                                  font=font_body(10), anchor="w")
                    wy += 16

                # ── 7 günlük tahmin şeridi ──────────────────────────────────
                forecast = self._weather_card.get("forecast") or []
                if forecast:
                    wy += 4
                    c.create_line(section_x+section_pad, wy,
                                  section_x+section_pad+section_bw, wy,
                                  fill=muted_label, width=1)
                    wy += 12
                    col_w = section_bw / max(1, len(forecast))
                    for i, day in enumerate(forecast):
                        cx = section_x + section_pad + int(i * col_w + col_w / 2)
                        c.create_text(cx, wy, text=day["gun"], fill=muted_label,
                                      font=font_body_bold(9), anchor="center")
                        c.create_text(cx, wy + 15, text=f"{day['max']}°",
                                      fill=muted_primary, font=font_body_bold(10),
                                      anchor="center")
                        c.create_text(cx, wy + 29, text=f"{day['min']}°",
                                      fill=muted_text, font=font_body(9), anchor="center")
                        if day.get("yagis", 0) >= 40:
                            c.create_text(cx, wy + 43, text=f"%{day['yagis']}",
                                          fill=muted_blue, font=font_body(8),
                                          anchor="center")

            elif section == "system":
                cy = current_y + 44
                uptime = int(time.time() - self._started_at)
                up_min, up_sec = divmod(uptime, 60)
                up_hr, up_min = divmod(up_min, 60)
                c.create_text(section_x+section_pad, cy, text=f"ÇALIŞMA SÜRESİ  {up_hr:02d}:{up_min:02d}:{up_sec:02d}",
                              fill=muted_label, font=font_body_bold(9), anchor="w")
                cy += 22
                stat_rows = [("CPU", "cpu", "%"), ("RAM", "ram", "%")]
                if self._stats.get("gpu_name"):
                    stat_rows.append(("GPU", "gpu", "%"))
                stat_rows += [("DİSK", "disk", "%"), ("PİL", "battery", "%")]
                for label, key, unit in stat_rows:
                    val = self._stats[key]
                    col = C_RED if val > 80 and key != "battery" else C_ORG if val > 55 and key != "battery" else (C_RED if key == "battery" and val < 20 else C_GREEN if key == "battery" else C_PRI)
                    if dimmed:
                        col = muted_red if col == C_RED else muted_warn if col == C_ORG else muted_green if col == C_GREEN else muted_primary
                    c.create_text(section_x+section_pad, cy, text=label, fill=muted_label, font=font_body(10), anchor="w")
                    c.create_text(section_x+section_pw-section_pad, cy, text=f"{val:.0f}{unit}", fill=col, font=font_body_bold(10), anchor="e")
                    cy += 14
                    self._bar(c, section_x+section_pad, cy, section_bw, 7, val, col)
                    cy += 16
                up = self._stats["net_up"]
                down = self._stats["net_down"]
                up_s = f"{up:.1f} KB/s" if up < 1000 else f"{up/1024:.1f} MB/s"
                down_s = f"{down:.1f} KB/s" if down < 1000 else f"{down/1024:.1f} MB/s"
                c.create_line(section_x+section_pad, cy-4, section_x+section_pw-section_pad, cy-4, fill=C_DIM)
                c.create_text(section_x+section_pad, cy+10, text=f"▲ {up_s}", fill=muted_warn, font=font_body(10), anchor="w")
                c.create_text(section_x+section_pw-section_pad, cy+10, text=f"▼ {down_s}", fill=muted_green, font=font_body(10), anchor="e")

            current_y += ph + gap

        self._card_focus_boost = 0.0
        self._card_dimmed = False

    # ── Sağ panel ─────────────────────────────────────────────────────────────
    def _draw_right_panel(self, c):
        x0  = self.CHAT_PANEL_X
        y0  = self.CHAT_PANEL_Y
        pw  = self.CHAT_PANEL_W
        ph  = self.CHAT_PANEL_H
        pad = 10

        c.create_rectangle(x0, y0, x0+pw, y0+ph, fill=C_PANEL, outline="")
        self._bracket(c, x0, y0, pw, ph, col=C_MID)

        if self.paused:
            sc, st = C_MID, "PAUSED"
        else:
            sc, st = self._state_color(self._yerinde_state), self._yerinde_state

        c.create_text(x0+14, y0+16, text="KONUŞMA", fill=C_PRI,
                      font=font_display(11), anchor="w")
        c.create_text(x0+pw-pad, y0+16, text=self._state_label_tr(st), fill=sc,
                      font=font_body_bold(10), anchor="e")
        c.create_line(x0+pad, y0+28, x0+pw-pad, y0+28, fill=C_DIM)

    # ── ORB (ana çizim) ───────────────────────────────────────────────────────
    def _draw_orb(self, c, cam: bool = False):
        style = str(get_app_config_value("orb_style", "klasik"))
        if style == "anka":
            self._draw_orb_anka(c, cam=cam)
            return
        if style == "anka_baloncuk":
            self._draw_orb_anka_baloncuk(c, cam=cam)
            return
        if style == "destek":
            self._draw_orb_destek(c, cam=cam)
            return
        state = "PAUSED" if self.paused else self._yerinde_state
        t    = self.tick
        speak_pulse = 1.0
        if self.speaking:
            speak_pulse = 1.0 + 0.12 * math.sin(t * 0.23) + 0.05 * math.sin(t * 0.11 + 1.2)
        elif self.user_speaking:
            speak_pulse = 1.0 + 0.06 * math.sin(t * 0.18 + 0.7)
        elif state in ("THINKING", "INITIALISING"):
            speak_pulse = 1.0 + 0.03 * math.sin(t * 0.10)
        else:
            speak_pulse = 1.0 + 0.01 * math.sin(t * 0.07)

        move_x = 0
        move_y = 0
        if self.user_speaking:
            move_x = int(6 * math.sin(t * 0.06))
            move_y = int(4 * math.cos(t * 0.09 + 0.5))
        elif state in ("THINKING", "INITIALISING"):
            move_x = int(3 * math.sin(t * 0.045))
            move_y = int(2 * math.cos(t * 0.05 + 0.4))

        FCX  = self.FCX + move_x
        # _cam_orb_shift her zaman uygulanır — animasyon hem açılışta hem
        # kapanışta çalışır; kamera kapalıysa target=0 olduğundan doğal döner.
        FCY  = self.FCY + move_y + int(self._cam_orb_shift)
        base_face = (int(self._cam_orb_face) if self._cam_orb_face > 1.0 else self.FACE)
        FW   = int(base_face * self.scale * speak_pulse)
        R, G, B = self._orb_rgb()
        ha   = self.halo_a
        field_r = int(FW * 0.49)
        inner_r = int(FW * 0.34)
        activity = (
            0.10 if self.paused else
            1.00 if self.speaking else
            0.78 if self.user_speaking else
            0.62 if state in ("THINKING", "INITIALISING") else
            0.26
        )
        if state in ("THINKING", "INITIALISING"):
            accent_rgb = (255, 210, 72)
        elif self.speaking:
            accent_rgb = (170, 220, 255)
        elif self.user_speaking:
            accent_rgb = (118, 200, 255)
        else:
            accent_rgb = (120, 255, 185)

        # Pulse rings
        for pr in self.pulse_r:
            alpha = max(0, int(160 * (1.0 - pr / (FW * 0.70))))
            rr = int(pr + field_r * 0.96)
            c.create_oval(
                FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                outline=self._ac(R, G, B, alpha),
                width=1,
            )

        # Large outer glow
        if not self.paused:
            for i in range(10, 0, -1):
                frac = i / 10
                rr = int(field_r * (1.02 + 0.045 * frac))
                alpha = int(ha * 0.10 * frac)
                if self.speaking:
                    ox = 0
                    oy = 0
                else:
                    ox = int(3 * math.sin(t * 0.010 + i))
                    oy = int(3 * math.cos(t * 0.009 + i * 1.3))
                c.create_oval(
                    FCX-rr+ox, FCY-rr+oy, FCX+rr+ox, FCY+rr+oy,
                    outline=self._ac(R, G, B, alpha),
                    width=3,
                )

        # Structural circles — kamera açıkken gizle (webcam zaten üstünü kapatır)
        if not cam:
            for frac, width, alpha_mult in (
                (1.00, 2, 0.34),
                (0.90, 2, 0.24),
                (0.76, 1, 0.18),
                (0.62, 1, 0.12),
            ):
                rr = int(field_r * frac)
                c.create_oval(
                    FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                    outline=self._ac(R, G, B, int(ha * alpha_mult * (0.4 if self.paused else 1.0))),
                    width=width,
                )

        speak_shell_push = 1.16 if self.speaking else 1.07 if self.user_speaking else 1.0
        # Orb shell particles
        shell_r = field_r * 0.93 * speak_shell_push
        for idx, sp in enumerate(self.orb_shell_particles):
            angle = sp['angle'] + t * sp['speed'] * (2.8 if self.speaking else 1.6 if self.user_speaking else 1.1)
            wobble = 1.0 + (0.07 if self.speaking else 0.035) * math.sin(t * 0.08 + sp['phase'])
            x = FCX + math.cos(angle) * shell_r * wobble
            y = FCY + math.sin(angle) * shell_r * wobble
            alpha = int((70 + 120 * sp['glow']) * (0.26 if self.paused else 0.52 + activity * 0.45))
            if idx % 9 == 0 and not self.paused:
                col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], min(255, alpha + 30))
            else:
                col = self._ac(R, G, B, alpha)
            pr = sp['size'] * (1.0 + 0.24 * math.sin(t * 0.05 + sp['phase']))
            c.create_oval(x-pr, y-pr, x+pr, y+pr, fill=col, outline="")

        # Rotating segmented arcs — kamera açıkken gizle
        if not cam:
            arc_r1 = int(field_r * 0.96)
            arc_r2 = int(field_r * 0.78)
            for start, extent, width, accent in (
                (self.rings_spin[0], 52 if self.speaking else 34, 3, False),
                ((self.rings_spin[0] + 148) % 360, 26, 2, True),
                ((self.rings_spin[2] + 28) % 360, 64 if self.user_speaking else 40, 3, False),
                ((self.rings_spin[2] + 212) % 360, 18, 2, True),
            ):
                rr = arc_r1 if width == 3 else arc_r2
                if accent and not self.paused:
                    col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], int(120 + 80 * activity))
                else:
                    col = self._ac(R, G, B, int(ha * (1.2 if width == 3 else 0.7)))
                c.create_arc(
                    FCX-rr, FCY-rr, FCX+rr, FCY+rr,
                    start=start, extent=extent,
                    outline=col, width=width, style="arc",
                )

        # Particle orb field
        field_limit = inner_r * (
            0.82 if self.paused else
            1.36 if self.speaking else
            1.16 if self.user_speaking else
            1.0
        )
        for idx, p in enumerate(self.orb_particles):
            speed_mult = (
                0.10 if self.paused else
                3.10 if self.speaking else
                2.00 if self.user_speaking else
                1.10
            )
            angle = p['angle'] + t * p['speed'] * speed_mult
            wobble = 1.0 + (0.30 if self.speaking else 0.18) * math.sin(t * p['wobble'] + p['phase'])
            orbit = field_limit * p['orbit'] * wobble
            depth = 0.5 + 0.5 * math.sin(angle * 2.0 + t * 0.013 + p['phase'])
            y_squash = 0.62 + depth * 0.38
            drift = (8.0 if self.speaking else 5.0 if self.user_speaking else 4.0) * p['depth']
            x = FCX + math.cos(angle) * orbit + math.sin(t * 0.011 + p['phase']) * drift
            y = FCY + math.sin(angle) * orbit * y_squash + math.cos(t * 0.010 + p['phase']) * drift
            base_alpha = int((18 + 155 * p['depth']) * (0.24 + activity * 0.86) * (0.45 + depth * 0.75))
            if self.paused:
                base_alpha = int(base_alpha * 0.40)
            if idx % 11 == 0 and not self.paused:
                col = self._ac(accent_rgb[0], accent_rgb[1], accent_rgb[2], min(255, base_alpha + 25))
            elif self.user_speaking and idx % 7 == 0:
                col = self._ac(*_hex_to_rgb_tuple(C_BLUE), min(255, base_alpha + 20))
            else:
                col = self._ac(R, G, B, base_alpha)
            pr = p['size'] * (0.70 if self.paused else 0.90 + depth * 0.65 + 0.30 * activity * p['depth'])
            c.create_oval(x-pr, y-pr, x+pr, y+pr, fill=col, outline="")
            if idx % 18 == 0 and not self.paused:
                c.create_line(
                    FCX + (x-FCX) * 0.18,
                    FCY + (y-FCY) * 0.18,
                    x, y,
                    fill=self._ac(R, G, B, int(18 + 35 * p['depth'] * activity)),
                    width=1,
                )

        # Center void keeps the orb airy instead of lens-like.
        void_r = int(inner_r * (0.18 if self.paused else 0.12))
        if void_r > 0:
            c.create_oval(
                FCX-void_r, FCY-void_r, FCX+void_r, FCY+void_r,
                fill=C_BG,
                outline="",
            )

    def _draw_orb_anka(self, c, cam: bool = False):
        """
        Logodan esinlenilmiş ALTERNATİF animasyon (klasik parçacık kürenin
        YERİNE değil, YANINDA bir seçenek — AYARLAR > Tema > 'Konuşma
        animasyonu stili' ile seçilir). Merkezde nabız gibi atan bir elmas/
        taş, yukarı-dışa açılan iki kanat (konuşurken çırpınır), aşağı uzanan
        iki alev yaprağı (konuşurken titrer) ve ince bir orta gövde.
        """
        state = "PAUSED" if self.paused else self._yerinde_state
        t = self.tick
        if self.speaking:
            speak_pulse = 1.0 + 0.14 * math.sin(t * 0.23) + 0.06 * math.sin(t * 0.11 + 1.2)
        elif self.user_speaking:
            speak_pulse = 1.0 + 0.07 * math.sin(t * 0.18 + 0.7)
        elif state in ("THINKING", "INITIALISING"):
            speak_pulse = 1.0 + 0.04 * math.sin(t * 0.10)
        else:
            speak_pulse = 1.0 + 0.015 * math.sin(t * 0.07)

        move_x = move_y = 0
        if self.user_speaking:
            move_x = int(6 * math.sin(t * 0.06))
            move_y = int(4 * math.cos(t * 0.09 + 0.5))
        elif state in ("THINKING", "INITIALISING"):
            move_x = int(3 * math.sin(t * 0.045))
            move_y = int(2 * math.cos(t * 0.05 + 0.4))

        FCX = self.FCX + move_x
        FCY = self.FCY + move_y + int(self._cam_orb_shift)
        base_face = (int(self._cam_orb_face) if self._cam_orb_face > 1.0 else self.FACE)
        FW = int(base_face * self.scale * speak_pulse)
        R, G, B = self._orb_rgb()
        ha = self.halo_a
        activity = (
            0.10 if self.paused else
            1.00 if self.speaking else
            0.78 if self.user_speaking else
            0.62 if state in ("THINKING", "INITIALISING") else
            0.30
        )

        # Durum halkası — klasik stildeki 'canlılık' göstergesiyle tutarlı
        if not self.paused:
            for i in range(6, 0, -1):
                frac = i / 6
                rr = int(FW * 0.30 * (1.05 + 0.05 * frac))
                alpha = int(ha * 0.14 * frac * activity)
                c.create_oval(FCX - rr, FCY - rr, FCX + rr, FCY + rr,
                             outline=self._ac(R, G, B, alpha), width=2)

        gem_r = FW * 0.15 * (1.0 if not self.paused else 0.85)

        # ── Kanatlar (yukarı-dışa, konuşurken çırpınır) ─────────────────────
        # Logodan ÖLÇÜLEN oran: kanat ucu, elmas merkezinden yataya göre
        # ~28.6° açıyla (dik değil, sığ bir süpürüşle) dışarı uzanıyor.
        wing_len = FW * 0.62
        flap_speed = 0.20 if self.speaking else 0.10 if self.user_speaking else 0.035
        flap_amt = (11 if self.speaking else 6 if self.user_speaking else 2)
        flap = flap_amt * math.sin(t * flap_speed)
        for side in (-1, 1):
            base_in = (FCX + side * gem_r * 0.25, FCY - gem_r * 0.55)
            base_out = (FCX + side * gem_r * 0.95, FCY - gem_r * 0.25)
            shoulder = (FCX + side * wing_len * 0.56, FCY - wing_len * 0.34)
            tip = (FCX + side * (wing_len + flap), FCY - wing_len * 0.55 - abs(flap) * 0.25)
            c.create_polygon(base_in, shoulder, tip, base_out, fill=C_MID, outline="")
            inner_shoulder = (FCX + side * wing_len * 0.34, FCY - wing_len * 0.20)
            inner_tip = (FCX + side * wing_len * 0.60, FCY - wing_len * 0.34)
            inner_base = (FCX + side * gem_r * 0.5, FCY - gem_r * 0.15)
            c.create_polygon(base_in, inner_shoulder, inner_tip, inner_base, fill=C_PRI, outline="")

        # ── Alev yaprakları (aşağı, konuşurken BELİRGİN şekilde titrer) ─────
        # Her iki alev BAĞIMSIZ titrer (gerçek alevler gibi asimetrik) —
        # konuşurken çok daha canlı, boşta sakin bir görünüm için.
        flame_len = FW * 0.46
        flame_amp = 0.22 if self.speaking else 0.07 if self.user_speaking else 0.03
        flame_amp2 = 0.13 if self.speaking else 0.04 if self.user_speaking else 0.015
        for side, col, ph in zip((-1, 1), (C_RED, C_ORG), (0.0, 2.1)):
            flicker = (flame_amp * math.sin(t * 0.42 + ph)
                      + flame_amp2 * math.sin(t * 0.83 + ph * 1.6 + 0.6))
            fl = flame_len * (1.0 + flicker)
            width_pulse = 1.0 + (0.18 if self.speaking else 0.05) * math.sin(t * 0.5 + ph + 1.0)
            base1 = (FCX + side * gem_r * 0.20 * width_pulse, FCY + gem_r * 0.85)
            base2 = (FCX + side * gem_r * 0.75 * width_pulse, FCY + gem_r * 0.55)
            tip = (FCX + side * gem_r * 0.42, FCY + gem_r * 0.55 + fl)
            c.create_polygon(base1, tip, base2, fill=col, outline="")
        stem_flicker = 0.08 * math.sin(t * 0.6) if self.speaking else 0.0
        stem_len = flame_len * (1.0 + stem_flicker) * 1.08
        c.create_line(FCX, FCY + gem_r * 0.6, FCX, FCY + gem_r * 0.6 + stem_len,
                     fill=C_GOLD, width=max(2, int(FW * 0.012)))

        # ── Merkez elmas/taş ─────────────────────────────────────────────────
        if not cam:
            pts = [(FCX, FCY - gem_r), (FCX + gem_r * 0.86, FCY),
                   (FCX, FCY + gem_r), (FCX - gem_r * 0.86, FCY)]
            c.create_polygon(pts, fill=C_PRI, outline=C_TEXT, width=1)
            shimmer = 0.85 + 0.15 * math.sin(t * (0.12 if self.speaking else 0.06))
            hi_r = gem_r * 0.42 * shimmer
            hi_cx, hi_cy = FCX - gem_r * 0.16, FCY - gem_r * 0.18
            hi_pts = [(hi_cx, hi_cy - hi_r), (hi_cx + hi_r * 0.86, hi_cy),
                     (hi_cx, hi_cy + hi_r), (hi_cx - hi_r * 0.86, hi_cy)]
            c.create_polygon(hi_pts, fill=C_TEXT, outline="")

    def _draw_orb_destek(self, c, cam: bool = False):
        """
        'Destek Ekosistemi' logosundan esinlenilmiş ALTERNATİF animasyon —
        klasik kürenin YERİNE değil YANINDA bir seçenek (AYARLAR > Tema >
        'Konuşma animasyonu stili' → 'Destek'). Merkezde yukarı açılan sıcak
        bir ışık huzmesi (elini uzatan/aydınlanan insan figürünü çağrıştırır),
        çevresinde yavaşça dönen bir yaprak/sarmaşık halkası (turuncu +
        adaçayı yeşili) — konuşurken halka nefes alır gibi büyüyüp küçülür.
        """
        state = "PAUSED" if self.paused else self._yerinde_state
        t = self.tick
        if self.speaking:
            speak_pulse = 1.0 + 0.14 * math.sin(t * 0.23) + 0.06 * math.sin(t * 0.11 + 1.2)
        elif self.user_speaking:
            speak_pulse = 1.0 + 0.07 * math.sin(t * 0.18 + 0.7)
        elif state in ("THINKING", "INITIALISING"):
            speak_pulse = 1.0 + 0.04 * math.sin(t * 0.10)
        else:
            speak_pulse = 1.0 + 0.015 * math.sin(t * 0.07)

        move_x = move_y = 0
        if self.user_speaking:
            move_x = int(6 * math.sin(t * 0.06))
            move_y = int(4 * math.cos(t * 0.09 + 0.5))
        elif state in ("THINKING", "INITIALISING"):
            move_x = int(3 * math.sin(t * 0.045))
            move_y = int(2 * math.cos(t * 0.05 + 0.4))

        FCX = self.FCX + move_x
        FCY = self.FCY + move_y + int(self._cam_orb_shift)
        base_face = (int(self._cam_orb_face) if self._cam_orb_face > 1.0 else self.FACE)
        FW = int(base_face * self.scale * speak_pulse)
        R, G, B = self._orb_rgb()
        ha = self.halo_a
        activity = (
            0.10 if self.paused else
            1.00 if self.speaking else
            0.78 if self.user_speaking else
            0.62 if state in ("THINKING", "INITIALISING") else
            0.30
        )

        ring_r = FW * 0.46

        # ── Sarmaşık halkası: iki iç içe ince çember (logodaki dönen
        #    yaprak/asma motifi) — konuşurken yavaşça döner ────────────────
        spin = t * (0.012 if self.speaking else 0.004)
        for off, col in ((0.0, C_GREEN), (0.35, C_ORG)):
            rr = ring_r * (1.0 + 0.05 * math.sin(t * 0.05 + off * 6))
            c.create_oval(FCX - rr, FCY - rr * 0.94, FCX + rr, FCY + rr * 0.94,
                         outline=col, width=2)

        # ── Yapraklar: halka boyunca eşit aralıklı, konuşurken nefes alır
        #    gibi büyüyüp küçülen küçük yaprak/damla şekiller ─────────────
        n_leaves = 10
        leaf_pulse = 1.0 + (0.22 if self.speaking else 0.08 if self.user_speaking
                            else 0.03) * math.sin(t * 0.14)
        for i in range(n_leaves):
            ang = spin + (2 * math.pi * i / n_leaves)
            nx, ny = math.cos(ang), math.sin(ang) * 0.94
            lx, ly = FCX + ring_r * nx, FCY + ring_r * ny
            leaf_len = FW * 0.13 * leaf_pulse * (1.0 + 0.08 * math.sin(t * 0.2 + i))
            tx, ty = -ny, nx   # teğet yön — yaprağın genişliği için
            tip = (lx + nx * leaf_len, ly + ny * leaf_len)
            base_l = (lx + tx * leaf_len * 0.32, ly + ty * leaf_len * 0.32)
            base_r = (lx - tx * leaf_len * 0.32, ly - ty * leaf_len * 0.32)
            col = C_ORG if i % 2 == 0 else C_GREEN
            c.create_polygon(tip, base_l, base_r, fill=col, outline="")

        # ── Durum halkası (canlılık göstergesi, diğer stillerle tutarlı) ──
        if not self.paused:
            for i in range(6, 0, -1):
                frac = i / 6
                rr = int(FW * 0.30 * (1.05 + 0.05 * frac))
                alpha = int(ha * 0.12 * frac * activity)
                c.create_oval(FCX - rr, FCY - rr, FCX + rr, FCY + rr,
                             outline=self._ac(R, G, B, alpha), width=2)

        # ── Merkez: yukarı açılan sıcak ışık huzmesi (elini uzatan/
        #    aydınlanan insan figürünü çağrıştırır) ───────────────────────
        if not cam:
            glow_r = FW * 0.17 * (1.0 if not self.paused else 0.85)
            body_h = glow_r * 1.9
            shimmer = 0.85 + 0.15 * math.sin(t * (0.12 if self.speaking else 0.06))
            c.create_polygon(
                (FCX - glow_r * 0.34, FCY + body_h * 0.55),
                (FCX + glow_r * 0.34, FCY + body_h * 0.55),
                (FCX + glow_r * 0.14, FCY - body_h * 0.45),
                (FCX - glow_r * 0.14, FCY - body_h * 0.45),
                fill=C_PRI, outline="")
            head_r = glow_r * (0.62 * shimmer)
            c.create_oval(FCX - head_r, FCY - body_h * 0.55 - head_r * 2,
                         FCX + head_r, FCY - body_h * 0.55,
                         fill=C_TEXT, outline="")

    def _draw_orb_anka_baloncuk(self, c, cam: bool = False):
        """
        ÜÇÜNCÜ konuşma animasyonu — istek üzerine iki tasarımın birleşimi:
        Anka'nın tanınabilir Y-silüeti (kanat + gövde iskeleti), Klasik'in
        yüzen parçacık/baloncuk estetiğiyle çizilir. Katı çokgen YOK — her
        şey, iskelet çizgileri boyunca dizilmiş, hafifçe süzülen küçük
        baloncuklardan oluşuyor.
        """
        state = "PAUSED" if self.paused else self._yerinde_state
        t = self.tick
        if self.speaking:
            speak_pulse = 1.0 + 0.14 * math.sin(t * 0.23) + 0.06 * math.sin(t * 0.11 + 1.2)
        elif self.user_speaking:
            speak_pulse = 1.0 + 0.07 * math.sin(t * 0.18 + 0.7)
        elif state in ("THINKING", "INITIALISING"):
            speak_pulse = 1.0 + 0.04 * math.sin(t * 0.10)
        else:
            speak_pulse = 1.0 + 0.015 * math.sin(t * 0.07)

        move_x = move_y = 0
        if self.user_speaking:
            move_x = int(6 * math.sin(t * 0.06))
            move_y = int(4 * math.cos(t * 0.09 + 0.5))
        elif state in ("THINKING", "INITIALISING"):
            move_x = int(3 * math.sin(t * 0.045))
            move_y = int(2 * math.cos(t * 0.05 + 0.4))

        FCX = self.FCX + move_x
        FCY = self.FCY + move_y + int(self._cam_orb_shift)
        base_face = (int(self._cam_orb_face) if self._cam_orb_face > 1.0 else self.FACE)
        FW = int(base_face * self.scale * speak_pulse)
        activity = (
            0.10 if self.paused else
            1.00 if self.speaking else
            0.78 if self.user_speaking else
            0.62 if state in ("THINKING", "INITIALISING") else
            0.30
        )

        gem_r = FW * 0.15 * (1.0 if not self.paused else 0.85)
        wing_len = FW * 0.62
        stem_len = FW * 0.50
        WING_SLOPE = 0.546  # logodan ölçülen ~28.6° kanat açısı (tan)

        def lerp(p0, p1, frac):
            return (p0[0] + (p1[0] - p0[0]) * frac, p0[1] + (p1[1] - p0[1]) * frac)

        # (başlangıç, bitiş, renk, kalınlık_baz) — iskelet çizgileri
        paths = []
        for side in (-1, 1):
            paths.append(((FCX + side * gem_r * 0.3, FCY - gem_r * 0.5),
                          (FCX + side * wing_len, FCY - wing_len * WING_SLOPE),
                          C_MID, 1.0))
            paths.append(((FCX + side * gem_r * 0.2, FCY - gem_r * 0.3),
                          (FCX + side * wing_len * 0.55, FCY - wing_len * 0.55 * WING_SLOPE),
                          C_PRI, 0.75))
        paths.append(((FCX, FCY + gem_r * 0.6), (FCX, FCY + gem_r * 0.6 + stem_len),
                      C_GOLD, 0.9))
        paths.append(((FCX - gem_r * 0.5, FCY + gem_r * 0.6),
                      (FCX - gem_r * 0.35, FCY + stem_len * 0.85), C_RED, 0.8))
        paths.append(((FCX + gem_r * 0.5, FCY + gem_r * 0.6),
                      (FCX + gem_r * 0.35, FCY + stem_len * 0.85), C_ORG, 0.8))

        n_per_path = 12
        for p_idx, (p0, p1, col, thick) in enumerate(paths):
            R, G, B = self._hex_rgb(col)
            for i in range(n_per_path):
                frac = i / max(1, n_per_path - 1)
                bx, by = lerp(p0, p1, frac)
                phase = p_idx * 1.7 + i * 0.9
                jitter = 5 + 9 * activity
                jx = jitter * math.sin(t * (0.05 + 0.03 * activity) + phase)
                jy = jitter * 0.6 * math.cos(t * (0.045 + 0.025 * activity) + phase * 1.3)
                pulse = 0.55 + 0.45 * math.sin(t * (0.08 + 0.10 * activity) + phase * 0.7)
                r = max(1.6, (FW * 0.013 * thick) * (0.6 + 0.5 * pulse))
                alpha = min(255, int(120 + 110 * pulse * activity + 40))
                fill = self._ac(R, G, B, alpha)
                c.create_oval(bx + jx - r, by + jy - r, bx + jx + r, by + jy + r,
                             fill=fill, outline="")

        if not cam:
            Rg, Gg, Bg = self._hex_rgb(C_PRI)
            core_n = 16
            for i in range(core_n):
                ang = (2 * math.pi / core_n) * i + t * 0.02
                rr = gem_r * (0.28 + 0.30 * math.sin(t * 0.1 + i))
                bx = FCX + rr * math.cos(ang)
                by = FCY + rr * math.sin(ang)
                r = max(1.8, gem_r * 0.13)
                c.create_oval(bx - r, by - r, bx + r, by + r,
                             fill=self._ac(Rg, Gg, Bg, 230), outline="")

    # ── Ana çizim ─────────────────────────────────────────────────────────────
    def _draw(self):
        c  = self.bg
        W  = self.W
        H  = self.H
        t  = self.tick
        c.delete("all")

        # ── Özel arkaplan resmi (varsa) — her şeyin en altına çizilir ─────────
        if getattr(self, "_bg_photo", None) is not None:
            c.create_image(0, 0, anchor="nw", image=self._bg_photo)

        # ── Arka plan ────────────────────────────────────────────────────────
        # Nokta ızgarası — 3 karede bir çiz, geniş adım → düşük yük
        if t % 3 == 0:
            step = 72
            for x in range(0, W, step):
                for y in range(0, H, step):
                    c.create_rectangle(x, y, x+1, y+1, fill=C_DIMMER, outline="")

        # Tarama çizgisi (yavaş, çok soluk)
        scan_y = (t * 0.7) % (H + 60) - 30
        for i in range(2):
            ly = (scan_y + i * 20) % H
            c.create_line(0, ly, W, ly+35, fill=C_DIMMER, width=1)

        # Partiküller
        R, G, B = self._orb_rgb()
        for p in self.particles:
            if self.speaking:
                col = self._ac(*_hex_to_rgb_tuple(C_GOLD), p['a'])
            else:
                col = self._ac(R, G, B, p['a'])
            r = p['r']
            c.create_oval(p['x']-r, p['y']-r, p['x']+r, p['y']+r,
                          fill=col, outline="")

        # ── Bölücü çizgiler (ince, soluk) ────────────────────────────────────
        c.create_line(self.LEFT_W, HDR_H, self.LEFT_W, H-FOOTER_H,
                      fill=C_DIM, width=1)
        c.create_line(W-self.RIGHT_W, HDR_H, W-self.RIGHT_W, H-FOOTER_H,
                      fill=C_DIM, width=1)

        # ── Yan paneller ──────────────────────────────────────────────────────
        self._draw_left_panel(c)
        self._draw_right_panel(c)

        # ── Orb — kamera açıkken aşağı kayar, sert halkalar gizlenir ─────────
        self._draw_orb(c, cam=self._webcam_active)

        state_label = "PAUSED" if self.paused else self._yerinde_state
        state_col = self._state_color(state_label)
        c.create_text(self.FCX, self.CTRL_Y - 34, text=SYSTEM_NAME,
                      fill=C_TEXT, font=font_display(18))
        c.create_text(self.FCX, self.CTRL_Y - 12, text=f"● {self._state_label_tr(state_label)}",
                      fill=state_col, font=font_body_bold(11))

        # ── HEADER ───────────────────────────────────────────────────────────
        c.create_rectangle(0, 0, W, HDR_H, fill=C_DIMMER, outline="")
        # Alt çizgi — teal parlak
        c.create_line(0, HDR_H, W, HDR_H, fill=C_MID, width=1)
        for i in range(3):
            a = 60 - i * 18
            c.create_line(0, HDR_H-1-i, W, HDR_H-1-i,
                          fill=self._ac(*_hex_to_rgb_tuple(C_PRI), a), width=1)

        # Büyük başlık
        c.create_text(W//2, 24, text=SYSTEM_NAME,
                      fill=C_PRI, font=font_display(26))
        c.create_text(W//2, 52, text="Akıllı Türkçe Sesli Asistan Sistemi",
                      fill=C_MID, font=font_body(11))

        # Sol: model badge
        c.create_text(22, 36, text=MODEL_BADGE,
                      fill=C_DIM, font=font_body(10), anchor="w")

        # Sağ: durum indikatörü
        indicator_state = "PAUSED" if self.paused else self._yerinde_state
        ind_col = self._state_color(indicator_state)
        indicator_text = self._state_badge_text(indicator_state)
        sym = "●" if self.status_blink else "○"
        c.create_text(W-22, 28, text=f"{sym}  {indicator_text}",
                      fill=ind_col, font=font_body_bold(11), anchor="e")

        # Webcam canlı yayın göstergesi
        if self._webcam_active:
            cam_blink = "●" if self.status_blink else "◉"
            c.create_text(W-22, 52, text=f"{cam_blink}  KAMERA CANLI",
                          fill=C_RED, font=font_body_bold(9), anchor="e")

        # ── FOOTER ───────────────────────────────────────────────────────────
        c.create_rectangle(0, H-FOOTER_H, W, H, fill=C_DIMMER, outline="")
        c.create_line(0, H-FOOTER_H, W, H-FOOTER_H, fill=C_DIM, width=1)
        c.create_text(W//2, H-13, fill=C_DIM, font=font_body(9),
                      text=f"YERINDE · {PLATFORM_NAME} Sürümü · Gerçek Zamanlı Ses Çekirdeği")
        c.create_text(W-18, H-13, fill=C_DIM, font=font_body(9),
                      text="[F4] SESSİZ  [F5] DURAKLAT  [F6] KAMERA  [F11] TAM EKRAN  [ESC] ÇIKIŞ/PENCERE", anchor="e")

    def wait_for_api_key(self):
        while not self._api_key_ready:
            time.sleep(0.1)

    def _show_setup_ui(self, edit_mode: bool = False):
        self._close_setup_ui()

        self.setup_frame = tk.Frame(self.root, bg=C_BG,
                                    highlightbackground=C_PRI,
                                    highlightthickness=1)
        self.setup_frame.place(relx=0.5, rely=0.5, anchor="center")

        title = "◈ API AYARLARI" if edit_mode else "◈ İLK KURULUM GEREKLİ"
        subtitle = (
            "Gemini API anahtarinizi guncelleyin."
            if edit_mode else
            "Gemini API anahtarinizi girin."
        )
        config = load_app_config()

        tk.Label(self.setup_frame, text=title,
                 fg=C_PRI, bg=C_BG, font=font_display(16)).pack(pady=(18, 4))
        tk.Label(self.setup_frame, text=subtitle,
                 fg=C_MID, bg=C_BG, font=font_body(11)).pack(pady=(0, 10))
        tk.Label(self.setup_frame, text="GEMINI API ANAHTARI",
                 fg=C_DIM, bg=C_BG, font=font_body(11)).pack(pady=(8, 2))

        self.api_entry = tk.Entry(
            self.setup_frame, width=52,
            fg=C_TEXT, bg=C_DIMMER, insertbackground=C_TEXT,
            borderwidth=0, font=font_body(12), show="*")
        self.api_entry.pack(pady=(0, 6))

        current_key = str(config.get("gemini_api_key", "") or "")
        if current_key:
            self.api_entry.insert(0, current_key)

        buttons = tk.Frame(self.setup_frame, bg=C_BG)
        buttons.pack(pady=14)

        tk.Button(buttons, text="▸ KAYDET",
                  command=self._save_api_key, bg=C_BG, fg=C_PRI,
                  activebackground=C_DIM, font=font_body_bold(12),
                  borderwidth=0, padx=18, pady=8).pack(side="left", padx=6)

        if edit_mode:
            tk.Button(buttons, text="KAPAT",
                      command=self._close_setup_ui, bg=C_BG, fg=C_DIM,
                      activebackground=C_DIMMER, font=font_body_bold(12),
                      borderwidth=0, padx=18, pady=8).pack(side="left", padx=6)

    def _save_api_key(self):
        was_ready = self._api_key_ready
        key = self.api_entry.get().strip() if self.api_entry else ""
        if not key:
            return
        youtube_key = self.youtube_api_entry.get().strip() if self.youtube_api_entry else ""
        youtube_handle = self.youtube_handle_entry.get().strip() if self.youtube_handle_entry else ""
        save_app_config(
            {
                "gemini_api_key": key,
                "youtube_api_key": youtube_key,
                "youtube_channel_handle": youtube_handle,
                # DİKKAT: yapılandırmaya Gemini ses KİMLİĞİ yazılır (Kore/Charon...),
                # Türkçe etiket değil — aksi halde API "böyle ses yok" hatası verir.
                "voice": VOICE_ID_BY_LABEL.get(self._current_voice, "Charon"),
            }
        )
        self._close_setup_ui()
        self._api_key_ready = True
        self._refresh_settings_status()
        if was_ready:
            self.write_log("SYS: API ayarlari guncellendi.")
        else:
            self.set_state("LISTENING")
            self.write_log("SYS: YERINDE hazır. Dinliyorum...")
