# YERINDE ANKA final37 RAPOR (final37.md uygulaması)

Tarih: 2026.08.18
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## §1 TIKLA-KUR = kurulum.sh SARICISI (pyrect çöküşünün kökü)

**Kök neden**: tıkla-kur zincirinin ucundaki `kurulum.sh` kendi
venv+`pip install -r requirements.txt` yolunu koşuyordu; pyautogui'nin
pyrect bağımlılığı sdist olarak pip build-isolation içinde derleniyor ve
temiz sistemlerde çöküyordu.

**Düzeltme** (`yerinde-ai-assistant/kurulum.sh`):
- `[2/4] venv` + `[3/4] pip install -r` + ultralytics pip bloğu TAMAMEN
  SİLİNDİ; `python-pip` PKGS listesinden çıktı; eski kurulumlardan kalma
  `venv/` dizini temizlenir.
- Python kütüphaneleri ARTIK yalnız pacman sistem paketlerinden:
  numpy/pillow/opencv/pyaudio/portaudio/psutil/requests/pyperclip/mss/
  selenium/vosk/av/openpyxl/websocket-client (hepsi depolarda VAR —
  `pacman -Si` ile tek tek doğrulandı; python-pyautogui depoda YOK →
  pyrect derlemesi hiç yapılamaz, Wayland'de zaten ydotool/dbus zinciri
  birincil). Depoda olmayanlar (google-genai, piper-tts, faster-whisper,
  pdfplumber, docx/pptx, sounddevice, dvrip, ultralytics) uygulama
  tarafından ZARİFÇE devre dışı (main.py importları try/except korumalı);
  pacman paketiyle kurulanlarda hepsi vendor/ içinde hazır gelir.
- Wayland filtresi + ydotool/uinput altyapısı + kdotool + config adımı
  AYNEN korundu ("doğru yol" zaten buradaydı).
- `yerinde-asistan-kur` (tıkla-kur) başlığı final37 sarıcı akışına
  güncellendi: 1) pacman [yerinde] → 2) yerel klasör → ./kurulum.sh →
  3) git clone → ./kurulum.sh → 4) final27 mesaj ayrışımıyla hata.
  Tıkla-kur'da zaten kendi kurulum/pip kodu yoktu (final25/27'den beri
  saf sarıcı) — akış korundu.
- **GitHub push (clone yolu düzeltmeyi alsın diye zorunluydu)**:
  `44cb450..90749c1 main` →
  github.com/zamansizyolcu/yerinde-ai-assistant ✓
  (yalnızca kurulum.sh; kişisel config/memory artıkları HARİÇ)

**Kanıt**:
- `bash -n kurulum.sh` OK
- `grep -c "pip install -r" kurulum.sh yerinde-asistan-kur` → **0 / 0**
- build-iso.sh prep kalıcı kontrolü: `ASISTAN-KUR OK (final37 §1):
  kurulum.sh pip/venv'siz (sistem paketleri) + tıkla-kur sarıcı`

## §2 UEFI TEMA: YEŞİL ARKA PLAN + KREM/TURUNCU YAZI

- **UEFI önyükleyici değişti**: profiledef.sh `uefi.systemd-boot` →
  **`uefi.grub`** (systemd-boot temayı YOKTU; GRUB gfxmenu temalı menü
  verir). `efiboot/loader` (systemd-boot yapılandırması) silindi.
  mkarchiso uefi.grub: BOOTx64.EFI + BOOTIA32.EFI = grub-mkstandalone;
  gömülü erken yapılandırma ISO birimini bulur ve `/boot/grub/grub.cfg`
  yükler.
- **Tema** (`grub/themes/anka/theme.txt` — hem ISO hem kurulu sistem):
  - `desktop-color: "#0B3D2E"` düz yeşil + `background.png`
    (1024x768, PIL ile üretildi: düz yeşil + küçük "yerinde ANKA"
    lockup üst-orta, krem yazı + turuncu vurgu — lockup renkleri
    yeşil zeminde okunur diye yeniden renklendirildi)
  - `item_color = "#EFE9DC"` (krem), `selected_item_color = "#C74A1F"`
    (seçili satır turuncu YAZI)
  - `title-text: "GRUB Açılış Menüsü"` + `title-color: "#EFE9DC"`
  - `desktop-image-scale-method: "stretch"`
