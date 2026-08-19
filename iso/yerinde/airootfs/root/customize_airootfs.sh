#!/bin/bash
# final16 §6 düzeltmesi: mkarchiso pacstrap'i root olarak koşturduğunda (-N
# bayrağı yalnız EUID != 0 iken eklenir) pacstrap'ın chroot mount'ları
# (proc/sys/efivarfs/dev/devpts/shm/run/tmp) HOST mount namespace'ine sızar ve
# build bittikten sonra da yerinde kalır. Sonuç: mksquashfs canlı sysfs'i
# yürüyüp saatlerce takılır ("Read failed because...") ve ISO görüntüsüne
# host sysfs/proc/run içeriği karışır.
#
# Bu script arch-chroot'un son adımı olarak çalışır ve squashfs'ten ÖNCE tüm
# sanal dosya sistemlerini sökerek hem takılmayı hem de görüntü kirlenmesini
# engeller. (Önce düz umount, başarısızsa lazy — chroot teardown'ı da bu
# yüzden zaten başarısız umount'u sessizce geçer.)
set +e

# final46 §1: plasma-welcome canlı oturumdan kaldır (KDE kurulum sihirbazı istenmez)
# NOT: umount ÖNCE — pacman /proc /sys /dev gerektirir.
# -Rdd: bağımlılıkları yok say (plasma-meta bağımlılığı yüzünden -Rns başarısız olabilir)
pacman -Rdd --noconfirm plasma-welcome 2>/dev/null || true

# final46 §4: Keşfet (discover) packages.x86_64'ta — kaldırma SİLİNDİ.

for _m in tmp run dev/pts dev/shm dev sys/firmware/efi/efivars sys proc; do
  umount "/$_m" 2>/dev/null || umount -l "/$_m" 2>/dev/null
done

exit 0
