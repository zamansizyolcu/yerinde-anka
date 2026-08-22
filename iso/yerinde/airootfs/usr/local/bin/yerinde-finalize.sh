#!/bin/bash
R="$1"
exec >>/tmp/finalize.log 2>&1
set -x

if [ -z "$R" ] || [ ! -d "$R" ]; then
  echo "yerinde-finalize: ROOT argümanı geçersiz ($R)" >&2
  exit 1
fi

echo "=== finalize basladi: $(date -Is)"

mkdir -p "$R/boot"
if [ -f /run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-linux ]; then
  cp -v /run/archiso/bootmnt/arch/boot/x86_64/vmlinuz-linux "$R/boot/vmlinuz-linux"
elif [ -f "$R/usr/share/yerinde/vmlinuz-linux" ]; then
  cp -v "$R/usr/share/yerinde/vmlinuz-linux" "$R/boot/vmlinuz-linux"
fi
ls -l "$R/boot/vmlinuz-linux"

rm -f "$R/etc/xdg/autostart/calamares.desktop"
# final33 (unpackfs düzeltmesi): canlı-ortam polkit kuralı kurulu sisteme
# GİRMEZ (parolasız calamares pkexec izni yalnız canlıda geçerliydi).
rm -f "$R/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules"
# final58.md §1: oto-giriş conf'u artık hedefte KALIR — şifresiz kurulumda
# oto-giriş AÇIK; parola konursa ilk açılışta yerinde-autologin-check.service
# (multi-user.target.wants) conf'u siler ve greeter parola sorar.
rm -f "$R/etc/xdg/autostart/yerinde-live.desktop"

rm -f "$R/etc/mkinitcpio.conf.d/archiso.conf"
cat > "$R/etc/mkinitcpio.d/linux.preset" <<'PRESET'
ALL_config="/etc/mkinitcpio.conf"
ALL_kver="/boot/vmlinuz-linux"
PRESETS=('default' 'fallback')
default_image="/boot/initramfs-linux.img"
fallback_image="/boot/initramfs-linux-fallback.img"
fallback_options="-S autodetect"
PRESET

for d in dev dev/pts proc sys run; do
  mkdir -p "$R/$d"
  mount --bind "/$d" "$R/$d"
done

# final63: hedefe yapilan gecici baglar HER CIKIS yolunda cozulur. Kalinti bag,
# kurulumun en sonundaki Calamares umount modulunu sert hata ile dusuruyor
# ("The device 'dev' is mounted ... could not be unmounted"). Once duz, olmazsa
# lazy (-l) umount denenir; efivarfs cocuk baglamasi sys'den ONCE cozulur.
yerinde_finaliz_temizlik() {
  umount "$R/sys/firmware/efi/efivars" >> /tmp/finalize.log 2>&1 \
    || umount -l "$R/sys/firmware/efi/efivars" >> /tmp/finalize.log 2>&1 \
    || true
  local _d
  for _d in run sys proc dev/pts dev; do
    umount "$R/$_d" >> /tmp/finalize.log 2>&1 \
      || umount -l "$R/$_d" >> /tmp/finalize.log 2>&1 \
      || true
  done
}
trap yerinde_finaliz_temizlik EXIT

chroot "$R" systemctl disable sshd livecd NetworkManager-wait-online.service systemd-networkd choose-mirror livecd-talk livecd-alsa-unmuter >> /tmp/finalize.log 2>&1 || true
chroot "$R" systemctl enable NetworkManager sddm >> /tmp/finalize.log 2>&1 || true
# final46 §2: Waydroid Android ortamı için container servisi
chroot "$R" systemctl enable waydroid-container >> /tmp/finalize.log 2>&1 || true
# final18.md §2b: X11 oturumunda kapat/yeniden başlat yetkisi için SDDM PAM'ine
# açıkça pam_systemd satırı (sistem-login include'u sağlar ama garantiye alınır).
for _pf in sddm sddm-autologin; do
  if [ -f "$R/etc/pam.d/$_pf" ]; then
    grep -q 'pam_systemd' "$R/etc/pam.d/$_pf" \
      || sed -i '1i -session optional pam_systemd.so' "$R/etc/pam.d/$_pf"
  fi
