@echo off
REM YERİNDE - Kendi Modelini Eğitme: sanal ortam (venv) kurulumu (Windows)
REM Bu dosyaya çift tıklayabilir YA DA bu klasörde bir terminal açıp
REM "kurulum_windows.bat" yazabilirsin. Bir kere çalıştırman yeterli.

echo === Sanal ortam (venv) olusturuluyor: venv\ ===
python -m venv venv
if errorlevel 1 (
    echo HATA: 'python' komutu bulunamadi. Python 3.10+ kurulu oldugundan
    echo ve PATH'e eklendiginden emin ol: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo === Sanal ortam etkinlestiriliyor ===
call venv\Scripts\activate.bat

echo === Kutuphaneler kuruluyor (bu birkac dakika surebilir) ===
pip install --upgrade pip
pip install -r requirements-egitim.txt

echo.
echo === llama.cpp kontrol ediliyor (GGUF donusumu icin gerekli) ===
if exist llama.cpp goto LLAMA_VAR
where git >nul 2>nul
if errorlevel 1 goto LLAMA_NO_GIT
echo llama.cpp klonlaniyor (internet gerekir, bir kereye mahsus)...
git clone --depth 1 https://github.com/ggerganov/llama.cpp.git
if errorlevel 1 goto LLAMA_CLONE_FAILED
echo llama.cpp donusum gereksinimleri kuruluyor...
pip install -r llama.cpp\requirements\requirements-convert_hf_to_gguf.txt
goto LLAMA_DONE

:LLAMA_VAR
echo llama.cpp zaten mevcut, klonlama atlaniyor.
goto LLAMA_DONE

:LLAMA_NO_GIT
echo UYARI: 'git' bulunamadi, llama.cpp klonlanamadi.
echo Git'i https://git-scm.com/downloads adresinden kurup bu scripti
echo tekrar calistirabilirsin - ya da git'i kurduktan sonra elle:
echo     git clone https://github.com/ggerganov/llama.cpp.git
goto LLAMA_DONE

:LLAMA_CLONE_FAILED
echo UYARI: llama.cpp klonlanamadi - internet baglantini kontrol et.

:LLAMA_DONE

echo.
echo ============================================================
echo  KURULUM TAMAMLANDI.
echo  Bundan sonra, bu klasorde YENI bir terminal actiginda once:
echo      venv\Scripts\activate.bat
echo  calistir, sonra scripti calistirabilirsin, ornek:
echo      python egitim_ve_gguf_donustur.py --llama-cpp-path .\llama.cpp
echo ============================================================
pause
