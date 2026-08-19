# final43 EK — YERINDE WAYDROID YÖNETİCİSİ (Tkinter GUI)
final42 §3'ü DEĞİŞTİRİR: terminal menüsü yerine grafik arayüz.
/usr/bin/yerinde-waydroid = Tkinter GUI (Terminal=false .desktop)
Eski menü yedek kalır: yerinde-waydroid-tty

## ARAYÜZ (ANKA paleti: krem zemin, yeşil başlık, turuncu buton)
• Durum kartı: Kurulu mu? / Çalışıyor mu? / GAPPS mı Vanilla mı
  (/var/lib/waydroid + waydroid status + config parse)
• Butonlar:
  [Kur: GAPPS (Play Store)]  [Kur: Vanilla]
  [Sil]  [Başlat]  [Durdur]  [Güncelle]
• Alt panel: canlı log (ScrolledText, subprocess stdout satır satır)
• Kur butonunda uyarı diyaloğu: "≈1-1.5 GB internetten inecek,
  5-15 dk sürebilir" + onay
• Sil butonunda TEHLİKE diyaloğu: "Android görüntüsü ve TÜM
  veriler silinecek — emin misin?" (iki aşamalı onay)

## YETKİ MODELİ (terminal/pkexec el ile yok)
- GUI kullanıcı olarak koşar
- Ayrıcalıklı işler: pkexec waydroid init -s GAPPS / rm -rf
  /var/lib/waydroid / waydroid container stop
  (KDE polkit diyaloğı şifre sorar — tek tık)
- Başlat: waydroid show-full-ui (kullanıcı olarak, thread içinde)

## DAVRANIŞ
- Kur → canlı log + butonlar kilitli; bitince Durum kartı güncel
- Sil → stop + rm -rf /var/lib/waydroid → "kurulu değil" durumu
- Güncelle → pkexec waydroid upgrade
- Hata olursa log panelinde Türkçe açıklama + öneri

## DOĞRULAMA + REGRESYON
- python -m py_compile; .desktop Terminal=false ls
- VM smoke: GUI açılır, durum kartı doğru okur
- final42'nin kalanı (Mağaza, Görev Yöneticisi, NVIDIA, GAPPS
  notları) AYNEN; build + sha256 + rapor

## TEST LİSTESİ (ana PC)
1) "Waydroid (Android)" ikonu → GUI açılır
2) [Kur: GAPPS] → polkit şifre → log akar → kurulum biter
3) [Başlat] → Android penceresi açılır (Play Store içinde)
4) [Sil] → onay → görüntü kalkar, durum "kurulu değil"
5) Hiçbir adımda terminal/komut YAZILMAZ