"""
ToolExecutor — Gemini modundaki main.py._execute_tool ile aynı araçları,
Ollama (çevrimdışı) modu için senkron biçimde çalıştırır.

Not: toggle_webcam ve analyze_screen gibi Gemini vision'a bağımlı araçlar
çevrimdışı modda desteklenmez; kullanıcıya bunu açıkça bildirir.
"""

from __future__ import annotations

import traceback
from pathlib import Path

from memory.memory_manager import load_memory, update_memory, delete_memory
from actions.open_app import open_app, close_app, set_last_opened
from actions.sys_info import sys_info
from actions.calendar import get_calendar_events, add_calendar_event, delete_calendar_event
from actions.reminders import get_reminders, add_reminder
from actions.browser import browser_control
from actions.shell import shell_run
from actions.whatsapp import send_whatsapp_message, save_whatsapp_contact
from actions.media import play_media
from actions.weather import get_weather_summary, get_forecast_summary
from actions.youtube_stats import get_youtube_channel_report
from actions.media_capture import take_photo, record_video, open_camera_preview, close_camera_preview
from actions.document_tools import analyze_document, read_document_aloud
from actions.zumre_tutanagi import zumre_tutanagi_olustur
from actions.belge_referanslari import referans_belge_kaydet
from actions.sinav_uret import sinav_olustur
from actions.yillik_plan import gunluk_plan_olustur, yillik_plan_guncelle
from actions.kulup_belgesi import kulup_calisma_plani_olustur
from actions.olcek_hazirla import olcek_hazirla
from actions.code_tools import save_python_file
from actions.type_text import type_text
from actions.system_media import system_volume, media_control, save_active_document, shutdown_assistant
from actions.office_blank import create_blank_document, normalize_kind, KINDS as OFFICE_KINDS
from actions import blender_bridge
from actions import freecad_bridge
from actions.office_format import office_format
from actions.mouse_control import mouse_control
from actions.voice_sample import record_voice_sample
from actions.keyboard_control import press_key
from actions.office_media import insert_image, word_export_pdf, excel_command, image_adjust
from actions.streaming import play_stream
from actions.whatsapp_call import whatsapp_call, calibrate_call_button
from actions import piper_dataset
from actions.scratch_bridge import scratch_command
from actions.office_show import slideshow, add_transition, add_animation, clear_effects, slide_edit
from actions.office_content import write_topic


OFFLINE_UNSUPPORTED = {
    "analyze_screen": "Ekran analizi çevrimdışı (Ollama) modda desteklenmiyor — bunun için Gemini moduna geç.",
}


_SAFE_WRAP = True


