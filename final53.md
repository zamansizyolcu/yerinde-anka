# final53 — ÇİFT BOOT + SDDM KULLANICI LİSTESİ + KULLANICI YÖNETİCİSİ
KURALLAR: grep/ls doğrulamalı; Türkçe rapor; VM testi YOK.

## §1 (final52) ÇİFT BOOT KUTUDAN
- packages.x86_64 += os-prober
- kurulu sisteme giden /etc/default/grub ŞABLONUNA:
  GRUB_DISABLE_OS_PROBER=false
- DOĞRULA: grep şablon + airootfs → VAR

## §2 SDDM: KULLANICILAR AÇILIR LİSTEDE
- Tema QML: kullanıcı TextField'ını KALDIR → ComboBox:
  model: userModel; textRole: "realName" (yoksa "name")
  avatar varsa küçük logo göster
- Giriş: sddm.login(comboBox currentText, parola, oturum)
- Tema AYNEN: krem zemin, yeşil/turuncu logo, Giriş + ⟳ + ⏻
- DOĞRULA: theme.qml grep ComboBox+userModel; py/qmllint temiz

## §3 "＋ YENİ KULLANICI" BUTONU (güvenli mimari)
a) Greeter'da ⟳/⏻ yanına "＋" butonu:
   tıklayınca QML bilgi penceresi:
   "Yeni kullanıcı, giriş sonrası: Yerinde Kullanıcı Yöneticisi
    veya Sistem Ayarları → Kullanıcılar"
   (greeter komut ÇALIŞTIRAMAZ + güvenlik; buton yönlendirir)
b) packages/yerinde-kullanici (YENİ, ~150 satır Tkinter):
   - pkexec ile çalışır (admin parolası ister)
   - kullanıcı ekle/sil, parola belirle, grup seç (ogrenci/ogretmen)
   - iki aşamalı onay; Türkçe; .desktop + menü + mağazada listelenir
   - DOĞRULA: py_compile + pkexec policy dosyası VAR

## §4 REGRESYON
oto-giriş (final34) ile ÇAKIŞMA kontrolü: Autologin açıksa
greeter atlanır → liste etkilenmez; drkonqi mask; ANKA teması;
quiet/audit; final51 font/serial; waydroid/ydotool zinciri AYNEN.

## §5 DERLEME + TEST
pkgrel bump + makepkg + repo-add; setsid build-iso + sha256
Testler:
1) greeter: açılır listede kullanıcılar görünür; ＋ bilgi verir
2) giriş sonrası: Yerinde Kullanıcı Yöneticisi pkexec ile açılır,
   deneme kullanıcısı ekler/siler
3) Windows'lu PC: menüde Windows Boot Manager
4) UEFI/MBR + kurulum regresyonu YOK