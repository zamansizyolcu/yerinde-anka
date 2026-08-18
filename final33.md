# YERINDE ANKA final34 — TOPLU MASTER PROMPT
(final30 kalan + final31 v2 + final32 v2 + final33 v2 TEK belgede)
BAZ SRC: /home/yerinde/yerinde-project/yerinde-ai-assistant
(kullanıcının proje içine kopyaladığı ÇALIŞAN cacyhos kopyası;
keşifle DEĞİŞTİRME; ~/yerinde-ai-assistant ve İndirilenler ESKİ)
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe
rapor; eksikse FAIL; push yalnız §8'de belirtilenler için.

## §1 ISO: ASİSTAN ÇALIŞMA ZAMANLARI (cacyhos paritesi)
packages.x86_64 += ydotool git xdotool wmctrl python-pyaudio portaudio
(numpy/pillow zaten var)
- sysusers: usr/lib/sysusers.d/yerinde-uinput.conf → group uinput
- udev: usr/lib/udev/rules.d/80-uinput.rules
  (KERNEL=="uinput", GROUP="uinput", MODE="0660")
- modules-load: uinput
- ydotoold drop-in: socket /run/ydotool.socket 0660 group uinput
  + airootfs multi-user.target.wants linki
- finalize: usermod -aG uinput,input "$NEW_USER" (idempotent)
DOĞRULA: airootfs ls kanıtı; eksikse FAIL.

## §2 SDDM OTO-GİRİŞ + DRKONQI POPUP
- etc/sddm.conf.d/yerinde.conf: [Autologin] User=yerinde
  Session=plasma.desktop (wayland-sessions/plasma.desktop ls kanıtı)
- grep: sddm config'lerinde xsessions referansı SIFIR
- mask: drkonqi-coredump@.service (airootfs mask linki ls kanıtı)
- sddm --test-mode log temiz

## §3 CALAMARES İLK AÇILIŞ DİSK YARIŞI
- welcome modülü checkEnoughStorage: libparted probe BAŞARISIZSA
  fallback /sys/block taraması: /sys/block/*/size (sektör*512;
  /sys/block/<d>/device dizini VARSA say; loop/ram HARİÇ)
  toplam >= requiredStorageB → enoughStorage=true
- calamares PKGBUILD: patch + pkgrel bump
- opsiyonel emniyet: canlı autostart "sleep 3 && calamares"
- TEST maddesi: VM ilk açılışta "4 GB" kutusu YOK

## §4 GEMINI SES ÇATALLANMASI
1) ÖNCE OKU + rapora bas: main.py 270-310 ve 2030-2075
   (stream = p.open(...) satırı + rate değişken tanımı)
2) ÇIKIŞ stream KESİN: rate=24000, channels=1, format=paInt16,
   frames_per_buffer=4096 (GİRİŞ mikrofon 16000 KALIR)
3) UNDERRUN: kuyruk ~100ms boşsa stream.write(b'\x00'*4096)
4) ESKİ akıcı kopya varsa aynı bölge diff → farkı eski değere çek
5) bundan sonra grep'lerde -x venv (gürültü temizliği)

## §5 "MASAÜSTÜNÜ GÖSTER" + PENCERE EYLEMLERİ
Keşif: input_backend.py → Wayland=ydotool, X11=xdotool,
satır 17 = Türkçe mesaj. Eylem zinciri:
1) ydotool (mevcut yol, DOKUNMA)
2) ydotool YOKSA: dbus-send --session --print-reply
   --dest=org.kde.kglobalaccel /desktop
   org.kde.kglobalaccel.Component.invokeShortcut
   string:"Show Desktop"
3) ikisi de yoksa ESKİ Türkçe mesaj
(input_backend mesaj katmanına DOKUNMA; sadece eylem zinciri)

## §6 TIKLA-KUR (final27 korunur)
§1 ile git artık ISO'da → clone fallback çalışır; mesaj ayrışımı
(final27) AYNEN kalır; bash -n + grep kanıtı.

## §7 ISO DERLEME (AYRI BAŞLIK — ATLANMAZ)
1) branding + calamares pkgrel bump; makepkg; repo-add
2) cd iso/yerinde && setsid bash -c './build-iso.sh >
   /tmp/opencode/final34-iso.log 2>&1' &
3) poll: "INFO: Done!" + out/yerinde-anka-*.iso + sha256
4) raporda: boyut + sha256 + log sonu

## §8 PUSH — İKİ REPO (doğrulamalı)
A) ASİSTAN (BAZ SRC'den):
   .gitignore: vosk-model/ *.gguf venv/ __pycache__/ *.pyc
   config/api_keys.json memory/*.json
   commit (§4 + §5 + final28 pyaudio/venv dahil)
   remote origin https://github.com/zamansizyolcu/yerinde-ai-assistant.git
   push -u origin main (KULLANICI İZNİ VAR)
B) OS KAYNAKLARI (source-only):
   A BİTTİKTEN SONRA: rm -rf yerinde-ai-assistant/.git
   .gitignore: work/ out/ *.iso repo/x86_64/*.pkg.tar.zst
   find . -size +90M → BOŞ olmalı (doluysa ignore'a ekle)
   git init -b main + commit
   remote https://github.com/zamansizyolcu/yerinde-anka.git + push
   (boş repo KULLANICI açacak; açılmadıysa raporda komutları yaz)
C) DOĞRULA: iki repo için git ls-remote + curl GitHub 200
NOT: *.iso GitHub'a GİREMEZ (100MB limit) → ISO binary LAN/USB;
README'ye yaz.

## §9 REGRESYON KORUMASI
Wayland-tek; SDDM krem+Enter+⟳⏻; ANKA markası; keyring; zip;
NOESCAPE; duvar kağıtları; sudoers wheel; asistanın KENDİSİ
ISO'da YOK; numpy/pip gevşek pinler; tıkla-kur mesaj ayrışımı.

## §10 RAPOR + KULLANICI TEST LİSTESİ
Kanıtlar: §1 ls; §2 conf+mask; §3 patch satırı; §4 stream.open
ÖNCE→SONRA; §5 zincir grep; §7 sha256; §8 ls-remote çıktıları.
Testler:
1) echo $XDG_SESSION_TYPE → wayland
2) ilk açılışta "4 GB" kutusu YOK; oto-giriş şifresiz çalışır
3) şifreli girişte drkonqi popup YOK
4) sesli "masaüstünü göster" → pencereler iner, mesaj YOK
5) "fareyi sağa oynat" / "ctrl+t yaz" → cacyhos paritesi
6) Gemini sesi AKICI (VM + cacyhos)
7) tıkla-kur, İndirilenler boşken git clone ile kurar
8) UEFI+MBR regresyonu YOK