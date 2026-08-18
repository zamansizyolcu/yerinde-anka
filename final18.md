# YERINDE OS v1.7 — İNCELTME + X11 GÜÇ + METİN CİLASI
KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls doğrulamalı.
REGRESYON KORUMASI: SDDM krem tema + Enter + güç düğmeleri + yan yana
oturum seçici, GRUB teması/fallback, MBR krem menü, 5 duvar kağıdı,
sudoers wheel, ilk-oturum betiği (duvar kağıdı + kickoff ikonu).

## 1) ASİSTANI ISO'DAN TOPTAN ÇIKAR (ISO ~3GB'a insin)
- packages.x86_64'dan SİL: yerinde-ai-assistant, ollama, ydotool,
  python-opencv, python-psutil, python-pillow, portaudio, ffmpeg
- airootfs'ten SİL (ls ile doğrula):
  usr/share/yerinde-modeller/, usr/share/ollama/,
  usr/share/yerinde-ai/, etc/systemd/system/yerinde-ollama-setup.service,
  etc/systemd/system/ollama.service.d/, ydotool drop-in'leri,
  etc/skel/.yerinde/, 80-uinput.rules, modules-load uinput
- multi-user.target.wants'tan ollama/ydotool linklerini SİL
- users.conf defaultGroups: wheel kalsın, uinput/input SİL
- finalize'daki usermod uinput satırını SİL
- NOT: yerinde-ai-assistant REPO'da KALSIN (pacman ile kurulabilir);
  ui.py X11 "zoomed" düzeltmesi repo paketinde uygulansın.
- Rapor: ISO boyutu öncekiyle karşılaştır.

## 2) X11 OTURUMDA KAPAT/YENİDEN BAŞLAT DÜZELTMESİ
a) startplasma-x11 betiğinin ihtiyaçlarını DOĞRULAMALI tamamla:
   betiği grep et (airootfs/usr/bin/startplasma-x11); çağrılan her
   aracın binary'si airootfs'te olsun. Eksikse packages'a ekle
   (beklenen: xorg-xrandr xorg-xrdb xorg-xsetroot xorg-xmessage
   xorg-sessreg). ls ile FAIL-kontrollü doğrula.
b) PAM: etc/pam.d/sddm ve sddm-autologin içinde
   "-session optional pam_systemd.so" satırı YOKSA ekle
   (oturum logind'e kaydolmazsa güç istekleri sessizce reddedilir).
c) Güvenli yedek: KDE menüsüne iki kısayol (branding paketi):
   yerinde-reboot.desktop  Exec=systemctl reboot   (Name=Yeniden Başlat)
   yerinde-poweroff.desktop Exec=systemctl poweroff (Name=Bilgisayarı Kapat)
   (Categories KDE; OnlyShowIn=KDE)
d) polkit-kde-agent-1 packages'ta yoksa ekle.

## 3) KURULUM EKRANINDAN "Calamares" YAZISINI ÇIKAR
- Host'ta qt6-tools yoksa kur (lconvert için).
- lconvert -i /usr/share/calamares/translations/calamares_tr.qm
  -o /tmp/tr.ts
- /tmp/tr.ts içinde başlık çevirisini değiştir:
  "…Calamares kurulum programına hoş geldiniz"
  -> "Yerinde OS Kurulum Sihirbazına hoş geldiniz"
  ("Calamares" geçen diğer Türkçe hedefler de temizlensin;
  kaynak metinlere DOKUNMA)
- lconvert -i /tmp/tr.ts -o airootfs/usr/share/calamares/translations/
  calamares_tr.qm
- Doğrulama: lconvert -i yeni.qm -o kontrol.ts; grep "Calamares"
  hedef metinlerde YOK (kaynaklarda olabilir).

## 4) PAKET + BUILD + RAPOR
- yerinde-branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256
- Rapor kanıtları:
  1) ISO boyutu (hedef ≤ ~3.5GB) + önceki boyut
  2) packages.x86_64 son hali (asistan/ollama YOK)
  3) startplasma-x11 araç listesi + airootfs binary ls kanıtı
  4) pam_systemd satırı kanıtı
  5) kontrol.ts'de "Calamares" hedef metin YOK
- Kullanıcı test listesi:
  • X11 oturumu: Başlat > Oturumu Kapat/Yeniden Başlat çalışır
    (yedek menü kısayolları da çalışır)
  • Kurulum ekranı başlığında "Calamares" YOK
  • Canlı menüde YERINDE asistan YOK; ISO ~3GB
  • UEFI+MBR kurulum, SDDM, GRUB/MBR menüler regresyonsuz
  
EK: PKGBUILD post_install() bildirimi yazdır:
"YERINDE kuruldu. Çevrimdışı mod için:
 systemctl enable --now ollama
 ollama pull llama3.1 && ollama pull qwen2.5-coder:1.5b"
Aynı talimatla README.md üret (GitHub'a gidecek).