done
grep -c 'pam_systemd' "$R/etc/pam.d/sddm" "$R/etc/pam.d/sddm-autologin" >> /tmp/finalize.log 2>&1 || true

rm -f "$R/etc/systemd/system/getty@tty1.service.d/autologin.conf"
rm -rf "$R/etc/systemd/system/getty@tty1.service.d"
# final27.md §3: canlı ortam birimleri hedeften silinir (kurulu sistemde
# /run/archiso olmadığından zaten ateşlenmezdi; temizlik için de kaldırılır).
# drkonqi maskı + ydotoold + uinput zinciri KALIR (kurulu asistan çalışma zamanı).
rm -f "$R/etc/systemd/system/yerinde-live-user.service"
rm -f "$R/etc/systemd/system/multi-user.target.wants/yerinde-live-user.service"
rm -f "$R/usr/local/bin/yerinde-live-user"
rm -f "$R/etc/systemd/system/choose-mirror.service"
rm -f "$R/etc/systemd/system/livecd-alsa-unmuter.service"
rm -f "$R/etc/systemd/system/livecd-talk.service"
rm -f "$R/etc/systemd/system/pacman-init.service"
rm -f "$R/etc/systemd/system/etc-pacman.d-gnupg.mount"
rm -f "$R/usr/local/bin/choose-mirror"
rm -f "$R/usr/local/bin/Installation_guide"
rm -f "$R/usr/local/bin/livecd-sound"
rm -f "$R/etc/ssh/sshd_config.d/10-archiso.conf"
rm -f "$R/etc/systemd/network/20-ethernet.network"
rm -f "$R/etc/systemd/network/20-wlan.network"
rm -f "$R/etc/systemd/network/20-wwan.network"
rm -rf "$R/home/live"
chroot "$R" userdel -r live >> /tmp/finalize.log 2>&1 || true

# final27.md §2: yeni kullanıcıyı asistan çalışma zamanı gruplarına al
# (ydotool /run/ydotool.socket 0660 uinput + /dev/uinput 0660 erişimi).
# usermod -aG idempotenttir; Calamares kullanıcısı uid>=1000 ile tespit edilir.
NEW_USER=$(awk -F: '$3>=1000 && $7!~/nologin|false/ {print $1; exit}' "$R/etc/passwd")
if [ -n "$NEW_USER" ]; then
  chroot "$R" usermod -aG uinput,input "$NEW_USER" >> /tmp/finalize.log 2>&1 || true
  echo "usermod: $NEW_USER -> uinput,input" >> /tmp/finalize.log
  chroot "$R" id "$NEW_USER" >> /tmp/finalize.log 2>&1 || true
else
  echo "UYARI: uid>=1000 kullanıcı bulunamadı (usermod atlandı)" >> /tmp/finalize.log
fi

# final62 §2: OTO-GİRİŞ KARARI KURULUM ANINDA — ilk-açılış betiğine muhtaç değil.
# Parola konmuşsa (shadow hash '$' ile başlar) autologin conf'u HEMEN silinir;
# parolasız kurulumda conf KALIR ama User= gerçek kullanıcı adına düzeltilir
# (kullanıcı 'yerinde' dışında bir ad girdiyse de tutarlı çalışır).
if [ -n "$NEW_USER" ] && [ -f "$R/etc/sddm.conf.d/yerinde-autologin.conf" ]; then
  HASH=$(awk -F: -v u="$NEW_USER" '$1==u{print $2}' "$R/etc/shadow" 2>/dev/null)
  case "$HASH" in
    \$*)
      rm -f "$R/etc/sddm.conf.d/yerinde-autologin.conf"
      echo "final62 §2: $NEW_USER parolalı → oto-giriş KAPALI (greeter parola sorar)" >> /tmp/finalize.log
      ;;
    *)
      sed -i "s/^User=.*/User=$NEW_USER/" "$R/etc/sddm.conf.d/yerinde-autologin.conf"
      echo "final62 §2: $NEW_USER parolasız → oto-giriş AÇIK (User=$NEW_USER)" >> /tmp/finalize.log
      ;;
  esac
fi
rm -f "$R/etc/machine-id"
chroot "$R" systemd-machine-id-setup >> /tmp/finalize.log 2>&1 || true
chroot "$R" hwclock --systohc --utc >> /tmp/finalize.log 2>&1 || true

