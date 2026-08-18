# YERINDE OS v1.6 — X11 STABİLİTE + SDDM YERLEŞİM + WAYLAND ARAÇLARI
KURALLAR: VM testi YOK; push YOK; setsid+log; her adım ls doğrulamalı;
regresyon koruması: MBR krem menü, GRUB teması/fallback, 5 duvar kağıdı,
ollama store+GGUF, sudoers wheel, SDDM Enter+güç düğmeleri, launcher
home-kopyası, kişisel config YOK (grep kanıtı).

## 1) SDDM: OTURUM SEÇİCİ BUTONLARLA YAN YANA
Main.qml yerleşimi (tek satır, ortalanmış):
Row(spacing:8){ ComboBox(session) ; Button"Giriş"(login()) ;
Button"⟳"(sddm.reboot()) ; Button"⏻"(sddm.powerOff()) }
- "Oturum:" etiketi ComboBox'ın solunda küçük kalabilir ama
  ComboBox AYNI satırda olacak; alttaki eski ayrı satırı SİL.
- login() = sddm.login(name, password, session.currentIndex) (v1.5 aynen)
- Parola focus + Keys.onReturnPressed login (v1.4 aynen)
- sddm --test-mode doğrulaması; "Cannot assign" varsa FAIL.

## 2) ASİSTAN X11 FULLSCREEN ÇÖKMESİ (kesik görünüm + kapat/yeniden
   başlat kırığı + drkonqi Qt6 abort)
Kök neden: Tk "-fullscreen" attribute'u X11/KWin'de çökme yapıyor.
ui.py _enter_fullscreen / _toggle_fullscreen / _esc_action DÜZELT:
- XDG_SESSION_TYPE == "x11" ise:
  self.root.attributes("-fullscreen", True) KULLANMA;
  try: self.root.state("zoomed")   # KWin maximize — stabil
  except: self.root.geometry(f"{sw}x{sh}+0+0")
  çıkışta: state("normal") + pencere geometrisi.
- Wayland/xwayland dalı mevcut -fullscreen davranışını KORUR.
- _resize_surface try/except ile sarmala (çökme → log, açık kal).
- Smoke: python3 -m py_compile ui.py main.py → FAIL-kontrollü.

## 3) X11 KAPAT/YENİDEN BAŞLAT GÜVENCESİ
- #2 büyük olasılıkla kökü çözer (KWin artık çökmüyor).
- Ek güvence: packages += xorg-xhost xorg-xprop xorg-xwininfo
- airootfs'e NOT ekleme; drkonqi'ye dokunma.
- Rapor notu: kurulu X11 oturumunda `systemctl reboot` GUI'siz de
  çalışır; GUI akışı #2 sonrası test edilecek (kullanıcı listesi).

## 4) WAYLAND'DE SESLİ KLAVYE/FARE = YDOTOOL
- packages += ydotool (regresyon: v1.4'te vardı, DOĞRULA)
- ydotoold drop-in + socket /run/ydotool.socket 0660 group uinput
  + airootfs wants linki + finalize usermod -aG uinput,input "$USER"
  (v1.4 aynen, ls/systemctl cat ile DOĞRULA)
- actions/type_text.py, mouse_control.py, keyboard_control(press_key):
  XDG_SESSION_TYPE=="wayland" → ydotool:
    yazı:  ydotool type "..."
    tuş:   ydotool key <code>:1 <code>:0
    tık:   ydotool click 0xC0 / 0xC1; hareket: ydotool move -- x y
  değilse xdotool. Hata mesajı Türkçe:
  "ydotool/uinput hazır değil (servis+grup kontrol)".
- vendor/kod smoke: py_compile üç dosya.

## 5) CANLI MOD: YERİNDE TIKLAYINCA AÇILSIN
- airootfs/usr/share/applications/yerinde-ai.desktop:
  Exec=/usr/bin/yerinde, Icon=yerinde, OnlyShowIn=KDE (DOĞRULA)
- /usr/bin/yerinde launcher: kaynak /usr/share/yerinde-ai/app
  (main.py+run.sh+vendor) airootfs'te VAR mı ls ile DOĞRULA;
  yoksa FAIL. chmod +x ikisi de.
- OTO-BAŞLATMA YOK (autostart dosyası YOK, ls kanıtı).
- Config yoksa main.py varsayılanı gemini → tıklayınca API ekranı.

## 6) PAKET + BUILD + RAPOR
- yerinde-branding + yerinde-ai-assistant pkgrel bump; makepkg;
  repo-add; commit (push YOK); ISO rebuild setsid+log; sha256.
- Rapor kanıtları:
  1) Main.qml Row satırı (ComboBox+3 buton yan yana)
  2) ui.py X11 "zoomed" dalı satırları
  3) ydotool dalı satırları (3 dosya)
  4) ls: yerinde-ai.desktop, /usr/share/yerinde-ai/app/main.py,
     run.sh(+x), autostart YOK
  5) sddm-test.log temiz
- Kullanıcı test listesi:
  • SDDM: seçici + Giriş + ⟳ + ⏻ TEK satırda
  • X11 oturumu: asistan kesiksiz (zoomed), kapat/yeniden başlat
    menüsü çökmeden çalışır
  • Wayland: "fareyi sağa oynat", "ctrl+t yaz" sesli komutları
    ydotool ile işler
  • Canlı: menüden tıkla → Gemini API ekranı açılır