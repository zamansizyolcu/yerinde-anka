# final30 — ISO REBUILD (final27 değişikliklerini ISO'ya al)
ÖN DOĞRULAMA (rebuild'den ÖNCE):
- grep: airootfs/usr/local/bin/yerinde-asistan-kur içinde yeni
  mesaj satırları VAR ("İnternet: VAR/YOK" ayrı, sabit yanıltıcı
  metin YOK) + git clone fallback VAR
- grep: packages.x86_64 içinde python-pyaudio + portaudio
- eksikse ÖNCE uygula, SONRA derle

BUILD:
- cd iso/yerinde (veya build-iso.sh kökü)
- setsid + log: ./build-iso.sh > /tmp/opencode/iso30.log 2>&1 &
- bitince: ls -lh out/*.iso + sha256sum

REGRESYON (raporda onay):
ANKA adları (GRUB/MBR/SDDM/Calamares), keyring doğumda, zip
araçları, NOESCAPE+TABMSG gizli, Wayland-tek oturum, SDDM krem +
Enter + ⟳⏻, 5 duvar kağıdı, asistanın KENDİSİ ISO'da YOK.

RAPOR:
- ISO boyutu + sha256 + dosya adı yerinde-anka-*.iso
- kullanıcı test: VM'de "YERINDE Asistanı Kur" → mesajlar doğru
  (internet var/yok ayrımı), LAN/clone yolları denemeye hazır