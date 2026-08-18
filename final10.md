# YERINDE AI ASİSTAN — MEVCUT GGUF MODELLERİYLE ISO'YA GÖMME (FİNAL)

Kaynak asistan klasörü: /home/yerinde/yerinde-ai-assistant/
GGUF modelleri (ZATEN İNDİRİLMİŞ, İNTERNETTEN ÇEKME):
  - /home/yerinde/yerinde-project/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf (~6GB)
  - /home/yerinde/yerinde-project/Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf (~1.6GB)
Hedef: Yerinde OS ISO'suna yerinde-ai-assistant paketi + Ollama modelleri gömülü

## 1. PAKET OLUŞTURMA (yerinde-ai-assistant)
~/yerinde-repo/yerinde-ai-assistant/PKGBUILD:

pkgname=yerinde-ai-assistant
pkgver=1.0.0
pkgrel=1
pkgdesc="YERINDE — Türkçe sesli AI asistan (Ollama çevrimdışı + Gemini bulut)"
arch=('x86_64')
license=('GPL3')
depends=(
  'python>=3.11'
  'tk'
  'portaudio'
  'ffmpeg'
  'python-opencv'
  'python-psutil'
  'python-pillow'
  'python-pip'
  'ollama'
)
optdepends=(
  'coqui-tts: XTTS-v2 ses klonlama (~2GB, opsiyonel)'
  'whisper: çevrimdışı konuşma tanıma (büyük, opsiyonel)'
  'vosk: hafif çevrimdışı STT alternatifi (opsiyonel)'
)
# DİKKAT: Kaynak klasörün yeni adı 'yerinde-ai-assistant'
source=("yerinde-ai-assistant::file:///home/yerinde/yerinde-ai-assistant")
sha256sums=('SKIP')

package() {
  cd "$srcdir/yerinde-ai-assistant"
  
  # Python dosyalarını /opt/yerinde-ai-assistant'a kur
  install -dm755 "$pkgdir/opt/yerinde-ai-assistant"
  cp -r *.py core actions backend memory voices SFX Arkaplanlar \
        config Fonts Icon model-egitimi pico-devre-atolyesi \
        robotik-simulator satranc scratch_library_assets \
        video-atolyesi vosk-model yerinde-donanim-atolyesi \
        yerinde-kodlama-araci 3b-tasarim-studyosu akis-semasi \
        bilisim-robotik-atolyesi blockly-games carkifelek cin-damasi \
        resim-pdf-atolyesi robot-tasarim-atolyesi \
        "$pkgdir/opt/yerinde-ai-assistant/"
  
  # YOLO modeli
  cp yolov11n.pt "$pkgdir/opt/yerinde-ai-assistant/" 2>/dev/null || true
  
  # Başlatıcı script
  install -dm755 "$pkgdir/usr/bin"
  cat > "$pkgdir/usr/bin/yerinde" <<'LAUNCHER'
#!/bin/bash
cd /opt/yerinde-ai-assistant
export PYTHONPATH="/opt/yerinde-ai-assistant:$PYTHONPATH"
exec python3 main.py "$@"
LAUNCHER
  chmod +x "$pkgdir/usr/bin/yerinde"
  
  # Masaüstü kısayolu
  install -dm755 "$pkgdir/usr/share/applications"
  cat > "$pkgdir/usr/share/applications/yerinde-ai.desktop" <<'DESKTOP'
[Desktop Entry]
Name=YERINDE AI Asistan
Comment=Türkçe sesli yapay zeka asistanı
Exec=yerinde
Icon=yerinde
Terminal=false
Type=Application
Categories=Utility;AI;
DESKTOP
  
  # İkon
  install -dm755 "$pkgdir/usr/share/icons/hicolor/256x256/apps"
  cp Icon/yerinde-icon-256.png \
     "$pkgdir/usr/share/icons/hicolor/256x256/apps/yerinde.png" 2>/dev/null || true
}

## 2. GGUF MODELLERİNİ OLLAMA FORMATINA ÇEVİR VE ISO'YA GÖM
Build sırasında mevcut GGUF dosyalarını Ollama Modelfile ile paketle:

MODEL_DIR="$HOME/yerinde-project/iso/yerinde/airootfs/usr/share/ollama/models"
mkdir -p "$MODEL_DIR"

