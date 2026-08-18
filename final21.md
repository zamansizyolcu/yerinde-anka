# YERINDE v2.1 (final20) — "Yerinde ANKA" + KEYRING + ZIP ARAÇLARI
BAĞLAM: "Ocağı" yeniden adlandırması HİÇ uygulanmamış (menüler hâlâ
"Yerinde OS"). KULLANICI KARARI: yeni ad "Yerinde ANKA".
KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls/grep
DOĞRULAMALI, eksikse FAIL; Türkçe rapor.

## 1) YENİDEN ADLANDIRMA: "Yerinde OS" → "Yerinde ANKA"
case-aware değiştir (grep -ri ile BUL, değişen dosyaları raporda listele):
"Yerinde OS"→"Yerinde ANKA", "yerinde OS"→"yerinde ANKA",
"YERINDE OS"→"YERINDE ANKA", "Yerinde Ocağı" kalıntıları da SİL.
Dokunulacak yerler:
- iso profili: grub.cfg + systemd-boot entry'leri
  ("Yerinde ANKA kurulum ortamı (x86_64, UEFI)"), syslinux cfg
  (başlık + "Yerinde ANKA kurulum ortami (x86_64, BIOS)" + HELP
  metinleri), profiledef iso_label="YERINDE_ANKA"
- calamares branding.desc: productName/bootloaderEntryName
  "Yerinde ANKA"; show.qml; pencere başlığı otomatik güncellenir
- lconvert override YENİDEN: "Yerinde ANKA Kurulum Sihirbazına
  hoş geldiniz" ("Calamares" geçen hedef metin YOK kalsın)
- SDDM Main.qml başlık metni "Yerinde ANKA"
- finalize: EFI entry adı + systemd-boot loader Name "Yerinde ANKA";
  GRUB_DISTRIBUTOR="Yerinde ANKA" (+ sed: "Advanced options for
  Yerinde ANKA"→"Yerinde ANKA gelişmiş seçenekler")
- .desktop Name'leri

## 2) GÖRSELLER YENİDEN ÜRET (eski wordmark'lar SİLİNSİN)
Yeni lockup: "yerinde" (#0B3D2E) + "ANKA" (#C74A1F) + alt satır
"AÇIK KAYNAK İŞLETİM SİSTEMİ" (krem)
Üret: splash.png 640x480 MBR (küçük lockup üst-orta),
yerinde-anka-lockup-720.png (SDDM+Calamares), GRUB zemin 1024x768.
ESKİ yerinde-os-*/yerinde-ocagi-* png'leri + referansları SİL.
DOĞRULA: eski png YOK (ls), yeni png'ler VAR, kaynak metinlerde
"ANKA" geçiyor.

## 3) KEYRING DOĞUMDA HAZIR (paket kurulamama hatasının kökü)
- finalize.sh chroot bölümüne:
  chroot "$R" pacman-key --init >> /tmp/finalize.log 2>&1 || true
  chroot "$R" pacman-key --populate archlinux >> /tmp/finalize.log 2>&1 || true
- CANLI: airootfs/usr/local/bin/yerinde-keyring-init (755) +
  yerinde-keyring.service oneshot (bayrak:
  /var/lib/yerinde-keyring-done) + wants linki
- DOĞRULA: finalize.log pacman-key satırları; service+script ls.

## 4) ZIP ARAÇLARI ISO'DA
packages.x86_64 += ark zip unzip p7zip p7zip-rar unrar
DOĞRULA (ls, eksikse FAIL): airootfs/usr/bin/ → zip, unzip, 7z,
ark; (sağ tık Ayıkla/Arşivle kutudan çıkar gibi çalışır)

## 5) MBR NOESCAPE KONTROL
syslinux.cfg'de "NOESCAPE 1" VAR mı? (ekranda hâlâ "Press [Tab]"
görünüyor) YOKSA ekle → İngilizce ipucu satırı gizlenir.

## 6) REGRESYON KORUMASI (DOKUNMA)
Wayland-tek oturum; SDDM krem + Enter + ⟳ + parola focus;
GRUB teması + fallback; 5 duvar kağıdı; sudoers wheel; asistan
ISO'da YOK; ilk-oturum betiği; ydotool zinciri; requiredStorage 40.

## 7) PAKET + BUILD + RAPOR
- branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256; dosya adı yerinde-anka-*.iso
- Rapor kanıtları:
  1) grep -ri "yerinde os|yerinde ocağı" → kullanıcıya görünür
     metinde SIFIR (dizin adları hariç)
  2) yeni lockup png'ler ls; eski png'ler YOK
  3) finalize.log keyring satırları; zip araçları ls
  4) NOESCAPE satırı grep kanıtı; sddm-test.log temiz
- Kullanıcı test listesi:
  • MBR/UEFI menüler + Calamares + SDDM başlığı: "Yerinde ANKA"
  • "Press [Tab]" satırı YOK
  • Kurulu: sudo pacman -S vlc → imza hatasız (keyring hazır)
  • Sağ tık → Ayıkla/Arşivle çalışır; unzip/zip komutları hazır
  • UEFI+MBR kurulum regresyonu YOK