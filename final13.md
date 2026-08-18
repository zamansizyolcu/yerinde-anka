# YERINDE OS v1.3 — TEK FİNAL MASTER PROMPT

BAĞLAM: v1.2 çalışıyor (UEFI+MBR kurulum, AI asistan Gemini+Ollama).
Bu tur: görsel/UX cila + canlı mod davranışı.
KURALLAR: VM testi YAPMA; git push YOK; setsid+log; zstd; Türkçe rapor;
her kopyalama adımı ls ile DOĞRULANIR, eksikse build FAIL.

## 1) CANLI MOD: OTO-BAŞLATMA YOK — TIKLAYINCA GEMINI
- airootfs'e yerinde autostart EKLEME; varsa yerinde-live.desktop SİL.
- airootfs root evine config KOYMA (config yoksa main.py varsayılanı
  gemini → tıklayınca API anahtar ekranı gelir).
- Menü kısayolu paketten gelir (yerinde-ai.desktop); launcher
  ~/.yerinde/app home-kopyası canlıda da çalışır (tmpfs yazılabilir).
- finalize'da koruma: rm -f ${ROOT}/etc/xdg/autostart/yerinde-live.desktop

## 2) MBR syslinux: KREM YAZI + KÜÇÜK LOGO + TAM TÜRKÇE
- splash.png yeniden üret: 640x480, koyu yeşil #0B3D2E zemin,
  lockup ÜST-ORTA, öncekinin ~%60'ı boyutta, menü alanı boş.
- Renkler (yeşil zemin üstüne KREM):
  MENU COLOR title 1 #FFF4EFE4 #00000000
  MENU COLOR sel 7 #FF0B3D2E #FFF4EFE4
  MENU COLOR unsel 0 #FFF4EFE4 #00000000
  MENU COLOR help 0 #FFE5DCC9 #00000000
  MENU COLOR timeout_msg 0 #FFF4EFE4 #00000000
- NOESCAPE 1   (İngilizce "Press [Tab]" satırını gizler)
- TEXT HELP blokları Türkçe: "Yerinde OS kurulum ortamını BIOS ile
  başlatır. Yerinde OS kurmanı veya sistem onarmanı sağlar."
- MENU AUTOBOOT: "Otomatik başlatma: # saniye"
- (ISO syslinux cfg + finalize BIOS dalındaki kurulu cfg ikisinde)

## 3) UEFI KURULU SİSTEM: TEMALI GRUB (KREM ZEMİN + YEŞİL YAZI)
   BAŞARISIZSA systemd-boot FALLBACK (kanıtlı yol)
- packages += grub efibootmgr
- finalize UEFI dalı sırası:
  1) grub-install --target=x86_64-efi --efi-directory=$ESP
     --bootloader-id=YerindeOS --removable
  2) /usr/share/grub/themes/yerinde/: krem #F4EFE4 zemin görseli
     (1024x768), metin/başlık koyu yeşil #0B3D2E, küçük logo üst-orta;
     /etc/default/grub GRUB_THEME yaz
  3) grub-mkconfig -o /boot/grub/grub.cfg
  4) HER ADIM || FALLBACK: mevcut systemd-boot dosyaları
     (EFI/BOOT/bootx64.efi + loader/) aynen kalsın, raporda
     hangi yolun alındığı yazsın.
- ISO'nun kendi UEFI menüsüne DOKUNMA (başlıklar zaten Türkçe).

## 4) DUVAR KAĞITLARI: 5'İ DE (doğrulamalı)
- Kaynak: ~/yerinde-project/branding/wallpapers/ (destek-*.png)
- PKGBUILD 5 tonu da kursun: Hologram-Mavi, Krem, Dalga-Mavi,
  Yesil, Mor → /usr/share/wallpapers/Yerinde-Destek-<Ton>/
  (metadata.desktop + contents/images/wallpaper.png)
- cp sonrası ls ile 5 metadata.desktop DOĞRULA; eksikse FAIL.
- Varsayılan: Yerinde-Destek-Yesil (ilk oturum betiğiyle).

