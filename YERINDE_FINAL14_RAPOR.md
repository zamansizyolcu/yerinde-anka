# YERINDE OS — FINAL14 RAPORU

**Sürüm:** v1.4 (final14.md'nin 6 bölümü — H1-H5 düzeltme turu)
**Tarih:** 2026-08-16
**Kapsam:** SDDM QML hatası (H1), X11 çift oturum (H2), asistan canlı mod + Gemini öncelik (H3), ydotool/uinput + yerel piper sesleri (H4+H5), paket + ISO rebuild, Türkçe rapor.

---

## 1. Yapılan Değişiklikler (bölüm bölüm)

### §1 — SDDM QML düzeltmesi (H1)
- `airootfs/usr/share/sddm/themes/yerinde/Main.qml` yenilendi:
  - `onActivated` SADECE ComboBox (oturum seçici) üzerinde kalabilir; buradaki ComboBox
    `onValueChanged: session.index = index` kullanır (SddmComponents ComboBox yalnızca
    `valueChanged` sunar — `onActivated` zaten yoktu).
  - Parola ve kullanıcı adı alanlarında `onAccepted` / `Keys.onReturnPressed` /
    `Keys.onEnterPressed` → `loginButton.onClicked()` (satır 82-83, 92-93).
  - Parola alanı `focus: true` + `Component.onCompleted: forceActiveFocus()` (v1.3 kuralı korundu).
  - `sddm.login(userEntry.text, passwordEntry.text, sessionIndex)` butonu `onClicked` ile.
- `/etc/sddm.conf.d/yerinde.conf` (yerinde-branding paketi): `[Theme] Current=yerinde`,
  `[Wayland] Enable=true`, `[X11] Enable=true`.
- **Build-zamanı doğrulama (VM'siz):**
  - Statik kontrol: `Main.qml` içinde `onActivated` satırı YOK (grep FAIL-kontrollü),
    `onValueChanged` VAR.
  - `sddm-greeter --test-mode` (offscreen, timeout 15): `/tmp/opencode/sddm-test.log` TEMİZ
    (Cannot assign / is not a type / QML Error / ReferenceError YOK) → H1 GREETER OK.

### §2 — X11 + çift oturum (H2)
- `packages.x86_64` += `xorg-server xorg-xinit xorg-xrandr` (zaten vardı), `xorg-xwayland`.
- `/usr/share/xsessions/plasma.desktop` yerinde-branding paketine eklendi:
  `Name=Plasma (X11)`, `Exec=startplasma-x11`, `TryExec=startplasma-x11`,
  `Type=Application`, `DesktopNames=KDE`.
- **ls ile doğrulandı (work airootfs / sfs):**
  - `usr/share/xsessions/plasma.desktop` ✓
  - `usr/share/wayland-sessions/plasma.desktop` ✓
  - `usr/bin/Xorg` ✓ ve `usr/bin/startplasma-x11` ✓
  - SFS içinde de aynı 4 dosya doğrulandı (unsquashfs -l).

### §3 — Asistan: canlı mod + Gemini öncelik (H3)
- `main.py`: `MOD_VARSAYILAN = "gemini"` (satır 258). Config/API anahtarı yoksa başlangıçta
  Gemini API anahtar ekranı gösterilir — çökme YOK. Ollama yalnızca menüden seçilince.
- Gevşek importlar: `pyaudio` ve `google.genai` try/except; eksik olsa bile PENCERE AÇILIR,
  özellik pas geçer (main.py satır 19-29). `sounddevice`/`piper`/`faster_whisper` vendor'a gömülü;
  xdotool/ydotool sarmalayıcıları `actions/` içinde subprocess tabanlı (import gerektirmez).
- `/usr/bin/yerinde` launcher: `~/.yerinde/app` yoksa `/usr/share/yerinde-ai/app`'ten kopyalar,
  `chmod +x main.py run.sh`, sonra `exec ~/.yerinde/app/run.sh` (ev-kopyası mantığı korundu).
- `run.sh`: `cd "$(dirname "$0")"`, `PYTHONPATH="$PWD/vendor"`, `mkdir -p ~/.yerinde`,
  `exec python3 main.py "$@" 2>>~/.yerinde/ai.log`.
- Canlı mod: `airootfs/etc/xdg/autostart` içinde yerinde-live.desktop YOK (yalnızca calamares);
  root evinde config YOK → menüden tıklayınca Gemini API anahtar ekranı gelir (regresyon korundu).
- **Smoke test:** `python3 -m py_compile main.py` OK; paket build'inde
  `PYTHONPATH=vendor python3 -c "import google.genai, ollama, numpy, onnxruntime, ctranslate2; print('IMPORT-OK')"`
  → **IMPORT-OK** görüldü (yerinde-ai-assistant 1.2.0-4 build logu).

### §4 — ydotool/uinput + ses dosyaları (H4+H5)
- `/etc/modules-load.d/uinput.conf` → `uinput` (yerinde-branding paketi; canlı + kurulu).
- udev `80-uinput.rules`: `KERNEL=="uinput", MODE="0660", GROUP="uinput"`.
- sysusers: `g uinput 790`. Canlı `airootfs/etc/group`: `live` → `uinput` (790), `input` (992), `wheel` (998).
- Kurulu sistemde `yerinde-finalize.sh` H4b: `usermod -aG uinput,input $NEW_USER`.
- `ydotool.service.d/yerinde-ydotool.conf` drop-in:
  `ExecStart=/usr/bin/ydotoold --socket-path=/run/ydotool.socket --socket-perm=0660 --socket-own=root:input`
  + `multi-user.target.wants/ydotool.service` linki + finalize `systemctl enable ydotool`.
- `actions/keyboard_control.py` / `mouse_control.py`: Wayland'de ydotool, X11'de xdotool;
  hata mesajı Türkçe: **"ydotool/uinput hazır değil (modül/servis kontrol)"** (satır 224-229,
  mouse_control.py 67-72).
- **Ses dosyaları (H5):** kaynak `/home/yerinde/yerinde-ai-assistant/voices/` İNDİRİLMEZ —
  sadece kopyalanır. `tr_TR-{dfki,fahrettin,fettah}-medium.onnx` + `.onnx.json` (6 dosya)
  → paket `app/voices/` + `airootfs` symlink `/usr/share/yerinde-ai/voices → app/voices`.
  ls ile **3 .onnx + 3 .onnx.json** doğrulandı (kaynak boş değildi → rhasspy indirilmedi).
- Ollama GGUF + store + `yerinde-ollama-setup` v1.3'ten AYNEN (regresyon yok).

### §5 — Paket + build
- `yerinde-branding` **1.2.0-9** (XSESSION + SDDM CONF + UINPUT build doğrulamaları eklendi).
- `yerinde-ai-assistant` **1.2.0-4** (MOD_VARSAYILAN=gemini, gevşek import, run.sh, yerel sesler,
  VOICES/SMOKE doğrulamaları).
- makepkg (zstd), repo-add (hem `/home/yerinde/yerinde-repo/x86_64` hem
  `/home/yerinde/yerinde-project/repo/x86_64` pacman `file://` repoları).
- git commit: `ca4eeef` (push YOK).
- ISO rebuild: `./build-iso.sh --skip-prep` (prep yani GGUF+store önceki oturumda yapılmış ve
  doğrulanmıştı), setsid + log (`/tmp/opencode/yerinde-iso-build.log`).
- **Build sonrası doğrulama (verify_post) TAMAMI GEÇTİ:**
  - H2: xsessions/wayland-sessions/plasma.desktop + Xorg + startplasma-x11 ✓
  - H4: modules-load uinput.conf + ydotool.service + drop-in + wants linki ✓
  - H5: app/voices *.onnx + *.onnx.json + voices symlink ✓
  - H1: Main.qml + sddm.conf.d/yerinde.conf (Current=yerinde) ✓
  - H3: /usr/share/yerinde-ai/app/main.py + /usr/bin/yerinde ✓
  - SFS içi (unsquashfs): GGUF'lar (llama 6,6GB + qwen 1,6GB), store 9 blob/7,7GB + manifest'ler,
    voices, sddm teması, xsessions, uinput/ydotool ✓
- **ISO:** `out/yerinde-2026.08.16-x86_64.iso` — 19.726.768.128 bayt (~19,7 GB)
- **sha256:** `194bab4788dd64b140cf22555a52ebd149c219300625b4a57393928988776b46` (→ `out/SHA256SUMS`)

---

## 2. Test Listesi (kurulum sonrası — VM testi YAPILMADI, manuel liste)

1. **SDDM (H1):** yerinde teması hatasız yüklenir (kırmızı hata metni YOK); parola alanı odaklı;
   Enter ile giriş çalışır.
2. **Oturum seçici (H2):** hem "Plasma" hem "Plasma (X11)" hem "Plasma (Wayland)" görünür.
3. **Canlı mod (H3):** girişte hiçbir şey otomatik açılmaz; menüden "YERINDE AI Asistan"
   tıklayınca **Gemini API anahtar ekranı** gelir (çökme yok).
4. **Wayland (H4):** sesli yanıt çalışır (piper + pyaudio/aplay yedekli); klavye/fare komutları
   ydotool ile çalışır; "ydotool/uinput hazır değil" hatası yalnızca servis/modül gerçekten
   eksikse çıkar.
5. **Ollama:** `ollama list` → `llama3.1` ve `qwen2.5-coder:1.5b` (2 model).
6. **UEFI+MBR kurulum regresyonu:** iki yolda da kurulum başarılı; `/etc/yerinde-bootloader`
   içeriği ile GRUB (temalı) mı systemd-boot fallback mi yazılacağı raporlanır.
   - MBR splash + krem menü + NOESCAPE + Türkçe HELP korundu.
   - UEFI GRUB krem teması + systemd-boot fallback korundu.
7. **Duvar kağıdı seçici:** 5 ton (Hologram-Mavi, Krem, Dalga-Mavi, Yesil, Mor); varsayılan Yesil.
8. **sudo:** wheel grubu `%wheel ALL=(ALL) ALL` (440) — canlıda live üyesi, kurulumda kullanıcı.

---

## 3. Sapmalar / Notlar
- **wait_build düzeltmesi (`build-iso.sh`):** mkarchiso ilk adımda ("Validating options...")
  `[mkarchiso] INFO: Done!` yazdığı için bitiş işaretçisi `Done!` satırına dayanamazdı.
  Artık bitiş, `_build_iso_image`'ın sonundaki `du -h` çıktısı (sayı ile başlayan
  `*.iso` satırı) + ISO dosyasının varlığı ile belirlenir; "Image file name:" yapılandırma
  satırıyla karışmaz. Bu düzeltme bu turda yapıldı; mevcut build öncesi başlatılmıştı ve
  doğrulama manuel tamamlandı.
- Store ve GGUF'lar v1.3'ten aynen (9 blob / 7,7GB; llama + qwen), orphan blob temizliği korundu.
- `google-genai` yine tüm deps ile kuruldu (`--no-deps` import'u kırardı) — regresyon yok.
- `build-iso.sh`/`Main.qml`/`PKGBUILD` kaynakları git'te takip edilmiyor (yalnızca ikili
  paketler + ai-assistant PKGBUILD izlenir) — v1.3 ile aynı.
