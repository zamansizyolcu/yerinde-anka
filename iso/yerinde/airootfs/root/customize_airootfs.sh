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

# final74 §1: Bluetooth "Forget Device" penceresi TR kataloğu.
# pacstrap pacman'ı --root modunda çalıştırdığından paket scriptlet'leri
# (yerinde-branding.install) güvenilir koşmaz; katalog burada elle
# yazılır (pacstrap SONRASI + squashfs ÖNCESİ = canlı ISO'da kesin).
# Katalog /usr/share/yerinde/locale altında taşınır (bluedevil ile
# dosya çakışmasını önlemek için).
for _m in bluedevil bluedevil5; do
    _src="/usr/share/yerinde/locale/tr/LC_MESSAGES/${_m}.mo"
    if [ -s "$_src" ]; then
        install -Dm644 "$_src" "/usr/share/locale/tr/LC_MESSAGES/${_m}.mo"
        echo "FINAL74: ${_m}.mo -> /usr/share/locale/tr/LC_MESSAGES/ OK"
    fi
done
# Kanıt: birleşik katalog gerçekten yerleşmiş olmalı
if command -v msgunfmt >/dev/null 2>&1; then
    msgunfmt /usr/share/locale/tr/LC_MESSAGES/bluedevil.mo \
        | grep -q "Bu Aygıt Unutulsun mu" \
        && echo "FINAL74: TR bluetooth katalog dogrulandi (Bu Aygıt Unutulsun mu?)"
fi

for _m in tmp run dev/pts dev/shm dev sys/firmware/efi/efivars sys proc; do
  umount "/$_m" 2>/dev/null || umount -l "/$_m" 2>/dev/null
done

exit 0
