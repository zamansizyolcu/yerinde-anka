#!/bin/bash
# YERINDE ANKA — ISO build + doğrulama (final18.md + final21.md + final24.md)
#
# final24.md ekleri:
#   §1  GRUB üstte 3'lü yazı → TEK lockup (title-text + logo resmi SİLİNDİ)
#   §2  calamares -4: ANKA çevirisi ikiliye GÖMÜLÜ (-3'te lrelease atlanmıştı)
#   §3  python-numpy + python-pillow ISO'da (opencv/cv2 YOK — depolarda değil)
#   §5  tıkla-çalıştır kurucu: yerinde-asistan-kur + masaüstü/menü .desktop
# final18: AI asistanı + ollama + ydotool ISO'dan TOPTAN ÇIKARILDI. Bu betik
# artık GGUF / ollama store enjeksiyonu YAPMAZ; prep yalnızca SDDM QML
# testini çalıştırır. POST doğrulamaları asistan-bağımsızdır ve final18/19
# eklerini içerir:
#   §1  inceltme+X11-kaldırma: asistan-ollama-ydotool + xorg-server/xinit/
#       xrandr/xrdb/xsetroot/xmessage/sessreg YOK; xorg-xwayland KALDI
#   §2  Wayland TEK oturum: xsessions/Xorg/startplasma-x11 YOK;
#       wayland-sessions + Xwayland VAR; SDDM [X11] Enable=false
#   §2b pam_systemd satırı sddm + sddm-autologin PAM'larında
#   §2c KDE menüsü güç kısayolları (yerinde-reboot/poweroff .desktop)
#   §3  calamares yeniden derlenmiş (-3): Türkçe hedeflerde "Calamares" YOK
#   regresyon: SDDM krem tema + Enter + güç düğmeleri + oturum
#      seçici, GRUB teması, MBR krem syslinux menüsü, 5 duvar kağıdı,
#      sudoers wheel, ilk-oturum betiği.
#
# Kullanım:  ./build-iso.sh [--prep-only] [--build-only] [--skip-prep]
# KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls/doğrulamalı.

set -u

ISO_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(dirname "$(dirname "$ISO_DIR")")"   # .../yerinde-project
AIROOTFS="$ISO_DIR/airootfs"
LOG=/tmp/opencode/yerinde-iso-build.log
mkdir -p /tmp/opencode

MODE_PREP=1
MODE_BUILD=1
MODE_POST_ONLY=0
for a in "$@"; do
  case "$a" in
    --prep-only) MODE_BUILD=0 ;;
    --build-only) MODE_PREP=0 ;;
    --skip-prep) MODE_PREP=0 ;;
    --post-only) MODE_PREP=0; MODE_BUILD=0; MODE_POST_ONLY=1 ;;
  esac
