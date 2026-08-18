# YERİNDE OS v1.1 — TEK PROMPT
UEFI kurulum sorunsuz; aşağıdaki maddeleri uygula ve TEK rebuild yap.

KURALLAR: UEFI kurulum mantığına DOKUNMA; VM testi YAPMA;
git push YOK; setsid+log; zstd; Türkçe rapor.

## 1) KURULU MBR syslinux: GÜVENİLİR + MARKALI + TÜRKÇE
Finalize BIOS dalında:
- B="$R/boot"; syslinux --install "$B"
- Modüller: ldlinux.c32 libcom32.c32 libutil.c32 menu.c32 vesamenu.c32
- cp /run/archiso/bootmnt/arch/boot/syslinux/splash.png "$B/"
- DISK'e mbr.bin yaz; parted ile boot bayrağı
- syslinux.cfg:
  UI vesamenu.c32
  MENU TITLE Yerinde OS
  MENU BACKGROUND splash.png
  TIMEOUT 50
  ONTIMEOUT yerinde
  MENU AUTOBOOT Yerinde OS # saniye içinde başlatilacak.
  LABEL yerinde
    MENU DEFAULT
    MENU LABEL Yerinde OS
    LINUX /vmlinuz-linux
    INITRD /initramfs-linux.img
    APPEND root=UUID=<UUID> rw quiet
  LABEL fallback
    MENU LABEL Yerinde OS (kurtarma modu)
    LINUX /vmlinuz-linux
    INITRD /initramfs-linux-fallback.img
    APPEND root=UUID=<UUID> rw

## 2) ISO BIOS MENÜSÜ TÜRKÇE
Profile syslinux cfg'lerinde görünen etiketler:
- "install medium (x86_64, BIOS)" -> "kurulum ortamı (x86_64, BIOS)"
- "with speech" -> "sesli okuma ile"
- "Boot existing OS" -> "Mevcut işletim sistemini başlat"
- "Run Memtest86+" -> "Bellek testi çalıştır (Memtest86+)"
- "Hardware Information (HDT)" -> "Donanım Bilgisi (HDT)"
- "Reboot" -> "Yeniden Başlat"
- "Power Off" -> "Bilgisayarı Kapat"
Yollara DOKUNMA.

## 3) ISO UEFI MENÜSÜ (yapılabildiği kadar)
- grep -rl "install medium" /usr/bin/mkarchiso /usr/lib/archiso
  bul, sed: "install medium"->"kurulum ortamı",
  "with speech"->"sesli okuma ile"
- ÇEVRİLEMEZ (dokunma): "Reboot Into Firmware Interface",
  "EFI Shell", "Press [Tab] to edit options"

## 4) KLAVYE TR
- sequence: welcome'dan sonra `keyboard` modülü
- modules/keyboard.conf: defaultLayout: tr
- airootfs/etc/X11/xorg.conf.d/00-keyboard.conf:
  InputClass + MatchIsKeyboard + Option "XkbLayout" "tr"
- airootfs/etc/vconsole.conf: KEYMAP=trq

## 5) KDE BAŞLAT İKONU + İLK OTURUM BETİĞİ
- hicolor/scalable/apps/yerinde.svg (koyu yeşil zeminli ikon)
- hicolor/scalable/apps/yerinde-light.svg (krem zeminli ikon)
- usr/share/yerinde/kde/yerinde-first-run.sh (755):
  6 sn bekle; bayrak yoksa:
  tema koyuysa icon=yerinde-light değilse icon=yerinde
  (kickoff writeConfig); duvar kağıdını org.kde.image ile
  Yerinde-Destek-Yesil yap; bayrak dosya yaz
- etc/xdg/autostart/yerinde-first-run.desktop (OnlyShowIn=KDE)

## 6) DESTEK DUVAR KAĞITLARI
Kaynak: ~/yerinde-project/branding/wallpapers/
(5 png: destek-hologram-mavi, destek-krem, destek-dalga-mavi,
destek-yesil, destek-mor)
Her biri: usr/share/wallpapers/Yerinde-Destek-<Ton>/
  metadata.desktop + contents/images/wallpaper.png
Ton adları: Hologram-Mavi, Krem, Dalga-Mavi, Yesil, Mor
SDDM krem arka plana DOKUNMA.

## 7) PAKET + REPO
- yerinde-branding pkgrel bump; yeni dosyaları da kursun
- repo-add + yerelde commit (push YOK)

## 8) BUILD + RAPOR
setsid+log, zstd, sha256. Rapor + checklist:
1) BIOS VM: kurulum -> ISO çıkar -> reboot -> menü 5 sn sayıp
   OTOMATİK masaüstüne gitmeli; splash koyu yeşil logolu
2) Installer klavye sayfası: tr seçili, i ğ ş ç doğru
3) İlk login ~6 sn: başlat ikonu Yerinde + duvar kağıdı yeşil destek
4) UEFI regresyon yok