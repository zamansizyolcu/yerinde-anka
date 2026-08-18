# YERINDE ANKA final23 — TEK PROMPT (görsel kalıntı + numpy kalıcı)
BAĞLAM: final21 başarılı (ANKA, keyring, zip, NOESCAPE, 2.8G ISO).
Kalan: GRUB'ta 3'lü logo, Calamares başlığında "OS", asistan
kurulumunda numpy==1.26.4 pin hatası (wheel yok → derleme → gcc yok).
KURALLAR: VM testi YOK; push YOK; setsid+log; grep/ls doğrulamalı;
Türkçe rapor; eksikse FAIL.

## 1) GRUB TEMASI: ÜSTTE 3 YAZI → TEK LOGO
(Ekran kanıtı: başlık + 2 lockup = 3 satır)
- theme.txt: title_text satırını SİL
- zemin/theme görselleri: YALNIZCA 1 adet "yerinde ANKA" lockup
  (üst-orta, küçük) kalacak şekilde YENİDEN üret
- DOĞRULA: theme.txt'te tek image referansı; grep title_text YOK

## 2) CALAMARES BAŞLIK: "OS" KALINTISI → ANKA
- lconvert override'ı YENİDEN üret; hedef metin:
  "Yerinde ANKA Kurulum Sihirbazına hoş geldiniz"
- DOĞRULA: kontrol .ts içinde kullanıcıya görünür "Yerinde OS"
  SIFIR sonuç (UEFI+MBR aynı dosyayı kullanır → ikisi birden düzelir)

## 3) ISO'YA NUMPY/PILLOW (çevrimdışı asistan kurulumu)
packages.x86_64 += python-numpy python-pillow
- DOĞRULA (ls, eksikse FAIL): airootfs/usr/lib/python3*/site-packages/
  altında numpy/ VE PIL/
- opencv: "opencv" paketini ekle; cv2 bağlaması site-packages'te
  VARSA kalır, YOKSA ISO'ya koyma + raporda belirt (best-effort,
  build'i DÜŞÜRMEZ)
- NOT: ~20-30 MB sıkıştırılmış; ince ISO'yu bozmaz

## 4) ASİSTAN REPOSU: NUMPY KALICI DÜZELTME
(asistan kaynak dizini: requirements.txt + kurulum.sh)
- requirements.txt: "numpy==1.26.4" pinini SİL veya "numpy>=2" yap
  (eski pin yeni Python'da wheel bulamaz → kaynak derlemeye düşer)
- kurulum.sh BAŞINA Arch/Yerinde ANKA ön adımı:
  sudo pacman -S --needed python-numpy python-pillow || true
- pip hata verirse Türkçe fallback mesajı:
  "Derleme hatası: numpy sistemden kurulmalı →
   sudo pacman -S python-numpy"
- README'ye "Kurulum" notu ekle
- commit (push YOK)

## 5) REGRESYON KORUMASI (DOKUNMA)
keyring doğumda hazır; zip araçları (ark/zip/unzip/7zip/unrar);
NOESCAPE + TABMSG gizli; Wayland-tek oturum; SDDM krem + Enter +
⟳⏻; 5 duvar kağıdı; sudoers wheel; asistanın KENDİSİ ISO'da YOK
(sadece python kütüphaneleri); ANKA adları; GRUB fallback;
requiredStorage 40.

## 6) PAKET + BUILD + RAPOR
- branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256; dosya adı yerinde-anka-*.iso
- Rapor kanıtları:
  1) theme.txt tek image + title_text YOK (grep)
  2) kontrol.ts içinde "Yerinde OS" SIFIR
  3) numpy/ + PIL/ airootfs ls kanıtı
  4) asistan repo: requirements.txt + kurulum.sh diff'i
- Kullanıcı test listesi:
  • GRUB: üstte TEK "yerinde ANKA" lockup
  • Calamares başlığı: "Yerinde ANKA Kurulum Sihirbazına hoş
    geldiniz" (UEFI+MBR)
  • Kurulu VM: asistan kurulum.sh → numpy derleme hatası YOK
  • Hiçbir ekranda "OS" kalıntısı YOK
  • UEFI+MBR kurulum regresyonu YOK