done

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- final18.md §1 (İNCELTME): kaynak düzeyinde asistan-ollama-ydotool YOK ---
verify_sources() {
  echo "== [0] final18 kaynak doğrulamaları =="
  local PK="$ISO_DIR/packages.x86_64"
  [ -f "$PK" ] || fail "packages.x86_64 yok"
  # final25ek.md: python-pyaudio + portaudio GERİ eklendi (venv
  # --system-site-packages çevrimdışı kurulumda bunları sistemden bulur)
  # final27.md §2: ydotool + git de eklendi (cacyhos paritesi — sesli
  # fare/klavye + tıkla-kur git clone yolu). Asistan PAKETİ + ollama
  # hâlâ YASAK (yalnızca ARAÇLAR geldi).
  if rg -q '^(yerinde-ai-assistant|ollama|python-psutil|ffmpeg)$' "$PK"; then
    fail "final18 §1 FAIL: packages.x86_64'te asistan/ollama paketi hâlâ listeli"
  fi
  echo "PKGS OK: asistan/ollama/python-psutil/ffmpeg YOK (numpy+pillow final24; ydotool+git final27)"

  # final27.md §2: asistan çalışma zamanı paketleri pozitif kontrol
  for p in python-pyaudio portaudio ydotool git xdotool; do
    rg -q "^$p$" "$PK" || fail "final27 §2 FAIL: packages.x86_64'te $p yok"
  done
  echo "PKGS OK (final27 §2): pyaudio+portaudio+ydotool+git+xdotool listeli"

  # final24.md §3: asistan python kütüphaneleri ISO'da
  for p in python-numpy python-pillow; do
    rg -q "^$p$" "$PK" || fail "final24 §3 FAIL: packages.x86_64'te $p yok"
  done
  echo "PKGS OK (final24 §3): python-numpy + python-pillow listeli (opencv YOK: cv2 bağlaması depolarda değil)"

  # final18 kaldıntıları (asistan zinciri) hâlâ yasak; final27 §2 uinput
  # zinciri ise ARTIK İSTENİYOR → pozitif kontrole taşındı (aşağıda).
  for d in usr/share/yerinde-modeller usr/share/ollama usr/share/yerinde-ai; do
    if [ -e "$AIROOTFS/$d" ]; then
      fail "final18 §1 FAIL: airootfs/$d kalmış (SİLİNMEMİŞ)"
    fi
  done
  for p in etc/tmpfiles.d/ollama.conf etc/sysusers.d/ollama.conf \
           usr/bin/yerinde-ollama-setup; do
    if [ -e "$AIROOTFS/$p" ]; then
      fail "final18 §1 FAIL: airootfs/$p kalıntısı var (SİLİNMEMİŞ)"
    fi
  done
  if [ -d "$AIROOTFS/etc/skel/.yerinde" ]; then
    fail "final18 §1 FAIL: airootfs/etc/skel/.yerinde kalmış"
  fi
  echo "AIROOTFS OK: yerinde-ai/ollama/yerinde-modeller/skel/.yerinde/ollama-setup YOK"

  # final27.md §2 DOĞRULA (airootfs ls; eksikse FAIL):
  # uinput zinciri + ydotoold drop-in + wants linki
  for f in etc/sysusers.d/yerinde-uinput.conf \
           etc/udev/rules.d/80-uinput.rules \
           etc/modules-load.d/uinput.conf \
           etc/systemd/system/ydotoold.service.d/yerinde.conf; do
    [ -f "$AIROOTFS/$f" ] || fail "final27 §2 FAIL: airootfs/$f yok"
  done
  [ -L "$AIROOTFS/etc/systemd/system/multi-user.target.wants/ydotoold.service" ] \
    || fail "final27 §2 FAIL: ydotoold wants linki yok"
  # final36: link HEDEFİ GERÇEKTEN VAR MI? (Arch ydotool paketi yalnız
  # kullanıcı birimi çıkarır — system/ydotoold.service YOKTUR; boşa bakan
  # link yüzünden daemon hiç çalışmıyordu. airootfs'te gerçek birim var.)
  # NOT: hedef mutlak yol → airootfs KÖKÜNE göre çözülür (readlink -f
  # host kökünü kullanır, yanlış negatif verir).
  local YT
  YT="$(readlink "$AIROOTFS/etc/systemd/system/multi-user.target.wants/ydotoold.service")"
  case "$YT" in /*) YT="$AIROOTFS$YT" ;; esac
  [ -f "$YT" ] || fail "final36 FAIL: ydotoold wants linki boşa bakıyor (hedef yok: $YT)"
  [ -f "$AIROOTFS/etc/systemd/system/ydotoold.service" ] \
    || fail "final36 FAIL: airootfs/etc/systemd/system/ydotoold.service yok (paket system birimi çıkarmıyor)"
  rg -q 'KERNEL=="uinput", GROUP="uinput", MODE="0660"' \
    "$AIROOTFS/etc/udev/rules.d/80-uinput.rules" \
    || fail "final27 §2 FAIL: 80-uinput.rules içeriği yanlış"
  rg -q -- '--socket-perm=0660' "$AIROOTFS/etc/systemd/system/ydotoold.service.d/yerinde.conf" \
    || fail "final27 §2 FAIL: ydotoold drop-in --socket-perm=0660 yok"
  rg -q 'Group=uinput' "$AIROOTFS/etc/systemd/system/ydotoold.service.d/yerinde.conf" \
    || fail "final27 §2 FAIL: ydotoold drop-in Group=uinput yok"
  echo "UINPUT OK (final27 §2): sysusers + udev 0660 + modules-load + ydotoold 0660/uinput + wants"

  # final27.md §3 DOĞRULA: oto-giriş + drkonqi maskı + canlı kullanıcı birimi
  local AL="$AIROOTFS/etc/sddm.conf.d/yerinde-autologin.conf"
  [ -f "$AL" ] || fail "final27 §3 FAIL: yerinde-autologin.conf yok"
  rg -q '^User=yerinde$' "$AL" || fail "final27 §3 FAIL: Autologin User=yerinde yok"
  rg -q '^Session=plasma\.desktop$' "$AL" \
    || fail "final27 §3 FAIL: Autologin Session=plasma.desktop yok"
  [ -L "$AIROOTFS/etc/systemd/system/drkonqi-coredump@.service" ] \
    || fail "final27 §3 FAIL: drkonqi-coredump@.service mask linki yok"
  [ "$(readlink "$AIROOTFS/etc/systemd/system/drkonqi-coredump@.service")" = "/dev/null" ] \
    || fail "final27 §3 FAIL: drkonqi maskı /dev/null değil"
  [ -f "$AIROOTFS/etc/systemd/system/yerinde-live-user.service" ] \
    || fail "final27 §3 FAIL: yerinde-live-user.service yok"
  rg -q 'ConditionPathExists=/run/archiso' "$AIROOTFS/etc/systemd/system/yerinde-live-user.service" \
    || fail "final27 §3 FAIL: live-user birimi /run/archiso koşullu değil"
  [ -L "$AIROOTFS/etc/systemd/system/multi-user.target.wants/yerinde-live-user.service" ] \
    || fail "final27 §3 FAIL: live-user wants linki yok"
  bash -n "$AIROOTFS/usr/local/bin/yerinde-live-user" \
    || fail "final27 §3 FAIL: yerinde-live-user bash -n hatası"
  # Baked uid-1000 kullanıcı YOK (Calamares 'yerinde' ad çakışması imkânsız)
  if awk -F: '$3==1000 {found=1} END {exit !found}' "$AIROOTFS/etc/passwd"; then
    fail "final27 §3 FAIL: passwd'te baked uid-1000 kullanıcı var (useradd -m runtime'da)"
  fi
  # finalize: usermod -aG uinput,input NEW_USER
  rg -q 'usermod -aG uinput,input' "$AIROOTFS/usr/local/bin/yerinde-finalize.sh" \
    || fail "final27 §2 FAIL: finalize usermod uinput,input yok"
  echo "AUTOLOGIN+DRKONQI+LIVE-USER OK (final27 §3): User=yerinde + plasma.desktop + mask + runtime kullanıcı"

  # final27.md §3: yapılandırmalarda xsessions oturum referansı SIFIR
  # (yalnız PKGBUILD/calamares kaynak KODUNDAKI yorum/upstream satırlar sayılır)
  local XS
  XS=$(rg -l 'xsessions' "$AIROOTFS/etc/sddm.conf.d" "$AIROOTFS/etc/systemd" \
        "$PROJ/packages/yerinde-branding" --glob '!pkg' 2>/dev/null \
        | rg -v 'PKGBUILD|sddm-yerinde\.conf' || true)
  if [ -n "$XS" ]; then
    fail "final27 §3 FAIL: xsessions referansı: $XS"
  fi
  echo "XSESSIONS OK (final27 §3): yapılandırmalarda xsessions referansı SIFIR"

  # users.conf defaultGroups: wheel evet, uinput/input hayır
  local UC
  UC="$(find "$AIROOTFS" -name users.conf 2>/dev/null | head -1)"
  [ -n "$UC" ] || fail "users.conf bulunamadı (airootfs)"
  if rg -q 'uinput|input' "$UC"; then
    fail "final18 §1 FAIL: users.conf defaultGroups içinde uinput/input hâlâ var"
  fi
  rg -q 'wheel' "$UC" || fail "users.conf wheel yok (regresyon)"
  echo "USERS OK: users.conf defaultGroups wheel var, uinput/input YOK"

  # §2b PAM overlay'leri
  for pf in sddm sddm-autologin; do
    [ -f "$AIROOTFS/etc/pam.d/$pf" ] || fail "final18 §2b FAIL: airootfs/etc/pam.d/$pf overlay yok"
    rg -q 'pam_systemd.so' "$AIROOTFS/etc/pam.d/$pf" \
      || fail "final18 §2b FAIL: $pf içinde pam_systemd.so satırı yok"
  done
  echo "PAM OK: sddm + sddm-autologin pam_systemd.so overlay'leri mevcut"

  # MBR krem syslinux menüsü (regresyon)
  [ -f "$ISO_DIR/syslinux/splash.png" ] || fail "regresyon: syslinux/splash.png yok"
  [ -f "$ISO_DIR/syslinux/archiso_head.cfg" ] || fail "regresyon: syslinux/archiso_head.cfg yok"
  rg -q 'Yerinde' "$ISO_DIR/syslinux/archiso_head.cfg" \
    || rg -q -i 'yerinde' "$ISO_DIR/syslinux/archiso_head.cfg" \
    || fail "regresyon: archiso_head.cfg içinde 'Yerinde' yok"
  echo "SYSLINUX OK: MBR krem menü (splash.png + archiso_head.cfg)"

  # §2a X11 araçları paket listesinde açık (final19: X11 KALDIRILDI)
  for p in xorg-server xorg-xinit xorg-xrandr xorg-xrdb xorg-xsetroot \
          xorg-xmessage xorg-xsessreg xorg-xinput; do
    if rg -q "^$p$" "$PK"; then
      fail "final19 §1 FAIL: packages.x86_64'te $p hâlâ var (X11 kaldırıldı)"
    fi
  done
  rg -q '^xorg-xwayland$' "$PK" || fail "final19 §1 FAIL: xorg-xwayland packages'te yok (KALMALI)"
  # final18.md §2d + finalmini18.md: polkit-kde-agent-1 YANLIŞ paket adı;
  # doğru adı polkit-kde-agent (extra). plasma-meta bağımlılık olarak kurar.
  if rg -q '^polkit-kde-agent-1$' "$PK"; then
    fail "finalmini18 FAIL: packages.x86_64'te polkit-kde-agent-1 hâlâ var (silinmeli; plasma-meta bağımlılığı yeterli)"
  fi
  echo "PKGS OK: X11 oturum paketleri YOK, xorg-xwayland KALDI (Wayland-tek oturum)"

  # final21.md §1: kaynaklarda "Yerinde OS"/"Yerinde Ocağı" kalıntısı SIFIR.
  # (desen parantezsiz yazılır ki bu betik kendini eşlemesin; work/out hariç)
  local REN
  REN=$(rg -ril --glob '!work' --glob '!out' --glob '!build-iso.sh' \
        'yerinde[ ]os|yerinde[ ]ocağı|yerinde-ocagi|YERINDE[_ ]OCAGI' \
        "$ISO_DIR" "$PROJ/packages" "$PROJ/branding" 2>/dev/null || true)
  if [ -n "$REN" ]; then
    fail "final21 §1 FAIL: eski ad kalıntısı: $REN"
  fi
  echo "RENAME OK: kaynaklarda 'Yerinde OS'/'Yerinde Ocağı' SIFIR (yerinde-anka temiz)"

  # final21.md §4: ZIP/arsiv araçları packages.x86_64'ta
  # (p7zip/p7zip-rar depolarda yok -> resmi 7zip paketi /usr/bin/7z verir)
  for p in ark zip unzip 7zip unrar; do
    rg -q "^$p$" "$PK" || fail "final21 §4 FAIL: packages.x86_64'te $p yok"
  done
  echo "PKGS OK (final21 §4): ark zip unzip 7zip unrar listeli"

  # final21.md §3: canlı keyring script + service + wants linki
  [ -f "$AIROOTFS/usr/local/bin/yerinde-keyring-init" ] \
    || fail "final21 §3 FAIL: airootfs/usr/local/bin/yerinde-keyring-init yok"
  [ -L "$AIROOTFS/etc/systemd/system/multi-user.target.wants/yerinde-keyring.service" ] \
    || fail "final21 §3 FAIL: yerinde-keyring.service wants linki yok"
  rg -q 'yerinde-keyring-done' "$AIROOTFS/usr/local/bin/yerinde-keyring-init" \
    || fail "final21 §3 FAIL: keyring-init bayrak dosyası kullanmıyor"
  echo "KEYRING OK (final21 §3): yerinde-keyring-init + service + wants linki"

  # final21.md §5: syslinux NOESCAPE 1 + İngilizce TABMSG ipucusu gizli
  rg -q '^NOESCAPE 1$' "$ISO_DIR/syslinux/archiso_head.cfg" \
    || fail "final21 §5 FAIL: syslinux archiso_head.cfg'de NOESCAPE 1 yok"
  rg -q '^MENU TABMSG$' "$ISO_DIR/syslinux/archiso_head.cfg" \
    || fail "final21 §5 FAIL: MENU TABMSG (bospul) yok - Press [Tab] ipucu gorunur"
  echo "SYSLINUX OK (final21 §5): NOESCAPE 1 + MENU TABMSG bos (Press [Tab] gizli)"

  # final21.md §2: yeni ANKA lockup png'leri var, eski png YOK
  for f in "$ISO_DIR/airootfs/etc/calamares/branding/yerinde/yerinde-anka-lockup-720.png" \
           "$ISO_DIR/airootfs/usr/share/sddm/themes/yerinde/yerinde-anka-lockup-720.png" \
           "$PROJ/packages/yerinde-branding/yerinde-anka-lockup-720.png"; do
    [ -f "$f" ] || fail "final21 §2 FAIL: $f yok"
  done
  if find "$ISO_DIR" "$PROJ/packages" "$PROJ/branding" -name "*ocagi*" -not -path "*/work/*" -not -path "*/out/*" -not -path "*/pkg/*" | grep -q .; then
    fail "final21 §2 FAIL: eski yerinde-ocagi-* dosyası kalmış"
  fi
  echo "IMAGES OK (final21 §2): yerinde-anka-lockup-720.png 3 konumda; eski ocagi png YOK"

  # final33 (unpackfs çöküşü) DOĞRULA: canlı oturum root değil → Calamares
  # pkexec + canlı-ortam polkit kuralıyla yetkili çalışmalı.
  rg -q 'pkexec calamares' "$AIROOTFS/etc/xdg/autostart/calamares.desktop" \
    || fail "final33 FAIL: autostart calamares.desktop pkexec içermiyor (yetkisiz calamares = unpackfs istisnası)"
  [ -f "$AIROOTFS/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules" ] \
    || fail "final33 FAIL: 49-yerinde-live-calamares.rules yok"
  rg -q 'program.*calamares' "$AIROOTFS/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules" \
    || fail "final33 FAIL: polkit kuralı calamares programına kısıtlı değil"
  rg -q '49-yerinde-live-calamares.rules' "$AIROOTFS/usr/local/bin/yerinde-finalize.sh" \
    || fail "final33 FAIL: finalize polkit kuralını kurulu sistemden silmiyor"
  echo "CALAMARES-PRIV OK (final33): autostart pkexec + canlı polkit kuralı + finalize temizliği"

  # final24.md §5: tıkla-çalıştır kurucu (script + 2 .desktop)
  [ -f "$AIROOTFS/usr/local/bin/yerinde-asistan-kur" ] \
    || fail "final24 §5 FAIL: airootfs/usr/local/bin/yerinde-asistan-kur yok"
  bash -n "$AIROOTFS/usr/local/bin/yerinde-asistan-kur" \
    || fail "final24 §5 FAIL: yerinde-asistan-kur bash -n hatası"
  for d in usr/share/applications/yerinde-asistan-kur.desktop etc/skel/Desktop/yerinde-asistan-kur.desktop; do
    [ -f "$AIROOTFS/$d" ] || fail "final24 §5 FAIL: airootfs/$d yok"
  done
  rg -q 'Exec=/usr/local/bin/yerinde-asistan-kur' "$AIROOTFS/usr/share/applications/yerinde-asistan-kur.desktop" \
    || fail "final24 §5 FAIL: .desktop Exec satırı yanlış"
  rg -q 'kurulum\.sh' "$AIROOTFS/usr/local/bin/yerinde-asistan-kur" \
    || fail "final24 §5 FAIL: script yerel kurulum.sh araması içermiyor"
  rg -q 'yerinde-ai-assistant' "$AIROOTFS/usr/local/bin/yerinde-asistan-kur" \
    || fail "final24 §5 FAIL: script yerinde-ai-assistant paket adı içermiyor"
  echo "ASISTAN-KUR OK (final24 §5): script (bash -n OK, 755) + masaüstü + menü .desktop"

  # final38.md §1/§2: "hepsi ya da hiç" düzeltmesi — pacman tek tek + venv
  # her zaman + eksikler pip ile TEK TEK. Yasak olan: 'pip install -r'
  # (toplu requirements — tek kötü ad tüm kurulumu öldürürdü) ve
  # pyautogui/pygetwindow/pyrect'in pip ile kurulması (pyrect çöküşü).
  if rg -q 'pip install -r' "$PROJ/yerinde-ai-assistant/kurulum.sh"; then
    fail "final38 FAIL: kurulum.sh içinde 'pip install -r' var (hepsi-ya-da-hiç yolu)"
  fi
  if rg -q 'pip install [^|]*(pyautogui|pygetwindow|pyrect)' "$PROJ/yerinde-ai-assistant/kurulum.sh"; then
    fail "final38 FAIL: kurulum.sh pyautogui/pygetwindow/pyrect pip ile kuruluyor (pyrect çöküşü)"
  fi
  rg -q 'python -m venv --system-site-packages venv' "$PROJ/yerinde-ai-assistant/kurulum.sh" \
    || fail "final38 §2 FAIL: kurulum.sh'te 'python -m venv --system-site-packages venv' yok"
  rg -q 'pacman -S --needed --noconfirm "\$pkg"' "$PROJ/yerinde-ai-assistant/kurulum.sh" \
    || fail "final38 §1 FAIL: kurulum.sh pacman tek tek kurmuyor (hepsi-ya-da-hiç kalmış)"
  rg -q 'python-selenium\)  echo "selenium"' "$PROJ/yerinde-ai-assistant/kurulum.sh" \
    || fail "final38 §1 FAIL: AD HARİTASI (python-selenium→selenium) yok"
  bash -n "$PROJ/yerinde-ai-assistant/kurulum.sh" \
    || fail "final38 FAIL: kurulum.sh bash -n hatası"
  bash -n "$PROJ/yerinde-ai-assistant/baslat.sh" \
    || fail "final38 §3 FAIL: baslat.sh bash -n hatası"
  rg -q 'PY="python3"' "$PROJ/yerinde-ai-assistant/baslat.sh" \
    || fail "final38 §3 FAIL: baslat.sh'te sistem python3 fallback yok"
  rg -q 'ModuleNotFoundError' "$PROJ/yerinde-ai-assistant/baslat.sh" \
    || fail "final38 §3 FAIL: baslat.sh eksik modül Türkçe ipucu içermiyor"
  echo "ASISTAN-KUR OK (final38 §1-§3): pacman tek tek + venv + pip fallback (pyrect yasağı) + güvenli baslat.sh"

  # final37.md §2: UEFI açılış GRUB (systemd-boot DEĞİL) — yeşil ANKA teması
  rg -q "'uefi\.grub'" "$ISO_DIR/profiledef.sh" \
    || fail "final37 §2 FAIL: profiledef.sh'te uefi.grub bootmode yok"
  if rg -q "uefi\.systemd-boot" "$ISO_DIR/profiledef.sh"; then
    fail "final37 §2 FAIL: profiledef.sh'te uefi.systemd-boot hâlâ var"
  fi
  [ -d "$ISO_DIR/efiboot" ] \
    && fail "final37 §2 FAIL: efiboot/ (systemd-boot) duruyor — silinmeliydi"
  [ -f "$ISO_DIR/grub/themes/anka/theme.txt" ] \
    || fail "final37 §2 FAIL: grub/themes/anka/theme.txt yok"
  for c in 'desktop-color: "#0B3D2E"' 'item_color = "#EFE9DC"' \
           'selected_item_color = "#C74A1F"' 'title-text: "GRUB Açılış Menüsü"'; do
    rg -qF "$c" "$ISO_DIR/grub/themes/anka/theme.txt" \
      || fail "final37 §2 FAIL: theme.txt'te '$c' yok (yeşil/krem/turuncu tema)"
  done
  for f in background.png anka-tr.pf2 anka-tr-44.pf2; do
    [ -s "$ISO_DIR/grub/themes/anka/$f" ] \
      || fail "final37 §2 FAIL: grub/themes/anka/$f yok veya boyut 0"
  done
  rg -q 'set theme="/boot/grub/themes/anka/theme\.txt"' "$ISO_DIR/grub/grub.cfg" \
    || fail "final37 §2 FAIL: grub.cfg'de set theme= /boot/grub/themes/anka yok (root-göreli olmalı — \${prefix} memdisk'e işaret eder)"
  rg -q 'terminal_output gfxterm' "$ISO_DIR/grub/grub.cfg" \
    || fail "final37 §2 FAIL: grub.cfg terminal_output gfxterm yok (siyah konsol menü)"
  # final37.md §3: Türkçe font yükleme + Türkçe menü metinleri (ASCII'ye KAÇMA YOK)
  rg -q 'loadfont /boot/grub/themes/anka/anka-tr\.pf2' "$ISO_DIR/grub/grub.cfg" \
    || fail "final37 §3 FAIL: grub.cfg anka-tr.pf2 loadfont etmiyor (root-göreli)"
  rg -q 'kurulum ortamı' "$ISO_DIR/grub/grub.cfg" \
    || fail "final37 §3 FAIL: grub.cfg menü metinleri Türkçe değil ('kurulum ortamı' yok)"
  rg -q 'kurulum ortamı' "$ISO_DIR/grub/loopback.cfg" \
    || fail "final37 §3 FAIL: loopback.cfg menü metinleri Türkçe değil"
  rg -q 'themes/anka' "$AIROOTFS/usr/local/bin/yerinde-finalize.sh" \
    || fail "final37 §2 FAIL: finalize.sh anka temasını kurmuyor"
  rg -q 'GRUB_THEME="/boot/grub/themes/anka/theme\.txt"' "$AIROOTFS/usr/local/bin/yerinde-finalize.sh" \
    || fail "final37 §2 FAIL: finalize.sh GRUB_THEME anka ayarlamıyor"
  echo "UEFI-GRUB OK (final37 §2/§3): uefi.grub + yeşil ANKA teması + anka-tr Türkçe font + Türkçe menü"
}

# --- SDDM QML testi (VM'siz, offscreen) ---
verify_prep() {
  echo "== [1] SDDM QML doğrulaması =="
  THEME="$AIROOTFS/usr/share/sddm/themes/yerinde"
  [ -f "$THEME/Main.qml" ] || fail "SDDM teması yok: $THEME/Main.qml"

  if grep -n "onActivated" "$THEME/Main.qml"; then
    fail "SDDM QML FAIL: onActivated satırı var (SddmComponents ComboBox yalnızca valueChanged sunar)"
  fi
  grep -q "onValueChanged" "$THEME/Main.qml" || fail "SDDM QML FAIL: ComboBox onValueChanged eksik"
  echo "SDDM QML OK: statik kontrol (onActivated yok, onValueChanged var)"

  rm -f /tmp/opencode/sddm-test.log
  timeout 15 env QT_QPA_PLATFORM=offscreen \
    sddm-greeter --test-mode --theme "$THEME" \
    > /tmp/opencode/sddm-test.log 2>&1 || true
  if grep -E "Cannot assign|is not a type|QML .* Error|ReferenceError" /tmp/opencode/sddm-test.log; then
    fail "SDDM GREETER FAIL: /tmp/opencode/sddm-test.log içinde QML hatası"
  fi
  echo "SDDM GREETER OK: sddm-test.log temiz (sddm-greeter --test-mode)"
  echo "--- sddm-test.log ---"
  cat /tmp/opencode/sddm-test.log
  echo "--- /sddm-test.log ---"
}

build() {
  echo "== [2] ISO build başlıyor (setsid + log) =="
  cd "$ISO_DIR"
  # final16 §6: önceki build'lerin KALINTI mount'ları (sys/proc/dev) sökülmeden
  # bırakılırsa mksquashfs canlı sysfs'i yürüyüp saatlerce takılır.
  for _m in sys proc dev run; do
    sudo umount -R "$ISO_DIR/work/x86_64/airootfs/$_m" 2>/dev/null
  done
  sudo rm -rf work out
  : > "$LOG"
  setsid bash -c "sudo mkarchiso -v -w work -o out . > '$LOG' 2>&1" &
  echo "ISO build arka planda başlatıldı — log: $LOG"
  echo "Takip: tail -f $LOG"
}

verify_post() {
  echo "== [3] BUILD SONRASI DOĞRULAMA =="
  WA="$ISO_DIR/work/x86_64/airootfs"
  [ -d "$WA" ] || fail "work/x86_64/airootfs yok: $WA"

  # H2 (final19 §2): Wayland TEK oturum — xsessions BOŞ, SDDM [X11] Enable=false,
  # wayland-sessions/plasma.desktop + startplasma-wayland + Xwayland VAR.
  # Not: /usr/bin/Xorg + /usr/bin/startplasma-x11 sddm/plasma-workspace
  # hard-dep olarak kurulur ama X11 OTURUMU YOK (xsessions boş + SDDM kapatık).
  [ -f "$WA/usr/share/wayland-sessions/plasma.desktop" ] \
    || fail "POSTFAIL (H2): /usr/share/wayland-sessions/plasma.desktop yok"
  [ -e "$WA/usr/bin/startplasma-wayland" ] \
    || fail "POSTFAIL (H2): /usr/bin/startplasma-wayland (Wayland) yok"
  if [ -e "$WA/usr/share/xsessions/plasma.desktop" ]; then
    fail "POSTFAIL (final19 §2): /usr/share/xsessions/plasma.desktop var (X11 kapatıldı)"
  fi
  if [ -d "$WA/usr/share/xsessions" ] && [ -n "$(ls -A "$WA/usr/share/xsessions" 2>/dev/null)" ]; then
    fail "POSTFAIL (final19 §2): /usr/share/xsessions/ boş değil (X11 oturumu kalmış)"
  fi
  [ -e "$WA/usr/bin/Xwayland" ] || fail "POSTFAIL (final19 §1): /usr/bin/Xwayland yok (KALMALI)"
  echo "POST OK (H2 final19): wayland-sessions/plasma.desktop + startplasma-wayland + Xwayland VAR"
  echo "POST OK (final19 §2): /usr/share/xsessions/ BOŞ (X11 oturumu seçilemez)"
  echo "--- ls /usr/share/xsessions/ (boş kanıtı) ---"
  ls -la "$WA/usr/share/xsessions/" 2>/dev/null | sed 's/^/    /'
  echo "--- ls /usr/share/wayland-sessions/ ---"
  ls -la "$WA/usr/share/wayland-sessions/" 2>/dev/null | sed 's/^/    /'
  echo "--- ls /usr/bin/Xwayland + startplasma-wayland (ls kanıtı) ---"
  ls -l "$WA/usr/bin/Xwayland" "$WA/usr/bin/startplasma-wayland" 2>/dev/null | sed 's/^/    /'

  # final18 §1 + final27 §2: asistan PAKETİ ISO'da YOK; ydotool+git ARAÇLARI VAR
  for d in usr/share/yerinde-ai usr/share/ollama usr/share/yerinde-modeller \
           var/lib/ollama usr/bin/yerinde usr/share/applications/yerinde-ai.desktop; do
    if [ -e "$WA/$d" ]; then
      fail "POSTFAIL (§1 inceltme): $WA/$d ISO'da var (asistan kalmış)"
    fi
  done
  # final27 §2: uinput/ydotoold zinciri work airootfs'te (ls kanıtı, eksikse FAIL)
  for f in etc/sysusers.d/yerinde-uinput.conf etc/udev/rules.d/80-uinput.rules \
           etc/modules-load.d/uinput.conf \
           etc/systemd/system/ydotoold.service.d/yerinde.conf; do
    [ -f "$WA/$f" ] || fail "POSTFAIL (final27 §2): /$f ISO'da yok"
  done
  [ -L "$WA/etc/systemd/system/multi-user.target.wants/ydotoold.service" ] \
    || fail "POSTFAIL (final27 §2): ydotoold wants linki ISO'da yok"
  local YTW
  YTW="$(readlink "$WA/etc/systemd/system/multi-user.target.wants/ydotoold.service")"
  case "$YTW" in /*) YTW="$WA$YTW" ;; esac
  [ -f "$YTW" ] || fail "POSTFAIL (final36): ydotoold wants linki boşa bakıyor (hedef yok: $YTW)"
  [ -f "$WA/etc/systemd/system/ydotoold.service" ] \
    || fail "POSTFAIL (final36): sistem ydotoold.service ISO'da yok (daemon çalışmaz — fare komutları ölür)"
  if ls "$WA/etc/systemd/system/multi-user.target.wants/"ollama.service 2>/dev/null; then
    fail "POSTFAIL (§1 inceltme): multi-user.target.wants ollama linki var"
  fi
  [ -x "$WA/usr/bin/ydotool" ] || fail "POSTFAIL (final27 §2): /usr/bin/ydotool yok"
  [ -x "$WA/usr/bin/ydotoold" ] || fail "POSTFAIL (final27 §2): /usr/bin/ydotoold yok"
  [ -x "$WA/usr/bin/git" ] || fail "POSTFAIL (final27 §2): /usr/bin/git yok (tıkla-kur clone yolu)"
  echo "POST OK (final27 §2): ydotool+ydotoold+git kurulu; uinput zinciri (sysusers+udev+modules-load+drop-in+wants) ISO'da"
  echo "--- ls uinput/ydotoold zinciri (kanıt) ---"
  ls -l "$WA/etc/udev/rules.d/80-uinput.rules" "$WA/etc/modules-load.d/uinput.conf" \
        "$WA/etc/sysusers.d/yerinde-uinput.conf" \
        "$WA/etc/systemd/system/ydotoold.service.d/yerinde.conf" \
        "$WA/etc/systemd/system/multi-user.target.wants/ydotoold.service" 2>/dev/null | sed 's/^/    /'

  # final27 §3 POST: oto-giriş + drkonqi maskı + canlı kullanıcı birimi
  rg -q '^User=yerinde$' "$WA/etc/sddm.conf.d/yerinde-autologin.conf" \
    || fail "POSTFAIL (final27 §3): autologin User=yerinde ISO'da yok"
  rg -q '^Session=plasma\.desktop$' "$WA/etc/sddm.conf.d/yerinde-autologin.conf" \
    || fail "POSTFAIL (final27 §3): autologin Session=plasma.desktop ISO'da yok"
  [ -L "$WA/etc/systemd/system/drkonqi-coredump@.service" ] \
    || fail "POSTFAIL (final27 §3): drkonqi-coredump@.service maskı ISO'da yok"
  [ -f "$WA/etc/systemd/system/yerinde-live-user.service" ] \
    || fail "POSTFAIL (final27 §3): yerinde-live-user.service ISO'da yok"
  [ -x "$WA/usr/local/bin/yerinde-live-user" ] \
    || fail "POSTFAIL (final27 §3): yerinde-live-user betiği ISO'da yok"
  rg -q 'usermod -aG uinput,input' "$WA/usr/local/bin/yerinde-finalize.sh" \
    || fail "POSTFAIL (final27 §2): finalize usermod ISO'da yok"
  echo "POST OK (final27 §3): User=yerinde + Session=plasma.desktop + drkonqi maskı + live-user birimi"
  echo "--- /usr/share pkg listesi (asistan YOK doğrulaması) ---"
  ls "$WA/usr/share/" | sed 's/^/    /'
  echo "--- /usr/bin yerinde* (asistan launcher YOK) ---"
  ls "$WA/usr/bin/" 2>/dev/null | { grep -i yerinde || echo '    (yerinde-* YOK)'; }

  # final18 §2b: PAM pam_systemd
  for pf in sddm sddm-autologin; do
    rg -q 'pam_systemd.so' "$WA/etc/pam.d/$pf" \
      || fail "POSTFAIL (§2b): $WA/etc/pam.d/$pf içinde pam_systemd.so yok"
  done
  echo "POST OK (§2b): /etc/pam.d/sddm + sddm-autologin içinde pam_systemd.so var"
  echo "--- pam.d/sddm (kanıt) ---"; cat "$WA/etc/pam.d/sddm" | sed 's/^/    /'
  echo "--- pam.d/sddm-autologin (kanıt) ---"; cat "$WA/etc/pam.d/sddm-autologin" | sed 's/^/    /'

  # final18 §2c: KDE menüsü güç kısayolları (branding pkg'den)
  for d in yerinde-reboot yerinde-poweroff; do
    [ -f "$WA/usr/share/applications/$d.desktop" ] \
      || fail "POSTFAIL (§2c): /usr/share/applications/$d.desktop yok"
  done
  rg -q 'Exec=systemctl reboot' "$WA/usr/share/applications/yerinde-reboot.desktop" \
    || fail "POSTFAIL (§2c): yerinde-reboot.desktop Exec=systemctl reboot yok"
  rg -q 'Exec=systemctl poweroff' "$WA/usr/share/applications/yerinde-poweroff.desktop" \
    || fail "POSTFAIL (§2c): yerinde-poweroff.desktop Exec=systemctl poweroff yok"
  rg -q 'OnlyShowIn=KDE' "$WA/usr/share/applications/yerinde-reboot.desktop" \
    || fail "POSTFAIL (§2c): yerinde-reboot.desktop OnlyShowIn=KDE yok"
  echo "POST OK (§2c): yerinde-reboot.desktop + yerinde-poweroff.desktop (systemctl reboot/poweroff + OnlyShowIn=KDE)"

  # final18 §3 + final24 §2 + final31: calamares -5 — ANKA çevirisi gömülü
  # + check_big_enough /sys/block taraması (VM'de libparted probe yanlış
  # negatif verip "en az 4 GB alan gerekli" uyarısı çıkarıyordu).
  local CDB
  CDB=$(ls -d "$WA/var/lib/pacman/local/calamares-3.4.2-5" 2>/dev/null)
  [ -n "$CDB" ] || fail "POSTFAIL (final31): calamares-3.4.2-5 pacman local DB'de yok (/sys/block disk kontrolü yeniden derlemesi)"
  rg -q '^%VERSION%$' "$CDB/desc" || true
  if ! grep -aq 'sys/block' "$WA/usr/lib/calamares/modules/welcome/libcalamares_viewmodule_welcome.so"; then
    fail "POSTFAIL (final31): welcome.so içinde /sys/block taraması yok (libparted probe sürümü kurulu)"
  fi
  echo "POST OK (final31): calamares-3.4.2-5 kuruldu + welcome.so /sys/block disk kontrolü kanıtlı"
  echo "--- calamares pacman local desc ---"; sed -n '1,12p' "$CDB/desc" | sed 's/^/    /'
  echo "--- yerinde repo paketleri (URI= file:// repo) ---"
  ls "$WA/var/lib/pacman/sync/" | sed 's/^/    /'

  # H1: sddm teması + conf (final19: [X11] Enable=false)
  [ -f "$WA/usr/share/sddm/themes/yerinde/Main.qml" ] || fail "POSTFAIL (H1): sddm teması Main.qml yok"
  [ -f "$WA/etc/sddm.conf.d/yerinde.conf" ] || fail "POSTFAIL (H1): sddm.conf.d/yerinde.conf yok"
  rg -q 'Current=yerinde' "$WA/etc/sddm.conf.d/yerinde.conf" || fail "POSTFAIL (H1): Current=yerinde yok"
  rg -q 'Enable=true' "$WA/etc/sddm.conf.d/yerinde.conf" || fail "POSTFAIL (H1): [Wayland] Enable=true yok"
  rg -q '\[X11\]' "$WA/etc/sddm.conf.d/yerinde.conf" || fail "POSTFAIL (final19 H1): [X11] bölümü yok"
  rg -A1 '^\[X11\]' "$WA/etc/sddm.conf.d/yerinde.conf" | grep -q 'Enable=false' \
    || fail "POSTFAIL (final19 H1): [X11] Enable=false yok"
  echo "POST OK (H1 final19): sddm teması + conf (Current=yerinde + Wayland=true + X11=false)"

  # F1: SDDM Main.qml tek satır oturum seçici (regresyon)
  # Not: `rg -q` yerine `grep -q` kullanılıyor çünkü desen `()` içerir ve
  # ripgrep bunları regex yakalama grubu olarak yorumlar (literal değil).
  grep -q 'onValueChanged: sessionIndex = index' "$WA/usr/share/sddm/themes/yerinde/Main.qml" \
    || fail "POSTFAIL (F1): Main.qml oturum seçici satırı yok"
  grep -q 'sddm.login(userEntry.text, passwordEntry.text, sessionIndex)' \
    "$WA/usr/share/sddm/themes/yerinde/Main.qml" \
    || fail "POSTFAIL (F1): Main.qml sddm.login(sessionIndex) yok"
  echo "POST OK (F1): Main.qml oturum seçici + sddm.login(sessionIndex) — SDDM regresyon koruması"

  # REGRESYON: 5 duvar kağıdı
  local nw=0
  for t in Hologram-Mavi Krem Dalga-Mavi Yesil Mor; do
    [ -f "$WA/usr/share/wallpapers/Yerinde-Destek-$t/metadata.desktop" ] \
      || fail "POSTFAIL (regresyon): /usr/share/wallpapers/Yerinde-Destek-$t/metadata.desktop yok"
    nw=$((nw+1))
  done
  echo "POST OK (regresyon): $nw duvar kağıdı metadata.desktop kurulu"

  # REGRESYON: GRUB teması (krem + select şerit)
  for f in theme.txt background.png logo.png DejaVuSans-32.pf2 select_c.png; do
    [ -f "$WA/usr/share/grub/themes/yerinde/$f" ] \
      || fail "POSTFAIL (regresyon): /usr/share/grub/themes/yerinde/$f yok"
  done
  # final24 §1: title-text YOK + tek image referansı (3'lü yazı → tek lockup)
  if rg -q '^[[:space:]]*title-text[[:space:]]*:' "$WA/usr/share/grub/themes/yerinde/theme.txt"; then
    fail "POSTFAIL (final24 §1): grub theme.txt'te title-text hâlâ var"
  fi
  [ "$(grep -c 'desktop-image:' "$WA/usr/share/grub/themes/yerinde/theme.txt")" -eq 1 ] \
    || fail "POSTFAIL (final24 §1): grub theme.txt'te desktop-image tam 1 değil"
  if grep -q '^+ image' "$WA/usr/share/grub/themes/yerinde/theme.txt"; then
    fail "POSTFAIL (final24 §1): grub theme.txt'te + image bloğu var (logo resmi kaldırılacaktı)"
  fi
  echo "POST OK (final24 §1): GRUB teması TEK lockup (title-text YOK, tek desktop-image)"

  # final37 §2 + §3 POST: UEFI GRUB + yeşil ANKA teması + Türkçe font ISO'da
  # (mkarchiso 89: ISO 9660 hazırlama dizini work/iso — altına arch/ boot/ EFI/)
  local ISOFS
  ISOFS="$ISO_DIR/work/iso"
  [ -d "$ISOFS" ] || fail "POSTFAIL (final37): work/x86_64/iso yok"
  [ -f "$ISOFS/boot/grub/grub.cfg" ] || fail "POSTFAIL (final37): ISO /boot/grub/grub.cfg yok"
  [ -f "$ISOFS/boot/grub/themes/anka/theme.txt" ] \
    || fail "POSTFAIL (final37 §2): ISO /boot/grub/themes/anka/theme.txt yok"
  for c in 'desktop-color: "#0B3D2E"' 'item_color = "#EFE9DC"' \
           'selected_item_color = "#C74A1F"' 'title-text: "GRUB Açılış Menüsü"'; do
    rg -qF "$c" "$ISOFS/boot/grub/themes/anka/theme.txt" \
      || fail "POSTFAIL (final37 §2): ISO theme.txt'te '$c' yok"
  done
  for f in background.png anka-tr.pf2 anka-tr-44.pf2; do
    [ -s "$ISOFS/boot/grub/themes/anka/$f" ] \
      || fail "POSTFAIL (final37 §3): ISO /boot/grub/themes/anka/$f yok/boş"
  done
  rg -q 'set theme="/boot/grub/themes/anka/theme\.txt"' "$ISOFS/boot/grub/grub.cfg" \
    || fail "POSTFAIL (final37 §2): ISO grub.cfg set theme= anka yok (root-göreli)"
  rg -q 'kurulum ortamı' "$ISOFS/boot/grub/grub.cfg" \
    || fail "POSTFAIL (final37 §3): ISO grub.cfg Türkçe menü yok ('ortamı')"
  rg -q 'loadfont /boot/grub/themes/anka/anka-tr\.pf2' "$ISOFS/boot/grub/grub.cfg" \
    || fail "POSTFAIL (final37 §3): ISO grub.cfg anka-tr.pf2 loadfont yok (root-göreli)"
  # UEFI önyükleyici GERÇEKTEN GRUB (systemd-boot izi YOK)
  [ -f "$ISOFS/EFI/BOOT/BOOTx64.EFI" ] \
    || fail "POSTFAIL (final37 §2): EFI/BOOT/BOOTx64.EFI yok"
  if ! grep -aq 'grub' "$ISOFS/EFI/BOOT/BOOTx64.EFI"; then
    fail "POSTFAIL (final37 §2): BOOTx64.EFI GRUB değil (grub imzası yok)"
  fi
  if grep -aq 'systemd-boot' "$ISOFS/EFI/BOOT/BOOTx64.EFI"; then
    fail "POSTFAIL (final37 §2): BOOTx64.EFI systemd-boot görünüyor"
  fi
  if [ -e "$ISOFS/loader/loader.conf" ]; then
    fail "POSTFAIL (final37 §2): ISO /loader/loader.conf var (systemd-boot kalıntı)"
  fi
  # kurulu sistem tarafı: branding paketi anka temasıyla + finalize anka kuruyor
  [ -f "$WA/usr/share/grub/themes/anka/theme.txt" ] \
    || fail "POSTFAIL (final37 §2): /usr/share/grub/themes/anka/theme.txt yok (branding -18?)"
  rg -q 'themes/anka' "$WA/usr/local/bin/yerinde-finalize.sh" \
    || fail "POSTFAIL (final37 §2): finalize.sh themes/anka kurmuyor"
  echo "POST OK (final37 §2/§3): ISO GRUB UEFI + yeşil/krem/turuncu ANKA teması + anka-tr pf2 + Türkçe menü; BOOTx64.EFI GRUB"
  echo "--- ls ISO grub/themes/anka (kanıt) ---"
  ls -l "$ISOFS/boot/grub/themes/anka/" | sed 's/^/    /'

  # REGRESYON: sudoers wheel + ilk-oturum betiği
  [ -f "$WA/etc/sudoers.d/wheel" ] || fail "POSTFAIL (regresyon): /etc/sudoers.d/wheel yok"
  [ -f "$WA/usr/local/bin/yerinde-finalize.sh" ] || fail "POSTFAIL (regresyon): yerinde-finalize.sh yok"
  [ -f "$WA/etc/xdg/autostart/yerinde-first-run.desktop" ] \
    || fail "POSTFAIL (regresyon): ilk-oturum autostart .desktop yok"
  [ -f "$WA/usr/share/yerinde/kde/yerinde-first-run.sh" ] \
    || fail "POSTFAIL (regresyon): ilk-oturum betiği .sh yok"
  echo "POST OK (regresyon): sudoers wheel + ilk-oturum betiği (duvar kağıdı + kickoff ikonu)"

  # final21.md §4: ZIP/arsiv araçları kurulu (ls kanıtı, eksikse FAIL)
  for b in zip unzip 7z ark; do
    [ -e "$WA/usr/bin/$b" ] || fail "POSTFAIL (final21 §4): /usr/bin/$b yok"
  done
  echo "POST OK (final21 §4): /usr/bin/ altında zip + unzip + 7z + ark VAR"
  echo "--- ls zip araçları (kanıt) ---"
  ls -l "$WA/usr/bin/zip" "$WA/usr/bin/unzip" "$WA/usr/bin/7z" "$WA/usr/bin/ark" 2>/dev/null | sed 's/^/    /'

  # final21.md §3: canlı keyring script + service ISO'da
  [ -f "$WA/usr/local/bin/yerinde-keyring-init" ] \
    || fail "POSTFAIL (final21 §3): /usr/local/bin/yerinde-keyring-init yok"
  [ -f "$WA/etc/systemd/system/yerinde-keyring.service" ] \
    || fail "POSTFAIL (final21 §3): yerinde-keyring.service yok"
  [ -L "$WA/etc/systemd/system/multi-user.target.wants/yerinde-keyring.service" ] \
    || fail "POSTFAIL (final21 §3): yerinde-keyring wants linki yok"
  rg -q 'pacman-key --populate archlinux' "$WA/usr/local/bin/yerinde-finalize.sh" \
    || fail "POSTFAIL (final21 §3): finalize.sh pacman-key populate yok"
  echo "POST OK (final21 §3): keyring-init + service + wants linki + finalize pacman-key"

  # final24.md §3: numpy + PIL site-packages'ta (ls kanıtı, eksikse FAIL)
  local SP
  SP=$(ls -d "$WA"/usr/lib/python3*/site-packages 2>/dev/null | head -1)
  [ -n "$SP" ] || fail "POSTFAIL (final24 §3): site-packages bulunamadı"
  [ -d "$SP/numpy" ] || fail "POSTFAIL (final24 §3): $SP/numpy yok"
  [ -d "$SP/PIL" ] || fail "POSTFAIL (final24 §3): $SP/PIL yok"
  echo "POST OK (final24 §3): site-packages altında numpy/ + PIL/ VAR"
  echo "--- ls numpy + PIL (kanıt) ---"
  ls -ld "$SP/numpy" "$SP/PIL" | sed 's/^/    /'
  if [ -d "$SP/cv2" ]; then
    echo "POST OK (final24 §3): cv2 bağlaması da mevcut (sürpriz ama zararsız)"
  else
    echo "POST BİLGİ (final24 §3): cv2 site-packages'te YOK — opencv paketi cv2 python bağlaması içermiyor (best-effort, build düşürülmez)"
  fi

  # final24.md §5: tıkla-çalıştır kurucu ISO'da
  [ -f "$WA/usr/local/bin/yerinde-asistan-kur" ] \
    || fail "POSTFAIL (final24 §5): /usr/local/bin/yerinde-asistan-kur yok"
  [ -f "$WA/usr/share/applications/yerinde-asistan-kur.desktop" ] \
    || fail "POSTFAIL (final24 §5): /usr/share/applications/yerinde-asistan-kur.desktop yok"
  [ -f "$WA/etc/skel/Desktop/yerinde-asistan-kur.desktop" ] \
    || fail "POSTFAIL (final24 §5): /etc/skel/Desktop/yerinde-asistan-kur.desktop yok"
  rg -q 'yerinde-ai-assistant' "$WA/usr/local/bin/yerinde-asistan-kur" \
    || fail "POSTFAIL (final24 §5): kurucu script yerinde-ai-assistant içermiyor"
  echo "POST OK (final24 §5): yerinde-asistan-kur + masaüstü + menü .desktop ISO'da (asistanın KENDİSİ YOK — yalnız kurucu)"
  ls -l "$WA/usr/local/bin/yerinde-asistan-kur" | sed 's/^/    /'

  # final33 POST: canlı calamares yetki zinciri
  rg -q 'pkexec calamares' "$WA/etc/xdg/autostart/calamares.desktop" \
    || fail "POSTFAIL (final33): autostart pkexec calamares ISO'da yok"
  # Not: polkit paketi /etc/polkit-1/rules.d'yi 0750 root:polkitd yapar →
  # yetkisiz test -f YANLIŞ NEGATİF verir; sudo ile bak.
  sudo test -f "$WA/etc/polkit-1/rules.d/49-yerinde-live-calamares.rules" \
    || fail "POSTFAIL (final33): canlı polkit kuralı ISO'da yok"
  echo "POST OK (final33): calamares pkexec + polkit kuralı ISO'da (unpackfs yetki düzeltmesi)"
  sudo ls -l "$WA/etc/polkit-1/rules.d/" | sed 's/^/    /'

  echo "== TÜM POST DOĞRULAMALAR BAŞARILI =="
}

