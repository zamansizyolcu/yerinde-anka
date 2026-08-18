"""
actions/blockly_solver.py — Blockly Games'in Labirent bulmacasını GERÇEK
Blockly bloklarına dönüştürüp tarayıcıda ÇÖZDÜRME.

DÜRÜST NOT (bu özelliğin sınırları): Bu modül Selenium ile GERÇEK bir
tarayıcıyı uzaktan kumanda eder. Bu, Scratch entegrasyonumuz gibi
kendi kendine yeten bir dosya biçimi DEĞİL — canlı bir web sayfasının
JS durumuna müdahale ediyoruz. Bu yüzden:
  • Chrome kurulu olmalı (webdriver-manager sürücüyü otomatik indirir).
  • Blockly Games sürümü değişirse (iç API'ler güncellenirse) kırılabilir.
  • İlk denemede %100 çalışacağının garantisi YOK — çalışmazsa tarayıcı
    konsolundaki (F12) hatayı görüp birlikte düzeltmemiz gerekebilir.

KULLANILAN GERÇEK API'LER (varsayım DEĞİL, gerçek kaynak koddan doğrulandı):
  • Blockly.mainWorkspace   — Blockly'nin KENDİ genel API'si, oyunun kendi
                              minify edilmiş iç değişken adından bağımsız.
  • Blockly.Xml.textToDom / domToWorkspace — standart Blockly XML enjeksiyonu.
  • document.getElementById("runButton")   — gerçek maze.html kaynağında
                              doğrulandı ("runButton" id'si birebir var).

ÇÖZÜM VERİSİ: Kullanıcının kendi ders materyalinden (görsel olarak
doğrulanmış, kendisinin sınıfta test ettiği) çıkarıldı — TAHMİN EDİLMEDİ.
"""

from __future__ import annotations

import time

_driver = None   # Selenium tarayıcısı — oturum boyunca TEK sefer açılır


# ══ Labirent seviye çözümleri ═══════════════════════════════════════════════
# Blok ağacı biçimi:
#   ("move",)                                    — ileri git
#   ("turn", "left"|"right")                      — sola/sağa dön
#   ("forever", [alt_bloklar])                     — kadar tekrar et... yap
#   ("if", "forward"|"left"|"right", [yap])        — eğer yol varsa... yap
#   ("ifelse", "forward"|"left"|"right", [yap], [değilse])
MAZE_LEVELS: dict[int, list] = {
    1: [("move",), ("move",)],
    2: [("move",), ("turn", "left"), ("move",), ("turn", "right"), ("move",)],
    3: [("forever", [("move",)])],
    4: [("forever", [("move",), ("turn", "left"), ("move",), ("turn", "right")])],
    5: [("move",), ("move",), ("turn", "left"), ("forever", [("move",)])],
    6: [("forever", [("move",), ("if", "left", [("turn", "left"), ("move",)])])],
    7: [("forever", [("move",), ("if", "right", [("turn", "right"), ("move",)])])],
    8: [("move",), ("forever", [
        ("if", "forward", [("move",)]),
        ("if", "left", [("turn", "left"), ("move",)]),
        ("if", "right", [("turn", "right"), ("move",)]),
    ])],
    9: [("forever", [
        ("if", "forward", [("move",)]),
        ("ifelse", "left", [("turn", "left"), ("move",)], [("turn", "right")]),
    ])],
    10: [("forever", [
        ("ifelse", "right",
         [("ifelse", "forward", [("turn", "right")],
           [("ifelse", "left", [("turn", "left")], [("turn", "right")])])],
         [("if", "left", [("turn", "left")])]),
        ("move",),
    ])],
}
# 10. seviyenin dosyada bulunan İKİNCİ (alternatif) çözümü
MAZE_LEVEL_10_ALT = [("forever", [
    ("ifelse", "left", [("turn", "left"), ("move",)],
     [("ifelse", "forward", [("move",)],
       [("ifelse", "right", [("turn", "right")],
         [("turn", "right"), ("turn", "right")])])]),
])]

_DIR_FIELD = {"left": "isPathLeft", "right": "isPathRight", "forward": "isPathForward"}
_TURN_FIELD = {"left": "turnLeft", "right": "turnRight"}


# ══ Blok ağacından Blockly XML üretimi ═══════════════════════════════════════
_id_counter = 0


def _next_id() -> str:
    global _id_counter
    _id_counter += 1
    return f"blk{_id_counter}"


