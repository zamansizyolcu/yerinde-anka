# YERINDE ANKA final25 — TEK MASTER PROMPT
BAĞLAM: final21 başarılı (ANKA, keyring, zip, NOESCAPE, 2.8G ISO).
Kalan: GRUB 3'lü logo, Calamares "OS" başlığı, numpy pin hatası,
tıkla-çalıştır kurucu isteği.
KURALLAR: VM testi YOK; push YOK; setsid+log; grep/ls doğrulamalı;
Türkçe rapor; eksikse FAIL.

## 1) GRUB TEMASI: ÜSTTE 3 YAZI → TEK LOGO
- theme.txt: title_text satırını SİL
- zemin/theme görselleri: YALNIZCA 1 "yerinde ANKA" lockup
  (üst-orta, küçük) kalacak şekilde YENİDEN üret
- DOĞRULA: theme.txt tek image referansı; grep title_text YOK

## 2) CALAMARES BAŞLIK: "OS" → ANKA
- lconvert override YENİDEN üret; hedef:
  "Yerinde ANKA Kurulum Sihirbazına hoş geldiniz"
- DOĞRULA: kontrol .ts içinde görünür "Yerinde OS" SIFIR
  (UEFI+MBR aynı dosya → ikisi birden düzelir)

## 3) ISO'YA PYTHON KÜTÜPHANELERİ (çevrimdışı asistan kurulumu)
packages.x86_64 += python-numpy python-pillow
- DOĞRULA (ls, eksikse FAIL): site-packages altında numpy/ VE PIL/
- opencv: "opencv" ekle; cv2 VARSA kalır, YOKSA koyma + raporda
  belirt (best-effort, build'i DÜŞÜRMEZ)

## 4) ASİSTAN REPOSU: NUMPY KALICI DÜZELTME
- requirements.txt: "numpy==1.26.4" pinini SİL veya "numpy>=2"
- kurulum.sh BAŞINA: sudo pacman -S --needed python-numpy
  python-pillow || true
- pip hatasında Türkçe fallback: "Derleme hatası: numpy sistemden
  kurulmalı → sudo pacman -S python-numpy"
- README "Kurulum" notu; commit (push YOK)

## 5) TIKLA-ÇALIŞTIR KURUCU (klasör ADINA bağımlı DEĞİL)
a) airootfs/usr/local/bin/yerinde-asistan-kur (755, bash, set -e YOK):
   1) pacman -Qi yerinde-ai-assistant → kuruluysa "Zaten kurulu"
      → yerinde başlat, çık
   2) internet VARSA: pacman.conf [yerinde] yoksa ekle
      (SigLevel=Never, Server=https://<USER>.github.io/yerinde-repo)
      → sudo pacman -Sy + -S --needed yerinde-ai-assistant
   3) YOKSA/başarısızsa YEREL ARAMA (imza bazlı, ada bakma):
      for d in ~/İndirilenler/*/ ~/Downloads/*/ ~/*/; do
        { [ -f "$d/kurulum.sh" ] || { [ -f "$d/main.py" ] &&
          [ -f "$d/ui.py" ]; }; } && grep -qi "yerinde" \
          "$d/kurulum.sh" "$d/main.py" 2>/dev/null && BUL="$d" && break
      done
      → bulursa: cd "$BUL"; chmod +x kurulum.sh 2>/dev/null;
        ./kurulum.sh
   4) hiçbiri yoksa Türkçe hata: "İnternet yok + yerel klasör
      bulunamadı. Asistan klasörünü İndirilenler'e koy."
   5) soru: "Çevrimdışı modeller kurulsun mu? (e/h)" → e:
      systemctl enable --now ollama + ollama pull llama3.1 +
      qwen2.5-coder:1.5b
   6) "Başlatmak için Enter" → yerinde
b) .desktop (skel/Desktop + usr/share/applications):
   Name=YERINDE Asistanı Kur (Tıkla-Çalıştır)
   Exec=/usr/local/bin/yerinde-asistan-kur
   Terminal=true; Icon=yerinde; Type=Application; Categories=Utility;
c) DOĞRULA: bash -n OK; script(755) + 2 .desktop ls; grep içinde
   "kurulum.sh" + "yerinde-ai-assistant" geçiyor

## 6) REGRESYON KORUMASI (DOKUNMA)
keyring doğumda hazır; zip araçları; NOESCAPE+TABMSG gizli;
Wayland-tek; SDDM krem+Enter+⟳⏻; 5 duvar kağıdı; sudoers wheel;
asistanın KENDİSİ ISO'da YOK (script ~2KB); ANKA adları;
GRUB fallback; requiredStorage 40.

## 7) PAKET + BUILD + RAPOR
- branding pkgrel bump; makepkg; repo-add; commit (push YOK)
- ISO rebuild setsid+log; sha256; yerinde-anka-*.iso
- Rapor kanıtları: theme.txt tek image; kontrol.ts "OS" SIFIR;
  numpy/+PIL/ ls; asistan repo diff; bash -n + .desktop ls
- Kullanıcı test listesi:
  • GRUB: TEK lockup; Calamares: "Yerinde ANKA ... hoş geldiniz"
  • Masaüstü "YERINDE Asistanı Kur" → ADI HER NE OLURSA OLSUN
    İndirilenler'deki klasörü bulur, numpy hatasız kurar
  • Hiçbir ekranda "OS" kalıntısı YOK; UEFI+MBR regresyonu YOK