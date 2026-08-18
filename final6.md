Calamares shellprocess, komutlardaki $d/$t/$ROOT_DEV gibi shell
değişkenlerini "tanımsız Calamares değişkeni" sanıp modülü
çalıştırmayı reddetti. Kalıcı çözüm: mantığı script dosyasına taşı.

1. airootfs/usr/local/bin/yerinde-finalize.sh oluştur (bash, 755):

#!/bin/bash
R="$1"
exec >>/tmp/finalize.log 2>&1
set -x
mkdir -p "$R/boot"
cp /run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-linux "$R/boot/"
rm -f "$R/etc/xdg/autostart/calamares.desktop"
rm -f "$R/etc/mkinitcpio.conf.d/archiso.conf"
cat > "$R/etc/mkinitcpio.d/linux.preset" <<'PRESET'
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"
PRESETS=('default' 'fallback')
default_image="/boot/initramfs-linux.img"
fallback_image="/boot/initramfs-linux.img"
fallback_options="-S autodetect"
PRESET
for d in dev dev/pts proc sys run; do mount --bind /"$d" "$R/$d"; done
chroot "$R" pacman -Rdd --noconfirm mkinitcpio-archiso || true
chroot "$R" mkinitcpio -P
grep -q ' / ' "$R/etc/fstab" || genfstab -U "$R" >> "$R/etc/fstab"
sed -i 's|/boot/efi|/boot|' "$R/etc/fstab"
if [ -d /sys/firmware/efi ]; then
  if mountpoint -q "$R/boot/efi"; then E="$R/boot/efi"; else E="$R/boot"; fi
  cp "$R/boot/vmlinuz-linux" "$E/"
  cp "$R/boot"/initramfs-linux*.img "$E/" 2>/dev/null || true
  mkdir -p "$E/EFI/BOOT" "$E/loader/entries"
  cp "$R/usr/lib/systemd/boot/efi/systemd-bootx64.efi" "$E/EFI/BOOT/bootx64.efi"
  printf 'default yerinde\ntimeout 5\n' > "$E/loader/loader.conf"
  UUID=$(lsblk -rno UUID,FSTYPE | awk '$2=="ext4"{print $1; exit}')
  cat > "$E/loader/entries/yerinde.conf" <<ENTRY
title Yerinde OS
linux /vmlinuz-linux
initrd /initramfs-linux.img
options root=UUID=$UUID rw
ENTRY
  cat > "$E/loader/entries/yerinde-fallback.conf" <<ENTRY
title Yerinde OS (fallback)
linux /vmlinuz-linux
initrd /initramfs-linux-fallback.img
options root=UUID=$UUID rw
ENTRY
fi
for d in run sys proc dev/pts dev; do umount "$R/$d" 2>/dev/null || true; done

2. profiledef.sh file_permissions'a ekle:
   ["/usr/local/bin/yerinde-finalize.sh"]="0:0:755"

3. shellprocess-finalize.conf SADECE şu olsun:
   dontChroot: true
   timeout: 600
   script:
     - /usr/local/bin/yerinde-finalize.sh ${ROOT}
   (${ROOT} tanımlı Calamares değişkeni; başka değişken YOK.)

4. Rebuild (setsid + log), sha256, kısa Türkçe rapor.