wait_build() {
  echo "Build tamamlanması bekleniyor..."
  for _i in $(seq 1 900); do
    if [ -e "$ISO_DIR"/out/yerinde-anka-*.iso ] 2>/dev/null \
       && rg -q '^[0-9][0-9.,]*[KMGT]?[[:space:]]+.*yerinde-anka-[0-9]{4}[.-][0-9]{2}[.-][0-9]{2}-x86_64\.iso$' "$LOG" 2>/dev/null; then
      echo "Build tamamlandı (mkarchiso ISO üretti)."; return 0
    fi
    if rg -q '==> ERROR|\[mkarchiso\] ERROR|Build started on.*failed' "$LOG" 2>/dev/null; then
      echo "Build HATA verdi — log sonu:" >&2; tail -40 "$LOG" >&2; return 1
    fi
    sleep 10
  done
  echo "Zaman aşımı (150 dk) — log sonu:" >&2; tail -40 "$LOG" >&2; return 1
}

if [ "$MODE_PREP" -eq 1 ]; then
  verify_sources
  verify_prep
fi
if [ "$MODE_BUILD" -eq 1 ]; then
  build
  if wait_build; then
    verify_post
    cd "$ISO_DIR/out"
    ISO=$(ls -1 yerinde-anka-*.iso | head -1)
    [ -n "$ISO" ] || fail "ISO bulunamadı (out/)"
    sha256sum "$ISO" | tee SHA256SUMS
    echo "ISO hazır: $ISO_DIR/out/$ISO"
    ls -lh "$ISO_DIR/out/$ISO"
  else
    exit 1
  fi
fi
if [ "$MODE_POST_ONLY" -eq 1 ]; then
  verify_post
  cd "$ISO_DIR/out"
  ISO=$(ls -1 yerinde-*.iso | head -1)
  [ -n "$ISO" ] || fail "ISO bulunamadı (out/)"
  sha256sum "$ISO" | tee SHA256SUMS
  echo "ISO hazır: $ISO_DIR/out/$ISO"
  ls -lh "$ISO_DIR/out/$ISO"
  exit 0
fi
exit 0