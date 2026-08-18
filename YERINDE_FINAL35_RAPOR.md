# YERINDE final35 — TÜM SESLİ KLAVYE/FARE KOMUTLARI "MASAÜSTÜNÜ GÖSTER" GİBİ

Tarih: 2026.08.18 (kullanıcı geri bildirimi: "masaüstünü göster çok iyi
çalıştı — tüm klavye ve fare sesli komut dizisi aynı şekilde çalışsın")

## 1) DBUS YEDEĞİ GENELLEŞTİ (actions/keyboard_control.py)

final33'te yalnız win_d'de olan kglobalaccel yedeği artık pencere
yönetimi kısayollarının TÜMÜNDE. Kısayol adları bu KDE 6.29 hostta
`allShortcutInfos` ile DOĞRULANDI + "Walk Through Windows" invoke ile
CANLI test edildi (method return):

| Sesli komut | kwin kısayolu | durum |
|---|---|---|
| masaüstünü göster | Show Desktop | final33 (kullanıcı doğruladı) |
| alt tab (pencereler arası) | Walk Through Windows | invoke canlı test ✓ |
| alt f4 (pencereyi kapat) | Window Close | allShortcutInfos ✓ |
| windows tab (genel görünüm) | Overview | allShortcutInfos ✓ |

Zincir (mesaj katmanı YDOTOOL_MISSING_TR DOKUNULMADI):
1) wtype → ydotool (mevcut yol, DOKUNULMADI)
2) başarısızsa → dbus kglobalaccel (yukarıdaki harita)
3) o da yoksa → ESKİ dürüst Türkçe mesaj

Genel kısayollar (enter, ctrl+t, kopyala, oklar, yazma…) dbus'a
eşlenemez — onlar için 2. madde devrede:

## 2) YDOTOOL SOKET EMNİYETİ (core/input_backend.py)

`run_ydotool()`: YDOTOOL_SOCKET unset ise `/run/ydotool.socket`
varsayılır. KLAVYE + FARE tüm ydotool çağrıları bu tek fonksiyondan
geçtiği için (mouse_control.py zaten delege — final kanıtı) tek satır
tüm fare/komut dizisini kapsar. Kullanıcı servisi kuran kurulumlar kendi
env'ini set ediyorsa dokunulmaz (setdefault).

## 3) KANITLAR

- py_compile: keyboard_control + input_backend + mouse_control OK
- grep: `_KGLOBALACCEL` haritası + `setdefault` satırı
- dbus canlı: Walk Through Windows invoke → method return
- Paket **yerinde-ai-assistant 2.0.0-2**: makepkg 7/7 doğrulama
  (SMOKE/VOICES/VENDOR/PRIVACY/LAUNCHER/DESKTOP/AUTOSTART OK);
  paket içi grep: _KGLOBALACCEL×6 + setdefault×1 ✓; repo-add OK
  (db: calamares-3.4.2-5 + asistan-2.0.0-2 + branding-1.2.0-17)

## 4) PUSH

- Asistan: **51595e1** → main (880f6f4..51595e1) ✓
- OS: **760813e** (asistan dosyaları + repo db + pkgrel) ✓
- ISO derlemesi GEREKMEDİ (asistan ISO'da yok; tıkla-kur clone/pacman
  yolları düzeltmeleri anında alır)

## 5) KULLANICI TESTİ

Canlı/kurulu sistemde sesle dene: "alt tab", "pencereyi kapat" (alt f4),
"genel görünüm" (win tab), "masaüstünü göster", "fareyi sağa oynat",
"ctrl t yaz" — ilkinde ydotool; o yoksa dbus (ilk dört) devralır.
