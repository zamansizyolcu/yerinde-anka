İki BIOS sorunu + rebuild (UEFI'ye DOKUNMA):

## A) TÜRKÇE KARAKTER → ASCII (syslinux CP437, UTF-8 yok)
syslinux'a giren TÜM metinleri harf eşlemesiyle ASCII yap:
ğ→g ş→s ı→i ç→c ö→o ü→u
Hem ISO syslinux cfg'leri hem kurulu syslinux.cfg.
(UEFI systemd-boot menülerinde doğru Türkçe KALSIN.)

ISO BIOS etiketleri:
- "kurulum ortami (x86_64, BIOS)"
- "sesli okuma ile"
- "Mevcut isletim sistemini baslat"
- "Bellek testi (Memtest86+)"
- "Donanim Bilgisi (HDT)"
- "Yeniden Baslat"
- "Bilgisayari Kapat"

## B) OTOMATIK BOOT DÖNGÜSÜNÜ KIR
Kurulu syslinux.cfg'yi en sade kanıtlanmış şablona indir
(ONTIMEOUT / MENU AUTOBOOT satırlarını KALDIR, dosya yolları
baştan "/" OLMADAN, DEFAULT doğrudan label adı):

DEFAULT yerinde
PROMPT 0
TIMEOUT 50
UI vesamenu.c32
MENU TITLE Yerinde OS
MENU BACKGROUND splash.png
LABEL yerinde
  MENU DEFAULT
  MENU LABEL Yerinde OS
  LINUX vmlinuz-linux
  INITRD initramfs-linux.img
  APPEND root=UUID=<UUID> rw quiet
LABEL fallback
  MENU LABEL Yerinde OS (kurtarma)
  LINUX vmlinuz-linux
  INITRD initramfs-linux-fallback.img
  APPEND root=UUID=<UUID> rw

## C) FINALIZE BIOS DALINA DOĞRULAMA
Yazdıktan sonra kontrol et, eksikse FAIL et:
test -f "$B/vmlinuz-linux" || exit 1
test -f "$B/initramfs-linux.img" || exit 1
test -f "$B/ldlinux.c32" || exit 1
ls -l "$B" >> /tmp/finalize.log

## D) BUILD + RAPOR
setsid+log, zstd, sha256.
Rapor: ASCII'ye çevrilen etiketler + finalize.log ls çıktısı.
Test notu: BIOS VM'de menü 5 sn sayıp TEK seferde masaüstüne
gitmeli; metinler bozuk karaktersiz olmalı.