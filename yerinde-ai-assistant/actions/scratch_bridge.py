"""
actions/scratch_bridge.py — Scratch'i sesle programlama.

Scratch'in (Blender'ın soket köprüsü gibi) dışarıdan komut alan bir arayüzü
YOKTUR. Ama Scratch proje dosyası (.sb3) açık bir biçimdir: içinde project.json
bulunan bir zip. Bu yüzden yaklaşımımız:

    Sesli komut  →  .sb3 projesi ÜRET/GÜNCELLE  →  Scratch'te AÇ

ÖNEMLİ DÜZELTME (önceki sürüm): Eskiden HER komutta saat damgalı YENİ bir
dosya oluşuyordu — artık TEK SABİT dosya (yerinde_proje.sb3) kullanılıyor.

BU SÜRÜMDE EKLENEN (kukla/kostüm/yorum/analiz):
  Kukla   : kukla ekle (basit çizilmiş şekil), kukla sil, kuklalar arasında
            geç — komutlar her zaman AKTİF kuklaya uygulanır.
  Çizim   : "kukla çiz: kırmızı yıldız" gibi — gerçek SVG üretilip kuklanın
            kostümü yapılır (daire/kare/üçgen/yıldız, herhangi bir renk).
  Kostüm  : mevcut kuklaya EK bir kostüm ekler (animasyon için).
  Yorum   : son eklenen bloğa sarı yapışkan not (yorum) ekler.
  Analiz  : var olan bir .sb3 dosyasını (varsayılan: kendi projemiz) açıp
            KOPUK REFERANSLARI ve ERİŞİLEMEZ BLOKLARI bulur, basit
            olanları OTOMATİK DÜZELTİR, bir özet rapor döner. Kendi
            ürettiğimiz dosyalar dışında, kullanıcının BAŞKA BİR YERDEN
            aldığı .sb3 dosyaları için de çalışır (yol verilirse).

DAHA AYRINTILI KONTROL (önceki sürümden): Hareket, Görünüm, Kontrol
(TEKRARLA/SONSUZA KADAR/EĞER), Kalem, Değişken blokları.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import random
import string
import subprocess
import zipfile
from pathlib import Path

from actions.mouse_control import (_is_wayland, _ydotool_move_absolute,
                                   _ydotool_click, _BTN_LEFT)

_IS_WINDOWS = platform.system() == "Windows"

PROJECT_FILENAME = "yerinde_proje.sb3"   # SABİT ad — saat damgası YOK

# ══ Çoklu kukla durumu ═══════════════════════════════════════════════════════
_DEFAULT_CAT_COSTUME = {"name": "kostüm1", "dataFormat": "svg",
                        "assetId": "bcf454acf82e4504149f7ffe07081dbc",
                        "md5ext": "bcf454acf82e4504149f7ffe07081dbc.svg",
                        "rotationCenterX": 48, "rotationCenterY": 50}


def _default_sprite_state() -> dict:
    return {"script": [], "container_stack": [], "costumes": [dict(_DEFAULT_CAT_COSTUME)],
            "assets": {}, "comments": [], "variables": {}}


_SPRITES: dict[str, dict] = {"Kedi": _default_sprite_state()}
_CURRENT_SPRITE = "Kedi"
_SCRATCH_LAUNCHED = False   # psutil yoksa (nadir) bu bayrağa düşülür

_PEN_COLORS = {
    "kırmızı": "#FF0000", "kirmizi": "#FF0000", "mavi": "#0000FF",
    "yeşil": "#00FF00", "yesil": "#00FF00", "sarı": "#FFFF00", "sari": "#FFFF00",
    "turuncu": "#FF8000", "mor": "#8000FF", "pembe": "#FF00C0",
    "siyah": "#000000", "beyaz": "#FFFFFF", "kahverengi": "#804000",
}


def _uid() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=20))


def _cur() -> dict:
    """Aktif kuklanın durum sözlüğü."""
    return _SPRITES.setdefault(_CURRENT_SPRITE, _default_sprite_state())


def _num(v) -> list:
    return [1, [4, str(v)]]


def _txt(v) -> list:
    return [1, [10, str(v)]]


# ── Blok üreticileri: DÜZ (basit) bloklar ────────────────────────────────────
def _block_move(steps: float) -> dict:
    return {"opcode": "motion_movesteps", "inputs": {"STEPS": _num(steps)}, "fields": {}}


def _block_turn(degrees: float, right: bool = True) -> dict:
    return {"opcode": "motion_turnright" if right else "motion_turnleft",
            "inputs": {"DEGREES": _num(abs(degrees))}, "fields": {}}


def _block_goto(x: float, y: float) -> dict:
    return {"opcode": "motion_gotoxy", "inputs": {"X": _num(x), "Y": _num(y)}, "fields": {}}


def _block_point_direction(degrees: float) -> dict:
    return {"opcode": "motion_pointindirection",
            "inputs": {"DIRECTION": _num(degrees)}, "fields": {}}


def _block_glide(x: float, y: float, secs: float = 1) -> dict:
    return {"opcode": "motion_glidesecstoxy",
            "inputs": {"SECS": _num(secs), "X": _num(x), "Y": _num(y)}, "fields": {}}


def _block_say(text: str, seconds: float | None = None) -> dict:
    if seconds is None:
        return {"opcode": "looks_say", "inputs": {"MESSAGE": _txt(text)}, "fields": {}}
    return {"opcode": "looks_sayforsecs",
            "inputs": {"MESSAGE": _txt(text), "SECS": _num(seconds)}, "fields": {}}


def _block_think(text: str, seconds: float | None = None) -> dict:
    if seconds is None:
        return {"opcode": "looks_think", "inputs": {"MESSAGE": _txt(text)}, "fields": {}}
    return {"opcode": "looks_thinkforsecs",
            "inputs": {"MESSAGE": _txt(text), "SECS": _num(seconds)}, "fields": {}}


def _block_show() -> dict:
    return {"opcode": "looks_show", "inputs": {}, "fields": {}}


def _block_hide() -> dict:
    return {"opcode": "looks_hide", "inputs": {}, "fields": {}}


def _block_size(percent: float) -> dict:
    return {"opcode": "looks_setsizeto", "inputs": {"SIZE": _num(percent)}, "fields": {}}


def _block_change_size(delta: float) -> dict:
    return {"opcode": "looks_changesizeby", "inputs": {"CHANGE": _num(delta)}, "fields": {}}


def _block_next_costume() -> dict:
    return {"opcode": "looks_nextcostume", "inputs": {}, "fields": {}}


def _block_wait(seconds: float) -> dict:
    return {"opcode": "control_wait", "inputs": {"DURATION": _num(seconds)}, "fields": {}}


def _block_stop_all() -> dict:
    return {"opcode": "control_stop", "inputs": {}, "fields": {"STOP_OPTION": ["all", None]}}


# ── Kalem (Pen uzantısı) ─────────────────────────────────────────────────────
def _block_pen_down() -> dict:
    return {"opcode": "pen_penDown", "inputs": {}, "fields": {}}


def _block_pen_up() -> dict:
    return {"opcode": "pen_penUp", "inputs": {}, "fields": {}}


def _block_pen_clear() -> dict:
    return {"opcode": "pen_clear", "inputs": {}, "fields": {}}


def _block_pen_stamp() -> dict:
    return {"opcode": "pen_stamp", "inputs": {}, "fields": {}}


def _block_pen_color(color_name: str) -> dict:
    hexval = _PEN_COLORS.get((color_name or "").lower().strip(), "#0000FF")
    return {"opcode": "pen_setPenColorToColor", "inputs": {"COLOR": ("__colour_shadow__", hexval)},
            "fields": {}}


# ── Değişken ─────────────────────────────────────────────────────────────────
def _block_set_variable(name: str, value) -> dict:
    return {"opcode": "data_setvariableto",
            "inputs": {"VALUE": _txt(value)},
            "fields": {"VARIABLE": (None, name)}, "__needs_var__": name}


def _block_change_variable(name: str, delta: float) -> dict:
    return {"opcode": "data_changevariableby",
            "inputs": {"VALUE": _num(delta)},
            "fields": {"VARIABLE": (None, name)}, "__needs_var__": name}


# ── C-blokları ────────────────────────────────────────────────────────────
def _block_repeat(times: int, body: list[dict]) -> dict:
    return {"opcode": "control_repeat", "inputs": {"TIMES": _num(int(times))},
            "fields": {}, "substack": body}


def _block_forever(body: list[dict]) -> dict:
    return {"opcode": "control_forever", "inputs": {}, "fields": {}, "substack": body}


def _block_if_touching_edge(body: list[dict]) -> dict:
    return {"opcode": "control_if", "inputs": {}, "fields": {}, "substack": body,
            "__condition__": ("sensing_touchingobject", "sensing_touchingobjectmenu",
                              "TOUCHINGOBJECTMENU", "_edge_")}


def _block_if_key_pressed(key: str, body: list[dict]) -> dict:
    return {"opcode": "control_if", "inputs": {}, "fields": {}, "substack": body,
            "__condition__": ("sensing_keypressed", "sensing_keyoptions",
                              "KEY_OPTION", key or "space")}


BUILDERS = {
    "move": _block_move,
    "turn_right": lambda d: _block_turn(d, True),
    "turn_left": lambda d: _block_turn(d, False),
    "goto": lambda v: _block_goto(*_parse_xy(v)),
    "point_direction": _block_point_direction,
    "glide": lambda v: _block_glide(*_parse_xy(v)),
    "say": lambda t: _block_say(t),
    "say_for": lambda t, s=2: _block_say(t, s),
    "think": lambda t: _block_think(t),
    "show": lambda *_: _block_show(),
    "hide": lambda *_: _block_hide(),
    "size": _block_size,
    "change_size": _block_change_size,
    "next_costume": lambda *_: _block_next_costume(),
    "wait": _block_wait,
    "stop_all": lambda *_: _block_stop_all(),
    "pen_down": lambda *_: _block_pen_down(),
    "pen_up": lambda *_: _block_pen_up(),
    "pen_clear": lambda *_: _block_pen_clear(),
    "pen_stamp": lambda *_: _block_pen_stamp(),
    "pen_color": _block_pen_color,
}


def _parse_xy(value: str) -> tuple[float, float]:
    x, y = (value or "0,0").split(",")
    return float(x), float(y)


def _block_uses_pen(b: dict) -> bool:
    if str(b.get("opcode", "")).startswith("pen_"):
        return True
    return any(_block_uses_pen(sub) for sub in b.get("substack", []))


# ── Basit şekil SVG üretimi (kukla çizme / kostüm ekleme) ───────────────────
_SHAPES = ("daire", "kare", "üçgen", "yıldız")


def _shape_svg(shape: str, hexcolor: str) -> bytes:
    shape = (shape or "daire").lower().strip()
    if shape in ("kare", "kutu"):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
              f'<rect x="5" y="5" width="90" height="90" fill="{hexcolor}"/></svg>')
    elif shape in ("üçgen", "ucgen", "üçgeni"):
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
              f'<polygon points="50,5 95,95 5,95" fill="{hexcolor}"/></svg>')
    elif shape in ("yıldız", "yildiz"):
        cx, cy, r_out, r_in = 50, 50, 45, 18
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            r = r_out if i % 2 == 0 else r_in
            pts.append(f"{cx + r*math.cos(ang):.1f},{cy - r*math.sin(ang):.1f}")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
              f'<polygon points="{" ".join(pts)}" fill="{hexcolor}"/></svg>')
    else:   # daire (varsayılan)
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
              f'<circle cx="50" cy="50" r="45" fill="{hexcolor}"/></svg>')
    return svg.encode("utf-8")


def _make_costume(name: str, shape: str, color_name: str) -> tuple[dict, bytes]:
    hexcolor = _PEN_COLORS.get((color_name or "").lower().strip(), "#3388FF")
    svg_bytes = _shape_svg(shape, hexcolor)
    md5 = hashlib.md5(svg_bytes).hexdigest()
    costume = {"name": name, "dataFormat": "svg", "assetId": md5,
              "md5ext": f"{md5}.svg", "rotationCenterX": 50, "rotationCenterY": 50}
    return costume, svg_bytes


# ── GERÇEK Scratch kütüphane kuklaları (91 doğrulanmış kayıt) ───────────────
# Bu veriler Scratch Desktop'ın kendi kurulumundan (resources/static/libraries/
# sprites.json + resources/static/assets/) ÇIKARILDI — hash TAHMİN EDİLMEDİ.
# Her kaydın gerçek SVG/PNG dosyası scratch_library_assets/ klasöründe duruyor.
LIBRARY_SPRITES = {
    "ahtapot": {"sprite_name": "Octopus", "costume_name": "octopus-a",
        "assetId": "e22d9b633feffc1d026980a1f21e07d7", "md5ext": "e22d9b633feffc1d026980a1f21e07d7.svg", "dataFormat": "svg",
        "rotationCenterX": 88, "rotationCenterY": 86},
    "anahtar": {"sprite_name": "Key", "costume_name": "key",
        "assetId": "680d3e4dce002f922b32447fcf29743d", "md5ext": "680d3e4dce002f922b32447fcf29743d.svg", "dataFormat": "svg",
        "rotationCenterX": 42, "rotationCenterY": 27},
    "araba": {"sprite_name": "Convertible", "costume_name": "convertible",
        "assetId": "5b883f396844ff5cfecd7c95553fa4fb", "md5ext": "5b883f396844ff5cfecd7c95553fa4fb.png", "dataFormat": "png",
        "rotationCenterX": 180, "rotationCenterY": 44},
    "aslan": {"sprite_name": "Lion", "costume_name": "lion-a",
        "assetId": "e88e83c8b3ca80c54540b5f0c5a0cc03", "md5ext": "e88e83c8b3ca80c54540b5f0c5a0cc03.svg", "dataFormat": "svg",
        "rotationCenterX": 95, "rotationCenterY": 43},
    "at": {"sprite_name": "Horse", "costume_name": "horse-a",
        "assetId": "ad458251c5bf5b375870829f1762fa47", "md5ext": "ad458251c5bf5b375870829f1762fa47.svg", "dataFormat": "svg",
        "rotationCenterX": 119, "rotationCenterY": 83},
    "ayakkabı": {"sprite_name": "Shoes", "costume_name": "shoes-a",
        "assetId": "f89f1656251248f1591aa67ae946c047", "md5ext": "f89f1656251248f1591aa67ae946c047.svg", "dataFormat": "svg",
        "rotationCenterX": 40, "rotationCenterY": 13},
    "ayı": {"sprite_name": "Bear", "costume_name": "bear-a",
        "assetId": "deef1eaa96d550ae6fc11524a1935024", "md5ext": "deef1eaa96d550ae6fc11524a1935024.svg", "dataFormat": "svg",
        "rotationCenterX": 100, "rotationCenterY": 90},
    "ağaç": {"sprite_name": "Tree1", "costume_name": "tree1",
        "assetId": "d04b15886635101db8220a4361c0c88d", "md5ext": "d04b15886635101db8220a4361c0c88d.svg", "dataFormat": "svg",
        "rotationCenterX": 77, "rotationCenterY": 126},
    "balon": {"sprite_name": "Balloon1", "costume_name": "balloon1-a",
        "assetId": "d7974f9e15000c16222f94ee32d8227a", "md5ext": "d7974f9e15000c16222f94ee32d8227a.svg", "dataFormat": "svg",
        "rotationCenterX": 32, "rotationCenterY": 94},
    "balonbalığı": {"sprite_name": "Pufferfish", "costume_name": "pufferfish-a",
        "assetId": "b8aa1bd46eacc054c695b89167c3ad28", "md5ext": "b8aa1bd46eacc054c695b89167c3ad28.svg", "dataFormat": "svg",
        "rotationCenterX": 69, "rotationCenterY": 61},
    "balık": {"sprite_name": "Fish", "costume_name": "fish-a",
        "assetId": "a9b3d163756621f8395592ad77fb9369", "md5ext": "a9b3d163756621f8395592ad77fb9369.svg", "dataFormat": "svg",
        "rotationCenterX": 63, "rotationCenterY": 45},
    "basketboltopu": {"sprite_name": "Basketball", "costume_name": "basketball",
        "assetId": "6b0b2aaa12d655e96b5b34e92d9fbd4f", "md5ext": "6b0b2aaa12d655e96b5b34e92d9fbd4f.svg", "dataFormat": "svg",
        "rotationCenterX": 23, "rotationCenterY": 23},
    "baykuş": {"sprite_name": "Owl", "costume_name": "owl-a",
        "assetId": "a518f70b65ec489e709795209b43207a", "md5ext": "a518f70b65ec489e709795209b43207a.svg", "dataFormat": "svg",
        "rotationCenterX": 24, "rotationCenterY": 40},
    "beyzboltopu": {"sprite_name": "Baseball", "costume_name": "baseball",
        "assetId": "74e08fc57820f925c7689e7b754c5848", "md5ext": "74e08fc57820f925c7689e7b754c5848.svg", "dataFormat": "svg",
        "rotationCenterX": 28, "rotationCenterY": 28},
    "bina": {"sprite_name": "Buildings", "costume_name": "building-a",
        "assetId": "e8c9508b1f6a0a432e09c10ef9ada67c", "md5ext": "e8c9508b1f6a0a432e09c10ef9ada67c.svg", "dataFormat": "svg",
        "rotationCenterX": 40, "rotationCenterY": 30},
    "bulut": {"sprite_name": "Cloud", "costume_name": "cloud",
        "assetId": "c9630e30e59e4565e785a26f58568904", "md5ext": "c9630e30e59e4565e785a26f58568904.svg", "dataFormat": "svg",
        "rotationCenterX": 71, "rotationCenterY": 45},
    "böcek": {"sprite_name": "Beetle", "costume_name": "beetle",
        "assetId": "46d0dfd4ae7e9bfe3a6a2e35a4905eae", "md5ext": "46d0dfd4ae7e9bfe3a6a2e35a4905eae.svg", "dataFormat": "svg",
        "rotationCenterX": 43, "rotationCenterY": 38},
    "büyücü": {"sprite_name": "Wizard", "costume_name": "wizard-a",
        "assetId": "91d495085eb4d02a375c42f6318071e7", "md5ext": "91d495085eb4d02a375c42f6318071e7.svg", "dataFormat": "svg",
        "rotationCenterX": 87, "rotationCenterY": 150},
    "cadı": {"sprite_name": "Witch", "costume_name": "witch-a",
        "assetId": "44cbaf358d2d8e66815e447c25a4b72e", "md5ext": "44cbaf358d2d8e66815e447c25a4b72e.svg", "dataFormat": "svg",
        "rotationCenterX": 65, "rotationCenterY": 140},
    "civciv": {"sprite_name": "Chick", "costume_name": "chick-a",
        "assetId": "80abbc427366bca477ccf1ef0faf240a", "md5ext": "80abbc427366bca477ccf1ef0faf240a.svg", "dataFormat": "svg",
        "rotationCenterX": 32, "rotationCenterY": 37},
    "davul": {"sprite_name": "Drum", "costume_name": "drum-a",
        "assetId": "ce6971317035091341ec40571c9056e9", "md5ext": "ce6971317035091341ec40571c9056e9.svg", "dataFormat": "svg",
        "rotationCenterX": 43, "rotationCenterY": 60},
    "denizanası": {"sprite_name": "Jellyfish", "costume_name": "jellyfish-a",
        "assetId": "4e259b7c08f05145fc7800b33e4f356e", "md5ext": "4e259b7c08f05145fc7800b33e4f356e.svg", "dataFormat": "svg",
        "rotationCenterX": 99, "rotationCenterY": 86},
    "denizyıldızı": {"sprite_name": "Starfish", "costume_name": "starfish-a",
        "assetId": "69dca6e42d45d3fef89f81de40b11bef", "md5ext": "69dca6e42d45d3fef89f81de40b11bef.svg", "dataFormat": "svg",
        "rotationCenterX": 75, "rotationCenterY": 75},
    "dinozor": {"sprite_name": "Dinosaur1", "costume_name": "dinosaur1-a",
        "assetId": "45b02fbd582c15a50e1953830b59b377", "md5ext": "45b02fbd582c15a50e1953830b59b377.svg", "dataFormat": "svg",
        "rotationCenterX": 98, "rotationCenterY": 92},
    "donut": {"sprite_name": "Donut", "costume_name": "donut",
        "assetId": "316a67c9e966fd015b4538f54be456db", "md5ext": "316a67c9e966fd015b4538f54be456db.svg", "dataFormat": "svg",
        "rotationCenterX": 72.11747235252724, "rotationCenterY": 14.658782444689848},
    "ejderha": {"sprite_name": "Dragon", "costume_name": "dragon-a",
        "assetId": "12ead885460d96a19132e5970839d36d", "md5ext": "12ead885460d96a19132e5970839d36d.svg", "dataFormat": "svg",
        "rotationCenterX": 124.12215277545062, "rotationCenterY": 106.25815347723332},
    "elma": {"sprite_name": "Apple", "costume_name": "apple",
        "assetId": "3826a4091a33e4d26f87a2fac7cf796b", "md5ext": "3826a4091a33e4d26f87a2fac7cf796b.svg", "dataFormat": "svg",
        "rotationCenterX": 31, "rotationCenterY": 31},
    "fare": {"sprite_name": "Mouse1", "costume_name": "mouse1-a",
        "assetId": "c5f76b65e30075c12d49ea8a8f7d6bad", "md5ext": "c5f76b65e30075c12d49ea8a8f7d6bad.svg", "dataFormat": "svg",
        "rotationCenterX": 50, "rotationCenterY": 27},
    "fil": {"sprite_name": "Elephant", "costume_name": "elephant-a",
        "assetId": "b59873e9558c1c456200f50e5ab34770", "md5ext": "b59873e9558c1c456200f50e5ab34770.svg", "dataFormat": "svg",
        "rotationCenterX": 107, "rotationCenterY": 33},
    "futboltopu": {"sprite_name": "Soccer Ball", "costume_name": "soccer ball",
        "assetId": "5d973d7a3a8be3f3bd6e1cd0f73c32b5", "md5ext": "5d973d7a3a8be3f3bd6e1cd0f73c32b5.svg", "dataFormat": "svg",
        "rotationCenterX": 23, "rotationCenterY": 22},
    "gitar": {"sprite_name": "Guitar", "costume_name": "guitar-a",
        "assetId": "8704489dcf1a3ca93c5db40ebe5acd38", "md5ext": "8704489dcf1a3ca93c5db40ebe5acd38.svg", "dataFormat": "svg",
        "rotationCenterX": 47, "rotationCenterY": 83},
    "gökkuşağı": {"sprite_name": "Rainbow", "costume_name": "rainbow",
        "assetId": "033979eba12e4572b2520bd93a87583e", "md5ext": "033979eba12e4572b2520bd93a87583e.svg", "dataFormat": "svg",
        "rotationCenterX": 72, "rotationCenterY": 36},
    "gözlük": {"sprite_name": "Glasses", "costume_name": "glasses-a",
        "assetId": "705035328ac53d5ce1aa5a1ed1c2d172", "md5ext": "705035328ac53d5ce1aa5a1ed1c2d172.svg", "dataFormat": "svg",
        "rotationCenterX": 33, "rotationCenterY": 13},
    "güneş": {"sprite_name": "Sun", "costume_name": "sun",
        "assetId": "406808d86aff20a15d592b308e166a32", "md5ext": "406808d86aff20a15d592b308e166a32.svg", "dataFormat": "svg",
        "rotationCenterX": 54, "rotationCenterY": 54},
    "güvercin": {"sprite_name": "Dove", "costume_name": "dove-a",
        "assetId": "0f83ab55012a7affd94e38250d55a0a0", "md5ext": "0f83ab55012a7affd94e38250d55a0a0.svg", "dataFormat": "svg",
        "rotationCenterX": 86, "rotationCenterY": 59},
    "hayalet": {"sprite_name": "Ghost", "costume_name": "ghost-a",
        "assetId": "f522b08c5757569ad289d67bce290cd0", "md5ext": "f522b08c5757569ad289d67bce290cd0.svg", "dataFormat": "svg",
        "rotationCenterX": 37, "rotationCenterY": 68},
    "hediye": {"sprite_name": "Gift", "costume_name": "gift-a",
        "assetId": "0fdd104de718c5fc4a65da429468bdbd", "md5ext": "0fdd104de718c5fc4a65da429468bdbd.svg", "dataFormat": "svg",
        "rotationCenterX": 33, "rotationCenterY": 25},
    "horoz": {"sprite_name": "Rooster", "costume_name": "rooster-a",
        "assetId": "0ae345deb1c81ec7f4f4644c26ac85fa", "md5ext": "0ae345deb1c81ec7f4f4644c26ac85fa.svg", "dataFormat": "svg",
        "rotationCenterX": 59, "rotationCenterY": 70},
    "iskelet": {"sprite_name": "Skeleton", "costume_name": "skeleton-a",
        "assetId": "c4d755c672a0826caa7b6fb767cc3f9b", "md5ext": "c4d755c672a0826caa7b6fb767cc3f9b.svg", "dataFormat": "svg",
        "rotationCenterX": 59, "rotationCenterY": 100},
    "kalem": {"sprite_name": "Pencil", "costume_name": "pencil-a",
        "assetId": "b3d6eae85f285dd618bf9dcf609b9454", "md5ext": "b3d6eae85f285dd618bf9dcf609b9454.svg", "dataFormat": "svg",
        "rotationCenterX": 49, "rotationCenterY": 54},
    "kalp": {"sprite_name": "Heart", "costume_name": "heart red",
        "assetId": "c77e640f6e023e7ce1e376da0f26e1eb", "md5ext": "c77e640f6e023e7ce1e376da0f26e1eb.svg", "dataFormat": "svg",
        "rotationCenterX": 65, "rotationCenterY": 56},
    "kamyon": {"sprite_name": "Truck", "costume_name": "Truck-a",
        "assetId": "aaa05abc5aa182a0d7bfdc6db0f3207a", "md5ext": "aaa05abc5aa182a0d7bfdc6db0f3207a.svg", "dataFormat": "svg",
        "rotationCenterX": 173.6413034351145, "rotationCenterY": 48.359999999999985},
    "kardanadam": {"sprite_name": "Snowman", "costume_name": "snowman",
        "assetId": "0f109df620f935b94cb154101e6586d4", "md5ext": "0f109df620f935b94cb154101e6586d4.svg", "dataFormat": "svg",
        "rotationCenterX": 75, "rotationCenterY": 75},
    "karpuz": {"sprite_name": "Watermelon", "costume_name": "watermelon-a",
        "assetId": "21d1340478e32a942914a7afd12b9f1a", "md5ext": "21d1340478e32a942914a7afd12b9f1a.svg", "dataFormat": "svg",
        "rotationCenterX": 40.13434982299805, "rotationCenterY": 27.860475540161133},
    "kartanesi": {"sprite_name": "Snowflake", "costume_name": "snowflake",
        "assetId": "083735cc9cd0e6d8c3dbab5ab9ee5407", "md5ext": "083735cc9cd0e6d8c3dbab5ab9ee5407.svg", "dataFormat": "svg",
        "rotationCenterX": 104, "rotationCenterY": 103},
    "kedi": {"sprite_name": "Cat", "costume_name": "cat-a",
        "assetId": "bcf454acf82e4504149f7ffe07081dbc", "md5ext": "bcf454acf82e4504149f7ffe07081dbc.svg", "dataFormat": "svg",
        "rotationCenterX": 48, "rotationCenterY": 50},
    "kedi2": {"sprite_name": "Cat 2", "costume_name": "cat 2",
        "assetId": "7499cf6ec438d0c7af6f896bc6adc294", "md5ext": "7499cf6ec438d0c7af6f896bc6adc294.svg", "dataFormat": "svg",
        "rotationCenterX": 87, "rotationCenterY": 39},
    "kelebek": {"sprite_name": "Butterfly 1", "costume_name": "butterfly1-a",
        "assetId": "fe98df7367e314d9640bfaa54fc239be", "md5ext": "fe98df7367e314d9640bfaa54fc239be.svg", "dataFormat": "svg",
        "rotationCenterX": 65, "rotationCenterY": 49},
    "kelebek2": {"sprite_name": "Butterfly 2", "costume_name": "butterfly2-a",
        "assetId": "372ae0abd2e8e50a20bc12cb160d8746", "md5ext": "372ae0abd2e8e50a20bc12cb160d8746.svg", "dataFormat": "svg",
        "rotationCenterX": 75, "rotationCenterY": 75},
    "kirpi": {"sprite_name": "Hedgehog", "costume_name": "hedgehog-a",
        "assetId": "3b0e1717859808cecf1a45e2a32dc201", "md5ext": "3b0e1717859808cecf1a45e2a32dc201.svg", "dataFormat": "svg",
        "rotationCenterX": 71, "rotationCenterY": 56},
    "kurbağa": {"sprite_name": "Frog", "costume_name": "frog",
        "assetId": "390845c11df0924f3b627bafeb3f814e", "md5ext": "390845c11df0924f3b627bafeb3f814e.svg", "dataFormat": "svg",
        "rotationCenterX": 48, "rotationCenterY": 30},
    "kutup ayısı": {"sprite_name": "Polar Bear", "costume_name": "polar bear-a",
        "assetId": "d050a3394b61ade080f7963c40192e7d", "md5ext": "d050a3394b61ade080f7963c40192e7d.svg", "dataFormat": "svg",
        "rotationCenterX": 104, "rotationCenterY": 42},
    "kuş": {"sprite_name": "Dove", "costume_name": "dove-a",
        "assetId": "0f83ab55012a7affd94e38250d55a0a0", "md5ext": "0f83ab55012a7affd94e38250d55a0a0.svg", "dataFormat": "svg",
        "rotationCenterX": 86, "rotationCenterY": 59},
    "köpek": {"sprite_name": "Dog2", "costume_name": "dog2-a",
        "assetId": "66b435d333f34d02d5ae49a598bcc5b3", "md5ext": "66b435d333f34d02d5ae49a598bcc5b3.svg", "dataFormat": "svg",
        "rotationCenterX": 75, "rotationCenterY": 75},
    "köpek2": {"sprite_name": "Dog1", "costume_name": "dog1-a",
        "assetId": "35cd78a8a71546a16c530d0b2d7d5a7f", "md5ext": "35cd78a8a71546a16c530d0b2d7d5a7f.svg", "dataFormat": "svg",
        "rotationCenterX": 83, "rotationCenterY": 80},
    "köpekbalığı": {"sprite_name": "Shark", "costume_name": "shark-a",
        "assetId": "6c8008ae677ec51af8da5023fa2cd521", "md5ext": "6c8008ae677ec51af8da5023fa2cd521.svg", "dataFormat": "svg",
        "rotationCenterX": 150, "rotationCenterY": 60},
    "lama": {"sprite_name": "Llama", "costume_name": "llama",
        "assetId": "c97824f20a45adfa3ff362f82247a025", "md5ext": "c97824f20a45adfa3ff362f82247a025.svg", "dataFormat": "svg",
        "rotationCenterX": 72, "rotationCenterY": 95},
    "maymun": {"sprite_name": "Monkey", "costume_name": "monkey-a",
        "assetId": "254926ee81bfa82f2db7009a80635061", "md5ext": "254926ee81bfa82f2db7009a80635061.svg", "dataFormat": "svg",
        "rotationCenterX": 68, "rotationCenterY": 99},
    "motosiklet": {"sprite_name": "Motorcycle", "costume_name": "Motorcycle-a",
        "assetId": "b73447c2577b8f77b5e2eb1da6d6445a", "md5ext": "b73447c2577b8f77b5e2eb1da6d6445a.svg", "dataFormat": "svg",
        "rotationCenterX": 51.21999999999994, "rotationCenterY": 43.599999999999994},
    "muz": {"sprite_name": "Bananas", "costume_name": "bananas",
        "assetId": "e5d3d3eb61797f5999732a8f5efead24", "md5ext": "e5d3d3eb61797f5999732a8f5efead24.svg", "dataFormat": "svg",
        "rotationCenterX": 39, "rotationCenterY": 38},
    "panter": {"sprite_name": "Panther", "costume_name": "panther-a",
        "assetId": "0e7c244f54b27058f8b17d9e0d3cee12", "md5ext": "0e7c244f54b27058f8b17d9e0d3cee12.svg", "dataFormat": "svg",
        "rotationCenterX": 125, "rotationCenterY": 81},
    "papağan": {"sprite_name": "Parrot", "costume_name": "parrot-a",
        "assetId": "082f371c206f07d20e53595a9c69cc22", "md5ext": "082f371c206f07d20e53595a9c69cc22.svg", "dataFormat": "svg",
        "rotationCenterX": 86, "rotationCenterY": 106},
    "pasta": {"sprite_name": "Cake", "costume_name": "cake-a",
        "assetId": "862488bf66b67c5330cae9235b853b6e", "md5ext": "862488bf66b67c5330cae9235b853b6e.svg", "dataFormat": "svg",
        "rotationCenterX": 64, "rotationCenterY": 50},
    "penguen": {"sprite_name": "Penguin", "costume_name": "penguin-a",
        "assetId": "dad5b0d82cb6e053d1ded2ef537a9453", "md5ext": "dad5b0d82cb6e053d1ded2ef537a9453.svg", "dataFormat": "svg",
        "rotationCenterX": 36, "rotationCenterY": 46},
    "portakal": {"sprite_name": "Orange", "costume_name": "orange",
        "assetId": "d0a55aae1decb57152b454c9a5226757", "md5ext": "d0a55aae1decb57152b454c9a5226757.svg", "dataFormat": "svg",
        "rotationCenterX": 19, "rotationCenterY": 18},
    "rengeyiği": {"sprite_name": "Reindeer", "costume_name": "reindeer",
        "assetId": "60993a025167e7886736109dca5d55e2", "md5ext": "60993a025167e7886736109dca5d55e2.svg", "dataFormat": "svg",
        "rotationCenterX": 39, "rotationCenterY": 70},
    "robot": {"sprite_name": "Robot", "costume_name": "robot-a",
        "assetId": "89679608327ad572b93225d06fe9edda", "md5ext": "89679608327ad572b93225d06fe9edda.svg", "dataFormat": "svg",
        "rotationCenterX": 58.44040786180267, "rotationCenterY": 95.79979917361628},
    "roket": {"sprite_name": "Rocketship", "costume_name": "rocketship-a",
        "assetId": "525c06ceb3a351244bcd810c9ba951c7", "md5ext": "525c06ceb3a351244bcd810c9ba951c7.svg", "dataFormat": "svg",
        "rotationCenterX": 63, "rotationCenterY": 92},
    "sihirlideğnek": {"sprite_name": "Magic Wand", "costume_name": "magicwand",
        "assetId": "89aa5332042d7bbf8368293a4efeafa4", "md5ext": "89aa5332042d7bbf8368293a4efeafa4.svg", "dataFormat": "svg",
        "rotationCenterX": 41, "rotationCenterY": 18},
    "sincap": {"sprite_name": "Squirrel", "costume_name": "squirrel",
        "assetId": "b86efb7f23387300cf9037a61f328ab9", "md5ext": "b86efb7f23387300cf9037a61f328ab9.png", "dataFormat": "png",
        "rotationCenterX": 158, "rotationCenterY": 146},
    "tavuk": {"sprite_name": "Hen", "costume_name": "hen-a",
        "assetId": "b02a33e32313cc9a75781a6fafd07033", "md5ext": "b02a33e32313cc9a75781a6fafd07033.svg", "dataFormat": "svg",
        "rotationCenterX": 60, "rotationCenterY": 53},
    "tavşan": {"sprite_name": "Rabbit", "costume_name": "rabbit-a",
        "assetId": "970f886bfa454e1daa6d6c30ef49a972", "md5ext": "970f886bfa454e1daa6d6c30ef49a972.svg", "dataFormat": "svg",
        "rotationCenterX": 84, "rotationCenterY": 84},
    "tekboynuzlu at": {"sprite_name": "Unicorn", "costume_name": "unicorn",
        "assetId": "1439d51d9878276362b123c9045af6b5", "md5ext": "1439d51d9878276362b123c9045af6b5.svg", "dataFormat": "svg",
        "rotationCenterX": 91, "rotationCenterY": 95},
    "tilki": {"sprite_name": "Fox", "costume_name": "fox-a",
        "assetId": "9dd59a4514b5373d4f665db78e145636", "md5ext": "9dd59a4514b5373d4f665db78e145636.svg", "dataFormat": "svg",
        "rotationCenterX": 86, "rotationCenterY": 44},
    "top": {"sprite_name": "Ball", "costume_name": "ball-a",
        "assetId": "3c6241985b581284ec191f9d1deffde8", "md5ext": "3c6241985b581284ec191f9d1deffde8.svg", "dataFormat": "svg",
        "rotationCenterX": 22, "rotationCenterY": 22},
    "trompet": {"sprite_name": "Trumpet", "costume_name": "trumpet-a",
        "assetId": "47a1ec267505be96b678df30b92ec534", "md5ext": "47a1ec267505be96b678df30b92ec534.svg", "dataFormat": "svg",
        "rotationCenterX": 57, "rotationCenterY": 38},
    "tukan": {"sprite_name": "Toucan", "costume_name": "toucan-a",
        "assetId": "9eef2e49b3bbf371603ae783cd82db3c", "md5ext": "9eef2e49b3bbf371603ae783cd82db3c.svg", "dataFormat": "svg",
        "rotationCenterX": 80, "rotationCenterY": 63},
    "uçan kedi": {"sprite_name": "Cat Flying", "costume_name": "cat flying-a",
        "assetId": "a1ab94c8172c3b97ed9a2bf7c32172cd", "md5ext": "a1ab94c8172c3b97ed9a2bf7c32172cd.svg", "dataFormat": "svg",
        "rotationCenterX": 55, "rotationCenterY": 37},
    "uğur böceği": {"sprite_name": "Ladybug1", "costume_name": "ladybug2",
        "assetId": "169c0efa8c094fdedddf8c19c36f0229", "md5ext": "169c0efa8c094fdedddf8c19c36f0229.svg", "dataFormat": "svg",
        "rotationCenterX": 41, "rotationCenterY": 43},
    "yavru köpek": {"sprite_name": "Puppy", "costume_name": "puppy right",
        "assetId": "2768d9e44a0aab055856d301bbc2b04e", "md5ext": "2768d9e44a0aab055856d301bbc2b04e.png", "dataFormat": "png",
        "rotationCenterX": 107, "rotationCenterY": 103},
    "yelkenli": {"sprite_name": "Sailboat", "costume_name": "sailboat",
        "assetId": "ca241a938a2c44a0de6b91230012ff39", "md5ext": "ca241a938a2c44a0de6b91230012ff39.png", "dataFormat": "png",
        "rotationCenterX": 224, "rotationCenterY": 182},
    "yengeç": {"sprite_name": "Crab", "costume_name": "crab-a",
        "assetId": "f7cdd2acbc6d7559d33be8675059c79e", "md5ext": "f7cdd2acbc6d7559d33be8675059c79e.svg", "dataFormat": "svg",
        "rotationCenterX": 75, "rotationCenterY": 75},
    "yumurta": {"sprite_name": "Egg", "costume_name": "egg-a",
        "assetId": "f8ee449298c1446cb0ef281923a4e57a", "md5ext": "f8ee449298c1446cb0ef281923a4e57a.svg", "dataFormat": "svg",
        "rotationCenterX": 18, "rotationCenterY": 26},
    "yusufçuk": {"sprite_name": "Dragonfly", "costume_name": "Dragonfly-a",
        "assetId": "5cdfe67af929e3fb095e83c9c4b0bd78", "md5ext": "5cdfe67af929e3fb095e83c9c4b0bd78.svg", "dataFormat": "svg",
        "rotationCenterX": 108, "rotationCenterY": 52},
    "yılan": {"sprite_name": "Snake", "costume_name": "snake-a",
        "assetId": "f0e6ebdbdc8571b42f8a48cc2aed3042", "md5ext": "f0e6ebdbdc8571b42f8a48cc2aed3042.svg", "dataFormat": "svg",
        "rotationCenterX": 142, "rotationCenterY": 68},
    "yıldız": {"sprite_name": "Star", "costume_name": "star",
        "assetId": "551629f2a64c1f3703e57aaa133effa6", "md5ext": "551629f2a64c1f3703e57aaa133effa6.svg", "dataFormat": "svg",
        "rotationCenterX": 22, "rotationCenterY": 23},
    "zebra": {"sprite_name": "Zebra", "costume_name": "zebra-a",
        "assetId": "0e3bc5073305b7079b5e9a8c7b7d7f9b", "md5ext": "0e3bc5073305b7079b5e9a8c7b7d7f9b.svg", "dataFormat": "svg",
        "rotationCenterX": 97, "rotationCenterY": 56},
    "zürafa": {"sprite_name": "Giraffe", "costume_name": "giraffe-a",
        "assetId": "43e89629fb9df7051eaf307c695424fc", "md5ext": "43e89629fb9df7051eaf307c695424fc.svg", "dataFormat": "svg",
        "rotationCenterX": 87, "rotationCenterY": 132},
    "çekirge": {"sprite_name": "Grasshopper", "costume_name": "Grasshopper-a",
        "assetId": "e7210a370837dd1e4ebc1a56a973b7f6", "md5ext": "e7210a370837dd1e4ebc1a56a973b7f6.svg", "dataFormat": "svg",
        "rotationCenterX": 103, "rotationCenterY": 43},
    "çilek": {"sprite_name": "Strawberry", "costume_name": "strawberry-a",
        "assetId": "2fa57942dc7ded7eddc4d41554768d67", "md5ext": "2fa57942dc7ded7eddc4d41554768d67.svg", "dataFormat": "svg",
        "rotationCenterX": 31, "rotationCenterY": 47},
    "ördek": {"sprite_name": "Duck", "costume_name": "duck",
        "assetId": "c9837d0454f5f0f73df290af2045359b", "md5ext": "c9837d0454f5f0f73df290af2045359b.svg", "dataFormat": "svg",
        "rotationCenterX": 61, "rotationCenterY": 59},
}

def _library_assets_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "scratch_library_assets"


def _library_costume(tr_name: str) -> tuple[dict, bytes] | None:
    """Türkçe isim GERÇEK bir Scratch kütüphane kuklasıyla eşleşiyorsa,
    o kuklanın GERÇEK kostümünü (ve gerçek dosya baytlarını) döner.
    Eşleşme yoksa None — çağıran taraf o zaman elle çizilmiş şekle döner."""
    key = (tr_name or "").lower().strip()
    entry = LIBRARY_SPRITES.get(key)
    if not entry:
        return None
    asset_path = _library_assets_dir() / entry["md5ext"]
    if not asset_path.exists():
        return None   # dosya bir şekilde eksikse sessizce elle-çizime düş
    data = asset_path.read_bytes()
    costume = {"name": entry["costume_name"], "dataFormat": entry["dataFormat"],
              "assetId": entry["assetId"], "md5ext": entry["md5ext"],
              "rotationCenterX": entry["rotationCenterX"],
              "rotationCenterY": entry["rotationCenterY"]}
    if "bitmapResolution" in entry:
        costume["bitmapResolution"] = entry["bitmapResolution"]
    return costume, data



# ── Kukla yönetimi ───────────────────────────────────────────────────────────
def _find_sprite_ci(name: str) -> str | None:
    """Var olan kukla adları arasında BÜYÜK/KÜÇÜK HARF DUYARSIZ arama —
    kullanıcı 'köpek' dese de kukla 'Köpek' olarak kayıtlıysa bulur.
    Tam eşleşme yoksa, Türkçe hâl eki farkını da tolere eder ('köpeği'
    dendiğinde 'Köpek' kuklasını bulur — sondaki ek + varsa ünsüz
    yumuşaması olası ekleri deneyerek)."""
    key = (name or "").lower().strip()
    for existing in _SPRITES:
        if existing.lower() == key:
            return existing
    # Tam eşleşme yok — sondan 1-2 karakter kırparak dene ('köpeği' → 'köpek'/'köpe')
    for cut in (1, 2):
        if len(key) > cut:
            trimmed = key[:-cut]
            for existing in _SPRITES:
                if existing.lower() == trimmed or existing.lower().startswith(trimmed) and len(existing) - len(trimmed) <= 2:
                    return existing
    return None


def add_sprite(name: str, shape: str = "daire", color: str = "mavi",
              color_explicit: bool = False) -> str:
    global _CURRENT_SPRITE
    name = (name or "").strip()

    # ── Kullanıcı AÇIKÇA bir renk istediyse (ör. "kırmızı yıldız"), gerçek
    #    kütüphaneyi ATLA — o kuklanın rengi SABİTTİR, kullanıcının rengini
    #    veremeyiz. Elle çizilmiş şekil, istenen rengi tam verir.
    if not color_explicit:
        lib_result = _library_costume(name) or _library_costume(shape)
        if lib_result:
            costume, real_bytes = lib_result
            display_name = name.capitalize() if name else costume["name"].capitalize()
            if _find_sprite_ci(display_name):
                return f"'{display_name}' adında bir kukla zaten var. Farklı bir isim söyler misin?"
            state = _default_sprite_state()
            state["costumes"] = [costume]
            state["assets"] = {costume["md5ext"]: real_bytes}
            _SPRITES[display_name] = state
            _CURRENT_SPRITE = display_name
            return (f"'{display_name}' kuklası eklendi (Scratch kütüphanesinden GERÇEK görsel) "
                    "— şimdi AKTİF kukla bu, sonraki komutlar buna uygulanır.")

    name = name or f"Kukla{len(_SPRITES) + 1}"
    if _find_sprite_ci(name):
        return f"'{name}' adında bir kukla zaten var. Farklı bir isim söyler misin?"
    costume, svg_bytes = _make_costume(f"{name}_kostüm1", shape, color)
    state = _default_sprite_state()
    state["costumes"] = [costume]
    state["assets"] = {costume["md5ext"]: svg_bytes}
    _SPRITES[name] = state
    _CURRENT_SPRITE = name
    return (f"'{name}' kuklası eklendi ({shape}, {color}) — şimdi AKTİF kukla bu, "
            "sonraki komutlar buna uygulanır.")


def delete_sprite(name: str) -> str:
    global _CURRENT_SPRITE
    name = (name or "").strip()
    real = _find_sprite_ci(name)
    if not real:
        return f"'{name}' adında bir kukla bulamadım. Mevcut kuklalar: {', '.join(_SPRITES)}."
    if len(_SPRITES) <= 1:
        return "Son kalan kuklayı silemezsin — en az bir kukla kalmalı."
    del _SPRITES[real]
    if _CURRENT_SPRITE == real:
        _CURRENT_SPRITE = next(iter(_SPRITES))
    return f"'{real}' kuklası silindi. Aktif kukla artık: {_CURRENT_SPRITE}."


def switch_sprite(name: str) -> str:
    global _CURRENT_SPRITE
    name = (name or "").strip()
    real = _find_sprite_ci(name)
    if not real:
        return f"'{name}' adında bir kukla yok. Önce 'kukla ekle {name}' de. Mevcut: {', '.join(_SPRITES)}."
    _CURRENT_SPRITE = real
    return f"Aktif kukla artık: {real}. Yeni komutlar buna uygulanacak."


def add_costume(shape: str = "daire", color: str = "mavi", color_explicit: bool = False) -> str:
    state = _cur()
    idx = len(state["costumes"]) + 1
    if not color_explicit:
        lib_result = _library_costume(shape)
        if lib_result:
            costume, real_bytes = lib_result
            state["costumes"].append(costume)
            state["assets"][costume["md5ext"]] = real_bytes
            return (f"'{_CURRENT_SPRITE}' kuklasına Scratch kütüphanesinden GERÇEK "
                    f"bir kostüm eklendi (toplam {idx} kostüm).")
    costume, svg_bytes = _make_costume(f"kostüm{idx}", shape, color)
    state["costumes"].append(costume)
    state["assets"][costume["md5ext"]] = svg_bytes
    return f"'{_CURRENT_SPRITE}' kuklasına yeni kostüm eklendi ({shape}, {color}, toplam {idx} kostüm)."


def add_comment(text: str) -> str:
    state = _cur()
    if not state["script"]:
        return "Henüz blok eklemedin — yorum ekleyecek bir blok yok."
    state["comments"].append({"text": text or "not", "target": "last_top_level"})
    return f"Yorum eklendi: \"{text}\" (son bloğun üzerine)."


# ── .sb3 üretimi (iç içe substack'leri doğru işler) ─────────────────────────
def _emit_chain(blocks: dict, script: list[dict], parent_id: str,
                variables: dict, top_level: bool = False) -> str | None:
    prev_id = None
    first_id = None
    for b in script:
        bid = _uid()
        if first_id is None:
            first_id = bid

        inputs = dict(b.get("inputs", {}))
        fields = {k: list(v) for k, v in b.get("fields", {}).items()}

        for key, val in list(inputs.items()):
            if isinstance(val, tuple) and val[0] == "__colour_shadow__":
                shadow_id = _uid()
                blocks[shadow_id] = {"opcode": "colour_picker", "next": None,
                                     "parent": bid, "inputs": {}, "fields": {},
                                     "shadow": True, "topLevel": False, "value": val[1]}
                inputs[key] = [1, shadow_id]

        var_name = b.get("__needs_var__")
        if var_name and var_name not in variables:
            variables[var_name] = [var_name, "0"]

        entry = {"opcode": b["opcode"], "next": None,
                 "parent": parent_id if prev_id is None else prev_id,
                 "inputs": inputs, "fields": fields, "shadow": False,
                 "topLevel": top_level and prev_id is None}
        if entry["topLevel"]:
            entry["x"] = 60
            entry["y"] = 60

        cond = b.get("__condition__")
        if cond:
            sens_opcode, menu_opcode, menu_field, menu_value = cond
            menu_id = _uid()
            sens_id = _uid()
            blocks[menu_id] = {"opcode": menu_opcode, "next": None, "parent": sens_id,
                               "inputs": {}, "fields": {menu_field: [menu_value, None]},
                               "shadow": True, "topLevel": False}
            blocks[sens_id] = {"opcode": sens_opcode, "next": None, "parent": bid,
                               "inputs": {menu_field: [1, menu_id]}, "fields": {},
                               "shadow": False, "topLevel": False}
            entry["inputs"]["CONDITION"] = [2, sens_id]

        substack = b.get("substack")
        if substack:
            child_first = _emit_chain(blocks, substack, bid, variables, top_level=False)
            if child_first:
                entry["inputs"]["SUBSTACK"] = [2, child_first]

        blocks[bid] = entry
        if prev_id is not None:
            blocks[prev_id]["next"] = bid
        prev_id = bid

    return first_id


def _build_target_json(name: str, state: dict, is_first: bool) -> dict:
    blocks: dict = {}
    variables: dict = {}
    hat_id = _uid()
    blocks[hat_id] = {"opcode": "event_whenflagclicked", "next": None, "parent": None,
                      "inputs": {}, "fields": {}, "shadow": False, "topLevel": True,
                      "x": 60, "y": 60}
    first = _emit_chain(blocks, state["script"], hat_id, variables, top_level=False)
    if first:
        blocks[hat_id]["next"] = first
        blocks[first]["parent"] = hat_id

    # Son üst düzey bloğu bul (yorumların iğneleneceği yer)
    last_top_id = hat_id
    node = hat_id
    while blocks[node].get("next"):
        node = blocks[node]["next"]
        last_top_id = node

    comments = {}
    for c in state.get("comments", []):
        cid = _uid()
        comments[cid] = {"blockId": last_top_id, "text": c["text"],
                         "x": 220, "y": 20, "width": 200, "height": 120,
                         "minimized": False}

    var_dict = {_uid(): [n, "0"] for n in variables}
    return {
        "isStage": False, "name": name, "variables": var_dict, "lists": {},
        "broadcasts": {}, "blocks": blocks, "comments": comments, "currentCostume": 0,
        "costumes": state["costumes"], "sounds": [], "volume": 100,
        "layerOrder": 1 if is_first else 2, "visible": True,
        "x": 0, "y": 0, "size": 100, "direction": 90, "draggable": False,
        "rotationStyle": "all around",
    }


def _build_project_json() -> tuple[dict, dict]:
    """Tüm kuklaları içeren proje + kullanılan tüm özel SVG varlıkları."""
    stage = {
        "isStage": True, "name": "Stage", "variables": {}, "lists": {},
        "broadcasts": {}, "blocks": {}, "comments": {}, "currentCostume": 0,
        "costumes": [{"name": "backdrop1", "dataFormat": "svg",
                      "assetId": "cd21514d0531fdffb22204e0ec5ed84a",
                      "md5ext": "cd21514d0531fdffb22204e0ec5ed84a.svg",
                      "rotationCenterX": 240, "rotationCenterY": 180}],
        "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60,
        "videoTransparency": 50, "videoState": "on", "textToSpeechLanguage": None,
    }
    targets = [stage]
    all_assets: dict[str, bytes] = {}
    uses_pen = False
    for i, (name, state) in enumerate(_SPRITES.items()):
        targets.append(_build_target_json(name, state, is_first=(i == 0)))
        all_assets.update(state.get("assets", {}))
        uses_pen = uses_pen or any(_block_uses_pen(b) for b in state["script"])

    extensions = ["pen"] if uses_pen else []
    project = {"targets": targets, "monitors": [], "extensions": extensions,
              "meta": {"semver": "3.0.0", "vm": "2.3.0", "agent": "YERINDE"}}
    return project, all_assets


def _find_scratch() -> list[str] | None:
    import glob
    import shutil
    if _IS_WINDOWS:
        # ÖNCE open_app.py'nin KANITLANMIŞ arama mantığını kullan — bu,
        # kullanıcı bazlı kurulum yolunu (%LOCALAPPDATA%\Programs\Scratch 3\)
        # da kapsıyor. Eskiden burada SADECE Program Files kontrol ediliyordu,
        # bu yüzden kullanıcı bazlı kurulumlarda Scratch bulunamıyordu —
        # "open_app ile açılabiliyor ama buradan açılamıyor" şikayetinin
        # kök nedeni buydu.
        try:
            from actions.open_app import _resolve_known_pattern
            found = _resolve_known_pattern("scratch")
            if found:
                return [found]
        except Exception:
            pass
        # Son çare — eski sabit yollar (open_app import edilemezse diye)
        for pat in (r"C:\Program Files\Scratch 3\Scratch 3.exe",
                    r"C:\Program Files (x86)\Scratch 3\Scratch 3.exe"):
            hits = glob.glob(pat)
            if hits:
                return [hits[0]]
        return None
    exe = shutil.which("scratch-desktop") or shutil.which("scratch")
    if exe:
        return [exe]
    try:
        r = subprocess.run(["flatpak", "info", "edu.mit.Scratch"],
                           capture_output=True, timeout=5)
        if r.returncode == 0:
            return ["flatpak", "run", "edu.mit.Scratch"]
    except Exception:
        pass
    return None


def _project_path() -> Path:
    from actions.code_tools import ensure_workspace_folder
    folder = ensure_workspace_folder("Scratch")
    return folder / PROJECT_FILENAME


def _scratch_is_running() -> bool:
    """Scratch GERÇEKTEN çalışıyor mu diye işletim sistemine SORAR — bir
    bayrağa güvenmez. Eski sürüm _SCRATCH_LAUNCHED bayrağı kullanıyordu:
    YERİNDE yeniden başlarsa (bayrak sıfırlanır) Scratch hâlâ AÇIK olsa
    bile YERİNDE 'hiç açmadım' sanıp GEREKSİZ YERE ikinci bir Scratch
    penceresi açıyordu — bildirdiğin hatanın kök nedeni buydu."""
    try:
        import psutil
        for p in psutil.process_iter(["name"]):
            pname = (p.info.get("name") or "").lower()
            if "scratch" in pname:
                return True
        return False
    except Exception:
        return _SCRATCH_LAUNCHED   # psutil yoksa (nadir durum) eski bayrağa düş


def load_saved_project() -> str:
    """
    'Bilgisayarımdan yükle' / 'kaydedilen dosyayı aç' — DİSKTEKİ GERÇEK
    dosyayı kontrol eder (bellekteki _SPRITES durumuna değil), böylece
    YERİNDE yeniden başlamış olsa bile (bellek sıfırlanmış olsa da) daha
    önce kaydedilmiş proje varsa onu açabilir.
    """
    path = _project_path()
    if not path.exists():
        return "Henüz kaydedilmiş bir Scratch projesi yok. Önce birkaç blok ekle."
    cmd = _find_scratch()
    if not cmd:
        return (f"Proje dosyası burada: {path}\nScratch bulunamadı — 'Dosya > "
                "Bilgisayarından Yükle' ile elle açabilirsin.")
    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if _IS_WINDOWS:
            kwargs["creationflags"] = 0x08000000
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd + [str(path)], **kwargs)
        global _SCRATCH_LAUNCHED
        _SCRATCH_LAUNCHED = True
        return f"Kaydedilen proje yükleniyor: {path.name}"
    except Exception as e:
        return f"Proje dosyası var ({path.name}) ama Scratch açılamadı: {e}"


def _focus_scratch_window() -> bool:
    """Scratch penceresini ÖNE GETİRİR (hangi pencerede olursan ol) —
    office_keys.py'de Office uygulamaları için zaten kanıtlanmış AYNI
    yöntem (Windows'ta WScript.Shell.AppActivate, Linux'ta wmctrl/xdotool)."""
    if _IS_WINDOWS:
        script = (
            "$w = New-Object -ComObject WScript.Shell; "
            "$found = Get-Process -Name 'Scratch*' -ErrorAction SilentlyContinue | "
            "         Where-Object { $_.MainWindowTitle -ne '' } | Select-Object -First 1; "
            "if ($found) { $null = $w.AppActivate($found.Id); Write-Output 'OK' } "
            "else { Write-Output 'NO' }"
        )
        try:
            r = subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", script],
                               capture_output=True, text=True, timeout=15,
                               creationflags=0x08000000)
            return (r.stdout or "").strip().startswith("OK")
        except Exception:
            return False

    import shutil
    if shutil.which("wmctrl"):
        try:
            out = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True,
                                 timeout=5).stdout.lower()
            for line in out.splitlines():
                if "scratch" in line:
                    wid = line.split()[0]
                    subprocess.run(["wmctrl", "-i", "-a", wid], timeout=5, capture_output=True)
                    return True
        except Exception:
            pass
    if shutil.which("xdotool"):
        try:
            r = subprocess.run(["xdotool", "search", "--name", "scratch"],
                               capture_output=True, text=True, timeout=5)
            ids = [i for i in (r.stdout or "").split() if i.strip()]
            if ids:
                subprocess.run(["xdotool", "windowactivate", ids[-1]], timeout=5,
                               capture_output=True)
                return True
        except Exception:
            pass
    return False


def close_scratch() -> str:
    """'Scratch'i kapat' — çalışan GERÇEK Scratch sürecini kapatır.
    ÜÇ yöntemi SIRAYLA dener (biri diğerini tamamlar):
      1) psutil (süreç adında 'scratch' arar)
      2) open_app.py'nin kanıtlanmış taskkill mekanizması
      3) Scratch penceresini ÖNE GETİRİP Alt+F4 gönderme — SEN BAŞKA BİR
         PENCEREDE OLSAN BİLE çalışır, çünkü önce Scratch'i biz kendimiz
         öne getiriyoruz (aktif pencereye körlemesine göndermiyoruz)."""
    global _SCRATCH_LAUNCHED
    closed_any = False

    try:
        import psutil
        for p in psutil.process_iter(["name", "pid"]):
            pname = (p.info.get("name") or "").lower()
            if "scratch" in pname:
                try:
                    p.terminate()
                    closed_any = True
                except Exception:
                    pass
    except ImportError:
        pass
    except Exception:
        pass

    if not closed_any and _IS_WINDOWS:
        try:
            from actions.open_app import close_app
            r = close_app("scratch")
            if "kapatıldı" in r:
                closed_any = True
        except Exception:
            pass

    if not closed_any:
        # Son çare: Scratch'i ÖNE GETİR, sonra Alt+F4 gönder — pencere
        # odakta olmasa bile bu şekilde çalışır.
        if _focus_scratch_window():
            try:
                from actions.keyboard_control import press_key
                import time
                time.sleep(0.3)   # pencerenin öne gelmesi için kısa bekleme
                press_key("alt_f4")
                closed_any = True
            except Exception:
                pass

    _SCRATCH_LAUNCHED = False
    if closed_any:
        return "Scratch kapatıldı."
    return "Açık bir Scratch penceresi bulamadım — zaten kapalı olabilir."


# ══ Yeşil bayrağı çalıştırma (kalibrasyonlu — WhatsApp arama düğmesiyle AYNI
#    kanıtlanmış yöntem: pencereye göre ORANSAL konum, Wayland-güvenli tık) ══
_GF_CFG_KEY = "scratch_green_flag_xy"


def _cfg_get(key, default=None):
    try:
        from app_config import get_app_config_value
        return get_app_config_value(key, default)
    except Exception:
        return default


def _cfg_set(key, value):
    try:
        from app_config import save_app_config
        save_app_config({key: value})
    except Exception:
        pass


def _find_scratch_window_rect() -> tuple[int, int, int, int] | None:
    """(sol, üst, genişlik, yükseklik) döner; bulunamazsa None."""
    if _IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            found = []

            def callback(hwnd, lparam):
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if "scratch" in buf.value.lower():
                    rect = wintypes.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    w, h = rect.right - rect.left, rect.bottom - rect.top
                    if w > 100 and h > 100:
                        found.append((rect.left, rect.top, w, h))
                        return False
                return True

            EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(EnumProc(callback), 0)
            return found[0] if found else None
        except Exception:
            return None

    import shutil
    if shutil.which("wmctrl"):
        try:
            out = subprocess.run(["wmctrl", "-lG"], capture_output=True,
                                 text=True, timeout=5).stdout
            for line in out.splitlines():
                if "scratch" in line.lower():
                    parts = line.split(None, 7)
                    if len(parts) >= 6:
                        x, y, w, h = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                        if w > 100 and h > 100:
                            return (x, y, w, h)
        except Exception:
            pass
    return None


def _gf_safe_click(x: int, y: int) -> tuple[bool, str]:
    if _is_wayland():
        ok1, err1 = _ydotool_move_absolute(x, y)
        if not ok1:
            return False, f"imleç taşınamadı: {err1}"
        import time
        time.sleep(0.05)
        ok2, err2 = _ydotool_click(_BTN_LEFT)
        return ok2, (err2 if not ok2 else "")
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        pyautogui.click(x, y)
        return True, ""
    except Exception as e:
        return False, str(e)


def calibrate_green_flag(seconds: int = 5, on_log=lambda m: None) -> str:
    """
    'Scratch yeşil bayrak düğmesini öğret' — kullanıcı imleci yeşil bayrağın
    üzerine götürür, konumu (pencereye göre ORANSAL) kaydedilir. WhatsApp
    arama düğmesi kalibrasyonuyla AYNI, kanıtlanmış yöntem.
    """
    try:
        import pyautogui
    except ImportError:
        return "Bunun için pyautogui gerekli: pip install pyautogui"

    on_log(f"SYS: 🎯 Scratch'i aç, imleci YEŞİL BAYRAK düğmesinin ÜZERİNE götür "
           f"— {seconds} saniye sayıyorum...")
    import time
    for i in range(seconds, 0, -1):
        on_log(f"SYS: {i}...")
        time.sleep(1)
    x, y = pyautogui.position()

    rect = _find_scratch_window_rect()
    if rect:
        wx, wy, ww, wh = rect
        rel_x = (x - wx) / ww
        rel_y = (y - wy) / wh
        if 0.0 <= rel_x <= 1.0 and 0.0 <= rel_y <= 1.0:
            _cfg_set(_GF_CFG_KEY, {"rel": [rel_x, rel_y]})
            return (f"Yeşil bayrak öğrenildi (pencereye göre %{rel_x*100:.0f}, "
                    f"%{rel_y*100:.0f}) — pencere taşınsa/boyutu değişse bile "
                    "artık doğru yeri bulur. Artık 'scratch'i çalıştır' diyebilirsin.")
        on_log("UYARI: İmleç Scratch penceresinin dışında görünüyor, mutlak "
              "konum olarak kaydediyorum.")
    _cfg_set(_GF_CFG_KEY, {"abs": [int(x), int(y)]})
    return f"Yeşil bayrak öğrenildi ({x}, {y}). Artık 'scratch'i çalıştır' diyebilirsin."


def run_green_flag(on_log=lambda m: None) -> str:
    """'Scratch'i çalıştır' — kalibre edilmiş yeşil bayrağa tıklar."""
    saved = _cfg_get(_GF_CFG_KEY)
    if not saved:
        return ("Yeşil bayrağın yerini bilmiyorum. Bir kez öğretmen yeterli: "
                "'scratch yeşil bayrak düğmesini öğret' de, Scratch'te imleci "
                "yeşil bayrağın üzerine götür.")

    if not _scratch_is_running():
        return "Scratch açık görünmüyor — önce 'scratch aç' de."

    _focus_scratch_window()
    import time
    time.sleep(0.2)

    rect = _find_scratch_window_rect()
    if isinstance(saved, dict) and "rel" in saved and rect:
        wx, wy, ww, wh = rect
        click_x = int(wx + saved["rel"][0] * ww)
        click_y = int(wy + saved["rel"][1] * wh)
    elif isinstance(saved, dict) and "abs" in saved:
        click_x, click_y = saved["abs"]
    else:
        return "Kayıtlı yeşil bayrak konumu bozuk görünüyor — yeniden öğretir misin?"

    ok, err = _gf_safe_click(click_x, click_y)
    if not ok:
        return f"Yeşil bayrağa tıklanamadı: {err}"
    return "Çalıştırılıyor! 🏳️"


