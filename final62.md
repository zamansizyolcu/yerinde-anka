# final62 — ELLE BÖLÜMLEME SONRASI YALNIZ WINDOWS AÇILIYOR + PAROLA HİÇ SORULMUYOR
KURALLAR: önce LOG/kanıt, sonra düzeltme; Türkçe rapor; regresyona DOKUNMA.

## KANIT (kullanıcı testi, 17:02 ISO'su = final61 dahil)
- squashfs içi: `unsquashfs -ll` → autologin-check.sh / grub-varsayilan / finalize.sh
  hepsi `-rwxr-xr-x` (755) → **final61 izin düzeltmesi ISO'da MEVCUT**; sorun başka.
- `grub-install --removable` NVRAM'e DOKUNMAZ (belgeli davranış) → BootOrder
  Windows'ta kalır → makine Anka'yı hiç açamadan Windows'u açar →
  ilk-açılış betiği (yerinde-grub-varsayilan) ASLA koşamaz.
  ⇒ "yalnız Windows açılıyor"un gerçek kökü BU (final59/61 ilk-açılış yaklaşımı
  bu senaryoda yapısal olarak işlevsizdi).

## §1 BOOT: NVRAM + BOOT ORDER ARTIK KURULUM ANINDA (finalize.sh)
1) GRUB_OK=1 dalında (grub-install + grub-mkconfig sonrası):
   - findmnt/lsblk ile ESP'nin DISK+PNUM'u bulunur
   - `chroot efibootmgr -c -d ... -L YerindeANKA -l \EFI\YerindeANKA\grubx64.efi`
     (giriş yoksa)
   - `chroot efibootmgr -o ANKA,...` → ANKA İLK, Windows girdisi korunur
   - hata olursa yalnız UYARI: ilk-açılış yerinde-grub-varsayilan yedek olarak durur
2) systemd-boot fallback dalına da aynı blok (\EFI\BOOT\BOOTX64.EFI yoluyla)
3) Paylaşılan ESP (Windows ESP'si /boot/efi seçilirse): grub-install --removable
   EFI/BOOT/BOOTX64.EFI üzerine yazmadan ÖNCE `.yerinde-yedek` kopyası alınır
   (geri alma yolu logda + Windows kurtarma notuyla aynı ad).

## §2 PAROLA: OTO-GİRİŞ KARARI KURULUM ANINDA (finalize.sh)
- NEW_USER'ın $R/etc/shadow hash'i `$*` ise (gerçek parola) → autologin conf
  kurulumda SİLİNİR → greeter İLK açılıştan itibaren parola sorar.
- Hash boş/!/* ise (parolasız kurulum) → conf KALIR, `User=` satırı gerçek
  kullanıcı adına sed'lenir ('yerinde' dışında ad girilse de tutarlı).
- İlk-açılış yerinde-autologin-check.service YEDOLARAK kalır ve artık
  kullanıcı-bağımsız: uid>=1000 + login kabuk taraması → sonradan konan
  parola bir sonraki açılışta oto-girişi kapatır ('yerinde' varsayımı YOK).

## §3 DESTEK
- packages.x86_64: +gawk (betikler awk kullanıyor; bağımlılık zincirine değil,
  açık listeye alındı)

## §4 REGRESYON (çalışanlara DOKUNMA)
- profiledef file_permissions (final61) AYNEN ✅
- partition.conf requiredStorage 15 (final61) AYNEN ✅
- iki aşamalı Windows-ESP onay mekanizması (final59) AYNEN ✅ (yedek yol artık
  kurulumsal yedekle güçlendirildi)
- SDDM tema/kullanıcı listesi, waydroid/ydotool/ses/piper/duvar kağıtları AYNEN ✅

## §5 BUILD DOĞRULAMA
- prep: FINALIZE-62 OK (NVRAM bloğu + bootorder + yedek + hash kararı + gawk + bash -n)
- post: POST OK (final62) — ISO'ya giren finalize/check içerikleri kanıtlandı
- setsid mkarchiso log: /tmp/opencode/yerinde-iso-build.log; çıktı out/*.iso + SHA256SUMS

## §6 TEST LİSTESİ (VM: 35GB Windows + 15GB boş alan)
1) Elle bölümleme (512M ESP FAT32 + ext4 /) → kurulum bitince reboot:
   **GRUB ÖNDE açılır** ("Windows Boot Manager" menüde os-prober ile VAR)
2) Kurulumda parola VERİLEREK kullanıcı oluştur → reboot → greeter parola sorar
3) Parolayı BOŞ bırak → oto-giriş açık (öğretmen PC senaryosu korunur)
4) Kurulumdan sonra parla konan parola → bir sonraki reboot'ta parola sorulur
5) Tek ESP paylaşımlı senaryo: BOOTX64.EFI.yerinde-yedek oluştu mu + NVRAM sırası
6) BIOS/MBR + tek-disk UEFI regresyonu YOK
