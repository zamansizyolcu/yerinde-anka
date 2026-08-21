#!/bin/bash
# final58.md §1 + final62.md §3 — OTO-GİRİŞ/PAROLA TUTARLILIĞI
# Kurulu sistemdeki GERÇEK kullanıcıya (uid>=1000, login kabuk) parola
# konmuşsa (passwd -S = P) SDDM oto-girişini KAPATIR. Parola yokken dokunmaz.
# Her açılışta koşar → sonradan konan parola da bir sonraki açılışta etkili olur.
# (final62: kullanıcı adı 'yerinde' dışında olsa bile çalışır.)
# Geri açma yolu: sudo touch /etc/yerinde/autologin-keep + conf'u geri koy
# (yerinde-kullanici uygulamasındaki "oto-girişi açık tut" onay kutusu).

[ -e /etc/yerinde/autologin-keep ] && exit 0

U=$(awk -F: '$3>=1000 && $7!~/nologin|false/ {print $1; exit}' /etc/passwd)
[ -z "$U" ] && exit 0

S=$(passwd -S "$U" 2>/dev/null | awk '{print $2}')

if [ "$S" = "P" ]; then
  rm -f /etc/sddm.conf.d/yerinde-autologin.conf
fi

exit 0
