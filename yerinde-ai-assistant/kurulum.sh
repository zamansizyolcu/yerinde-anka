#!/usr/bin/env bash
# YERINDE — CachyOS / Yerinde ANKA (Arch Linux) kurulum betiği
# final38: "HEPSİ YA DA HİÇ" hatası düzeltildi:
#   §1 pacman paketleri TEK TEK kurulur; biri başarısız olursa "atlandı"
#      olarak loglanır ve kurulum SÜRER (tek kötü ad tüm listeyi öldürmez).
#      AD HARİTASI ile pip'e düşer: python-selenium→selenium,
#      python-vosk→vosk, python-opencv→opencv-python, python-X→X
#   §2 venv HER ZAMAN var ([ -d venv ] || python -m venv
#      --system-site-packages) + pip/wheel/setuptools upgrade; pacman'ın
#      kuramadıkları + depoda olmayanlar pip ile TEK TEK kurulur.
#      Wayland'de pyautogui/pygetwindow/pyrect pip ile ASLA kurulmaz
#      (pyrect sdist çöküşü — final37'nin bulduğu kök neden).
#   §4 kdotool: cc YOKSA önce pacman gcc binutils; cargo install
#      başarısızsa UYARI + devam (kurulumu ÖLDÜRMEZ).
# Tıkla-kur (yerinde-asistan-kur) bu betiği SARICI olarak çağırır:
# pacman paketi yoksa yerel klasörden/clone'dan bu betik koşar.
set -e

echo "══════════════════════════════════════════"
echo "  YERINDE — Kurulum (tek tek kur; hata = atla)"
echo "══════════════════════════════════════════"

ATLANAN=""        # final38 §5 raporu: atlanan paket listesi
PIP_BEKLEYEN=""   # pacman'ın kuramayıp pip'e düşürdüğü adlar

# final38 §1 AD HARİTASI: pacman paket adı → pip paket adı
# (boş dönüş = pip karşılığı yok, sadece atla)
pip_adi() {
    case "$1" in
        python-selenium)  echo "selenium" ;;
        python-vosk)      echo "vosk" ;;
        python-opencv)    echo "opencv-python" ;;
        python-*)         echo "${1#python-}" ;;
        *)                echo "" ;;
    esac
}

# final38 §1: pacman TEK TEK — tek kötü ad tüm listeyi öldürmesin
pacman_tek_tek() {
    local pkg p
    for pkg in "$@"; do
        if pacman -Qi "$pkg" >/dev/null 2>&1; then
            echo "  [OK] $pkg (zaten kurulu)"
        elif sudo pacman -S --needed --noconfirm "$pkg" >/dev/null 2>&1; then
            echo "  [OK] $pkg kuruldu"
        else
            echo "  [ATLANDI] $pkg — pacman başarısız, kurulum sürüyor"
            ATLANAN="$ATLANAN $pkg"
            p="$(pip_adi "$pkg")"
            [ -n "$p" ] && PIP_BEKLEYEN="$PIP_BEKLEYEN $p"
        fi
    done
}

echo
echo "[1/5] Gerekli sistem paketleri (tek tek)..."
# pipewire-pulse: 'parec' sağlar — sounddevice/PortAudio sessiz kalırsa
#   (hata vermeden mikrofon verisi göndermezse) MicStream buna otomatik
#   düşer. wtype/ydotool: Wayland oturumunda klavye/fare kontrolü için
#   xdotool/pyautogui işe yaramaz; bu ikisi gerçek Wayland araçlarıdır.
#   grim: Wayland'de ekran görüntüsü yakalama (mss çalışmaz) için gereklidir.
pacman_tek_tek python tk portaudio pipewire-pulse xclip wl-clipboard \
    espeak-ng ffmpeg xdotool wtype ydotool grim

