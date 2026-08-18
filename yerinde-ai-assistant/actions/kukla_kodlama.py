"""
actions/kukla_kodlama.py — YERİNDE Kodlama Aracını tarayıcıda açar VE
(araç açıkken) sesli komutlarla canlı olarak yönetir.

3B Tasarım Stüdyosu / Robot Tasarım Atölyesi ile AYNI köprü mimarisi
(core/bridge_server.py) paylaşılır — ayrı bir sunucu/port gerekmez, çünkü
sesli komutlar zaten hangi araç o an bağlıysa ona gider.

YERİNDE Kodlama Aracı, Scratch benzeri blok tabanlı (Blockly) VE Python
metin tabanlı (Skulpt — tarayıcıda çalışan gerçek bir Python yorumlayıcısı)
kodlamayla, basit 3B karakterleri (ileri/geri git, dön, zıpla, konuş, renk/
boyut değiştir) programlamayı sağlar. Projeler '.yerinde' uzantılı (JSON
tabanlı) dosyalar olarak Çalışmalarım/Karakter-Kodlama klasörüne kaydedilir.
"""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

from core import bridge_server

_IS_WINDOWS = platform.system() == "Windows"

from actions.browser_launch import open_tool_url

_NOT_OPEN_MSG = ("YERİNDE Kodlama Aracı şu an açık değil gibi görünüyor — "
                  "önce 'yerinde kodlama aracını aç' diyerek açar mısın?")


def _tool_path() -> Path:
    return Path(__file__).resolve().parent.parent / "yerinde-kodlama-araci" / "yerinde-kodlama-araci.html"


def _handle_project_export_trigger(payload: dict) -> None:
    """Tarayıcıdaki '💾 Kaydet' düğmesine tıklandığında (Python bir şey
    İSTEMEDEN) çağrılır - projeyi Çalışmalarım/Karakter-Kodlama'ya kaydeder."""
    raw = payload.get("data")
    if not raw:
        bridge_server.send_command({"action": "export_result", "ok": False, "message": "Proje verisi boş geldi."})
        return
    from actions.code_tools import ensure_workspace_folder
    import time

    folder = ensure_workspace_folder("Karakter-Kodlama")
    target = folder / f"karakter-projem {time.strftime('%Y-%m-%d %H.%M')}.yerinde"
    try:
        target.write_text(raw, encoding="utf-8")
        bridge_server.send_command({"action": "export_result", "ok": True, "message": f"Proje kaydedildi: {target.name}"})
    except Exception as e:
        bridge_server.send_command({"action": "export_result", "ok": False, "message": f"Kaydedilemedi: {e}"})


def _handle_list_projects_trigger(_payload: dict) -> None:
    """Tarayıcıdaki '🔄 Listeyi Yenile' düğmesine tıklandığında çağrılır -
    kayıtlı .yerinde dosyalarının adlarını tarayıcıya gönderir."""
    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Karakter-Kodlama")
    files = sorted((p.name for p in folder.glob("*.yerinde")),
                    key=lambda n: (folder / n).stat().st_mtime, reverse=True)
    bridge_server.send_command({"action": "saved_projects_list", "files": files})


def _handle_load_specific_project_trigger(payload: dict) -> None:
    """Tarayıcıda kayıtlı bir projeye tıklandığında çağrılır - o dosyayı
    okuyup tarayıcıya geri gönderir."""
    filename = payload.get("filename")
    if not filename:
        return
    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Karakter-Kodlama")
    target = folder / filename
    if not target.exists():
        bridge_server.send_command({"action": "export_result", "ok": False, "message": "Dosya bulunamadı."})
        return
    try:
        raw = target.read_text(encoding="utf-8")
        bridge_server.send_command({"action": "load_project_data", "data": raw})
    except Exception as e:
        bridge_server.send_command({"action": "export_result", "ok": False, "message": f"Dosya okunamadı: {e}"})


def open_kukla_kodlama_atolyesi() -> str:
    """'yerinde kodlama aracını aç' / 'yerinde programlama aracını aç' /
    'blok kodlama aracını aç' — Scratch benzeri, blok VE Python tabanlı 3B
    yerinde kodlama aracını tarayıcıda açar (sunucu gerekmez)."""
    path = _tool_path()
    if not path.exists():
        return ("YERİNDE Kodlama Aracı bulunamadı — 'yerinde-kodlama-araci' klasörünün "
                "YERİNDE'nin ana klasöründe olduğundan emin ol.")
    bridge_server.ensure_started()
    bridge_server.register_trigger("project_export_trigger", _handle_project_export_trigger)
    bridge_server.register_trigger("list_projects_trigger", _handle_list_projects_trigger)
    bridge_server.register_trigger("load_specific_project_trigger", _handle_load_specific_project_trigger)
    url = path.resolve().as_uri()
    try:
        open_tool_url(url)
        return ("YERİNDE Kodlama Aracı tarayıcıda açılıyor! Soldan yeni bir karakter ekleyip, "
                "Blok Modu'nda hareket/görünüm bloklarını sürükleyerek ya da Python Modu'nda "
                "kod yazarak programlayabilirsin. 'Çalıştır' ile başlat, 'Kaydet' ile "
                "Çalışmalarım/Karakter-Kodlama klasörüne kaydedebilirsin.")
    except Exception as e:
        return f"YERİNDE Kodlama Aracı açılamadı: {e}"


