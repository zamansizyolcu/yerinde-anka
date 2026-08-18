# YERINDE AI Asistanı

## Kurulum (Yerinde ANKA)

En kolay yol: Yerinde ANKA masaüstündeki **"YERINDE Asistanı Kur"** kısayoluna
tıkla (`/usr/local/bin/yerinde-asistan-kur`). İnternet varsa paket deposundan
kurar; internet yoksa İndirilenler'deki bu klasörü imza bazlı bulup
`kurulum.sh`'i çalıştırır.

Elle kurulum:

```bash
# ön adım (aifinal.md §1): numpy/pyaudio SİSTEMden → pip asla derleme denemez
sudo pacman -S --needed python-numpy python-pillow python-opencv \
    python-pyaudio portaudio ydotool
./kurulum.sh
```

Not: numpy/pyaudio PIPEX/derleme hatası alırsan pip'e düşme — numpy/Pillow/
pyaudio Yerinde ANKA'da sistem paketi olarak gelir (`python -m venv
--system-site-packages` sayesinde venv bunları görür; kurulum.sh eski venv'i
`rm -rf venv` ile temizleyip yeniden kurar). Hata mesajı görürsen:
`sudo pacman -S python-numpy python-pyaudio portaudio`

## Wayland klavye/fare (ydotool)

Wayland oturumunda pyautogui/xdotool çalışmaz — YERİNDE `ydotool` kullanır
(`core/input_backend.py` birleşik arka uç: tuş, metin, tıklama, kaydırma).

Kurulum (kurulum.sh Wayland'da bunları otomatik yapar):

```bash
sudo pacman -S ydotool
sudo systemctl enable --now ydotoold
sudo usermod -aG uinput,input $USER   # sonra OTURUMU YENİDEN AÇ
echo 'uinput' | sudo tee /etc/modules-load.d/uinput.conf
```

Kontrol: `systemctl status ydotoold` • `ls /dev/uinput` • `groups $USER`
X11 oturumlarında xdotool yolu aynen korunur.

## Varsayılan model: Gemini

Kayıtlı tercihin yoksa asistan GEMINI ile açılır. Gemini API anahtarı
girilmemişse açılışta anahtar giriş ekranı gelir — Ollama'ya sessizce
düşülmez; Ollama'yı yine de MODEL düğmesinden elle seçebilirsin.
