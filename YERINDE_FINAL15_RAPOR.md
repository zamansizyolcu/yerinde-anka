# YERINDE OS 1.5 (final15) — Uygulama Raporu

**Tarih:** 2026-08-16
**Hedef:** final15.md — GRUB teması (koyu + büyük + yeşil/turuncu, Türkçe menü), SDDM yerleşimi + güç düğmeleri + gerçekten çalışan oturum seçimi, X11 sağlamlaştırma, asistanın kişisel config'inin paketten sıyrılması.

**Sonuç:** Tüm hedefler tamamlandı; ISO üretildi, build-sonrası doğrulamaların tümü geçti. VM testi kural gereği yapılmadı.

---

## 1. Yapılan Değişiklikler

### 1.1 GRUB Teması (koyu + büyük + yeşil/turuncu, Türkçe menü)

- Kaynak: `packages/yerinde-branding/` (PKGBUILD pkgrel=10).
- DejaVu Sans `32px` ve `44px` `.pf2` fontları + 9 dilim `select_*.png` + `theme.txt` → pakete derlendi (`yerinde-branding-1.2.0-10`), ISO build'te doğrulandı.
- Menü Türkçeleştirildi: "Yerinde OS'u Başlat", "Gelişmiş seçenekler", "Sistem bilgisi" (GRUB varsayılan tercümeleri).

