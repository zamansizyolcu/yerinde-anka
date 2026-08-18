# YERINDE OS — FINAL13 RAPORU

**Sürüm:** v1.3 (final13.md'nin 10 bölümü)
**Tarih:** 2026-08-15
**Kapsam:** Canlı mod davranışı, MBR syslinux teması, UEFI GRUB + fallback, 5 ton duvar kağıdı, SDDM oturum seçici, Wayland/X11 araçları, AI paketi sağlamlaştırması, sudo/kapasite, paket + ISO build.

---

## 1. Yapılan Değişiklikler (bölüm bölüm)

### §1 — Canlı mod: autostart yok, tıklayınca Gemini ekranı
- Kurulu sisteme "yerinde-live.desktop" koruması eklendi: `yerinde-finalize.sh` artık
  `${ROOT}/etc/xdg/autostart/yerinde-live.desktop` dosyasını siler (bulunmasa bile zararsız).
- ISO'da hiçbir yerinde-live.desktop yok (grep ile doğrulandı); canlı oturumda asistan
  otomatik AÇILMAZ.
- Canlı kullanıcı root'tur (sddm autologin `User=root`) ve root evinde `~/.yerinde/config.json`
  YOKTUR → menüden tıklandığında `main.py` varsayılanı (gemini) devreye girer → **API anahtar ekranı** gelir.
- skel'deki `config.json` (ollama) yalnızca **kurulu sistem** kullanıcılarına uygulanır (istenen davranış).
- Asistanı AÇMAYAN yalnızca tema betiği (yerinde-first-run.desktop → ikon + duvar kağıdı) autostart olarak kalır.

### §2 — MBR syslinux: krem tema (BIOS)
- **splash.png yeniden üretildi:** 640x480, koyu yeşil zemin `#0B3D2E`, "yerinde OS" lockup'ı üst-orta konumda ~%60 boyutunda (432x144), menü alanı boş.
  Kaynak: `packages/yerinde-branding/lockup-green-bg.svg` (krem metinli varyant) → rsvg-convert + PIL.
- **`syslinux/archiso_head.cfg`:** krem renkler uygulandı
  - title `1 #FFF4EFE4` (krem), sel `7 #FF0B3D2E #FFF4EFE4` (koyu yeşil yazı + krem seçili bar),
    unsel/msg07 `#FFF4EFE4`, help/timeout_msg `#FFE5DCC9`; border koyu yeşil.
  - `NOESCAPE 1` eklendi (alt satırdaki "Press [Tab]" yok).
- **`archiso_sys.cfg`:** `MENU AUTOBOOT Otomatik baslatma: # saniye` eklendi.
- **Türkçe TEXT HELP** (`archiso_sys-linux.cfg` + `archiso_pxe-linux.cfg`):
  "Yerinde OS kurulum ortamını BIOS ile başlatır. Yerinde OS kurmanı veya sistem onarmanı sağlar." (ve sesli okuma/NBD/NFS/HTTP varyantları).
- **`yerinde-finalize.sh` BIOS dalı:** kurulu sisteme yazılan `syslinux.cfg` da aynı krem tema +
  NOESCAPE + MENU AUTOBOOT + Türkçe yardım metinleri içerir.

### §3 — UEFI kurulu sistem: temalı GRUB, fallback systemd-boot
- **GRUB teması** `yerinde-branding` paketine eklendi → `/usr/share/grub/themes/yerinde/`
  - `background.png`: 1024x768 krem `#F4EFE4`
  - `logo.png`: koyu yeşil lockup (360x120), küçük, üst-orta
  - `theme.txt`: koyu yeşil `#0B3D2E` menü metni, krem seçili satır (reverse)
- **`yerinde-finalize.sh` UEFI dalı yeniden yazıldı (sırayla):**
  1. `grub-install --target=x86_64-efi --efi-directory=$ESP --bootloader-id=YerindeOS --removable --no-nvram`
  2. tema `$R/boot/grub/themes/yerinde/` altına kopyalanır
  3. `unifont.pf2` prefix fonts dizinine kopyalanır
  4. `/etc/default/grub`'a `GRUB_THEME="/boot/grub/themes/yerinde/theme.txt"` yazılır
  5. `grub-mkconfig -o /boot/grub/grub.cfg`
  - **Herhangi bir adım başarısızsa** → systemd-boot fallback (eski sistemd-boot dosyaları: `EFI/BOOT/bootx64.efi` + `loader/` + kernel kopyaları) yazılır.
  - Hangi yolun alındığı `${ROOT}/etc/yerinde-bootloader` dosyasına yazılır (`grub` veya `systemd-boot`).
- ISO'nun kendi UEFI menüsüne (grub/ + efiboot/) dokunulmadı.

### §4 — 5 ton duvar kağıdı
- `yerinde-branding` PKGBUILD zaten 5 tonu kuruyordu; artık **build doğrulaması** eklendi:
  `Yerinde-Destek-{Hologram-Mavi, Krem, Dalga-Mavi, Yesil, Mor}` → 5 `metadata.desktop` doğrulanır, eksikse **build FAIL**.
- Varsayılan: **Yerinde-Destek-Yesil** (ilk-oturum betiği).

### §5 — SDDM: X11+Wayland seçici + Enter ile giriş
- `Main.qml` yenilendi:
  - **Oturum seçici** (ComboBox, sessionModel): "Plasma" ve "Plasma (Wayland)" listelenir.
  - **Parola alanı odaklı** (focus: true + forceActiveFocus).
  - **Enter/Return** hem kullanıcı adı hem parola alanında `login()` tetikler.
- `qmllint` ile doğrulandı (0 hata).

### §6 — Wayland/X11 araçları
- `packages.x86_64` += `xorg-xrandr xdotool ydotool wmctrl xclip` (alsa-utils zaten vardı).
- `airootfs/etc/udev/rules.d/80-uinput.rules`: `KERNEL=="uinput", MODE="0660", GROUP="uinput"`
- `airootfs/etc/sysusers.d/uinput.conf`: `g uinput 790`
- `users.conf` defaultGroups += `uinput input`
- `ydotool.service` → `multi-user.target.wants` symlink (kurulu + canlı sistemde başlatılır)

### §7 — AI paketi sağlamlaştırma (regresyon koruması)
Tümü v1.2'den taşındı ve DOĞRULANDI (değişiklik gerekmedi):
- Launcher ev kopyası (`/usr/bin/yerinde` → `$HOME/.yerinde/app`)
- GGUF enjeksiyonu (`/usr/share/yerinde-modellers/`, 644) + Ollama store ISO'ya gömülü (`/var/lib/ollama/models`, 9 blob / 7,7GB)
- `ollama.service.d/yerinde.conf` drop-in (`OLLAMA_MODELS=/usr/share/ollama/models` → symlink → store)
- `yerinde-ollama-setup.service` oneshot + `/usr/bin/yerinde-ollama-setup`
- pip bağımlılıkları (vendor; google-genai TÜM deps ile — `--no-deps` import'u kırardı)
- piper Türkçe ses (voices/ zaten var → PIPER OK) + `_play_audio` 3 yollu fallback + başlangıçta varsayılan çıkış cihazı logu
- KDE başlat ikonu: `yerinde.svg` (koyu yeşil) + `yerinde-light.svg` (krem) hicolor/scalable/apps; ilk-oturum betiği temaya göre kickoff ikonu + Yesil duvar kağıdı (bayrak dosyalı)

### §8 — sudo + kapasite
- `sudoers.d/wheel`: `%wheel ALL=(ALL) ALL`, izin `440` (doğrulandı).
- `partition.conf` `requiredStorage: 40` (40GB, model+store gömülü) (doğrulandı).

### §9 — Paket + ISO build
- `yerinde-branding` **1.2.0-8** (grub teması + duvar kağıdı doğrulaması; WALLPAPER OK + GRUB THEME OK)
- `yerinde-ai-assistant` **1.2.0-3** (VENDOR OK: onnxruntime + ctranslate2; PIPER OK)
- Çift repo güncellendi: `/home/yerinde/yerinde-repo/x86_64` (git) + `/home/yerinde/yerinde-project/repo/x86_64` (ISO pacman.conf `file://`)
- `repo-add yerinde.db.tar.zst`
- git commit: `765c288` (push YOK)
- ISO rebuild: `mkarchiso -v -w work -o out .` (setsid + log), squashfs zstd.
- **ISO:** `out/yerinde-2026.08.15-x86_64.iso` — 19.726.772.224 bayt (~19,7 GB)
- **sha256:** `c94751969485f7bc749c5758b37a818f539ac4ee87b1f5fe6c8dda0574a7a626` (→ `out/SHA256SUMS`)
- ISO içeriği sfs üzerinden doğrulandı: paketler (branding 1.2.0-8, ai-assistant 1.2.0-3, xdotool/ydotool/wmctrl/xclip/xorg-xrandr), store 9 blob / 7,7GB, grub teması, 5 duvar kağıdı, 80-uinput.rules, sysusers uinput, users.conf, ydotool wants symlink, SDDM Main.qml, finalize UEFI/BIOS dalları, yerinde-live.desktop koruması.

### §10 — Build doğrulamaları (build-iso.sh)
- GGUF enjeksiyonu + manifest doğrulaması
- **Orphan blob temizliği EKLENDİ:** ollama create, ham GGUF kopyalarını da blobs/'a yazar ama manifest referans vermez → manifest digest'leri toplanıp referanssız blob'lar silinir. (v1.2'de 2 orphan ~8,2GB; otomatikleştirildi)
- Store son hali: **9 blob / 7,7GB** (llama3.1 + qwen2.5-coder)

---

## 2. Test Listesi (kurulum sonrası — VM testi YAPILMADI, manuel liste)

1. **Canlı oturum:** Giriş yapınca hiçbir şey otomatik açılmaz; menüden "YERINDE AI Asistan" tıklanınca **Gemini API anahtar ekranı** gelir (root evinde config yok → varsayılan).
2. **Canlı oturum:** `ollama list` → `llama3.1` ve `qwen2.5-coder:1.5b` (salt-okunur gömülü store servis edilir).
3. **MBR (BIOS) menüsü:** krem yazılar okunur, küçük logo üst-orta, Türkçe alt yazılar, alt satırda "Press [Tab]" YOK; geri sayım "Otomatik başlatma: # saniye".
4. **UEFI kurulu:** temalı GRUB menüsü (krem zemin + yeşil metin + logo) VEYA systemd-boot fallback — `/etc/yerinde-bootloader` içeriği (`grub` / `systemd-boot`) ile hangi yolun kullanıldığı raporlanır.
5. **SDDM:** oturum listesinde hem "Plasma" hem "Plasma (Wayland)"; parola alanı odaklı; Enter/Return ile giriş.
6. **Duvar kağıdı seçici:** 5 ton (Hologram-Mavi, Krem, Dalga-Mavi, Yesil, Mor); varsayılan Yesil.
7. **Wayland oturumu:** `ydotool`/`xdotool`/`wmctrl`/`xclip` çalışır (masaüstü / fare / klavye komutları); `uinput` grubu üyede, `80-uinput.rules` aktif.
8. **UEFI + MBR kurulum regresyonu:** kurulum her iki yolda da başarılı; canlı sorun yok.

---

## 3. Sapmalar / Notlar
- Store hedefi `airootfs/usr/share/ollama/` değil `airootfs/var/lib/ollama/models` (ollama paketi `/usr/share/ollama -> /var/lib/ollama` symlink'i üstüne dizin yazmak `cp -af`'i kırar; `OLLAMA_MODELS=/usr/share/ollama/models` symlink ile çözülür). — v1.2'den beri.
- `google-genai --no-deps` KULLANILMAZ (import kırar), tüm deps ile kurulur. — v1.2'den beri.
- Orphan blob temizliği artık build-iso.sh'te otomatik.
- sfs içinde GGUF'lar 755 görünür (644 değil) — mkarchiso profiledef'in dizin girişini dosyalara özyinelemeli uygulamasından. Dünya-okunur, ollama sadece okur → zararsız. Kaynak tarafı (airootfs) prep'te 644 olarak doğrulandı; gelecekteki build'ler için profiledef `["/usr/share/yerinde-modeller/"]="0:0:644"` yapıldı.
- `yerinde-branding` PKGBUILD (kaynak) `/home/yerinde/yerinde-project/packages/yerinde-branding/` altındadır (git repo'da yalnızca ikili paket izlenir).