# final21.md §3: kurulu sistemde paket kurulamama hatasının kökü —
# pacman keyring doğumda hazır: init + populate archlinux
chroot "$R" pacman-key --init >> /tmp/finalize.log 2>&1 || true
chroot "$R" pacman-key --populate archlinux >> /tmp/finalize.log 2>&1 || true

chroot "$R" pacman -Rdd --noconfirm mkinitcpio-archiso >> /tmp/finalize.log 2>&1 || true
# final46 §1: plasma-welcome kaldır (KDE kurulum sihirbazı — Yerinde ANKA'da istenmez)
chroot "$R" pacman -Rns --noconfirm plasma-welcome >> /tmp/finalize.log 2>&1 || true

# final42 §4: NVIDIA sahipli driver otomatik tespit
# Canli ortamda Nouveau acik (her GPU'da Wayland acilir);
# NVIDIA sahipli driver kurulumdan sonra aktif olur.
if lspci 2>/dev/null | grep -qi nvidia; then
  echo "--- NVIDIA tespit edildi: sahipli driver yapilandirmasi" >> /tmp/finalize.log
  # mkinitcpio.conf MODULES+=(nvidia nvidia_modeset nvidia_uvm nvidia_drm)
  if [ -f "$R/etc/mkinitcpio.conf" ]; then
    if ! grep -q 'nvidia_drm' "$R/etc/mkinitcpio.conf"; then
      sed -i 's/^MODULES=(/MODULES=(nvidia nvidia_modeset nvidia_uvm nvidia_drm /' "$R/etc/mkinitcpio.conf"
      echo "finalize: mkinitcpio.conf MODULES nvidia eklendi" >> /tmp/finalize.log
    fi
  fi
  # GRUB_CMDLINE_LINUX_DEFAULT icine nvidia-drm parametreleri
  if [ -f "$R/etc/default/grub" ]; then
    if ! grep -q 'nvidia-drm.modeset' "$R/etc/default/grub"; then
      sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 nvidia-drm.modeset=1 nvidia-drm.fbdev=1"/' "$R/etc/default/grub"
      echo "finalize: GRUB nvidia-drm.modeset=1 eklendi" >> /tmp/finalize.log
    fi
  fi
  chroot "$R" mkinitcpio -P >> /tmp/finalize.log 2>&1
  echo "--- NVIDIA: mkinitcpio + GRUB yapilandirmasi tamamlandi" >> /tmp/finalize.log
else
  echo "--- NVIDIA tespit edilmedi: Nouveau kullaniliyor" >> /tmp/finalize.log
fi

chroot "$R" mkinitcpio -P >> /tmp/finalize.log 2>&1

grep -q ' / ' "$R/etc/fstab" || genfstab -U "$R" >> "$R/etc/fstab"
sed -i 's|/boot/efi|/boot|' "$R/etc/fstab"
echo "--- fstab:" >> /tmp/finalize.log
grep -vE '^#|^$' "$R/etc/fstab" >> /tmp/finalize.log 2>&1 || true

ROOT_DEV=$(findmnt -n -o SOURCE -M "$R")
ROOT_UUID=$(blkid -s UUID -o value "$ROOT_DEV")

