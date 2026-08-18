# final27 EK — TIKLA-KUR AKILLI MESAJ + ERİŞİM YOLLARI
HEDEF DOSYA: iso/yerinde/airootfs/usr/local/bin/yerinde-asistan-kur

## 1) MESAJ AYRIŞTIR (yanıltıcı sabit metni KALDIR)
- "İnternet: VAR/YOK" AYRI satır
- pacman "hedef bulunamadı" → "[yerinde] reposu pacman.conf'ta
  yok veya yayında değil" yaz (ASLA "internet yok" deme)
- yerel arama sonucu AYRI satır
- final hata = gerçek durumların birleşimi

## 2) OTOMATİK REPO TANIMI
[yerinde] pacman.conf'ta yoksa ekle:
SigLevel = Never
Server = http://10.0.2.2:8000     (host LAN: python -m http.server)
# GitHub Pages 404MB paketi taşıyamaz (100MB limit) → LAN öncelikli
sonra sudo pacman -Sy

## 3) GIT CLONE FALLBACK (internet VAR + pacman/yerel YOKSA)
git clone https://github.com/zamansizyolcu/yerinde-ai-assistant
→ cd yerinde-ai-assistant && ./kurulum.sh
(kamu yolu = kaynak repo; pacman yolu = LAN)

## 4) DOĞRULA
- bash -n yerinde-asistan-kur → syntax OK
- grep: 3 ayrı mesaj satırı VAR; "İnternet yok + yerel" sabit metni YOK

## 5) REGRESYON
Kalan akış aynen: kuruluysa başlat, "modeller kurulsun mu (e/h)",
Enter → yerinde. Başka hiçbir ISO dosyasına DOKUNMA.