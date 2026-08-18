#!/usr/bin/env bash
# YERINDE — CachyOS (Arch Linux) kurulum betiği
set -e

echo "══════════════════════════════════════════"
echo "  YERINDE CachyOS — Kurulum"
echo "══════════════════════════════════════════"

# final24.md §4 + aifinal.md §1: Yerinde ANKA ön adımı — numpy/Pillow/pyaudio
# SİSTEMden (wheel'siz kaynak derlemeyi ve gcc hatasını baştan engeller;
# venv --system-site-packages bunları otomatik görür). ydotool: Wayland
# klavye/fare kontrolü (aifinal.md §2).
sudo pacman -S --needed python-numpy python-pillow python-opencv \
    python-pyaudio portaudio ydotool || true

# ══ Wayland girdi altyapısı (aifinal.md §2): ydotool daemon + uinput ════════
# ydotoold: ydotool'un tuş/fare olaylarını /dev/uinput üzerinden göndermesi
# için gereken daemon. Modern Arch/CachyOS'ta KULLANICI servisi tercih edilir
# (soket $XDG_RUNTIME_DIR/.ydotool_socket'e gider — ydotool istemcisi bunu
# varsayılan olarak bulur; sistem servisi YOKSA ona düşülür). uinput grubu +
# modules-load ile açılışta hazır olur.
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    echo
    echo "[*] Wayland oturumu algılandı — ydotool altyapısı hazırlanıyor..."
    if ! systemctl --user enable --now ydotoold 2>/dev/null; then
        sudo systemctl enable --now ydotoold 2>/dev/null || \
            sudo systemctl enable --now ydotool 2>/dev/null || \
            echo "[UYARI] ydotoold servisi etkinleştirilemedi (paketi kurulu mu?)"
    fi
    sudo usermod -aG uinput,input "$USER" 2>/dev/null || true
    echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf >/dev/null 2>&1 || true
    echo "[NOT] Grup değişikliklerinin geçerli olması için OTURUMU YENİDEN AÇ."
fi

echo
echo "[1/4] Gerekli sistem paketleri kontrol ediliyor (pacman)..."
# pipewire-pulse: 'parec' sağlar — sounddevice/PortAudio sessiz kalırsa
#   (hata vermeden mikrofon verisi göndermezse) MicStream buna otomatik
#   düşer. wtype/ydotool: Wayland oturumunda klavye/fare kontrolü için
#   xdotool/pyautogui işe yaramaz; bu ikisi gerçek Wayland araçlarıdır.
#   grim: Wayland'de ekran görüntüsü yakalama (mss çalışmaz) için gereklidir.
PKGS="python python-pip tk portaudio pipewire-pulse xclip wl-clipboard espeak-ng ffmpeg xdotool wtype ydotool grim"
MISSING=""
for p in $PKGS; do
    pacman -Qi "$p" >/dev/null 2>&1 || MISSING="$MISSING $p"
done
if [ -n "$MISSING" ]; then
    echo "Eksik paketler bulundu:$MISSING"
    echo "Şunu çalıştırman gerekebilir:"
    echo "    sudo pacman -S$MISSING"
    read -p "Şimdi kurmayı dene? [y/N] " yn
    if [ "$yn" = "y" ] || [ "$yn" = "Y" ]; then
        sudo pacman -S --needed $MISSING
    fi
else
    echo "Tüm sistem paketleri kurulu görünüyor."
fi

