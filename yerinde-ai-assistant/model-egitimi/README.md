# YERİNDE — Kendi Modelini Eğitme (LoRA ince ayar + GGUF dönüşümü)

Bu klasör, YERİNDE'yi kullandıkça biriken eğitim verisiyle **kendi küçük dil
modelini** ince ayarlayıp (fine-tune) Ollama ile kullanabileceğin bir
**GGUF** dosyasına çevirmeni sağlayan bir script içerir.

**Bu script YERİNDE'nin içinden otomatik çalışmaz** — kendi bilgisayarında,
bir terminalden sen çalıştırırsın. Gerçek bir model eğitmek internetten
model indirmek (birkaç GB), gerçek işlemci/ekran kartı zamanı (dakikalar-
saatler) ve ağır kütüphaneler (torch, transformers, peft) gerektirir; bu
YERİNDE'nin hafif/çevrimdışı asistan mimarisinin dışında kalır.

**Bu klasörde ne var:**
- `egitim_ve_gguf_donustur.py` — asıl script
- `egitim_verisi.jsonl` — YERİNDE Ayarlar'daki "🧠 Kendi Modelini Eğit"
  düğmesine her bastığında, **güncel** eğitim verinle burada otomatik
  yenilenir (elle bir yerden kopyalamana gerek YOK — script varsayılan
  olarak burayı, yani kendisiyle AYNI klasörü arar)
- `requirements-egitim.txt` — gerekli Python kütüphaneleri listesi
- `kurulum_windows.bat` / `kurulum_linux.sh` — sanal ortamı (venv) VE
  llama.cpp'yi otomatik kurup gereksinimlerini yükleyen scriptler (SADECE
  İLK SEFERDE çalıştırılır)
- `egitim_baslat.bat` / `egitim_baslat.sh` — kurulum bittikten SONRA, her
  eğitim istediğinde çift tıklayacağın/çalıştıracağın dosya — komut
  yazmana gerek kalmadan eğitimi + GGUF dönüşümünü başlatır. YERİNDE
  Ayarlar'daki "🧠 Kendi Modelini Eğit" düğmesi de (kurulum zaten
  yapıldıysa) bunu senin için otomatik açmayı dener.

## Neden Sanal Ortam (venv)?

`torch`/`transformers`/`peft` gibi kütüphaneler hem BÜYÜK (birkaç yüz MB)
hem de sistemindeki başka Python kurulumlarıyla çakışabilir. Bu yüzden
onları sisteme değil, **bu klasöre özel, izole bir sanal ortama (venv)**
kuruyoruz — bilgisayarının geri kalanına hiç dokunmaz, silmek istersen
sadece `venv` klasörünü silmen yeterli.

## Adım Adım

### 1) Kurulum scriptini çalıştır (SADECE BİR KERE)
**Windows:** Bu klasörde `kurulum_windows.bat` dosyasına çift tıkla (ya da
bir terminalde `kurulum_windows.bat` yaz).
**Linux (Pardus/CachyOS/OrangePi 5 Plus):** Bu klasörde bir terminal aç, `bash kurulum_linux.sh` çalıştır.

Bu TEK script şunların HEPSİNİ senin için otomatik yapar:
1. `venv/` adlı izole bir sanal ortam oluşturur
2. `requirements-egitim.txt`'teki kütüphaneleri (torch, transformers, peft...) oraya kurar
3. `llama.cpp`'yi klonlar (GGUF dönüşümü için gerekli) ve onun da kendi
   gereksinimlerini kurar — `llama.cpp` klasörü zaten varsa bu adımı atlar
   (yani scripti tekrar çalıştırsan bile yeniden klonlamaz)

