#!/usr/bin/env bash
# YERİNDE - Kendi Modelini Eğit (GGUF'a Dönüştür) - TEK KOMUTLA ÇALIŞTIR
# Bu klasörde: bash egitim_baslat.sh
# Önce 'kurulum_linux.sh' çalıştırılmış olmalı (sanal ortam + llama.cpp hazır).

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "HATA: Sanal ortam (venv) bulunamadı."
    echo "Önce 'bash kurulum_linux.sh' çalıştır, o bitince bunu tekrar çalıştır."
    read -p "Kapatmak için Enter'a bas..."
    exit 1
fi

source venv/bin/activate

LLAMA_ARG=""
if [ -d "llama.cpp" ]; then
    LLAMA_ARG="--llama-cpp-path llama.cpp"
else
    echo "UYARI: llama.cpp bulunamadı - sadece eğitim yapılacak, GGUF'a"
    echo "çevrilmeyecek. GGUF için önce 'bash kurulum_linux.sh'yi tekrar"
    echo "çalıştır (llama.cpp'yi otomatik klonlar)."
fi

echo ""
echo "=== Eğitim + GGUF dönüşümü başlıyor ==="
echo "(Bu işlem veri boyutuna ve bilgisayarına göre dakikalar-saatler sürebilir)"
echo ""
python egitim_ve_gguf_donustur.py $LLAMA_ARG

echo ""
echo "============================================================"
echo " BİTTİ. Yukarıdaki çıktıda hata var mı kontrol et."
echo " Başarılıysa, çıktılar 'cikti/' klasöründe (Modelfile dahil)."
echo "============================================================"
read -p "Kapatmak için Enter'a bas..."
