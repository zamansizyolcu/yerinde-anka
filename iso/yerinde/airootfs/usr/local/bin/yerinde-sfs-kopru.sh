#!/bin/bash
# yerinde-sfs-kopru.sh — final73 (final62) §2: pre-unpackfs köprüsü
#
# SORUN: Geekom/copytoram gibi ortamlarda canlı oturumda
# /run/archiso/bootmnt/arch/x86_64/airootfs.sfs görünmez; unpackfs %2
# "kaynak yok" şifreli hatasıyla düşer.
#
# ÇÖZÜM: unpackfs ÇALIŞMADAN ÖNCE (shellprocess@preunpack, dontChroot=true
# → canlı sistemde root olarak) sfs dosyası RAM'de/değişik mount'ta aranır
# ve beklenen yere SYMLINK ile köprülenir. Normal modda dosya zaten
# yerindedir; betik hiçbir şeye dokunmaz (idempotent).
#
# Köprüden sonra da kaynak yoksa: NET Türkçe hata + exit 1 → Calamares
# DURUR; şifreli %2 hatası asla gösterilmez.

set -u
HDEF=/run/archiso/bootmnt/arch/x86_64/airootfs.sfs

# Keşif çıktısı (kullanıcı raporu için Calamares loguna düşer)
echo "SFS-KOPRU: cmdline=$(tr '\0' ' ' < /proc/cmdline)"
findmnt -rn -o TARGET,SOURCE,FSTYPE | grep -i archiso || true

# Normal mod: dosya yerinde → dokunma
if [ -e "$HDEF" ]; then
    echo "SFS-KOPRU: kaynak yerinde (normal mod) -> $HDEF"
    exit 0
fi

mkdir -p "$(dirname "$HDEF")"

# Aday konumlar: copytoram (archiso standardı) + final73 §1 keşif yolları
ADAYLAR=(
    /run/archiso/copytoram/airootfs.sfs
    /run/archiso/sfs/airootfs.sfs
)
for c in /run/archiso/sfs/*/airootfs.sfs; do
    [ -e "$c" ] && ADAYLAR+=("$c")
done

# Geekom mount quirk'i: sfs, archiso/airootfs ile ilgili HERHANGİ bir
# mount ağacında olabilir → sınırlı derinlikle tara
while IFS= read -r m; do
    while IFS= read -r f; do
        ADAYLAR+=("$f")
    done < <(find "$m" -maxdepth 5 -name airootfs.sfs -type f 2>/dev/null)
done < <(findmnt -rn -o TARGET | grep -i -E 'archiso|airootfs' | sort -u)

for c in "${ADAYLAR[@]}"; do
    if [ -e "$c" ] && [ "$c" != "$HDEF" ]; then
        ln -sfn "$c" "$HDEF" && {
            echo "SFS-KOPRU: köprü kuruldu -> $HDEF -> $c"
            exit 0
        }
    fi
done

# final73 §3: net Türkçe mesaj + DUR (şifreli %2 hatası asla)
MSG="Kurucu canlı ISO ortamı bulamadı (airootfs.sfs yok).\n\nBilgisayarı kurulum medyasından yeniden başlatın; hata sürerse medyayı başka bir USB bağlantı noktasına takıp 'copytoram' seçeneği olmadan deneyin."
echo "SFS-KOPRU HATA: $HDEF bulunamadı; adaylar: ${ADAYLAR[*]:-yok}"
if command -v kdialog >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    kdialog --title "Yerinde AnkA Kurucu" --error "$MSG" >/dev/null 2>&1 || true
elif command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    zenity --error --title="Yerinde AnkA Kurucu" --text="$MSG" >/dev/null 2>&1 || true
fi
exit 1
