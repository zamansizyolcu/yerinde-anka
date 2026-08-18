# YERINDE FINAL21 RAPOR — "Yerinde ANKA" + KEYRING + ZIP ARAÇLARI

Tarih: 2026.08.17
Amaç: "Yerinde OS"/"Yerinde Ocağı" → **"Yerinde ANKA"**, keyring doğumda
hazır, ZIP/arsiv araçları ISO'da, MBR "Press [Tab]" ipucu gizli.
KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls/grep DOĞRULAMALI.

## 1) YENİDEN ADLANDIRMA: "Yerinde OS"/"Yerinde Ocağı" → "Yerinde ANKA"

Case-aware + Türkçe ek uyumlu sıralı değiştirme (38 kaynak dosya):
- "Yerinde Ocağı'na" → "Yerinde ANKA'ya" (datif)
- "Yerinde Ocağı'nı" → "Yerinde ANKA'yı" (akuzatif)
- "Yerinde Ocağı'nın" → "Yerinde ANKA'nın" (genitif)
- "Yerinde Ocağı" → "Yerinde ANKA" (genel)
- "YERINDE_OCAGI"→"YERINDE_ANKA", "yerinde-ocagi"→"yerinde-anka",
  "YerindeOS"→"YerindeANKA" (finalize.sh EFI bootloader-id)

