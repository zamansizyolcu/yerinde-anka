# final59 — UEFI ÇİFT ESP: GRUB HER SENARYODA ÖNDE
SORUN: elle bölümlemede 2. ESP'ye kurulan GRUB'u firmware
bulamıyor (NVRAM girdisi yok/arkada) → sadece Windows açılıyor.

## §1 CALAMARES: FALLBACK + NVRAM GARANTİSİ
- bootloader(grub) modülü config:
  installEFIFallback: true
  (seçilen ESP'ye \EFI\BOOT\BOOTX64.EFI yazılır)
- grub-install'a --no-nvram ASLA; efivarfs mount kontrolü ekle
- DOĞRULA: grep installEFIFallback config → true

## §2 KURULUM SONRASI YARDIMCI: yerinde-grub-varsayilan
finalize'a ekle (ilk açılışta bir kez koşar):
1) tüm ESP'leri bul (PARTTYPE c12a7328-...)
2) efibootmgr -v: ANKA girdisi YOKSA oluştur (-l yolu ESP'den
   otomatik oku: /boot/efi/EFI/<id>/grubx64.efi)
3) bootorder: ANKA İLK (efibootmgr -o)
4) BAŞKA ESP (Windows) varsa ve NVRAM yazılamadıysa (VBox gibi):
   iki aşamalı onayla Windows ESP'sine BOOTX64.EFI fallback kopyala
   (geri alma komutu raporda: Windows kurtarma notu)
- log: /var/log/yerinde-grub.log

## §3 REGRESYON
"yanına kur" akışı AYNEN çalışır; tek ESP senaryosu değişmez;
SDDM tema, oto-giriş, os-prober (Windows listede) AYNEN

## §4 BUILD + PUSH
pkgrel bump + makepkg + repo-add; setsid build-iso + sha256;
git push yerinde-anka (KULLANICI İZNİ VAR)

## §5 TEST (VM, tam senaryo)
1) 100GB disk: 35GB Windows + kalan boş
2) elle: 512M ESP FAT32 + ext4 / + 2G swap
3) kurulum → reboot → ISO'suz DOĞRUDAN GRUB açılır
4) GRUB menüsünde "Windows Boot Manager" VAR
5) efibootmgr -o çıktısında ANKA ilk