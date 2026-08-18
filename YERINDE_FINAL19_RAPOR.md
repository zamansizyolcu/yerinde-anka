# YERINDE OS v1.9 — final19 RAPOR
## X11 KALDIRILDI, WAYLAND-TEK OTURUM

Tarih: 17 Ağu 2026
Önceki: final18 (ISO 2.62GB, sha256 957b8db8...)

---

## YAPILANLAR

### 1) packages.x86_64 — X11 paketleri SİLİNDİ
- SİLİNEN: `xorg-server`, `xorg-xinit`, `xorg-xrandr`, `xorg-xrdb`,
  `xorg-xsetroot`, `xorg-xmessage`, `xorg-sessreg`
- KALAN: `xorg-xwayland` (Tkinter asistan + X11 apps), `xorg-xhost`,
  `xorg-xprop`, `xorg-xwininfo`, `xdotool`, `wmctrl`, `xclip`
- Not: `xorg-server` paketi `sddm` hard-dep olarak yine kurulur,
  ama SDDM `[X11] Enable=false` + `xsessions/` BOŞ → X11 oturumu
  seçilemez, kullanılamaz. `xwayland` ise `xorg-server-common` bağımlı
  (xorg-server DEĞIL) — bu doğru.

### 2) Oturum dosyaları + SDDM
- `xsessions-plasma.desktop` branding PKGBUILD'ten KALDIRILDI
  (source + install + doğrulama; dosya + symlink silindi)
- `sddm-yerinde.conf`: `[X11] Enable=false` (Wayland Enable=true KALDI)
- SDDM `Main.qml`: "Oturum:" etiketi + ComboBox
  `visible: sessionModel.count > 1` (tek oturumda gizlenir)

