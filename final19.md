# YERINDE OS v1.9 — X11 KALDIRILIYOR, WAYLAND-TEK OTURUM
GEREKÇE: X11'de KWin başlamıyor (süs yok, Alt+F4 ölü, bırakma
menüsü donuk). Wayland tüm özelliklerle sağlam. KULLANICI KARARI:
X11 SİLİNSİN.

## 1) PAKET LİSTESİNDEN X11'İ ÇIKAR
packages.x86_64'dan SİL: xorg-server xorg-xinit xorg-xrandr
xorg-xrdb xorg-xsetroot xorg-xmessage xorg-sessreg xorg-xinput
KALSIN: xorg-xwayland (Wayland üstünde X11 uygulamaları + Tkinter
asistan için ŞART), mesa, libinput.
DOĞRULA: grep ile listede olmadıklarını göster.

## 2) OTURUM DOSYALARI + SDDM
- airootfs/usr/share/xsessions/ DİZİNİNİ SİL
- branding X11 desktop dosyası eklemeyi BIRAK (varsa kaldır)
- /etc/sddm.conf.d/yerinde.conf: [X11] Enable=false
  ([Wayland] Enable=true KALSIN)
- SDDM teması: session ComboBox'ı visible: sessionModel.count > 1
  yap (tek oturumda seçici gizlensin, düzen bozulmasın)

## 3) BUILD BETİĞİ GÜNCELLE (yoksa FAIL yer)
- build-iso.sh + finalize'daki X11TOOLS ls doğrulamalarını
  (xrandr/xrdb/xsetroot/xmessage/sessreg) KALDIR
- YENİ DOĞRULA: usr/share/xsessions YOK + usr/bin/Xorg YOK +
  usr/bin/Xwayland VAR (ls kanıtı)

## 4) REGRESYON KORUMASI (DOKUNMA)
MBR krem menü, GRUB teması+fallback, 5 duvar kağıdı, sudoers wheel,
SDDM krem tema + Enter + ⟳⏻, "Calamares" temizliği, asistan ISO'da
YOK, ilk-oturum betiği, ydotool/Wayland araç zinciri.

## 5) PAKET + BUILD + RAPOR
- branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256
- Rapor kanıtları: packages son hali; xsessions/Xorg YOK ls;
  Xwayland VAR; sddm.conf [X11] Enable=false
- Kullanıcı test listesi:
  1) SDDM: tek oturum "Plasma (Wayland)", giriş sorunsuz
  2) Pencere süsleri + kapat düğmeleri + Alt+F4 ÇALIŞIR
  3) Bırakma menüsü: Uyut/Yeniden Başlat/Kapat tıklanır
  4) Tkinter asistan xwayland üstünde açılır (repo'dan kurulumda)
  5) UEFI+MBR kurulum regresyonu YOK
```

## Not

```text
• Çok eski GPU'lu gerçek makineler Wayland'siz kalabilir — bu,
  bilinçli takas (hedef donanım modern).
• Mevcut VM'de reinstall şart değilse: sudo pacman -Rs xorg-server
  ile X11'i oradan da atabilirsin; ama temiz test = yeni ISO.
```

Bu tur, oturum karmaşasını **kalıcı olarak kapatır**: tek oturum, tam çalışan masaüstü. 🏁