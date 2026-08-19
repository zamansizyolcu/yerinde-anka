# YERINDE ANKA final46 — TOPLU (final45 + yeni maddeler + DERLEME)
KURALLAR: VM testi YOK; setsid+log; grep/ls doğrulamalı; Türkçe
rapor; eksikse FAIL; ÖNCE teşhis (log/traceback), sonra düzeltme.

## §1 (final45) PLASMA-WELCOME KALDIR
- packages.x86_64'tan çıkar; plasma-meta geliyorsa finalize'da
  chroot "$R" pacman -Rns --noconfirm plasma-welcome || true
- KANIT: pacman -r work/.../airootfs -Q | grep welcome → BOŞ
- drkonqi mask CANLIDA da VAR → kurulum ekranında çökme penceresi YOK

## §2 (final45+) WAYDROID: ZİNCİR + GERÇEK İLERLEME BAR
- modules-load: binder_linux; finalize: enable waydroid-container
- yerinde-waydroid GUI:
  • imaj indirirken GERÇEK ilerleme: /var/lib/waydroid altındaki
    imaj boyutunu 1sn'de bir oku → ttk.Progressbar doldur
    (belirsiz spinner YASAK)
  • "Yenile" = waydroid status + oturum + imaj boyutu GERÇEK yenile
  • binder yoksa Türkçe uyarı + modprobe komutunu göster
- DOĞRULA: py_compile + bash -n (tty sürümü)

## §3 GÖREV YÖNETİCİSİ AÇILMIYOR
- ÖNCE terminalden çalıştır → traceback'i rapora BAS (tahmin yasak)
- Olası kökler: psutil/tk eksik, nvidia-smi yokken istisna, Exec hatalı
- Düzelt: bağımlılıklar packages'ta VAR; kod nvidia-smi YOKSA "—"
  göstersin (çökmesin); .desktop Exec doğrula
- DOĞRULA: py_compile + Exec ls

## §4 MAĞAZA MODERN + KEŞFET GERİ GELİYOR
- yerinde-magaza ttk modernizasyon: tema (clam/sun-valley tarzı),
  kart görünümü, üstte arama çubuğu, kategori sekmeleri, renkli
  kur/kaldır butonları, ince ilerleme çubuğu — İŞLEV AYNEN
  (pacman+flatpak+AUR, kuyruk, Flathub oto-ekle)
- packages.x86_64 += discover packagekit appstream  (KULLANICI
  İSTEĞİ: Keşfet yüklü olsun) — boyut etkisini rapora yaz
- KANIT: pacman -r airootfs -Q | grep -E "magaza|gorev|waydroid|
  discover" → 4'ü de LİSTEDE

## §5 TIKLA-KUR OLLAMA (satır 138/139 "command not found")
"Çevrimdışı modeller (e/h)" = e ise SIRAYLA:
  sudo pacman -S --needed ollama
  sudo systemctl enable --now ollama
  ollama pull llama3.1 && ollama pull qwen2.5-coder:1.5b
başarısızsa Türkçe uyarı + DEVAM (script ÖLMEZ)
KANIT: bash -n + grep "pacman -S --needed ollama" VAR

## §6 REGRESYON KORUMASI
UEFI yeşil/krem/turuncu + MBR krem (final37); Türkçe pf2 font;
ydotool zinciri; ses 24kHz; tıkla-kur=kurulum.sh delege; keyring;
zip; oto-giriş; NVIDIA finalize; unpackfs koruması; asistanın
KENDİSİ ISO'da YOK (ollama da ISO'da YOK — tıkla-kur kurar).

## §7 ISO DERLEME (ATLANMAZ — final44 dersi!)
1) pkgrel bump'lar (branding + değişen yerinde-*) + makepkg + repo-add
2) setsid bash -c './build-iso.sh > /tmp/opencode/final46-iso.log
   2>&1' &  → poll "INFO: Done!" + out/*.iso + sha256
3) İÇERİK KANITI: pacman -r work/x86_64/airootfs -Q |
   grep -E "magaza|gorev|waydroid|discover" → dolu

## §8 RAPOR + KULLANICI TEST LİSTESİ
1) Görev yöneticisi açılır (menü + terminal temiz)
2) Mağaza modern; Keşfet menüde VAR
3) Waydroid: indirmede bar DOLAR; Yenile çalışır
4) tıkla-kur "e" → ollama kurulur + modeller iner (not-found YOK)
5) Kurulum ekranında çökme penceresi YOK
6) UEFI yeşil + MBR krem regresyonu YOK