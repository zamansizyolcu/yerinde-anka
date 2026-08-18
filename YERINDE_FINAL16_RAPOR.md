# YERINDE OS v1.6 — final16 Uygulama Raporu (2026-08-16)

## 1. SDDM: Oturum seçici + Giriş/⟳/⏻ tek satırda (final16.md §1)

`iso/yerinde/airootfs/usr/share/sddm/themes/yerinde/Main.qml` — `Row(spacing:8)` içinde
`"Oturum:"` etiketi + `ComboBox(sessionCombo)` + `Giriş` + `⟳` + `⏻` hepsi TEK satırda, ortalanmış.

- `sessionCombo`: `model: sessionModel`, `index: sessionIndex`, `onValueChanged: sessionIndex = index`
- `loginButton.onClicked: sddm.login(userEntry.text, passwordEntry.text, sessionIndex)`
- `rebootButton` (`visible: sddm.canReboot`, `onClicked: sddm.reboot()`), `powerOffButton` (`canPowerOff`/`powerOff()`)
- Enter/Giriş: passwordEntry `Keys.onReturnPressed/EnterPressed → loginButton.onClicked()` korundu

Doğrulamalar:
- `sddm-greeter --test-mode` (`/tmp/opencode/sddm16-test.log`): tema hatasız yüklendi; yalnız çıkış
  anı `wl_callback#25 still attached` uyarısı (zararsız), hiçbir "Cannot assign" hatası YOK.