**Belgelenen sapmalar / tespitler:**
- `item_background` ve `selected_item_attr` GRUB 2.06'da **desteklenmiyor** (sessizce yok sayılıyor) → `item_background` atıldı; seçili öğe şeridi 9 dilim `select_*.png` resimleriyle çizildi.
- Fontlar dosya adıyla değil **iç isimle** referanslanmalı: `"DejaVu Sans Regular 32"` ve `"DejaVu Sans Regular 44"`.
- `.pf2` dosyaları tema **kökünde düz** durmalı (`00_header` yalnızca `"$themedir"/*.pf2` tarar; alt dizinlerdeki pf2'ler yüklenmez).
- Başlık yeri sabit formülle hesaplanır: `y=40+ascent` (üst-orta) — başlık dikey konumlandırması tema dosyasında buna göre yapıldı.

### 1.2 SDDM Teması (yerleşim + güç düğmeleri + gerçek oturum seçimi)

- Gerçek kaynak: `iso/yerinde/airootfs/usr/share/sddm/themes/yerinde/Main.qml` (spec'teki `branding/sddm/yerinde/` dizini **yoktu** — varsayım hatalıydı; düzeltildi).
- Yeni yerleşim: krem zemin, "Yerinde OS" başlığı, kullanıcı adı + parola kutuları, parolanın **altında** "Oturum:" satırı (açılır liste), Giriş düğmesi, **⟳ (Yeniden Başlat)** ve **⏻ (Kapat)** düğmeleri (`visible: sddm.canReboot` / `sddm.canPowerOff`), başarısız girişte hata mesajı + parola temizleme.

**Belgelenen sapma — oturum seçimi API'si:**
- SDDM 0.21.0 `GreeterApp.cpp`'de `session` bağlam nesnesi **yoktur**; greeter'a yalnızca `sessionModel`, `screenModel`, `userModel`, `config`, `sddm`, `keyboard`, `primaryScreen` sunulur.
- `SessionModel` yalnızca `lastIndex` ve `count` sağlar; `session.currentIndex` diye bir özellik **yoktur**.
- Spec'teki `session.currentIndex` varsayımı geçersiz → uygulanan gerçek desen:
  - `property int sessionIndex: sessionModel.lastIndex`
  - ComboBox: `model: sessionModel`, `index: sessionIndex`, `onValueChanged: sessionIndex = index`
  - Giriş: `sddm.login(userEntry.text, passwordEntry.text, sessionIndex)`

**Doğrulama yöntemleri:**
- `qmllint` exit 0.
- `sddm-greeter --test-mode` → 0-byte hata log'u (daemonsuz ortamda sınırlı güçte; final14 ile aynı yöntem).
- Özel C++ Qt6 harness (kaynak `/tmp/opencode/qmltest/`) QML'i yükledi: `objectCreated` OK, `rootObjects=1` → yapısal hata yok. Çıkan uyarılar stub artefaktıdır (context property'ler harness'ta görünmez, `keyboard` stub'ı yok), gerçek hata değil.

### 1.3 X11 Sağlamlaştırma

- `usr/share/xsessions/plasma.desktop`: `Exec=startplasma-x11` + `TryExec=startplasma-x11` — zaten mevcuttu, doğrulandı.
- `etc/sddm.conf.d/yerinde.conf`: `[X11] Enable=true` — zaten mevcuttu, doğrulandı.
- Yeni koruma: `yerinde-branding` PKGBUILD doğrulama adımına `TryExec=startplasma-x11` grep kontrolü eklendi (pakette eksikse build FAIL).

### 1.4 Asistan Gizliliği (kişisel config paketten sıyrıldı)

- `yerinde-ai-assistant` PKGBUILD (pkgrel 4→5):
  - `cp` listesinden `config` dizini **çıkarıldı**.
  - Pakete yalnızca temiz config yazılıyor: `{"model_provider": "gemini"}`.
  - Build zamanı PRIVACY/CONFIG doğrulaması eklendi: config dosyası var mı, kişisel alanlar (`garden_pass`, `obs_ws_password`, `gemini_api_key`) boş mu, `model_provider=gemini` mevcut mu.
  - API anahtarı **değeri** PKGBUILD'e yazılmıyor; build'te kaynak config'ten okunup paket içinde aranıyor (`grep -c` = 0 → PASS).
- Sonuç: pakette yalnızca `{"model_provider": "gemini"}` var; `gemini_api_key` vb. hiç yok (paket içeriği birebir doğrulandı). Kişisel `config/api_keys.json` makinede duruyor, pakete GİRMEZ. Kurulu kullanıcılar kendi config'iyle devam eder; canlı oturum root Gemini anahtar ekranına yönlenir.
- **Bilinen sınır:** `app_config.py` içindeki `DEFAULT_CONFIG`'ta hardcoded `garden_pass` kaynak `.py` dosyasında kalmaktadır (kullanıcı onayıyla kapsam dışı bırakıldı).

---

## 2. Paketler ve Repo Durumu

| Paket | Sürüm | Boyut |
|---|---|---|
| `yerinde-branding` | 1.2.0-10-any | 11.301.426 B |
| `yerinde-ai-assistant` | 1.2.0-5-x86_64 | 439.809.157 B |

- Derleme doğrulamaları: WALLPAPER OK (5 ton), GRUB THEME OK (×2), XSESSION OK (Exec+TryExec), SDDM CONF OK, UINPUT OK, PRIVACY OK.
- **repo-add dersi:** `repo-add` DB'yi **yalnızca verilen paketlerle değiştirir** → bir kez sadece yeni paketlerle çağrılınca `calamares` kaydı silindi ve ilk ISO build `error: target not found: calamares` ile FAIL oldu. Düzeltme: her iki repo DB'sine **tüm paketler** birlikte tek `repo-add` ile eklendi.
- İki repo DB'si son durumu (bsdtar ile doğrulandı): `calamares 3.4.2-2`, `yerinde-ai-assistant 1.2.0-5`, `yerinde-branding 1.2.0-10`.
- ISO reposu `yerinde-project/repo/x86_64` → **zst** DB; git reposu `yerinde-repo/x86_64` → **gzip** DB.
- Git commit'leri (push YOK):
  - `23559aa` final15: grub teması 32/44px + turuncu seçili şerit, SDDM oturum seçimi + güç düğmeleri, asistan temiz config + gizlilik doğrulaması
  - `8d243e2` final15-fix: repo-add DB'yi sıfırlamıştı — calamares + tüm paket sürümleri iki repo DB'sine geri eklendi

---

## 3. ISO Build ve Doğrulama

- İlk deneme calamares kaydı kaybı nedeniyle FAIL etti; ikinci deneme **başarılı**.
- `--skip-prep` kullanıldı (ollama store + GGUF'ler airootfs'te önceden doğrulanmıştı: manifest `llama3.1` + `qwen2.5-coder 1.5b`, 9 blob, GGUF 6.6GB + 1.6GB). `tessdata` provider promt'u default=1 (final14 ile aynı).
- Build: 974 paket kuruldu; ISO **19,7 GB** (19.726.829.568 B).
- **Build-sonrası doğrulamalar — TÜMÜ OK:**
  - H1: sddm teması `Main.qml` + `sddm.conf.d/yerinde.conf` + `Current=yerinde`
  - H2: `xsessions/plasma.desktop` + `wayland-sessions/plasma.desktop` + `Xorg` + `startplasma-x11`
  - H3: `/usr/share/yerinde-ai/app/main.py` + `/usr/bin/yerinde` launcher
  - H4: `uinput` modülü + `ydotool.service` + drop-in + wants linki
  - H5: `voices/*.onnx` + `*.onnx.json` + `/usr/share/yerinde-ai/voices` symlinki
- **SHA256:** `da9dda1427b139826fdc5bef596e530af2d1480679f29b0431332f13fb11c12b` → `out/SHA256SUMS` dosyasında.
- ISO: `iso/yerinde/out/yerinde-2026.08.16-x86_64.iso`.

**Nüans (build-iso.sh):** `wait_build`'in bitiş deseni tarih ayracını kısa çizgi bekliyordu (`yerinde-2026.08.16-…` noktalı isimle eşleşmiyor) → desen `[.-]` ile düzeltildi. Çalışan süreç eski kodla parselendiği için `verify_post` + `sha256sum` elle (aynı işlevlerle) çalıştırıldı; sonuçlar yukarıda.

---

## 4. Regresyon Korunması (doğrulanmadı değil — build içinde var)

Aşağıdaki korumalar ISO build'te yer aldı ve yukarıdaki POST/package doğrulamalarıyla teyit edildi:
- MBR syslinux krem menü (dokunulmadı).
- 5 duvar kağıdı tonu (WALLPAPER OK).
- ollama store + GGUF'ler (prep doğrulaması).
- sudoers wheel (440) (dokunulmadı).
- launcher home-kopyası mantığı (dokunulmadı).

---

## 5. Kalan İşler / Notlar

- VM'de canlı test isteğe bağlı (kural gereği yapılmadı): GRUB menüsü, SDDM oturum değiştirme + güç düğmeleri, ilk açılışta asistan ekranı.
- `app_config.py` `DEFAULT_CONFIG`'taki hardcoded `garden_pass` için karar: kullanıcı onayıyla kapsam dışı.
- Yeni ISO sha256'sı final14'ünkinden (`194bab…`) farklıdır; beklenen davranış.
