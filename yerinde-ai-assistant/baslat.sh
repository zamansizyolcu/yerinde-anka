#!/usr/bin/env bash
# YERINDE — CachyOS / Yerinde ANKA (Arch Linux) başlatma betiği
# final38 §3: GÜVENLİ BAŞLATMA —
#   - venv yoksa oluşturulur (--system-site-packages: sistem paketleri görülür)
#   - venv/bin/python yoksa SİSTEM python3 fallback'i
#   - uygulama açılamazsa Türkçe ipucu: eksik modül adı + kurulacak komut
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    python -m venv --system-site-packages venv 2>/dev/null || true
fi

if [ -x venv/bin/python ]; then
    PY="venv/bin/python"
else
    PY="python3"
fi

HATA_LOG="$(mktemp)"
"$PY" main.py 2> >(tee "$HATA_LOG" >&2)
RC=$?

if [ "$RC" -ne 0 ]; then
    MOD="$(grep -o "ModuleNotFoundError: No module named '[^']*'" "$HATA_LOG" \
           | head -1 | sed "s/.*named '//;s/'\$//")"
    if [ -n "$MOD" ]; then
        echo
        echo "══════════════════════════════════════════════════"
        echo "HATA: Uygulama '$MOD' modülü eksik olduğu için açılamadı."
        echo "Kurmak için ya tüm kurulumu yeniden çalıştır:"
        echo "    ./kurulum.sh"
        echo "ya da yalnız bu modülü kur:"
        echo "    source venv/bin/activate && pip install $MOD"
        echo "══════════════════════════════════════════════════"
    else
        echo
        echo "UYARI: Uygulama beklenmedik şekilde kapandı (hata kodu: $RC)."
        echo "Ayrıntılı günlük için:"
        echo "    ~/.yerinde/ai.log"
    fi
fi
rm -f "$HATA_LOG"
exit "$RC"
