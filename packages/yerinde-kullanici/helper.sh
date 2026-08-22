#!/bin/bash
# yerinde-kullanici helper — pkexec ile çalışır (root yetkisi)
# Kullanım: helper.sh <komut> [args...]
# Komutlar: ekle <kullanıcı> <gruplar>     (parola STDIN'den okunur)
#           sil <kullanıcı>
#           parola <kullanıcı>            (yeni parola STDIN'den okunur)
#           liste                          (ad|tam-ad satırları)
#           otogiris <acik|kapali>
#
# final63: parola ARTIK komut satırı argümanı DEĞİL (stdin) — /proc/*/cmdline'a
# sızmaz. 'liste' GUI açılır listelerini besler. otogiris 'acik' gerçek
# kullanıcıya yazar ('yerinde' sabiti değildi — farklı adla kurulmuşsa bozulur).

set -euo pipefail

AUTOLOGIN_CONF=/etc/sddm.conf.d/yerinde-autologin.conf
AUTOLOGIN_KEEP=/etc/yerinde/autologin-keep

gercek_kullanici() {
  # Kurulu sistemdeki gerçek (insan) kullanıcı: uid>=1000 + login kabuk
  awk -F: '$3>=1000 && $7!~/nologin|false/ {print $1; exit}' /etc/passwd
}

kullanici_adi_gecerli() {
  local u="$1"
  [[ "$u" =~ ^[a-z_][a-z0-9_-]{0,31}$ ]]
}

cmd="${1:-}"
shift || true

case "$cmd" in
  ekle)
    user="${1:-}"; groups="${2:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    kullanici_adi_gecerli "$user" || { echo "Geçersiz kullanıcı adı: $user (küçük harf/rakam/-/_)" >&2; exit 1; }
    id "$user" &>/dev/null && { echo "Kullanıcı zaten var: $user" >&2; exit 1; }
    IFS= read -r pass || true
    [ -z "${pass:-}" ] && { echo "Parola gerekli" >&2; exit 1; }
    useradd -m -G "${groups:-wheel}" "$user"
    echo "$user:$pass" | chpasswd
    echo "OK: $user eklendi (grup: ${groups:-wheel})"
    ;;
  sil)
    user="${1:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    [ "$user" = "root" ] && { echo "Root silinemez" >&2; exit 1; }
    [ "$user" = "$(gercek_kullanici)" ] && { echo "Oturum açmış kullanıcı silinemez: $user" >&2; exit 1; }
    id "$user" &>/dev/null || { echo "Kullanıcı bulunamadı: $user" >&2; exit 1; }
    userdel -r "$user"
    echo "OK: $user silindi"
    ;;
  parola)
    user="${1:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    id "$user" &>/dev/null || { echo "Kullanıcı bulunamadı: $user" >&2; exit 1; }
    IFS= read -r pass || true
    [ -z "${pass:-}" ] && { echo "Yeni parola gerekli" >&2; exit 1; }
    echo "$user:$pass" | chpasswd
    echo "OK: $user parolası güncellendi"
    # final63: sonraki açılış davranışını açıkça bildir
    if [ -e "$AUTOLOGIN_KEEP" ]; then
      echo "NOT: oto-giriş açık tutuluyor (parolaya rağmen doğrudan masaüstü)"
    elif [ -f "$AUTOLOGIN_CONF" ]; then
      echo "NOT: bir sonraki açılışta oto-giriş kapanır, parolanız sorulur"
    fi
    ;;
  liste)
    # GUI açılır listeleri için: ad|görünen-ad (GECOS'un ilk alanı)
    awk -F: '$3>=1000 && $7!~/nologin|false/ {n=$5; sub(/,.*/, "", n); print $1 "|" n}' /etc/passwd
    ;;
  otogiris)
    # final58.md §1.4 — oto-girişi parola olsa bile açık tut / kapat.
    durum="${1:-}"
    case "$durum" in
      acik)
        touch "$AUTOLOGIN_KEEP"
        mkdir -p "$(dirname "$AUTOLOGIN_CONF")"
        RU="$(gercek_kullanici)"
        [ -z "$RU" ] && RU="yerinde"
        cat > "$AUTOLOGIN_CONF" <<CONF
# final58 §1.4: kullanıcı "oto-girişi açık tut" seçti (autologin-keep).
# final63: User= gerçek kullanıcıdan alınır (sabit 'yerinde' DEĞİL).
[Autologin]
User=$RU
Session=plasma.desktop
Relogin=false
CONF
        echo "OK: oto-giriş AÇIK tutulacak ($RU, parola olsa bile)"
        ;;
      kapali)
        rm -f "$AUTOLOGIN_KEEP" "$AUTOLOGIN_CONF"
        echo "OK: oto-giriş kapandı (greeter parola sorar)"
        ;;
      *)
        echo "Kullanım: $0 otogiris <acik|kapali>" >&2
        exit 1
        ;;
    esac
    ;;
  *)
    echo "Kullanım: $0 <ekle|sil|parola|liste|otogiris> [args...]" >&2; exit 1
    ;;
esac
