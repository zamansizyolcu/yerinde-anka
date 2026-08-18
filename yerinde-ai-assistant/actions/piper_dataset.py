"""
actions/piper_dataset.py — Piper ses klonlama için EĞİTİM SETİ hazırlama.

XTTS-v2'nin aksine (10 sn'de anlık klonlama), Piper gerçek bir EĞİTİM süreci
ister: birden fazla cümleyi kaydedip metniyle eşleştiren bir veri kümesi
(LJSpeech biçimi) + Google Colab'da (ücretsiz GPU) mevcut tr_TR-dfki-medium
sesinden İNCE AYAR (fine-tuning). Bu modül o veri kümesini hazırlar:

  1) Fonetik açıdan çeşitli ~50 Türkçe cümle sırayla okutulur
  2) Her cümle MicStream ile (aynı uyarlanabilir VAD, parec/arecord yedeği)
     kaydedilir → wavs/001.wav, wavs/002.wav, ...
  3) LJSpeech formatında metadata.csv üretilir: "001|Cümle metni"
  4) Her şey tek bir .zip'e paketlenir, Colab'a yüklemeye hazır

Çıktı, Piper'ın kendi eğitim betiğinin (piper_train) beklediği biçimdedir:
16 bit mono WAV + "dosya_adı|transkript" satırları.
"""

from __future__ import annotations

import csv
import json
import time
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "egitim_seti_piper"
WAVS_DIR = DATASET_DIR / "wavs"
META_PATH = DATASET_DIR / "metadata.csv"
STATE_PATH = DATASET_DIR / "durum.json"

SAMPLE_RATE = 22050   # Piper "medium" kalite sesler bu hızda (tr_TR-dfki-medium ile eşleşir)

# Fonetik açıdan çeşitli ~50 Türkçe cümle: tüm sesli harfler (a,e,ı,i,o,ö,u,ü),
# ayırt edici ünsüzler (ç,ş,ğ,c,j), sayılar, sorular, farklı cümle uzunlukları.
SENTENCES: list[str] = [
    "Bugün hava çok güzel, dışarı çıkalım mı?",
    "Yarın sabah erkenden işe gitmem gerekiyor.",
    "Bu kitabı okumayı çok seviyorum.",
    "Annem akşam yemeğinde köfte yaptı.",
    "İstanbul'da trafik bazen çok yoğun oluyor.",
    "Çocuklar bahçede neşeyle oynuyorlardı.",
    "Öğretmenimiz bize yeni bir ödev verdi.",
    "Kütüphanede sessizce ders çalışıyorum.",
    "Güneş doğarken deniz pembeye boyanıyor.",
    "Bu yıl tatilde dağlara gitmeyi planlıyoruz.",
    "Bilgisayarım son zamanlarda çok yavaşladı.",
    "Türkçe öğrenmek başta zor gibi görünse de zevkli.",
    "Şehrin merkezinde yeni bir alışveriş merkezi açıldı.",
    "Kahvaltıda peynir, zeytin ve bal tercih ederim.",
    "Yağmur yağmaya başlayınca şemsiyemi açtım.",
    "Üniversite sınavına hazırlanan öğrenciler çok çalışıyor.",
    "Bahçedeki güller bu bahar erken açtı.",
    "Telefonumun şarjı bitmek üzere, hemen şarj etmeliyim.",
    "Kardeşimle birlikte sinemaya gitmeyi düşünüyoruz.",
    "Bu proje için üç hafta süre tanındı.",
    "Sabah kalkar kalkmaz bir bardak su içerim.",
    "Yeni aldığım ayakkabılar çok rahat.",
    "Öğleden sonra arkadaşlarımla buluşacağım.",
    "Mutfakta güzel bir yemek kokusu var.",
    "Geçen hafta sonu köye gidip dedemi ziyaret ettik.",
    "Bu şarkının sözleri gerçekten çok anlamlı.",
    "Kışın en sevdiğim şey sıcak çorba içmek.",
    "Bilgisayar mühendisliği okumak istiyorum.",
    "Otobüs bu sabah biraz gecikti.",
    "Balkonda küçük bir sebze bahçesi yetiştiriyorum.",
    "Yarınki toplantı saat onda başlayacak.",
    "Bu filmi daha önce üç kere izledim.",
    "Kedimiz her sabah beni uyandırıyor.",
    "Yeni yıl için güzel hedefler belirledim.",
    "Sokakta satılan mısır çok güzel kokuyor.",
    "Ailemle birlikte pikniğe gitmeyi çok seviyorum.",
    "Bu soruyu çözmek biraz zaman aldı.",
    "Denize girmeden önce güneş kremi sürmeliyiz.",
    "Öğretmen sınıfa yeni bir konu anlattı.",
    "Akşam olduğunda gökyüzü kızıla dönüyor.",
    "Bu hafta işlerim yoğun geçti.",
    "Küçük kardeşim resim yapmayı çok seviyor.",
    "Yolda giderken eski bir arkadaşımla karşılaştım.",
    "Bu yemeğin tarifini bana verir misin?",
    "Kitapçıda saatlerce kitap karıştırdım.",
    "Sabah koşusu güne enerjik başlamamı sağlıyor.",
    "Bu şehirde kaç yıldır yaşıyorsun?",
    "Yeni telefonumun kamerası gerçekten çok başarılı.",
    "Pazar günleri genelde ailemle vakit geçiririm.",
    "Bu proje tam olarak ne zaman teslim edilecek?",
    "Dışarıda rüzgar oldukça sert esiyor bugün.",
]


