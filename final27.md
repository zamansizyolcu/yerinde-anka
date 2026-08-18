# YERINDE ANKA final30 — TEK MASTER PROMPT
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## §1 BAZ KAYNAK SABİTLE
SRC=/home/yerinde/yerinde-project/yerinde-ai-assistant
(kullanıcının proje içine kopyaladığı BAZ; ~/yerinde-ai-assistant
ve İndirilenler kopyaları KULLANILMAZ)
ls kanıtı: kurulum.sh + actions/keyboard_control.py +
actions/mouse_control.py VAR
PKGBUILD (final26 şablonu v2.0.0) bu SRC'yi kullanır.

## §2 ASİSTAN ÇALIŞMA ZAMANLARI (cacyhos PARİTESİ)
packages.x86_64 += ydotool git python-pyaudio portaudio xdotool
- sysusers: group uinput
- udev: 80-uinput.rules (KERNEL=="uinput", GROUP="uinput", MODE="0660")
- ydotoold drop-in: /run/ydotool.socket 0660 group uinput + wants linki
- modules-load: uinput
- finalize: usermod -aG uinput,input "$NEW_USER" (idempotent)
DOĞRULA: airootfs ls; eksikse FAIL.

## §3 SDDM OTO-GİRİŞ + DRKONQI
- etc/sddm.conf.d/yerinde.conf: [Autologin] User=yerinde
  Session=plasma.desktop (wayland-sessions/plasma.desktop ls kanıtı)
- grep: xsessions referansı SIFIR
- mask linki: drkonqi-coredump@.service (popup söner)
- sddm --test-mode log temiz

## §4 ISO DERLEME (AYRI BAŞLIK — ATLANMAZ)
1) branding pkgrel bump + makepkg + repo-add
2) cd iso/yerinde && setsid bash -c './build-iso.sh >
   /tmp/opencode/final30-iso.log 2>&1' &
3) poll: "INFO: Done!" + out/yerinde-anka-*.iso + sha256
4) raporda: ISO boyutu + sha256 + log sonu

## §5 PUSH — İKİ REPO (doğrulamalı)
A) ASİSTAN:
   cd $SRC
   git init -b main (yoksa); .gitignore: vosk-model/ *.gguf
   venv/ __pycache__/ *.pyc
   commit (final28 pyaudio/venv düzeltmeleri dahil)
   remote add origin https://github.com/zamansizyolcu/yerinde-ai-assistant.git
   push -u origin main  (KULLANICI İZNİ: BAZ kopya halka geçer)
B) OS KAYNAKLARI:
   cd /home/yerinde/yerinde-project
   A BİTTİKTEN SONRA: rm -rf yerinde-ai-assistant/.git
   (embedded-repo uyarısı olmasın; dosyalar OS reposuna girer)
   .gitignore: work/ out/ *.iso repo/x86_64/*.pkg.tar.zst
   find . -size +90M → BOŞ olmalı (doluysa ignore'a ekle)
   git init -b main + commit
   remote add origin https://github.com/zamansizyolcu/yerinde-anka.git
   push -u origin main
   (KULLANICI boş "yerinde-anka" reposu açmalı; açılmadıysa
   raporda komutları yaz)
C) DOĞRULA: her iki repo için git ls-remote origin +
   curl GitHub sayfası 200
NOT: *.iso GitHub'a GİREMEZ (100MB limit) → ISO binary dağıtımı
LAN (python -m http.server) / USB; README'ye yaz.

## §6 REGRESYON + TEST LİSTESİ
Wayland-tek; SDDM krem+Enter+⟳⏻; ANKA markası; keyring; zip;
NOESCAPE; duvar kağıtları; sudoers wheel; asistan paketi ISO'da YOK.
Testler:
1) echo $XDG_SESSION_TYPE → wayland
2) oto-giriş şifresiz açar
3) şifreli girişte drkonqi popup YOK
4) tıkla-kur, İndirilenler boşken git clone ile kurar
5) sesli "fareyi sağa oynat" / "ctrl+t yaz" → cacyhos gibi
6) UEFI+MBR regresyonu YOK