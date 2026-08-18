# YERINDE ANKA final30 RAPOR

Tarih: 2026.08.18
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe rapor.

## §1 BAZ KAYNAK SABİTLENDİ

- Kullanıcı kopyası `~⁄yerinde-ai-assistant` (bozuk ad) →
  **SRC=/home/yerinde/yerinde-project/yerinde-ai-assistant** olarak taşındı.
- ls kanıtı: `kurulum.sh` (6363 B) + `actions/keyboard_control.py` (12850 B)
  + `actions/mouse_control.py` (14566 B) VAR ✓
- ~/yerinde-repo/yerinde-ai-assistant/PKGBUILD (final26 şablonu v2.0.0):
  `SRC=/home/yerinde/yerinde-project/yerinde-ai-assistant` yapıldı
  (ev/İndirilenler kopyaları artık KULLANILMAZ).

## §2 ASİSTAN ÇALIŞMA ZAMANLARI (cacyhos PARİTESİ)

- packages.x86_64 += **ydotool git** (pyaudio/portaudio/xdotool zaten vardı)
- sysusers: `etc/sysusers.d/yerinde-uinput.conf` (`g uinput -`)
- udev: `etc/udev/rules.d/80-uinput.rules`
  (`KERNEL=="uinput", GROUP="uinput", MODE="0660"`)
- ydotoold drop-in: `etc/systemd/system/ydotoold.service.d/yerinde.conf`
  (Group=uinput + `--socket-path=/run/ydotool.socket --socket-perm=0660`)
  + `multi-user.target.wants/ydotoold.service` linki
