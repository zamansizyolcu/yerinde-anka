YERINDE OS v1.4 — TEK FİNAL MASTER PROMPT (HATA DÜZELTME TURU)
HEDEF: Bu dosya OpenCode "big pickle" modeline TEK prompt olarak verilecek.
BAĞLAM: v1.3 KISMEN BAŞARILI → MBR splash/menü GÜZEL, UEFI GRUB teması GÜZEL.
BU TURUN HATALARI (kanıt: ekran görüntüsü + kullanıcı testi):
 H1) SDDM: "Main.qml:72:17 Cannot assign to non-existent property 'onActivated'"
     → tema fallback'e düşüyor, kırmızı hata metni görünüyor.
 H2) Oturum seçicide SADECE "Plasma (Wayland)"; X11 kurulu DEĞİL.
 H3) Asistan CANLI modda açılmıyor; açılış modu GEMINI olmalı,
     config yoksa tıklayınca API anahtar ekranı gelmeli (çökme YOK).
 H4) Sesli yanıt + klavye/fare komutları çalışmıyor: "ydotool/uinput sorun" hatası.
 H5) Piper ses dosyaları İNDİRİLMEYECEK; kaynak: /home/yerinde/yerinde-ai-assistant/voices/
KURALLAR: VM testi YAPMA; git push YOK; setsid+log; zstd; Türkçe rapor;
her kopyalama adımı ls ile DOĞRULANIR, eksikse build FAIL.
DOKUNMA (regresyon koruması): MBR splash + krem menü + NOESCAPE + Türkçe HELP,
UEFI GRUB teması + systemd-boot fallback, 5 duvar kağıdı, ollama store + GGUF,
sudoers wheel (440), requiredStorage 40, launcher home-kopyası mantığı.

1) SDDM QML DÜZELTMESİ (H1)
Kaynak: ~/yerinde-project/branding/sddm/yerinde/Main.qml
a) "onActivated" araması yap: SADECE ComboBox (session/layout) üzerinde kalabilir.
   TextField/TextInput (parola) üzerindeki onActivated KALDIR, doğrusu:
     onAccepted: login()
     Keys.onReturnPressed: login()
     Keys.onEnterPressed: login()
   Button üzerindeki varsa onClicked yap.
b) Parola alanı focus: true ile açılacak (v1.3 kuralı aynen).
c) /etc/sddm.conf.d/yerinde.conf (yerinde-branding paketinden):
   [Theme] Current=yerinde
   [Wayland] Enable=true
   [X11] Enable=true
d) BUILD-ZAMANI DOĞRULAMA (VM'siz):
   timeout 15 env QT_QPA_PLATFORM=offscreen \
     sddm-greeter --test-mode --theme <pkg>/usr/share/sddm/themes/yerinde \
     > sddm-test.log 2>&1 || true   (sddm-greeter yoksa: sddm --test-mode)
   grep -E "Cannot assign|is not a type|QML .* Error" sddm-test.log → VARSA FAIL.
   Statik kontrol: TextField bloğu içinde onactivated geçen satır YOK (awk/grep).

2) X11 + ÇİFT OTURUM (H2)
packages += xorg-server xorg-xrandr xorg-xinit
  (HEM airootfs packages.x86_64 HEM kurulu sistem paket listesi)
/usr/share/xsessions/plasma.desktop YOKSA paketle EKLE:
  [Desktop Entry] Name=Plasma (X11) Exec=startplasma-x11
  TryExec=startplasma-x11 Type=Application DesktopNames=KDE
DOĞRULA (ls ile, eksikse FAIL):
  airootfs/usr/share/xsessions → plasma.desktop
  airootfs/usr/share/wayland-sessions → plasma.desktop
  airootfs/usr/bin → Xorg VE startplasma-x11

3) ASİSTAN: CANLI MOD + GEMİNİ ÖNCELİK (H3)
a) main.py: MOD_VARSAYILAN = "gemini". Config/anahtar yoksa BAŞLANGIÇTA
   Gemini API anahtar ekranı göster — çökme YOK. Ollama sadece menüden seçilince.
b) Importları gevşet: pyaudio, sounddevice, piper, faster_whisper, xdotool/ydotool
   sarmalayıcıları try/except; eksik ols bile PENCERE AÇILIR, özellik pas geçer.
c) /usr/bin/yerinde: ~/.yerinde/app yoksa /usr/share/yerinde-ai/app'ten kopyala,
   chmod +x main.py run.sh; sonra exec ~/.yerinde/app/run.sh
   run.sh: cd "$(dirname "$0")"; export PYTHONPATH="$PWD/vendor/site-packages";
   mkdir -p ~/.yerinde; exec python3 main.py "$@" 2>>~/.yerinde/ai.log
d) ilk-oturum betiği v1.3 aynen (home-kopyası + duvar kağıdı Yesil + kickoff icon).
e) BUILD smoke-test (FAIL-kontrollü):
   python3 -m py_compile main.py
   PYTHONPATH=vendor/site-packages python3 -c "import google.genai, ollama, numpy, onnxruntime, ctranslate2; print('IMPORT-OK')"
   → IMPORT-OK görülmezse FAIL. (sounddevice/pyaudio opsiyonel)

4) YDOTOOL/UINPUT + SES DOSYALARI (H4 + H5)
a) /etc/modules-load.d/uinput.conf → "uinput" (branding paketi; canlı+kurulu)
b) udev 80-uinput.rules + sysusers "g uinput 790" (v1.3 aynen)
   airootfs/etc/group: canlı kullanıcıyı uinput,input,wheel gruplarına EKLE.
   Kurulu sistemde finalize: usermod -aG uinput,input "$USER"
c) ydotoold sistem servisi drop-in (yerinde-ydotool.conf):
   [Service] ExecStart=/usr/bin/ydotoold --socket-path=/run/ydotool.socket --socket-perm=0660
   enable: airootfs multi-user.target.wants linki + finalize systemctl enable ydotool
d) main.py araç sırası: WAYLAND_DISPLAY varsa ydotool, yoksa DISPLAY ile xdotool;
   hata mesajı Türkçe: "ydotool/uinput hazır değil (modül/servis kontrol)".
e) SES DOSYALARI: cp /home/yerinde/yerinde-ai-assistant/voices/*.onnx ve *.onnx.json
   → paket voices/ + airootfs/usr/share/yerinde-ai/voices/
   ls ile EN AZ 1 .onnx + 1 .onnx.json DOĞRULA; kaynak boşsa rhasspy indir (v1.3 yedek).
f) Ollama GGUF + store + yerinde-ollama-setup v1.3'ten AYNEN (regresyon YOK).

5) PAKET + BUILD
yerinde-branding + yerinde-ai-assistant pkgrel bump
makepkg (zstd), repo-add, git commit (push YOK)
ISO rebuild: setsid + log; sha256 üret

6) RAPOR + TEST LİSTESİ (Türkçe)
Kanıtlar: sddm-test.log temiz; xsessions/Xorg/startplasma-x11 ls; voices ls; IMPORT-OK.
Kullanıcı testi listesi:
 - SDDM: yerinde teması hatasız yüklenir; parola odaklı; Enter ile giriş
 - Seçicide "Plasma" + "Plasma (Wayland)"
 - Canlı: menüden asistan → Gemini API anahtar ekranı (otomatik açılan YOK)
 - Wayland: sesli yanıt + klavye/fare komutları (ydotool) çalışır
 - ollama list → 2 model
 - UEFI+MBR kurulum regresyonu YOK; raporda GRUB/fallback hangisi yazsın