def _send_or_warn(payload: dict, basari_mesaji: str) -> str:
    if bridge_server.send_command(payload):
        return basari_mesaji
    return _NOT_OPEN_MSG


def kukla_calistir_command() -> str:
    """YERİNDE Kodlama Aracında, tüm karakterlerin programlarını (hangi
    moddaysa - blok ya da Python) aynı anda çalıştırır."""
    return _send_or_warn({"action": "run_program"}, "Programı çalıştırıyorum!")


def kukla_durdur_command() -> str:
    """YERİNDE Kodlama Aracınde çalışmakta olan programı durdurur."""
    return _send_or_warn({"action": "stop_program"}, "Programı durduruyorum!")


# Sahnedeki zemin (yer/döşeme) dokusu ön ayarları - HTML'deki ZEMIN_DOKULARI
# nesnesinin anahtarlarına birebir karşılık gelir.
_ZEMIN_DOKUSU_HARITASI = {
    "düz": "varsayilan", "duz": "varsayilan", "varsayılan": "varsayilan", "varsayilan": "varsayilan",
    "çim": "cim", "cim": "cim", "çimen": "cim", "cimen": "cim", "ot": "cim",
    "ahşap": "ahsap", "ahsap": "ahsap", "tahta": "ahsap",
    "halı": "hali_desenli", "hali": "hali_desenli", "halı desenli": "hali_desenli", "hali desenli": "hali_desenli",
    "halı tüylü": "hali_tuylu", "hali tuylu": "hali_tuylu", "tüylü halı": "hali_tuylu", "tuylu hali": "hali_tuylu",
    "minder": "minder",
    "koltuk": "koltuk",
    "deri": "deri",
    "duvar": "duvar", "taş": "duvar", "tas": "duvar", "taş duvar": "duvar",
    "kiremit": "kiremit", "eski kiremit": "kiremit", "yıpranmış kiremit": "kiremit",
    "kiremit düz": "kiremit_duz", "düz kiremit": "kiremit_duz",
}


def kukla_tema_command(tema: str) -> str:
    """YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, arayüz temasını değiştirir:
    mavi, yeşil ya da krem. 'temayı yeşil yap', 'krem temaya geç' gibi
    komutlarla tetiklenir."""
    haritalar = {"mavi": "blue", "yeşil": "green", "yesil": "green", "krem": "cream"}
    key = (tema or "").strip().lower()
    theme_id = haritalar.get(key)
    if not theme_id:
        return f"'{tema}' tanıdık bir tema değil — mavi, yeşil ya da krem diyebilirsin."
    return _send_or_warn({"action": "set_theme", "theme": theme_id}, f"Temayı {tema} yapıyorum!")


def kukla_kapat_command() -> str:
    """YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener.
    'kodlama aracını kapat', 'aracı kapat' gibi komutlarla tetiklenir. NOT:
    bazı tarayıcılar, script tarafından açılmamış sekmelerin kapatılmasını
    güvenlik nedeniyle engeller — bu durumda kullanıcının sekmeyi elle
    kapatması gerekebilir."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    bridge_server.send_command({"action": "close_tool"})
    return ("Kapatmayı deniyorum — tarayıcın izin verirse sekme kapanacak; bazı "
            "tarayıcılar bunu engelleyebilir, o zaman sekmeyi elle kapatman gerekir.")


def kukla_zemin_dokusu_command(doku: str) -> str:
    """YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, Sahnenin zemin (yer/döşeme)
    dokusunu değiştirir — özellik panelindeki '🟫 Zemin' açılır menüsünden
    seçmiş gibi. Düz (varsayılan), çim, ahşap, halı (desenli), halı (tüylü),
    minder, koltuk, deri, taş duvar, kiremit (eski) ve kiremit (düz)
    dokuları arasından seçilebilir. 'zemine çim dokusu uygula', 'zemini
    ahşap yap', 'zemin dokusunu halı yap' gibi komutlarla tetiklenir."""
    key = (doku or "").strip().lower()
    texture_key = _ZEMIN_DOKUSU_HARITASI.get(key)
    if not texture_key:
        return (f"'{doku}' tanıdık bir zemin dokusu değil — düz, çim, ahşap, halı (desenli/tüylü), "
                "minder, koltuk, deri, taş duvar ya da kiremit (eski/düz) diyebilirsin.")
    return _send_or_warn({"action": "set_ground_texture", "texture": texture_key}, f"Zemin dokusunu {doku} yapıyorum!")


