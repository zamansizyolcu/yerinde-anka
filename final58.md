# final58 — OTO-GİRİŞ/PAROLA TUTARLILIĞI + HIZLI OTURUM KAPATMA
KURALLAR: grep/ls doğrulamalı; Türkçe rapor; test temizlenmeden
paket/ISO/push YOK.

## §1 OTO-GİRİŞ: PAROLA KONUNCA OTOMATİK KAPANIR
1) airootfs/usr/local/bin/yerinde-autologin-check.sh:
   U=yerinde
   [ -e /etc/yerinde/autologin-keep ] && exit 0
   S=$(passwd -S "$U" | awk '{print $2}')
   [ "$S" = "P" ] && rm -f /etc/sddm.conf.d/yerinde-autologin.conf
2) systemd oneshot birimi:
   [Unit] Before=display-manager.service
   [Service] Type=oneshot ExecStart=/usr/local/bin/...check.sh
   [Install] WantedBy=multi-user.target → airootfs enable linki
3) Parola YOKKEN (NP/L) DOKUNMA → öğretmen PC'si pratik kalır
4) Geri açma yolu: sudo touch /etc/yerinde/autologin-keep +
   conf'u geri koy (yerinde-kullanici uygulamasına "oto-girişi
   açık tut" onay kutusu ekle)
5) DOĞRULA: bash -n; oneshot linki ls; conf davranışı grep

## §2 OTURUM KAPATMA HIZI (<10sn)
1) ASİSTAN (repo): main.py'ye SIGTERM/SIGHUP handler →
   asyncio loop stop + pyaudio stream close + temiz exit
   commit + push (asistan repo, KULLANICI İZNİ VAR)
2) systemd kısaltma (airootfs + kurulu şablon):
   /etc/systemd/system.conf.d/yerinde-timeouts.conf
   [Manager] DefaultTimeoutStopSec=15s
             DefaultTimeoutStartSec=30s
3) Suçlu birim raporu: journalctl -b -1 | grep -iE "stopping|timeout"
   → inatçı unit'e TimeoutStopSec=5 + KillMode=mixed
4) DOĞRULA: kullanıcı testinde oturum kapat <10sn

## §3 REGRESYON + BUILD + PUSH
- SDDM tema (final57 verbatim dosya) AYNEN; liste+giriş çalışır
- "Kullanıcı değiştir" → greeter (normal, DOKUNMA)
- çift boot, waydroid, ydotool, ses 24kHz, piper, ANKA markası AYNEN
- branding pkgrel + makepkg + repo-add
- setsid build-iso.sh > /tmp/opencode/final58-iso.log 2>&1 &
  poll "INFO: Done!" + sha256
- git push: yerinde-anka + asistan repo (SIGTERM commit)

## §4 KULLANICI TEST LİSTESİ
1) kurulum şifresiz → oto-giriş AÇIK
2) sonra parola konur → reboot → greeter PAROLA ister
   (oto-giriş otomatik kapandı)
3) autologin-keep ile parola varken oto-giriş geri açılır
4) oturum kapat <10sn; kullanıcı değiştir → greeter (normal)