def _save_and_open(force_relaunch: bool = False) -> str:
    global _SCRATCH_LAUNCHED
    path = _project_path()

    project, assets = _build_project_json()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project, ensure_ascii=False))
        for md5ext, data in assets.items():
            z.writestr(md5ext, data)

    total_blocks = sum(_count_blocks(s["script"]) for s in _SPRITES.values())
    cmd = _find_scratch()
    if not cmd:
        return (f"Proje güncellendi: {path}\nScratch bulunamadı — dosyayı Scratch'te "
                "(scratch.mit.edu) 'Dosya > Bilgisayarından Yükle' ile açabilirsin.")

    if _scratch_is_running() and not force_relaunch:
        return (f"Proje güncellendi ({path.name}) — Scratch zaten açık, tekrar "
                "açmadım. Son hâli görmek için 'Dosyadan Yükle' ile aynı dosyayı "
                "aç (Scratch dış değişiklikleri otomatik yenilemiyor).")

    try:
        kwargs = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if _IS_WINDOWS:
            kwargs["creationflags"] = 0x08000000
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd + [str(path)], **kwargs)
        _SCRATCH_LAUNCHED = True
        return f"Scratch açıldı: {total_blocks} blokluk betik, {len(_SPRITES)} kukla hazır ({path.name})."
    except Exception as e:
        return f"Proje kaydedildi ({path.name}) ama Scratch açılamadı: {e}"


