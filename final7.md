İki düzeltme + rebuild (UEFI tarafına DOKUNMA):

## 1) BIOS/MBR BOOTLOADER (bu sefer best-effort DEĞİL)
Finalize'ın BIOS dalını kanıtlanmış syslinux yöntemiyle yaz;
hata olursa finalize FAIL etsin (sessiz geçme):

if [ ! -d /sys/firmware/efi ]; then
  B="$R/boot"
  syslinux --install "$B"
  for m in ldlinux.c32 libcom32.c32 libutil.c32 menu.c32 vesamenu.c32; do
    cp /usr/share/syslinux/$m "$B/"
  done
  DISK=$(lsblk -ndo PKNAME "$(findmnt -n -o SOURCE "$R")")
  PNUM=$(lsblk -no PARTN "$(findmnt -n -o SOURCE "$B")")
  cat /usr/share/syslinux/mbr.bin > "/dev/$DISK"
  parted -s "/dev/$DISK" set "$PNUM" boot on
  UUID=$(lsblk -rno UUID,FSTYPE | awk '$2=="ext4"{print $1; exit}')
  cat > "$B/syslinux.cfg" <<CFG
DEFAULT menu.c32
PROMPT 0
TIMEOUT 50
MENU TITLE Yerinde OS
LABEL yerinde
  MENU DEFAULT
  MENU LABEL Yerinde OS
  KERNEL /vmlinuz-linux
  APPEND root=UUID=$UUID rw
  INITRD /initramfs-linux.img
LABEL fallback
  MENU LABEL Yerinde OS (fallback)
  KERNEL /vmlinuz-linux
  APPEND root=UUID=$UUID rw
  INITRD /initramfs-linux-fallback.img
CFG
fi

## 2) KLAVYE (TR + seçim sayfası)
- settings.conf sequence'ine welcome'dan SONRA `keyboard` modülü ekle
  (Calamares'ın standart "klavye seç + kutuda dene" sayfası gelir).
- modules/keyboard.conf: defaultLayout: tr
- Canlı ortam klavyesi TR olsun:
  airootfs/etc/X11/xorg.conf.d/00-keyboard.conf:
    Section "InputClass"
      Identifier "system-keyboard"
      MatchIsKeyboard "on"
      Option "XkbLayout" "tr"
    EndSection
  airootfs/etc/vconsole.conf:
    KEYMAP=trq

## 3) BUILD
- setsid + log, zstd, sha256
- Rapor: BIOS dalı komutları + klavye sayfası + test checklist'i:
  1) BIOS VM: syslinux menüsü "Yerinde OS" → kurulum → reboot
     → ISO çıkar → DİSKTEN AÇILMALI (syslinux menüsü yine gelmeli)
  2) Installer'da klavye sayfası: "tr" seçili, deneme kutusunda
     i ğ ş ç ö ü doğru yazılmalı
  3) UEFI kurulum hâlâ hatasız (regresyon yok)