### Dokunulan yerler (özet)
| Yer | Değişiklik |
|-----|------------|
| profiledef.sh | iso_name="yerinde-anka", iso_label="YERINDE_ANKA", iso_application |
| build-iso.sh | Başlık "YERINDE ANKA" + ISO deseni yerinde-anka-*.iso + yeni doğrulamalar |
| grub/grub.cfg + loopback.cfg | menuentry "Yerinde ANKA install medium (...)" |
| efiboot/loader/entries/*.conf | "Yerinde ANKA kurulum ortamı (x86_64, UEFI)" (+sesli) |
| syslinux/*.cfg | MENU TITLE + "Yerinde ANKA kurulum ortami (x86_64, BIOS)" + HELP metinleri |
| calamares branding.desc | productName/versionedName/welcome + **bootloaderEntryName: "Yerinde ANKA"** |
| calamares show.qml | "Yerinde ANKA kuruluyor..." + anka png |
| calamares_tr_TR.ts (×2) | 14 çeviri: "Yerinde ANKA Kurulum Sihirbazına hoş geldiniz" dahil; hedef metinde "Calamares" YOK (korundu) |
| SDDM Main.qml | başlık "Yerinde ANKA" + anka png |
| finalize.sh | EFI bootloader-id=YerindeANKA; GRUB_DISTRIBUTOR="Yerinde ANKA"; sed "Advanced options for Yerinde ANKA"→"Yerinde ANKA gelişmiş seçenekler"; systemd-boot title'ları; kurulu syslinux MENU TITLE/LABEL/HELP |
| .desktop'lar | calamares.desktop Name/Name[tr]/Comment; duvar kağıdı metadata'ları; plymouth; os-release; motd; pacman.conf yorumu |

## 2) GÖRSELLER YENİDEN ÜRETİLDİ (eski wordmark'lar SİLİNDİ)

Yeni lockup: **"yerinde" (#0B3D2E) + "ANKA" (#C74A1F)** + alt satır
"AÇIK KAYNAK İŞLETİM SİSTEMİ" (krem #F7F2E2). Font: DejaVu Sans Bold.

| Dosya | Boyut | Kullanım |
|-------|-------|----------|
| yerinde-anka-lockup-720.png | 720x240 RGBA şeffaf | SDDM + Calamares (branding dir, pkg src/files, airootfs ×2) |
| splash.png | 640x480 krem zemin + küçük lockup üst-orta | MBR syslinux menü |
| grub-background.png | 1024x768 krem zemin + küçük lockup | GRUB tema zemini |
| grub-logo.png | 360x120 şeffaf wordmark | GRUB teması logosu |
| yerinde-anka-lockup-cream.svg | SVG (tspan OS→ANKA, renkler spec'e) | kaynak varlık |

DOĞRULAMA: `find -name "*ocagi*"` → kaynaklarda SIFIR; yeni png'ler 6+ konumda;
piksel kanıtı: yeşil (11,61,46) + turuncu (199,74,31) wordmark, bbox'lar
kenar taşması YOK (lockup 550px genişlik ortalı).

## 3) KEYRING DOĞUMDA HAZIR

- **finalize.sh** (kurulu sistem) chroot bölümüne eklendi:
  ```
  chroot "$R" pacman-key --init
  chroot "$R" pacman-key --populate archlinux
  ```
- **CANLI**: airootfs/usr/local/bin/yerinde-keyring-init (755, bayrak:
  /var/lib/yerinde-keyring-done) + yerinde-keyring.service (oneshot,
  ConditionPathExists=!bayrak) + multi-user.target.wants linki +
  profiledef.sh file_permissions'a 755 girişi.
- DOĞRULAMA: work airootfs'te ls kanıtı (script 546B 755 + service 306B +
  wants symlink → ../yerinde-keyring.service). finalize.log'a pacman-key
  satırları kurulum anında yazılır (kaynak satırlar 74-75).

## 4) ZIP ARAÇLARI ISO'DA

packages.x86_64 += **ark zip unzip 7zip unrar**
(Not: p7zip/p7zip-rar resmi depolardan kaldırıldı → "target not found"
build hatası verdi; resmi **7zip** paketi /usr/bin/7z sağlar, RAR için
unrar mevcut. Bu sapma bilinçli.)

DOĞRULAMA (work airootfs, ls kanıtı):
```
-rwxr-xr-x /usr/bin/7z      (7zip)
-rwxr-xr-x /usr/bin/ark     (KDE arşiv aracı → sağ tık Ayıkla/Arşivle)
-rwxr-xr-x /usr/bin/unzip
-rwxr-xr-x /usr/bin/zip
```

## 5) MBR NOESCAPE KONTROL

- `NOESCAPE 1` VARDI (archiso_head.cfg:18 + finalize.sh kurulu cfg) ✓
- Kullanıcı ekranda hâlâ "Press [Tab]" gördüğü için ek olarak
  **`MENU TABMSG`** (boş) eklendi → İngilizce ipucu satırı tamamen gizli
  (hem ISO menüsü hem kurulu sistem syslinux.cfg'si).

## 6) REGRESYON KORUMASI (DOKUNULMADI — build sonrası POST OK)

- Wayland TEK oturum (xsessions boş, SDDM [X11] Enable=false) ✓ POST OK
- SDDM krem tema + Enter + ⟳⏻ + oturum seçici + parola focus ✓ (sddm-greeter
  --test-mode log TEMİZ)
- GRUB teması + fallback ✓ (title-text "Yerinde ANKA")
- 5 duvar kağıdı ✓ | sudoers wheel ✓ | asistan ISO'da YOK ✓ |
  ilk-oturum betiği ✓ | requiredStorage 40 (partition.conf) ✓
- xdotool/xorg-xwayland zinciri aynen korundu ✓

## 7) PAKET + BUILD + RAPOR

- branding pkgrel 14 → **15**; makepkg OK; repo-add OK:
  `repo/x86_64/yerinde-branding-1.2.0-15-any.pkg.tar.zst` (yerinde.db güncellendi)
- **commit: YAPILAMADI — proje dizini git deposu DEĞİL** (`git status` →
  "not a git repository"). Push da YOK (kural).
- ISO rebuild: setsid+log (/tmp/opencode/yerinde-iso-build.log) BAŞARILI
- **out/yerinde-anka-2026.08.17-x86_64.iso (2.8G)**
- SHA256: `1899fd2cc7322464233fc39ba115a31ff640e508b3f6472cfed5157aaf61ac`
  (out/SHA256SUMS'a yazıldı)

### Rapor kanıtları
1) `rg -ri 'yerinde[ ]os|yerinde[ ]ocağı|yerinde-ocagi|YERINDE[_ ]OCAGI'`
   → kullanıcıya görünür kaynak metinde SIFIR (yalnız build-iso.sh'in kendi
   kontrol deseni kendini eşliyor; betik kendi kontrolünde build-iso.sh'i hariç tutar)
2) Yeni lockup png'ler ls ✓; eski yerinde-os-*/yerinde-ocagi-* png YOK ✓
3) finalize.sh pacman-key satırları (74-75) + keyring service/script ls ✓;
   zip araçları ls ✓
4) NOESCAPE + MENU TABMSG grep kanıtı (ISO İÇİNDEN çıkarıldı):
   ```
   boot/syslinux/archiso_head.cfg: MENU TITLE Yerinde ANKA / NOESCAPE 1 / MENU TABMSG
   boot/syslinux/archiso_sys-linux.cfg: MENU LABEL Yerinde ANKA kurulum ortami (x86_64, BIOS)
   boot/grub/loopback.cfg: menuentry "Yerinde ANKA install medium (x86_64, ...)"
   loader/entries/01-archiso-linux.conf: title Yerinde ANKA kurulum ortamı (x86_64, UEFI)
   ```
   sddm-test.log temiz ✓

## KULLANICI TEST LİSTESİ (VM'de manuel)

1. MBR/UEFI menüler + Calamares + SDDM başlığı: **"Yerinde ANKA"**
2. "Press [Tab]" satırı YOK (MBR menüde)
3. Kurulu sistemde `sudo pacman -S vlc` → imza hatasız (keyring doğumda hazır)
4. Sağ tık → Ayıkla/Arşivle çalışır (ark); unzip/zip/7z komutları hazır
5. UEFI+MBR kurulum regresyonu YOK
