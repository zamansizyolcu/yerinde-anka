# YERINDE FINAL24 RAPOR — TEK LOGO + CALAMARES ANKA + NUMPY + TIKLA-ÇALIŞTIR

Tarih: 2026.08.17
KURALLAR: VM testi YOK; push YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## 1) GRUB TEMASI: ÜSTTE 3 YAZI → TEK LOGO

Sorunun kökü: title-text (1) + background.png içi lockup (2) + "+ image
logo.png" resmi (3) = 3 satır. Çözüm:
- grub-theme.txt: `title-text`/`title-font`/`title-color` satırları SİLİNDİ;
  `+ image { file = "logo.png" }` bloğu SİLİNDİ
- Kalan TEK görsel: `desktop-image: "background.png"` (içinde tek ANKA
  lockup, üst-orta küçük — final21 üretimi aynen geçerli)

DOĞRULA (kurulu work airootfs, grep kanıtı):
```
theme.txt → yalnız satır 9: desktop-image: "background.png"
^title-text YOK; ^+ image YOK  ✓
```
PKGBUILD + build-iso.sh kontrolleri tersine çevrildi (title-text VARSA FAIL,
desktop-image tam 1 DEĞİLSE FAIL, + image VARSA FAIL). Not: yorum
satırındaki "title-text" kelimesi ilk turda yanlış pozitif verdi → desen
yönerge-çapalı (`^\s*title-text\s*:`) yapıldı.

## 2) CALAMARES BAŞLIK: "OS" → ANKA (KÖK NEDEN BULUNDU)

KÖK NEDEN: ISO'daki calamares-3.4.2-**3** paketi 16 Ağu (saat 18:28)
derlemesiydi — yeniden adlandırmalardan ÖNCE. Çeviriler Qt QRC ile ikiliye
**zlib sıkıştırılmış** gömülür (düz `strings` araması bu yüzden her iki
ikilide de boş görünür). -3 içindeki gömülü çeviri "Yerinde OS..." idi.

ÇÖZÜM: pkgrel 3→**4**, kaynak .ts (final21'den ANKA'lı) ile yeniden derleme.
Kanıt zinciri:
1. Kaynak .ts: `rg "Yerinde OS"` → **SIFIR**; "Yerinde ANKA Kurulum
   Sihirbazına hoş geldiniz" ×2 (welcome + welcomeq) ✓