**İnternet SADECE bu adımda gerekir** (kütüphaneleri ve llama.cpp'yi indirmek
için) — bir daha kurmana/klonlamana gerek kalmaz. `git` kurulu değilse
(Linux'ta `sudo pacman -S git` / `sudo apt install git`, Windows'ta
https://git-scm.com/downloads) script llama.cpp adımını atlar, geri kalanı
yine de tamamlar; git'i kurup scripti tekrar çalıştırman yeterli.

> 💡 Ekran kartın (NVIDIA) varsa, bu scripti çalıştırmadan ÖNCE
> https://pytorch.org/get-started/locally/ adresinden kendi CUDA sürümüne
> uygun torch kurulum komutunu not al; kurulum scripti bittikten SONRA
> `venv`'i etkinleştirip o komutu ayrıca çalıştırarak CPU sürümünün üzerine
> GPU sürümünü kurabilirsin (çok daha hızlı eğitim sağlar). Yoksa CPU'da
> (daha yavaş ama küçük veri kümeleri için birkaç dakika) çalışır.

### 2) Eğitimi başlat

**En kolay yol:** `egitim_baslat.bat` (Windows) / `egitim_baslat.sh` (Linux —
`bash egitim_baslat.sh`) dosyasını çalıştır. Bu, sanal ortamı kendi
etkinleştirir, aynı klasördeki `egitim_verisi.jsonl`'i otomatik bulur ve
GGUF dönüşümünü (llama.cpp varsa) yapar — komut yazmana GEREK YOK. YERİNDE
Ayarlar'daki "🧠 Kendi Modelini Eğit" düğmesi de (kurulum zaten yapıldıysa)
bunu senin için yeni bir terminalde otomatik başlatmayı dener.

**Elle çalıştırmak istersen:** Her yeni terminal açtığında ÖNCE:
```bash
# Windows:
venv\Scripts\activate.bat
# Linux:
source venv/bin/activate
```
Sonra:
```bash
python egitim_ve_gguf_donustur.py --llama-cpp-path ./llama.cpp
```
Bu, aynı klasördeki `egitim_verisi.jsonl`'i otomatik bulur — başka bir yol
belirtmene gerek yok.

Sık kullanılan seçenekler:
```bash
# Farklı bir temel model
python egitim_ve_gguf_donustur.py --base-model "Qwen/Qwen2.5-0.5B-Instruct" --llama-cpp-path ./llama.cpp

# Daha fazla epoch (veri azsa faydalı olabilir, ama ezberlemeye de dikkat)
python egitim_ve_gguf_donustur.py --epochs 5 --llama-cpp-path ./llama.cpp

# Sadece eğit, GGUF'a çevirme (llama.cpp henüz hazır değilse)
python egitim_ve_gguf_donustur.py

# Daha sonra, hazır eğitilmiş modeli GGUF'a çevir
python egitim_ve_gguf_donustur.py --skip-training --llama-cpp-path ./llama.cpp

# Niceleme (daha küçük dosya) - llama.cpp derlenmiş olmalı:
#   cmake -B llama.cpp/build llama.cpp && cmake --build llama.cpp/build --config Release
python egitim_ve_gguf_donustur.py --llama-cpp-path ./llama.cpp --quantize Q4_K_M
```

### 3) Ollama'ya tanıt
Script bittiğinde `cikti/` klasöründe bir `Modelfile` bulacaksın:
```bash
cd cikti
ollama create benim-modelim -f Modelfile
ollama run benim-modelim
```

## İnternet Ne Zaman Gerekir, Ne Zaman GEREKMEZ?

| Adım | İnternet gerekir mi? | Ne sıklıkla? |
|---|---|---|
| Kurulum scripti (venv + kütüphaneler + llama.cpp klonlama) | ✅ Evet | Sadece 1. kez |
| Temel model indirme (ör. Qwen2.5) | ✅ Evet | Sadece İLK çalıştırmada (sonra bilgisayarında `~/.cache/huggingface` içinde önbelleğe alınır — AYNI modeli tekrar kullanırsan bir daha inmez) |
| Scripti (veri biriktikçe) TEKRAR çalıştırmak | ❌ Hayır | — (her şey zaten diskinde) |

Yani: kurulum scriptini bir kere çalıştırdıktan sonra, YERİNDE'yi kullanmaya
devam edip yeni veri biriktirdikçe eğitim scriptini tekrar çalıştırmak için
**internete ihtiyacın olmaz** (aynı temel modeli kullanmaya devam ettiğin
sürece).

## Gerçekçi Beklentiler

- **Az veri = az etki.** Birkaç düzine örnekle eğitilen bir LoRA, modelin
  "kişiliğini" tamamen değiştirmez. Daha belirgin bir fark için YERİNDE'yi
  kullanmaya devam edip verinin (ideal olarak birkaç yüz - birkaç bin
  örnek) birikmesini beklemek en iyisi.
- **Her zaman sorunsuz çalışmayabilir.** Temel model değişirse, llama.cpp
  güncellenirse ya da bir format uyumsuzluğu çıkarsa hata alabilirsin —
  hata mesajını YERİNDE'ye/Claude'a gösterirsen birlikte çözebiliriz.
- **Disk alanı.** Temel model (~1-3 GB) + venv (~2-4 GB, çoğunlukla torch)
  + GGUF çıktısı (benzer boyut) — toplamda birkaç GB boş yer ayır.
