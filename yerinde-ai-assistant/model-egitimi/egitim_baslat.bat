@echo off
REM YERİNDE - Kendi Modelini Eğit (GGUF'a Dönüştür) - TEK TIKLA ÇALIŞTIR
REM Bu dosyaya çift tıkla - kurulum_windows.bat'ı daha önce çalıştırmış
REM olman gerekir (sanal ortam + llama.cpp hazır olmalı).
REM
REM NOT: Bu pencerede bir sorun görürsen, ayrıca "egitim_log.txt" dosyasına
REM da bak - bu script her adımı oraya da yazar (teşhis için).

cd /d "%~dp0"

echo [%date% %time%] egitim_baslat.bat calisti > egitim_log.txt
echo Calisma klasoru: %CD% >> egitim_log.txt

if not exist venv goto NO_VENV

echo venv klasoru bulundu, etkinlestiriliyor... >> egitim_log.txt
call venv\Scripts\activate.bat
echo venv etkinlestirildi. >> egitim_log.txt

set "LLAMA_ARG="
if not exist llama.cpp goto NO_LLAMA
set "LLAMA_ARG=--llama-cpp-path llama.cpp"
echo llama.cpp bulundu, GGUF donusumu de yapilacak. >> egitim_log.txt
goto RUN_TRAINING

:NO_LLAMA
echo UYARI: llama.cpp bulunamadi - sadece egitim yapilacak, GGUF'a
echo cevrilmeyecek. GGUF icin once kurulum_windows.bat'i tekrar
echo calistir (llama.cpp'yi otomatik klonlar).
echo llama.cpp bulunamadi, sadece egitim yapilacak. >> egitim_log.txt

:RUN_TRAINING
echo.
echo === Egitim + GGUF donusumu basliyor ===
echo (Bu islem veri boyutuna ve bilgisayarina gore dakikalar-saatler surebilir)
echo.
echo Calistirilan komut: python egitim_ve_gguf_donustur.py %LLAMA_ARG% >> egitim_log.txt
python egitim_ve_gguf_donustur.py %LLAMA_ARG%
set SCRIPT_HATA=%errorlevel%
echo Script bitti, cikis kodu: %SCRIPT_HATA% >> egitim_log.txt

echo.
echo ============================================================
if "%SCRIPT_HATA%"=="0" goto BASARILI
echo  BIR HATA OLUSTU (cikis kodu: %SCRIPT_HATA%).
echo  Yukaridaki kirmizi/hata metnini ve 'egitim_log.txt' dosyasini
echo  kontrol et.
goto SON

:BASARILI
echo  BITTI. Ciktilar 'cikti\' klasorunde (Modelfile dahil).

:SON
echo ============================================================
pause
exit /b %SCRIPT_HATA%

:NO_VENV
echo HATA: Sanal ortam (venv) bulunamadi. >> egitim_log.txt
echo HATA: Sanal ortam (venv) bulunamadi.
echo Once 'kurulum_windows.bat' dosyasina cift tikla, o bitince
echo bu dosyayi tekrar calistir.
pause
exit /b 1