echo
echo "[*] KDE Plasma Wayland tespit edilirse: kdotool kuruluyor (opsiyonel)..."
# kdotool: xdotool'un KDE Wayland karşılığı — pencere arama/odaklama için
# (bkz. actions/office_keys.py, actions/window_safety.py, actions/whatsapp_call.py).
# ÖNEMLİ: kdotool'un kaynak kodu 'let chain' (if/while içinde birden fazla
# 'let' zincirlenmesi) gibi YENİ bir Rust söz dizimi kullanıyor — bu ancak
# rustc 1.88+ (Rust 2024 edition) ile derlenebiliyor. Dağıtım paketindeki
# (pacman) rustc bazen bundan daha eski olabilir, bu yüzden dağıtım
# paketine güvenmek yerine rustup (resmi Rust kurulum aracı) ile HER ZAMAN
# GÜNCEL bir araç zinciri kuruyoruz. Yalnızca KDE Plasma + Wayland ise ve
# kdotool zaten yoksa devreye girer; başarısız olursa kurulumu DURDURMAZ
# (Hyprland/Sway kullananlar için zaten gerekli değil; GNOME Wayland'de
# karşılığı yok, YERİNDE bunu güvenli biçimde algılayıp pencere-bulma
# özelliklerini "emin olamıyorum" moduna düşürür).
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ] && \
   printf '%s' "${XDG_CURRENT_DESKTOP:-}${DESKTOP_SESSION:-}" | grep -qi "kde\|plasma"; then
    if command -v kdotool >/dev/null 2>&1; then
        echo "[OK] kdotool zaten kurulu."
    else
        CARGO_BIN="$HOME/.cargo/bin/cargo"
        if [ ! -x "$CARGO_BIN" ]; then
            command -v curl >/dev/null 2>&1 || sudo pacman -S --needed --noconfirm curl || true
            pacman -Qi dbus >/dev/null 2>&1 && pacman -Qi pkgconf >/dev/null 2>&1 || \
                sudo pacman -S --needed --noconfirm dbus pkgconf || true
            echo "     rustup ile güncel bir Rust araç zinciri kuruluyor (bir kereye"
            echo "     mahsus, birkaç dakika sürebilir)..."
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
                | sh -s -- -y -q --default-toolchain stable || true
        fi
        if [ -x "$CARGO_BIN" ]; then
            if "$CARGO_BIN" install kdotool; then
                echo "[OK] kdotool kuruldu (~/.cargo/bin/kdotool)."
                echo "     ~/.cargo/bin dizini PATH'te değilse ~/.bashrc'ye ekle:"
                echo "         export PATH=\"\$HOME/.cargo/bin:\$PATH\""
            else
                echo "[UYARI] kdotool derlenemedi — pencere odaklama özellikleri"
                echo "        Wayland'de bu olmadan çalışmayacak. Elle deneyebilirsin:"
                echo "        \"$CARGO_BIN\" install kdotool"
            fi
        else
            echo "[UYARI] rustup/cargo kurulamadı (internet yok/erişilemedi olabilir),"
            echo "        kdotool atlandı. Elle kurulum:"
            echo "        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            echo "        ~/.cargo/bin/cargo install kdotool"
        fi
    fi
else
    echo "KDE Plasma Wayland tespit edilmedi, kdotool atlanıyor."
fi

echo
echo "[2/4] Sanal ortam oluşturuluyor (venv)..."
# --system-site-packages: LibreOffice'in python-uno modülü SİSTEM
# python'una kurulur; venv onu görebilsin diye şart. Ayrıca sistemden gelen
# python-numpy/python-pyaudio gibi paketleri de görür → pip asla derleme
# DENEMEZ (aifinal.md §1). Eski/bozuk venv'i temizleyerek başla.
rm -rf venv
python -m venv --system-site-packages venv
source venv/bin/activate

echo
echo "[3/4] Python paketleri kuruluyor..."
pip install --upgrade pip
# aifinal.md §1: pip kaynak derlemeye düşerse (numpy/pyaudio wheel bulunamadı
# vb.) Türkçe fallback ile yönlendir — sistem paketleri kuruluysa venv
# --system-site-packages sayesinde pip bunları derlemeden GÖRÜR.
if ! pip install -r requirements.txt; then
    echo
    echo "Derleme hatası (numpy/pyaudio): sudo pacman -S python-numpy python-pyaudio portaudio"
    exit 1
fi

# ultralytics (YOLO11 - kamerada canlı nesne algılama) kasıtlı olarak
# requirements.txt dışında tutuluyor (torch bağımlılığı büyük ve bazı
# platformlarda ABI çatışması yaşayabiliyor). yolo_enabled varsayılan
# olarak AÇIK olduğundan, burada AYRI ve best-effort olarak kurmayı
# deniyoruz - başarısız olursa kurulumu DURDURMUYOR, YERİNDE zaten
# ultralytics eksikse kamerayı otomatik "sadece önizleme" moduna
# düşürüyor (bkz. backend/vision_engine.py).
echo
echo "[*] Kamera nesne algılama (YOLO11) için ultralytics kuruluyor..."
if pip install ultralytics -q; then
    echo "[OK] ultralytics kuruldu - kamerada canlı nesne algılama (YOLO11) hazır."
    echo "[*] YOLO11n model ağırlıkları indiriliyor (ilk kullanımda beklememek için)..."
    if python3 -c "from ultralytics import YOLO; YOLO('yolo11n.pt')" >/dev/null 2>&1; then
        echo "[OK] yolo11n.pt indirildi/hazır."
    else
        echo "[UYARI] yolo11n.pt şimdi indirilemedi (internet yok/erişilemedi olabilir)."
        echo "        İlk kamera kullanımında otomatik indirilmeyi deneyecek."
    fi
else
    echo "[UYARI] ultralytics kurulamadı - kamera sadece önizleme modunda çalışacak."
    echo "        Sonradan elle kurmak için: source venv/bin/activate && pip install ultralytics"
fi

echo
echo "[4/4] Yapılandırma dosyası hazırlanıyor..."
mkdir -p config
if [ ! -f config/api_keys.json ]; then
    cp config/api_keys.example.json config/api_keys.json
    echo "config/api_keys.json oluşturuldu — Gemini API anahtarını programın"
    echo "AYARLAR panelinden girebilir, ya da bu dosyayı elle düzenleyebilirsin."
fi

echo
echo "Kurulum tamamlandı! Başlatmak için:  ./baslat.sh"
