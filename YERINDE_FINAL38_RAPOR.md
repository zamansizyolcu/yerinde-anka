# YERINDE ANKA final38 RAPOR (final38.md uygulaması)

Tarih: 2026.08.18
KURALLAR: VM testi YOK (host eşdeğeri kanıtlar); setsid+log; grep/ls
doğrulamalı; Türkçe rapor.

## §1 PACMAN TEK TEK ("hepsi ya da hiç" düzeltmesi)

`kurulum.sh` yeniden yazıldı (final37'nin "pip tamamen yasak" yaklaşımı
→ final38'in hibrit yaklaşımı):

- `pacman_tek_tek()` yardımcı fonksiyonu: her paket ÖNCE `pacman -Qi`
  ile kontrol (zaten kurulu → `[OK]`), sonra `sudo pacman -S --needed
  --noconfirm "$pkg"` TEK TEK; başarısızsa `[ATLANDI] $paket` loglanır
  ve KURULUM SÜRER — tek kötü ad tüm listeyi öldüremez.
- Eski interaktif `read -p "Şimdi kurmayı dene? [y/N]"` bloğu kalktı
  (tıkla-kur'un terminalinde takılma riski de bitti).
- **AD HARİTASI** (`pip_adi()`): pacman kuramayınca pip'e DÜŞEN adlar:
  `python-selenium→selenium`, `python-vosk→vosk`,
  `python-opencv→opencv-python`, genel `python-X→X`; pip karşılığı
  olmayan sistem araçları (tk/grim/…) yalnız atlanır.

## §2 VENV HER ZAMAN + EKSİKLER PİP İLE

- `[ ! -d venv ] && python -m venv --system-site-packages venv` —
  mevcut venv KORUNUR (final37'nin `rm -rf venv`'si kaldırıldı).
- Aktivasyondan sonra `pip install --upgrade pip wheel setuptools`.
- Pip listesi TEK TEK kurulur: pacman'ın atladıkları (PIP_BEKLEYEN,
  AD HARİTASI'yla) + depoda olmayanlar (google-genai, sounddevice,
  faster-whisper, piper-tts, pdfplumber, python-docx, python-pptx,
  dvrip, webdriver-manager). Her biri `pip install -q "$ad" ||
  [ATLANDI-pip]` — biri tutmazsa kurulum ölmez.
- **Wayland'de pyautogui/pygetwindow/pyrect ASLA pip ile kurulmaz**
  (case filtresi + `[BİLGİ] Wayland: pip ile bilinçli KURULMADI:`
  logu) — pyrect sdist çöküşü (final37 kök nedeni) tekerrür edemez.
- `pip install -r` (toplu requirements) scriptte YOK (grep kanıtı:
  0 eşleşme) — hepsi-ya-da-hiç yolu kapalı.

## §3 baslat.sh GÜVENLİ

Yeni `baslat.sh`:
1. venv yoksa `python -m venv --system-site-packages venv` oluşturur
2. `venv/bin/python` yoksa **PY="python3"** sistem fallback'i
3. Uygulama çökince stderr'den `ModuleNotFoundError: No module named
   'X'` ayıklanır → Türkçe ipucu: eksik modül ADI + `./kurulum.sh`
   veya `source venv/bin/activate && pip install X` komutu; başka
   hata ise `~/.yerinde/ai.log` yönlendirmesi. Çıkış kodu korunur.

**Stub kanıtı** (geçici dizinde `import named_module_olan_bir_sey`
hatası veren sahte main.py ile `bash baslat.sh`):
```
HATA: Uygulama 'named_module_olan_bir_sey' modülü eksik olduğu için açılamadı.
Kurmak için ya tüm kurulumu yeniden çalıştır:
    ./kurulum.sh
ya da yalnız bu modülü kur:
    source venv/bin/activate && pip install named_module_olan_bir_sey
```
`baslat RC=1` doğru yayıldı ✓

## §4 KDOTOOL: cc ÖNKOŞULU

- `command -v cc` yoksa önce `pacman_tek_tek gcc binutils` (yine tek
  tek/atla mantığıyla), sonra rustup/cargo akışı.
- `cargo install kdotool` başarısızsa `[UYARI] … kurulum sürüyor` +
  elle komut — kurulum ASLA ölmez (rustup `|| true` korumalı, aynen).

## §5 TEST (temiz-VM eşdeğeri host kanıtları)

VM testi kuralı gereği host üzerinde birebir akış koşuldu:

1. **Taze venv + pip zinciri** (setsid+log:
   `/tmp/opencode/final38-pip.log`) — kurulum.sh'in [3/5] adımıyla
   aynı komut dizisi:
```
[OK-pip] google-genai      [OK-pip] piper-tts
[OK-pip] sounddevice       [OK-pip] pdfplumber
[OK-pip] faster-whisper    [OK-pip] python-docx
[OK-pip] python-pptx       [OK-pip] dvrip
[OK-pip] webdriver-manager
ATLANAN:            ← BOŞ (9/9 kuruldu)
```
2. **Başlama kanıtı**: taze venv'ten `import main` (GUI'siz tam modül
   zinciri: numpy, ui/tkinter, PIL, psutil, tüm actions/backend +
   google.genai):
```
IMPORT-OK: asistan modül zinciri tamam
```
   (`main.py` `if __name__ == "__main__"` korumalı — import güvenli.)
3. **bash -n**: kurulum.sh + baslat.sh + build-iso.sh OK.

## §6 REGRESYON (AYNEN korundu)

- **ydotool/socket adımı**: final36 bloğu birebir korundu — grep:
  `run/ydotool.socket|systemctl --user enable --now ydotool` → 4 eşleşme
- **numpy gevşek pin**: requirements.txt `numpy>=2` (satır 22) el
  değmedi
- **Türkçe mesajlar**: tüm [OK]/[UYARI]/[ATLANDI]/[BİLGİ] metinleri
  Türkçe; Wayland açıklama metinleri aynen
- build-iso.sh prep: final37 kuralları → **final38 kuralları**
  (`pip install -r` YASAK + pyautogui/pygetwindow/pyrect pip YASAĞI +
  pozitif kontroller: venv satırı, `pacman -S --needed --noconfirm
  "$pkg"`, AD HARİTASI, baslat.sh fallback + ipucu):
  `ASISTAN-KUR OK (final38 §1-§3)` + SDDM GREETER OK

## PUSH (§5 commit + push)

- **Asistan** (clone yolu düzeltmeyi anında alır):
  `90749c1..f2d3657 main` →
  github.com/zamansizyolcu/yerinde-ai-assistant ✓
  (yalnız kurulum.sh + baslat.sh; kişisel config/memory HARİÇ)
- **OS kaynakları**: `3a5a179..1cb4d58 main` →
  github.com/zamansizyolcu/yerinde-anka ✓ (final37 commit'i 41a1b78
  de önceki push'ta eksik kalmıştı — bu push'ta birlikte gitti)
- **ISO derlemesi GEREKMEDİ** (final35 emsali): asistan ISO'da yok;
  tıkla-kur clone/pacman yolları GitHub'dan anında çeker.

## KULLANICI TESTİ (temiz VM)

1. `./kurulum.sh` → her paket için [OK]/[ATLANDI] satırları akar;
   sonunda "ATLANAN paketler" özeti (boşsa "hiçbir paket atlanmadı")
2. `./baslat.sh` → asistan penceresi AÇILIR (Gemini doğal ses dahil:
   google-genai bu kez pip ile kuruluyor)
3. Bilerek bir paketi boz (örn. `venv/bin/pip uninstall -y pdfplumber`
   + sistemden de yoksa) → `./baslat.sh` çöküşte eksik modül adını +
   kurulacak komutu Türkçe yazdırır