# ══ Wayland girdi altyapısı: ydotool daemon + uinput (AYNEN — final36) ══════
# ydotoold: ydotool'un tuş/fare olaylarını /dev/uinput üzerinden göndermesi
# için gereken daemon. Modern Arch/CachyOS'ta KULLANICI servisi tercih edilir
# (soket $XDG_RUNTIME_DIR/.ydotool_socket'e gider — ydotool istemcisi bunu
# varsayılan olarak bulur; sistem servisi YOKSA ona düşülür). uinput grubu +
# modules-load ile açılışta hazır olur.
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
    echo
    echo "[*] Wayland oturumu algılandı — ydotool altyapısı hazırlanıyor..."
    # final36: önce SAĞLIKLI sistem soketi var mı bak (yerinde-anka:
    # /run/ydotool.socket 0660 + uinput grubu) — varsa hiçbir servise
    # dokunma (çift daemon olmasın).
    if [ -S /run/ydotool.socket ] && [ -w /run/ydotool.socket ]; then
        echo "[OK] /run/ydotool.socket hazır (sistem daemonu çalışıyor)."
    else
        # Arch/CachyOS ydotool paketi KULLANICI birimi çıkarır ve adı
        # 'ydotool.service'tir ('ydotoold' DEĞİL — eski satır bu yüzden
        # hep başarısız oluyordu). Kullanıcı daemonu XDG altında soket açar.
        if ! systemctl --user enable --now ydotool 2>/dev/null; then
            sudo systemctl enable --now ydotoold 2>/dev/null || \
                sudo systemctl enable --now ydotool 2>/dev/null || \
                echo "[UYARI] ydotoold servisi etkinleştirilemedi — asistan çalışırken öz-onarım dener."
        fi
    fi
    sudo usermod -aG uinput,input "$USER" 2>/dev/null || true
    echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf >/dev/null 2>&1 || true
    echo "[NOT] Grup değişikliklerinin geçerli olması için OTURUMU YENİDEN AÇ."
fi

echo
echo "[2/5] Python kütüphaneleri — önce pacman (tek tek; eksikler pip'e düşecek)..."
# Sistem paketi öncelikli: önceden derli gelir, pip asla kaynak derlemez.
# Depoda olmayanlar (google-genai, piper-tts, faster-whisper, sounddevice,
# pdfplumber, python-docx, python-pptx, dvrip, webdriver-manager) aşağıda
# [3/5] adımında pip ile kurulur.
pacman_tek_tek python-numpy python-pillow python-opencv python-pyaudio \
    portaudio python-psutil python-requests python-pyperclip python-mss \
    python-selenium python-vosk python-av python-openpyxl \
    python-websocket-client

echo
echo "[3/5] Sanal ortam (venv her zaman) + eksik kalanlar pip ile (tek tek)..."
# final38 §2: venv --system-site-packages — sistem python paketleri
# (numpy/pyaudio/opencv...) venv'den görünür; pip yalnız DEPODA OLMAYAN
# ve pacman'ın KURAMADIĞI paketleri kurar. Eski/bozuk venv korunur:
# pip/wheel/setuptools upgrade'i düzeltir; bozuksa baslat.sh sistem
# python3'üne düşer.
if [ ! -d venv ]; then
    python -m venv --system-site-packages venv
fi
if [ -x venv/bin/pip ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
    pip install --upgrade pip wheel setuptools >/dev/null 2>&1 \
        || echo "  [UYARI] pip/wheel/setuptools upgrade başarısız (kurulum sürüyor)"
    # Depoda OLMAYAN çalışma zamanı bağımlılıkları + pacman'ın atladıkları.
    # final38: TEK TEK — biri tutmazsa "atlandı" loglanır, kurulum ölmez.
    PIP_EK="google-genai sounddevice faster-whisper piper-tts pdfplumber \
python-docx python-pptx dvrip webdriver-manager"
    WAYLAND_HARIC=""
    for ad in $PIP_BEKLEYEN $PIP_EK; do
        # final38 §2: Wayland'de pyautogui/pygetwindow/pyrect HARİÇ
        # (pyrect sdist çöküşü; Wayland'de wtype/ydotool zinciri birincil)
        if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
            case "$ad" in
                pyautogui|pygetwindow|pyrect)
                    WAYLAND_HARIC="$WAYLAND_HARIC $ad"
                    continue ;;
            esac
        fi
        if pip install -q "$ad"; then
            echo "  [OK-pip] $ad"
        else
            echo "  [ATLANDI-pip] $ad — pip başarısız, kurulum sürüyor"
            ATLANAN="$ATLANAN pip:$ad"
        fi
    done
    [ -n "$WAYLAND_HARIC" ] && \
        echo "  [BİLGİ] Wayland: pip ile bilinçli KURULMADI:$WAYLAND_HARIC"
    deactivate 2>/dev/null || true
else
    echo "  [UYARI] venv/pip oluşturulamadı — pip adımı atlandı."
    echo "          ./baslat.sh sistem python3 fallback'ine düşer."
fi