def kukla_ekle_command(isim: str = "") -> str:
    """YERİNDE Kodlama Aracıne yeni bir 3B karakter oluşturur. DİKKAT: bu,
    gerçek (2 boyutlu) Scratch'teki kukla/sprite ekleme komutundan FARKLIDIR —
    sadece YERİNDE Kodlama Aracı açıkken ve bahsedilen 'karakter' bu 3B araca
    aitse kullanılmalıdır."""
    payload = {"action": "add_puppet"}
    if isim:
        payload["name"] = isim
    return _send_or_warn(payload, "Yeni bir karakter oluşturuyorum!")


def kukla_sec_command(tanim: str = "") -> str:
    """YERİNDE Kodlama Aracında 'son'/'ilk' eklenen karakteri seçer."""
    which = "first" if (tanim or "").strip().lower() in ("ilk", "ilki", "ilk eklenen") else "last"
    return _send_or_warn({"action": "select_puppet", "which": which}, "Karakteri seçiyorum!")


def kukla_mod_degistir_command(mod: str) -> str:
    """YERİNDE Kodlama Aracında, seçili karakterin kodlama modunu (blok ya
    da Python) değiştirir."""
    key = (mod or "").strip().lower()
    if key in ("blok", "block", "blok modu"):
        return _send_or_warn({"action": "set_mode", "mode": "blok"}, "Blok Moduna geçiyorum!")
    if key in ("python", "piton", "python modu"):
        return _send_or_warn({"action": "set_mode", "mode": "python"}, "Python Moduna geçiyorum!")
    return "'blok' ya da 'python' diyebilirsin."


