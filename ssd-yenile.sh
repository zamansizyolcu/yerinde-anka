#!/bin/bash
# final70: /dev/sda uzerindeki eski Yerinde ANKA kurulumunu son ISO ile yeniler.
# SADECE sda4 (ESP) + sda5 (anka-root) formatlanir; sda1/2/3 (Ventoy + veri) DOKUNULMAZ.
# Calamares akisinin birebir taklidi: unpackfs(rsync) -> users -> yerinde-finalize.sh
# GUVENLIK: host NVRAM'i tmpfs kalkaniyla korur; NVRAM girdisini hedef makinede
# ilk acilista yerinde-grub-varsayilan.service kurar.
set -euo pipefail

ISO=/home/yerinde/yerinde-project/iso/yerinde/out/yerinde-anka-2026.08.23-x86_64.iso
ESP_PART=/dev/sda4
ROOT_PART=/dev/sda5
M=/mnt-yeni-anka
KULLANICI_PAROLA="${1:-45923122}"

log(){ echo -e "[yerinde-kur] $*"; }

# ---- 0. Guvenlik on kontrolleri -------------------------------------------
[ "$(id -u)" = 0 ] || { echo "root gerekli"; exit 1; }
[ -b "$ROOT_PART" ] && [ -b "$ESP_PART" ] || { echo "sda4/sda5 yok"; exit 1; }
[ -f "$ISO" ] || { echo "ISO yok: $ISO"; exit 1; }

for p in sda1 sda2 sda3 sda6; do
  mount | grep -q "^/dev/$p" && { echo "HATA: /dev/$p bagli — dokunma!"; exit 1; }
done

log "hedef dogrulandi:"
lsblk -no NAME,SIZE,FSTYPE,LABEL "$ROOT_PART" "$ESP_PART" | sed 's/^/    /'

# ---- 1. Format (yalnizca hedef iki bolum) ----------------------------------
umount -l "$M" 2>/dev/null || true
umount -l "$M/boot" 2>/dev/null || true
mkfs.vfat -F32 -n YERINDE "$ESP_PART"
mkfs.ext4 -F -L anka-root "$ROOT_PART"

mkdir -p "$M"
mount "$ROOT_PART" "$M"
mkdir -p "$M/boot"
mount "$ESP_PART" "$M/boot"

# ---- 2. unpackfs esdegeri: squashfs -> rsync -------------------------------
mkdir -p /tmp-yeni-sfs
mount -o loop,ro "$ISO" /tmp-yeni-sfs
SFS=/tmp-yeni-sfs/arch/x86_64/airootfs.sfs
[ -f "$SFS" ] || { echo "airootfs.sfs yok"; exit 1; }
mkdir -p /tmp-yeni-root
mount -o loop,ro "$SFS" /tmp-yeni-root

log "dosyalar kopyalaniyor (~9 GB, birkac dakika)..."
rsync -aHAX --info=progress2 \
  --exclude='/run/*' --exclude='/tmp/*' \
  /tmp-yeni-root/ "$M"/
umount /tmp-yeni-root; umount /tmp-yeni-sfs; rmdir /tmp-yeni-sfs 2>/dev/null || true

rm -rf "$M/run"/* "$M/tmp"/* 2>/dev/null || true
chmod 1777 "$M/tmp" 2>/dev/null || true

# ---- 3. Kullanici (parolali; oto-giris kapali) ------------------------------
chroot "$M" useradd -m \
  -G wheel,audio,video,storage,optical,lp,power,network,uinput,input \
  -s /usr/bin/zsh -c 'Yerinde Kullanici' yerinde
printf 'yerinde:%s\n' "$KULLANICI_PAROLA" | chroot "$M" chpasswd
printf 'root:%s\n' "$KULLANICI_PAROLA" | chroot "$M" chpasswd
chroot "$M" systemctl enable sddm NetworkManager 2>/dev/null || true
rm -f "$M/etc/sddm.conf.d/yerinde-autologin.conf"

# ---- 4. finalize: HOSTTAN calistir ($M gostergeriyle; asla 'chroot $M ... /' DEGIL!)
# NVRAM korumasi: host efivarfs gecici olarak ayrilir; NVRAM girdisini hedef
# makinede ilk acilista yerinde-grub-varsayilan.service kurar.
log "yerinde-finalize.sh calistiriliyor..."
EFIVAR_BAGLI=0
mountpoint -q /sys/firmware/efi/efivars && { umount /sys/firmware/efi/efivars && EFIVAR_BAGLI=1; } || true
"$M/usr/local/bin/yerinde-finalize.sh" "$M"
[ "$EFIVAR_BAGLI" = 1 ] && mount -t efivarfs efivarfs /sys/firmware/efi/efivars || true
tail -25 "$M/var/log/yerinde-finalize.log" || true

# fstab'i deterministik yaz (genfstab mukerrer/dogru-uuid sorunlarina karsi)
ROOT_UUID=$(blkid -s UUID -o value "$ROOT_PART")
SW_UUID=$(blkid -s UUID -o value /dev/sda6)
cat > "$M/etc/fstab" <<FSTAB
UUID=$ROOT_UUID	/	ext4	rw,relatime	0 1

UUID=06A2-50B4	/boot	vfat	rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=ascii,shortname=mixed,utf8,errors=remount-ro	0 2

UUID=$SW_UUID	none	swap	defaults	0 0
FSTAB

# cekirdek eslestirmesi: ISO'daki GUNCEL vmlinuz'u kullan (gomulu eski olabilir)
mount -o loop,ro "$ISO" /mnt-yeni-sfs 2>/dev/null || true
[ -f /mnt-yeni-sfs/arch/boot/x86_64/vmlinuz-linux ] && \
  cp /mnt-yeni-sfs/arch/boot/x86_64/vmlinuz-linux "$M/boot/vmlinuz-linux"
umount /mnt-yeni-sfs 2>/dev/null || true

# initramfs + locale
for d in proc sys dev; do mount --bind "/$d" "$M/$d"; done
chroot "$M" mkinitcpio -P
chroot "$M" grub-mkconfig -o /boot/grub/grub.cfg
chroot "$M" locale-gen >/dev/null 2>&1 || true
umount "$M/dev" "$M/sys" "$M/proc"

# swap fstab satiri yukarida yazildi

log "=== DOGRULAMA ==="
echo "-- boot:";            ls "$M/boot" | head
echo "-- grub cfg:";       test -f "$M/boot/grub/grub.cfg" && echo OK
echo "-- EFI BOOTX64:";    test -f "$M/boot/EFI/BOOT/BOOTX64.EFI" && echo OK
echo "-- EFI YerindeANKA:";test -f "$M/boot/EFI/YerindeANKA/grubx64.efi" && echo OK
echo "-- fstab:";          grep -vE '^#' "$M/etc/fstab"
echo "-- kullanici:";      grep yerinde "$M/etc/passwd"
echo "-- oto-giris:";      cat "$M/etc/sddm.conf.d/yerinde-autologin.conf" 2>/dev/null
echo "-- ses servisi:";    test -e "$M/etc/systemd/system/multi-user.target.wants/yerinde-ses.service" && echo OK
echo "-- pipewire linkleri:"; ls "$M/etc/systemd/user/sockets.target.wants/" | grep pipe

umount "$M/boot"; umount "$M"
log "TAMAM — /dev/sda uzerine son sistem kuruldu."
