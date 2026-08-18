# final38 — KURULUM/BASLAT "HEPSİ YA DA HİÇ" HATASI
## §1 pacman TEK TEK (§[2/3])
for pkg in liste; pacman -S --needed "$pkg" || "atlandı: $pkg" logla
(tek kötü adın tüm listeyi öldürmesi YASAK)
AD HARİTASI: python-selenium→pip selenium; python-vosk depoda
yoksa→pip vosk; python-opencv yoksa→pip opencv-python
## §2 VENV HER ZAMAN ([2.5/3])
[ -d venv ] || python -m venv --system-site-packages venv
+ pip/wheel/setuptools upgrade; eksik kalanlar pip ile
(Wayland'de pyautogui/pygetwindow/pyrect HARİÇ — pyrect çöküşü)
## §3 baslat.sh GÜVENLİ
venv yoksa oluştur; venv/bin/python yoksa system python3 fallback;
açılmazsa Türkçe ipucu: eksik modül adı + kurulacak komut
## §4 kdotool: cc YOKSA önce pacman -S --needed gcc binutils,
sonra cargo install; başarısızsa UYARI + devam (kurulumu ÖLDÜRME)
## §5 TEST: temiz VM → ./kurulum.sh && ./baslat.sh → asistan açılır;
rapor: atlanan paket listesi + başlama kanıtı; commit + push
## §6 REGRESYON: ydotool/socket adımı, numpy gevşek pin, Türkçe
mesajlar AYNEN