# YERINDE ASİSTAN — TEK PROMPT (kurulum + Wayland girdi + Gemini)
BAĞLAM: asistan reposu GitHub'da (zamansizyolcu/yerinde-ai-assistant).
Bu md ASİSTAN KLASÖRÜNDE çalıştırılır (requirements.txt + kurulum.sh
+ main.py buradaysa doğru dizindesin).
KURALLAR: Türkçe mesajlar; her adım doğrulamalı (py_compile/grep/ls);
config/api_keys.json GİZLİ kalır (.gitignore'da, commit EDİLMEZ).

## 1) KURULUM: VENV + SİSTEM PAKETLERİ (numpy/pyaudio kalıcı)
- kurulum.sh: venv'i ŞÖYLE kur:
  rm -rf venv
  python -m venv --system-site-packages venv
  (sistem paketleri venv'e görünür → pip derleme DENEMEZ)
- kurulum.sh pacman ön adımı:
  sudo pacman -S --needed python-numpy python-pillow \
    python-pyaudio portaudio ydotool || true
- requirements.txt:
  • numpy==1.26.4 YASAK → "numpy>=2" veya satır silinir
  • pyaudio satırı yorum: # pyaudio -> sistemden: python-pyaudio
- pip hatasında Türkçe fallback:
  "Derleme hatası (numpy/pyaudio): sudo pacman -S
   python-numpy python-pyaudio portaudio"
- README "Kurulum" bölümü güncelle

## 2) WAYLAND GİRDİ: ydotool BACKEND
- YENİ core/input_backend.py:
  • session = XDG_SESSION_TYPE (wayland/x11)
  • type_text: wayland+ydotool → ydotool type; değilse xdotool
  • key/combo: evdev haritası (enter=28 tab=15 esc=1 space=57
    ctrl=29 alt=56 shift=42 super=125 mute=113 vol+=115 vol-=114
    play=164) → wayland: ydotool key {c}:1 {c}:0; x11: xdotool
  • mouse: ydotool click 0xC0/0xC1/0xC2 + move -- dx dy
  • ydotool YOKSA Türkçe yol gösterici mesaj (eski sabit hata
    "Wayland ortamında çalışmamaktadır" YERİNE):
    "sudo pacman -S ydotool && sudo systemctl enable --now ydotoold
     && sudo usermod -aG uinput,input $USER → yeniden giriş"
- actions/type_text.py + mouse_control.py + keyboard_control.py
  bu yardımcıyı çağırsın (X11/xwayland yolu AYNEN korunur)
- kurulum.sh wayland bölümü:
  systemctl enable --now ydotoold; usermod -aG uinput,input;
  echo uinput > /etc/modules-load.d/uinput.conf; "yeniden giriş" notu
- README "Wayland klavye/fare" bölümü

## 3) VARSAYILAN MOD: GEMINI (Ollama DEĞİL)
- app_config.py / backend/model_router.py: kayıtlı kullanıcı tercihi
  YOKSA varsayılan model_provider = "gemini"
- config/api_keys.example.json: model_provider "gemini"
- açılışta Gemini anahtarı YOKSA → Gemini anahtar giriş ekranı
  (mevcut setup UI) göster; Ollama'ya SESSİZCE düşme
- Ollama manuel seçenek olarak KALSIN (MODEL düğmesi)
- DOĞRULA: grep ile "ollama" varsayılan ataması YOK (seçenek listesi hariç)

## 4) DOĞRULAMA
- python -m py_compile: core/input_backend.py + 3 eylem + app_config.py
- bash -n kurulum.sh
- grep: "Wayland ortamında çalışmamaktadır" YOK;
  varsayılan provider "gemini" kanıtı
- smoke: ydotool kuruluysa `ydotool type test` dene

## 5) COMMIT + PUSH (asistan reposu halka açık — push SERBEST)
git add -A
git commit -m "v2.1: system-site-packages venv + ydotool Wayland + Gemini varsayilan"
git push
Rapor: değişen dosyalar + grep kanıtları + push URL