- modules-load: `etc/modules-load.d/uinput.conf` (uinput)
- finalize: `NEW_USER` (uid>=1000) tespiti + `usermod -aG uinput,input`
  (idempotent; kanıt /tmp/finalize.log'a yazılır)
- DOĞRULA: airootfs ls kanıtı build-iso.sh'de pozitif kontrol olarak
  kodlandı; prep çalıştı: `UINPUT OK (final27 §2)` ✓ — eksik olsa FAIL.

## §3 SDDM OTO-GİRİŞ + DRKONQI

- `etc/sddm.conf.d/yerinde-autologin.conf`: **User=yerinde,
  Session=plasma.desktop** (wayland-sessions/plasma.desktop ls kanıtı POST'ta)
- **TASARIM KARARI**: "yerinde" canlı kullanıcısı passwd'e BAKED DEĞİL;
  açılışta `yerinde-live-user.service` oluşturur
  (ConditionPathExists=/run/archiso + Before=display-manager.service;
  useradd -m -p '' + wheel,uinput,input,... grupları). Neden: baked satır
  Calamares'te "yerinde" ad çakışması yapardı (kurulum hatası).
  finalize kurulu sistemden birimi/betiği temizler.
- Baked `live` kullanıcısı passwd/shadow/group/gshadow'dan tamamen
  silindi (grep 'live' → 0).
- Mask linki: `etc/systemd/system/drkonqi-coredump@.service → /dev/null`
- grep: yapılandırmalarda xsessions referansı SIFIR ✓
- sddm-greeter --test-mode log temiz ✓ (`SDDM GREETER OK`)

## §4 ISO DERLEME

- yerinde-branding pkgrel 16→**17**; makepkg OK; repo-add OK
  (db: calamares-3.4.2-4 + yerinde-ai-assistant-2.0.0-1 + branding-17)
- geo ayna kilitlenmesi ("Operation too slow") → pacman.conf'a
  mirror.rackspace.com birincil eklendi; yeniden derleme başarılı
- setsid + log: /tmp/opencode/final30-iso.log (+ mkarchiso:
  /tmp/opencode/yerinde-iso-build.log — `[mkarchiso] INFO: Done!` ✓)
- **out/yerinde-anka-2026.08.18-x86_64.iso — 2,7G**
- **SHA256: b45cada76204fdaa2d113a7f09bb93bba3477c5f3245a67ff41fbee51affb8fc**
  (out/SHA256SUMS yazıldı)
- `== TÜM POST DOĞRULAMALAR BAŞARILI ==` (445. satır) — final27 §2/§3
  POST kanıtları dahil (uinput/ydotoold zinciri ls kanıtı, autologin,
  drkonqi maskı, /usr/bin/{ydotool,ydotoold,git})

## §5 PUSH — İKİ REPO

### A) ASİSTAN → zamansizyolcu/yerinde-ai-assistant

- Remote'ta final28 düzeltmeleri (v2.1: eaf5554+7251713) zaten vardı;
  proje kopyası eski (v2.0) ve **commit'inde kişisel API anahtarı**
  tespit edildi → o geçmiş ASLA push EDİLMEDİ.
- Temiz senkron: HEAD = remote v2.1 (final28 pyaudio/venv/ydotool
  dahil) + `model-egitimi/egitim_verisi.jsonl` (50 satır) eklendi.
- Kişisel/büyük dosyalar diskte kaldı, izlenmiyor (remote .gitignore:
  config/api_keys.json, memory/memory.json, voices/*.onnx(+json),
  yolo11n.pt, vosk-model/, *.gguf, venv/ ✓ prompt listesi tam kapsam)
- **e8332f6** push: `7251713..e8332f6 main -> main` ✓ (FF)

### B) OS KAYNAKLARI → zamansizyolcu/yerinde-anka

- A bittikten sonra `rm -rf yerinde-ai-assistant/.git` (embedded-repo
  uyarısı önlendi) + `rm -rf repo/x86_64/.git` (lokal deneme kalıntısı)
- .gitignore: work/ out/ *.iso repo/x86_64/*.pkg.tar.zst *.gguf
  .ollama-staging./ key.txt __pycache__/ *.pyc venv/
- find -size +90M → yalnızca ignore kapsamındakiler (ikinci filtreli
  find BOŞ) ✓
- README.md oluşturuldu: ISO dağıtımı (LAN http.server / USB) + SHA256
  + asistan kurulum yolları (*.iso GitHub'a GİREMEZ notu ile)
- **a138785** push: `* [new branch] main -> main` ✓

### C) DOĞRULA

- yerinde-ai-assistant: ls-remote main = e8332f6 + sayfa **200** ✓
- yerinde-anka: ls-remote main = a138785 + sayfa **200** ✓

## §6 REGRESYON (POST kanıtlı) + KULLANICI TEST LİSTESİ

Regresyon: Wayland-tek (xsessions boş + [X11] false) ✓; SDDM krem tema
+ Enter + ⟳⏻ kısayolları ✓; ANKA markası (eski ad SIFIR) ✓; keyring
doğumda ✓; zip araçları ✓; NOESCAPE+TABMSG gizli ✓; 5 duvar kağıdı ✓;
sudoers wheel ✓; **asistan paketi ISO'da YOK** (yalnız kurucu) ✓.

VM'de manuel testler:
1. `echo $XDG_SESSION_TYPE` → wayland
2. Oto-giriş şifresiz açar (canlıda "yerinde" oturumu)
3. Şifreli girişte drkonqi popup YOK (maskı kurulu sistemde de sürer)
4. Tıkla-kur, İndirilenler boşken git clone ile kurar (git artık ISO'da)
5. "fareyi sağa oynat" / "ctrl+t yaz" → cacyhos gibi (ydotoold 0660
   uinput; kurulumda kullanıcı otomatik uinput,input grubunda)
6. UEFI+MBR kurulum regresyonu YOK

## UYARILAR / NOTLAR

- **key.txt** düz metin API anahtarları içeriyor (AQ…/sk-…). Repoya
  GİRMEDİ (.gitignore) — anahtarları döndürmeniz önerilir.
- Asistan reposunun GEÇMİŞİ temiz (anahtar yalnız push edilmemiş
  lokal 6b830ca'daydı; o commit erişilmez bırakıldı).
- repo/x86_64'teki asistan paketleri LAN dağıtımı için yerelde kalır
  (OS reposuna yalnız db girer).