# ── Durum yönetimi ───────────────────────────────────────────────────────────
def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"recorded": []}   # kaydedilen cümle indeksleri


def _save_state(state: dict) -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _write_metadata(state: dict) -> None:
    """LJSpeech biçimi: dosya_adı|transkript (uzantısız dosya adı)."""
    with META_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="|")
        for idx in sorted(state["recorded"]):
            writer.writerow([f"{idx:03d}", SENTENCES[idx]])


# ── Durum sorgulama ──────────────────────────────────────────────────────────
def dataset_status() -> str:
    state = _load_state()
    done = len(state["recorded"])
    total = len(SENTENCES)
    remaining = [i for i in range(total) if i not in state["recorded"]]
    if not remaining:
        return f"Eğitim seti TAMAM: {done}/{total} cümle kaydedildi. 'eğitim setini paketle' de."
    nxt = remaining[0]
    return (f"Eğitim seti: {done}/{total} cümle kaydedildi. "
            f"Sıradaki ({nxt + 1}. cümle): \"{SENTENCES[nxt]}\"")


def next_sentence_index() -> int | None:
    state = _load_state()
    remaining = [i for i in range(len(SENTENCES)) if i not in state["recorded"]]
    return remaining[0] if remaining else None


# ── Kayıt ────────────────────────────────────────────────────────────────────
def record_sentence(index: int | None = None, seconds: float = 8.0,
                    on_log=lambda m: None) -> str:
    """
    Belirtilen (ya da bir sonraki) cümleyi kaydeder. Aynı uyarlanabilir VAD'i
    (ortam gürültüsü ölçümü + tavanlı eşik) kullanır — 'sağırlık' regresyonuna
    yol açan hatanın aynısına düşmemek için STT'deki mantığın birebir aynısı.
    """
    try:
        import numpy as np
        from backend.audio_input import MicStream, resample_to_16k
    except ImportError as e:
        return f"Kayıt için eksik paket: {e}"

    state = _load_state()
    if index is None:
        index = next_sentence_index()
        if index is None:
            return "Tüm cümleler zaten kaydedilmiş — 'eğitim setini paketle' de."
    if not (0 <= index < len(SENTENCES)):
        return f"Geçersiz cümle numarası (1-{len(SENTENCES)} arası olmalı)."

    text = SENTENCES[index]
    on_log(f"SYS: 🎙 {index + 1}/{len(SENTENCES)}: \"{text}\"")
    on_log("SYS: Konuşmaya başlayabilirsin, sessizlik olunca otomatik durur...")

    mic = MicStream(samplerate=16000, blocksize=1024, log=on_log)
    if not mic.start():
        return "Mikrofon açılamadı — kayıt alınamadı."

    def _rms(chunk: bytes) -> float:
        s = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
        return float(np.sqrt(np.mean(s ** 2))) if len(s) else 0.0

    buf = bytearray()
    speaking = False
    silence_acc = 0.0
    start_t = time.time()
    pending = None
    try:
        # Ortam gürültüsü ölçümü (~0.25 sn) — konuşma varsa kaçırma
        noise = []
        calib_until = time.time() + 0.25
        while time.time() < calib_until:
            chunk = mic.read(timeout=0.3)
            if chunk is None:
                break
            r = _rms(chunk)
            if r > 0.04:
                pending = chunk
                break
            noise.append(r)
        noise.sort()
        noise_floor = noise[len(noise) // 2] if noise else 0.005
        start_threshold = min(max(0.012, noise_floor * 3.5), 0.045)
        stop_threshold = min(max(0.008, noise_floor * 2.0), 0.030)

        if pending is not None:
            speaking = True
            buf.extend(pending)

        max_seconds = max(seconds, 20.0)   # cümle uzunsa kesmesin
        while time.time() - start_t < max_seconds:
            chunk = mic.read(timeout=0.5)
            if chunk is None:
                continue
            rms = _rms(chunk)
            block_ms = (len(chunk) / 2) / 16000 * 1000
            if rms > start_threshold:
                speaking = True
                silence_acc = 0.0
                buf.extend(chunk)
            elif speaking:
                buf.extend(chunk)
                if rms < stop_threshold:
                    silence_acc += block_ms
                    if silence_acc >= 900:
                        break
                else:
                    silence_acc = 0.0
    finally:
        mic.close()

    pcm = resample_to_16k(bytes(buf), mic.rate) if mic.rate != 16000 else bytes(buf)
    if len(pcm) < 8000:      # <0.5 sn → muhtemelen yakalanamadı
        return "Neredeyse hiç ses kaydedilemedi — mikrofona daha yakın konuşup tekrar dene."

    # Piper eğitimi için 22050 Hz'e yükselt (tr_TR-dfki-medium ile eşleşsin)
    import wave
    WAVS_DIR.mkdir(parents=True, exist_ok=True)
    tmp16 = WAVS_DIR / f"_tmp_{index:03d}.wav"
    with wave.open(str(tmp16), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(pcm)

    out_path = WAVS_DIR / f"{index:03d}.wav"
    try:
        import shutil
        shutil.copy(tmp16, out_path)
        _upsample_wav(out_path, SAMPLE_RATE)
    except Exception:
        import shutil
        shutil.copy(tmp16, out_path)
    finally:
        tmp16.unlink(missing_ok=True)

    state["recorded"] = sorted(set(state.get("recorded", [])) | {index})
    _save_state(state)
    _write_metadata(state)

    done = len(state["recorded"])
    total = len(SENTENCES)
    return f"Kaydedildi ({done}/{total}). " + dataset_status().split(". ", 1)[-1]


def _upsample_wav(path: Path, target_rate: int) -> None:
    """Standart kütüphaneyle basit yeniden örnekleme (harici bağımlılık yok)."""
    import array
    import wave
    with wave.open(str(path), "rb") as w:
        ch, width, sr, n = (w.getnchannels(), w.getsampwidth(),
                            w.getframerate(), w.getnframes())
        if sr == target_rate or width != 2 or n == 0:
            return
        raw = w.readframes(n)
    samples = array.array("h"); samples.frombytes(raw)
    frames = len(samples) // ch
    ratio = target_rate / sr
    out_frames = int(frames * ratio)
    out = array.array("h", bytes(out_frames * ch * 2))
    for i in range(out_frames):
        src = i / ratio
        i0 = int(src); i1 = min(i0 + 1, frames - 1); frac = src - i0
        for c in range(ch):
            a = samples[i0 * ch + c]; b = samples[i1 * ch + c]
            out[i * ch + c] = int(a + (b - a) * frac)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(target_rate)
        w.writeframes(out.tobytes())


def redo_sentence(index: int) -> str:
    """Bir cümleyi listeden çıkarır ki tekrar kaydedilebilsin."""
    state = _load_state()
    if index in state.get("recorded", []):
        state["recorded"].remove(index)
        _save_state(state)
        _write_metadata(state)
        wav = WAVS_DIR / f"{index:03d}.wav"
        wav.unlink(missing_ok=True)
        return f"{index + 1}. cümle sıfırlandı, tekrar kaydedebilirsin."
    return "Bu cümle zaten kaydedilmemiş."


def reset_dataset() -> str:
    import shutil
    shutil.rmtree(DATASET_DIR, ignore_errors=True)
    return "Eğitim seti tamamen sıfırlandı."


# ── Paketleme (Colab'a yüklemeye hazır .zip) ────────────────────────────────
def package_dataset(on_log=lambda m: None) -> str:
    state = _load_state()
    done = len(state.get("recorded", []))
    if done == 0:
        return "Henüz hiç cümle kaydedilmedi."

    readme = f"""YERİNDE — Piper İnce Ayar Veri Kümesi
=====================================

Kaydedilen cümle: {done}/{len(SENTENCES)}
Örnekleme hızı  : {SAMPLE_RATE} Hz, mono, 16-bit
Biçim           : LJSpeech (metadata.csv → "dosya_adı|transkript")

NASIL KULLANILIR (Google Colab, ücretsiz):
  1) Bu wavs/ klasörünü ve metadata.csv'yi Google Drive'ına yükle.
  2) Piper eğitim not defterini aç (topluluk sürümü):
     https://colab.research.google.com/github/rmcpantoja/piper/blob/master/notebooks/piper_multilingual_training_notebook.ipynb
  3) Veri kümesi yolunu bu klasöre göre ayarla.
  4) Sıfırdan değil, mevcut Türkçe sesten İNCE AYAR yapmak için taban model
     olarak "tr_TR-dfki-medium" checkpoint'ini seç (daha az veri/süreyle
     daha iyi sonuç verir).
  5) Eğitim bitince dışa aktar:
       python3 -m piper_train.export_onnx model.ckpt model.onnx
       cp training_dir/config.json model.onnx.json
  6) İki dosyayı (model.onnx + model.onnx.json) YERİNDE'nin 'voices/'
     klasörüne koy — SES listesinde otomatik görünür, başka hiçbir şey
     yapmana gerek yok.

Not: {len(SENTENCES) - done} cümle daha kaydedip veri kümesini
büyütmek istersen, "eğitim için ses kaydet" demeye devam edebilirsin.
"""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    (DATASET_DIR / "OKU_BENI.txt").write_text(readme, encoding="utf-8")

    zip_path = BASE_DIR / f"piper_egitim_seti_{time.strftime('%Y%m%d_%H%M')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for wav in sorted(WAVS_DIR.glob("*.wav")):
            z.write(wav, arcname=f"wavs/{wav.name}")
        z.write(META_PATH, arcname="metadata.csv")
        z.write(DATASET_DIR / "OKU_BENI.txt", arcname="OKU_BENI.txt")

    on_log(f"SYS: Paket hazır: {zip_path.name} ({done} cümle)")
    return (f"Eğitim seti paketlendi: {zip_path.name} ({done}/{len(SENTENCES)} cümle). "
            "Google Drive'a yükleyip Piper eğitim not defterini açabilirsin — "
            "adımlar paketin içindeki OKU_BENI.txt'de.")