- C++ QML harness (`/tmp/opencode/qmltest/`): `objectCreated: OK`, `rootObjects=1` (yapı geçerli;
  "Cannot read property of null" uyarıları sddm bağlam stub'ından — gerçek greeter testi temizdir).

## 2. ui.py X11 fullscreen çökme düzeltmesi (final16.md §2)

- `_session_is_x11()` (X11/xwayland oturumunu algılar)
- `_enter_fullscreen` X11'de: `root.state("zoomed")` (try/except → `geometry(f"{sw}x{sh}+0+0")`);
  Wayland'de `-fullscreen` korunur
- `_toggle_fullscreen` / `_esc_action` çıkışları `_exit_fullscreen_state()` kullanır
- `_resize_surface` try/except ile sarıldı (hata `write_log("ERR: _resize_surface — …")`)
- ISO içindeki paket: `/usr/share/yerinde-ai/app/ui.py` (kanıt satırları: 831, 858, 866, 869, 884, 889)

## 3. Wayland'de yazma: ydotool (final16.md §3)

- `actions/type_text.py`: `_type_wayland_ydotool` → `ydotool type --key-delay 40`
- Akış: pano→paste → Wayland'de ydotool → hata `"Yazılamadı: ydotool/uinput hazır değil (servis+grup kontrol). …"`
  → X11/Windows pyautogui
- `actions/mouse_control.py` (69) ve `keyboard_control.py` (224): Türkçe hata
  `"ydotool/uinput hazır değil (modül/servis kontrol)"`
- Altyapı (final14'ten, ISO'da doğrulandı): `/etc/systemd/system/ydotool.service` +
  `yerinde-ydotool.conf` (`--socket-path=/run/ydotool.socket --socket-perm=0660 --socket-own=root:input`) +
  `multi-user.target.wants/ydotool.service` symlinki + `uinput` modülü
- kullanıcı `input,uinput` gruplarında (calamares users.conf)

## 4. Canlı mod masaüstü kısayolu (final16.md §5)

- `/usr/share/applications/yerinde-ai.desktop`: `Exec=/usr/bin/yerinde`, `Icon=yerinde`,
  `OnlyShowIn=KDE`, `Terminal=false`
- `/usr/bin/yerinde` launcher: `/usr/share/yerinde-ai/app` → `$HOME/.yerinde/app` kopyası → `run.sh`
- OTOMATİK BAŞLATMA YOK (autostart dizinlerinde `Exec=yerinde` eşleşmesi yok)

## 5. X11 kapatma/yeniden başlatma araçları (final16.md §6)

- `packages.x86_64` + asistan PKGBUILD depends: `xorg-xhost xorg-xprop xorg-xwininfo`
- ISO'da kurulu doğrulandı: xorg-xhost-1.0.10-1, xorg-xprop-1.2.8-1, xorg-xwininfo-1.1.7-1

## 6. SquashFS takılması düzeltmesi (build altyapısı)

- Bulgu: mkarchiso pacstrap'i root olarak koştuğunda `-N` (mount namespace) bayrağı atlanır;
  chroot mount'ları (proc/sys/efivarfs/dev/run/tmp) HOST namespace'e sızar ve kalıcı kalır.
  mksquashfs canlı sysfs'i yürüyüp saatlerce takılı kalıyordu ("Read failed…", ~%2).
- Çözümler:
  - `airootfs/root/customize_airootfs.sh` (yeni): arch-chroot'un son adımında tüm sanal dosya
    sistemlerini söker (squashfs'ten ÖNCE) — hem takılmayı hem ISO'ya sysfs/proc içeriği karışmasını engeller
  - `build-iso.sh build()`: `rm -rf work out` ÖNCESİ kalıntı mount'ları `umount -R` ile temizler
- Sonuç: squashfs ~160 MB/s (30sn'de 4.8GB), build kısa sürede tamamlandı

## 7. Doğrulamalar (build sonrası otomatik POST)

```
POST OK (H2): xsessions/plasma.desktop + wayland-sessions/plasma.desktop + Xorg + startplasma-x11
POST OK (H4): uinput modülü + ydotool servisi + drop-in + wants linki
POST OK (H5): voices/*.onnx + *.onnx.json + /usr/share/yerinde-ai/voices symlinki
POST OK (H1): sddm teması + sddm.conf.d/yerinde.conf
POST OK (H3): /usr/share/yerinde-ai/app/main.py + /usr/bin/yerinde launcher
POST OK (F5): yerinde-ai.desktop (Exec=/usr/bin/yerinde + OnlyShowIn=KDE) + otomatik başlatma YOK
POST OK (F1): Main.qml oturum seçici + sddm.login(sessionIndex)
POST OK (F2/F4): ui.py X11 zoomed + type_text/ydotool + mouse_control mesajı
== TÜM POST DOĞRULAMALAR BAŞARILI ==
```

## 8. ISO ve paketler

- ISO: `iso/yerinde/out/yerinde-2026.08.16-x86_64.iso` — **19 GB**
- SHA256SUMS: **8cad0ee0e364f417c57b3a6a24b2ee5af3d73d77c5396d3dcb8462f73390210a** (`sha256sum -c` → Tamam)
- Paketler (iki repo DB'sinde de): yerinde-ai-assistant-1.2.0-6, yerinde-branding-1.2.0-11,
  calamares-3.4.2-2
- Commit: `adece4a` (branch main, push yapılmadı)

## 9. Kullanıcı test listesi (VM kurulumunda)

1. SDDM ekranında oturum seçici TEK satırda: "Oturum:" + açılır liste + Giriş + ⟳ + ⏻ yan yana.
2. Plasma (X11) oturumunda asistan çalıştırın: tam ekran kesiksiz açılmalı, kenarlıkta boşluk/çökme olmamalı.
3. Plasma (Wayland) oturumunda metin yazma/mouse kontrolü ydotool ile çalışmalı; servis yoksa Türkçe hata mesajı çıkmalı.
4. Masaüstündeki "YERINDE AI Asistan" kısayolundan asistan açılmalı; oturum açılışında asistan OTOMATİK BAŞLAMAMALI.
5. Kapat/Yeniden başlat düğmeleri ve X11'de güç işlemleri çalışmalı.
6. MBR krem menü, GRUB teması/fallback, 5 duvar kağıdı, ollama store+GGUF'ler kurulumda yerinde olmalı.
