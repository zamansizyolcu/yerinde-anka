# YERİNDE OS — FİNAL CİLA PROMPT (v2)

BAĞLAM: Yerinde OS kuruldu ve açılıyor (manuel kurtarma ile kanıtlandı).
Şimdi kanıtlanan adımları ISO'ya kalıcı göm; gelecek kurulumlar
SIFIRDAN hatasız bitsin. Proje hazır — sadece aşağıdakileri değiştir
ve yeniden derle.

## KURALLAR
- VM/QEMU testi YAPMA; kullanıcı test eder.
- git push YAPMA; sadece raporda komut ver.
- Build sırasında airootfs içine /proc,/sys,/dev MOUNT ETME.
- zstd sıkıştırma; sfs 5G'yi geçerse DUR.
- setsid + /tmp/opencode/build.log ile ayrılmış build.
- Türkçe rapor.

## 1) CALAMARES SEQUENCE (settings.conf)
- mount'tan sonra `fstab` modülü EKLE.
- `initcpio` ve `bootloader/grub` modüllerini KALDIR
  (hepsini finalize yapacak).
- Sıra: welcome, partition, mount, unpackfs, fstab, users,
  displaymanager, shellprocess@finalize, umount, finish

## 2) shellprocess-finalize.conf (dontChroot: true, ${ROOT} makrosu)
Sırayla şu komutları yaz (her çıktı /tmp/finalize.log'a eklensin):

1.  mkdir -p ${ROOT}/boot
2.  cp /run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-linux ${ROOT}/boot/
3.  rm -f ${ROOT}/etc/xdg/autostart/calamares.desktop
    (canlı ortamdaki installer autostart'ı kurulu sisteme taşınmasın)
4.  rm -f ${ROOT}/etc/mkinitcpio.conf.d/archiso.conf
5.  ${ROOT}/etc/mkinitcpio.d/linux.preset dosyasını standart yaz:
    ALL_config="/etc/mkinitcpio.conf"
    ALL_kver="/boot/vmlinuz-linux"
    PRESETS=('default' 'fallback')
    default_image="/boot/initramfs-linux.img"
    fallback_image="/boot/initramfs-linux.img"
    fallback_options="-S autodetect"
6.  for d in dev dev/pts proc sys run; do mount --bind /$d ${ROOT}/$d; done
7.  chroot ${ROOT} pacman -Rdd --noconfirm mkinitcpio-archiso || true
8.  chroot ${ROOT} mkinitcpio -P
9.  UEFI ise ([ -d /sys/firmware/efi ]):
    - ESP=${ROOT}/boot/efi (yoksa ${ROOT}/boot içinde vfat mount'u bul)
    - cp ${ROOT}/boot/vmlinuz-linux $ESP/
    - cp ${ROOT}/boot/initramfs-linux.img $ESP/
    - cp ${ROOT}/boot/initramfs-linux-fallback.img $ESP/ 2>/dev/null || true
    - mkdir -p $ESP/EFI/BOOT $ESP/loader/entries
    - cp ${ROOT}/usr/lib/systemd/boot/efi/systemd-bootx64.efi $ESP/EFI/BOOT/bootx64.efi
    - loader.conf: default yerinde, timeout 5
    - entries/yerinde.conf:
      title Yerinde OS
      linux /vmlinuz-linux
      initrd /initramfs-linux.img
      options root=UUID=<kök ext4 UUID> rw
      (UUID'yi runtime'da blkid/lsblk ile ${ROOT} mount'undan oku)
    - entries/yerinde-fallback.conf: aynı ama initrd fallback img
    - sed -i 's|/boot/efi|/boot|' ${ROOT}/etc/fstab
      (ESP kalıcı olarak /boot'ta → güncellemeler ESP'ye gider)
10. BIOS ise (best-effort, başarısız olursa kurulumu DURDURMA, logla):
    - syslinux/extlinux ile ${ROOT}/boot'a kurulum + MBR boot record
    - syslinux.cfg: MENU TITLE Yerinde OS, kernel/initrd + root=UUID
    - hata olursa /tmp/finalize.log'a yaz, devam et
11. for d in run sys proc dev/pts dev; do umount ${ROOT}/$d; done

## 3) BIOS SPLASH: LOGOLAR ÜSTTE
- syslinux/splash.png'i yeniden üret: 640x480, koyu yeşil #0B3D2E zemin,
  lockup (ikon + yerinde OS + AÇIK KAYNAK İŞLETİM SİSTEMİ) ÜST-ORTA.
- Mevcut splash ile AYNI format (8-bit RGBA PNG) olsun.
- syslinux.cfg metinleri zaten markalı; yollara dokunma.

## 4) BUILD
cd ~/yerinde-project/iso/yerinde
sudo rm -rf work out
setsid ile mkarchiso -v -w work -o out . > /tmp/opencode/build.log 2>&1
- sfs boyutu 2,5-3,5G olmalı; sha256sum üret.

## 5) RAPOR (Türkçe)
- Değişen dosyalar (settings.conf, finalize conf, splash)
- ISO yolu + boyut + SHA256
- Manuel test checklist'i:
  1) UEFI VM: systemd-boot "Yerinde OS" → kurulum HATASIZ
  2) Reboot (ISO yok) → diskten açılış → SDDM → masaüstü
  3) Kurulu sistemde calamares autostart YOK
  4) /etc/fstab'da ESP /boot olarak görünüyor
  5) sudo pacman -Sy → yerinde repo senkron
  6) BIOS VM: markalı splash + menü (bootloader best-effort)
- Push komutları (çalıştırma):
  cd ~/yerinde-repo && git add . && git commit -m "yerinde os 1.0 final" && git push