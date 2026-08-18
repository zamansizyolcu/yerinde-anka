# YERINDE v2.0 — YENİDEN ADLANDIRMA: "Yerinde OS" → "Yerinde Ocağı"
HEDEF: Kullanıcıya görünen HER metinde "OS" kalkar, "Ocağı" gelir.
Paket/adlar ASCII kalır (yerinde-branding, yerinde-ai-assistant).
KURAL: grep -ri ile tüm varyantlar bulunur; değişen her dosya
raporda listelenir; wordmark'lı görseller YENİDEN ÜRETİLİR.

## 1) METİN DEĞİŞİMLERİ (case-aware)
"Yerinde OS" → "Yerinde Ocağı"
"yerinde OS" → "yerinde ocağı" (lockup: "yerinde" koyu yeşil +
"OCAĞI" turuncu)
"YERINDE OS" → "YERINDE OCAĞI"
Grep ile BUL ve değiştir (raporda liste):
- iso/yerinde/** : grub.cfg + systemd-boot entry'leri + syslinux
  cfg'leri ("Yerinde Ocağı kurulum ortamı (x86_64, BIOS/UEFI)"),
  profiledef.sh (iso_name/iso_label="YERINDE_OCAGI")
- branding: calamares branding.desc (productName,
  bootloaderEntryName), show.qml, SDDM Main.qml başlığı
- finalize + build-iso.sh: EFI entry adı, GRUB_DISTRIBUTOR=
  "Yerinde Ocağı", systemd-boot loader entry Name
- lconvert override güncelle: "Yerinde Ocağı Kurulum Sihirbazına
  hoş geldiniz"
- .desktop Name'leri ("Yerinde Ocağı")

## 2) GÖRSELLERİ YENİDEN ÜRET (eski wordmark SİLİNİR)
Yeni lockup: "yerinde" (#0B3D2E) + "OCAĞI" (#C74A1F) + alt satır
"AÇIK KAYNAK İŞLETİM SİSTEMİ" (krem)
Üretilecekler:
- yerinde-ocagi-lockup-720.png (SDDM + Calamares sidebar)
- splash.png 640x480 MBR (küçük lockup üst-orta, krem menü alanı)
- GRUB tema zemini 1024x768 (krem + küçük lockup)
Eski yerinde-os-lockup-*.png dosyalarını + referanslarını SİL.

## 3) DOĞRULAMA (FAIL-kontrollü)
- grep -ri "yerinde os" airootfs + iso profili + paket kaynakları
  → kullanıcıya görünür metinde SIFIR sonuç (dizin/repo adları hariç)
- ls: eski lockup YOK, yeni png'ler VAR
- sddm --test-mode log temiz

## 4) REGRESYON KORUMASI (DOKUNMA)
Wayland-tek oturum; SDDM krem + Enter + ⟳⏻; MBR krem menü +
NOESCAPE + Türkçe HELP; GRUB teması + fallback; 5 duvar kağıdı;
sudoers wheel; "Calamares" temizliği; asistan ISO'da YOK;
ilk-oturum betiği.

## 5) PAKET + BUILD + RAPOR
- branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256; dosya adı yerinde-ocagi-*.iso
- Rapor: değişen dosya listesi + grep kanıtı + test listesi:
  1) MBR/UEFI menülerde "Yerinde Ocağı"
  2) SDDM + Calamares başlıklarında "Yerinde Ocağı"
  3) Kurulu GRUB giriş adı "Yerinde Ocağı"
  4) Hiçbir ekranda "OS" kelimesi YOK