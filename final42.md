# YERINDE ANKA final42 — MAĞAZA + GÖREV YÖNETİCİSİ + WAYDROID GAPPS + NVIDIA
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## §1 YERINDE MAĞAZASI (Discover yerine — özel Tkinter)
Paket: packages/yerinde-magaza/
- PKGBUILD: pkgname=yerinde-magaza, arch=any
- /usr/bin/yerinde-magaza (Tkinter uygulaması, ~500 satır)
- /usr/share/applications/yerinde-magaza.desktop
ÖZELLİKLER (Türkçe arayüz):
• Sol: kategoriler (İnternet, Grafik, Geliştirme, Ofis, Ses/Video,
  Oyun, Sistem, Eğitim)
• Orta: paket listesi (AppStream + pacman + flatpak birleşik)
  arama kutusu, "kurulu" filtresi
• Sağ: paket detay + "Kur"/"Kaldır"/"Güncelle" butonları
• Alt: işlem kuyruğu + ilerleme çubuğu
• Arka uç: pacman (resmî + yerinde repo), flatpak (Flathub),
  AUR (yay -S --noconfirm)
• "Yenile" butonu: pacman -Sy + flatpak update --appstream
• İlk açılışta Flathub remote'ı otomatik ekle
• Tema: ANKA krem (#EFE9DC) zemin + koyu yeşil (#0B3D2E) başlıklar
  + turuncu (#C74A1F) vurgu
KISAYOL: skel masaüstüne + görev çubuğuna sabitle

## §2 YERINDE GÖREV YÖNETİCİSİ (systemmonitor yerine — özel)
Paket: packages/yerinde-gorev-yoneticisi/
- PKGBUILD: pkgname=yerinde-gorev-yoneticisi, arch=any
  depends=(python python-psutil python-tk)
- /usr/bin/yerinde-gorev-yoneticisi (Tkinter, ~400 satır)
- /usr/share/applications/yerinde-gorev-yoneticisi.desktop
ÖZELLİKLER:
• Sekmeler: Süreçler | Kaynaklar | Performans
• Süreçler: tablo (PID, Ad, CPU%, RAM, Kullanıcı) + "Öldür" butonu
  + arama + sıralama (CPU/RAM sırasına göre)
• Kaynaklar: CPU (tüm çekirdekler), RAM, SWAP, Disk G/Ç —
  CANLI grafik (tkinter.Canvas, 1sn refresh)
• Performans: CPU sıcaklığı (lm_sensors varsa), GPU kullanım
  (nvidia-smi varsa), ağ G/Ç
• Tema: §1 ile aynı ANKA paleti
• Sağ tık → Süreci Öldür / Yeniden Başlat / Dosyaları Aç
• Ctrl+Alt+Delete kısayolu = bu uygulamayı açar (kglobalaccel)

## §3 WAYDROID GAPPS (Play Store'lu)
yerinde-waydroid scriptini GÜNCELLE (final40):
1) Menüye "Kurulum (GAPPS - Play Store)" seçeneği
2) waydroid init -s GAPPS (~1.5GB internetten iner)
3) ISO'ya GÖRÜNTÜ KONMAZ (sadece script)
4) Post-init: Play Store giriş ekranı kullanıcıya bırakılır
5) README notu: "Play Store kurulumu 5-10dk internet hızına bağlı"
NOT: Waydroid gerçek donanımda kernel 5.18+ + binder_linux ister;
VM'de yazılım render ile çalışır (uyarı mesajı)

## §4 NVIDIA SAHİPLİ DRIVER (ana PC otomatik)
packages.x86_64 += nvidia nvidia-utils nvidia-settings
lib32-nvidia-utils libva-nvidia-driver
OTOMATİK TESPİT (finalize.sh + post-install hook):
- lspci | grep -i nvidia → VARSA:
  • /etc/mkinitcpio.conf MODULES+=(nvidia nvidia_modeset
    nvidia_uvm nvidia_drm) + mkinitcpio -P
  • /etc/default/grub GRUB_CMDLINE_LINUX_DEFAULT içine
    "nvidia-drm.modeset=1 nvidia-drm.fbdev=1" ekle + grub-mkconfig
- YOKSA: Nouveau kullan, dokunma
CANLI ORTAM: Nouveau zaten açık (her GPU'da Wayland açılır);
NVIDIA sahipli driver KURULUMDAN SONRA aktif olur.
DOĞRULA: packages.x86_64 ls + finalize hook ls + grep
  "nvidia-drm.modeset" /etc/default/grub (kurulu sistem test VM)

## §5 REGRESYON KORUMASI
final40 üçlüsü (systemmonitor/apper/discover) → §1+§2 ile DEĞİŞTİR
(apper ve discover KALDIRILIR; "Yerinde" özel uygulamalar öncelik)
KORUNACAKLAR: Wayland-tek; SDDM krem+Enter+⟳⏻; ANKA markası;
keyring; zip; NOESCAPE; duvar kağıtları; ydotool/uinput zinciri;
ses 24kHz; tıkla-kur; unpackfs; drkonqi mask; oto-giriş;
Türkçe GRUB fontu.

## §6 BUILD + RAPOR
1) İki yeni paket: makepkg + repo-add (yerinde-magaza,
   yerinde-gorev-yoneticisi)
2) branding pkgrel bump; ISO rebuild setsid+log; sha256
3) Kanıtlar:
   - her iki paketin .desktop ls + bash -n scriptleri
   - packages.x86_64: nvidia ailesi + iki yeni paket
   - finalize hook grep; /etc/default/grub güncelleme satırı
   - yerinde-waydroid GAPPS seçeneği grep
   - ISO boyut (hedef ~3.3GB; +200MB NVIDIA nedeniyle)
4) Kullanıcı test listesi (ana PC + VM):
   • Masaüstü "Yerinde Mağazası" → açılır, arama + kur çalışır
   • Ctrl+Alt+Delete → "Yerinde Görev Yöneticisi" açılır,
     süreç öldürme çalışır
   • "yerinde-waydroid" → GAPPS seçeneği VAR, init başlar
   • NVIDIA PC: nvidia-smi çalışır; Wayland oturumu akıcı
   • Nouveau PC (Intel/AMD): her şey kutudan çalışır
   • UEFI+MBR regresyonu YOK