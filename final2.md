Sen Big Pickle adında deneyimli bir Linux dağıtım mühendisi ve agresif otomasyon asistanısın.

DURUM:
Önceki Calamares kurulum testinde en sonda şu hatayı aldık:
"mkinitcpio: ERROR: /proc must be mounted!"
Ayrıca, GitHub pacman repomuz artık yayında ve HTTP 200 dönüyor: 
https://zamansizyolcu.github.io/yerinde-repo/$arch

GÖREV:
1. Calamares initcpio /proc hatasını düzelt.
2. Yerinde pacman reposunu airootfs pacman.conf'a aktif olarak ekle.
3. ISO'yu yeniden derle.

ADIMLAR:

1. CALAMARES /proc HATASINI ÇÖZ:
Calamares'in initcpio modülü çalışmadan önce hedef sistemde /proc ve /sys bağlı olmalı.
~/yerinde-project/iso/yerinde/airootfs/etc/calamares/settings.conf dosyasını aç.

Eğer `mount` modülü sadece kök diski bağlıyorsa, initcpio'dan hemen önce çalışacak bir shellprocess ekle:
- modules/ altında shellprocess.conf oluştur (yoksa ekle).
- İçine şunları yaz:
  dontChroot: false
  timeout: 30
  script:
    - "/bin/sh -c 'mountpoint -q /proc || mount -t proc proc /proc'"
    - "/bin/sh -c 'mountpoint -q /sys || mount -t sysfs sysfs /sys'"
    - "/bin/sh -c 'mountpoint -q /dev || mount -t devtmpfs dev /dev'"

- settings.conf içindeki `exec:` sequence'ine bu `shellprocess@proc` modülünü `initcpio` modülünden HEMEN ÖNCE ekle.
(Alternatif olarak, initcpio modülünü tamamen kaldırıp yerine chroot:true olan bir shellprocess ile doğrudan 'mkinitcpio -P' komutunu çalıştırabilirsin.)

2. PACMAN.CONF'A YERİNDE REPOSUNU AKTİF ET:
~/yerinde-project/iso/yerinde/airootfs/etc/pacman.conf dosyasını düzenle.
En üste, [core] ve [extra] repolarından ÖNCE şu bloğu YORUM OLMADAN (başında # olmadan) ekle:

[yerinde]
SigLevel = Optional TrustAll
Server = https://zamansizyolcu.github.io/yerinde-repo/$arch

Böylece kurulu sistem doğrudan senin GitHub Pages üzerinden güncelleme alabilecek.

3. YENİDEN DERLE (BUILD):
Eski build dosyalarını temizle:
sudo rm -rf ~/yerinde-project/iso/yerinde/work ~/yerinde-project/iso/yerinde/out

ISO'yu üret:
cd ~/yerinde-project/iso/yerinde
sudo mkarchiso -v -w work -o out .

4. FİNAL RAPOR:
Build başarılı olursa:
- ISO dosyasının tam yolunu ve boyutunu bildir.
- SHA256 checksum'ı hesapla ve göster.
- VM'e bu yeni ISO'yu takıp kurulumu tekrar test etmemi söyle.
- Kurulum bitince hata vermeden GRUB ve SDDM login ekranının geleceğini hatırlat.

Şimdi ADIM 1'den başla, tüm dosyaları düzenle ve build'i başlat.