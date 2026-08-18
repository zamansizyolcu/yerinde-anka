# YERINDE OS v1.7 — final18 Uygulama Raporu (2026-08-16)

## 1) İNCELTME: Asistan + ollama + ydotool ISO'dan TOPTAN çıkarıldı (§1)

**packages.x86_64** — silinen paketler: `yerinde-ai-assistant`, `ollama`, `ydotool`,
`python-opencv`, `python-psutil`, `python-pillow`, `portaudio`, `ffmpeg` (asistan
için olanlar). X11 araçları (`xorg-xrandr/xrdb/xsetroot/xmessage/sessreg`) açık
listeli; `xdotool/xorg-xhost/xorg-xprop/xorg-xwininfo/wmctrl/xclip` korundu.

**airootfs overlay** — silinen kalıntılar:
- `etc/tmpfiles.d/ollama.conf` (ollama dizinleri yaratıyordu)
- `etc/sysusers.d/ollama.conf` (ollama system user)
- `etc/sysusers.d/uinput.conf` (uinput modülü → ydotool)
- `usr/bin/yerinde-ollama-setup` (ollama kurulum betiği)

**profiledef.sh** — `file_permissions`'tan `yerinde-ollama-setup`,
`yerinde-modeller/`, `var/lib/ollama/models/` satırları silindi.
**users.conf** — `defaultGroups`: `uinput`/`input` SİLİNDİ, `wheel` korundu.
**branding PKGBUILD** — `modules-load-uinput.conf` kaynağı + install/doğrulama
/ kaldırıldı.

**NOT:** `yerinde-ai-assistant` REPO'da kalır (pacman ile kurulabilir); pkgrel
6→7 bump + `post_install()` bildirimi eklendi (§EK).

Doğrulama (POST): ISO'nun pacman local DB'sinde `ollama`/`yerinde-ai-assistant`/
`ydotool` paketleri YOK; `/etc/passwd`'de ollama user YOK; `/usr/share/ollama`,
`/var/lib/ollama`, `/usr/share/yerinde-ai`, `/usr/bin/yerinde` YOK;
`multi-user.target.wants`'ta ollama/ydotool linki YOK.

## 2) X11 OTURUMDA KAPAT/YENİDEN BAŞLAT DÜZELTMESİ (§2)

### a) startplasma-x11 X11 araçları (ls kanıtı)
work/x86_64/airootfs'te kurulu (pacman local):
```
14352  /usr/bin/sessreg
27552  /usr/bin/xmessage
67776  /usr/bin/xrandr
34992  /usr/bin/xrdb
22616  /usr/bin/xsetroot
```
Ayrıca `usr/bin/Xorg` + `usr/bin/startplasma-x11` kurulu (H2 OK).

### b) PAM pam_systemd.so (§2b)
`airootfs/etc/pam.d/sddm` ve `sddm-autologin` overlay'leri açıkça
`-session optional pam_systemd.so` satırı içerir (oturum systemd-logind'ye
kaydolmazsa güç istekleri sessizce reddedilir). POST kanıtı:
```
/etc/pam.d/sddm:            -session    optional    pam_systemd.so
/etc/pam.d/sddm-autologin:  -session    optional    pam_systemd.so
```

### c) KDE menüsü güç kısayolları (§2c) — branding paketinden
- `/usr/share/applications/yerinde-reboot.desktop` — `Exec=systemctl reboot`
  `Name=Yeniden Başlat`, `OnlyShowIn=KDE`
- `/usr/share/applications/yerinde-poweroff.desktop` — `Exec=systemctl poweroff`
  `Name=Bilgisayarı Kapat`, `OnlyShowIn=KDE`

Plasma ayrılma menüsü D-Bus yolu başarısız olsa bile bu kısayollar yedek güvence
sağlar. POST: her iki .desktop Exec + OnlyShowIn=KDE OK.

### d) polkit-kde-agent-1 düzeltmesi (finalmini18)
`polkit-kde-agent-1` packages.x86_64'ten SİLİNDİ (yanlış paket adı — "target not
found" hatası). Doğru paket `polkit-kde-agent` (extra); `plasma-meta` →
`plasma-workspace`/`plasma-desktop` bağımlılık olarak kurar. POST: pacman local
DB'de `polkit-kde-agent-6.7.4-1` kurulu.

## 3) KURULUM EKRANINDAN "Calamares" YAZISINI ÇIKAR (§3)

Calamares Qt çevirileri harici .qm olarak değil, **ikili içine gömülü** derlenir
(calamares-i18n object lib, `calamares_qrc_translations`). Bu yüzden:
1. Kaynak `calamares_tr_TR.ts` (5423 satır) kopyalandı; Python ile Türkçe
   `<translation>` hedeflerindeki "Calamares" → "Yerinde OS" değiştirildi
   (welcome başlığı: 2x "Yerinde OS Kurulum Sihirbazına hoş geldiniz";
   10 ek hedef). Kaynak `<source>` metinlere DOKUNULMADI (14 "Calamares" korundu).
2. PKGBUILD `prepare()` düzeltmeyi uygular + doğrular (hedeflerde Calamares YOK).
3. `makepkg` → `lrelease` .ts'i .qm'e derleyip ikiliye gömer.
4. **lconvert doğrulama** (`/tmp/opencode/kontrol-calamares.ts`):
```
hedef(translation) Calamares: 0  (YOK) ✓
kaynak(source) Calamares:    14  (dokunulmadı) ✓
welcome "Yerinde OS Kurulum Sihirbazına": 2 ✓
```

## 4) PAKET + BUILD + RAPOR (§4)