def _count_blocks(script: list[dict]) -> int:
    n = 0
    for b in script:
        n += 1
        if "substack" in b:
            n += _count_blocks(b["substack"])
    return n


# ══ Analiz / Onarım: var olan bir .sb3 dosyasını incele ve düzelt ══════════
def analyze_project(path_str: str = "") -> str:
    """
    Bir .sb3 dosyasını (varsayılan: bizim kendi projemiz) açar, KOPUK
    REFERANSLARI (var olmayan bloğa işaret eden next/parent) ve ERİŞİLEMEZ
    BLOKLARI (hiçbir yeşil bayrak/olay zincirine bağlı olmayan) bulur.
    Kopuk referansları OTOMATİK DÜZELTİR (None yapar, Scratch'in yüklerken
    çökmesini önler) ve bir özet rapor döner. Kullanıcının BAŞKA BİR
    yerden aldığı .sb3 dosyaları için de çalışır (tam yol verilirse).
    """
    path = Path(path_str.strip()) if path_str and path_str.strip() else _project_path()
    if not path.exists():
        return f"Dosya bulunamadı: {path}"
    try:
        with zipfile.ZipFile(path) as z:
            project = json.loads(z.read("project.json"))
    except Exception as e:
        return f"Dosya okunamadı ya da geçerli bir Scratch projesi değil: {e}"

    issues: list[str] = []
    fixed = 0
    for target in project.get("targets", []):
        blocks = target.get("blocks", {})
        if not isinstance(blocks, dict):
            continue
        name = target.get("name", "?")

        for bid, b in list(blocks.items()):
            if not isinstance(b, dict):
                continue
            nxt = b.get("next")
            if nxt and nxt not in blocks:
                issues.append(f"{name}: '{bid[:8]}…' bloğunun 'next' referansı kopuktu — düzeltildi")
                b["next"] = None
                fixed += 1
            par = b.get("parent")
            if par and par not in blocks:
                issues.append(f"{name}: '{bid[:8]}…' bloğunun 'parent' referansı kopuktu — düzeltildi")
                b["parent"] = None
                fixed += 1

        reachable: set[str] = set()

        def walk(bid):
            while bid and bid in blocks and bid not in reachable:
                reachable.add(bid)
                b = blocks[bid]
                for inp in b.get("inputs", {}).values():
                    if isinstance(inp, list) and len(inp) == 2 and isinstance(inp[1], str):
                        if inp[1] in blocks:
                            walk(inp[1])
                bid = b.get("next")

        for bid, b in blocks.items():
            if isinstance(b, dict) and b.get("topLevel"):
                walk(bid)
        orphans = [bid for bid, b in blocks.items()
                  if isinstance(b, dict) and bid not in reachable and not b.get("shadow")]
        if orphans:
            issues.append(f"{name}: {len(orphans)} blok hiçbir yeşil bayrak/olay zincirine "
                          "bağlı değil (erişilemez — silinmedi, sadece bildiriliyor)")

    if not issues:
        return f"'{path.name}' incelendi — yapısal bir sorun bulunamadı, temiz görünüyor."

    if fixed:
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("project.json", json.dumps(project, ensure_ascii=False))

    report = "\n".join(f"  • {i}" for i in issues[:10])
    more = f"\n  ... ve {len(issues) - 10} sorun daha" if len(issues) > 10 else ""
    fix_note = f"\n\n{fixed} kopuk referans otomatik düzeltilip dosyaya kaydedildi." if fixed else ""
    return f"'{path.name}' incelendi:\n{report}{more}{fix_note}"


