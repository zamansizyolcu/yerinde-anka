#!/usr/bin/env bash
# YERİNDE - Kendi Modelini Eğitme: sanal ortam (venv) kurulumu (Linux —
# Pardus / CachyOS / OrangePi 5 Plus)
# Bu klasörde bir terminal açıp şunu çalıştır:  bash kurulum_linux.sh
# Bir kere çalıştırman yeterli.

set -e
cd "$(dirname "$0")"

PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" &> /dev/null; then
    echo "HATA: python3/python bulunamadı. Python 3.10+ kurulu olduğundan emin ol."
    exit 1
fi

echo "=== Sanal ortam (venv) oluşturuluyor: venv/ ==="
"$PYTHON_BIN" -m venv venv

echo "=== Sanal ortam etkinleştiriliyor ==="
source venv/bin/activate

echo "=== Kütüphaneler kuruluyor (bu birkaç dakika sürebilir) ==="
pip install --upgrade pip
pip install -r requirements-egitim.txt

echo ""
echo "=== llama.cpp kontrol ediliyor (GGUF dönüşümü için gerekli) ==="
if [ -d "llama.cpp" ]; then
    echo "llama.cpp zaten mevcut, klonlama atlanıyor."
elif ! command -v git &> /dev/null; then
    echo "UYARI: 'git' bulunamadı, llama.cpp klonlanamadı."
    echo "Dağıtımına göre kur, ör:"
    echo "    sudo pacman -S git      (CachyOS/Arch tabanlı)"
    echo "    sudo apt install git    (Pardus/Debian tabanlı)"
    echo "sonra bu scripti tekrar çalıştır - ya da git kurulduktan sonra elle:"
    echo "    git clone https://github.com/ggerganov/llama.cpp.git"
else
    echo "llama.cpp klonlanıyor (internet gerekir, bir kereye mahsus)..."
    if git clone --depth 1 https://github.com/ggerganov/llama.cpp.git; then
        echo "llama.cpp dönüşüm gereksinimleri kuruluyor..."
        pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
    else
        echo "UYARI: llama.cpp klonlanamadı - internet bağlantını kontrol et."
    fi
fi

cat << 'EOF'

============================================================
 KURULUM TAMAMLANDI.
 Bundan sonra, bu klasörde YENİ bir terminal açtığında önce:
     source venv/bin/activate
 çalıştır, sonra scripti çalıştırabilirsin, örnek:
     python egitim_ve_gguf_donustur.py --llama-cpp-path ./llama.cpp
============================================================
EOF
