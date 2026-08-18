# final37 — TIKLA-KUR DELEGE + UEFI YEŞİL TEMA + "ı" GLYPH
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## §1 TIKLA-KUR = kurulum.sh SARICISI (pyrect çöküşünün kökü)
SORUN: script kendi venv+pip -r yolunu koşuyor; pyautogui→pyrect
sdist derlemesi pip build-isolation'da çöküyor. kurulum.sh zaten
doğru yolu biliyor (Wayland filtresi + sistem paketleri).
ÇÖZÜM: tıkla-kur kurulum mantığını SİL; akış:
1) pacman yolu (final27) dene
2) yerel klasör dene → varsa ./kurulum.sh
3) git clone → cd → ./kurulum.sh
4) hiçbiri yoksa final27 mesaj ayrışımıyla hata
KENDİ pip/venv kodu TAMAMEN kalkar. bash -n + grep kanıtı
("pip install -r" satırı scriptte YOK).

## §2 UEFI TEMA: YEŞİL ARKA PLAN + KREM/TURUNCU YAZI
(MBR/syslinux KREM tema AYNEN korunur — DOKUNMA)
- GRUB theme: iso + kurulu sistem:
  background: #0B3D2E düz yeşil + küçük ANKA lockup üst-orta
  menu_normal: krem #EFE9DC; menu_highlight: turuncu #C74A1F
  (seçili satır: turuncu yazı veya turuncu zemin-krem yazı)
  title: "GRUB Açılış Menüsü" krem + "yerinde ANKA" lockup
- ISO UEFI: efiboot grub.cfg'ye set theme=... (tema efiboot içine
  gömülür); kurulu: /boot/grub/themes/anka + GRUB_THEME + grub-mkconfig
- DOĞRULA: theme.txt renk satırları grep; eski siyah menü YOK

## §3 TÜRKÇE GLYPH ("ortamı" → "ortam?")
KÖK: GRUB pf2 fontu Türkçe glyphsuz (gerçek donanımda ı→?).
- grub-mkfont -o anka-tr.pf2 /usr/share/fonts/TTF/DejaVuSans.ttf
  (DejaVu Türkçe tam kapsar)
- ISO UEFI efiboot + kurulu ESP: font göm; grub.cfg/theme
  set font=(...)/anka-tr.pf2
- DOĞRULA: fc-list ile DejaVuSans VAR; pf2 boyut>0; menü metinleri
  "ortamı" olarak kalır (ASCII'ye KAÇMA — font çözümü esastır)

## §4 REGRESYON + BUILD + RAPOR
- MBR krem + NOESCAPE aynen; SDDM/oto-giriş/drkonqi/ydotool
  zinciri; ses 24kHz; ANKA markası; keyring; zip; unpackfs
- pkgrel bump; makepkg; repo-add; ISO rebuild setsid+log; sha256
- Kanıtlar: scriptte "pip install -r" YOK grep; theme.txt renkler;
  pf2 ls; sha256
- Kullanıcı testleri:
  1) UEFI VM: yeşil menü + krem/turuncu + "ortamı" doğru
  2) MBR: krem tema AYNEN (regresyon YOK)
  3) temiz VM: tıkla-kur → clone+kurulum.sh → pyrect hatasız kurulum
  4) gerçek donanım notu: ı/? kontrolü kullanıcıda