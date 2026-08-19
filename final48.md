# YERINDE ASISTAN final50 — TEK PROMPT
HEDEF: /home/yerinde/yerinde-project/yerinde-ai-assistant
KURAL: ISO'ya DOKUNMA (gerek yok); grep/ls doğrulamalı; Türkçe
rapor; VM testi YOK; sessiz bekleme YASAK.

## §1 SES LİSTESİ: 'str' object has no attribute 'get' KÖK DÜZELTME
1) grep -n "Ses listesi alınamadı" → try bloğunu bul, rapora bas
2) KÖK: voices girdileri string iken kod dict.get(...) çağırıyor.
   DÜZELT (dosya-adı bazlı ayrıştırma):
   - glob voices/*.onnx → eş <ad>.onnx.json'ı json.load ile oku
   - eleman dict olsun: {name, path, config, sample_rate}
     (sample_rate = meta.get('audio',{}).get('sample_rate',22050))
   - UI seçici etiketi: "{name} ({sample_rate}Hz)"
   - seçim config.json'da kalıcı; başlangıçta geri yükle
3) TTS zinciri (ilk çalışan kazanır):
   a) venv piper Python API'si (piper-tts pip'te VAR — seshata
      kanıtı: piper/voice.py) → PiperVoice.load(path, config)
   b) ./piper/piper binary
   c) SON çare sistem TTS + Türkçe uyarı
4) DOĞRULA: py_compile + headless test:
   load_voices() → "3 model: [isimler]" raporda
5) UI test maddesi: seçicide 3 model görünür, seçimde ERR YOK,
   seçilen modelle doğal Türkçe ses

## §2 OLLAMA HANG: llama3.1 "biraz sürebilir"de KALMIYOR
1) pull ÖNCESİ servis: systemctl is-active ollama ||
   sudo systemctl enable --now ollama
2) pull ÇIKTISI CANLI (subprocess capture YOK, stdout inherit)
   → kullanıcı gerçek progress'i GÖRÜR (4.7GB gerçekten iniyor
   olabilir; yutulan çıktı "takıldı" hissi veriyor)
3) ekrana not: "llama3.1 ~4.7GB — iniyor; atlamak için Ctrl+C"
   Ctrl+C yakala → o modeli ATLA + Türkçe bilgi + DEVAM
4) pull sonrası DOĞRULA: ollama list | grep <model> → yoksa
   uyarı + devam (script ÖLMEZ)
5) config: offline_models = [qwen2.5-coder:1.5b, llama3.1]
   (sıralı kur; qwen hızlı, llama opsiyonel-ağır)

## §3 PIPER + VOICES SELF-CONTAINED (aynen korunur)
- voices/*.onnx + *.onnx.json REPODA (3 model) → git ls-files kanıtı
- .gitignore: piper/  (binary GitHub'a girmez)
- kurulum.sh: [ -x ./piper/piper ] || release tar.gz → ./piper/
  (curl başarısızsa venv piper API'sine düş + uyarı)
- TTS yolları BASE_DIR-bağıl (./piper/piper, ./voices);
  /usr/local gibi global yol YASAK

## §4 YAYIN + RAPOR + TEST
- git add -A && commit -m "ses listesi kök düzeltme + ollama canlı
  progress" && git push -u origin main (KULLANICI İZNİ VAR)
- Kanıtlar: "Ses listesi" bloğu ÖNCE→SONRA diff; load_voices 3
  model; kurulum.sh stdout-inherit satırı; git ls-files voices;
  ls-remote 200
- Kullanıcı testi:
  1) seçicide 3 model + doğal ses + ERR YOK
  2) tıkla-kur "e" → qwen hızlı kurulur; llama3.1 CANLI progress
     ile iner VEYA Ctrl+C ile temiz atlanır
  3) ISO sha256 DEĞİŞMEZ (ISO'ya dokunulmadı)