2. lrelease çıktısı qm ÜRETİLDİ: `build/lang/calamares_tr_TR.qm` (166302 B)
   içinde ANKA karşılama **UTF-16-BE** olarak kanıtlı ✓
   (qm UTF-16-BE saklar — ilk kontrol desenim utf-16-le'di, düzeltildi)
3. qrc 75 qm listeliyor (tr_TR dahil) + link satırında
   `qrc_calamares-i18n.cxx.o` + ikilide `qInitResources_calamares_i18n` ✓
4. PKGBUILD package()'e kalıcı doğrulama eklendi: qm yoksa/ANKA metin
   yoksa **build FAIL**. build-iso.sh post: pacman DB'de
   `calamares-3.4.2-4` arar (-3 geçersiz).

## 3) ISO'YA PYTHON KÜTÜPHANELERİ

packages.x86_64 += **python-numpy python-pillow** (yorumlu).

- opencv: Arch "opencv" 5.0.0 paketi **cv2 python bağlaması içermiyor**
  (resmî files listesinde site-packages yok; python-opencv depolarda yok)
  → **EKLENMEDİ** (best-effort; build düşürülmedi) + build-iso.sh bilgi
  satırı: cv2 site-packages'te YOKsa BİLGİ verir, FAIL etmez.

DOĞRULA (work airootfs ls kanıtı):
```
.../python3.14/site-packages/numpy  (1054 öğe)
.../python3.14/site-packages/PIL    (3826 öğe)
cv2 → YOK (POST BİLGİ olarak raporlandı)
```

## 4) ASİSTAN REPOSU: NUMPY KALICI DÜZELTME

(/home/yerinde/yerinde-ai-assistant — paket adı aynı kalır)
- requirements.txt: `numpy<2` → **`numpy>=2`** (eski pin yeni Python'da
  wheel bulamıyor → kaynak derleme → gcc yok hatası)
- kurulum.sh BAŞINA (banner sonrası, [1/4] öncesi):
  `sudo pacman -S --needed python-numpy python-pillow || true`
- pip adımı sarıldı: `if ! pip install -r requirements.txt; then
  "Derleme hatası: numpy sistemden kurulmalı → sudo pacman -S python-numpy";
  exit 1; fi`
- README.md OLUŞTURULDU (önceden yoktu): "Kurulum (Yerinde ANKA)" bölümü —
  tıkla-çalıştır kısayolu + elle kurulum + numpy notu
- **commit YAPILAMADI: dizin git deposu DEĞİL** (`git rev-parse` → "not a
  git repository"). Push da YOK (kural).

## 5) TIKLA-ÇALIŞTIR KURUCU (klasör adına bağımlı DEĞİL)

- `airootfs/usr/local/bin/yerinde-asistan-kur` (755, bash, set -e YOK,
  ~2.9 KB):
  1) pacman -Qi yerinde-ai-assistant → kuruluysa "Zaten kurulu" + başlat
  2) İnternet VARSA: [yerinde] yoksa pacman.conf'a ekle
     (SigLevel=Never, zamansizyolcu.github.io/yerinde-repo) → pacman -Sy +
     -S --needed yerinde-ai-assistant
  3) YOKSA yerel arama (imza bazlı): ~/İndirilenler/*/ ~/Downloads/*/ ~/*/
     içinde kurulum.sh VEYA main.py+ui.py + "yerinde" grep → ./kurulum.sh
  4) Hiçbiri yoksa: "İnternet yok + yerel klasör bulunamadı. Asistan
     klasörünü İndirilenler'e koy."
  5) "Çevrimdışı modeller kurulsun mu? (e/h)" → ollama enable --now +
     pull llama3.1 + qwen2.5-coder:1.5b
  6) "Başlatmak için Enter" → yerinde
- .desktop ×2 (aynı içerik):
  - airootfs/usr/share/applications/yerinde-asistan-kur.desktop (menü)
  - airootfs/etc/skel/Desktop/yerinde-asistan-kur.desktop (masaüstü)
  - Name=YERINDE Asistanı Kur (Tıkla-Çalıştır); Exec=/usr/local/bin/
    yerinde-asistan-kur; Terminal=true; Icon=yerinde; Type=Application;
    Categories=Utility;
- profiledef.sh file_permissions'a 755 girişi eklendi
- DOĞRULA: `bash -n` OK; script 755 + 2 .desktop ls ✓; script içinde
  "kurulum.sh" + "yerinde-ai-assistant" grep ✓; POST: üçü de ISO'da ✓;
  asistanın KENDİSİ ISO'da YOK (usr/bin/yerinde yok — yalnız kurucu script)

## 6) REGRESYON KORUMASI (DOKUNULMADI — POST OK)

keyring doğumda hazır ✓; zip araçları (ark/zip/unzip/7zip/unrar) ✓;
NOESCAPE + MENU TABMSG gizli ✓; Wayland-tek oturum (xsessions boş) ✓;
SDDM krem + Enter + ⟳⏻ + sddm-test.log temiz ✓; 5 duvar kağıdı ✓;
sudoers wheel ✓; ilk-oturum betiği ✓; ANKA adları (kaynaklarda eski ad
SIFIR) ✓; GRUB fallback (finalize.sh) ✓; requiredStorage 40 ✓;
asistan/ollama/ydotool ISO'da YOK ✓.

## 7) PAKET + BUILD + RAPOR

- yerinde-branding: pkgrel 15→**16**; makepkg OK; repo-add OK
- calamares: pkgrel 3→**4**; makepkg OK (I18N doğrulaması geçti); repo-add OK
- **commit: YAPILAMADI — hiçbir dizin git deposu değil** (yerinde-project,
  yerinde-ai-assistant). Push YOK (kural).
- ISO rebuild: setsid+log; **out/yerinde-anka-2026.08.17-x86_64.iso (2.8G)**
- SHA256: `08ca057cac022501de36abc716cad24ad93e901dce741603fc53565564000971`
  (out/SHA256SUMS)
- TÜM POST DOĞRULAMALAR BAŞARILI (build-iso.sh çıktısı)

## KULLANICI TEST LİSTESİ (VM'de manuel)

1. GRUB: üstte TEK "yerinde ANKA" lockup (3'lü yazı YOK)
2. Calamares başlığı (UEFI+MBR aynı ikili): "Yerinde ANKA Kurulum
   Sihirbazına hoş geldiniz"
3. Masaüstü "YERINDE Asistanı Kur" → İndirilenler'deki klasörü ADI HER NE
   OLURSA OLSUN bulur; kurulum.sh → numpy derleme hatası YOK
4. Kurulu VM: `python3 -c "import numpy, PIL"` çalışır
5. Hiçbir ekranda "OS" kalıntısı YOK; UEFI+MBR kurulum regresyonu YOK
