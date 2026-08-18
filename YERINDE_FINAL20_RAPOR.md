# YERINDE FINAL20 RAPOR — "Yerinde OS" → "Yerinde Ocağı"

Tarih: 2026.08.17
Amaç: Kullanıcıya görünen HER metinde "OS" kalkar, "Ocağı" gelir.
Paket/adlar ASCII kalır (yerinde-branding, yerinde-ai-assistant).

## 1) METİN DEĞİŞİMLERİ (case-aware, Türkçe ek uyumlu)

Türkçe ek uyumu için sıralı değiştirme uygulandı:
- "Yerinde OS’in" → "Yerinde Ocağı’nın" (genitive, U+2019 apostrof)
- "Yerinde OS'a"  → "Yerinde Ocağı'na"  (dative, U+0027 apostrof)
- "Yerinde OS’i"  → "Yerinde Ocağı’nı"  (accusative, U+2019 apostrof)
- "Yerinde OS"    → "Yerinde Ocağı"     (genel)

### Değişen dosyalar (kaynak, 47 dosya):

#### iso/yerinde/ (24 dosya)
| # | Dosya | Değişiklik |
|---|-------|------------|
| 1 | profiledef.sh | iso_name="yerinde-ocagi", iso_label="YERINDE_OCAGI", iso_application |
| 2 | build-iso.sh | Başlık "YERINDE OCAGI" + ISO dosya adı deseni yerinde-ocagi-*.iso |
| 3 | grub/grub.cfg | 2 menuentry metni |
| 4 | grub/loopback.cfg | 2 menuentry metni |
| 5 | syslinux/archiso_head.cfg | MENU TITLE + yorum |
| 6 | syslinux/archiso_sys-linux.cfg | MENU LABEL + TEXT HELP (4 satır) |
| 7 | syslinux/archiso_pxe-linux.cfg | MENU LABEL + TEXT HELP (9 satır) |
| 8 | syslinux/splash.png | YENİ ÜRETİLDİ 640x480 (krem + küçük lockup) |
| 9 | efiboot/loader/entries/01-archiso-linux.conf | title |
| 10 | efiboot/loader/entries/02-archiso-speech-linux.conf | title |
| 11 | airootfs/etc/os-release | PRETTY_NAME |
| 12 | airootfs/etc/motd | Welcome |
| 13 | airootfs/etc/default/grub | GRUB_DISTRIBUTOR |
| 14 | airootfs/etc/pacman.conf | Yorum |
| 15 | airootfs/etc/xdg/autostart/calamares.desktop | Name/Name[tr]/Comment/Comment[tr] |
| 16 | airootfs/etc/calamares/branding/yerinde/branding.desc | productName, versionedName, welcome, productWelcome |
| 17 | airootfs/etc/calamares/branding/yerinde/show.qml | source + text |
| 18 | airootfs/etc/calamares/branding/yerinde/yerinde-ocagi-lockup-720.png | YENİ |
| 19 | airootfs/usr/share/sddm/themes/yerinde/Main.qml | text (başlık) + source |
| 20 | airootfs/usr/share/sddm/themes/yerinde/yerinde-ocagi-lockup-720.png | YENİ |
| 21 | airootfs/usr/share/wallpapers/Yerinde/metadata.desktop | Comment |
| 22 | airootfs/usr/share/plymouth/themes/yerinde/yerinde.plymouth | Description |
| 23 | airootfs/usr/bin/yerinde-first-run | Yorum |
| 24 | airootfs/usr/local/bin/yerinde-finalize.sh | GRUB_DISTRIBUTOR, systemd-boot entry, syslinux cfg, GRUB alt menü sed |

#### packages/yerinde-branding/ (17 dosya)
| # | Dosya | Değişiklik |
|---|-------|------------|
| 25 | PKGBUILD | pkgrel 13→14, source/install dosya adları, grep doğrulama, Comment |
| 26 | grub-theme.txt | title-text + yorum |
| 27 | grub-background.png | YENİ ÜRETİLDİ 1024x768 (krem + küçük lockup) |
| 28 | grub-logo.png | YENİ ÜRETİLDİ 360x120 ("yerinde" yeşil + "OCAĞI" turuncu) |
| 29 | yerinde-ocagi-lockup-720.png | YENİ (eski yerinde-os-lockup-720.png SİLİNDİ) |
| 30 | src/yerinde-ocagi-lockup-720.png | YENİ |
| 31 | files/yerinde-ocagi-lockup-720.png | YENİ |
| 32 | yerinde-icon-cream.svg | YENİ AD (eski yerinde-os-icon-cream.svg) |
| 33 | src/yerinde-icon-cream.svg | YENİ AD |
| 34 | files/yerinde-icon-cream.svg | YENİ AD |
| 35 | yerinde-ocagi-lockup-cream.svg | YENİ AD (eski yerinde-os-lockup-cream.svg) |
| 36 | src/yerinde-ocagi-lockup-cream.svg | YENİ AD |
| 37 | files/yerinde-ocagi-lockup-cream.svg | YENİ AD |
| 38 | files/yerinde-first-run.sh | Yorum |
| 39 | files/os-release | PRETTY_NAME |
| 40 | os-release | PRETTY_NAME |
| 41 | yerinde-first-run.sh | Yorum |

