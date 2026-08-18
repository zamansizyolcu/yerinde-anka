# YERINDE AI ASİSTAN — NÜKLEER DÜZELTME (v1.1.0)

Mevcut sorunlar:
1. Kurulu sistemde Gemini çalışmıyor (google-genai/vendor eksik).
2. Ollama modelleri ISO'da ama servis başlamıyor/model görünmüyor.
3. Whisper/Piper yüklü değil (STT/TTS çalışmıyor).
4. İzin hataları devam ediyor.

HEDEF: Tek seferde tüm bağımlılıkları, modelleri ve servisleri ISO'ya gömüp çalışır hale getirmek.

## 1. PKGBUILD — BAĞIMLILIKLARI ZORLA KUR (Vendor Fix)
~/yerinde-repo/yerinde-ai-assistant/PKGBUILD dosyasını güncelle.
`package()` fonksiyonundaki pip satırını şu şekilde değiştir (tüm bağımlılıkları ve alt bağımlılıkları çek):

  # Önce vendor dizinini temizle
  rm -rf "$pkgdir/opt/yerinde-ai-assistant/vendor"
  
  # google-genai ve TÜM alt bağımlılıklarını (httpx, pydantic vb.) kur
  # faster-whisper ve piper-tts'i de ekle
  pip install --target="$pkgdir/opt/yerinde-ai-assistant/vendor" \
    google-genai \
    faster-whisper \
    piper-tts \
    sounddevice \
    numpy \
    pyaudio \
    ollama \
    opencv-python \
    psutil \
    pillow

  # NOT: --no-deps KALDIRILDI. Alt bağımlılıklar gelmezse google-genai çalışmaz.

## 2. OLLAMA — SYSTEMD VE MODEL YOLLARI (Garanti Başlatma)
GGUF dosyaları ISO'da ama Ollama onları görmüyor. İki kritik düzeltme:

A) airootfs/etc/systemd/system/ollama.service dosyasını oluştur (veya güncelle):
   [Unit]
   Description=Ollama Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/ollama serve
   User=ollama
   Group=ollama
   Restart=always
   RestartSec=3
   Environment="OLLAMA_HOST=0.0.0.0"
   # Modellerin nerede olduğunu Ollama'ya söyle
   Environment="OLLAMA_MODELS=/usr/share/ollama/models"

   [Install]
   WantedBy=default.target

B) airootfs/usr/lib/sysusers.d/ollama.conf (Kullanıcı oluşturma):
   u ollama 780 "Ollama User" /usr/share/ollama

C) airootfs/usr/lib/tmpfiles.d/ollama.conf (Dizin izinleri):
   d /usr/share/ollama 0755 ollama ollama -
   d /usr/share/ollama/models 0755 ollama ollama -

D) Build sırasında modelleri kopyalarken SAHİPLİĞİ değiştir:
   # Mevcut kopyalama komutundan sonra:
   chown -R 780:780 "$MODEL_DIR"

## 3. İLK AÇILIŞ — SERVISI ZORLA BAŞLAT
airootfs/usr/bin/yerinde-first-run scriptini güncelle:

#!/bin/bash
# 1. Ollama kullanıcısı ve dizinleri hazır mı kontrol et
id ollama &>/dev/null || useradd -r -u 780 -d /usr/share/ollama -s /bin/false ollama
mkdir -p /usr/share/ollama/models
chown -R ollama:ollama /usr/share/ollama

# 2. Servisi etkinleştir ve başlat
systemctl enable --now ollama.service

# 3. Modellerin yüklendiğini doğrula (ISO'dan geldikleri için hemen görünmeli)
sleep 2
if ! ollama list | grep -q llama3.1; then
   zenity --warning --text="Ollama modelleri henüz yüklenmedi. Biraz bekleyin..."
fi

exit 0

## 4. UYGULAMA YOLU (PYTHONPATH Fix)
~/yerinde-ai-assistant/PKGBUILD içindeki başlatıcı scripti (yerinde) güncelle:

cat > "$pkgdir/usr/bin/yerinde" <<'LAUNCHER'
#!/bin/bash
cd /opt/yerinde-ai-assistant
# Vendor dizinini PYTHONPATH'in EN BAŞINA koy (sistem paketlerinden önce gelsin)
export PYTHONPATH="/opt/yerinde-ai-assistant/vendor:$PYTHONPATH"
# Hata ayıklama için logla (sorun devam ederse buraya bakacağız)
exec python3 main.py "$@" 2>> /tmp/yerinde-error.log
LAUNCHER

## 5. PAKET SÜRÜMÜ VE REBUILD
- pkgver=1.1.0 yap.
- makepkg -si
- repo-add ../yerinde.db.tar.zst yerinde-ai-assistant-1.1.0-1-x86_64.pkg.tar.zst
- git add . && git commit -m "fix: nuclear deps + ollama systemd + whisper/piper"
- ISO rebuild (setsid + log)

## 6. RAPOR VE TEST
- Rapor: vendor/ klasör boyutu (büyük olmalı), ollama.service durumu.
- Test Checklist'i:
  1) Kurulu sistemde `yerinde` -> UI açılsın.
  2) AYARLAR -> MODEL: GEMINI -> API anahtarı gir -> Bağlansın (hata yok).
  3) AYARLAR -> MODEL: OLLAMA -> `ollama list` terminalde çalışsın -> llama3.1 görünsün.
  4) "Merhaba" de -> Whisper (faster-whisper) ile dinlesin -> Llama3.1 cevap versin.
  5) Sesli yanıt -> Piper veya Sistem TTS ile gelsin.