### Paketler
- **yerinde-branding** 1.2.0-11 → **1.2.0-12**: `modules-load-uinput.conf` +
  uinput install/doğrulama kaldırıldı; 2 güç .desktop + doğrulama eklendi.
- **calamares** 3.4.2-2 → **3.4.2-3**: `calamares_tr_TR.ts` kaynak eklendi,
  `prepare()` ile değiştirme + doğrulama; `lrelease` gömme.
- **yerinde-ai-assistant** 1.2.0-6 → **1.2.0-7**: `post_install()` bildirimi
  eklendi (REPO'da; ISO'da yok).
- **README.md** (/home/yerinde/yerinde-repo): GitHub'a gidecek; depo ekleme +
  çevrimdışı AI modu talimatı.

Her iki repo (ISO-facing `repo/x86_64` + GitHub-facing `yerinde-repo/x86_64`)
`repo-add -R` ile güncellendi.

### ISO rebuild (setsid+log)
```
mkarchiso -v -w work -o out .  →  setsid + /tmp/opencode/yerinde-iso-build.log
[mkarchiso] INFO: Done!
2.7G  yerinde-2026.08.16-x86_64.iso
```

### Boyut + sha256
```
ISO:    yerinde-2026.08.16-x86_64.iso
boyut:  2,807,857,152 bayt (2.62 GB)  —  hedef ≤3.5GB: EVET ✓
önceki: 19,727,026,176 bayt (19 GB)   —  final16 (asistan+GGUF+ollama store)
küçülme: 7.0x    tasarruf: 85.8%

SHA256: 957b8db8ddd65af3e7008af0901fcd8147f8a2672ef3938b937b81c8a0fc51b9
sha256sum -c SHA256SUMS → Tamam ✓
```

### Tüm POST doğrulamaları başarılı
```
H2  OK: xsessions/plasma.desktop + wayland-sessions/plasma.desktop + Xorg + startplasma-x11
§2a OK: /usr/bin/{xrandr,xrdb,xsetroot,xmessage,sessreg} kurulu (ls kanıtı)
§1  OK: asistan/ollama/ydotool/yerinde-ai/uinput/sysusers/tmpfiles/ollama-setup/ollama-user ISO'da YOK
§2b OK: /etc/pam.d/sddm + sddm-autologin içinde pam_systemd.so var
§2c OK: yerinde-reboot.desktop (systemctl reboot) + yerinde-poweroff.desktop (systemctl poweroff) + OnlyShowIn=KDE
§3  OK: calamares-3.4.2-3 kuruldu (Türkçe çeviri .ts içinde gömülü, hedeflerde Calamares YOK)
H1  OK: sddm teması + sddm.conf.d/yerinde.conf (Current=yerinde)
F1  OK: Main.qml oturum seçici (onValueChanged: sessionIndex = index) + sddm.login(sessionIndex)
regresyon OK: 5/5 duvar kağıdı (Hologram-Mavi, Krem, Dalga-Mavi, Yesil, Mor)
regresyon OK: GRUB teması (theme.txt + background + logo + DejaVuSans-32.pf2 + select_c.png + title-text)
regresyon OK: /etc/sudoers.d/wheel + yerinde-finalize.sh + ilk-oturum autostart .desktop + .sh
== TÜM POST DOĞRULAMALAR BAŞARILI ==
```

## 5) Kullanıcı test listesi (VM/donanım kurulumunda)

1. **X11 oturumu**: Plasma (X11) oturumunda Başlat > Oturumu Kapat / Yeniden
   Başlat çalışmalı. Yedek menü kısayolları (Uygulamalar menüsünde "Yeniden
   Başlat" / "Bilgisayarı Kapat") da çalışmalı.
2. **Kurulum ekranı başlığında "Calamares" YOK**: kurulum sihirbazı açıldığında
   başlık "Yerinde OS Kurulum Sihirbazına hoş geldiniz" olmalı.
3. **Canlı menüde YERINDE asistan YOK**: Masaüstü/kickoff'ta AI asistan kısayolu
   OLMAMALI; ISO ~2.6 GB. (Asistanı kurmak için: `pacman -S yerinde-ai-assistant`
   — yerinde-repo eklenmeli; README.md'ye bakın.)
4. **UEFI+MBR kurulum**, SDDM (krem tema + Enter + güç düğmeleri + yan yana
   oturum seçici), GRUB/MBR menüler regresyonsuz: 5 duvar kağıdı, wheel sudoers,
   ilk-oturum betiği (duvar kağıdı + kickoff ikonu).

## EK — PKGBUILD post_install + README.md

`yerinde-ai-assistant` PKGBUILD `post_install()` (pkgrel 7):
```
YERINDE kuruldu. Çevrimdışı mod için:
  systemctl enable --now ollama
  ollama pull llama3.1 && ollama pull qwen2.5-coder:1.5b
```
Aynı talimat `/home/yerinde/yerinde-repo/README.md` içinde (GitHub'a gidecek).

## Notlar — build-iso.sh düzeltmeleri

- `rg -qE` → `rg -q` (ripgrep `-E` = encoding flag'ı, extended regex değil;
  `wait_build` complete/error tespiti düzeltildi).
- `verify_post` F1: `rg -q` → `grep -q` (desen `()` içerir; ripgrep yakalama
  grubu yorumlar — literal eşleşme için `grep -q` temel regex kullanır).
- `verify_sources`'a `tmpfiles.d/ollama.conf`, `sysusers.d/(ollama|uinput).conf`,
  `usr/bin/yerinde-ollama-setup` prep kontrolleri eklendi.
- `polkit-kde-agent-1` yanlış adı için explicit FAIL kontrolü eklendi.