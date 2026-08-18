"""
core/stt_correction.py — Ses tanıma (STT) yanlış anlama filtresi.

SORUN: Whisper/Vosk gibi motorlar bazı Türkçe kelimeleri, birbirine çok
yakın telaffuzları yüzünden karıştırabiliyor — en sık görülenler:
  • "sahneyi temizle"  → "saniyeyi temizle" duyuluyor (3B Tasarım Stüdyosu /
    Blender sahne temizleme komutları çalışmıyor)
  • "kodlama"          → "kotlama" duyuluyor (Yerinde Kodlama Aracı /
    kukla kodlama atölyesi komutları çalışmıyor)
  • "kukla"            → "kutla" duyuluyor
  • "tasarım"          → "tasarim" (noktasız ı yerine düz i) duyuluyor
  • "stüdyo"           → "studyo" (Türkçe harfler düşüyor)
intent_parser tamamen regex tabanlı olduğu için bu küçük sapmalar komutun
HİÇ tanınmamasına yol açıyor ve istek boşuna LLM'e "sohbet" olarak gidiyor.

ÇÖZÜM — iki aşamalı, SADECE YEDEK bir düzeltme katmanı:
  1) Bilinen/sık karışan ifadeler için elle yazılmış, DAR KAPSAMLI regex
     düzeltmeleri. Her biri bağlama duyarlı yazıldı (ör. "kutla" sadece
     "ekle/sil/seç/çiz/geç" gibi bir kodlama-aracı fiiliyle yan yana
     geldiğinde düzeltilir) — böylece "doğum günümü kutla" gibi gerçek
     cümleler ETKİLENMEZ.
  2) Yukarıdakiler yetmezse: metinde bu araçlarla (3B Tasarım Stüdyosu,
     Robot Tasarım Atölyesi, Robotik Simülatör, Yerinde/Kukla Kodlama
     Aracı, fare/klavye kısayolları) ilgili bir ipucu varsa, metindeki
     kelimeler bu araçlara özgü bir anahtar-kelime sözlüğüyle (difflib)
     karşılaştırılır; SADECE güçlü ve TEK bir eşleşme bulunursa düzeltilir.

ÖNEMLİ — GÜVENLİK: core/intent_parser.py ÖNCE düzeltilmemiş orijinal
metni dener; SADECE o hiçbir komutla eşleşmezse bu modül çağrılıp metin
düzeltilir ve TEKRAR denenir. Yani hâlihazırda doğru çalışan hiçbir komutun
davranışı bundan etkilenmez — bu tamamen EK bir güvenlik ağıdır, mevcut
davranışı asla değiştirmez.

Bu modül hem Ollama (çevrimdışı, core/intent_parser üzerinden) hem de
Gemini modunda (dolaylı olarak — bkz. tool_defs.py'deki "sık karışan
telaffuzlar" notları, çünkü Gemini kendi ses-metin dönüşümünü kendisi
yapıyor ve buraya bir Python katmanı giremiyor) düşünülerek tasarlandı.
"""

from __future__ import annotations

import difflib
import re

# ── 1) Bilinen karışıklıklar (elle yazılmış, bağlama duyarlı) ───────────────
# Liste sırası önemlidir: daha spesifik/riskli olanlar üstte, düzeltmeler
# sırayla uygulanır.
_KNOWN_FIXES: list[tuple[re.Pattern, str]] = [
    # "sahne" ⇄ "saniye" — EN SIK karışan çift. "Saniyeyi temizle/boşalt/sil"
    # anlamca saçma bir cümle olduğundan düzeltme pratikte risksizdir.
    (re.compile(r"\bsaniy(?:ey)?i\b(?=(?:.{0,15}?\b(?:temizle|boşalt|sil)\b))",
                re.IGNORECASE), "sahneyi"),
    (re.compile(r"\bsaniyesini\b(?=(?:.{0,15}?\btemizle\b))", re.IGNORECASE),
     "sahnesini"),
    (re.compile(r"\bsaniyedeki\b", re.IGNORECASE), "sahnedeki"),

    # "kodlama" ⇄ "kotlama" — "kotlama" geçerli bir Türkçe kelime olmadığı
    # için (Kotlin programlama diliyle karıştırılmadıkça, ki o da ayrı bir
    # bağlamda "Kotlin" olarak geçer) her yerde güvenle düzeltilebilir.
    (re.compile(r"\bkotlama(\w*)", re.IGNORECASE), r"kodlama\1"),
    (re.compile(r"\bkod\s+lama(\w*)", re.IGNORECASE), r"kodlama\1"),

    # "kukla" ⇄ "kutla" — SADECE Kodlama Aracı fiilleriyle (ekle/sil/seç/
    # çiz/geç) yan yana geldiğinde düzeltilir; kutlama/kutla gibi gerçek
    # kelime kullanan cümleler etkilenmez.
    (re.compile(r"\bkutla(y[ıi]|s[ıi]n[ıi]|ya)?\b(?=\s*(?:ekle|sil|seç|çiz|geç)\b)",
                re.IGNORECASE), r"kukla\1"),

    # "tasarım" ASCII kayması: noktasız "ı" yerine düz "i" duyulması —
    # bazı desenler (ör. 3B Tasarım Stüdyosu açma) yalnızca doğru yazımı
    # tanıyor.
    (re.compile(r"\btasarim(\w*)\b", re.IGNORECASE), r"tasarım\1"),

    # "stüdyo" ASCII kayması: Türkçe "ü" harfinin düşmesi.
    (re.compile(r"\bstudyo(\w*)\b", re.IGNORECASE), r"stüdyo\1"),

    # "küp" ASCII kayması (silindir/küre/koni gibi diğer şekillerde zaten
    # ASCII alternatifleri regex'te var — sadece "küp" eksikti).
    (re.compile(r"\bkup\b(?=\s*(?:ekle|ekler|oluştur|olustur)\b)", re.IGNORECASE),
     "küp"),

    # "robotik" kelimesinin ikiye bölünmesi ("robot ik").
    (re.compile(r"\brobot\s+ik\b", re.IGNORECASE), "robotik"),

    # "yerinde" komutunun bölünmesi — SADECE hemen ardından "kodlama"
    # geldiğinde düzeltilir (başka bağlamda "yer inde" anlamsızdır zaten).
    (re.compile(r"\byer\s+inde(?=\s+kodlama)", re.IGNORECASE), "yerinde"),

    # ── Klavye/fare kısayolları: sık İngilizce terim kaymaları ─────────────
    (re.compile(r"\beskeyp\b|\beskape\b", re.IGNORECASE), "escape"),
    (re.compile(r"\bvindovs\b|\bvindoz\b", re.IGNORECASE), "windows"),
]

