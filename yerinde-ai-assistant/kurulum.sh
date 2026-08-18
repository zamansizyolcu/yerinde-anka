#!/usr/bin/env bash
# YERINDE — CachyOS / Yerinde ANKA (Arch Linux) kurulum betiği
# final37 §1: pip/venv YOK — yalnızca sistem paketleri (pacman).
# Bu betik tıkla-kur (yerinde-asistan-kur) tarafından SARICI olarak
# çağrılır: pacman paketi yoksa yerel klasörden/clone'dan bu betik koşar.
set -e

echo "══════════════════════════════════════════"
echo "  YERINDE — Kurulum (sistem paketleri)"
echo "══════════════════════════════════════════"

# final24.md §4 + aifinal.md §1 + final37 §1: numpy/Pillow/pyaudio gibi tüm
# python kütüphaneleri SİSTEM paketi olarak kurulur (aşağıda [2/3] adımında
# tek liste halinde; wheel'siz kaynak derleme baştan engellenir). ydotool:
# Wayland klavye/fare kontrolü (aifinal.md §2) — [1/3] PKGS listesinde.

# ══ Wayland girdi altyapısı (aifinal.md §2): ydotool daemon + uinput ════════
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
echo "[1/3] Gerekli sistem paketleri kontrol ediliyor (pacman)..."
# pipewire-pulse: 'parec' sağlar — sounddevice/PortAudio sessiz kalırsa
#   (hata vermeden mikrofon verisi göndermezse) MicStream buna otomatik
#   düşer. wtype/ydotool: Wayland oturumunda klavye/fare kontrolü için
#   xdotool/pyautogui işe yaramaz; bu ikisi gerçek Wayland araçlarıdır.
#   grim: Wayland'de ekran görüntüsü yakalama (mss çalışmaz) için gereklidir.
PKGS="python tk portaudio pipewire-pulse xclip wl-clipboard espeak-ng ffmpeg xdotool wtype ydotool grim"
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
echo "[2/3] Python kütüphaneleri SİSTEM paketi olarak kontrol ediliyor..."
# final37 §1: venv + pip YOLU TAMAMEN KALDIRILDI. Kök neden: pyautogui'nin
# pyrect bağımlılığı sdist olarak pip build-isolation'da derleniyor ve
# temiz sistemlerde çöküyordu. Python kütüphaneleri ARTIK yalnızca pacman
# paketlerinden gelir (önceden derli, hiçbir sdist derlemesi YOK).
# Depolarda OLMAYAN kütüphaneler (google-genai, piper-tts, faster-whisper,
# pdfplumber, python-docx, python-pptx, sounddevice, dvrip, ultralytics,
# pyautogui) uygulama tarafından ZARİFÇE atlanır: pyaudio mikrofonu yeter,
# TTS espeak-ng'ye düşer, kamera önizleme modunda kalır, Gemini/genai
# seçeneği pas geçer (main.py importları try/except korumalı).
# NOT: pacman paketi yoluyla kurulanlarda (yerinde-ai-assistant) bu
# kütüphanelerin hepsi vendor/ içinde hazır gelir.
PYPKGS="python-numpy python-pillow python-opencv python-pyaudio portaudio \
python-psutil python-requests python-pyperclip python-mss python-selenium \
python-vosk python-av python-openpyxl python-websocket-client"
PYMISSING=""
for p in $PYPKGS; do
    pacman -Qi "$p" >/dev/null 2>&1 || PYMISSING="$PYMISSING $p"
done
if [ -n "$PYMISSING" ]; then
    echo "Eksik python paketleri bulundu:$PYMISSING"
    sudo pacman -S --needed $PYMISSING || \
        echo "[UYARI] Bazı paketler kurulamadı (depolar erişilemiyor olabilir) — ilgili özellikler zarifçe devre dışı kalır."
else
    echo "Tüm python kütüphaneleri sistemde kurulu."
fi
# Eski kurulumlardan kalmış venv varsa kaldır (artık kullanılmıyor).
rm -rf venv

echo
echo "[3/3] Yapılandırma dosyası hazırlanıyor..."
mkdir -p config
if [ ! -f config/api_keys.json ]; then
    cp config/api_keys.example.json config/api_keys.json
    echo "config/api_keys.json oluşturuldu — Gemini API anahtarını programın"
    echo "AYARLAR panelinden girebilir, ya da bu dosyayı elle düzenleyebilirsin."
fi

echo
echo "Kurulum tamamlandı! Başlatmak için:  ./baslat.sh"