if [ -d /sys/firmware/efi ]; then
  echo "--- UEFI: GRUB kurulumu (deneme, final13.md §3)" >> /tmp/finalize.log
  # final59.md §1: efivarfs mount kontrolü — chroot'a bind edilen /sys altında
  # efivars alt bağlaması taşınmayabilir; NVRAM yazımı (grub-install, --no-nvram
  # ASLA) için garantiye alınır.
  if ! mountpoint -q "$R/sys/firmware/efi/efivars"; then
    mkdir -p "$R/sys/firmware/efi/efivars"
    mount -t efivarfs efivarfs "$R/sys/firmware/efi/efivars" \
      && echo "--- efivarfs chroot'a bağlandı" >> /tmp/finalize.log \
      || echo "--- UYARI: efivarfs bağlanamadı (NVRAM girdisi ilk açılışta yerinde-grub-varsayilan ile oluşur)" >> /tmp/finalize.log
  fi
  if mountpoint -q "$R/boot/efi"; then
    ESP="$R/boot/efi"
    ESP_INNER="/boot/efi"
  else
    ESP="$R/boot"
    ESP_INNER="/boot"
  fi
  # final62: paylaşılan ESP (Windows) senaryosu — grub-install --removable
  # EFI/BOOT/BOOTX64.EFI'nın ÜZERİNE yazar; Windows'un kendi fallback
  # yükleyicisini ÖNCE yedekle (geri alma yolu açık kalsın).
  if [ -d "$ESP/EFI/Microsoft" ] || [ -d "$ESP/EFI/MICROSOFT" ]; then
    if [ -f "$ESP/EFI/BOOT/BOOTX64.EFI" ] && [ ! -f "$ESP/EFI/BOOT/BOOTX64.EFI.yerinde-yedek" ]; then
      cp -v "$ESP/EFI/BOOT/BOOTX64.EFI" "$ESP/EFI/BOOT/BOOTX64.EFI.yerinde-yedek" >> /tmp/finalize.log 2>&1 \
        && echo "--- final62: Windows BOOTX64.EFI yedeklendi (.yerinde-yedek)" >> /tmp/finalize.log
    fi
  fi
  GRUB_OK=1
  (
    set -e
    chroot "$R" grub-install --target=x86_64-efi --efi-directory="$ESP_INNER" \
      --bootloader-id=YerindeANKA --removable
    # final61: bazı grub-install/--removable kombinasyonları yalnız EFI/BOOT/
    # BOOTX64.EFI yazıp EFI/YerindeANKA/grubx64.efi'yi atlıyor (VM kanıtı).
    # NVRAM girdisi + yerinde-grub-varsayilan bu yola muhtaç — yoksa BOOTX64'ten kopyala.
    if [ ! -f "$ESP/EFI/YerindeANKA/grubx64.efi" ]; then
      mkdir -p "$ESP/EFI/YerindeANKA"
      cp "$ESP/EFI/BOOT/BOOTX64.EFI" "$ESP/EFI/YerindeANKA/grubx64.efi"
      echo "--- final61: EFI/YerindeANKA/grubx64.efi BOOTX64.EFI'dan tamamlandi" >> /tmp/finalize.log
    fi
    # final37 §2 + §3: yeşil ANKA teması + Türkçe fontlar /boot/grub'a;
    # fontlar ayrıca ESP'ye de gömülür (emniyet — 00_header tema dizinindeki
    # tüm .pf2'leri zaten otomatik yükler).
    mkdir -p "$R/boot/grub/themes"
    cp -r "$R/usr/share/grub/themes/anka" "$R/boot/grub/themes/"
    mkdir -p "$ESP/grub/fonts" "$R/boot/grub/fonts"
    cp "$R/usr/share/grub/themes/anka/anka-tr.pf2" "$ESP/grub/fonts/anka-tr.pf2"
    cp "$R/usr/share/grub/themes/anka/anka-tr.pf2" "$R/boot/grub/fonts/anka-tr.pf2"
    cp "$R/usr/share/grub/unicode.pf2" "$ESP/grub/fonts/unifont.pf2" 2>/dev/null || true
    grep -q '^GRUB_THEME=' "$R/etc/default/grub" 2>/dev/null \
      || echo 'GRUB_THEME="/boot/grub/themes/anka/theme.txt"' >> "$R/etc/default/grub"
    sed -i 's|^GRUB_THEME=.*|GRUB_THEME="/boot/grub/themes/anka/theme.txt"|' "$R/etc/default/grub"
    chroot "$R" grub-mkconfig -o /boot/grub/grub.cfg
    # final15.md §1: GRUB menü yazılarını Türkçeleştir (idempotent).
    # 10_linux alt menüyü "Advanced options for ${OS}" (OS=Yerinde ANKA Linux)
    # diye üretir; 30_uefi-firmware "UEFI Firmware Settings" üretir.
    sed -i 's/Advanced options for Yerinde ANKA Linux/Yerinde ANKA gelişmiş seçenekler/g' "$R/boot/grub/grub.cfg"
    sed -i 's/UEFI Firmware Settings/UEFI Ürün Yazılımı Ayarları/g' "$R/boot/grub/grub.cfg"
    grep -q 'Yerinde ANKA gelişmiş seçenekler' "$R/boot/grub/grub.cfg" \
      && echo "GRUB TR OK: alt menü Türkçeleştirildi" >> /tmp/finalize.log \
      || echo "GRUB TR UYARI: alt menü çevirisi eşleşmedi (submenu üretilmemiş olabilir)" >> /tmp/finalize.log
    grep -q 'UEFI Ürün Yazılımı Ayarları' "$R/boot/grub/grub.cfg" \
      && echo "GRUB TR OK: UEFI Firmware Settings Türkçeleştirildi" >> /tmp/finalize.log \
      || echo "GRUB TR UYARI: UEFI Firmware Settings satırı yok (BIOS sisteminde beklenir)" >> /tmp/finalize.log
  ) >> /tmp/finalize.log 2>&1 || GRUB_OK=0
  if [ "$GRUB_OK" -eq 1 ]; then
    echo "--- UEFI: GRUB OK (yeşil ANKA temalı, final37)" >> /tmp/finalize.log
    echo "grub" > "$R/etc/yerinde-bootloader"
    ls -l "$R/boot/grub/themes/anka" "$R/boot/grub/fonts" "$ESP/EFI/BOOT" "$ESP/grub/fonts" >> /tmp/finalize.log 2>&1
    # final62 §1: KURULUM ANINDA NVRAM garantisi — grub-install --removable
    # NVRAM'e DOKUNMAZ; boot sırası Windows'ta kalır, makine Anka'yi HİÇ
    # açamadan Windows'a gider ve ilk-açılış betiği (yerinde-grub-varsayilan)
    # asla koşamaz (yerinde1 VM kanıtı). Giriş + boot order burada yazılır:
    (
      set -e
      ESP_SRC=$(findmnt -n -o SOURCE -T "$ESP")
      echo "final62: ESP=$ESP SRC=$ESP_SRC PARTUUID=$(blkid -s PARTUUID -o value "$ESP_SRC")" >> /tmp/finalize.log
      echo "final62: $ESP/EFI içerigi:" >> /tmp/finalize.log
      ls "$ESP/EFI/" >> /tmp/finalize.log 2>&1 || true
      DISK=$(lsblk -nro PKNAME "$ESP_SRC" | head -n1)
      PNUM=$(lsblk -nro PARTN "$ESP_SRC")
      [ -n "$DISK" ] && [ -n "$PNUM" ]
      # final62ek: girdi yalnız GERÇEKTEN var olan dosyayı göstersin.
      # (BdsDxe kanıtı: \EFI\YerindeANKA\grubx64.efi NOT FOUND → makine Windows'a düşer)
      ENTRY_PATH='\EFI\YerindeANKA\grubx64.efi'
      if [ ! -f "$ESP/EFI/YerindeANKA/grubx64.efi" ]; then
        ENTRY_PATH='\EFI\BOOT\BOOTX64.EFI'
        echo "final62ek UYARI: EFI/YerindeANKA yok — girdi EFI/BOOT/BOOTX64.EFI'ya yazilacak" >> /tmp/finalize.log
      fi
      # final62ek: eski/yanlış yollu YerindeANKA girdileri temizlenir (yeniden
      # kurulum senaryolarında bozuk girdi makineyi sonsuza dek Windows'a düşürür)
      for bn in $(chroot "$R" efibootmgr 2>/dev/null | grep -i YerindeANKA | awk '{gsub(/\*/,"",$1); print substr($1,5)}'); do
        chroot "$R" efibootmgr -b "$bn" -B >> /tmp/finalize.log 2>&1 \
          && echo "final62ek: eski girdi silindi Boot$bn" >> /tmp/finalize.log || true
      done
      chroot "$R" efibootmgr -c -d "/dev/$DISK" -p "$PNUM" \
        -L YerindeANKA -l "$ENTRY_PATH"
      echo "final62: NVRAM girdisi kuruldu (/dev/$DISK p$PNUM -> $ENTRY_PATH)" >> /tmp/finalize.log
      ANKA_NUM=$(chroot "$R" efibootmgr 2>/dev/null | awk 'tolower($0) ~ /yerindeanka/{gsub(/\*/,"",$1); print substr($1,5); exit}')
      ORDER_NOW=$(chroot "$R" efibootmgr 2>/dev/null | awk '/^BootOrder/{print $2}')
      if [ -n "$ANKA_NUM" ] && [ -n "$ORDER_NOW" ]; then
        NEW_ORDER="$ANKA_NUM"
        OLDIFS=$IFS; IFS=','
        for b in $ORDER_NOW; do
          [ "$b" != "$ANKA_NUM" ] && NEW_ORDER="$NEW_ORDER,$b"
        done
        IFS=$OLDIFS
        chroot "$R" efibootmgr -o "$NEW_ORDER"
        echo "final62: bootorder = $NEW_ORDER (ANKA ilk)" >> /tmp/finalize.log
      fi
    ) >> /tmp/finalize.log 2>&1 \
      || echo "--- UYARI: final62 NVRAM/bootorder yazılamadı — ilk açılışta yerinde-grub-varsayilan tekrar dener" >> /tmp/finalize.log
  else
    echo "--- UEFI: GRUB basarisiz -> systemd-boot fallback" >> /tmp/finalize.log
    cp -v "$R/boot/vmlinuz-linux" "$ESP/vmlinuz-linux" >> /tmp/finalize.log 2>&1
    cp -v "$R/boot/initramfs-linux.img" "$ESP/initramfs-linux.img" >> /tmp/finalize.log 2>&1
    cp -v "$R/boot/initramfs-linux-fallback.img" "$ESP/initramfs-linux-fallback.img" >> /tmp/finalize.log 2>&1 || true
    mkdir -p "$ESP/EFI/BOOT" "$ESP/loader/entries"
    cp -v "$R/usr/lib/systemd/boot/efi/systemd-bootx64.efi" "$ESP/EFI/BOOT/bootx64.efi" >> /tmp/finalize.log 2>&1
    printf 'default yerinde\ntimeout 5\nconsole-mode keep\n' > "$ESP/loader/loader.conf"
    cat > "$ESP/loader/entries/yerinde.conf" <<ENTRY