class ToolExecutor:
    """Ollama sohbet döngüsünün çağırdığı, senkron araç yürütücüsü."""

    def __init__(self, webcam=None, garden=None, ui=None):
        # webcam: paylaşımlı WebcamStreamer (arayüz içi canlı önizleme için).
        # Verilmezse eski davranışa (ayrı OpenCV penceresi) düşer.
        # garden: paylaşımlı GardenCamStreamer (bahçe kamerası / DVRIP).
        self.webcam = webcam
        self.garden = garden
        self.ui = ui

    def _capture_source(self):
        """FOTO/VİDEO/DURAKLAT ve 'fotoğraf çek'/'video kaydet' sesli
        komutları için: o an hangi kamera akışı canlıysa (bahçe kamerası
        ya da webcam) onu döndürür. GardenCamStreamer, WebcamStreamer/
        VisionEngine ile birebir aynı arayüzü (is_active/get_latest_frame)
        sunduğundan take_photo/record_video hangi kaynağı aldığını bilmeden
        ikisiyle de çalışır."""
        if self.garden is not None and getattr(self.garden, "is_active", False):
            return self.garden
        return self.webcam

    def execute(self, name: str, args: dict):
        """Araç çalıştırma — HİÇBİR hata programı düşürmez, Türkçe mesaja çevrilir."""
        try:
            return self._execute_inner(name, args)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"'{name}' aracı çalışırken hata oluştu: {e}"

    def _execute_inner(self, name: str, args: dict) -> str:
        args = dict(args or {})
        try:
            if name in OFFLINE_UNSUPPORTED:
                return OFFLINE_UNSUPPORTED[name]

            if name == "save_memory":
                cat = args.get("category", "notes")
                key = args.get("key", "")
                val = args.get("value", "")
                if key and val:
                    update_memory({cat: {key: {"value": val}}})
                return "ok"

            if name == "delete_memory":
                return delete_memory(
                    args.get("category", ""),
                    args.get("key", ""),
                    args.get("match_text", ""),
                )

            if name == "open_app":
                app_l = normalize_kind(str(args.get("app_name", "")))
                if app_l in ("blender", "tasarım", "tasarim", "3d"):
                    set_last_opened("blender")
                    return blender_bridge.launch_blender_with_bridge()
                if app_l in ("freecad", "free cad"):
                    set_last_opened("freecad")
                    return freecad_bridge.launch_freecad_with_bridge()
                if app_l in OFFICE_KINDS:
                    blank = create_blank_document(app_l)
                    if blank:
                        set_last_opened(app_l)   # "kapat" hedefi bilinsin
                        return blank  # boş belge doğrudan açıldı
                return open_app(args.get("app_name", "")) or f"{args.get('app_name')} açıldı."

            if name == "close_app":
                return close_app(args.get("app_name", "")) or f"{args.get('app_name')} kapatıldı."

            if name == "sys_info":
                return sys_info(args.get("query", "all")) or "Bilgi alındı."

            if name == "get_forecast":
                return get_forecast_summary(int(args.get("days", 7) or 7))

            if name == "get_weather":
                return get_weather_summary(args.get("location") or None) or "Hava durumu bilgisi alındı."

            if name == "get_calendar_events":
                return get_calendar_events(
                    args.get("query", "today"), int(args.get("limit", 6) or 6)
                ) or "Takvim bilgisi alındı."

            if name == "add_calendar_event":
                return add_calendar_event(
                    args.get("title", ""),
                    args.get("start_iso", ""),
                    args.get("end_iso", ""),
                    args.get("notes", ""),
                    args.get("location", ""),
                    args.get("calendar_name", ""),
                    bool(args.get("all_day", False)),
                ) or "Takvim etkinliği eklendi."

            if name == "delete_calendar_event":
                return delete_calendar_event(
                    args.get("title", ""),
                    args.get("start_iso", ""),
                    args.get("calendar_name", ""),
                    bool(args.get("delete_all_matches", False)),
                ) or "Takvim etkinliği silindi."

            if name == "get_reminders":
                return get_reminders(
                    args.get("query", "upcoming"),
                    int(args.get("limit", 8) or 8),
                    args.get("list_name", ""),
                ) or "Anımsatıcı bilgisi alındı."

            if name == "add_reminder":
                return add_reminder(
                    args.get("title", ""),
                    args.get("due_iso", ""),
                    args.get("notes", ""),
                    args.get("list_name", ""),
                    args.get("priority", ""),
                    bool(args.get("all_day", False)),
                ) or "Anımsatıcı eklendi."

            if name == "browser_control":
                return browser_control(
                    args.get("action"), args.get("url"), args.get("query")
                ) or "Tamam."

            if name == "shell_run":
                return shell_run(args.get("command", "")) or "Komut çalıştırıldı."

            if name == "play_media":
                return play_media(
                    args.get("query", ""),
                    args.get("provider", "auto"),
                    bool(args.get("autoplay", True)),
                ) or "Medya oynatma başlatıldı."

            if name == "get_youtube_channel_report":
                return get_youtube_channel_report(
                    args.get("query", "overview"),
                    args.get("handle", ""),
                    int(args.get("video_limit", 6) or 6),
                ) or "YouTube kanal raporu alındı."

            if name == "send_whatsapp_message":
                return send_whatsapp_message(
                    args.get("message", ""),
                    args.get("phone_number", ""),
                    args.get("recipient_name", ""),
                    bool(args.get("send_now", False)),
                    args.get("app_target", "auto"),
                ) or "WhatsApp işlemi tamamlandı."

            if name == "save_whatsapp_contact":
                return save_whatsapp_contact(
                    args.get("display_name", ""),
                    args.get("phone_number", ""),
                    args.get("aliases", ""),
                ) or "WhatsApp kişisi kaydedildi."

            if name == "take_photo":
                return take_photo(self._capture_source()) or "Fotoğraf çekildi."

            if name == "record_video":
                return record_video(args.get("seconds", 5),
                                    self._capture_source()) or "Video kaydedildi."

            if name == "toggle_webcam":
                action = str(args.get("action", "start")).lower()
                # Paylaşımlı akış varsa: arayüz içi (animasyonun üstünde) önizleme —
                # Gemini modundakiyle aynı görünüm. Sesli komut ve KAMERA düğmesi
                # aynı kamerayı kontrol eder.
                if self.webcam is not None:
                    if action == "stop":
                        self.webcam.stop()
                        if self.ui:
                            self.ui.set_webcam_active(False)
                        return "Kamera kapatıldı."
                    status = self.webcam.start()
                    if status in ("ok", "already_active"):
                        if self.ui:
                            self.ui.set_webcam_active(True)
                        return ("Kamera açıldı — canlı görüntü ekranda. "
                                "(Çevrimdışı modda görüntü analiz edilmiyor; analiz için Gemini moduna geç.)")
                    err = getattr(self.webcam, "last_error", None) or "bilinmeyen hata"
                    return f"Kamera açılamadı: {err}"
                # Yedek: ayrı OpenCV penceresi
                if action == "stop":
                    return close_camera_preview()
                return (open_camera_preview() +
                        " (Çevrimdışı modda görüntü analiz edilmiyor, sadece canlı önizleme "
                        "gösteriliyor — analiz için Gemini moduna geç.)")

            if name == "toggle_garden_cam":
                action = str(args.get("action", "start")).lower()
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                if action == "stop":
                    self.garden.stop()
                    if self.ui:
                        self.ui.set_garden_active(False)
                    return "Bahçe kamerası kapatıldı (kamera uyuyabilir)."
                # Webcam açıksa kapat — tek önizleme paneli.
                if self.webcam is not None and getattr(self.webcam, "is_active", False):
                    self.webcam.stop()
                    if self.ui:
                        self.ui.set_webcam_active(False)
                status = self.garden.start()
                if status in ("ok", "already_active"):
                    if self.ui:
                        self.ui.set_garden_active(True)
                    return ("Bahçe kamerası açıldı — bahçenin canlı görüntüsü "
                            "ekranda. Yön değiştirmek istersen söyleyebilirsin.")
                err = getattr(self.garden, "last_error", None) or status
                return (f"Bahçe kamerası açılamadı: {err}. Güneş enerjili kamera "
                        "uykuda olabilir; önce 'bahçe kamerasını uyandır' de.")

            if name == "wake_garden_cam":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                status = self.garden.wake()
                if status == "ok":
                    return ("Bahçe kamerası uyandırıldı. Şimdi 'bahçe kamerasını "
                            "aç' diyerek görüntüyü başlatabilirsin.")
                err = getattr(self.garden, "last_error", None) or status
                return f"Bahçe kamerası uyandırılamadı: {err}"

            if name == "garden_ptz":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                direction = str(args.get("direction", "")).strip().lower()
                status = self.garden.ptz(direction)
                labels = {
                    "left": "sola", "right": "sağa", "up": "yukarı",
                    "down": "aşağı", "center": "ortaya", "stop": "durdu",
                }
                if status == "ok":
                    return "Bahçe kamerası %s döndürüldü." % labels.get(direction, direction)
                return status

            if name == "garden_ptz_start":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                direction = str(args.get("direction", "")).strip().lower()
                status = self.garden.ptz_start(direction)
                if status == "ok":
                    return "Bahçe kamerası %s yönünde dönüyor (dur deyince veya tuşu bırakınca durur)." % direction
                return status

            if name == "garden_ptz_stop":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                status = self.garden.ptz_stop()
                return "Bahçe kamerası durdu." if status == "ok" else status

            if name == "garden_horn":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                on = not getattr(self, "_garden_horn_on", False)
                status = self.garden.set_horn(on)
                if status == "ok":
                    self._garden_horn_on = on
                    return "Alarm çalıyor." if on else "Alarm durduruldu."
                return status

            if name == "garden_talk":
                if self.garden is None:
                    return "Bahçe kamerası bu modda bağlı değil (dvrip kurulu mu?)."
                if getattr(self, "_garden_talking", False):
                    self._garden_talking = False
                    self.garden.talk_stop()
                    return "İki yönlü ses kapatıldı."
                status = self.garden.talk_start()
                if status == "ok":
                    self._garden_talking = True
                    return "Kameraya konuşuyorsunuz — tekrar deyince kapanır."
                return status

            if name == "zumre_tutanagi_olustur":
                return zumre_tutanagi_olustur(
                    args.get("donem_turu", ""),
                    args.get("toplanti_tarihi", ""),
                    args.get("toplanti_saati", ""),
                    args.get("toplanti_no", ""),
                    args.get("ders_yili", ""),
                    args.get("ek_talimat", ""),
                    args.get("dosya_yolu", ""),
                    args.get("ders", ""),
                ) or "Zümre tutanağı hazırlandı."

            if name == "referans_belge_kaydet":
                return referans_belge_kaydet(
                    args.get("tur", ""), args.get("dosya_yolu", "")
                ) or "Referans kaydedildi."

            if name == "sinav_olustur":
                return sinav_olustur(
                    args.get("ders", "bilişim"),
                    args.get("sinif", "5"),
                    args.get("sinav_no", "1"),
                    args.get("senaryo_no", "1"),
                    args.get("donem", "2"),
                    args.get("soru_sayisi", 0),
                    args.get("konu_kapsam", ""),
                    args.get("ek_talimat", ""),
                    args.get("ksdt_dosya_yolu", ""),
                    args.get("yillik_plan_dosya_yolu", ""),
                    args.get("soru_tipi", "karışık"),
                ) or "Sınav hazırlandı."

            if name == "yillik_plan_guncelle":
                return yillik_plan_guncelle(
                    args.get("ders", "bilişim"),
                    args.get("sinif", "5"),
                    args.get("egitim_yili", ""),
                    args.get("dosya_yolu", ""),
                ) or "Yıllık plan güncellendi."

            if name == "gunluk_plan_olustur":
                return gunluk_plan_olustur(
                    args.get("ders", "bilişim"),
                    args.get("sinif", "5"),
                    args.get("hafta_no", ""),
                    args.get("konu_arama", ""),
                    args.get("ek_talimat", ""),
                    args.get("yillik_plan_dosya_yolu", ""),
                ) or "Günlük plan hazırlandı."

            if name == "kulup_calisma_plani_olustur":
                return kulup_calisma_plani_olustur(
                    args.get("egitim_yili", ""),
                    args.get("katilimci_toplam", ""),
                    args.get("katilimci_kiz", ""),
                    args.get("katilimci_erkek", ""),
                    args.get("danisman_adi", ""),
                    bool(args.get("etkinlikleri_yenile", False)),
                    args.get("ek_talimat", ""),
                    args.get("dosya_yolu", ""),
                ) or "Kulüp çalışma planı hazırlandı."

            if name == "olcek_hazirla":
                return olcek_hazirla(
                    args.get("ders", "bilişim"),
                    args.get("sinif", "5/A"),
                    args.get("donem", ""),
                    args.get("egitim_yili", ""),
                    args.get("ogrenciler", ""),
                    args.get("puantaj_dosya_yolu", ""),
                    args.get("dosya_yolu", ""),
                ) or "Ölçek hazırlandı."

            if name == "analyze_document":
                return analyze_document(
                    args.get("file_path", ""), args.get("query", "")
                ) or "Belge analiz edildi."

            if name == "read_document_aloud":
                return read_document_aloud(args.get("file_path", "")) or "Belge sesli okundu."

            if name == "system_volume":
                return system_volume(str(args.get("action", "")), int(args.get("step", 10) or 10))

            if name == "media_control":
                return media_control(str(args.get("action", "")))

            if name == "arkaplan_command":
                if not self.ui:
                    return "Arayüz bağlantısı yok."
                raw = str(args.get("mod", "")).strip().lower()
                mod = {"açık": "acik", "acik": "acik", "aydınlık": "acik",
                       "koyu": "koyu", "karanlık": "koyu",
                       "sade": "sade", "normal": "sade", "normale": "sade"}.get(raw, raw)
                if mod in ("acik", "koyu"):
                    return self.ui.set_bg_image_builtin(mod)
                if mod == "sade":
                    return self.ui.clear_bg_image_voice()
                return "Tanımadığım bir arkaplan modu — 'açık', 'koyu' ya da 'sade' diyebilirsin."

            if name == "tema_command":
                if not self.ui:
                    return "Arayüz bağlantısı yok."
                return self.ui.set_theme_by_voice(str(args.get("mod", "")))

            if name == "save_active_document":
                return save_active_document()

            if name == "office_format":
                return office_format(str(args.get("action", "")), str(args.get("value", "")))

            if name == "mouse_control":
                return mouse_control(str(args.get("action", "")),
                                     str(args.get("direction", "")),
                                     int(args.get("amount", 0) or 0))

            if name == "record_voice_sample":
                log = self.ui.write_log if self.ui else (lambda m: None)
                return record_voice_sample(int(args.get("seconds", 10) or 10), on_log=log)

            if name == "insert_image":
                return insert_image(str(args.get("source", "")))

            if name == "whatsapp_call":
                log = self.ui.write_log if self.ui else (lambda m: None)
                return whatsapp_call(str(args.get("contact", "")),
                                     str(args.get("kind", "voice")), on_log=log)

            if name == "calibrate_whatsapp":
                log = self.ui.write_log if self.ui else (lambda m: None)
                return calibrate_call_button(str(args.get("kind", "voice")), on_log=log)

            if name == "play_stream":
                return play_stream(str(args.get("service", "")), str(args.get("query", "")))

            if name == "scratch_command":
                return scratch_command(str(args.get("action", "")),
                                       str(args.get("value", "")),
                                       str(args.get("text", "")),
                                       str(args.get("times", "")),
                                       str(args.get("key", "")))

            if name == "blockly_command":
                from actions.blockly_games import open_blockly_game
                return open_blockly_game(str(args.get("key", "")))

            if name == "blockly_games_kapat_command":
                from actions.blockly_games import blockly_games_kapat_command
                return blockly_games_kapat_command()

            if name == "akis_command":
                from actions.akis_semasi import open_akis_semasi
                return open_akis_semasi()

            if name == "akis_semasi_kapat_command":
                from actions.akis_semasi import akis_semasi_kapat_command
                return akis_semasi_kapat_command()

            if name == "carkifelek_command":
                from actions.carkifelek import open_carkifelek
                return open_carkifelek()

            if name == "carkifelek_kapat_command":
                from actions.carkifelek import carkifelek_kapat_command
                return carkifelek_kapat_command()

            if name == "satranc_command":
                from actions.satranc import open_satranc
                return open_satranc()

            if name == "satranc_kapat_command":
                from actions.satranc import satranc_kapat_command
                return satranc_kapat_command()

            if name == "cin_damasi_command":
                from actions.cin_damasi import open_cin_damasi
                return open_cin_damasi()

            if name == "cin_damasi_kapat_command":
                from actions.cin_damasi import cin_damasi_kapat_command
                return cin_damasi_kapat_command()

            if name == "robotik_simulator_command":
                from actions.robotik_simulator import open_robotik_simulator
                return open_robotik_simulator()

            if name == "robotik_simulator_kapat_command":
                from actions.robotik_simulator import robotik_simulator_kapat_command
                return robotik_simulator_kapat_command()

            if name == "tasarim_studyosu_command":
                from actions.tasarim_studyosu import open_tasarim_studyosu
                return open_tasarim_studyosu()

            if name == "robot_tasarim_command":
                from actions.robot_tasarim import open_robot_tasarim_araci
                return open_robot_tasarim_araci()

            if name == "donanim_atolyesi_command":
                from actions.donanim_atolyesi import open_donanim_atolyesi
                return open_donanim_atolyesi()

            if name == "donanim_anladim_command":
                from actions.donanim_atolyesi import anladim_command
                return anladim_command()

            if name == "donanim_parca_ekle_command":
                from actions.donanim_atolyesi import parca_ekle_command
                return parca_ekle_command(args.get("parca", ""))

            if name == "donanim_parca_sok_command":
                from actions.donanim_atolyesi import parca_sok_command
                return parca_sok_command(args.get("parca", ""))

            if name == "donanim_tema_command":
                from actions.donanim_atolyesi import tema_command
                return tema_command(args.get("tema", ""))

            if name == "resim_pdf_command":
                from actions.resim_pdf_atolyesi import open_resim_pdf_atolyesi
                return open_resim_pdf_atolyesi()

            if name == "resim_pdf_ayar_command":
                from actions.resim_pdf_atolyesi import resim_pdf_ayar_command
                return resim_pdf_ayar_command(
                    args.get("arac", ""), args.get("eylem", ""), str(args.get("deger", "")))

            if name == "video_atolyesi_command":
                from actions.video_atolyesi import open_video_atolyesi
                return open_video_atolyesi()

            if name == "video_atolyesi_ayar_command":
                from actions.video_atolyesi import video_atolyesi_ayar_command
                return video_atolyesi_ayar_command(
                    args.get("sekme", ""), args.get("eylem", ""), str(args.get("deger", "")))

            if name == "kukla_kodlama_command":
                from actions.kukla_kodlama import open_kukla_kodlama_atolyesi
                return open_kukla_kodlama_atolyesi()

            if name == "kukla_calistir_command":
                from actions.kukla_kodlama import kukla_calistir_command
                return kukla_calistir_command()

            if name == "kukla_durdur_command":
                from actions.kukla_kodlama import kukla_durdur_command
                return kukla_durdur_command()

            if name == "kukla_ekle_command":
                from actions.kukla_kodlama import kukla_ekle_command
                return kukla_ekle_command(args.get("isim", ""))

            if name == "kukla_sec_command":
                from actions.kukla_kodlama import kukla_sec_command
                return kukla_sec_command(args.get("tanim", ""))

            if name == "kukla_mod_degistir_command":
                from actions.kukla_kodlama import kukla_mod_degistir_command
                return kukla_mod_degistir_command(args.get("mod", ""))

            if name == "kukla_tema_command":
                from actions.kukla_kodlama import kukla_tema_command
                return kukla_tema_command(args.get("tema", ""))

            if name == "kukla_kapat_command":
                from actions.kukla_kodlama import kukla_kapat_command
                return kukla_kapat_command()

            if name == "kukla_zemin_dokusu_command":
                from actions.kukla_kodlama import kukla_zemin_dokusu_command
                return kukla_zemin_dokusu_command(args.get("doku", ""))

            if name == "kukla_kaydet_command":
                from actions.kukla_kodlama import kukla_kaydet_command
                return kukla_kaydet_command()

            if name == "kukla_ac_command":
                from actions.kukla_kodlama import kukla_ac_command
                return kukla_ac_command(args.get("dosya_adi", ""))

            if name == "karakter_blok_ekle_command":
                from actions.kukla_kodlama import karakter_blok_ekle_command
                return karakter_blok_ekle_command(args.get("blok", ""), str(args.get("deger", "")))

            if name == "karakter_blok_sil_command":
                from actions.kukla_kodlama import karakter_blok_sil_command
                return karakter_blok_sil_command()

            if name == "bilisim_robotik_atolyesi_command":
                from actions.bilisim_robotik_atolyesi import open_bilisim_robotik_atolyesi
                return open_bilisim_robotik_atolyesi()

            if name == "bilisim_robotik_unite_gec_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_unite_gec_command
                return bilisim_robotik_unite_gec_command(args.get("unite", ""))

            if name == "bilisim_robotik_tema_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_tema_command
                return bilisim_robotik_tema_command(args.get("tema", ""))

            if name == "bilisim_robotik_kapat_command":
                from actions.bilisim_robotik_atolyesi import bilisim_robotik_kapat_command
                return bilisim_robotik_kapat_command()

            if name == "bilisim_labirent_komut_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_komut_command
                return bilisim_labirent_komut_command(args.get("komut", ""), args.get("labirent", "1"))

            if name == "bilisim_labirent_calistir_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_calistir_command
                return bilisim_labirent_calistir_command(args.get("labirent", "1"))

            if name == "bilisim_labirent_geri_al_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_geri_al_command
                return bilisim_labirent_geri_al_command(args.get("labirent", "1"))

            if name == "bilisim_labirent_temizle_command":
                from actions.bilisim_robotik_atolyesi import bilisim_labirent_temizle_command
                return bilisim_labirent_temizle_command(args.get("labirent", "1"))

            if name == "bilisim_kart_cevir_command":
                from actions.bilisim_robotik_atolyesi import bilisim_kart_cevir_command
                return bilisim_kart_cevir_command(args.get("kart_no", ""))

            if name == "bilisim_quiz_cevapla_command":
                from actions.bilisim_robotik_atolyesi import bilisim_quiz_cevapla_command
                return bilisim_quiz_cevapla_command(args.get("secenek", ""))

            if name == "bilisim_ilerlemeyi_sifirla_command":
                from actions.bilisim_robotik_atolyesi import bilisim_ilerlemeyi_sifirla_command
                return bilisim_ilerlemeyi_sifirla_command()

            if name == "bilisim_web_ekle_command":
                from actions.bilisim_robotik_atolyesi import bilisim_web_ekle_command
                return bilisim_web_ekle_command(args.get("eleman", ""))

            if name == "pico_devre_atolyesi_command":
                from actions.pico_devre_atolyesi import open_pico_devre_atolyesi
                return open_pico_devre_atolyesi()

            if name == "pico_kart_degistir_command":
                from actions.pico_devre_atolyesi import pico_kart_degistir_command
                return pico_kart_degistir_command(args.get("kart", ""))

            if name == "pico_bilesen_ekle_command":
                from actions.pico_devre_atolyesi import pico_bilesen_ekle_command
                return pico_bilesen_ekle_command(args.get("bilesen", ""))

            if name == "pico_bilesen_sil_command":
                from actions.pico_devre_atolyesi import pico_bilesen_sil_command
                return pico_bilesen_sil_command(args.get("bilesen", ""))

            if name == "pico_bilesen_dondur_command":
                from actions.pico_devre_atolyesi import pico_bilesen_dondur_command
                return pico_bilesen_dondur_command(args.get("bilesen", ""))

            if name == "pico_bilesen_tasi_command":
                from actions.pico_devre_atolyesi import pico_bilesen_tasi_command
                return pico_bilesen_tasi_command(
                    args.get("bilesen", ""), args.get("yon", ""), str(args.get("miktar", "1")))

            if name == "pico_kablo_sil_command":
                from actions.pico_devre_atolyesi import pico_kablo_sil_command
                return pico_kablo_sil_command(
                    args.get("bilesen1", ""), args.get("pin1", ""),
                    args.get("bilesen2", ""), args.get("pin2", ""))

            if name == "pico_blok_ekle_command":
                from actions.pico_devre_atolyesi import pico_blok_ekle_command
                return pico_blok_ekle_command(
                    args.get("blok", ""), str(args.get("pin", "")), str(args.get("pin2", "")),
                    str(args.get("deger", "")), str(args.get("yon", "")), str(args.get("birim", "")))

            if name == "pico_blok_sil_command":
                from actions.pico_devre_atolyesi import pico_blok_sil_command
                return pico_blok_sil_command()

            if name == "pico_mod_degistir_command":
                from actions.pico_devre_atolyesi import pico_mod_degistir_command
                return pico_mod_degistir_command(args.get("mod", ""))

            if name == "pico_tema_degistir_command":
                from actions.pico_devre_atolyesi import pico_tema_degistir_command
                return pico_tema_degistir_command(args.get("tema", ""))

            if name == "pico_yakinlastir_command":
                from actions.pico_devre_atolyesi import pico_yakinlastir_command
                return pico_yakinlastir_command(args.get("yon", ""))

            if name == "pico_calistir_command":
                from actions.pico_devre_atolyesi import pico_calistir_command
                return pico_calistir_command()

            if name == "pico_durdur_command":
                from actions.pico_devre_atolyesi import pico_durdur_command
                return pico_durdur_command()

            if name == "pico_kaydet_command":
                from actions.pico_devre_atolyesi import pico_kaydet_command
                return pico_kaydet_command()

            if name == "pico_ac_command":
                from actions.pico_devre_atolyesi import pico_ac_command
                return pico_ac_command(args.get("dosya_adi", ""))

            if name == "pico_kodu_indir_command":
                from actions.pico_devre_atolyesi import pico_kodu_indir_command
                return pico_kodu_indir_command()

            if name == "pico_bagla_command":
                from actions.pico_devre_atolyesi import pico_bagla_command
                return pico_bagla_command(
                    args.get("bilesen1", ""), args.get("pin1", ""),
                    args.get("bilesen2", ""), args.get("pin2", ""))

            if name == "pico_seri_monitor_command":
                from actions.pico_devre_atolyesi import pico_seri_monitor_command
                return pico_seri_monitor_command(args.get("durum", "ac"))

            if name == "pico_kapat_command":
                from actions.pico_devre_atolyesi import pico_kapat_command
                return pico_kapat_command()

            if name == "tasarim_tema_command":
                from actions.tasarim_studyosu import tasarim_tema_command
                return tasarim_tema_command(args.get("tema", ""))

            if name == "tasarim_kapat_command":
                from actions.tasarim_studyosu import tasarim_kapat_command
                return tasarim_kapat_command()

            if name == "tasarim_ekle_sekil_command":
                from actions.tasarim_studyosu import ekle_sekil_command
                return ekle_sekil_command(args.get("sekil", ""))

            if name == "tasarim_robot_parca_ekle_command":
                from actions.tasarim_studyosu import robot_parca_ekle_command
                return robot_parca_ekle_command(args.get("parca", ""))

            if name == "tasarim_renk_command":
                from actions.tasarim_studyosu import renk_command
                return renk_command(args.get("renk", ""))

            if name == "tasarim_malzeme_command":
                from actions.tasarim_studyosu import malzeme_command
                return malzeme_command(args.get("malzeme", ""))

            if name == "tasarim_doku_uygula_command":
                from actions.tasarim_studyosu import doku_uygula_command
                return doku_uygula_command(args.get("doku", ""))

            if name == "tasarim_tasi_command":
                from actions.tasarim_studyosu import tasi_command
                return tasi_command(args.get("yon", ""))

            if name == "tasarim_boyutlandir_command":
                from actions.tasarim_studyosu import boyutlandir_command
                return boyutlandir_command(args.get("yon", ""), args.get("eksen"))

            if name == "tasarim_dondur_command":
                from actions.tasarim_studyosu import dondur_command
                return dondur_command(args.get("yon", ""))

            if name == "tasarim_donusu_baslat_command":
                from actions.tasarim_studyosu import donusu_baslat_command
                return donusu_baslat_command(args.get("eksen", "y"))

            if name == "tasarim_donusu_durdur_command":
                from actions.tasarim_studyosu import donusu_durdur_command
                return donusu_durdur_command()

            if name == "tasarim_yorunge_baslat_command":
                from actions.tasarim_studyosu import yorunge_baslat_command
                return yorunge_baslat_command(args.get("eksen", "y"))

            if name == "tasarim_yorunge_durdur_command":
                from actions.tasarim_studyosu import yorunge_durdur_command
                return yorunge_durdur_command()

            if name == "tasarim_nesne_sec_command":
                from actions.tasarim_studyosu import nesne_sec_command
                return nesne_sec_command(args.get("tanim", ""), args.get("renk", ""))

            if name == "tasarim_stl_kaydet_command":
                from actions.tasarim_studyosu import stl_kaydet_command
                return stl_kaydet_command(args.get("isim", ""))

            if name == "tasarim_stl_ac_command":
                from actions.tasarim_studyosu import stl_ac_command
                return stl_ac_command(args.get("dosya_adi", ""))

            if name == "tasarim_glb_kaydet_command":
                from actions.tasarim_studyosu import glb_kaydet_command
                return glb_kaydet_command(args.get("isim", ""))

            if name == "tasarim_glb_ac_command":
                from actions.tasarim_studyosu import glb_ac_command
                return glb_ac_command(args.get("dosya_adi", ""))

            if name == "tasarim_glb_indir_command":
                from actions.tasarim_studyosu import glb_indir_command
                return glb_indir_command()

            if name == "tasarim_nesne_ortala_command":
                from actions.tasarim_studyosu import nesne_ortala_command
                return nesne_ortala_command()

            if name == "tasarim_kopyala_command":
                from actions.tasarim_studyosu import kopyala_command
                return kopyala_command()

            if name == "tasarim_kenar_yumusat_command":
                from actions.tasarim_studyosu import kenar_yumusat_command
                return kenar_yumusat_command(args.get("miktar", ""))

            if name == "tasarim_birlestir_command":
                from actions.tasarim_studyosu import birlestir_command
                return birlestir_command()

            if name == "tasarim_birlestirmeyi_geri_al_command":
                from actions.tasarim_studyosu import birlestirmeyi_geri_al_command
                return birlestirmeyi_geri_al_command()

            if name == "tasarim_nesne_sil_command":
                from actions.tasarim_studyosu import nesne_sil_command
                return nesne_sil_command()

            if name == "tasarim_delik_yap_command":
                from actions.tasarim_studyosu import delik_yap_command
                return delik_yap_command()

            if name == "tasarim_kati_yap_command":
                from actions.tasarim_studyosu import kati_yap_command
                return kati_yap_command()

            if name == "tasarim_delikleri_uygula_command":
                from actions.tasarim_studyosu import delikleri_uygula_command
                return delikleri_uygula_command()

            if name == "tasarim_stl_indir_command":
                from actions.tasarim_studyosu import stl_indir_command
                return stl_indir_command()

            if name == "tasarim_temizle_command":
                from actions.tasarim_studyosu import sahneyi_temizle_command
                return sahneyi_temizle_command()

            if name == "tasarim_blendere_aktar_command":
                from actions.tasarim_studyosu import blendere_aktar_command
                return blendere_aktar_command(args.get("isim", ""))

            if name == "tasarim_blend_ac_command":
                from actions.tasarim_studyosu import blend_dosyasi_ac_command
                return blend_dosyasi_ac_command(args.get("dosya_adi", ""))

            if name == "obs_kayit_baslat_command":
                from actions.obs_kayit import start_recording
                return start_recording()

            if name == "obs_kayit_duraklat_command":
                from actions.obs_kayit import pause_recording
                return pause_recording()

            if name == "obs_kayit_devam_command":
                from actions.obs_kayit import resume_recording
                return resume_recording()

            if name == "obs_kayit_bitir_command":
                from actions.obs_kayit import stop_recording
                return stop_recording()

            if name == "egitim_baslat_command":
                from actions.model_egitimi import egitim_baslat_command
                return egitim_baslat_command()

            if name == "egitim_verisi_command":
                from backend.habits import HabitLearner
                hl = HabitLearner("memory/habits.json")
                action = str(args.get("action", "stats")).lower()
                me_dir = Path(__file__).resolve().parent.parent / "model-egitimi"
                me_dir.mkdir(parents=True, exist_ok=True)
                if action == "export":
                    return hl.export_dataset(me_dir / "egitim_verisi.jsonl")
                if action == "import":
                    candidates = sorted(me_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
                    name_key = str(args.get("dosya_adi", "")).strip().lower()
                    matches = [p for p in candidates if name_key and name_key in p.stem.lower()]
                    chosen = matches[0] if matches else (candidates[0] if candidates else None)
                    if chosen is None:
                        return ("model-egitimi klasöründe hiç .jsonl dosyası "
                               "bulunamadı — önce içe aktarılacak dosyayı oraya koyar mısın?")
                    return hl.import_dataset(chosen)
                stats = hl.dataset_stats()
                rotalar = ", ".join(f"{k}: {v}" for k, v in stats["rotalar"].items()) or "yok"
                return (f"Şu ana kadar {stats['toplam_olay']} etkileşim kaydedildi, "
                        f"{stats['egitime_uygun']} tanesi eğitime uygun. Rotalar: {rotalar}.")

            if name == "blockly_solve":
                from actions.blockly_solver import solve_maze_level
                try:
                    level = int(args.get("level", 1))
                except Exception:
                    level = 1
                return solve_maze_level(level, use_alt=bool(args.get("alt")))

            if name == "blockly_describe":
                from actions.blockly_solver import describe_maze_level
                try:
                    level = int(args.get("level", 1))
                except Exception:
                    level = 1
                return describe_maze_level(level, use_alt=bool(args.get("alt")))

            if name == "piper_dataset":
                log = self.ui.write_log if self.ui else (lambda m: None)
                action = str(args.get("action", "status")).lower()
                if action == "record":
                    idx = args.get("index")
                    idx0 = int(idx) - 1 if idx else None
                    return piper_dataset.record_sentence(idx0, on_log=log)
                if action == "status":
                    return piper_dataset.dataset_status()
                if action == "package":
                    return piper_dataset.package_dataset(on_log=log)
                if action == "redo":
                    idx = args.get("index")
                    if not idx:
                        return "Hangi cümleyi tekrar kaydedeyim? Numarasını söyler misin?"
                    return piper_dataset.redo_sentence(int(idx) - 1)
                if action == "reset":
                    return piper_dataset.reset_dataset()
                return "Eğitim seti komutunu anlamadım (kaydet / durum / paketle)."

            if name == "mic_test":
                from backend.stt_engine import mic_test
                log = self.ui.write_log if self.ui else (lambda m: None)
                return mic_test(int(args.get("seconds", 3) or 3), on_log=log)

            if name == "toggle_detection":
                want = str(args.get("action", "start")).lower() != "stop"
                cam = getattr(self, "webcam", None)
                if cam is not None and hasattr(cam, "set_detection"):
                    return cam.set_detection(want)
                try:
                    from app_config import save_app_config
                    save_app_config({"yolo_enabled": want})
                except Exception:
                    pass
                return ("Nesne algılama " + ("açıldı" if want else "kapatıldı") +
                        " (kamerayı açtığında geçerli olacak).")

            if name == "slideshow":
                return slideshow(str(args.get("action", "")))

            if name == "slide_edit":
                return slide_edit(str(args.get("action", "")))

            if name == "add_transition":
                return add_transition(str(args.get("name", "rastgele")),
                                      bool(args.get("all_slides", True)))

            if name == "add_animation":
                return add_animation(str(args.get("name", "solarak")),
                                     bool(args.get("all_slides", True)))

            if name == "clear_effects":
                return clear_effects(str(args.get("what", "all")))

            if name == "write_topic":
                return write_topic(str(args.get("topic", "")),
                                   str(args.get("target", "auto")))

            if name == "image_adjust":
                return image_adjust(str(args.get("action", "")), str(args.get("value", "")))

            if name == "word_export_pdf":
                return word_export_pdf(str(args.get("name", "")))

            if name == "excel_command":
                return excel_command(str(args.get("action", "")), str(args.get("value", "")))

            if name == "press_key":
                return press_key(str(args.get("key", "")), int(args.get("times", 1) or 1))

            if name == "save_blender_project":
                return blender_bridge.save_blender_project(str(args.get("name", "")))

            if name == "blender_scene":
                return blender_bridge.scene_command(str(args.get("action", "")))

            if name == "blender_exec":
                return blender_bridge.send_code(str(args.get("code", "")))

            if name == "save_freecad_project":
                return freecad_bridge.save_freecad_project(str(args.get("name", "")))

            if name == "freecad_scene":
                return freecad_bridge.scene_command(str(args.get("action", "")))

            if name == "freecad_exec":
                return freecad_bridge.send_code(str(args.get("code", "")))

            if name == "shutdown_assistant":
                from app_config import get_app_config_value as _g
                if not bool(_g("voice_shutdown_enabled", True)):
                    return ("Sesle kapatma AYARLARDAN kapalı. Açmak için ayarlara "
                            "'voice_shutdown_enabled' ekle ya da pencereden kapat.")
                return shutdown_assistant(ui=self.ui)

            if name == "type_text":
                return type_text(args.get("text", "")) or "Yazıldı."

            if name == "save_python_file":
                return save_python_file(
                    args.get("filename", ""), args.get("code", ""),
                    args.get("project_name", "")
                ) or "Dosya kaydedildi."

            return f"Bilinmeyen araç: {name}"

        except Exception as e:
            traceback.print_exc()
            return f"Hata: {e}"