def kukla_kaydet_command() -> str:
    """YERİNDE Kodlama Aracındaki projeyi (tüm karakterler, blok/Python
    programlarıyla birlikte) doğrudan Çalışmalarım/Karakter-Kodlama klasörüne
    bir .yerinde dosyası olarak kaydeder."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG
    raw = bridge_server.request_and_wait({"action": "request_project_export"}, timeout=8.0)
    if raw is None:
        return "Araçtan proje verisi alınamadı (zaman aşımı)."
    try:
        data = json.loads(raw)
    except Exception:
        return "Proje verisi okunamadı (beklenmeyen format)."
    if not data.get("ok", True):
        return data.get("message", "Proje dışa aktarılamadı.")
    proje_json = data.get("data")
    if not proje_json:
        return "Proje verisi boş geldi."

    from actions.code_tools import ensure_workspace_folder
    import time

    folder = ensure_workspace_folder("Karakter-Kodlama")
    target = folder / f"karakter-projem {time.strftime('%Y-%m-%d %H.%M')}.yerinde"
    try:
        target.write_text(proje_json, encoding="utf-8")
    except Exception as e:
        return f"Proje kaydedilemedi: {e}"
    return f"Proje kaydedildi: {target.name} (Çalışmalarım/Karakter-Kodlama klasörü)."


def kukla_ac_command(dosya_adi: str = "") -> str:
    """Çalışmalarım/Karakter-Kodlama klasöründe verilen isme uyan (ya da isim
    verilmezse en son kaydedilen) bir .yerinde dosyasını bulup açık olan
    YERİNDE Kodlama Aracıne yükler."""
    if not bridge_server.is_client_connected():
        return _NOT_OPEN_MSG

    from actions.code_tools import ensure_workspace_folder

    folder = ensure_workspace_folder("Karakter-Kodlama")
    candidates = sorted(folder.glob("*.yerinde"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return "Çalışmalarım/Karakter-Kodlama klasöründe hiç .yerinde dosyası bulunamadı."

    name_key = (dosya_adi or "").strip().lower()
    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
    chosen = matches[0] if matches else candidates[0]

    try:
        raw = chosen.read_text(encoding="utf-8")
    except Exception as e:
        return f"Dosya okunamadı: {e}"
    ok = bridge_server.send_command({"action": "load_project_data", "data": raw})
    if not ok:
        return _NOT_OPEN_MSG
    return f"{chosen.name} projesini yüklüyorum!"


# Blockly'deki dahili blok türü adı -> kullanıcıya gösterilecek Türkçe etiket.
# Hem karakter (kukla) hem de Sahne blok paletindeki TÜM "yığın" (komut)
# bloklarını kapsar (bkz. yerinde-kodlama-araci.html: KUKLA_TOOLBOX / SAHNE_TOOLBOX).
_BLOK_ETIKETLERI = {
    "kukla_ileri_git": "ileri git", "kukla_geri_git": "geri git",
    "kukla_sag_don": "sağa dön", "kukla_sol_don": "sola dön",
    "kukla_zipla": "zıpla", "kukla_kenara_deginde_sektir": "kenara değince sektir",
    "kukla_x_degistir": "x konumunu değiştir", "kukla_z_degistir": "z konumunu değiştir",
    "kukla_yone_bak": "yöne bak", "kukla_kaydirarak_git": "kaydırarak git",
    "kukla_konuma_git": "konuma git",
    "kukla_bekle_saniye": "bekle",
    "kukla_konus": "konuş", "kukla_konus_sure": "süreli konuş", "kukla_dusun": "düşün",
    "kukla_renk_degistir": "renk değiştir",
    "kukla_boyut_ayarla": "boyut ayarla", "kukla_boyut_degistir": "boyut değiştir",
    "kukla_goster_gizle": "göster/gizle",
    "kukla_sonraki_kostum": "sonraki kostüme geç", "kukla_kostum_degistir": "kostüm değiştir",
    "kukla_arkaplan_degistir": "arkaplanı değiştir", "kukla_sonraki_arkaplan": "sonraki arkaplana geç",
    "kukla_bip_cal": "bip sesi çal", "kukla_ses_cal": "nota çal",
    "kukla_tumunu_durdur": "tümünü durdur",
    "kukla_bayrak_tiklaninca": "bayrağa tıklanınca", "kukla_tusa_basilinca": "tuşa basılınca",
    "kukla_sonsuza_kadar": "sonsuza kadar tekrarla",
    "kukla_zamanlayici_sifirla": "zamanlayıcıyı sıfırla", "kukla_sor_bekle": "sor ve bekle",
}

# Bu bloklarda "deger" parametresi SAYISAL değil, METİN olarak gönderilir
# (konuşma balonu / soru metni gibi) — sayıya çevirmeye ÇALIŞMA.
_METIN_DEGERLI_BLOKLAR = {"kukla_konus", "kukla_konus_sure", "kukla_dusun", "kukla_sor_bekle"}


def karakter_blok_ekle_command(blok: str, deger: str = "") -> str:
    """YERİNDE Kodlama Aracında (seçili karakter YA DA Sahne Blok Modu'ndayken)
    yeni bir kodlama bloğu ekler — sanki sol menüden sürükleyip bırakmış gibi.
    'blok' Blockly'deki dahili blok türü adıdır (ör. 'kukla_ileri_git');
    'deger' verilmişse (ör. '5', '90', '3' ya da bir konuşma/soru metni gibi
    'Merhaba!') bloğun ana girişine (MESAFE/DERECE/SANIYE/MIKTAR/METIN/SORU
    vb.) uygulanır — verilmezse toolbox'taki varsayılan değer kullanılır.
    Blok, o an workspace'te açık olan ilk bloklar zincirinin en altına
    otomatik eklenir; hiç blok yoksa (ya da bir 'olay' bloğuysa, ör. bayrağa
    tıklanınca ya da tuşa basılınca) serbest bırakılır."""
    payload = {"action": "add_block", "block_type": blok}
    if deger:
        if blok in _METIN_DEGERLI_BLOKLAR:
            payload["value"] = deger
        else:
            try:
                payload["value"] = float(deger) if "." in deger else int(deger)
            except ValueError:
                pass
    isim = _BLOK_ETIKETLERI.get(blok, blok)
    return _send_or_warn(payload, f"'{isim}' bloğunu ekliyorum!")


def karakter_blok_sil_command() -> str:
    """YERİNDE Kodlama Aracında (seçili karakter YA DA Sahne Blok Modu'ndayken)
    bir kodlama bloğunu siler. Öncelik: sesli komutla en son eklenen blok
    (varsa) silinir; yoksa mevcut bloklar zincirinin en sonundaki blok
    silinir. 'bloğu sil', 'son bloğu sil', 'son eklenen bloğu sil' gibi
    komutlarla tetiklenir — DİKKAT: bu, karakterin/Sahnenin kendisini silmekle
    (ör. 'karakteri sil') KARIŞTIRILMAMALIDIR, sadece KOD BLOĞUNU siler."""
    return _send_or_warn({"action": "delete_block"}, "Bloğu siliyorum!")