def _block_to_xml(node: tuple) -> str:
    kind = node[0]
    if kind == "move":
        return f'<block type="maze_moveForward" id="{_next_id()}">{{NEXT}}</block>'
    if kind == "turn":
        direction = _TURN_FIELD[node[1]]
        return (f'<block type="maze_turn" id="{_next_id()}">'
                f'<field name="DIR">{direction}</field>{{NEXT}}</block>')
    if kind == "forever":
        inner = _chain_to_xml(node[1])
        return (f'<block type="maze_forever" id="{_next_id()}">'
                f'<statement name="DO">{inner}</statement>{{NEXT}}</block>')
    if kind == "if":
        direction = _DIR_FIELD[node[1]]
        inner = _chain_to_xml(node[2])
        return (f'<block type="maze_if" id="{_next_id()}">'
                f'<field name="DIR">{direction}</field>'
                f'<statement name="DO">{inner}</statement>{{NEXT}}</block>')
    if kind == "ifelse":
        direction = _DIR_FIELD[node[1]]
        do_inner = _chain_to_xml(node[2])
        else_inner = _chain_to_xml(node[3])
        return (f'<block type="maze_ifElse" id="{_next_id()}">'
                f'<field name="DIR">{direction}</field>'
                f'<statement name="DO">{do_inner}</statement>'
                f'<statement name="ELSE">{else_inner}</statement>{{NEXT}}</block>')
    raise ValueError(f"Bilinmeyen blok türü: {kind}")


def _chain_to_xml(nodes: list) -> str:
    """Sıralı blokları <next> ile zincirler (Scratch köprüsündeki AYNI mantık)."""
    if not nodes:
        return ""
    head_xml = _block_to_xml(nodes[0])
    rest_xml = _chain_to_xml(nodes[1:])
    next_xml = f"<next>{rest_xml}</next>" if rest_xml else ""
    return head_xml.replace("{NEXT}", next_xml)


# ══ Çözümü SESLE/YAZIYLA anlatma (tarayıcı otomasyonu OLMADAN — %100 güvenilir) ══
# Blockly'nin bu sürümünün iç API'si tamamen gizlenmiş (gerçek kullanıcı
# testinde doğrulandı) olduğu için otomatik blok yerleştirme güvenilir
# çalışmıyor. Bunun yerine, AYNI doğrulanmış çözüm verisini kullanarak
# çözümü DOĞAL TÜRKÇE olarak anlatıyoruz — öğrenci blokları kendi sürükler,
# oyunun kendi (bizden bağımsız, her zaman güvenilir) doğrulaması çalışır.
_DIR_TR = {"left": "solda", "right": "sağda", "forward": "önde"}
_TURN_TR = {"left": "sola dön", "right": "sağa dön"}


def _describe_chain(nodes: list) -> list[str]:
    lines = []
    for node in nodes:
        kind = node[0]
        if kind == "move":
            lines.append("ileri git")
        elif kind == "turn":
            lines.append(_TURN_TR[node[1]])
        elif kind == "forever":
            inner = ", sonra ".join(_describe_chain(node[1]))
            lines.append(f"hedefe ulaşana kadar şunu tekrarla: {inner}")
        elif kind == "if":
            inner = ", sonra ".join(_describe_chain(node[2]))
            lines.append(f"eğer {_DIR_TR[node[1]]} yol varsa: {inner}")
        elif kind == "ifelse":
            yap = ", sonra ".join(_describe_chain(node[2]))
            degilse = ", sonra ".join(_describe_chain(node[3]))
            lines.append(f"eğer {_DIR_TR[node[1]]} yol varsa: {yap}; değilse: {degilse}")
    return lines


def describe_maze_level(level: int, use_alt: bool = False) -> str:
    """
    'labirentin 3. seviyesinin çözümünü söyle' — tarayıcı/Selenium GEREKTİRMEZ,
    sadece doğrulanmış çözümü doğal Türkçe cümlelerle anlatır. Öğrenci
    blokları kendi sürükler, oyunun kendi doğrulaması (bizden bağımsız)
    her zaman güvenilir şekilde çalışır.
    """
    if use_alt and level == 10:
        blocks = MAZE_LEVEL_10_ALT
    else:
        blocks = MAZE_LEVELS.get(level)
    if not blocks:
        return f"Labirent için {level}. seviyenin çözümünü bilmiyorum (bilinen: 1-10)."

    steps = _describe_chain(blocks)
    adim_metni = ", sonra ".join(f"{i+1}) {s}" for i, s in enumerate(steps))
    varyant = " (alternatif çözüm)" if use_alt else ""
    return f"Labirent {level}. seviye{varyant} çözümü: {adim_metni}."


def level_to_xml(level_blocks: list) -> str:
    global _id_counter
    _id_counter = 0
    body = _chain_to_xml(level_blocks)
    # Üst düzey bloğa AÇIK bir x/y konumu ver — yoksa Blockly varsayılan bir
    # yere koyabiliyor, bu da görsel olarak "bağlantısız duruyor" izlenimi
    # veriyordu (gerçek kullanıcı testinde gözlemlendi).
    body = body.replace('<block type=', '<block x="70" y="70" type=', 1)
    return f'<xml xmlns="https://developers.google.com/blockly/xml">{body}</xml>'


