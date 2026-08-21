#!/bin/bash
# final58.md §1 — OTO-GİRİŞ/PAROLA TUTARLILIĞI
# "yerinde" kullanıcısına parola konmuşsa (passwd -S = P) SDDM oto-girişini
# otomatik KAPATIR. Parola yokken (NP/L) DOKUNMAZ → öğretmen PC'si pratik kalır.
# Geri açma yolu: sudo touch /etc/yerinde/autologin-keep + conf'u geri koy
# (yerinde-kullanici uygulamasındaki "oto-girişi açık tut" onay kutusu).

U=yerinde

# final58 §1.4: kullanıcı açıkça "oto-girişi açık tut" dedi ise karışma
[ -e /etc/yerinde/autologin-keep ] && exit 0

S=$(passwd -S "$U" 2>/dev/null | awk '{print $2}')

if [ "$S" = "P" ]; then
  rm -f /etc/sddm.conf.d/yerinde-autologin.conf
fi

exit 0