title Yerinde ANKA
linux /vmlinuz-linux
initrd /initramfs-linux.img
options root=UUID=$ROOT_UUID rw
ENTRY
    cat > "$ESP/loader/entries/yerinde-fallback.conf" <<ENTRY
title Yerinde ANKA (guvenli mod)
linux /vmlinuz-linux
initrd /initramfs-linux-fallback.img
options root=UUID=$ROOT_UUID rw
ENTRY
    echo "systemd-boot" > "$R/etc/yerinde-bootloader"
    ls -l "$ESP" "$ESP/loader" "$ESP/loader/entries" >> /tmp/finalize.log 2>&1
    # final62 §1b: systemd-boot yedeğinde de NVRAM girdisi + sıra kur
    (
      set -e
      ESP_SRC=$(findmnt -n -o SOURCE -T "$ESP")
      DISK=$(lsblk -nro PKNAME "$ESP_SRC" | head -n1)
      PNUM=$(lsblk -nro PARTN "$ESP_SRC")
      [ -n "$DISK" ] && [ -n "$PNUM" ]
      chroot "$R" efibootmgr -c -d "/dev/$DISK" -p "$PNUM" \
        -L YerindeANKA -l '\EFI\BOOT\BOOTX64.EFI' || true
      ANKA_NUM=$(chroot "$R" efibootmgr 2>/dev/null | awk 'tolower($0) ~ /yerindeanka/{gsub(/\*/,"",$1); print substr($1,5); exit}')
      ORDER_NOW=$(chroot "$R" efibootmgr 2>/dev/null | awk '/^BootOrder/{print $2}')
      if [ -n "$ANKA_NUM" ] && [ -n "$ORDER_NOW" ]; then
        NEW_ORDER="$ANKA_NUM"; OLDIFS=$IFS; IFS=','
        for b in $ORDER_NOW; do [ "$b" != "$ANKA_NUM" ] && NEW_ORDER="$NEW_ORDER,$b"; done
        IFS=$OLDIFS
        chroot "$R" efibootmgr -o "$NEW_ORDER" || true
        echo "final62 §1b: bootorder = $NEW_ORDER (systemd-boot)" >> /tmp/finalize.log
      fi
    ) >> /tmp/finalize.log 2>&1 || true
  fi
  echo "--- fstab ESP satiri /boot yapildi" >> /tmp/finalize.log