# ── Dış API ─────────────────────────────────────────────────────────────────
def scratch_command(action: str, value: str = "", text: str = "",
                    times: str = "", key: str = "") -> str:
    action = (action or "").lower().strip()

    if action == "clear":
        _cur()["script"] = []
        _cur()["container_stack"] = []
        return f"'{_CURRENT_SPRITE}' kuklasının betiği temizlendi — sıfırdan başlayabiliriz."

    if action == "reopen":
        if not any(s["script"] for s in _SPRITES.values()):
            return "Henüz blok eklemedin. Örnek: 'scratch'te 10 adım git'."
        return _save_and_open(force_relaunch=True)

    if action == "load":
        return load_saved_project()

    if action == "close":
        return close_scratch()

    if action == "calibrate_green_flag":
        return calibrate_green_flag()

    if action == "run_green_flag":
        return run_green_flag()

    if action == "run":
        if not any(s["script"] for s in _SPRITES.values()):
            return "Henüz blok eklemedin. Örnek: 'scratch'te 10 adım git'."
        return _save_and_open()

    if action == "add_sprite":
        raw = " ".join(p for p in (key, value, text) if p).strip()
        name, shape, color, color_explicit = _split_name_shape_color(raw)
        msg = add_sprite(name, shape, color, color_explicit)
        return f"{msg} {_save_and_open()}"

    if action == "delete_sprite":
        msg = delete_sprite(key or text or value)
        if "silindi" in msg:
            return f"{msg} {_save_and_open()}"
        return msg   # kukla bulunamadı / son kukla — dosyaya dokunma

    if action == "switch_sprite":
        # Sadece DAHİLİ "hangi kuklaya komut ekleniyor" durumunu değiştirir —
        # projenin kendisi değişmediği için dosyayı yeniden kaydetmeye/
        # Scratch'i güncellemeye gerek yok.
        return switch_sprite(key or text or value)

    if action == "draw_sprite":
        # "kukla çiz: kırmızı yıldız" ya da "kukla çiz köpek" gibi — hem
        # isim hem şekil/renk AYNI serbest metinden doğru ayrıştırılır.
        raw = " ".join(p for p in (key, value, text) if p).strip()
        name, shape, color, color_explicit = _split_name_shape_color(raw)
        msg = add_sprite(name, shape, color, color_explicit)
        return f"{msg} {_save_and_open()}"

    if action == "add_costume":
        raw = " ".join(p for p in (value, text, key) if p).strip()
        _, shape, color, color_explicit = _split_name_shape_color(raw)
        msg = add_costume(shape, color, color_explicit)
        return f"{msg} {_save_and_open()}"

    if action == "add_comment":
        msg = add_comment(text or value)
        if "eklendi" in msg:
            return f"{msg} {_save_and_open()}"
        return msg   # henüz blok yoksa dosyaya dokunma

    if action == "analyze":
        return analyze_project(value or text)

    state = _cur()
    target_list = state["container_stack"][-1]["substack"] if state["container_stack"] else state["script"]

    if action == "repeat_start":
        try:
            n = int(float(times or value or 10))
        except Exception:
            n = 10
        block = _block_repeat(n, [])
        target_list.append(block)
        state["container_stack"].append(block)
        return f"'{n} kere tekrarla' başladı ({_CURRENT_SPRITE}) — içine ne olacağını söyle, bitince 'blok bitti' de."

    if action == "forever_start":
        block = _block_forever([])
        target_list.append(block)
        state["container_stack"].append(block)
        return "'Sonsuza kadar tekrarla' başladı — içine ne olacağını söyle, bitince 'blok bitti' de."

    if action == "if_touching_edge_start":
        block = _block_if_touching_edge([])
        target_list.append(block)
        state["container_stack"].append(block)
        return "'Eğer kenara değerse' başladı — içine ne olacağını söyle, bitince 'blok bitti' de."

    if action == "if_key_pressed_start":
        block = _block_if_key_pressed(key or value or "space", [])
        target_list.append(block)
        state["container_stack"].append(block)
        return f"'Eğer {key or value or 'boşluk'} tuşuna basılırsa' başladı — bitince 'blok bitti' de."

    if action == "block_end":
        if not state["container_stack"]:
            return "Kapatılacak açık bir blok (tekrarla/eğer) yok."
        state["container_stack"].pop()
        kalan = f" ({len(state['container_stack'])} blok daha açık)" if state["container_stack"] else ""
        return f"Blok kapatıldı.{kalan} Yeni bloklar artık {'bir üstteki bloğa' if state['container_stack'] else 'ana betiğe'} ekleniyor."

    if action == "set_variable":
        name = key or "değişken"
        block = _block_set_variable(name, value or "0")
        target_list.append(block)
        result = _save_and_open()
        return f"'{name}' değişkeni {value or '0'} yapıldı. {result}"

    if action == "change_variable":
        name = key or "değişken"
        try:
            delta = float(value or 1)
        except Exception:
            delta = 1
        block = _block_change_variable(name, delta)
        target_list.append(block)
        result = _save_and_open()
        return f"'{name}' değişkeni {delta:+g} değiştirildi. {result}"

    builder = BUILDERS.get(action)
    if not builder:
        return ("Bu Scratch komutunu bilmiyorum. Örnekler: '10 adım git', "
                "'90 derece sağa dön', 'merhaba de', '5 kere tekrarla', "
                "'kukla ekle', 'kukla çiz kırmızı yıldız', 'yorum ekle bu bölüm zıplatıyor'.")

    try:
        if action in ("say", "think"):
            block = builder(text or value or "Merhaba!")
        elif action == "say_for":
            block = _block_say(text or value or "Merhaba!", 2)
        elif action == "pen_color":
            block = builder(value or text or "mavi")
        elif action in ("show", "hide", "next_costume", "stop_all",
                        "pen_down", "pen_up", "pen_clear", "pen_stamp"):
            block = builder()
        elif action in ("goto", "glide"):
            block = builder(value or "0,0")
        else:
            block = builder(float(value or 10))
    except Exception:
        return "Değeri anlayamadım — 'scratch'te 10 adım git' gibi söyler misin?"

    target_list.append(block)
    result = _save_and_open()
    total = sum(_count_blocks(s["script"]) for s in _SPRITES.values())
    return f"Blok eklendi ({total}, {_CURRENT_SPRITE}). {result}"


