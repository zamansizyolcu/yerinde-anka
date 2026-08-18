# YERINDE OS — final12.md Uygulama Raporu

ISO: `iso/yerinde/out/yerinde-2026.08.15-x86_64.iso` (19.7 GB)
SHA256: `19978c7afc3928173ecdb0382c3e6860564db49e26a229053a3ede0725379fed`
Paket: `yerinde-ai-assistant-1.2.0-2` — commit `57a2d60` (main, push yok)

## 1) LAUNCHER — EV KOPYASI ✓
`/usr/bin/yerinde` (paket içinde): SRC=/opt/yerinde-ai-assistant, DST=$HOME/.yerinde/app.
İlk çalıştırmada `cp -r "$SRC"/. "$DST"/`, ardından `PYTHONPATH="$DST/vendor:$PYTHONPATH"` ile
çalışır. config/memory/Arkaplanlar eve yazıldığından API anahtarı kaydı ve OLLAMA↔GEMINI geçişi
canlı+kurulu hiçbir izin hatası vermez. ISO'da doğrulandı.

## 2) GGUF ENJEKSİYONU + OLLAMA STORE ✓ (build-iso.sh --prep-only)
- `airootfs/usr/share/yerinde-modeller/` → Meta-Llama-3.1-8B-Instruct-Q6_K.gguf (6.6GB) +
  Qwen2.5-Coder-1.5B-Instruct-Q8_0.gguf (1.6GB), chmod 644, `ls -l` ile doğrulandı.
- Store, ayrı instance'ta (port 11435, OLLAMA_MODELS=$STAGING) Modelfile (FROM gguf) ile
  önceden üretildi → `airootfs/var/lib/ollama/models`. **Neden /usr/share/ollama değil:** ollama
  paketinin `/usr/share/ollama -> /var/lib/ollama` symlink'i varken oraya dizin yazılırsa
  mkarchiso'nun `cp -af` kopyası `cannot overwrite non-directory ... with directory` hatasıyla
  patlar. OLLAMA_MODELS=/usr/share/ollama/models, symlink ile store'u bulur.
- Doğrulandı (sfs içinden): manifest `llama3.1/latest` + `qwen2.5-coder/1.5b`, 9 blob, 7.7GB.
  Orphan raw-gguf blob'ları (create artığı, manifest'te referanssız 2 adet, ~8GB) silindi.
- `ollama.service.d/yerinde.conf`: `Environment="OLLAMA_MODELS=/usr/share/ollama/models"`
- `yerinde-ollama-setup` (755): sunucuyu 60sn bekler → model varsa çıkar → store read-only ise
  (touch testi başarısız) CANLI'da create ATLAR (tmpfs şişmez) → yazılabilirse GGUF'tan create.
- `yerinde-ollama-setup.service` (oneshot) + ollama.service, `multi-user.target.wants/`
  symlink'leri → CANLI ortamda da çalışır. Hepsi sfs'te doğrulandı.

## 3) PIP BAĞIMLILIK DOĞRULUĞU ✓ (belgelenmiş sapma)
- Sandbox pip testi kanıtladı: `google-genai --no-deps` kurulunca `import google.genai`
  KIRILIR (pydantic, google-auth, httpx, anyio, tenacity, websockets, distro, sniffio,
  typing-extensions piper-tts/faster-whisper'dan GELMEZ). Bu yüzden maddedeki `--no-deps`
  yalnızca pyaudio/ollama/sounddevice/numpy için; **google-genai deps ile** kurulur (PKGBUILD
  içinde yorumla belgelendi).
- Build çıktısı: `VENDOR OK: onnxruntime + ctranslate2 doğrulandı` (yoksa exit 1).

## 4) PIPER TÜRKÇE SES GARANTİSİ ✓
- voices/ içinde dfki/fahrettin/fettah onnx zaten var → build'de indirme tetiklenmedi.
- PKGBUILD'e güvence eklendi: voices'da `*.onnx` yoksa rhasspy lessya medium (.onnx+.onnx.json)
  best-effort indirilir. Build çıktısı: `PIPER OK: voices/ içinde Türkçe ses zaten var`.
- `offline_voice_choice: "auto"` zaten varsayılan.

## 5) STT ÇİFT GÜVENCE ✓ (hazırdı, değişiklik gerekmedi)
faster-whisper birincil + pakete gömülü vosk-model tam çevrimdışı yedek; stt_engine hatasında
çökme yok. main.py'de doğrulandı.

## 6) GEMINI LIVE HOPARLÖR ✓ (hazırdı)
`_play_audio` zaten 3 kademeli: pyaudio 24000 → except 48000+np.repeat(x2) → except
`aplay -q -f S16_LE -r 24000 -c 1`. packages.x86_64 satır 1'de `alsa-utils` zaten var.

## 7) SUDO + KAPASİTE ✓
- `airootfs/etc/sudoers.d/wheel` (%wheel ALL=(ALL) ALL, 440, root:root) — sfs'te doğrulandı.
- users.conf defaultGroups `wheel` içeriyor (değişiklik gerekmedi).
- partition.conf `requiredStorage: 40` eklendi.

## 8) PAKET + BUILD ✓
- pkgrel 1→2; `makepkg -f` OK; iki repo'ya (`yerinde-repo` git + ISO'nun kullandığı
  `yerinde-project/repo/x86_64`) kopyalandı, `repo-add` yapıldı; git commit `57a2d60` (push yok).
- İlk build denemesi geo.mirror'da linux-firmware-* indirmesi çok yavaş olduğundan
  "Operation too slow" ile düştü; eksik firmware paketleri cache'e çekildi, tekrar başarılı.
- mkarchiso OK: pacstrap 970 paket, airootfs.sfs (394bin dosya, 19.2GB), ISO 19.7GB, `Done!`.
- sfs içinden doğrulandı: store, gguflar, setup birimleri, symlink, launcher,
  `pacman -r sfs -Q` → yerinde-ai-assistant 1.2.0-2 + ollama 0.32.13-1.

## 9) TEST LİSTESİ (donanımda çalıştırılacak)
1. **CANLI**: `ollama list` → llama3.1 + qwen2.5-coder:1.5b (2 model); `yerinde` → Ollama doğal
   Türkçe yanıt + Piper konuşur; Gemini Live hoparlörden duyulur (hızlı yedeklerde de);
   `mic_test` whisper/vosk ile sonuç verir (yoksa internet veya vosk yedeği devrede).
2. **KURULU (46GB disk, requiredStorage 40)**: aynı testler + AYARLAR'dan OLLAMA→GEMINI geçişi
   hatasız kaydolur ve bağlanır (launcher ev kopyası sayesinde izin hatası yok).
3. **UEFI/MBR boot regresyonu yok** (grub+syslinux konfigürasyonu değişmedi).
