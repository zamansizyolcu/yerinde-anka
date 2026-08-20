## §6 PUSH — GITHUB (derleme temizse)
1) cd /home/yerinde/yerinde-project
   git add -A && git commit -m "final53: çift boot + SDDM kullanıcı
   listesi + yerinde-kullanici" && git push -u origin main
   (KULLANICI İZNİ VAR; *.iso ve *.pkg.tar.zst zaten .gitignore'da
   → push takılmaz)
2) ASİSTAN reposu bu turda değişmediyse push GEREKSİZ —
   Big Pickle asistana dokunduysa commit + push zorunlu
3) DOĞRULA: git ls-remote origin + curl GitHub sayfası 200
4) RAPORA: commit hash + ls-remote çıktısı + ISO sha256