#### packages/calamares/ (3 dosya)
| # | Dosya | Değişiklik |
|---|-------|------------|
| 42 | calamares_tr_TR.ts | 13 çeviri: "Yerinde OS" → "Yerinde Ocağı" (ek uyumlu: Ocağı'nı, Ocağı'nın) |
| 43 | PKGBUILD | prepare() yorumu |
| 44 | src/calamares-3.4.2/lang/calamares_tr_TR.ts | 13 çeviri (mirror) |

#### branding/ (3 dosya)
| # | Dosya | Değişiklik |
|---|-------|------------|
| 45 | yerinde-ocagi-lockup-720.png | YENİ (eski yerinde-os-lockup-720.png SİLİNDİ) |
| 46 | yerinde-icon-cream.svg | YENİ AD |
| 47 | yerinde-ocagi-lockup-cream.svg | YENİ AD |

#### iso/yerinde/work/x86_64/ (root-owned mirror — yeniden inşa ile üstüne yazılır)
work/x86_64/airootfs/ altındaki aynı dosyaların hepsi güncellendi.

## 2) GÖRSELLERİ YENİDEN ÜRETİLDİ

Yeni lockup tasarımı:
- "yerinde" #0B3D2E (koyu yeşil) + "OCAĞI" #C74A1F (turuncu)
- Alt satır: "AÇIK KAYNAK İŞLETİM SİSTEMİ" (krem #F7F2E2)
- Font: DejaVu Sans Bold

Üretilenler:
- **yerinde-ocagi-lockup-720.png** (720x240 RGBA, şeffaf zemin) — SDDM + Calamares sidebar/show.qml
- **splash.png** (640x480 RGB, krem #F4EFE4 zemin + küçük lockup üst-orta) — MBR syslinux menü
- **grub-background.png** (1024x768 RGB, krem zemin + küçük lockup) — GRUB tema zemini
- **grub-logo.png** (360x120 RGBA, şeffaf, yalnızca wordmark) — GRUB tema logosu

Eski yerinde-os-lockup-*.png dosyaları + referansları SİLİNDİ.

## 3) DOĞRULAMA (FAIL-kontrollü)

### grep kanıtı: "yerinde os" SIFIR sonuç (kaynak dosyalarda)
```
grep -rin "yerinde.os\b" (tüm metin kaynaklar) → (boş)
```
Geriye kalan: yalnızca binary build çıktıları (airootfs.sfs, efiboot.img, eski ISO) —
bunlar yeniden inşa ile yeniden üretilecek.

### ls kanıtı: eski lockup YOK, yeni png'ler VAR
```
find -name "yerinde-os-lockup-*.png" → (boş) ✓
find -name "yerinde-ocagi-lockup-720.png" → 9 konumda mevcut ✓
```

### sddm --test-mode
SDDM test-mode GUI süreç olarak çalışır (ekran gerektirir). VM ortamında test edilir.
Main.qml kaynak kodu doğrulandı: text: "Yerinde Ocağı", source: "yerinde-ocagi-lockup-720.png"

## 4) REGRESYON KORUMASI (DOKUNULMADI)
- Wayland tek oturum (SDDM [X11] Enable=false) ✓
- SDDM krem + Enter + ⟳⏻ düğmeleri ✓
- MBR krem menü + NOESCAPE + Türkçe HELP ✓
- GRUB teması + fallback ✓
- 5 duvar kağıdı ✓
- sudoers wheel ✓
- "Calamares" temizliği (çeviriler) ✓
- Asistan ISO'da YOK ✓
- İlk-oturum betiği ✓

## 5) PAKET + BUILD + RAPOR

- branding pkgrel: 13 → 14 (bump)
- makepkg / repo-add: Kullanıcı tarafından yapılacak (push YOK)
- ISO rebuild: build-iso.sh setsid+log; sha256; dosya adı yerinde-ocagi-*.iso
- profiledef.sh: iso_name="yerinde-ocagi" → mkarchiso çıktısı yerinde-ocagi-YYYY.MM.DD-x86_64.iso

## 6) TEST LİSTESİ (VM'de manuel doğrulama)

1) MBR/UEFI menülerde "Yerinde Ocağı"
   - syslinux: MENU TITLE Yerinde Ocağı ✓
   - systemd-boot: title Yerinde Ocağı kurulum ortamı ✓
   - GRUB: menuentry "Yerinde Ocağı install medium" ✓

2) SDDM + Calamares başlıklarında "Yerinde Ocağı"
   - SDDM Main.qml: text: "Yerinde Ocağı" ✓
   - Calamares branding.desc: productName "Yerinde Ocağı", welcome "Yerinde Ocağı'na hoş geldiniz" ✓
   - Calamares show.qml: "Yerinde Ocağı kuruluyor..." ✓
   - Calamares .ts: "Yerinde Ocağı Kurulum Sihirbazına hoş geldiniz" ✓

3) Kurulu GRUB giriş adı "Yerinde Ocağı"
   - GRUB_DISTRIBUTOR="Yerinde Ocağı" ✓
   - grub-theme.txt title-text: "Yerinde Ocağı" ✓
   - finalize.sh: GRUB alt menü "Yerinde Ocağı gelişmiş seçenekler" ✓
   - finalize.sh: systemd-boot "title Yerinde Ocağı" ✓
   - finalize.sh: syslinux "MENU TITLE Yerinde Ocağı" ✓

4) Hiçbir ekranda "OS" kelimesi YOK
   - grep "yerinde os" → SIFIR (kaynak dosyalar) ✓
