# YERINDE ANKA — OS Kaynakları

Yerinde ANKA Linux (CachyOS/Arch tabanlı, Wayland-tek oturum, Plasma)
ISO'sunun tam kaynak ağacı: `iso/yerinde` (mkarchiso profili),
`packages/` (yerinde-branding + calamares), `repo/x86_64` ([yerinde]
pacman deposu db'si) ve asistan BAZ kopyası `yerinde-ai-assistant/`.

İlgili depolar:

- Asistan (kamu BAZ): https://github.com/zamansizyolcu/yerinde-ai-assistant
- Bu depo (OS kaynakları): https://github.com/zamansizyolcu/yerinde-anka

## ISO derleme

```bash
cd iso/yerinde
./build-iso.sh          # prep doğrulamaları + mkarchiso + POST kontrolleri
```

Brandıng/calamares paketleri değiştiyse önce `packages/*/` içinde
`makepkg` + `repo-add ../../repo/x86_64/yerinde.db.tar.zst` yapın
(paket `.zst`'leri bu depoya GİRMEZ — `.gitignore`).

## ISO dağıtımı (ÖNEMLİ)

`*.iso` (~2,7 GB) GitHub'a **GİREMEZ** (100 MB dosya limiti). Dağıtım:

1. **LAN**: derleme makinesinde `cd iso/yerinde/out && python -m http.server`
   → hedef makinede tarayıcı ile indir; kurulu sistemde
   `/etc/pacman.conf`'a `[yerinde]` + `Server = http://<host-ip>:8000`
   eklenmişse asistan da `pacman -S yerinde-ai-assistant` ile kurulur.
2. **USB**: `sudo dd if=yerinde-anka-*.iso of=/dev/sdX bs=4M status=progress`
   (Ventoy da çalışır).

SHA256 doğrulaması: `out/SHA256SUMS`.

## Asistan kurulumu (kurulu sistemde)

Masaüstündeki **"YERINDE Asistanı Kur"** kısayolu 3 yol dener:
pacman [yerinde] LAN deposu → İndirilenler'deki yerel klasör →
`git clone https://github.com/zamansizyolcu/yerinde-ai-assistant`.