echo
echo "[4/5] kdotool (KDE Plasma Wayland, opsiyonel)..."
# kdotool: xdotool'un KDE Wayland karşılığı — pencere arama/odaklama için
# (bkz. actions/office_keys.py, actions/window_safety.py, actions/whatsapp_call.py).
# Yalnızca KDE Plasma + Wayland ise ve kdotool zaten yoksa devreye girer;
# başarısız olursa kurulumu DURDURMAZ (final38 §4: UYARI + devam).
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ] && \
   printf '%s' "${XDG_CURRENT_DESKTOP:-}${DESKTOP_SESSION:-}" | grep -qi "kde\|plasma"; then
    if command -v kdotool >/dev/null 2>&1; then
        echo "[OK] kdotool zaten kurulu."
    else
        # final38 §4: cargo DERLEME için cc gerekir — yoksa önce derleyici
        # (tek tek; kurulamazsa UYARI ile sürülür, cargo zaten kurulamazsa
        # aşağıdaki rustup/cargo bloğu kendi UYARI'sını verir).
        if ! command -v cc >/dev/null 2>&1; then
            echo "     cc yok — önce derleyici kuruluyor (gcc binutils)..."
            pacman_tek_tek gcc binutils
        fi
        CARGO_BIN="$HOME/.cargo/bin/cargo"
        if [ ! -x "$CARGO_BIN" ]; then
            # rustup: dağıtım rustc'sı kdotool'un kullandığı YENİ Rust söz
            # dizimini ('let chain') derleyemeyebilir; güncel araç zinciri
            # garanti eder (bir kereye mahsus, birkaç dakika).
            command -v curl >/dev/null 2>&1 || sudo pacman -S --needed --noconfirm curl || true
            pacman -Qi dbus >/dev/null 2>&1 && pacman -Qi pkgconf >/dev/null 2>&1 || \
                sudo pacman -S --needed --noconfirm dbus pkgconf || true
            echo "     rustup ile güncel bir Rust araç zinciri kuruluyor..."
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
                | sh -s -- -y -q --default-toolchain stable || true
        fi
        if [ -x "$CARGO_BIN" ]; then
            if "$CARGO_BIN" install kdotool; then
                echo "[OK] kdotool kuruldu (~/.cargo/bin/kdotool)."
                echo "     ~/.cargo/bin dizini PATH'te değilse ~/.bashrc'ye ekle:"
                echo "         export PATH=\"\$HOME/.cargo/bin:\$PATH\""
            else
                echo "[UYARI] kdotool derlenemedi — kurulum sürüyor. Elle deneyebilirsin:"
                echo "        \"$CARGO_BIN\" install kdotool"
            fi
        else
            echo "[UYARI] rustup/cargo kurulamadı (internet yok/erişilemedi olabilir),"
            echo "        kdotool atlandı — kurulum sürüyor. Elle kurulum:"
            echo "        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
            echo "        ~/.cargo/bin/cargo install kdotool"
        fi
    fi
else
    echo "KDE Plasma Wayland tespit edilmedi, kdotool atlanıyor."
fi

echo
echo "[5/5] Yapılandırma dosyası hazırlanıyor..."
mkdir -p config
if [ ! -f config/api_keys.json ]; then
    cp config/api_keys.example.json config/api_keys.json
    echo "config/api_keys.json oluşturuldu — Gemini API anahtarını programın"
    echo "AYARLAR panelinden girebilir, ya da bu dosyayı elle düzenleyebilirsin."
fi

# ══ Piper TTS binary (yerel nöral ses için) ══════════════════════════════
echo
echo "[*] Piper TTS binary kontrol..."
PIPER_DIR="$(dirname "$0")/piper"
PIPER_BIN="$PIPER_DIR/piper"
if [ -x "$PIPER_BIN" ]; then
    echo "  [OK] Piper binary zaten mevcut ($PIPER_BIN)"
else
    echo "  [*] Piper indiriliyor (GitHub release ~34MB)..."
    PIPER_VER="1.2.0"
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VER}/piper_linux_x86_64.tar.gz"
    if command -v curl >/dev/null 2>&1; then
        mkdir -p "$PIPER_DIR"
        if curl -fSL "$PIPER_URL" | tar xz -C "$PIPER_DIR" --strip-components=1; then
            chmod +x "$PIPER_BIN"
            echo "  [OK] Piper binary indirildi ($PIPER_BIN)"
        else
            echo "  [UYARI] Piper indirilemedi — espeak-ng fallback kullanılacak."
            echo "           Elle kurulum: curl -fSL $PIPER_URL | tar xz -C piper/ --strip-components=1"
        fi
    else
        echo "  [UYARI] curl yok — Piper indirilemedi. espeak-ng fallback kullanılacak."
    fi
fi

echo
echo "══════════════════════════════════════════"
if [ -n "$ATLANAN" ]; then
    echo "Kurulum tamamlandı. ATLANAN paketler (hata DEĞİL; ilgili özellik"
    echo "uygulama içinde zarifçe devre dışı kalıyor):"
    for a in $ATLANAN; do echo "  - $a"; done
else
    echo "Kurulum tamamlandı — hiçbir paket atlanmadı."
fi
echo "Başlatmak için:  ./baslat.sh"