# ── 2) Zayıf/gürültülü eşleşmeler için yedek sözlük (difflib) ──────────────
# Yukarıdaki bilinen düzeltmeler işe yaramazsa, ama metinde bu araçlarla
# ilgili bir İPUCU varsa devreye girer. Sıradan sohbet cümlelerinde boşuna
# çalışmasın diye bu ön-kontrol şart.
_DOMAIN_HINTS = re.compile(
    r"tasar|atölye|atolye|stüdyo|studyo|robot|kodlam|simülat|simulat|"
    r"karakter|sahne|\bblok",
    re.IGNORECASE,
)

# Bu araçların komutlarında geçen, düzeltme hedefi olabilecek anahtar
# kelimeler (kısa/çok genel kelimeler KASITLI OLARAK dışarıda tutuldu —
# yanlış pozitif riskini azaltır). NOT: "kukla" BİLEREK burada yok — gerçek
# bir kelime olan "kutla/kutlama" ile karıştırılma riski çok yüksek; o
# çift yalnızca yukarıdaki bağlama duyarlı regex ile düzeltiliyor. Aynı
# nedenle "saniye" de yok (gerçek ve sık kullanılan bir kelime).
_VOCAB = [
    "sahneyi", "sahnesini", "sahnedeki", "temizle", "boşalt",
    "kodlama", "kodlamayı", "kodlamasını",
    "tasarım", "tasarımı", "tasarımını", "stüdyosunu", "stüdyosu",
    "atölyesini", "atölyesi", "atölyesinde",
    "robotik", "simülatörünü", "simülatör", "simülasyonu",
    "karakter", "karakteri", "bloğu",
]
_VOCAB_LOWER = sorted({w.lower() for w in _VOCAB})

_WORD_RE = re.compile(r"[\wçğıöşüÇĞİÖŞÜ]+|[^\wçğıöşüÇĞİÖŞÜ]+")


def _fuzzy_fix(word: str) -> str | None:
    """Tek bir kelimeyi sözlüğe karşı dener. SADECE güçlü (>=0.8 benzerlik)
    ve TEK bir eşleşme varsa düzeltilmiş halini döner; aksi halde None
    (kelimeye dokunulmaz — belirsiz durumlarda düzeltmemek daha güvenlidir)."""
    low = word.lower()
    if len(low) < 5 or low in _VOCAB_LOWER:
        return None
    matches = difflib.get_close_matches(low, _VOCAB_LOWER, n=2, cutoff=0.8)
    if len(matches) == 1 and matches[0] != low:
        return matches[0]
    return None


# Son çağrıda gerçekten bir düzeltme yapıldıysa buraya yazılır — GUI/log
# katmanı bunu okuyup kullanıcıya "şunu şöyle anladım" diye gösterebilir.
_last_correction: dict | None = None


def get_last_correction() -> dict | None:
    """normalize_stt_text() bir önceki çağrıda gerçekten metni değiştirdiyse
    {'original': ..., 'corrected': ...} döner; değiştirmediyse None."""
    return _last_correction


def normalize_stt_text(text: str) -> str:
    """
    detect_intent() ilk (düzeltilmemiş) denemede eşleşme bulamazsa çağrılır.
    Bilinen düzeltmeleri uygular; hâlâ değişiklik yoksa ve metinde bu
    araçlarla ilgili bir ipucu varsa, tek-kelime bulanık eşleştirmeyi dener.
    """
    global _last_correction
    original = text
    fixed = text

    for pattern, repl in _KNOWN_FIXES:
        fixed = pattern.sub(repl, fixed)

    if fixed == original and _DOMAIN_HINTS.search(original):
        tokens = _WORD_RE.findall(fixed)
        changed = False
        for i, tok in enumerate(tokens):
            if not tok or not tok[0].isalpha():
                continue  # boşluk/noktalama parçalarını ve rakamla başlayanları atla
            fix = _fuzzy_fix(tok)
            if fix:
                tokens[i] = fix
                changed = True
        if changed:
            fixed = "".join(tokens)

    if fixed != original:
        _last_correction = {"original": original, "corrected": fixed}
    else:
        _last_correction = None
    return fixed
