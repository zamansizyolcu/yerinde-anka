# final63 — BLUETOOTH TR ÇEVİRİ + DVRIP VENV + DERLEME + PUSH
KURALLAR: grep/ls doğrulamalı; Türkçe rapor; test temizlenmeden
paket/ISO/push YOK.

## §1 BLUETOOTH "FORGET DEVICE" → TÜRKÇE (çeviri yaması)
1) Kataloğu bul: msgunfmt /usr/share/locale/tr/LC_MESSAGES/
   bluedevil5.mo (yoksa kcm_bluetooth*.mo dene) → tr.po
2) Eksik msgstr'leri DOLDUR:
   "Forget this Device?"            → "Bu Aygıt Unutulsun mu?"
   "Are you sure you want to forget
    \"%1\"?" (veya ilgili msgid)     → "\"%1\" aygıtını unutmak
                                      istediğine emin misin?"
   "Forget Device"                  → "Aygıtı Unut"
   "Cancel"                         → "Vazgeç"
   (mevcut çeviriler SİLİNMEZ — msgcat/birleştirme, üzerine yazma)
3) msgfmt tr.po -o bluedevil5.mo → BİRLEŞTİRİLMİŞ katalog
4) SEVK: yerinde-branding paketine koy:
   usr/share/locale/tr/LC_MESSAGES/bluedevil5.mo
   → hem canlı hem kurulu sistemde geçerli
5) DOĞRULA: msgunfmt yeni .mo | grep "Aygıtı Unut" → VAR

## §2 DVRIP / BAHÇE KAMERASI (venv önceliği)
1) baslat.sh: PYTHON="$DIR/venv/bin/python"
   [ -x "$PYTHON" ] || PYTHON=python3   (venv ÖNCE)
2) kamera kodu: try: import dvrip except → Türkçe ipucu:
   "dvrip eksik: ./venv/bin/python -m pip install dvrip"
3) DOĞRULA: ./venv/bin/python -c "import dvrip" → OK raporda
   + grep baslat.sh "venv/bin/python" → VAR
4) commit + push ASİSTAN repo (baslat.sh değişti) — İZİN VAR

## §3 REGRESYON
SDDM tema + kullanıcı listesi, oto-giriş check, os-prober,
ESP fallback, ydotool, piper/voices, copytoram köprüsü,
unpackfs ön-kontrol, ANKA markası AYNEN

## §4 ISO DERLEME (ATLANMAZ)
- branding pkgrel bump + makepkg + repo-add
- setsid build-iso.sh > /tmp/opencode/final63-iso.log 2>&1 &
  poll "INFO: Done!" + out/*.iso + sha256
- KANIT: unsquashfs -l airootfs.sfs | grep bluedevil5.mo → VAR

## §5 PUSH (ATLANMAZ)
- git add -A && commit "final63: TR bluetooth + dvrip venv"
  && git push -u origin main (yerinde-anka)
- asistan repo push (§2) — ikisi de ls-remote ile DOĞRULA

## §6 KULLANICI TEST LİSTESİ
1) Bluetooth → aygıt unut penceresi TAM TÜRKÇE
2) Asistan → bahçe kamerası açılır (dvrip venv'den gelir)
3) VM + gerçek makine regresyonu YOK