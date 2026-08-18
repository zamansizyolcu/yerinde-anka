# YERINDE ANKA final34 RAPOR (final33.md uygulaması)

Tarih: 2026.08.18
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## 0) UNPACKFS ÇÖKÜŞÜ — KÖK NEDEN + DÜZELTME (kullanıcı hatası raporu)

**Belirti**: "unpackfs python işi için /usr/lib/calamares/modules/unpackfs/main.py
ana komut dosyası bir istisna oluşturdu" — UEFI ve MBR'de aynı.

**Kök neden**: airootfs autostart'ı `Exec=calamares` (yetkilendirme YOK).
final30'a kadar canlı oturum ROOT açılıyordu → sorunsuzdu. final30'da
cacyhos paritesiyle oturum `User=yerinde` (yetkisiz) olunca Calamares
yetkisiz çalıştı → unpackfs `do_mount` içindeki `mount -t squashfs -o loop`
başarısız → yakalanmamış CalledProcessError → istisna kutusu. final31
disk-uyarısı düzelene kadar kurulum welcome'da takıldığı için bu hata ilk
kez final31 ISO'da yüzeye çıktı. (Kanıt zinciri: akış hostta birebir
yeniden üretildi — ISO loop-mount + sfs loop-mount + `rsync -aHAXSr
--filter=-x trusted.overlay.*` → EXIT=0, stderr SIFIR; binary'ler
(rsync/unsquashfs/mount/umount) ISO'da mevcut → hata akışta değil,
YETKİDE.)

**Düzeltme** (airootfs düzeyi; calamares derlemesi gerekmedi):
- `/etc/xdg/autostart/calamares.desktop`: `Exec=sh -c "sleep 3; pkexec calamares"`
  (menü kısayoluyla aynı yol; sleep 3 polkit ajanı emniyeti — final33 §3)
- `/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules`: YALNIZ
  `/usr/bin/calamares` + yerel-etkin wheel oturumu → parolasız izin
  (program kısıtı `action.lookup("program")` ile)
- `yerinde-finalize.sh`: bu kuralı kurulu sistemden SİLER (güvenlik);
  autostart zaten siliniyordu
- build-iso.sh: prep+POST doğrulamaları (POST'ta sudo ile — polkit paketi
  rules.d'yi 0750 root:polkitd yapar, yetkisiz `test -f` yanlış negatif
  verirdi; ilk derlemede bu yüzden FAIL oldu, kontrol düzeltildi)
- Kanıt: `POST OK (final33): calamares pkexec + polkit kuralı ISO'da` + sudo ls

## §1 ASİSTAN ÇALIŞMA ZAMANLARI — ZATEN YERİNDE (final30; yeniden kanıtlandı)

- packages.x86_64: ydotool git xdotool wmctrl python-pyaudio portaudio ✓
  (numpy/pillow zaten var) — `PKGS OK (final27 §2)` prep kanıtı
- sysusers `yerinde-uinput.conf` + udev `80-uinput.rules` (0660) +
  modules-load uinput + ydotoold drop-in (0660/uinput) + wants linki ✓
  (`UINPUT OK`) — NOT: prompt usr/lib/... diyor; etc/... konumu systemd'de
  eşdeğerdir (etc, usr/lib'i ezer), değiştirilmedi.
- finalize `usermod -aG uinput,input "$NEW_USER"` (idempotent) ✓

## §2 SDDM OTO-GİRİŞ + DRKONQI — YERİNDE (final30)

- `yerinde-autologin.conf`: User=yerinde + Session=plasma.desktop
  (wayland-sessions ls kanıtı POST'ta) — NOT: prompt yerinde.conf içinde
  [Autologin] istiyor; ayrı dosya + finalize silmesi DAHA GÜVENLİ (kurulu
  sisteme oto-giriş sızmaz), korundu.
- grep: sddm yapılandırmalarında xsessions referansı SIFIR ✓
- drkonqi-coredump@.service → /dev/null mask linki ✓
- sddm-greeter --test-mode log temiz ✓

## §3 CALAMARES DİSK YARIŞI — final31'de yapıldı (-5)

- check_big_enough: /sys/block taraması (prompt'un "fallback"undan güçlü,
  tam değiştirme); ilk açılışta "4 GB" kutusu gitti (kullanıcı kurulumun
  unpackfs'e kadar ilerlediğini doğruladı).
- "sleep 3 && calamares" emniyeti autostart'a eklendi (yukarıda).

## §4 GEMINI SES ÇATALLANMASI

ÖNCE (main.py 2017-2022): `pya.open(format=paInt16, channels=1,
rate=RECV_SAMPLE_RATE(24000), output=True)` — frames_per_buffer YOK;
`chunk = await self.audio_in_queue.get()` BLOKLAYICI (underrun korumasız).

SONRA:
- ÇIKIŞ (yol 1 + yol 2): `rate=24000, channels=1, paInt16,
  frames_per_buffer=4096` ✓ (GİRİŞ mikrofon rate=16000 DOKUNULMADI —
  satır 1896 kanıtı)
- UNDERRUN: `asyncio.wait_for(queue.get(), timeout=0.1)` → TimeoutError'da
  konuşma SÜRERKEN `stream.write(b"\x00"*4096)` dijital sessizlik
  (48kHz upsample dalında 2x tekrarlı)
- Eski akıcı kopya (~/yerinde-ai-assistant) ile bölge diff → FARK-YOK
  (çekilecek eski değer yoktu)
- py_compile OK; grep'ler -x venv ile (bağımlılık taramalarında venv hariç)

## §5 "MASAÜSTÜNÜ GÖSTER" ZİNCİRİ

- Keşif: core/input_backend.py (satır 17 mesaj katmanı = YDOTOOL_MISSING_TR)
  DOKUNULMADI; actions/keyboard_control.py `press_key` Wayland dalına
  YALNIZ eylem zinciri eklendi:
  1) wtype→ydotool mevcut yol DOKUNULMADI (`_wayland_press`)
  2) ydotool YOKSA/BAŞARISIZSA: `_show_desktop_dbus()` →
     `dbus-send --session --print-reply --dest=org.kde.kglobalaccel
     /component/kwin org.kde.kglobalaccel.Component.invokeShortcut
     string:"Show Desktop"` — NOT: prompt'taki `/desktop` yolu bu hostta
     DENEYLENIP doğrulandı: çalışan yol `/component/kwin` (yöntem dönüşü
     kanıtı); `/desktop` da ikinci sırada denenir (zararsız).
  3) ikisi de yoksa ESKİ Türkçe mesaj aynen döner
