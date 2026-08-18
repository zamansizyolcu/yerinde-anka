#!/usr/bin/env bash
# YERINDE — masaüstüne çift tıklayınca baslat.sh'yi çalıştıran bir kısayol
# (.desktop dosyası) oluşturur. KDE/GNOME farketmez, Türkçe ("Masaüstü") ya
# da İngilizce ("Desktop") klasör adı otomatik bulunur.
set -e
cd "$(dirname "$0")"
PROJE_DIZINI="$(pwd)"

# Masaüstü klasörünü doğru şekilde bul (xdg-user-dir varsa onu kullan,
# yoksa Masaüstü/Desktop'tan hangisi varsa ona düş).
if command -v xdg-user-dir >/dev/null 2>&1; then
    MASAUSTU="$(xdg-user-dir DESKTOP)"
elif [ -d "$HOME/Masaüstü" ]; then
    MASAUSTU="$HOME/Masaüstü"
else
    MASAUSTU="$HOME/Desktop"
fi
mkdir -p "$MASAUSTU"

DOSYA="$MASAUSTU/YERINDE.desktop"
cat > "$DOSYA" <<EOF
[Desktop Entry]
Type=Application
Name=YERINDE
Comment=YERINDE Sesli Asistanı Başlat
Exec=/bin/bash -lc 'cd "$PROJE_DIZINI" && ./baslat.sh'
Path=$PROJE_DIZINI
Icon=utilities-terminal
Terminal=true
Categories=Utility;
EOF
chmod +x "$DOSYA"

# GNOME/Nautilus ve bazı KDE sürümleri, çift tıklamadan önce dosyanın
# "güvenilir" işaretlenmesini ister; destekleniyorsa otomatik dene.
if command -v gio >/dev/null 2>&1; then
    gio set "$DOSYA" metadata::trusted true 2>/dev/null || true
fi

# Masaüstü ayrıca uygulama menüsünde de görünsün istersen:
mkdir -p "$HOME/.local/share/applications"
cp "$DOSYA" "$HOME/.local/share/applications/yerinde.desktop"

echo "Kısayol oluşturuldu: $DOSYA"
echo "Masaüstünde ilk çift tıklamada 'Güvenilir/Yürüt' gibi bir onay isteyebilir —"
echo "bir kere onaylaman yeterli, sonrasında normal simge gibi çalışır."
