# YERINDE ANKA final47 — TEK PROMPT (EK koruma birleşik)
KURALLAR: önce teşhis (traceback/log), sonra düzeltme; grep/ls
doğrulamalı; Türkçe rapor; eksikse FAIL; idempotent (final46
maddeleri uygulandıysa DOĞRULA-geç, yoksa UYGULA).

## §1 ASİSTAN ÇEVRİMDIŞI SES: PIPER + SES LİSTESİ
SORUN: "Piper kurulu değil" → mekanik sistem sesi;
"ERR: 'str' object has no attribute 'get'" (ses listesi).
1) TTS zinciri: a) pip piper (import piper) VEYA proje/piper
   binary → b) sistem piper → c) SON çare sistem TTS
2) voices/*.onnx+.json çiftlerini DOSYA ADINDAN ayrıştır
   (dict.get varsayımı = hatanın kökü → kaldır)
3) UI ses seçici voices/ listesini DOLDURSUN; seçim config'de kalıcı
4) DOĞRULA: py_compile + headless birim test: ses listesi fonksiyonu
   voices/ ile dolu liste döndürür
5) commit + push (asistan repo)

## §2 GÖREV YÖNETİCİSİ: AÇILIR GİBİ YAPIP AÇILMIYOR
1) terminalde çalıştır → stderr/traceback rapora (tahmin YASAK)
2) tüm donanım propları (nvidia-smi, sensors, psutil) try/except;
   eksikse "—"
3) .desktop Exec = /usr/bin/yerinde-gorev-yoneticisi wrapper;
   wrapper doğru python'u çağırsın (system/venv karışmasın)

## §3 WAYDROID: BINDER + SURFACEFLINGER + GERÇEK DONANIM KORUMASI
1) BINDER KEŞİF zinciri (GUI de bunu kullansın):
   a) /dev/binder* VAR → yüklü
   b) /sys/module/binder_linux VAR → built-in → yüklü
   c) modprobe binder_linux
   d) hiçbiri: zgrep ANDROID_BINDER /proc/config.gz →
      "=m ama modül yok" → "linux paketini yenile" önerisi;
      "yok" → Türkçe nazik uyarı: "bu çekirdekte binder yok →
      linux-lts veya gerçek donanım" (çökme değil, uyarı)
2) surfaceflinger/composer ABORT (VM grafği) → software render
   prop'ları (ro.hardware.egl=swiftshader / gralloc=default —
   waydroid 1.x'te geçerli olanı) YALNIZCA
   `systemd-detect-virt` != none (VM) iken uygulanır;
   GERÇEK DONANIMDA varsayılan GL/EGL yolu DOKUNULMAZ
   (grep kanıtı: detect-virt koşul satırı raporda)
   VM'de yine çökerse GUI: "Sanal makinede GPU sınırlıdır;
   gerçek donanımda deneyin"
3) binder zinciri ortam-bazlı: modprobe çalışıyorsa gerçek
   makinede doğrudan yüklenir, prop'a GEREK YOK
4) modules-load'a binder_linux YALNIZCA modül gerçekten varsa

## §4 ISO'YA OBS + LIBREOFFICE (KULLANICI İSTEĞİ)
packages.x86_64 += obs-studio libreoffice-fresh
(boyut etkisi rapora: ISO önce/sonra; USB 8GB yeter)

## §5 REGRESYON (final46 + korumalar)
mağaza modern + Keşfet; waydroid ilerleme barı; tıkla-kur ollama;
plasma-welcome YOK; UEFI yeşil + MBR krem; Türkçe pf2; ydotool
zinciri; ses 24kHz; NVIDIA finalize (modeset) AYNEN; asistanın
KENDİSİ ISO'da YOK.

## §6 DERLEME (ATLANMAZ)
pkgrel bump'lar + makepkg + repo-add
setsid build-iso.sh > /tmp/opencode/final47-iso.log 2>&1 &
poll "INFO: Done!" + sha256
KANIT: pacman -r work/x86_64/airootfs -Q | grep -E "obs-studio|
libreoffice-fresh|discover|magaza|gorev|waydroid" → dolu

## §7 RAPOR + KULLANICI TEST LİSTESİ
1) çevrimdışı ses: Piper Türkçe DOĞAL; seçici dolu; 'str' hatası YOK
2) görev yöneticisi AÇILIR (menü + terminal temiz)
3) waydroid: binder durumu DOĞRU; VM'de nazik uyarı + software
   render; GERÇEK makinede donanım GL (prop sızmaz)
4) menüde OBS + LibreOffice VAR
5) UEFI/MBR + kurulum regresyonu YOK