# ══ Tarayıcı yönetimi (Selenium) ═════════════════════════════════════════════
def _get_driver():
    global _driver
    if _driver is not None:
        try:
            _ = _driver.current_url   # tarayıcı hâlâ açık mı kontrol et
            return _driver
        except Exception:
            _driver = None

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    _driver = webdriver.Chrome(service=service, options=options)
    return _driver


def _maze_url(level: int | None = None) -> str:
    """
    ARTIK file:// KULLANMIYOR — Chrome her file:// adresini BENZERSİZ bir
    güvenlik kaynağı saydığı için sayfa/seviye geçişlerinde "Unsafe attempt
    to load URL... unique security origins" hatası veriyordu (gerçek
    kullanıcı testinde bulundu). blockly_games.py'nin yerel HTTP
    sunucusunu (aynı, TEK sunucu — oturumda bir kez açılır) kullanıyoruz.

    'level' verilirse DOĞRUDAN o seviyeye gider — gerçek kullanıcı
    testinde URL'nin '?lang=tr&level=N&skin=0' biçiminde olduğu görüldü;
    seviye linkine TIKLAMAK yerine bunu doğrudan URL'ye koymak daha
    güvenilir (tıklama+geçiş zamanlamasına bağımlı kalmıyoruz).
    """
    from actions.blockly_games import _game_url
    base = _game_url("maze.html")
    if level is not None:
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}lang=tr&level={level}&skin=0"
    return base


def solve_maze_level(level: int, use_alt: bool = False) -> str:
    """
    'labirent 3. seviyeyi çöz' → Labirent sayfasını açar (ya da zaten
    açıksa kullanır), o seviyenin GERÇEK çözümünü Blockly bloklarına
    çevirip çalışma alanına ekler, Çalıştır'a basar.
    """
    if use_alt and level == 10:
        blocks = MAZE_LEVEL_10_ALT
    else:
        blocks = MAZE_LEVELS.get(level)
    if not blocks:
        return f"Labirent için {level}. seviyenin çözümünü bilmiyorum (bilinen: 1-10)."

    xml = level_to_xml(blocks)

    try:
        driver = _get_driver()
    except Exception as e:
        return (f"Tarayıcı başlatılamadı: {e}\n"
                "Chrome kurulu mu? 'pip install selenium webdriver-manager' yapıldı mı?")

    try:
        # DOĞRUDAN doğru seviyeye git (URL parametresiyle) — artık seviye
        # linkine TIKLAYIP geçiş animasyonunun bitmesini beklemek yerine,
        # sayfa DAHA İLK YÜKLENİRKEN doğru seviyede açılıyor. Bu, gerçek
        # kullanıcı testinde görülen "tıklama+geçiş zamanlaması" belirsizliğini
        # tamamen ortadan kaldırıyor.
        driver.get(_maze_url(level=level))
        time.sleep(2.5)   # sayfanın/Blockly'nin tam yüklenmesini bekle

        escaped_xml = xml.replace("`", "\\`")
        # JS TARAFINDA da Blockly.mainWorkspace hazır olana kadar kısa bir
        # süre bekleyip (yeniden kurulma anına denk gelmeyelim diye),
        # enjeksiyondan SONRA gerçekten kaç blok eklendiğini SAYIP döndürüyoruz
        # — böylece "sessizce başarısız oldu mu" sorusuna kör tahmin yerine
        # gerçek bir sayıyla cevap verebiliyoruz.
        script = f"""
            var xmlText = `{escaped_xml}`;
            if (typeof Blockly === 'undefined' || !Blockly.mainWorkspace) {{
                return -1;
            }}
            var xmlDom = Blockly.Xml.textToDom(xmlText);
            Blockly.mainWorkspace.clear();
            Blockly.Xml.domToWorkspace(xmlDom, Blockly.mainWorkspace);
            return Blockly.mainWorkspace.getAllBlocks(false).length;
        """
        block_count = driver.execute_script(script)

        if block_count in (0, -1, None):
            # İlk deneme başarısız — muhtemelen tam bu anda çalışma alanı
            # yeniden kuruluyordu. Biraz daha bekleyip BİR KEZ daha dene.
            time.sleep(2)
            block_count = driver.execute_script(script)

        if block_count in (0, -1, None):
            return (f"Bloklar eklenemedi (Blockly çalışma alanı hazır olmadı ya "
                    "da bulunamadı). Tarayıcıda F12 > Console'da 'Blockly' yazıp "
                    "Enter'a basarsan, tanımlı olup olmadığını görebiliriz.")

        time.sleep(0.5)

        run_btn = driver.find_element("id", "runButton")
        run_btn.click()
        return f"Labirent {level}. seviye çözülüyor — {block_count} blok eklendi, çalıştırıldı."
    except Exception as e:
        return (f"Bloklar eklenirken/çalıştırılırken bir sorun oldu: {e}\n"
                "Tarayıcıda F12 ile konsolu açıp hatayı paylaşırsan birlikte düzeltiriz.")
