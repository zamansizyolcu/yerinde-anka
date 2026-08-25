# final62 — UNPACKFS KAYNAK YOLU: AÇILIŞ MODU BAĞIMSIZ
SORUN: Geekom'da %2 "airootfs.sfs kaynak yok"; VM/ASUS temiz.
Medya aklandı (Ventoy/direkt/flaş aynı) → kök: canlı oturumda
sfs dosyası bootmnt'de değil (copytoram/Geekom mount quirks).

## §1 KEŞİF (canlı oturumda, VM + Geekom)
- cat /proc/cmdline; mount | grep airootfs; ls bootmnt
- RAM'deki sfs konumunu bul: ls /run/archiso/sfs/ (dosya veya
  dizin) → rapora yaz

## §2 PRE-UNPACKFS KÖPRÜSÜ (shellprocess, unpackfs'ten ÖNCE)
S=/run/archiso/bootmnt/arch/x86_64/airootfs.sfs
[ -e "$S" ] || {
  mkdir -p "$(dirname "$S")"
  for c in /run/archiso/sfs/airootfs.sfs \
           /run/archiso/sfs/*/airootfs.sfs; do
    [ -e "$c" ] && ln -s "$c" "$S" && break
  done
}
→ copytoram/RAM modunda symlink RAM'deki sfs'i gösterir;
  normal modda dosya zaten var → dokunmaz
- KEŞİF farklı yol gösterirse symlink hedefini ona göre ayarla

## §3 NET HATA (final61 §1 korunur)
köprüden SONRA hâlâ yoksa: "Kurucu canlı ISO ortamı bulamadı…"
Türkçe mesaj + DUR (şifreli %2 hatası asla)

## §4 REGRESYON + BUILD + PUSH
- VM: normal boot + copytoram boot İKİSİ de kurulumu bitirir
- yanına kur / elle bölümleme / SDDM tema / os-prober AYNEN
- pkgrel bump + makepkg + repo-add
- setsid build-iso.sh > /tmp/opencode/final62-iso.log 2>&1 &
  poll "INFO: Done!" + sha256
- git push yerinde-anka (KULLANICI İZNİ VAR)

## §5 TEST
1) VM normal girdi → kurulum ✅
2) VM copytoram girdi → kurulum ✅ (yeni: symlink köprüsü)
3) Geekom: hangi girdi olursa olsun → %2 hatası YOK,
   Windows yanına kurulum tamamlanır