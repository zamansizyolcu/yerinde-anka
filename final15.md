# YERINDE OS v1.5 — GÖRSEL/OTURUM CİLASI (TEK REBUILD)
KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls/doğrulamalı;
regresyon koruması: MBR syslinux krem menü, 5 duvar kağıdı, ollama
store+GGUF, sudoers wheel, launcher home-kopyası AYNEN kalacak.

## 1) GRUB TEMASI: KOYU + BÜYÜK + YEŞİL/TURUNCU
Sorun: seçili giriş BEYAZ yazı krem zeminde GÖRÜNMÜYOR, yazılar küçük.
/usr/share/grub/themes/yerinde/theme.txt:
- item_color:          #0B3D2E (koyu yeşil)
- selected_item_color: #C74A1F (turuncu)   ← beyaz YASAK
- item_background:     #00000000
- selected_item_pixmap_style: koyu yeşil yarı saydam şerit
  (select_*.png: #0B3D2E ~%20 opaklık)
- item_font:  32px; title_font: 44px (grub-mkfont ile DejaVuSans'tan
  .pf2 üret, theme fonts/ içine koy; unicode Türkçe karakter destekli)
- title-text: "Yerinde OS" (logo yanında, koyu yeşil, 44px)
- "GRUB Açılış Menüsü" yazısını KALDIR
/etc/default/grub: GRUB_DISTRIBUTOR="Yerinde OS"
grub.cfg sed çevirileri (her mkconfig sonrası):
  "Advanced options for Yerinde OS" -> "Yerinde OS gelişmiş seçenekler"
  "UEFI Firmware Settings"          -> "UEFI Ürün Yazılımı Ayarları"
finalize: grub-mkconfig sonrası sed uygula (idempotent).

## 2) SDDM TEMASI: YERLEŞİM + GÜÇ DÜĞMELERİ + OTURUM AKTARIMI
Kaynak: ~/yerinde-project/branding/sddm/yerinde/Main.qml
a) Oturum ComboBox'ını AŞAĞI taşı: parola alanının altı,
   Giriş düğmesinin üstü (yatay ortada, "Oturum:" etiketiyle).
b) Giriş düğmesinin YANINA iki ikon düğmesi ekle:
   ⟳ yeniden başlat  -> onClicked: sddm.reboot()
   ⏻ kapat          -> onClicked: sddm.powerOff()
   (canReboot/canPowerOff false ise gizle)
c) OTURUM SEÇİMİ GERÇEKTEN İŞLESİN (X11 bug'ı):
   login çağrısı BİREBİR: sddm.login(name, password, session.currentIndex)
   ComboBox model: sessionModel; seçim değişince currentIndex güncel.
   (Şu an seçim görmezden geliniyor, hep Wayland açılıyor.)
d) Parola focus + Enter ile giriş + build-zamanı sddm --test-mode
   doğrulaması (v1.4 aynen; "Cannot assign" varsa FAIL).

## 3) X11 SİSTEM SAĞLAMLAŞTIRMA
- /etc/sddm.conf.d/yerinde.conf: [X11] Enable=true (zaten var, doğrula)
- airootfs/usr/share/xsessions/plasma.desktop:
  Exec=startplasma-x11, TryExec=startplasma-x11 (doğrula)
- Test notu rapora: kurulu sistemde X11 seçilince
  `echo $XDG_SESSION_TYPE` -> x11 beklenir.

## 4) ASİSTAN: CANLI'DA GEMINI İLE BAŞLASIN
Sorun: paket, geliştiricinin KİŞİSEL config/*.json dosyalarını
kopyalıyor (model_provider=ollama geliyor) → canlıda Gemini açılmıyor.
- PKGBUILD: cp listesinden config/*.json ÇIKAR; paket TEMİZ config
  taşısın: {"model_provider":"gemini"} dışında anahtar İÇERMESİN.
- Kurulu sistem davranışı DEĞİŞMEZ: skel config ollama varsayılanlı
  (yeni kullanıcı çevrimdışı başlar), canlı root config'siz → GEMINI
  API anahtar ekranı.
- Doğrulama: pakette `grep -r gemini_api_key` BOŞ dönmeli (kişisel
  anahtar sızıntısı YASAK) → doluysa FAIL.

## 5) PAKET + BUILD + RAPOR
- yerinde-branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256
- Rapor kanıtları:
  1) theme.txt renk/font satırları + grub.cfg sed sonrası menü adları
  2) Main.qml: sddm.login(...,session.currentIndex) satırı + reboot/
     powerOff düğmeleri + ComboBox yeni konumu
  3) pakette kişisel config YOK (grep kanıtı)
  4) sddm-test.log temiz
- Kullanıcı test listesi:
  • GRUB: ilk giriş TURUNCU seçili görünür, yazılar büyük/koyu,
    alt girişler Türkçe
  • SDDM: oturum listesi altta; Giriş yanında ⟳ ve ⏻; X11 seçince
    masaüstü x11 olur; Enter çalışır
  • Canlı: yerinde'ye tıklayınca GEMINI anahtar ekranı gelir