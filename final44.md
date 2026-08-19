# final44 EK — ISO DERLEME (final43'te EKSİK adım)
SORUN: paketler/repo/doğrulama tamam ama ISO build YOK → kullanıcı
ESKİ ISO açtı (Keşfet var, mağaza/waydroid yok).
1) cd iso/yerinde && setsid bash -c './build-iso.sh >
   /tmp/opencode/final44-iso.log 2>&1' &
2) poll: "INFO: Done!" + out/yerinde-anka-*.iso (tarih = BUGÜN)
   + sha256 → rapora
3) İÇERİK KANITI (VM'siz):
   pacman -r work/x86_64/airootfs -Q | grep -E "magaza|waydroid|gorev"
   → 3 paket de LİSTEDE (yoksa FAIL: packages.x86_64 + repo db kontrol)
   + pacman -r ... -Q | grep -iE "discover|apper" → BOŞ (Keşfet YOK)
4) VM test maddesi: menüde Yerinde Mağaza + Görev Yöneticisi +
   Waydroid VAR; Keşfet YOK; NVIDIA host'ta finalize modset kanıtı
5) REGRESYON: önceki tüm maddeler (ANKA temalar, ydotool zinciri,
   ses, tıkla-kur, keyring) AYNEN