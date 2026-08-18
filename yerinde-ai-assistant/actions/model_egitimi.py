"""
actions/model_egitimi.py — "Kendi Modelini Eğit (GGUF'a Dönüştür)" akışının
tüm mantığı burada toplanır; hem Ayarlar > Eğitim Verisi panelindeki düğme
hem de sesli komut ("eğitimi başlat" / "ggufa dönüştür") AYNI bu kodu
çağırır — böylece ikisi arasında davranış farkı olmaz.
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

_IS_WINDOWS = platform.system() == "Windows"


def model_egitimi_dir() -> Path:
    """YERİNDE'nin KENDİ kurulum klasöründeki 'model-egitimi' klasörü —
    Masaüstü/Çalışmalarım'da DEĞİL, doğrudan burada (script, kurulum
    dosyaları ve eğitim verisi hep AYNI yerde durur)."""
    d = Path(__file__).resolve().parent.parent / "model-egitimi"
    d.mkdir(parents=True, exist_ok=True)
    return d


def launch_in_new_terminal(script_path: Path) -> tuple[bool, str]:
    """Verilen .bat/.sh dosyasını YENİ, GÖRÜNÜR bir terminal penceresinde
    başlatmayı dener. Birden fazla yöntemi sırayla dener (biri işe
    yaramazsa diğerine geçer). (başarılı_mi, hangi_yöntemle/hata) döner."""
    if _IS_WINDOWS:
        # 1) os.startfile: dosyaya çift tıklamışsın gibi, Windows'un KENDİ
        # dosya ilişkilendirmesini kullanır (.bat -> cmd.exe). En basit ve
        # en genel-uyumlu yöntem, elle çift tıklamayla AYNI davranışı taklit
        # eder.
        try:
            import os
            os.startfile(str(script_path))  # noqa: S606
            return True, "os.startfile"
        except Exception as e1:
            hata1 = str(e1)
        # 2) cmd.exe'yi DOĞRUDAN, yeni bir konsol penceresi açacak şekilde
        # (CREATE_NEW_CONSOLE) başlat.
        try:
            subprocess.Popen(
                ["cmd.exe", "/c", str(script_path)],
                cwd=str(script_path.parent),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return True, "cmd.exe /c (yeni konsol)"
        except Exception as e2:
            hata2 = str(e2)
        # 3) Klasik "start" idiomu (shell=True ile, boş başlık "" ile —
        # yol boşluk içerse bile doğru çalışır).
        try:
            subprocess.Popen(f'start "" "{script_path}"', shell=True,
                             cwd=str(script_path.parent))
            return True, "start (shell)"
        except Exception as e3:
            return False, f"Hiçbir yöntem çalışmadı: [{hata1}] [{hata2}] [{e3}]"

    # Linux: yaygın terminal emülatörlerini sırayla dene
    for term_cmd in (
        ["x-terminal-emulator", "-e", "bash", str(script_path)],
        ["gnome-terminal", "--", "bash", str(script_path)],
        ["konsole", "-e", "bash", str(script_path)],
        ["xfce4-terminal", "-e", f"bash {script_path}"],
        ["xterm", "-e", "bash", str(script_path)],
    ):
        try:
            subprocess.Popen(term_cmd, cwd=str(script_path.parent),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, term_cmd[0]
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return False, "Bilinen hiçbir terminal emülatörü bulunamadı"


def egitim_baslat_command() -> str:
    """YERİNDE'nin kendi 'model-egitimi' klasöründeki, daha önce kurulmuş
    (venv hazır) eğitim ortamında, güncel eğitim verisiyle LoRA ince ayarını
    ve (llama.cpp varsa) GGUF dönüşümünü YENİ bir terminal penceresinde
    başlatır. 'eğitimi başlat', 'modelimi eğit', 'ggufa dönüştür', 'eğitimi
    ggufa çevir' gibi komutlarla tetiklenir. NOT: sanal ortam henüz
    kurulmadıysa (ilk kullanım), önce kurulum dosyasını çalıştırman
    gerektiğini söyler, hiçbir şey başlatmaz."""
    folder = model_egitimi_dir()
    if not (folder / "egitim_ve_gguf_donustur.py").exists():
        return (f"'{folder}' klasöründe eğitim scripti bulunamadı — "
                "YERİNDE kurulumu eksik/bozuk olabilir.")

    venv_var_mi = (folder / "venv").exists()

    from backend.habits import HabitLearner
    hl = HabitLearner("memory/habits.json")
    veri_msg = hl.export_dataset(folder / "egitim_verisi.jsonl")

    baslat_dosyasi = folder / ("egitim_baslat.bat" if _IS_WINDOWS else "egitim_baslat.sh")

    if not venv_var_mi:
        kurulum_adi = "kurulum_windows.bat" if _IS_WINDOWS else "kurulum_linux.sh"
        return (f"Eğitim verin güncellendi ({veri_msg}). Ama bu bilgisayarda İLK "
                f"KEZ eğitim yapıyorsun — önce '{folder}' klasöründeki "
                f"'{kurulum_adi}' dosyasını çalıştırman gerekiyor (sanal ortamı + "
                "llama.cpp'yi otomatik kurar, internet gerekir, sadece bir kere). "
                "O bittikten sonra bana tekrar 'eğitimi başlat' diyebilirsin.")

    acildi, detay = launch_in_new_terminal(baslat_dosyasi)
    if acildi:
        return (f"Eğitim verisi güncellendi ({veri_msg}) ve yeni bir terminal "
                f"penceresinde eğitim+GGUF dönüşümünü başlattım ({detay}). "
                "İlerlemeyi açılan pencereden takip edebilirsin — veri boyutuna "
                "göre dakikalar-saatler sürebilir.")
    return (f"Eğitim verisi güncellendi ({veri_msg}), AMA yeni bir terminal "
            f"penceresi otomatik açamadım ({detay}). '{folder}' klasörüne gidip "
            f"'{baslat_dosyasi.name}' dosyasını sen çalıştırır mısın?")
