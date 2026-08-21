#!/bin/bash
# yerinde-kullanici helper — pkexec ile çalışır (root yetkisi)
# Kullanım: helper.sh <komut> [args...]
# Komutlar: ekle <kullanıcı> <parola> <gruplar>
#           sil <kullanıcı>
#           parola <kullanıcı> <yeni_parola>
#           otogiris <acik|kapali>   (final58 §1.4)

set -euo pipefail

AUTOLOGIN_CONF=/etc/sddm.conf.d/yerinde-autologin.conf
AUTOLOGIN_KEEP=/etc/yerinde/autologin-keep

cmd="${1:-}"
shift || true

case "$cmd" in
  ekle)
    user="${1:-}"; pass="${2:-}"; groups="${3:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    [ -z "$pass" ] && { echo "Parola gerekli" >&2; exit 1; }
    id "$user" &>/dev/null && { echo "Kullanıcı zaten var: $user" >&2; exit 1; }
    useradd -m -G "${groups:-wheel}" "$user"
    echo "$user:$pass" | chpasswd
    echo "OK: $user eklendi (grup: ${groups:-wheel})"
    ;;
  sil)
    user="${1:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    [ "$user" = "root" ] && { echo "Root silinemez" >&2; exit 1; }
    id "$user" &>/dev/null || { echo "Kullanıcı bulunamadı: $user" >&2; exit 1; }
    userdel -r "$user"
    echo "OK: $user silindi"
    ;;
  parola)
    user="${1:-}"; pass="${2:-}"
    [ -z "$user" ] && { echo "Kullanıcı adı gerekli" >&2; exit 1; }
    [ -z "$pass" ] && { echo "Yeni parola gerekli" >&2; exit 1; }
    id "$user" &>/dev/null || { echo "Kullanıcı bulunamadı: $user" >&2; exit 1; }
    echo "$user:$pass" | chpasswd
    echo "OK: $user parolası güncellendi"
    ;;
  otogiris)
    # final58.md §1.4 — oto-girişi parola olsa bile açık tut / kapat.
    durum="${1:-}"
    case "$durum" in
      acik)
        touch "$AUTOLOGIN_KEEP"
        mkdir -p /etc/sddm.conf.d
        cat > "$AUTOLOGIN_CONF" <<'CONF'
# final58 §1.4: kullanıcı "oto-girişi açık tut" seçti (autologin-keep).
[Autologin]
User=yerinde
Session=plasma.desktop
Relogin=false
CONF
        echo "OK: oto-giriş AÇIK tutulacak (parola olsa bile)"
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
    echo "Kullanım: $0 <ekle|sil|parola|otogiris> [args...]" >&2; exit 1
    ;;
esac
