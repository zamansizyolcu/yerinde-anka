#!/bin/bash
# yerinde-kullanici helper — pkexec ile çalışır (root yetkisi)
# Kullanım: helper.sh <komut> [args...]
# Komutlar: ekle <kullanıcı> <parola> <gruplar>
#           sil <kullanıcı>
#           parola <kullanıcı> <yeni_parola>

set -euo pipefail

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
  *)
    echo "Kullanım: $0 <ekle|sil|parola> [args...]" >&2; exit 1
    ;;
esac