- **KRİTİK teknik ayrıntı**: grub-mkstandalone EFI'sinde `${prefix}`
  memdisk'i gösterir → tema yolları **root-göreli mutlak** yazıldı
  (`loadfont /boot/grub/themes/anka/anka-tr.pf2`,
  `set theme="/boot/grub/themes/anka/theme.txt"`). İlk derlemedeki
  `${prefix}` sürümü bu yüzden yeniden derlendi (ikinci derleme = final).
- **Kurulu sistem**: yerinde-branding **1.2.0-17 → 1.2.0-18**
  (/usr/share/grub/themes/anka); yerinde-finalize.sh UEFI dalı:
  `cp -r themes/anka → /boot/grub/themes/anka`,
  `GRUB_THEME="/boot/grub/themes/anka/theme.txt"` (idempotent sed ile
  eski değeri de düzeltir) + `grub-mkconfig`. /etc/grub.d/00_header tema
  dizinindeki TÜM .pf2'leri otomatik loadfont eder (grub 2.14 kaynak
  davranışı — host /etc/grub.d/00_header satır 281 ile doğrulandı).
- **MBR/syslinux KREM tema AYNEN** (DOKUNULMADI): ISO splash.png md5
  kaynak=ISO birebir aynı (e071de02…); NOESCAPE 1 + MENU TABMSG gizli
  POST'ta yine doğrulandı; kurulu BIOS dalındaki krem syslinux.cfg
  el değmedi.

**Kanıt** (üretim sonrası, ISO mount edilerek):
```
theme.txt: desktop-color: "#0B3D2E" / item_color = "#EFE9DC"
           selected_item_color = "#C74A1F" / title-text: "GRUB Açılış Menüsü"
BOOTx64.EFI: grep -ac grub → 897; grep -ac systemd-boot → 0
ISO /loader/loader.conf → YOK (systemd-boot izi sıfır)
grub-script-check grub.cfg + loopback.cfg → sessiz (sözdizimi OK)
```

## §3 TÜRKÇE GLYPH ("ortamı" → "ortam?" SORUNU)

**Kök bulgu (derinlemesine)**: Eski DejaVuSans-32.pf2 aslında
0x0-0x17F kapsam ÜRETİLMİŞTİ (CHIX ikili analizi: 287 glyph, 0x131 =
"ı" dahil). Gerçek kök: ISO UEFI akışında font HİÇ yüklenmiyordu —
eski grub.cfg `loadfont "${prefix}/fonts/unicode.pf2"` arıyordu ama
(a) ISO'da böyle bir dosya yoktu, (b) `${prefix}` standalone EFI'de
memdisk'ti. Sonuç: `terminal_output console` → donanım üretici
yazıtipi → gerçek donanımda ı→?. systemd-boot menüsü de aynı nedenle
glpyh'suzdu.

**Düzeltme**:
- `grub-mkfont --output=anka-tr.pf2 --name="anka-tr" --size=32
  --range=0x0-0x17F /usr/share/fonts/TTF/DejaVuSans.ttf` (+ 44px başlık
  sürümü anka-tr-44.pf2). `fc-list` → DejaVuSans.ttf VAR ✓.
  `--range=0x0-0x17F` Latin-1 + Latin Extended-A = ı İ ş Ş ğ Ğ ç Ç ö Ö
  ü Ü â û TAM kapsam (grub-mkfont varsayılanı yalnız ASCII olurdu —
  aralık AÇIKÇA verildi).
- Fontlar ISO'da `/boot/grub/themes/anka/` altında gömülü + grub.cfg
  root-göreli `loadfont` ile yükler; menü metinleri Türkçeleştirildi:
  "Yerinde ANKA **kurulum ortamı** (x86_64, UEFI)", "ekran okuyuculu
  kurulum ortamı", "Memtest86+ çalıştır (RAM testi)", "UEFI Ürün
  Yazılımı Ayarları", "Sistemi kapat/yeniden başlat" (grub.cfg +
  loopback.cfg; --id'ler değişmedi).