# Llama 3.1 8B
cat > /tmp/Modelfile.llama <<'MODELFILE'
FROM /home/yerinde/yerinde-project/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf
PARAMETER temperature 0.7
PARAMETER num_ctx 4096
SYSTEM "Sen YERINDE'sin — Türkçe konuşan, yardımcı bir AI asistanısın. Kısa ve net yanıtlar ver."
MODELFILE

ollama create llama3.1 -f /tmp/Modelfile.llama
cp -r ~/.ollama/models/manifests/registry.ollama.ai/library/llama3.1 "$MODEL_DIR/manifests/registry.ollama.ai/library/" 2>/dev/null || true
cp -r ~/.ollama/models/blobs "$MODEL_DIR/" 2>/dev/null || true

# Qwen2.5 Coder 1.5B
cat > /tmp/Modelfile.qwen <<'MODELFILE'
FROM /home/yerinde/yerinde-project/Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf
PARAMETER temperature 0.2
PARAMETER num_ctx 8192
SYSTEM "Sen bir kod asistanısın. Python, Blender bpy, FreeCAD macro kodu üretirsin. Sadece kod bloğunu döndür, açıklama ekleme."
MODELFILE

ollama create qwen2.5-coder:1.5b -f /tmp/Modelfile.qwen
cp -r ~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5-coder "$MODEL_DIR/manifests/registry.ollama.ai/library/" 2>/dev/null || true
cp -r ~/.ollama/models/blobs "$MODEL_DIR/" 2>/dev/null || true

# profiledef.sh'de file_permissions'a ekle:
["/usr/share/ollama/models"]="0:0:755"

## 3. PACKAGES.X86_64'A EKLE
iso/yerinde/packages.x86_64:
yerinde-ai-assistant
ollama
python-opencv
python-psutil
python-pillow
portaudio
ffmpeg

## 4. İLK AÇILIŞ SCRIPTİ
airootfs/usr/bin/yerinde-first-run:
#!/bin/bash
systemctl enable --now ollama
sleep 3

# Modellerin yüklü olduğunu doğrula
if ! ollama list | grep -q llama3.1; then
  zenity --error --text="Ollama modeli bulunamadı — ISO eksik olabilir."
fi

exit 0

airootfs/etc/xdg/autostart/yerinde-first-run.desktop:
[Desktop Entry]
Name=YERINDE İlk Kurulum
Exec=/usr/bin/yerinde-first-run
OnlyShowIn=KDE
Type=Application

## 5. VARSAYILAN AYARLAR
airootfs/etc/skel/.yerinde/config.json:
{
  "model_provider": "ollama",
  "ollama_model": "llama3.1",
  "ollama_coder_model": "qwen2.5-coder:1.5b",
  "v3_core_enabled": true,
  "ui_theme": "krem",
  "orb_style": "anka_baloncuk"
}

## 6. REPO + BUILD
cd ~/yerinde-repo/yerinde-ai-assistant
makepkg -si
repo-add ../yerinde.db.tar.zst yerinde-ai-assistant-1.0.0-1-x86_64.pkg.tar.zst
git add . && git commit -m "yerinde-ai-assistant v1.0.0 + mevcut GGUF modelleri"

cd ~/yerinde-project/iso/yerinde
sudo rm -rf work out
setsid bash -c 'mkarchiso -v -w work -o out . > /tmp/opencode/build.log 2>&1' &

## 7. RAPOR
- Paket boyutu
- ISO boyutu (beklenti: ~9-10GB)
- Kopyalanan modeller: llama3.1 (~6GB), qwen2.5-coder:1.5b (~1.6GB)
- Test checklist'i:
  1) Kurulu sistemde `yerinde` komutu çalışmalı
  2) Menüde "YERINDE AI Asistan" görünmeli
  3) Ollama modu: `ollama serve` otomatik başlamalı
  4) `ollama list` → llama3.1 + qwen2.5-coder:1.5b görünmeli
  5) UI açılsın → "Merhaba" de → llama3.1 yanıt vermeli
  6) "Blender'da küre çiz" de → qwen2.5-coder kod üretmeli
  7) İnternet yokken bile çalışmalı (çevrimdışı test)