else
  echo "--- BIOS: syslinux kurulumu (STRICT)" >> /tmp/finalize.log
  (
    set -e
    B="$R/boot"
    mkdir -p "$B"
    [ -f "$B/vmlinuz-linux" ] || { echo "BIOS: $B/vmlinuz-linux yok" >&2; exit 1; }
    for m in ldlinux.c32 libcom32.c32 libutil.c32 menu.c32 vesamenu.c32; do
      cp "/usr/lib/syslinux/bios/$m" "$B/"
    done
    cp /run/archiso/bootmnt/arch/boot/syslinux/splash.png "$B/"
    extlinux --install "$B"
    DISK=$(lsblk -ndo PKNAME "$(findmnt -n -o SOURCE "$R")")
    [ -n "$DISK" ] || { echo "BIOS: disk bulunamadi" >&2; exit 1; }
    cat /usr/lib/syslinux/bios/mbr.bin > "/dev/$DISK"
    BOOT_SRC=$(findmnt -n -o SOURCE "$B")
    PNUM=$(lsblk -no PARTN "$BOOT_SRC")
    if [ -n "$PNUM" ]; then
      parted -s "/dev/$DISK" set "$PNUM" boot on
    fi
    UUID=$(lsblk -rno UUID,FSTYPE | awk '$2=="ext4"{print $1; exit}')
    cat > "$B/syslinux.cfg" <<CFG
DEFAULT yerinde
PROMPT 0
TIMEOUT 50
NOESCAPE 1
UI vesamenu.c32
MENU TITLE Yerinde ANKA
MENU BACKGROUND splash.png
MENU COLOR border       30;44   #FF0B3D2E #00000000 std
MENU COLOR title        1       #FFF4EFE4 #00000000 std
MENU COLOR sel          7       #FF0B3D2E #FFF4EFE4 all
MENU COLOR unsel        0       #FFF4EFE4 #00000000 std
MENU COLOR help         0       #FFE5DCC9 #00000000 std
MENU COLOR timeout_msg  0       #FFF4EFE4 #00000000 std
MENU COLOR timeout      0       #FFF4EFE4 #00000000 std
MENU COLOR msg07        0       #FFE5DCC9 #00000000 std
MENU COLOR tabmsg       0       #FFF4EFE4 #00000000 std
MENU AUTOBOOT Otomatik baslatma: # saniye
MENU TABMSG
LABEL yerinde
  TEXT HELP
  Yerinde ANKA kurulum ortamini BIOS ile baslatir.
  Yerinde ANKA kurmani veya sistem onarmanizi saglar.
  ENDTEXT
  MENU DEFAULT
  MENU LABEL Yerinde ANKA
  LINUX vmlinuz-linux
  INITRD initramfs-linux.img
  APPEND root=UUID=$UUID rw quiet
LABEL fallback
  TEXT HELP
  Yerinde ANKA kurulum ortamini BIOS ile guvenli modda baslatir.
  Son yapilandirmalarin sorunlu oldugu durumlarda kullanilir.
  ENDTEXT
  MENU LABEL Yerinde ANKA (kurtarma)
  LINUX vmlinuz-linux
  INITRD initramfs-linux-fallback.img
  APPEND root=UUID=$UUID rw
CFG
    test -f "$B/vmlinuz-linux" || exit 1
    test -f "$B/initramfs-linux.img" || exit 1
    test -f "$B/ldlinux.c32" || exit 1
    ls -l "$B" >> /tmp/finalize.log
    sync
  ) >> /tmp/finalize.log 2>&1 || {
    echo "--- BIOS: syslinux KURULAMADI -> finalize FAIL" >> /tmp/finalize.log
    exit 1
  }
  echo "--- BIOS: syslinux kuruldu" >> /tmp/finalize.log
fi

yerinde_finaliz_temizlik

# final62ek: log kurulu sistemde de kalsın (parola/NVRAM kararları kanıtı)
cp /tmp/finalize.log "$R/var/log/yerinde-finalize.log" 2>/dev/null || true

echo "=== finalize bitti: $(date -Is)"