## 5) SDDM: X11+WAYLAND SEÇİCİ + ENTER İLE GİRİŞ
- packages += xorg-server xorg-xrandr xorg-xinit
- Tema: parola alanı odaklı + Keys Return/Enter -> login()
- Oturum listesinde hem "Plasma" hem "Plasma (Wayland)" görünsün.

## 6) ASİSTAN WAYLAND/X11 ARAÇLARI
- packages += xdotool ydotool wmctrl xclip alsa-utils
- airootfs/etc/udev/rules.d/80-uinput.rules:
  KERNEL=="uinput", MODE="0660", GROUP="uinput"
- sysusers: g uinput 790; users.conf defaultGroups += wheel uinput input
- ydotool.service enable (airootfs wants sembolik link)

## 7) AI PAKETİ SAĞLAMLAŞTIRMA (regresyon koruması)
- Launcher home-kopyası aynen kalsın (/usr/bin/yerinde → ~/.yerinde/app).
- GGUF enjeksiyonu DOĞRULAMALI:
  ~/yerinde-project/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf ve
  Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf →
  airootfs/usr/share/yerinde-modeller/ (chmod 644, ls ile FAIL-kontrollü)
- Ollama store BUILD'de önceden üretilir (live RAM'i şişmesin):
  OLLAMA_MODELS=$STAGING ile serve+create, sonra store'u
  airootfs/usr/share/ollama/ altına kopyala (manifest+blob ls DOĞRULA)
- airootfs/etc/systemd/system/ollama.service.d/yerinde.conf:
  Environment="OLLAMA_MODELS=/usr/share/ollama/models"
- yerinde-ollama-setup oneshot: model yoksa VE store yazılabilirse
  (touch testi) create et; live read-only'de create DENEMEZ.
  ollama.service + setup, airootfs multi-user.target.wants/ linkleri.
- pip: BAĞIMLILIKLI → piper-tts faster-whisper;
  --no-deps → google-genai pyaudio ollama sounddevice numpy
  vendor'da onnxruntime + ctranslate2 DOĞRULA (yoksa FAIL).
- voices/'te *.onnx yoksa build'de indir: rhasspy/piper-voices
  tr/tr_TR/lessya/medium (.onnx + .onnx.json).
- main.py _play_audio yedekli yol:
  a) pya.open 24000 → b) except: 48000 + np.repeat(x2) →
  c) except: aplay -q -f S16_LE -r 24000 -c 1 subprocess;
  başlangıçta varsayılan çıkış cihazını logla.
- KDE başlat ikonu (yapılmadıysa): hicolor apps/ yerinde.svg (koyu
  yeşil) + yerinde-light.svg (krem); ilk oturum betiği temaya göre
  kickoff icon yazsın + duvar kağıdını Yesil yapsın (bayrak dosyalı).

## 8) SUDO + KAPASİTE
- airootfs/etc/sudoers.d/wheel: %wheel ALL=(ALL) ALL (440)
- partition.conf requiredStorage: 40

## 9) PAKET + BUILD
- yerinde-branding + yerinde-ai-assistant pkgrel bump
- makepkg, repo-add, commit (push YOK)
- ISO rebuild setsid+log; sha256

## 10) RAPOR + TEST LİSTESİ
1) Canlı: login'de hiçbir şey otomatik açılmaz; menüden tıklayınca
   Gemini API anahtar ekranı gelir
2) Canlı: ollama list → 2 model (read-only store'dan serve)
3) MBR menü: krem yazı okunur, logo küçük, alt metinler Türkçe,
   "Press [Tab]" yok
4) UEFI kurulu: temalı GRUB (krem zemin/yeşil yazı) VEYA fallback
   systemd-boot — raporda hangisi
5) SDDM: X11+Wayland seçici; Enter ile giriş
6) Duvar kağıdı seçicide 5 ton
7) Wayland oturumunda: masaüstünü göster / fare / klavye komutları
8) UEFI+MBR kurulum regresyonu yok