- Kurulu sistem: finalize fontu ESP'ye de gömer
  (`$ESP/grub/fonts/anka-tr.pf2` + `/boot/grub/fonts/anka-tr.pf2`) —
  00_header tema dizini taramasıyla çifte güvence.
- Menü metinleri ASCII'ye KAÇMADI (font çözümü esastır).

**Kanıt** (PF2 CHIX ikili analizi — python struct):
```
anka-tr.pf2     → 319 glyph | maks 0x17F | eksik TR: YOK ✓ (boyut 21507 > 0)
anka-tr-44.pf2  → 319 glyph | maks 0x17F | eksik TR: YOK ✓ (boyut 35135 > 0)
ISO grub.cfg → "kurulum ortamı" ×2 (grep -c)
```

## §4 REGRESYON + BUILD + RAPOR

- Prep + POST doğrulamaları (build-iso.sh'e final37 blokları eklendi):
  `ASISTAN-KUR OK (final37 §1)` + `UEFI-GRUB OK (final37 §2/§3)` +
  `POST OK (final37 §2/§3): … BOOTx64.EFI GRUB` — 18 POST OK toplam,
  `== TÜM POST DOĞRULAMALAR BAŞARILI ==`
- Regresyon zinciri yeniden kanıtlandı: MBR krem syslinux + NOESCAPE;
  Wayland-tek oturum; SDDM krem + oto-giriş + drkonqi maskı;
  ydotool/uinput zinciri (wants linki hedef dahil — final36 düzeltmesi
  çalışma ağacında); keyring; zip/unzip/7z/ark; unpackfs/pkexec;
  calamares-3.4.2-5; 5 duvar kağıdı; sudoers wheel; asistan PAKETİ
  ISO'da YOK. Ses 24kHz (final33/34) — asistan kaynak koduna
  dokunulmadı.
- **Paket**: yerinde-branding **1.2.0-18** makepkg OK (ANKA THEME OK
  doğrulaması paket içinde) + repo-add → yerinde.db.tar.zst
  (%VERSION% 1.2.0-18 kanıtlı).
- **ISO**: `setsid ./build-iso.sh > /tmp/opencode/final37-iso2.log`
  (log sonu: `INFO: Done!` + `TÜM POST DOĞRULAMALAR BAŞARILI`)

```
Dosya : iso/yerinde/out/yerinde-anka-2026.08.18-x86_64.iso
Boyut : 2.607.841.280 bayt (2.4G)
sha256: 71073ae0d782dc135a9988db72392c26e20cd5b79dd5d418e7476f8424916b3b
```
NOT: İlk derleme `${prefix}` hatalı sürümle üretildi (6728b64e… —
GEÇERSİZ), hemen fark edilip root-göreli sürümle yeniden derlendi;
yukarıdaki sha256 GEÇERLİ olandır (out/SHA256SUMS yazıldı).

## KULLANICI TESTLERİ

1. **UEFI VM**: yeşil menü + krem yazı + turuncu seçili satır + başlık
   "GRUB Açılış Menüsü" + girişte "kurulum ortamı" — "ı" doğru görünür.
2. **MBR VM**: krem syslinux menüsü AYNEN (regresyon YOK).
3. **Temiz VM**: "YERINDE Asistanı Kur" → İndirilenler boş + LAN repo
   yoksa git clone → kurulum.sh (pip'siz) → pyrect DERLEME HATASI YOK;
   kurulum sonunda ./baslat.sh ile uygulama açılır (Gemini/piper gibi
   pip-only özellikler zarifçe pas — tam işlevsellik için pacman paketi
   veya vendor).
4. **Gerçek donanım**: kurulu sistem GRUB menüsünde "Yerinde ANKA
   gelişmiş seçenekler" / "UEFI Ürün Yazılımı Ayarları" satırlarında
   ı/ş/ğ karakterlerini kontrol et (ı→? görülürse bildir — font
   kanıtları bu raporda, gerçek donanım üretici yazıtipi etkisi
   ayrıştırılır).