def _parse_shape_color(text: str) -> tuple[str, str]:
    """'kırmızı yıldız' ya da 'yıldız kırmızı' gibi serbest metinden
    (renk, şekil) çıkarır — sıra önemli değil."""
    text = (text or "").lower().strip()
    words = text.replace(",", " ").split()
    color = next((w for w in words if w in _PEN_COLORS), "mavi")
    shape = next((w for w in words if w in _SHAPES or w in ("kutu", "ucgen", "yildiz")), "daire")
    return color, shape


def _split_name_shape_color(text: str) -> tuple[str, str, str, bool]:
    """'köpek kırmızı yıldız' gibi serbest bir ifadeden (İSİM, şekil, renk,
    renk_açıkça_belirtildi_mi) çıkarır — renk/şekil OLARAK TANINAN
    kelimeler çıkarılır, GERİYE KALAN kelimeler kuklanın adı sayılır. Bu,
    'köpek kuklası ekle' dediğinde 'köpek'in şekil/renk sanılıp yok
    sayılması yerine doğru şekilde İSİM olarak kullanılmasını sağlar
    (önceki hatanın kök nedeni buydu). 4. değer (renk_açık), kullanıcı
    AÇIKÇA bir renk söylediyse True döner — bu durumda kütüphaneden GERÇEK
    (sabit renkli) bir görsel yerine, kullanıcının istediği RENKTE elle
    çizilmiş şekil önceliklidir."""
    shape_aliases = {"kutu": "kare", "ucgen": "üçgen", "yildiz": "yıldız"}
    words = (text or "").lower().replace(",", " ").split()
    color = None
    shape = None
    name_words = []
    for w in words:
        if w in _PEN_COLORS and color is None:
            color = w
        elif (w in _SHAPES or w in shape_aliases) and shape is None:
            shape = shape_aliases.get(w, w)
        else:
            name_words.append(w)
    name = " ".join(name_words).strip()
    return name, (shape or "daire"), (color or "mavi"), (color is not None)
