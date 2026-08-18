# YERINDE OS — AI MASTER PROMPT (v3 FİNAL)
Hedef: CANLI ve KURULU sistemde Gemini + Ollama + Piper + Whisper
hatasız; izin hatası yok; modeller ISO'da.

## 1) LAUNCHER: EV KOPYASI (izin hatasının kökü)
PKGBUILD /usr/bin/yerinde:
#!/bin/bash
SRC=/opt/yerinde-ai-assistant
DST="$HOME/.yerinde/app"
if [ ! -f "$DST/main.py" ]; then mkdir -p "$DST"; cp -r "$SRC"/. "$DST"/; fi
cd "$DST"
export PYTHONPATH="$DST/vendor:$PYTHONPATH"
exec python3 main.py "$@"
(config/memory/Arkaplanlar eve yazılır → API anahtarı kaydı ve
OLLAMA↔GEMINI geçişi asla izin hatası vermez; canlı+kurulu.)

## 2) GGUF ENJEKSİYONU + OLLAMA STORE (build'de, doğrulamalı)
- mkdir -p airootfs/usr/share/yerinde-modeller
- cp ~/yerinde-project/Meta-Llama-3.1-8B-Instruct-Q6_K.gguf ve
  Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf oraya; chmod 644
- cp sonrası ls -l ile DOĞRULA; 2 dosya yoksa build FAIL.
- Ollama store'u BUILD makinesinde önceden üret (live RAM'ine
  yazılmasın): OLLAMA_MODELS=$STAGING ile ollama serve başlat,
  iki modeli Modelfile (FROM gguf) ile create et, serve kapat,
  $STAGING içeriğini airootfs/usr/share/ollama/ altına kopyala,
  ls ile manifest+blob DOĞRULA (yoksa FAIL).
- airootfs/etc/systemd/system/ollama.service.d/yerinde.conf:
  [Service] Environment="OLLAMA_MODELS=/usr/share/ollama/models"
- airootfs/usr/bin/yerinde-ollama-setup (755): sunucuyu bekle;
  ollama list'te model yoksa VE store yazılabilirse
  (touch testi) create et; live'da read-only store'da create
  DENEMEZ (tmpfs şişmez).
- yerinde-ollama-setup.service oneshot + ollama.service ile
  birlikte airootfs multi-user.target.wants/ sembolik linkleri
  (CANLI ortamda da çalışır).

## 3) PIP: BAĞIMLILIK DOĞRULUĞU
pip install --target=vendor (BAĞIMLILIKLI): piper-tts faster-whisper
pip install --no-deps --target=vendor: google-genai pyaudio ollama
sounddevice numpy
Build sonunda vendor'da onnxruntime ve ctranslate2 klasörlerini
DOĞRULA (yoksa FAIL).

## 4) PIPER TÜRKÇE SES GARANTİSİ
voices/ içinde *.onnx yoksa build'de indir:
rhasspy/piper-voices tr/tr_TR/lessya/medium (.onnx + .onnx.json)
Varsayılan offline_voice_choice "auto" (Piper'ı otomatik seçer).

## 5) STT: ÇİFT GÜVENCE
faster-whisper birincil (ilk kullanımda model indirir, internetle);
vosk-model/ pakete gömülü tam çevrimdışı yedek; stt_engine hata
verirse kullanıcıya anlaşılır mesaj (çökme yok).

## 6) GEMINI LIVE HOPARLÖR YEDEKLİ YOL (main.py _play_audio)
a) pya.open 24000 → b) except: 48000 + np.repeat(x2) →
c) except: aplay -q -f S16_LE -r 24000 -c 1 subprocess.
packages.x86_64 += alsa-utils

## 7) SUDO + KAPASİTE
- airootfs/etc/sudoers.d/wheel: %wheel ALL=(ALL) ALL (440)
- users.conf defaultGroups += wheel
- partition.conf requiredStorage: 40

## 8) PAKET + BUILD
pkgver=1.2.0; makepkg; repo-add; commit (push YOK);
ISO rebuild setsid+log; sha256.

## 9) RAPOR + TEST LİSTESİ
1) CANLI: ollama list → 2 model; yerinde → Ollama doğal Türkçe
   (Piper) konuşur; Gemini Live hoparlörden duyulur; mic_test
   whisper/vosk ile sonuç verir
2) KURULU (46GB): aynı testler + AYARLAR'dan OLLAMA→GEMINI geçişi
   hatasız kaydolur ve bağlanır
3) UEFI/MBR boot regresyonu yok