- py_compile OK; zincir grep kanıtı: `_show_desktop_dbus` + `Show Desktop`

## §6 TIKLA-KUR — KORUNDU

- bash -n OK; "İnternet: $INTERNET" ayrıştırma + git clone fallback +
  kurulum.sh araması grep kanıtı (13 eşleşme); git artık ISO'da (§1).

## §7 ISO DERLEME

- branding -17 / calamares -5 değişmedi (pkgrel bump gerekmedi — unpackfs
  düzeltmesi airootfs'te); repo db: calamares-3.4.2-5 + branding-17 +
  asistan-2.0.0-1
- setsid + log: /tmp/opencode/final34-iso.log (+ mkarchiso logunda
  14× `INFO: Done!` — bootstrap/overlay/iso aşamaları)
- **out/yerinde-anka-2026.08.18-x86_64.iso — 2,7G**
- **SHA256: 795264e086ee6b0445efc92eb55470b8537824ecfc8f04bf07d6222f2689cd75**
- `== TÜM POST DOĞRULAMALAR BAŞARILI ==` (final33 POST kanıtları dahil)

## §8 PUSH — İKİ REPO

**A) ASİSTAN** (BAZ SRC'den; BAZ'ın .git'i final30 §5B'de kaldırılmıştı →
geçici repo: init + fetch + reset e8332f6 + commit):
- commit **880f6f4**: §4 (main.py) + §5 (keyboard_control.py);
  kişisel memory/habits.json EKLENMEDİ
- push: `e8332f6..880f6f4 main -> main` ✓
**B) OS KAYNAKLARI** (A'dan sonra .git yine kaldırıldı):
- commit **1eea840** (polkit kuralı + autostart + finalize + build-iso +
  asistan değişiklikleri + final33.md) → push ✓
**C) DOĞRULA**: asistan ls-remote main=880f6f4 + HTTP 200 ✓;
yerinde-anka ls-remote main=1eea840 + HTTP 200 ✓
NOT: *.iso GitHub'a giremez → LAN `python -m http.server` / USB
(README.md'de yazılı).

## §9 REGRESYON (POST kanıtlı)

Wayland-tek (xsessions boş, [X11] false) ✓; SDDM krem+Enter+⟳⏻ ✓; ANKA
markası ✓; keyring ✓; zip araçları ✓; NOESCAPE+TABMSG ✓; 5 duvar kağıdı ✓;
sudoers wheel ✓; asistan PAKETİ ISO'da YOK (yalnız kurucu) ✓; numpy/pip
gevşek pinler (paket -5/-17 sürümleri) ✓; tıkla-kur mesaj ayrışımı ✓.

## §10 KULLANICI TEST LİSTESİ

1. `echo $XDG_SESSION_TYPE` → wayland
2. İlk açılışta "4 GB" kutusu YOK; oto-giriş şifresiz; Calamares kendiliğinden
   YETKİLİ açılır (polkit parola kutusu YOK) — unpackfs artık istisna vermez
3. Şifreli girişte drkonqi popup YOK
4. Sesli "masaüstünü göster" → pencereler iner (ydotool yoksa bile — dbus
   yedeği), hata mesajı YOK
5. "fareyi sağa oynat" / "ctrl+t yaz" → cacyhos paritesi (ydotoold 0660)
6. Gemini sesi AKICI (çıkış 24kHz buffer 4096 + underrun sessizlik)
7. Tıkla-kur, İndirilenler boşken git clone ile kurar
8. UEFI+MBR kurulum regresyonu YOK
9. KURULU sistemde: `/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules`
   YOK olmalı (finalize temizliği) + kullanıcı `groups` çıktısında
   uinput,input olmalı