### 3) build-iso.sh güncellendi
- X11TOOLS paket doğrulamaları → TERSINE çevrildi (xorg-server vs
  packages'te YOK Failure)
- POST H2: `wayland-sessions/plasma.desktop` + `startplasma-wayland`
  + `Xwayland` VAR; `xsessions/` BOŞ; SDDM `[X11] Enable=false`
- POST §2a (xrandr/xrdb/xsetroot/xmessage/sessreg ls) → KALDIRILDI
  (plasma-workspace hard-dep olarak kurar; BILINÇLI)
- `--post-only` bayrağı eklendi (ISO yeniden derlemesi yapmadan son
  doğrulama)

### 4) Branding paketi
- `yerinde-branding-1.2.0-13` (pkgrel 12→13)
- SKIP count 34→33 (xsessions-plasma.desktop çıktı)
- makepkg başarılı, tüm doğrulamalar OK
- `repo-add` her iki repo (ISO-facing + GitHub-facing)
- Repo DB: `calamares-3.4.2-3`, `yerinde-ai-assistant-1.2.0-6`,
  `yerinde-branding-1.2.0-13`

### 5) ISO Build
- `mkarchiso` setsid+log ile çalıştı
- **ISO:** `yerinde-2026.08.16-x86_64.iso`
- **Boyut:** 2,7G
- **sha256:** `a465741c18821379e9cec7242a309159839216b21e47f0caaafc40d89c115c95`

---

## POST DOĞRULAMALAR (TÜMÜ BAŞARILI)

```
== [3] BUILD SONRASI DOĞRULAMA ==
POST OK (H2 final19): wayland-sessions/plasma.desktop + startplasma-wayland + Xwayland VAR
POST OK (final19 §2): /usr/share/xsessions/ BOŞ (X11 oturumu seçilemez)
  ls xsessions/ → toplam 0 (BOŞ)
  ls wayland-sessions/ → plasma.desktop (3909 byte)
  ls /usr/bin/ → startplasma-wayland (122248) + Xwayland (2360840)
POST OK (§1 inceltme): asistan/ollama/ydotool/yerinde-ai/uinput ISO'da YOK
POST OK (§2b): pam_systemd.so (sddm + sddm-autologin)
POST OK (§2c): yerinde-reboot + yerinde-poweroff .desktop (systemctl + OnlyShowIn=KDE)
POST OK (§3): calamares-3.4.2-3 (Türkçe çeviri gömülü, "Calamares" YOK)
POST OK (H1 final19): sddm teması + conf (Current=yerinde + Wayland=true + X11=false)
POST OK (F1): Main.qml oturum seçici + sddm.login(sessionIndex)
POST OK (regresyon): 5 duvar kağıdı metadata.desktop
POST OK (regresyon): GRUB teması (krem + select şerit + font)
POST OK (regresyon): sudoers wheel + ilk-oturum betiği
== TÜM POST DOĞRULAMALAR BAŞARILI ==
```

### SDDM conf içeriği (work airootfs)
```ini
[Theme]
Current=yerinde

[Wayland]
Enable=true

[X11]
Enable=false
```

### ls /usr/share/xsessions/ (work airootfs)
```
toplam 0
drwxr-xr-x 1 root root 0 Ağu  5 00:54 .
drwxr-xr-x 1 root root 3724 Ağu 16 23:59 ..
```
BOŞ — hiçbir .desktop yok.

### ls /usr/share/wayland-sessions/ (work airootfs)
```
-rw-r--r-- 1 root root 3909 Ağu  5 00:54 plasma.desktop
```
Tek oturum: Plasma (Wayland).

### ls /usr/bin/Xwayland + startplasma-wayland (work airootfs)
```
-rwxr-xr-x 1 root root  122248 Ağu  5 00:54 startplasma-wayland
-rwxr-xr-x 1 root root 2360840 Tem  8 09:07 Xwayland
```

---

## BILINÇLI KARARLAR

1. **`xorg-server` ISO'da KALDI** (sddm hard-dep). Kullanıcı DOSYASINDA
   da not edildi: "Mevcut VM'de reinstall şart değilse: sudo pacman -Rs
   xorg-server ile X11'i oradan da atabilirsin; ama temiz test = yeni ISO."
   X11 oturumu seçilemez (xsessions BOŞ + SDDM [X11] Enable=false) —
   fonksiyonel olarak Wayland-tek oturum sağlanır.

2. **`startplasma-x11` binary KALDI** (plasma-workspace paketinin parçası;
   hem Wayland hem X11 binary tek paketle gelir). Kullanılmaz çünkü
   xsessions/plasma.desktop yok + SDDM X11 kapatık.

3. **`xorg-xrandr`, `xorg-xrdb`, `xorg-xmessage`** plasma-workspace
   hard-dep olarak kurulur. packages.x86_64'ten sildik ama bağımlılık
   zinciri kurar. Kullanılmayan X11 oturum araçlarıdır; zararsız.

---

## REGRESYON KORUMASI (DOKUNULMADI)
- MBR krem menü (syslinux splash + archiso_head.cfg "Yerinde")
- GRUB teması (krem + select şerit + font + fallback)
- 5 duvar kağıdı
- sudoers wheel
- SDDM krem tema + Enter + ⟳⏻ düğmeleri
- "Calamares" temizliği (Türkçe çeviri .ts gömülü, kaynaklar dokunulmaz)
- Asistan ISO'da YOK (paket + airootfs + users.conf temiz)
- İlk-oturum betiği (yerinde-first-run.sh + .desktop + kickoff ikonu)
- ydotool/Wayland araç zinciri (asistan repo'da, ISO'da yok)

---

## KULLANICI TEST LISTESİ

1. **SDDM:** Tek oturum "Plasma (Wayland)" görünür; Oturum seçici
   GİZLİ (sessionModel.count > 1 = false → etiket + ComboBox görünmez);
   giriş sorunsuz
2. **Pencere süsleri:** Kapat düğmeleri + Alt+F4 ÇALIŞIR (KWin Wayland)
3. **Bırakma menüsü:** Uyut/Yeniden Başlat/Kapat tıklanır (pam_systemd
   + systemctl reboot/poweroff .desktop belt-and-suspenders)
4. **Tkinter asistan:** xwayland üstünde açılır (repo'dan kurulumda;
   ISO'da asistan yok, kullanıcı kurar)
5. **UEFI+MBR kurulum:** Calamares regresyonu YOK (hem BIOS hem UEFI boot
   setup mkarchiso tarafından hazır)