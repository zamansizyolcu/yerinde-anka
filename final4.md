İki sorun kaldı; ikisini de kalıcı çöz ve ISO'yu yeniden derle.

SORUN 1: mkinitcpio hatası sürüyor ('/boot/vmlinuz-linux' must be
readable, preset 'archiso'). shellprocess@finalize pratikte
çalışmamış. Önce teşhis et:
- ~/.cache/Calamares/Calamares.log içinde shellprocess satırlarını oku, raporla
- settings.conf sequence'ini yazdır

KALICI ÇÖZÜM (@@ROOT@@'a güvenme, /mnt ile açık yaz):
1. Kernel'i sfs içine göm (archiso /boot'u temizlese bile bu yol kalır):
   cp work/iso/arch/boot/x86_64/vmlinuz-linux airootfs/usr/share/yerinde/vmlinuz-linux
2. shellprocess-finalize.conf (dontChroot: true), script:
   - "cp -v /mnt/usr/share/yerinde/vmlinuz-linux /mnt/boot/vmlinuz-linux > /tmp/finalize.log 2>&1 || cp -v /run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-linux /mnt/boot/vmlinuz-linux >> /tmp/finalize.log 2>&1"
   - "ls -l /mnt/boot/vmlinuz-linux >> /tmp/finalize.log 2>&1"
   - "rm -f /mnt/etc/mkinitcpio.conf.d/archiso.conf"
   - "chroot /mnt pacman -Rdd --noconfirm mkinitcpio-archiso >> /tmp/finalize.log 2>&1 || true"
   - "chroot /mnt mkinitcpio -P >> /tmp/finalize.log 2>&1"
3. sequence'de düz `initcpio` modülü VARSA KALDIR;
   shellprocess@finalize umount'tan hemen önce olsun.

SORUN 2: Boot ekranının tepesinde hâlâ ARCH LOGOSU var.
1. file syslinux/splash.png ile boyut/formatı öğren
2. rsvg-convert ile lockup SVG'sinden AYNI boyutta, koyu yeşil
   (#0B3D2E) zeminli PNG üret; gerekirse 256 renge indir ve
   syslinux/splash.png üzerine yaz
3. Olmazsa splash satırını SİL (metin menü yeter, Arch logosu gitsin)
4. Kernel/initrd yollarına dokunma

SON:
- work/out temizle, setsid + log ile derle
- sfs 2,5-3,5G kontrolü + SHA256
- Rapor: finalize.log okuma talimatı dahil (hata olursa kullanıcı
  canlı ortamda tail /tmp/finalize.log ile baksın)