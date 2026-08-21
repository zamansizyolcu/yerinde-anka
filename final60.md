# final60 — ŞİFRELİ GİRİŞ SİYAH EKRAN + ELLE BÖLÜMLEME TEYİT
KURALLAR: önce LOG, sonra düzeltme; grep/ls kanıt; Türkçe rapor.

## §1 SİYAH EKRAN (şifre girince oturum açılmıyor)
TEŞHİS (çıktılar rapora):
1) /var/log/sddm.log tail -40 + journalctl -b -0 -u display-manager
   + coredumpctl list | tail -5 (kwin_wayland çöküyor mu?)
2) /var/lib/sddm/state.conf → kayıtlı Session değeri;
   wayland-sessions/*.desktop ile EŞLEŞMİYORSA düzelt
3) final57 Main.qml doLogin: sessionModel.lastIndex geçersizse
   oturum siyah düşer. VERBATIM dosyaya TEK cerrahi:
   function doLogin() {
     var u = (userListView.currentItem !== null)
             ? userListView.currentItem.userName : ""
     var s = 0
     if (typeof sessionModel !== "undefined" && sessionModel.count > 0)
         s = sessionModel.lastIndex
     if (s < 0 || s >= sessionModel.count) s = 0
     sddm.login(u, passwordField.text, s)
   }
4) Tema'ya hata görünürlüğü: errorMessage context property'sini
   guard'lı Text ile altta göster (siyah ekran yerine mesaj)
5) TEST: sddm-greeter --test-mode stderr temiz (final57 döngüsü) +
   VM maddesi: şifreli giriş → masaüstüne düşer, siyah YOK

## §2 ELLE BÖLÜMLEME (final59 UYGULANMAMIŞSA UYGULA)
1) grep installEFIFallback bootloader config → true DEĞİLSE uygula
2) yerinde-grub-varsayilan oneshot + enable linki airootfs'te
   YOKSA ekle (final59 §2 birebir)
3) VM TEST: 35GB Windows + boş alana elle
   (512M ESP FAT32 + ext4 / + 2G swap) → reboot →
   GRUB ÖNDE + "Windows Boot Manager" listede

## §3 REGRESYON (çalışanlara DOKUNMA)
- parola → oto-giriş kapanır (final58) ✅ çalışıyor, AYNEN
- autologin-keep marker yolu AYNEN
- SDDM kullanıcı listesi + krem tema AYNEN
- waydroid/ydotool/ses 24kHz/piper/ANKA markası AYNEN

## §4 BUILD + PUSH
pkgrel bump + makepkg + repo-add; setsid build-iso + sha256;
git push yerinde-anka (KULLANICI İZNİ VAR)

## §5 RAPOR + TEST LİSTESİ
- Kanıtlar: sddm.log ilgili satır, state.conf, doLogin SON hali,
  installEFIFallback grep, oneshot ls
- Testler:
  1) şifreli giriş → masaüstü (siyah ekran YOK)
  2) şifresiz deneme → greeter (oto-giriş kapalı, DOĞRU)
  3) elle bölümleme VM senaryosu → GRUB önde + Windows listede
  4) UEFI/MBR + kurulum regresyonu YOK