"""
YERINDE — Gemini Live araç (tool) tanımları
Windows masaüstü çekirdeği (main.py) kullanır.
"""

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Windows'ta herhangi bir uygulamayı açar. Spotify, Chrome, Terminal, Dosya Gezgini, "
            "VS Code, Blender, Godot, OBS Studio, Android Studio, Unity, Word, Excel, PowerPoint vb. "
            "Word/Excel/PowerPoint için Microsoft Office, LibreOffice veya OnlyOffice'ten hangisi "
            "kuruluysa otomatik olarak onu açar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı (örn. 'Spotify', 'Chrome', 'Blender', 'Godot', 'OBS')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "close_app",
        "description": (
            "Açık olan bir uygulamayı sesli komutla kapatır. "
            "Kullanıcı 'Blender'i kapat', 'OBS'i kapat', 'Godot'u kapat', "
            "'Chrome'u kapat' gibi bir şey söylediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Kapatılacak uygulama adı (örn. 'Blender', 'OBS', 'Godot')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "sys_info",
        "description": "Sistem bilgisi alır: pil durumu, CPU, RAM, disk, saat, tarih, ağ bağlantısı.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "battery | cpu | ram | disk | time | date | network | all"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_weather",
        "description": (
            "Anlik hava durumunu ozetler. Varsayilan konum Edirne'dir. "
            "Kullanici hava durumunu, sicakligi veya yagmur durumunu sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "location": {
                    "type": "STRING",
                    "description": "Sehir veya konum. Bos birakilirsa Edirne kullanilir."
                }
            }
        }
    },
    {
        "name": "get_forecast",
        "description": ("7 GÜNLÜK hava durumu tahmini (haftalık). 'haftalık hava durumu', "
                        "'7 günlük hava', 'yarın hava nasıl' gibi ileriye dönük sorularda kullan. "
                        "Anlık hava için get_weather kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "days": {"type": "NUMBER", "description": "kaç gün (1-7, varsayılan 7)"}},
            "required": []}
    },
    {
        "name": "get_calendar_events",
        "description": (
            "Takvim (Google Calendar) etkinliklerini okur. "
            "Bugun, yarin, siradaki etkinlik veya yaklasan ajandayi ozetler. "
            "Kullanici toplanti, takvim, ajanda, etkinlik veya gunluk programini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "today | tomorrow | next | agenda | week veya dogal dilde "
                        "'onumuzdeki 30 gun', '2 hafta', 'bu ay', 'gelecek ay'"
                    )
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum etkinlik sayisi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_calendar_event",
        "description": (
            "Takvim (Google Calendar) servisine yeni etkinlik ekler. "
            "Kullanici toplanti, randevu, takvime ekleme veya etkinlik olusturma isterse kullan. "
            "Baslangic tarihini gercek tarih/saat olarak ver; bitis verilmezse varsayilan sure kullanilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Baslangic tarih/saat. ISO veya yyyy-MM-dd HH:mm formatinda."
                },
                "end_iso": {
                    "type": "STRING",
                    "description": "Bitis tarih/saat. Opsiyonel."
                },
                "location": {
                    "type": "STRING",
                    "description": "Etkinlik konumu. Opsiyonel."
                },
                "notes": {
                    "type": "STRING",
                    "description": "Etkinlik notlari. Opsiyonel."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Eklenecek takvim adi. Opsiyonel."
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "true ise tum gun etkinligi olusturur."
                }
            },
            "required": ["title", "start_iso"]
        }
    },
    {
        "name": "delete_calendar_event",
        "description": (
            "Takvim (Google Calendar) servisinden etkinlik siler. "
            "Kullanici bir toplantiyi, randevuyu veya takvim kaydini silmek istediginde kullan. "
            "Ayni ada birden fazla etkinlik varsa dogru kaydi bulmak icin baslangic tarihini gercek tarih/saat olarak ver."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Silinecek etkinlik basligi. Ornek: 'Disci Randevusu'"
                },
                "start_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ayni isimli birden fazla etkinligi ayirt etmek icin kullan."
                },
                "calendar_name": {
                    "type": "STRING",
                    "description": "Opsiyonel takvim adi"
                },
                "delete_all_matches": {
                    "type": "BOOLEAN",
                    "description": "true ise eslesen tum etkinlikleri siler"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "get_reminders",
        "description": (
            "Hatırlatıcılar (Microsoft To-Do) listesini okur. "
            "Bugunku, yaklasan, geciken veya tum acik animsaticilari ozetler. "
            "Kullanici hatirlatma, animsatici, reminder veya yapilacaklar listesini sordugunda kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "today | upcoming | overdue | all | next"
                },
                "limit": {
                    "type": "NUMBER",
                    "description": "Maksimum animsatici sayisi"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Istenirse belirli bir animsatici listesi adi"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "add_reminder",
        "description": (
            "Hatırlatıcılar (Microsoft To-Do) uygulamasina yeni bir animsatici ekler. "
            "Kullanici 'hatirlat', 'animsatici ekle', 'reminder kur' dediginde kullan. "
            "Goreli zaman ifadelerini bugunku tarih baglamina gore due_iso alanina ISO formatinda cevir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                    "description": "Animsatici basligi"
                },
                "due_iso": {
                    "type": "STRING",
                    "description": "Opsiyonel tarih/saat. Ornek: 2026-04-13T09:00 veya tum gun icin 2026-04-13"
                },
                "notes": {
                    "type": "STRING",
                    "description": "Opsiyonel not"
                },
                "list_name": {
                    "type": "STRING",
                    "description": "Opsiyonel animsatici listesi"
                },
                "priority": {
                    "type": "STRING",
                    "description": "low | medium | high"
                },
                "all_day": {
                    "type": "BOOLEAN",
                    "description": "Tum gun animsatici ise true"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "browser_control",
        "description": "Tarayıcıda URL açar, Google'da arama yapar veya YouTube'da ilk sonucu doğrudan oynatır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "open_url | search | play_youtube"},
                "url":    {"type": "STRING", "description": "Açılacak URL (open_url için)"},
                "query":  {"type": "STRING", "description": "Arama sorgusu (search veya play_youtube için)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "shell_run",
        "description": "Windows komut satırı (cmd.exe) komutu çalıştırır. Dosya işlemleri, sistem yönetimi.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "Çalıştırılacak komut"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "toggle_webcam",
        "description": (
            "Gerçek zamanlı webcam akışını başlatır veya durdurur. "
            "Gemini modunda akış aktifken model sürekli kamera görüntüsü alıp yorumlar — "
            "'bak', 'gör', 'göster', 'kameraya bak', 'önümdekileri anlat', 'ne görüyorsun' "
            "gibi komutlarda 'start' kullan. Çevrimdışı (Ollama) modda sadece canlı önizleme "
            "penceresi açılır, görüntü yorumlanmaz. "
            "'kamerayı kapat', 'artık bakma' gibi durumlarda 'stop' kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "start — akışı başlat  |  stop — akışı durdur"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "toggle_garden_cam",
        "description": (
            "Bahçe (Yoosee/DVRIP IP) kamerasının canlı akışını başlatır veya durdurur. "
            "Kullanıcı 'bahçe kamerasını aç/başlat', 'güvenlik kamerasını aç', 'yoosee'yi aç' "
            "derse 'start'; 'bahçe kamerasını kapat/durdur' derse 'stop' kullan. "
            "Açarken ilk denemede cihaz uyku modundaysa uyanması birkaç deneme sürebilir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "start — akışı başlat  |  stop — akışı durdur"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "wake_garden_cam",
        "description": (
            "Bahçe (Yoosee/DVRIP IP) kamerasını uyku modundan uyandırır. "
            "Kullanıcı 'bahçe kamerasını uyandır', 'yoosee uyansın' gibi bir şey söylediğinde "
            "veya akış açılamadığında cihazı uyandırmak için kullan. Uyandırma birkaç saniye "
            "sürebilir; akışı açmaz, sadece cihazı hazırlar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "garden_ptz",
        "description": (
            "Bahçe (Yoosee/DVRIP IP) kamerasının DÖNEN KAFASINI (PTZ) çevirir. "
            "Bu kamera TEK cihazdır: üstte sabit görüntü sensörü, altta dönen kafa "
            "vardır ve kafa DÖNER — kamera sabit DEĞİLDİR. Kullanıcı 'kamerayı "
            "sağa/sola/yukarı/aşağı çevir', 'kamerayı döndür', 'kamerayı ortaya al', "
            "'çapraz yukarı sola döndür' gibi bir şey söylediğinde kullan. "
            "Yönler: up, down, left, right, up_left, up_right, down_left, down_right, center, stop."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "direction": {
                    "type": "STRING",
                    "description": "up | down | left | right | up_left | up_right | down_left | down_right | center | stop"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "garden_ptz_start",
        "description": (
            "Bahçe kamerasının dönen kafasını sürekli harekete başlatır (yön tuşuna "
            "basılı tutmak gibi). Kamera ayrıca durdurma komutu gelene dek döner; "
            "hemen garden_ptz_stop çağrılmalıdır. Yönler: up, down, left, right, "
            "up_left, up_right, down_left, down_right."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "direction": {
                    "type": "STRING",
                    "description": "up | down | left | right | up_left | up_right | down_left | down_right"
                }
            },
            "required": ["direction"]
        }
    },
    {
        "name": "garden_ptz_stop",
        "description": (
            "Bahçe kamerasının dönen kafasının hareketini durdurur. "
            "garden_ptz_start veya garden_ptz sonrası kullanıcı 'dur/kamera dönmesin' "
            "dediğinde ya da hareket sonlandırılacaksa çağrılır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "garden_horn",
        "description": (
            "Bahçe kamerasının alarmını/sirenini açar/kapatır (açıksa kapatır). "
            "Kullanıcı 'alarmı çal', 'alarmı kapat', 'sireni çal', 'hoparlörü aç', "
            "'düdük çal' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "garden_talk",
        "description": (
            "Bahçe kamerasıyla iki yönlü ses (konuşma) başlatır; açıkken tekrar "
            "çağrılırsa kapatır. Kullanıcı 'kameraya seslen', 'kameraya konuş', "
            "'hoparlörden konuş' gibi bir şey söylediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "play_media",
        "description": (
            "YouTube veya Spotify'da şarkı, müzik veya video açar. "
            "Kullanıcı belirli bir platform söylerse onu kullan. "
            "Belirtmezse uygun olanı dene. "
            "Kullanıcı 'çal', 'oynat', 'aç' diyorsa autoplay=true kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Şarkı, sanatçı, albüm veya video arama ifadesi"
                },
                "provider": {
                    "type": "STRING",
                    "description": "auto | youtube | spotify"
                },
                "autoplay": {
                    "type": "BOOLEAN",
                    "description": "true ise mümkünse doğrudan oynatır"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_youtube_channel_report",
        "description": (
            "YouTube kanalinin public istatistiklerini ve son videolarin performansini raporlar. "
            "Kullanici kanal istatistiklerini, abone sayisini, son videolarini, buyume hizini "
            "veya YouTube analizini sordugunda kullan. Bu arac Studio yerine public YouTube Data API verisini kullanir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": (
                        "Dogal dilde analiz istegi. Ornek: "
                        "'YouTube istatistiklerim nasil', 'son videolarimi analiz et', "
                        "'kanal buyumemi ozetle'"
                    )
                },
                "handle": {
                    "type": "STRING",
                    "description": (
                        "Opsiyonel kanal handle'i, kanal linki veya kanal ID'si. "
                        "Bos birakilirsa ayarlardaki youtube_channel_handle kullanilir."
                    )
                },
                "video_limit": {
                    "type": "NUMBER",
                    "description": "Analize dahil edilecek son video sayisi. Varsayilan 6."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_screen",
        "description": (
            "Aktif pencerenin ekran goruntusunu alip Gemini vision ile analiz eder. "
            "Kullanici ekranda ne oldugunu, bir hatayi, gorunen metni, butonlari veya pencere icerigini sordugunda kullan. "
            "Bu surum yalnizca aktif pencereyi destekler."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Kullanicinin ekranla ilgili sorusu. Ornek: 'Bu hatayi oku', 'Ekranda ne var?'"
                },
                "target": {
                    "type": "STRING",
                    "description": "Su an sadece active_window desteklenir."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "save_memory",
        "description": "Kullanıcı hakkında önemli bilgiyi kalıcı belleğe kaydeder. İsim, tercihler, projeler vb. duyunca sessizce çağır.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "identity | preferences | projects | notes"
                },
                "key":   {"type": "STRING", "description": "Kısa anahtar (örn. 'name')"},
                "value": {"type": "STRING", "description": "Değer (İngilizce)"}
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "delete_memory",
        "description": (
            "Kalici hafizadaki bir kaydi siler. "
            "Kullanici 'bunu hafizandan kaldir', 'unut', 'sil' gibi bir sey derse kullan. "
            "Mumkunse category ve key ile sil; emin degilsen match_text ile ilgili kaydi bulup kaldir."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "Kaydin kategorisi. Ornek: notes | identity | preferences | projects"
                },
                "key": {
                    "type": "STRING",
                    "description": "Silinecek anahtar. Ornek: claude_limit_refresh"
                },
                "match_text": {
                    "type": "STRING",
                    "description": "Kaydi bulmak icin kullanilacak dogal dil parcasi. Ornek: 'claude ai limit yenilenmesi'"
                }
            }
        }
    },
    {
        "name": "send_whatsapp_message",
        "description": (
            "WhatsApp Desktop veya WhatsApp Web üzerinden mesaj taslağı açar veya mesajı gönderir. "
            "Kişi adı veya telefon numarasıyla çalışabilir. "
            "Telefon numarası verilmemişse kişi adını önce kayıtlı WhatsApp kişileri ve içe aktarılan telefon rehberinde ara. "
            "Kullanıcı 'gönder', 'yolla', 'ile', 'hemen gönder' gibi açık bir gönderme niyeti söylüyorsa "
            "ekstra onay istemeden send_now=true kullan. "
            "Yalnızca 'hazırla', 'taslak aç', 'yaz ama gönderme' diyorsa send_now=false kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient_name": {
                    "type": "STRING",
                    "description": "Kişi adı. Örn: 'Anne', 'Ahmet', 'Ece'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararası telefon numarası. Örn: +905551112233"
                },
                "message": {
                    "type": "STRING",
                    "description": "Gönderilecek mesaj içeriği"
                },
                "app_target": {
                    "type": "STRING",
                    "description": "desktop | web | auto. Varsayılan auto, tercihen desktop."
                },
                "send_now": {
                    "type": "BOOLEAN",
                    "description": "true ise sohbet açıldıktan sonra mesajı otomatik gönderir"
                }
            },
            "required": ["message"]
        }
    },
    {
        "name": "save_whatsapp_contact",
        "description": (
            "Sık kullanılan bir WhatsApp kişisini adı ve telefon numarasıyla kalıcı belleğe kaydeder. "
            "Kullanıcı bir kişiyi 'annem', 'Ahmet', 'iş ortağım' gibi tekrar kullanılacak şekilde tanımladığında kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "display_name": {
                    "type": "STRING",
                    "description": "Kaydedilecek kişi adı. Örn: 'Annem', 'Ahmet'"
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "Uluslararası telefon numarası. Örn: +905551112233"
                },
                "aliases": {
                    "type": "STRING",
                    "description": "Virgülle ayrılmış alternatif hitaplar. Örn: 'anne, annem, mom'"
                }
            },
            "required": ["display_name", "phone_number"]
        }
    },
    {
        "name": "take_photo",
        "description": (
            "O an açık olan kameradan (bahçe kamerası açıksa ONDAN, değilse "
            "webcam'dan) bir fotoğraf çeker ve Captures klasörüne kaydeder. "
            "Kullanıcı 'fotoğraf çek', 'kameradan resim al', 'bahçe "
            "kamerasından fotoğraf çek', 'bahçenin fotoğrafını çek' "
            "dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "record_video",
        "description": (
            "O an açık olan kameradan (bahçe kamerası açıksa ONDAN, değilse "
            "webcam'dan) belirtilen süre kadar video kaydeder (Captures "
            "klasörüne). Kullanıcı 'video kaydet', 'beni kaydet', 'bahçe "
            "kamerasından video kaydet', 'bahçeyi kaydet' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "seconds": {
                    "type": "NUMBER",
                    "description": "Kaç saniye kayıt yapılacağı (varsayılan 5, en fazla 60)"
                }
            },
            "required": []
        }
    },
    {
        "name": "zumre_tutanagi_olustur",
        "description": (
            "Kullanıcının 'DOSYA YÜKLE' ile yüklediği GERÇEK bir zümre toplantı tutanağı "
            "(.docx) örneğini alıp, aynı okul/zümre biçimini, tablo düzenini ve MEB "
            "gündem maddelerini BİREBİR KORUYARAK yeni bir toplantı için tutanak üretir: "
            "yeni tarih/toplantı no/dönem bilgileriyle 'Alınan Kararlar' sütununu o "
            "döneme uygun (planlama ya da değerlendirme diliyle) yeniden yazar. "
            "'zümre tutanağını yeni döneme uyarla', 'dönem başı zümre tutanağı hazırla', "
            "'eylül ayı zümre tutanağını oluştur' gibi isteklerde kullan. Gündem "
            "maddelerinin METNİNİ ASLA DEĞİŞTİRMEZ (yasal/sabit ifadelerdir) — sadece "
            "kararları yeniden üretir. Önce örnek .docx yüklenmiş olmalı."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "donem_turu": {
                    "type": "STRING",
                    "description": "'dönem başı' | 'dönem ortası' | 'ara toplantı' | 'dönem sonu' — kararların planlama mı değerlendirme mi dilinde yazılacağını belirler. Belirtilmezse bugünün tarihine göre tahmin edilir."
                },
                "toplanti_tarihi": {
                    "type": "STRING",
                    "description": "GG.AA.YYYY, ör. '08.09.2026'. Belirtilmezse bugünün tarihi kullanılır."
                },
                "toplanti_saati": {
                    "type": "STRING",
                    "description": "SS.DD, ör. '10.00'. Belirtilmezse örnekteki saat korunur."
                },
                "toplanti_no": {
                    "type": "STRING",
                    "description": "ör. '2026/1'. Belirtilmezse örnekteki numara + dönem etiketi korunur."
                },
                "ders_yili": {
                    "type": "STRING",
                    "description": "ör. '2026-2027'. Belirtilmezse bugünün tarihine göre tahmin edilir."
                },
                "ek_talimat": {
                    "type": "STRING",
                    "description": "Kararların içeriğine yön verecek serbest not, ör. 'robotik yarışmasına katılım vurgulansın'. Opsiyonel."
                },
                "dosya_yolu": {
                    "type": "STRING",
                    "description": "Örnek .docx yolu (opsiyonel — boşsa önce kayıtlı 'ders' referansı, sonra son yüklenen dosya kullanılır)"
                },
                "ders": {
                    "type": "STRING",
                    "description": "'bilişim' | 'robotik' — hangi zümrenin kayıtlı örneğini kullanacağını belirtir (referans_belge_kaydet ile önceden kaydedilmiş olmalı). dosya_yolu verilmişse bu yoksayılır."
                }
            },
            "required": []
        }
    },
    {
        "name": "referans_belge_kaydet",
        "description": (
            "En son 'DOSYA YÜKLE' ile yüklenen dosyayı, KALICI bir referans olarak "
            "adlandırılmış bir yuvaya kaydeder (ör. 'bilişim kazanım senaryosu', "
            "'robotik yıllık planı', 'bilişim zümre örneği'). Kaydedilen referans, "
            "sonraki TÜM zumre_tutanagi_olustur / sinav_olustur çağrılarında "
            "otomatik kullanılır — kullanıcı bir daha aynı dosyayı yüklemek zorunda "
            "kalmaz. 'bunu bilişim kazanım senaryosu olarak kaydet', 'bu dosyayı "
            "robotik yıllık planı yap' gibi isteklerde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tur": {
                    "type": "STRING",
                    "description": "Referans türü, ör. 'bilişim zümre örneği', 'robotik zümre örneği', 'bilişim kazanım senaryosu', 'bilişim yıllık planı', 'robotik yıllık planı', 'bilişim 5. sınıf sınav örneği', 'bilişim 6. sınıf sınav örneği', 'robotik 5. sınıf sınav örneği', 'robotik 6. sınıf sınav örneği'. Serbest/doğal ifadeler de kabul edilir (ör. 'ksdt')."
                },
                "dosya_yolu": {
                    "type": "STRING",
                    "description": "Kaydedilecek dosyanın yolu (opsiyonel — boşsa son yüklenen dosya kullanılır)"
                }
            },
            "required": ["tur"]
        }
    },
    {
        "name": "sinav_olustur",
        "description": (
            "Kazanımlara dayalı YAZILI SINAV üretir. BİLİŞİM dersinde, kayıtlı "
            "'bilişim kazanım senaryosu' (İl'in KSDT tablosu) hangi kazanımların "
            "hangi sınav/senaryoda soru olacağını SAYIYLA belirtir — bu tablo "
            "kullanılır (tahmin değil, gerçek veri). ROBOTİK dersinde böyle bir "
            "tablo olmadığından, kayıtlı 'robotik yıllık planı' bağlam olarak "
            "kullanılır ve konu_kapsam/ek_talimat ile hangi kazanımların "
            "sorulacağı yönlendirilir. Sonuç, önceden kaydedilmiş örnek sınavın "
            "biçimine benzer yeni bir .docx olarak üretilir. 'bilişim 5. sınıf "
            "1. sınav 1. senaryo hazırla', 'robotik 6. sınıf ikinci yazılıyı "
            "algoritma konusundan hazırla' gibi isteklerde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ders": {
                    "type": "STRING",
                    "description": "'bilişim' | 'robotik'"
                },
                "sinif": {
                    "type": "STRING",
                    "description": "'5' | '6'"
                },
                "sinav_no": {
                    "type": "STRING",
                    "description": "'1' | '2' — dönemin kaçıncı yazılı sınavı"
                },
                "senaryo_no": {
                    "type": "STRING",
                    "description": "'1' | '2' — SADECE bilişimde anlamlı (KSDT'nin 1./2. Senaryo sütunu). Robotikte yoksayılır."
                },
                "donem": {
                    "type": "STRING",
                    "description": "'1' | '2' — başlıkta görünecek dönem numarası. Varsayılan '2'."
                },
                "soru_sayisi": {
                    "type": "NUMBER",
                    "description": "SADECE robotik için: kaç soru üretilecek. Belirtilmezse 8. Bilişimde kazanım senaryosundan otomatik belirlenir, bu alan yoksayılır."
                },
                "konu_kapsam": {
                    "type": "STRING",
                    "description": "SADECE robotik için: hangi konu/üniteden soru sorulacağı, ör. 'algoritma ve akış şeması'. Opsiyonel ama önerilir — verilmezse yıllık planın tamamından serbestçe seçilir."
                },
                "ek_talimat": {
                    "type": "STRING",
                    "description": "Soruların içeriğine yön verecek serbest not. Opsiyonel."
                },
                "ksdt_dosya_yolu": {
                    "type": "STRING",
                    "description": "Bilişim kazanım senaryosu dosya yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                },
                "yillik_plan_dosya_yolu": {
                    "type": "STRING",
                    "description": "Robotik yıllık plan dosya yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                },
                "soru_tipi": {
                    "type": "STRING",
                    "description": "'karışık' (varsayılan, model kazanıma göre klasik/boşluk doldurma/eşleştirme karışımı seçer) | 'klasik' | 'boşluk doldurma' | 'eşleştirme' — tümü tek tipte istenirse belirt."
                }
            },
            "required": ["ders", "sinif", "sinav_no"]
        }
    },
    {
        "name": "yillik_plan_guncelle",
        "description": (
            "Kayıtlı bir YILLIK PLAN'ı (Excel), MEB'in yayınladığı akademik "
            "çalışma takvimine göre YENİ eğitim-öğretim yılına uyarlar: her "
            "haftanın gerçek tarih aralığını (dönem başlangıcı, ara tatiller, "
            "yarıyıl tatili dikkate alınarak) yeniden hesaplar, AY ve HAFTA "
            "sütunlarını günceller, başlıktaki yılı değiştirir. Kazanım/ünite/"
            "etkinlik İÇERİĞİNE DOKUNMAZ — sadece hangi haftanın hangi "
            "tarihe denk geldiğini günceller. 'yıllık planı yeni döneme "
            "uyarla', '2026-2027 için bilişim yıllık planını güncelle' gibi "
            "isteklerde kullan. Önce ilgili örnek .xlsx 'referans_belge_kaydet' "
            "ile kaydedilmiş olmalı VE o akademik yılın çalışma takvimi "
            "bilinmelidir (kullanıcı MEB'in yayınladığı takvim görselini "
            "paylaşmışsa Claude bunu zaten biliyordur)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ders": {
                    "type": "STRING",
                    "description": "'bilişim' | 'robotik'"
                },
                "sinif": {
                    "type": "STRING",
                    "description": "'5' | '6'"
                },
                "egitim_yili": {
                    "type": "STRING",
                    "description": "Güncellenecek hedef eğitim-öğretim yılı, ör. '2026-2027'. ZORUNLU — akademik takvimi bilinen bir yıl olmalı."
                },
                "dosya_yolu": {
                    "type": "STRING",
                    "description": "Örnek .xlsx yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                }
            },
            "required": ["ders", "sinif", "egitim_yili"]
        }
    },
    {
        "name": "gunluk_plan_olustur",
        "description": (
            "Kayıtlı YILLIK PLAN'dan belirli bir haftanın kazanım/konu bilgisini "
            "alıp, o haftaya ait GÜNLÜK (HAFTALIK) DERS PLANINI (SINIF/ÜNİTE/KONU/"
            "HEDEFLER/TARİH/SÜRE/MATERYALLER/DERS İŞLENİŞ/ÖLÇME-DEĞERLENDİRME "
            "alanlarını içeren .docx) üretir. Kazanım metnini yıllık plandan "
            "AYNEN alır, değiştirmez — sadece o haftaya özgü ders işleniş "
            "adımlarını, materyalleri ve ölçme-değerlendirmeyi üretir. "
            "'5. sınıf bilişim için 3. hafta günlük planını hazırla', 'robotik "
            "algoritma konusunun günlük planını çıkar' gibi isteklerde kullan. "
            "Önce ilgili yıllık plan 'referans_belge_kaydet' ile kaydedilmiş olmalı."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ders": {
                    "type": "STRING",
                    "description": "'bilişim' | 'robotik'"
                },
                "sinif": {
                    "type": "STRING",
                    "description": "'5' | '6'"
                },
                "hafta_no": {
                    "type": "STRING",
                    "description": "Yıllık plandaki hafta numarası, ör. '3'. konu_arama ile birlikte kullanılmaz — biri yeterli."
                },
                "konu_arama": {
                    "type": "STRING",
                    "description": "Hafta numarası yerine konu/kazanım metniyle arama, ör. 'algoritma'. hafta_no verilmemişse kullanılır."
                },
                "ek_talimat": {
                    "type": "STRING",
                    "description": "Ders işlenişine yön verecek serbest not. Opsiyonel."
                },
                "yillik_plan_dosya_yolu": {
                    "type": "STRING",
                    "description": "Yıllık plan dosya yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                }
            },
            "required": ["ders", "sinif"]
        }
    },
    {
        "name": "kulup_calisma_plani_olustur",
        "description": (
            "Kayıtlı bir öğrenci kulübü YILLIK ÇALIŞMA PLANI örneğini (MEB "
            "Sosyal Etkinlikler Yönetmeliği EK-7/b formatı — AY sütununda "
            "Eylül-Haziran, her ay için o aya ait etkinlikler ve belirli gün/"
            "haftalar) alıp yeni eğitim-öğretim yılı için klonlar: başlıktaki "
            "yılı, katılımcı öğrenci sayılarını, danışman öğretmeni günceller. "
            "Etkinlik içerikleri VARSAYILAN olarak geçen yılkiyle AYNI kalır "
            "(genelde istenen budur — kulüp planları yıldan yıla büyük ölçüde "
            "tekrar eder); istenirse etkinlikleri_yenile=true ile taze "
            "içerikle yeniden yazdırılabilir. 'kulübü yeni döneme aç', "
            "'kulüp planını bu yıla uyarla' gibi isteklerde kullan. Önce "
            "örnek .xlsx yüklenip 'kulüp yıllık çalışma planı' olarak "
            "kaydedilmiş olmalı."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "egitim_yili": {
                    "type": "STRING",
                    "description": "ör. '2026-2027'. Belirtilmezse bugünün tarihine göre tahmin edilir."
                },
                "katilimci_toplam": {
                    "type": "STRING",
                    "description": "Toplam katılımcı öğrenci sayısı. Opsiyonel."
                },
                "katilimci_kiz": {
                    "type": "STRING",
                    "description": "Katılımcı kız öğrenci sayısı. Opsiyonel."
                },
                "katilimci_erkek": {
                    "type": "STRING",
                    "description": "Katılımcı erkek öğrenci sayısı. Opsiyonel."
                },
                "danisman_adi": {
                    "type": "STRING",
                    "description": "Danışman öğretmen adı. Belirtilmezse örnekteki isim korunur."
                },
                "etkinlikleri_yenile": {
                    "type": "BOOLEAN",
                    "description": "true ise her ayın etkinlik içeriği modelle yeniden yazılır (aynı ay yapısı korunarak). Varsayılan false — geçen yılki etkinlikler aynen kalır."
                },
                "ek_talimat": {
                    "type": "STRING",
                    "description": "etkinlikleri_yenile=true iken içeriğe yön verecek not. Opsiyonel."
                },
                "dosya_yolu": {
                    "type": "STRING",
                    "description": "Örnek .xlsx yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                }
            },
            "required": []
        }
    },
    {
        "name": "olcek_hazirla",
        "description": (
            "Dönem/sene sonunda teslim edilen DERS İÇİ KATILIM ÖLÇEĞİ ve "
            "PROJE DEĞERLENDİRME ÖLÇEĞİ Excel aracını yeni bir sınıf/dönem "
            "için hazırlar. Bu araç 50+ sayfalık, formüllerle birbirine bağlı "
            "bir şablondur — sadece 'Anasayfa' sekmesindeki sabit bilgiler "
            "(eğitim yılı, dönem, ders adı, sınıf adı) güncellenir, tüm diğer "
            "sayfalardaki başlıklar buna göre otomatik hesaplanır. Gerçek "
            "sınav/proje NOTLARINI bilemeyeceğinden (bunlar e-okul'dan "
            "kopyalanır), sadece İSTENİRSE öğrenci No/Ad-Soyad listesini "
            "önceden doldurur; notlar öğretmen tarafından e-okul'dan "
            "yapıştırılarak tamamlanır. Bilişim ve Robotik derslerinde "
            "kriterler AYNIDIR — tek fark ders adı. 'robotik 5B için ders "
            "içi katılım ölçeğini hazırla', '6A bilişim proje ölçeğini "
            "aç' gibi isteklerde kullan. Önce örnek .xlsx yüklenip 'ölçek "
            "şablonu' olarak kaydedilmiş olmalı."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "ders": {
                    "type": "STRING",
                    "description": "'bilişim' | 'robotik'"
                },
                "sinif": {
                    "type": "STRING",
                    "description": "Sınıf/şube adı, ör. '5/A', '6/B'"
                },
                "donem": {
                    "type": "STRING",
                    "description": "'1' | '2' | '1.DÖNEM' | '2.DÖNEM' | 'SENE SONU'. Belirtilmezse '1.DÖNEM'."
                },
                "egitim_yili": {
                    "type": "STRING",
                    "description": "ör. '2026-2027'. Belirtilmezse bugünün tarihine göre tahmin edilir."
                },
                "ogrenciler": {
                    "type": "STRING",
                    "description": "Opsiyonel: her satırda 'okul_no ad soyad' — ör. '17 Nur Cennet Zangalı\n24 Beyzanur Patlıcan'. Kayıtlı bir 'puantaj' referansı varsa bu yoksayılır (puantaj önceliklidir). İkisi de yoksa öğrenci listesi boş kalır."
                },
                "puantaj_dosya_yolu": {
                    "type": "STRING",
                    "description": "Öğretmenin kendi tuttuğu, sınıf sınıf sayfalara ayrılmış (ör. '5A BİLİŞİM', '5B ROBOTİK') kişisel not/puantaj Excel dosyasının yolu (opsiyonel — boşsa kayıtlı 'puantaj' referansı kullanılır). Varsa, öğrenci No/Ad Soyadı/Sınav/Proje notları GERÇEK verilerden otomatik doldurulur."
                },
                "dosya_yolu": {
                    "type": "STRING",
                    "description": "Örnek .xlsx yolu (opsiyonel — boşsa kayıtlı referans kullanılır)"
                }
            },
            "required": ["ders", "sinif"]
        }
    },
    {
        "name": "analyze_document",
        "description": (
            "Kullanıcının 'DOSYA YÜKLE' düğmesiyle yüklediği (ya da tam yolu verilen) bir "
            "PDF, Word, PowerPoint, Excel veya resim dosyasını analiz eder/özetler. "
            "Dosya yolu belirtilmezse en son yüklenen dosyayı kullanır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Dosyanın tam yolu (opsiyonel — boşsa son yüklenen dosya kullanılır)"
                },
                "query": {
                    "type": "STRING",
                    "description": "Kullanıcının dosya hakkındaki spesifik sorusu (opsiyonel)"
                }
            },
            "required": []
        }
    },
    {
        "name": "read_document_aloud",
        "description": (
            "Bir PDF/Word/PowerPoint dosyasını sesli kitap gibi yüksek sesle okur. "
            "Kullanıcı 'bunu sesli oku', 'PDF'i oku' dediğinde kullan. "
            "Dosya yolu belirtilmezse en son yüklenen dosyayı kullanır."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Dosyanın tam yolu (opsiyonel — boşsa son yüklenen dosya kullanılır)"
                }
            },
            "required": []
        }
    },
    {
        "name": "save_python_file",
        "description": (
            "Verilen Python kodunu masaüstündeki 'Çalışmalarım' klasörüne .py dosyası "
            "olarak kaydeder (istenirse bir alt proje klasörüne). Kullanıcı senden kod "
            "yazmanı ve masaüstüne kaydetmeni istediğinde, ya da yüklenen bir .py "
            "dosyasını düzeltip 'doğrusunu masaüstüne kaydet' dediğinde kullan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Dosya adı (örn. 'hesap_makinesi.py')"
                },
                "code": {
                    "type": "STRING",
                    "description": "Kaydedilecek tam Python kodu"
                },
                "project_name": {
                    "type": "STRING",
                    "description": "Opsiyonel: 'Çalışmalarım' altında bir alt klasör adı (proje için)"
                }
            },
            "required": ["filename", "code"]
        }
    },
    {
        "name": "type_text",
        "description": (
            "Söylenen metni AKTİF penceredeki imlece klavyeden yazar (sesle yazma/dikte). "
            "Kullanıcı 'yaz ...', 'şunu yaz: ...' dediğinde kullan. Not defteri, Word, "
            "tarayıcı — hangi pencere aktifse oraya yazar."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {
                    "type": "STRING",
                    "description": "Klavyeden yazılacak metin"
                }
            },
            "required": ["text"]
        }
    },
    {
        "name": "system_volume",
        "description": "Bilgisayarın SES DÜZEYİNİ değiştirir. 'sesi kıs/azalt'→down, 'sesi yükselt/arttır/aç'→up, 'sesi kapat/sustur'→mute.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "up | down | mute"},
            "step": {"type": "NUMBER", "description": "yüzde adım (varsayılan 10)"}},
            "required": ["action"]}
    },
    {
        "name": "media_control",
        "description": "Çalan müziği/videoyu kontrol eder (Spotify, YouTube sekmesi...): 'şarkıyı durdur/duraklat/devam ettir'→playpause, 'sonraki şarkı'→next, 'önceki'→prev, 'tamamen durdur'→stop. Yeni şarkı AÇMAK için play_media kullan.",
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "playpause | stop | next | prev"}},
            "required": ["action"]}
    },
    {
        "name": "arkaplan_command",
        "description": ("YERİNDE'nin ANA PENCERESİNİN arkaplanını değiştirir (atölye "
                        "araçlarının kendi mavi/yeşil/krem temasıyla KARIŞTIRMA — bu "
                        "farklı bir şey, YERİNDE'nin kendi pencere arkaplanı). Üç modu "
                        "var: 'acik' (aydınlık, projeyle gelen hazır görsel), 'koyu' "
                        "(karanlık, projeyle gelen hazır görsel), 'sade' (özel arkaplanı "
                        "kaldırıp düz tema rengine döner — 'normale döndür' de aynı "
                        "anlama gelir). 'arkaplanı açık yap', 'arkaplanı koyu yap', "
                        "'arkaplanı sadeleştir', 'arkaplanı normale döndür' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mod": {"type": "STRING", "description": "'acik', 'koyu' ya da 'sade'"}
            },
            "required": ["mod"]
        }
    },
    {
        "name": "tema_command",
        "description": ("YERİNDE'nin TÜM ARAYÜZÜNÜN RENK TEMASINI ve konuşma "
                        "animasyonu stilini birlikte değiştirir (arkaplan_command'dan "
                        "FARKLI — o sadece pencere arkaplan resmini değiştirir, bu ise "
                        "renk paletini VE konuşma animasyonunu değiştirir; atölye "
                        "araçlarının kendi temasıyla da KARIŞTIRMA). Yedi mod: 'acik' "
                        "ya da 'krem' → Krem (Aydınlık) teması; 'mavi' → Pico Mavi "
                        "teması; 'yesil' → Pico Yeşil teması; 'mor' → Lavanta "
                        "(Mavi-Mor) teması; 'turuncu' → Amber (Turuncu-Sarı) teması; "
                        "'kirmizi' → Kızıl (Ateş) teması; 'sade' ya da 'karanlik' → "
                        "Karanlık (Turkuaz) teması, varsayılan. Karanlık/sade temada "
                        "konuşma animasyonu Klasik olur, diğer altısında Anka Baloncuk "
                        "olur — bu otomatik, ayrıca sorulmaz. 'temayı mavi yap', "
                        "'yeşil temaya geç', 'temayı sadeleştir', 'kırmızı temaya "
                        "geç', 'mor temaya geç', 'turuncu temaya geç' gibi komutlarla "
                        "tetiklenir. Uygulanması için birkaç saniye içinde kendini "
                        "otomatik yeniden başlatır — bu normal, kullanıcıya söyle."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mod": {"type": "STRING", "description": "'acik'/'krem', 'mavi', 'yesil', 'mor', 'turuncu', 'kirmizi' ya da 'sade'/'karanlik'"}
            },
            "required": ["mod"]
        }
    },
    {
        "name": "save_active_document",
        "description": "Aktif penceredeki dosyayı kaydeder (Ctrl+S gönderir). 'dosyayı kaydet', 'belgeyi kaydet' dendiğinde kullan.",
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "office_format",
        "description": ("AÇIK Word/PowerPoint belgesini biçimlendirir: yazı rengi/boyutu, "
                        "sayfa arka plan rengi, YENİ SAYFA/SLAYT ekleme, RASTGELE TASARIM. "
                        "'yazı rengini kırmızı yap', 'yazı boyutunu 24 yap', 'yazıyı büyüt/küçült', "
                        "'sayfa rengini mavi yap', 'yeni sayfa/slayt'→new_page, "
                        "'tasarım seç'→random_design için kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "font_color | font_size | font_grow | font_shrink | page_color | new_page | random_design | align_left | align_center | align_right | align_justify"},
            "value": {"type": "STRING", "description": "renk adı (kırmızı, mavi...) ya da punto sayısı"}},
            "required": ["action"]}
    },
    {
        "name": "mouse_control",
        "description": ("Fareyi sesle kontrol eder: 'tıkla/sol tıkla'→left_click, 'sağ tıkla'→right_click, "
                        "'çift tıkla'→double_click, 'aşağı/yukarı kaydır'→scroll_down/up, "
                        "'fareyi sağa götür'→move, 'imleci ortala'→center."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "left_click | right_click | double_click | scroll_up | scroll_down | move | center"},
            "direction": {"type": "STRING", "description": "move için: sağa | sola | yukarı | aşağı"},
            "amount": {"type": "NUMBER", "description": "piksel ya da kaydırma miktarı (opsiyonel)"}},
            "required": ["action"]}
    },
    {
        "name": "record_voice_sample",
        "description": ("Kullanıcının sesinden örnek kaydeder ve YERINDE'nin çevrimdışı sesini "
                        "'KENDİ SESİM' (Coqui XTTS-v2 klonlama) yapar. 'sesimi kaydet' dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "seconds": {"type": "NUMBER", "description": "kayıt süresi sn (varsayılan 10)"}},
            "required": []}
    },
    {
        "name": "insert_image",
        "description": ("Açık PowerPoint slaydına ya da Word belgesine RESİM ekler. "
                        "Kullanıcı 'sunuma kedi resmi ekle', 'internetten İstanbul resmi "
                        "indir ve ekle' derse, source'a ARAMA KELİMESİNİ yaz — resmi "
                        "internetten kendisi indirir. Dosya yolu da verilebilir."),
        "parameters": {"type": "OBJECT", "properties": {
            "source": {"type": "STRING", "description": "arama kelimesi (örn. 'kedi') ya da dosya yolu"}},
            "required": ["source"]}
    },
    {
        "name": "whatsapp_call",
        "description": ("WhatsApp'tan SESLİ ya da GÖRÜNTÜLÜ arama başlatır. "
                        "'annemi ara'→voice, 'babamla görüntülü konuş'→video. "
                        "Arama düğmesinin yeri bir kez öğretilmelidir "
                        "(calibrate_whatsapp)."),
        "parameters": {"type": "OBJECT", "properties": {
            "contact": {"type": "STRING", "description": "kişi adı"},
            "kind": {"type": "STRING", "description": "voice | video"}},
            "required": ["contact"]}
    },
    {
        "name": "calibrate_whatsapp",
        "description": ("WhatsApp arama düğmesinin ekrandaki yerini ÖĞRENİR. "
                        "'whatsapp sesli arama düğmesini öğret' dendiğinde kullan. "
                        "Kullanıcı 5 sn içinde imleci düğmenin üzerine götürür."),
        "parameters": {"type": "OBJECT", "properties": {
            "kind": {"type": "STRING", "description": "voice | video"}},
            "required": ["kind"]}
    },
    {
        "name": "play_stream",
        "description": ("Film/dizi servisinde arar ve açar: Disney+ (disney), Netflix, "
                        "Prime Video (prime), YouTube, Exxen, BluTV, Gain, TOD, MUBI. "
                        "'disney plus'tan Frozen aç', 'netflix'te Dark aç' dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "service": {"type": "STRING", "description": "disney | netflix | prime | youtube | exxen | blutv | gain | tod | mubi"},
            "query": {"type": "STRING", "description": "film/dizi adı (opsiyonel)"}},
            "required": ["service"]}
    },
    {
        "name": "scratch_command",
        "description": ("Scratch'te blok programlama (Türkçe, sesle): 'scratch'te 10 adım git'→move, "
                        "'90 derece sağa dön'→turn_right, 'merhaba de'→say, "
                        "'2 saniye bekle'→wait, 'boyutu 150 yap'→size, "
                        "'5 kere tekrarla'→repeat_start (DÖNGÜ, içine sonraki komutlar girer, "
                        "'blok bitti' ile kapanır), 'sonsuza kadar tekrarla'→forever_start, "
                        "'eğer kenara değerse'→if_touching_edge_start (KOŞUL), "
                        "'eğer X tuşuna basılırsa'→if_key_pressed_start, 'blok bitti'→block_end, "
                        "'kalemi indir/kaldır/temizle'→pen_down/pen_up/pen_clear, "
                        "'kalem rengini X yap'→pen_color, 'X değişkenini Y yap'→set_variable, "
                        "'kukla ekle [ad]'→add_sprite (YENİ kukla oluşturur ve AKTİF yapar — "
                        "sonraki komutlar buna uygulanır. Eğer [ad] Scratch'in GERÇEK kütüphane "
                        "kuklalarından biriyle eşleşiyorsa — kedi/köpek/aslan/tilki/fil/top/elma/"
                        "gitar/roket gibi 91 doğrulanmış isimden biri — RENK BELİRTİLMEDİĞİ "
                        "sürece GERÇEK Scratch görseli kullanılır, basit çizim YAPILMAZ; renk "
                        "AÇIKÇA belirtilirse [ör. 'kırmızı yıldız'] elle çizilmiş renkli şekle "
                        "düşülür çünkü kütüphane görselinin rengi sabittir), "
                        "'kukla sil [ad]'→delete_sprite, '[ad] kuklasına geç'→switch_sprite "
                        "(hangi kuklaya komut ekleneceğini değiştirir), "
                        "'kukla çiz: kırmızı yıldız'→draw_sprite (basit bir SVG şekil ÇİZİP yeni "
                        "kukla olarak ekler; renk: kırmızı/mavi/yeşil/sarı/turuncu/mor/pembe/"
                        "siyah/beyaz; şekil: daire/kare/üçgen/yıldız), "
                        "'kostüm ekle: mavi kare'→add_costume (AKTİF kuklaya ek görünüm ekler), "
                        "'yorum ekle: [metin]'→add_comment (son bloğa sarı açıklama notu iğneler), "
                        "'sb3 dosyasını analiz et'→analyze (kendi projemizi ya da 'value' ile "
                        "verilen BAŞKA bir .sb3 dosyasını inceler; kopuk blok referanslarını "
                        "OTOMATİK DÜZELTİR, erişilemez blokları raporlar), "
                        "'scratch'i temizle'→clear (aktif kuklanın betiğini sıfırlar), "
                        "'scratch'i yeniden aç'→reopen, 'bilgisayarımdan yükle'→load "
                        "(DİSKTEKİ kaydedilmiş dosyayı açar — YERİNDE yeniden başlamış "
                        "olsa bile çalışır), 'scratch'i kapat'→close (çalışan Scratch "
                        "sürecini kapatır, başka pencerede olsan bile), "
                        "'yeşil bayrağı öğret'→calibrate_green_flag (yeşil bayrak "
                        "düğmesinin yerini bir kez öğrenir), 'scratch'i çalıştır'/"
                        "'yeşil bayrağa tıkla'→run_green_flag (öğrenilen yeşil bayrağa "
                        "tıklayıp yazılan kodu ÇALIŞTIRIR — öğrenciye kodunu test "
                        "ettirmek için). Bloklar SABİT TEK dosyada "
                        "(yerinde_proje.sb3) birikir — her komutta YENİ dosya AÇILMAZ."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "move | turn_right | turn_left | say | say_for | think | show | hide | goto | point_direction | glide | size | change_size | next_costume | wait | stop_all | repeat_start | forever_start | if_touching_edge_start | if_key_pressed_start | block_end | pen_down | pen_up | pen_clear | pen_stamp | pen_color | set_variable | change_variable | add_sprite | delete_sprite | switch_sprite | draw_sprite | add_costume | add_comment | analyze | clear | run | reopen | load | close | calibrate_green_flag | run_green_flag"},
            "value": {"type": "STRING", "description": "sayı, renk adı, 'x,y' (goto/glide), 'renk şekil' (draw_sprite/add_costume, ör. 'kırmızı yıldız'), ya da analiz edilecek dosya yolu"},
            "text": {"type": "STRING", "description": "say/think/add_comment için metin"},
            "times": {"type": "STRING", "description": "repeat_start için tekrar sayısı"},
            "key": {"type": "STRING", "description": "if_key_pressed_start için tuş adı; set_variable/change_variable için değişken adı; add_sprite/delete_sprite/switch_sprite için kukla adı"}},
            "required": ["action"]}
    },
    {
        "name": "akis_command",
        "description": ("YERİNDE'nin KENDİ (sıfırdan yazılmış) akış şeması ve algoritma "
                        "öğretim aracını tarayıcıda açar. Başla/Bitir, İşlem, Karar "
                        "(Evet/Hayır), Giriş/Çıkış kutularıyla sürükle-bırak akış şeması "
                        "kurma; adım adım ÇALIŞTIRMA simülasyonu (değişken paneli + ekran "
                        "çıktısı); ve otomatik Python kod üretimi içerir. "
                        "'algoritma oyununu aç' / 'akış şeması aracını aç' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "akis_semasi_kapat_command",
        "description": ("Akış şeması aracı tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. "
                        "'akış şeması aracını kapat', 'aracı kapat' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "carkifelek_command",
        "description": ("Çarkıfelek — Bilişim Bilgi Yarışması'nı tarayıcıda açar. "
                        "Sorular kullanıcının kendi ders sitesinden (bilişim, bilgi, "
                        "iletişim, teknoloji, donanım/yazılım, giriş-çıkış-depolama "
                        "birimleri) alınmıştır. Çarkı çevirip düşülen dilimin sorusunu "
                        "cevaplama, puan toplama oyunu. "
                        "'çarkıfelek oyununu aç' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "carkifelek_kapat_command",
        "description": ("Çarkıfelek tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. "
                        "'çarkıfeleği kapat', 'aracı kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "satranc_command",
        "description": ("Satranç oyununu tarayıcıda açar. YERİNDE'nin kendi (sıfırdan "
                        "yazılmış) satranç uygulaması — tüm kurallar (rok, en passant, "
                        "terfi, şah/mat/pat) dahildir. İki kişi aynı ekrandan sırayla "
                        "oynayabilir, ya da 'Yerinde'ye Karşı' modunda yapay zekaya "
                        "karşı oynanabilir (kolay/orta/zor). "
                        "'satranç aç' / 'satranç oynamak istiyorum' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "satranc_kapat_command",
        "description": ("Satranç tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. "
                        "'satrancı kapat', 'aracı kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "cin_damasi_command",
        "description": ("Çin Daması oyununu tarayıcıda açar. YERİNDE'nin kendi (sıfırdan "
                        "yazılmış) 121 delikli klasik yıldız tahtası — sıçrama zincirleri "
                        "dahil tüm kurallar uygulanır. İki kişi aynı ekrandan sırayla "
                        "oynayabilir, ya da 'Yerinde'ye Karşı' modunda yapay zekaya karşı "
                        "oynanabilir. "
                        "'çin daması aç' / 'çin daması oynamak istiyorum' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "cin_damasi_kapat_command",
        "description": ("Çin Daması tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. 'çin "
                        "damasını kapat', 'aracı kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "robotik_simulator_command",
        "description": ("Robotik ve Devre Simülatörünü tarayıcıda açar. Ortaokul/lise "
                        "seviyesine uygun; Arduino Uno, ESP32, Raspberry Pi Pico ve "
                        "Pico W kartlarını, ÖNCEDEN HAZIRLANMIŞ (engelden kaçan / ışık "
                        "takip eden / çizgi izleyen) robot SENARYOLARINI sabit bir devre "
                        "şeması, örnek kod ve canlı 2D animasyonla İZLETİR — kullanıcı "
                        "burada breadboard üzerinde kendi devresini KURMAZ, hazır bir "
                        "senaryoyu seçip izler/çalıştırır. "
                        "'robotik simülatörünü aç' / 'robot simülasyonu aç' bu aracı açar. "
                        "SES TANIMA NOTU: 'robot ik simülatör' veya 'robotik simülatör' "
                        "gibi ufak telaffuz farkları hep bu aracı işaret eder. "
                        "DİKKAT: pico_devre_atolyesi_command'dan TAMAMEN FARKLI bir "
                        "araçtır — kullanıcı 'devre ATÖLYESİ', 'breadboard', 'devre elemanı "
                        "EKLE/KUR' gibi kendi devresini İNŞA ETMEK isteyen ifadeler "
                        "kullanıyorsa (senaryo İZLEMEK değil), o zaman DAİMA "
                        "pico_devre_atolyesi_command'ı kullan, bunu değil."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "robotik_simulator_kapat_command",
        "description": ("Robotik ve Devre Simülatörü tarayıcıda AÇIKKEN, o sekmeyi "
                        "kapatmayı dener. 'robotik simülatörü kapat', 'aracı kapat' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_studyosu_command",
        "description": ("3B Tasarım Stüdyosunu tarayıcıda açar. Tinkercad benzeri "
                        "basit bir 3 boyutlu tasarım aracı: küp, silindir, küre, koni, "
                        "piramit ve simit gibi temel şekillerden nesne oluşturma, konum/ "
                        "boyut/döndürme/renk düzenleme, delik açma (boolean kesme) ve "
                        "sonucu STL dosyası olarak indirme. Var olan bir STL dosyası da "
                        "açılıp üzerinde çalışmaya devam edilebilir. "
                        "'3 boyutlu tasarım stüdyosunu aç' / '3B tasarım aracını aç' / "
                        "'stl tasarım aracını aç' / 'nesne tasarlama aracını aç' bu aracı açar. "
                        "SES TANIMA NOTU: 'tasarım' konuşma tanımada bazen 'tasarim' "
                        "(noktasız ı yerine düz i), 'stüdyo' bazen 'studyo' şeklinde geçebilir "
                        "— bunlar hep bu aracı işaret eder, farklı bir araç değildir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "robot_tasarim_command",
        "description": ("Robot Tasarım Atölyesini tarayıcıda açar. 3B Tasarım Stüdyosu "
                        "ile AYNI motoru kullanan, ama gövde/tekerlek/eklem/kol parçası/ "
                        "sensör/motor gibi hazır robot parçaları paleti içeren, parçaları "
                        "birbirine EKLEMLE bağlayıp (biri hareket edince bağlı olan da "
                        "onunla birlikte gitsin diye) robot kurmaya odaklanan ayrı bir "
                        "araçtır. Kenar yumuşatma, delik/birleştirme, malzeme/doku, "
                        "animasyon, STL indirme ve Blender'a aktarma özelliklerinin "
                        "hepsi burada da vardır. "
                        "'robot tasarım atölyesini aç' / 'robot tasarım aracını aç' / "
                        "'3 boyutlu robot tasarlama aracını aç' / 'robot yapma aracını aç' "
                        "bu aracı açar. "
                        "SES TANIMA NOTU: 'tasarım' bazen 'tasarim', 'atölye' bazen 'atolye' "
                        "şeklinde duyulabilir — bunlar hep bu aracı işaret eder."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "donanim_atolyesi_command",
        "description": ("YERİNDE Donanım Atölyesini tarayıcıda açar — işlemci, işlemci "
                        "soğutucusu, RAM, ekran kartı (GPU), M.2 SSD, SATA SSD/HDD, SATA "
                        "veri/güç kabloları, 24-pin güç kablosu, CPU güç kablosu (EPS), "
                        "kasa fanları ve ön panel kabloları gibi bilgisayar parçalarını "
                        "sürükleyip anakart üzerindeki DOĞRU yuvalarına yerleştirerek bir "
                        "bilgisayarın nasıl monte edildiğini öğretir. 'Bilgi' modunda her "
                        "parçanın ne işe yaradığı anlatılır, 'Sınav' modunda parça "
                        "yerleştirildikçe küçük sorular sorulur. "
                        "'donanım atölyesini aç' / 'bilgisayar parçaları atölyesini aç' / "
                        "'bilgisayar montajı aracını aç' / 'donanım eğitim aracını aç' bu "
                        "aracı açar. "
                        "SES TANIMA NOTU: 'donanım' bazen 'donanim', 'atölye' bazen "
                        "'atolye' şeklinde duyulabilir — bunlar hep bu aracı işaret eder."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "donanim_anladim_command",
        "description": ("Donanım Atölyesi tarayıcıda AÇIKKEN, o an ekranda açık olan "
                        "açıklama/yardım/bilgi penceresini kapatır — kullanıcı 'Anladım' "
                        "ya da 'Kapat' düğmesine kendi basmış gibi. 'anladım', 'tamam "
                        "anladım', 'açıklamayı kapat', 'pencereyi kapat' gibi komutlarla "
                        "tetiklenir. Sadece Donanım Atölyesi açıkken anlamlıdır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "donanim_parca_ekle_command",
        "description": ("Donanım Atölyesi tarayıcıda AÇIKKEN, bir bilgisayar parçasını "
                        "(işlemci, işlemci soğutucusu, RAM Bellek 1, RAM Bellek 2, ekran "
                        "kartı, M.2 SSD, SATA SSD/HDD, SATA veri kablosu, SATA güç kablosu, "
                        "24-pin güç kablosu, CPU/işlemci güç kablosu (EPS), kasa fanı 1, "
                        "kasa fanı 2, ön panel kablo demeti) anakart üzerindeki doğru "
                        "yuvasına yerleştirir. 'işlemciyi ekle', 'işlemci soğutucusunu ekle', "
                        "'işlemci güç kablosunu ekle', 'ikinci RAM'i ekle', 'ikinci kasa "
                        "fanını tak', 'ön paneli ekle', 'ekran kartını tak' gibi belirli bir "
                        "parça adıyla — parca parametresine kullanıcının SÖYLEDİĞİ ifadeyi "
                        "olduğu gibi ver (örn. 'işlemci güç kablosu'), yukarıdaki tam parça "
                        "adına çevirmeye ÇALIŞMA, bu eşleştirmeyi araç kendisi yapıyor. Sadece "
                        "'parça ekle' denirse (parça adı belirtilmezse) sırada takılabilecek "
                        "ilk parçayı ekler."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "parca": {"type": "STRING", "description": "İsteğe bağlı: eklenecek parçanın adı, kullanıcının söylediği gibi (örn. 'işlemci', 'işlemci güç kablosu', 'ikinci RAM', 'ön panel'). Boş bırakılırsa sıradaki parça eklenir."}
            },
            "required": []
        }
    },
    {
        "name": "donanim_parca_sok_command",
        "description": ("Donanım Atölyesi tarayıcıda AÇIKKEN, anakarta daha önce takılmış "
                        "bir bilgisayar parçasını söker. 'RAM'i sök', 'ekran kartını çıkar', "
                        "'işlemci soğutucusunu sök', 'işlemci güç kablosunu çıkar', 'ikinci "
                        "kasa fanını sök' gibi belirli bir parça adıyla — parca parametresine "
                        "kullanıcının SÖYLEDİĞİ ifadeyi olduğu gibi ver, tam parça adına "
                        "çevirmeye ÇALIŞMA. Sadece 'parça sök' denirse (parça adı "
                        "belirtilmezse) en son eklenen (takılan) parçayı söker."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "parca": {"type": "STRING", "description": "İsteğe bağlı: sökülecek parçanın adı, kullanıcının söylediği gibi. Boş bırakılırsa en son eklenen parça sökülür."}
            },
            "required": []
        }
    },
    {
        "name": "donanim_tema_command",
        "description": ("Donanım Atölyesi tarayıcıda AÇIKKEN, arayüz temasını değiştirir: "
                        "mavi, yeşil ya da krem. 'temayı yeşil yap', 'krem temaya geç', "
                        "'mavi temaya geç' gibi komutlarla tetiklenir. Sadece Donanım "
                        "Atölyesi açıkken anlamlıdır."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tema": {"type": "STRING", "description": "'mavi', 'yeşil' ya da 'krem'"}
            },
            "required": ["tema"]
        }
    },
    {
        "name": "resim_pdf_command",
        "description": ("Resim & PDF Atölyesini tarayıcıda açar — resim arka planını "
                        "silme/fırçalama, çerçeve ekleme, biçim dönüştürme (JPEG/PNG/ "
                        "WEBP/ICO vb., toplu dönüştürme dahil) ve PDF oluşturma "
                        "işlemlerini tek sayfada topluyor. Tek bağımsız HTML dosyası, "
                        "sunucu gerekmez. "
                        "'resim pdf atölyesini aç' / 'resim ve pdf aracını aç' / "
                        "'fotoğraf düzenleme aracını aç' / 'pdf aracını aç' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "resim_pdf_ayar_command",
        "description": ("Resim & PDF Atölyesi tarayıcıda AÇIKKEN, sol menüden bir ARACA "
                        "(panele) geçer VE o araçtaki bir AYARI değiştirir ya da bir işlemi "
                        "tetikler — sanki kullanıcı ilgili kutuyu/düğmeyi kendi tıklamış "
                        "gibi. DİKKAT: bu, resim_pdf_command'dan (aracı SADECE AÇAN komut) "
                        "TAMAMEN FARKLI — burada araç zaten açık olmalı ve amaç İÇİNDEKİ bir "
                        "ayarı değiştirmek/bir işlemi başlatmak. ÖNEMLİ: dosya seçme (resim/"
                        "PDF açma) tarayıcı güvenliği nedeniyle sesle YAPILAMAZ — kullanıcı "
                        "dosyayı önce elle seçmelidir; bu araç sadece o AÇIK dosya "
                        "üzerindeki ayarları/işlemleri kontrol eder. "
                        "Örnekler: 'çerçeve kalınlığını 60 yap', 'çerçeveyi kırmızı yap', "
                        "'arka planı sil aracına geç', 'arka planı otomatik sil', "
                        "'fırça boyutunu büyüt', 'toleransı "
                        "40 yap', 'geri al', 'sıfırla', 'daire şeklinde çerçeve yap', "
                        "'formatı webp yap', 'kaliteyi 80 yap', 'tümünü indir', '256 "
                        "boyutunu ikon listesine ekle', 'resimleri yan yana birleştir', "
                        "'3 sütunlu yap', 'kare başına süreyi 2 saniye yap', 'geçiş "
                        "efektini fade yap', 'videoyu oluştur', 'dili Türkçe yap', "
                        "'metni çıkar', 'panoya kopyala', 'word olarak indir', 'temayı yeşil "
                        "yap', 'aracı kapat' gibi. 'tema' ve 'kapat' eylemleri GENELDİR — "
                        "hangi araçta olursan ol çalışır, bu durumda 'arac' boş bırakılabilir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "arac": {"type": "STRING",
                         "description": ("Sol menüdeki 10 araçtan biri: frame (Çerçeve "
                                         "Ekle) | bgremove (Arka Planı Sil) | round (Şekilli "
                                         "Çerçeve) | format (Format Dönüştür) | ico (İkon/ICO "
                                         "Oluştur) | merge (Resimleri Birleştir) | video "
                                         "(Resimden Video) | ocr (Resimden Yazıya) | pdf2img "
                                         "(PDF → Resim) | pdf2word (PDF → Word). 'tema'/'kapat' "
                                         "eylemleri için boş bırakılabilir.")},
                "eylem": {"type": "STRING",
                          "description": ("GENEL (arac gerektirmez): tema | kapat. Araca göre — "
                                          "frame: kalinlik|renk|stil|radius|"
                                          "indir. bgremove: mod|otomatik_sil|tolerans|bagli_alan|"
                                          "firca_boyutu|firca_modu|yumusat|geri_al|sifirla|"
                                          "indir. round: sekil|radius|renk|daire_boyutu|"
                                          "yakinlastir|konum_sifirla|indir|hepsini_indir. "
                                          "format: hedef|kalite|hepsini_indir. ico: "
                                          "yakinlastir|konum_sifirla|boyut_ac_kapa|indir. "
                                          "merge: duzen|sutun|hedef_boyut|bosluk|opaklik|"
                                          "zemin_rengi|indir. video: kare_suresi|gecis|"
                                          "gecis_suresi|cozunurluk|format|zemin_rengi|"
                                          "ses_duzeyi|olustur|iptal|indir. ocr: dil|calistir|"
                                          "kopyala|txt_indir|word_indir. pdf2img: kalite|"
                                          "hepsini_indir. pdf2word: indir.")},
                "deger": {"type": "STRING",
                          "description": ("İsteğe bağlı: ayarın yeni değeri (sayı, hex renk "
                                          "kodu, ya da yukarıdaki enum'lardan biri). eylem='tema' "
                                          "için kullanıcının söylediği tema adını Türkçe olarak "
                                          "olduğu gibi ver ('mavi'/'yeşil'/'krem'), çevirmeye "
                                          "çalışma. Değer gerektirmeyen eylemler (indir, geri_al, "
                                          "sifirla, olustur, calistir vb.) için boş bırak.")}
            },
            "required": ["arac", "eylem"]
        }
    },
    {
        "name": "video_atolyesi_command",
        "description": ("Video Atölyesini tarayıcıda açar — video kırpma, birleştirme, "
                        "ses çıkarma/ekleme, sıkıştırma, hazır oran/biçim ayarları ve "
                        "ekran/kamera kaydı işlemlerini tek sayfada topluyor. Kendi "
                        "yerel sunucusu YERİNDE ile birlikte otomatik başlar, ayrı "
                        "kurulum/başlatma gerekmez. "
                        "'video atölyesini aç' / 'video düzenleme aracını aç' / "
                        "'video montaj aracını aç' bu aracı açar."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "video_atolyesi_ayar_command",
        "description": ("Video Atölyesi tarayıcıda AÇIKKEN, içindeki bir sekmeye (Düzenleyici/ "
                        "Slayt/Kayıt) geçer VE o sekmedeki bir AYARI değiştirir ya da bir "
                        "işlemi tetikler — sanki kullanıcı ilgili kutuyu/düğmeyi kendi "
                        "tıklamış gibi. DİKKAT: bu, video_atolyesi_command'dan (aracı SADECE "
                        "AÇAN komut) TAMAMEN FARKLI — burada araç zaten açık olmalı ve amaç "
                        "İÇİNDEKİ bir ayarı değiştirmek/bir işlemi başlatmak. ÖNEMLİ: dosya "
                        "seçme (video/ses/görsel açma) tarayıcı güvenliği nedeniyle sesle "
                        "YAPILAMAZ — kullanıcı dosyayı önce elle seçmelidir; bu araç sadece "
                        "o AÇIK dosya üzerindeki ayarları/işlemleri kontrol eder. "
                        "Örnekler: 'hızı 2 kat yap', 'videoyu 90 derece sağa döndür', "
                        "'9:16 hikaye oranında kırp', 'videoyu dışa aktar', 'sesi ayır', "
                        "'dosyayı küçült', 'düşük kalitede sıkıştır', 'slayt sekmesine geç', "
                        "'çözünürlüğü 1920x1080 yap', 'görseller arası geçiş ekle', 'slayt "
                        "videosunu oluştur', 'kayıt sekmesine geç', 'ekran kaydı moduna geç', "
                        "'kaydı başlat', 'kaydı durdur', 'kamerayı aç', 'mikrofonu kapat', "
                        "'kaydı mp4'e dönüştür', 'temayı yeşil yap', 'aracı kapat' gibi."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "sekme": {"type": "STRING",
                          "description": "'editor' (Düzenleyici) | 'slides' (Slayt Oluştur) | 'record' (Kayıt)"},
                "eylem": {"type": "STRING",
                          "description": ("Hangi ayar/işlem — biri: kirpma_modu | hiz | donus | "
                                          "fade_giris | fade_cikis | metin | metin_konum | "
                                          "kirp_ac_kapa | kirp_sifirla | kirp_9_16 | kirp_1_1 | "
                                          "kirp_16_9 | disa_aktar | devam_et | sikistir_kalite | "
                                          "sikistir | ses_ayir | sessiz_indir | ses_modu | "
                                          "ses_uygula | kuyruga_ekle | birlestir | "
                                          "slayt_cozunurluk | slayt_gecis | slayt_olustur | "
                                          "kayit_modu | kayit_gecikme | kaynak_sec | "
                                          "kaydi_baslat | kaydi_duraklat | kaydi_durdur | "
                                          "kayit_vazgec | kamera_ac_kapa | mikrofon_ac_kapa | "
                                          "kaydi_donustur | duzenleyiciye_gonder | tema | kapat")},
                "deger": {"type": "STRING",
                          "description": ("İsteğe bağlı: ayarın yeni değeri (ör. hız için '2', "
                                          "döndürme için '90cw', kırpma modu için 'keep'/"
                                          "'remove', metin için serbest metin, tema için "
                                          "'blue'/'green'/'cream'). Bazı eylemler (ör. "
                                          "disa_aktar, kirp_sifirla, kaydi_baslat) değer "
                                          "gerektirmez, boş bırak.")}
            },
            "required": ["sekme", "eylem"]
        }
    },
    {
        "name": "kukla_kodlama_command",
        "description": ("YERİNDE Kodlama Aracını tarayıcıda açar — Scratch benzeri BLOK "
                        "TABANLI (sürükle-bırak) YA DA PYTHON METİN TABANLI kodlamayla, "
                        "3 BOYUTLU karakterleri (basit eklemli figürler) programlayabildiğin "
                        "bir araçtır. Bu araç, GERÇEK (2 boyutlu) Scratch'i sesle kontrol "
                        "eden ayrı bir sistemden (scratch_command) TAMAMEN FARKLIDIR — "
                        "bu araçtaki karakterler 3 BOYUTLUDUR ve kendi motoruyla çalışır. "
                        "'yerinde kodlama aracını aç', 'blok kodlama aracını aç', "
                        "'3 boyutlu karakter programlama aracını aç' gibi komutlarla açılır. "
                        "SES TANIMA NOTU: 'kodlama' konuşma tanımada bazen 'kotlama' şeklinde "
                        "duyulabilir ('kotlama' diye bir kelime yoktur) — bu HER ZAMAN bu "
                        "aracı işaret eder, Kotlin programlama diliyle karıştırma."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "kukla_calistir_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, tüm 3B karakterlerin "
                        "programlarını (hangi moddaysa - blok ya da Python) aynı anda "
                        "çalıştırır. Sadece bu araç açıkken anlamlıdır. 'programı çalıştır', "
                        "'karakterleri çalıştır', 'başlat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "kukla_durdur_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, çalışmakta olan "
                        "programı durdurur. 'programı durdur', 'karakterleri durdur' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "kukla_ekle_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, yeni bir 3B karakter "
                        "oluşturur. DİKKAT: gerçek (2 boyutlu) Scratch'teki kukla/sprite "
                        "ekleme komutuyla KARIŞTIRMA — bu, YERİNDE Kodlama Aracı bağlamında "
                        "'yeni karakter oluştur', '3B karakter oluştur' gibi komutlarla "
                        "tetiklenir. Sadece bu araç açıkken anlamlıdır. "
                        "SES TANIMA NOTU: bu araç açıkken 'kukla ekle' komutu bazen 'kutla "
                        "ekle' şeklinde duyulabilir (anlamsız bir ifadedir) — bu bağlamda "
                        "HER ZAMAN 'kukla ekle' (yeni karakter oluştur) olarak yorumla."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "isim": {"type": "STRING", "description": "İsteğe bağlı: yeni karakterin adı."}
            },
            "required": []
        }
    },
    {
        "name": "kukla_sec_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, 'son'/'ilk' eklenen "
                        "karakteri seçer (programlamak için). 'son karakteri seç', 'ilk "
                        "karakteri seç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tanim": {"type": "STRING", "description": "İsteğe bağlı: 'son' ya da 'ilk'. Belirtilmezse son eklenen karakter seçilir."}
            },
            "required": []
        }
    },
    {
        "name": "kukla_mod_degistir_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, seçili karakterin "
                        "kodlama modunu Blok Modu ile Python Modu arasında değiştirir. "
                        "'blok moduna geç', 'python moduna geç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mod": {"type": "STRING", "description": "'blok' ya da 'python'."}
            },
            "required": ["mod"]
        }
    },
    {
        "name": "kukla_tema_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, arayüz temasını değiştirir. "
                        "'temayı yeşil yap', 'krem temaya geç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"tema": {"type": "STRING", "description": "'mavi' | 'yeşil' | 'krem'"}},
            "required": ["tema"]
        }
    },
    {
        "name": "kukla_kapat_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. "
                        "'kodlama aracını kapat', 'aracı kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "kukla_zemin_dokusu_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, Sahnenin zemin (yer/döşeme) "
                        "dokusunu değiştirir — özellik panelindeki '🟫 Zemin' açılır menüsünden "
                        "seçmiş gibi. Düz (varsayılan), çim, ahşap, halı (desenli/tüylü), minder, "
                        "koltuk, deri, taş duvar, kiremit (eski/düz) dokuları arasından seçilebilir. "
                        "'zemine çim dokusu uygula', 'zemini ahşap yap', 'zemin dokusunu halı yap', "
                        "'zemine taş duvar dokusu koy' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doku": {"type": "STRING",
                         "description": "düz | çim | ahşap | halı desenli | halı tüylü | minder | koltuk | deri | taş duvar | kiremit | kiremit düz"}
            },
            "required": ["doku"]
        }
    },
    {
        "name": "kukla_kaydet_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN, projeyi (tüm karakterler, "
                        "blok/Python programlarıyla birlikte) Çalışmalarım/Karakter-Kodlama "
                        "klasörüne bir .yerinde dosyası olarak kaydeder. 'karakter projesini "
                        "kaydet', 'projeyi çalışmalarıma kaydet' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "kukla_ac_command",
        "description": ("Çalışmalarım/Karakter-Kodlama klasöründe verilen isme uyan (ya da "
                        "isim verilmezse en son kaydedilen) bir .yerinde proje dosyasını "
                        "bulup YERİNDE Kodlama Aracına yükler. 'karakter projemi aç', 'son "
                        "kaydettiğim karakter projesini aç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı: açılacak .yerinde dosyasının adı ya da adının bir kısmı."}
            },
            "required": []
        }
    },
    {
        "name": "karakter_blok_ekle_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN VE seçili karakter YA DA "
                        "Sahne 'Blok Modu'ndayken, kod alanına yeni bir kodlama bloğu ekler — "
                        "tıpkı sol menüden sürükleyip bırakmış gibi. DİKKAT: bu, "
                        "'5 adım git' gibi anlık ÇALIŞTIRMA komutlarından (Scratch'e giden "
                        "scratch_command'dan) TAMAMEN FARKLI — burada amaç bloğu görsel "
                        "PROGRAMA EKLEMEK. 'ileri git bloğunu ekle', '90 derece sağa dön "
                        "bloğu ekle', '3 saniye bekle bloğunu ekle', 'zıpla bloğu ekle', "
                        "'konuş bloğunu ekle', 'renk değiştir bloğu ekle', 'arkaplanı "
                        "değiştir bloğu ekle', 'bip sesi çal bloğu ekle', 'zamanlayıcıyı "
                        "sıfırla bloğu ekle', 'sor ve bekle bloğu ekle', 'tümünü durdur "
                        "bloğunu ekle', 'bayrağa tıklanınca bloğunu ekle', 'tuşa basılınca "
                        "bloğunu ekle', 'sonsuza kadar tekrarla bloğunu ekle' gibi — cümlede "
                        "AÇIKÇA 'blok/bloğu ekle' geçtiğinde bu aracı kullan. Sahne seçiliyken "
                        "arkaplan/ses/zamanlayıcı/soru bloklarını, karakter seçiliyken hareket/"
                        "görünüm bloklarını eklemek en doğal kullanımdır."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "blok": {"type": "STRING",
                         "description": ("Eklenecek bloğun dahili adı — biri: kukla_ileri_git | "
                                         "kukla_geri_git | kukla_sag_don | kukla_sol_don | "
                                         "kukla_zipla | kukla_kenara_deginde_sektir | "
                                         "kukla_x_degistir | kukla_z_degistir | kukla_yone_bak | "
                                         "kukla_kaydirarak_git | kukla_konuma_git | "
                                         "kukla_bekle_saniye | kukla_konus | kukla_konus_sure | "
                                         "kukla_dusun | kukla_renk_degistir | kukla_boyut_ayarla | "
                                         "kukla_boyut_degistir | kukla_goster_gizle | "
                                         "kukla_sonraki_kostum | kukla_kostum_degistir | "
                                         "kukla_arkaplan_degistir | kukla_sonraki_arkaplan | "
                                         "kukla_bip_cal | kukla_ses_cal | kukla_tumunu_durdur | "
                                         "kukla_bayrak_tiklaninca | kukla_tusa_basilinca | "
                                         "kukla_sonsuza_kadar | kukla_zamanlayici_sifirla | "
                                         "kukla_sor_bekle")},
                "deger": {"type": "STRING",
                          "description": ("İsteğe bağlı: bloğun ana girişine uygulanacak değer. "
                                          "Çoğu blok için sayısaldır (MESAFE/DERECE/SANIYE/"
                                          "MIKTAR/YUZDE/NUMARA vb.), ör. '5', '90', '3'. "
                                          "kukla_konus / kukla_konus_sure / kukla_dusun / "
                                          "kukla_sor_bekle için ise bir METİN olmalıdır (ör. "
                                          "'Merhaba!', 'Adın ne?'). Kullanıcı bir değer "
                                          "söylemediyse boş bırak, toolbox'taki varsayılan "
                                          "değer kullanılır.")}
            },
            "required": ["blok"]
        }
    },
    {
        "name": "karakter_blok_sil_command",
        "description": ("YERİNDE Kodlama Aracı tarayıcıda AÇIKKEN VE seçili karakter YA DA "
                        "Sahne 'Blok Modu'ndayken, kod alanından bir kodlama bloğunu siler — "
                        "sesli komutla en son eklenen blok varsa onu, yoksa bloklar zincirinin "
                        "en sonundakini siler. 'bloğu sil', 'son bloğu sil', 'son eklenen "
                        "bloğu sil', 'bu bloğu sil' gibi komutlarla tetiklenir. DİKKAT: bu, "
                        "karakterin/Sahnenin kendisini silmekle (ör. 'karakteri sil') "
                        "KARIŞTIRILMAMALIDIR — sadece tek bir KOD BLOĞUNU siler."),
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "bilisim_robotik_atolyesi_command",
        "description": ("Bilişim ve Robotik Atölyesini tarayıcıda açar — 5-6. sınıf "
                        "müfredatına uygun, çevrimdışı çalışan etkileşimli bir bilişim ve "
                        "robotik ders aracı. Giriş, Bilgi ve Teknoloji, Robotlar ve "
                        "Hayatımız, Web Tasarımının Temelleri, Çevrimiçi Ortamlar ve Ortak "
                        "Çalışma, Dijital İçerik Üretimi, Genel Sınav ve Kaynaklar "
                        "ünitelerinden oluşur; çevirme kartları, eşleştirme oyunları, "
                        "sıralama alıştırmaları, mini sınavlar ve canlı önizlemeli bir HTML "
                        "editörü içerir. "
                        "'bilişim ve robotik atölyesini aç', 'bilişim atölyesini aç', "
                        "'robotik dersini aç', '5-6 sınıf bilişim aracını aç' gibi "
                        "komutlarla açılır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "bilisim_robotik_unite_gec_command",
        "description": ("Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, gezinme "
                        "çubuğundan bir üniteye geçer. 'giriş', '1. ünite'/'bilgi ve "
                        "teknoloji', '2. ünite'/'robotlar', '3. ünite'/'web tasarımı', '4. "
                        "ünite'/'çevrimiçi ortamlar', '5. ünite'/'dijital içerik', 'genel "
                        "sınav', 'kaynaklar' üniteleri arasından geçilebilir. '1. üniteye "
                        "geç', 'robot ünitesini aç', 'sınava geç', 'kaynaklara git' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "unite": {"type": "STRING", "description": "giriş | 1. ünite (bilgi) | 2. ünite (robotlar) | 3. ünite (web) | 4. ünite (çevrimiçi) | 5. ünite (içerik) | sınav | kaynaklar"}
            },
            "required": ["unite"]
        }
    },
    {
        "name": "bilisim_robotik_tema_command",
        "description": ("Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, arayüz temasını "
                        "değiştirir. 'temayı mavi yap', 'yeşil temaya geç' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"tema": {"type": "STRING", "description": "'krem' | 'mavi' | 'yeşil'"}},
            "required": ["tema"]
        }
    },
    {
        "name": "bilisim_robotik_kapat_command",
        "description": ("Bilişim ve Robotik Atölyesi tarayıcıda AÇIKKEN, o sekmeyi "
                        "kapatmayı dener. 'bilişim atölyesini kapat', 'aracı kapat' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "bilisim_labirent_komut_command",
        "description": ("Bilişim ve Robotik Atölyesi'nin Ünite 2 (Robotlar) bölümündeki "
                        "labirent bulmacasına bir robot komutu ekler. İki labirent bulmacası "
                        "vardır (1 ve 2); belirtilmezse ilki kullanılır. 'ileri git bloğu "
                        "ekle', 'robota sağa dön komutu ekle', '2. labirentte sola dön' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "komut": {"type": "STRING", "description": "'ileri' | 'sağa dön' | 'sola dön'"},
                "labirent": {"type": "STRING", "description": "'1' ya da '2' (verilmezse '1')"}
            },
            "required": ["komut"]
        }
    },
    {
        "name": "bilisim_labirent_calistir_command",
        "description": ("Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasındaki "
                        "programı çalıştırır. 'labirenti çalıştır', 'robotu çalıştır' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"labirent": {"type": "STRING", "description": "'1' ya da '2' (verilmezse '1')"}},
            "required": []
        }
    },
    {
        "name": "bilisim_labirent_geri_al_command",
        "description": ("Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasında en son "
                        "eklenen robot komutunu geri alır. 'son komutu geri al' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"labirent": {"type": "STRING", "description": "'1' ya da '2' (verilmezse '1')"}},
            "required": []
        }
    },
    {
        "name": "bilisim_labirent_temizle_command",
        "description": ("Bilişim ve Robotik Atölyesi'nin Ünite 2 labirent bulmacasındaki tüm "
                        "robot programını temizler. 'programı temizle' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"labirent": {"type": "STRING", "description": "'1' ya da '2' (verilmezse '1')"}},
            "required": []
        }
    },
    {
        "name": "bilisim_kart_cevir_command",
        "description": ("Bilişim ve Robotik Atölyesi'nde, o an açık ünitedeki bir çevirme "
                        "kartını (terim/tanım) çevirir. 'kart_no' verilirse o sıradaki kart "
                        "çevrilir; verilmezse henüz çevrilmemiş ilk kart çevrilir. 'kartı "
                        "çevir', '3. kartı çevir' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"kart_no": {"type": "STRING", "description": "İsteğe bağlı: kaçıncı kart (1'den başlar)."}},
            "required": []
        }
    },
    {
        "name": "bilisim_quiz_cevapla_command",
        "description": ("Bilişim ve Robotik Atölyesi'nde, o an açık ünitedeki bir mini "
                        "sınavın ilk cevaplanmamış sorusunu, verilen seçenekle cevaplar. 'A "
                        "seçeneğini işaretle', 'ikinci seçeneği seç', 'C diyorum' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"secenek": {"type": "STRING", "description": "'A'|'B'|'C'|'D' ya da '1'|'2'|'3'|'4'"}},
            "required": ["secenek"]
        }
    },
    {
        "name": "bilisim_ilerlemeyi_sifirla_command",
        "description": ("Bilişim ve Robotik Atölyesi'ndeki TÜM ünite ilerlemesini "
                        "(tamamlanan üniteler, rozetler) sıfırlar — dikkatli kullanılmalı, "
                        "geri alınamaz. 'ilerlemeyi sıfırla', 'baştan başla' gibi AÇIKÇA "
                        "istendiğinde tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "bilisim_web_ekle_command",
        "description": ("Bilişim ve Robotik Atölyesi'nin Ünite 3 (Web Tasarımı) bölümündeki "
                        "canlı HTML editörüne bir HTML öğesi ekler. Sadece Ünite 3 açıkken "
                        "anlamlıdır. 'başlık ekle', 'paragraf ekle', 'resim yeri ekle', "
                        "'bağlantı ekle', 'liste ekle' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"eleman": {"type": "STRING", "description": "'başlık' | 'paragraf' | 'resim' | 'bağlantı' | 'liste'"}},
            "required": ["eleman"]
        }
    },
    {
        "name": "pico_devre_atolyesi_command",
        "description": ("YERİNDE Pico Devre Atölyesini tarayıcıda açar — Raspberry Pi Pico / "
                        "Pico W / Arduino Nano / ESP32 DevKit V1 için Tinkercad Circuits benzeri "
                        "bir breadboard + Blockly (blok tabanlı) kodlama aracı. Kullanıcı LED, "
                        "direnç, buton, buzzer, potansiyometre, ışık sensörü (LDR), servo motor, "
                        "ultrasonik sensör, OLED ekran, DC motor, motor sürücü, pil ve güneş "
                        "paneli gibi devre elemanlarını KENDİSİ breadboard'a yerleştirip kablo "
                        "çekerek SIFIRDAN bir devre KURAR, Blockly blokları ya da (kart seçimine "
                        "göre) gerçek MicroPython/Arduino C++ koduyla programlayıp canlı "
                        "simülasyonunu izler. "
                        "'pico devre atölyesini aç', 'pico devre aracını aç', 'breadboard "
                        "aracını aç', 'devre kurma aracını aç' gibi komutlarla açılır. "
                        "SES TANIMA NOTU: 'pico' bazen 'piko' şeklinde duyulabilir — bu HER "
                        "ZAMAN bu aracı işaret eder. DİKKAT: robotik_simulator_command'dan "
                        "TAMAMEN FARKLI bir araçtır — ORADA kullanıcı ÖNCEDEN HAZIRLANMIŞ bir "
                        "robot senaryosunu SEÇİP İZLER (kendi devresini kurmaz); BURADA "
                        "kullanıcı devre elemanlarını KENDİSİ EKLEYİP KURAR ve breadboard "
                        "üzerinde gerçek, özgün bir devre inşa eder. Cümlede 'atölye', "
                        "'breadboard', 'devre elemanı ekle/kur', ya da spesifik bir devre "
                        "elemanı adı (LED/direnç/servo/motor sürücü vb.) geçiyorsa DAİMA bu "
                        "aracı kullan, robotik_simulator_command'ı DEĞİL."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_kart_degistir_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, kullanılan kartı değiştirir. "
                        "'Pico'ya geç', 'Pico W kullan', 'Nano'ya geç', 'ESP32'ye geç' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "kart": {"type": "STRING", "description": "'pico' | 'pico w' | 'nano' | 'esp32'"}
            },
            "required": ["kart"]
        }
    },
    {
        "name": "pico_bilesen_ekle_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard'a (ya da serbest "
                        "alana) yeni bir devre elemanı ekler — sanki sol paletten sürükleyip "
                        "bırakmış gibi. 'LED ekle', 'direnç ekle', 'buton ekle', 'buzzer ekle', "
                        "'potansiyometre ekle', 'ışık sensörü ekle', 'servo motor ekle', "
                        "'ultrasonik sensör ekle', 'OLED ekran ekle', 'DC motor ekle', 'motor "
                        "sürücü ekle', 'pil ekle', 'güneş paneli ekle' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen": {"type": "STRING",
                            "description": ("led | direnç | buton | buzzer | potansiyometre | "
                                            "ışık sensörü | servo | ultrasonik | oled | dc motor | "
                                            "motor sürücü | pil | güneş paneli")}
            },
            "required": ["bilesen"]
        }
    },
    {
        "name": "pico_bilesen_sil_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki "
                        "bir devre elemanını (ve ona bağlı tüm kabloları) siler. 'bilesen' "
                        "verilirse o türden EN SON EKLENEN öğe silinir; verilmezse SON EKLENEN "
                        "devre elemanı (türü ne olursa olsun) silinir. 'LED'i sil', 'son "
                        "eklenen direnci sil', 'son eklenen devre elemanını sil' gibi "
                        "komutlarla tetiklenir. DİKKAT: pico_blok_sil_command'dan TAMAMEN "
                        "FARKLI — bu bir kodlama bloğunu değil, breadboard üzerindeki FİZİKSEL "
                        "bir devre elemanını siler."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen": {"type": "STRING", "description": "İsteğe bağlı: silinecek devre elemanı türü (led, direnç, buton, buzzer, potansiyometre, ışık sensörü, servo, ultrasonik, oled, dc motor, motor sürücü, pil, güneş paneli). Boş bırakılırsa en son eklenen (herhangi bir türden) devre elemanı silinir."}
            },
            "required": []
        }
    },
    {
        "name": "pico_bilesen_dondur_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki "
                        "bir devre elemanını döndürür (özellik panelindeki '↻ Döndür' "
                        "düğmesine basmış gibi). Breadboard'a takılan elemanlar (LED, direnç, "
                        "buton, buzzer, potansiyometre, LDR) 0/180 derece arasında aynalanır; "
                        "serbest duran elemanlar (servo, ultrasonik, OLED, DC motor, motor "
                        "sürücü, pil, güneş paneli) 90 derecelik adımlarla tam döner. 'bilesen' "
                        "verilirse o türden EN SON EKLENEN öğe döndürülür; verilmezse SON "
                        "EKLENEN devre elemanı döndürülür. 'LED'i döndür', 'servoyu döndür', "
                        "'son eklenen devre elemanını döndür' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen": {"type": "STRING", "description": "İsteğe bağlı: döndürülecek devre elemanı türü. Boş bırakılırsa en son eklenen (herhangi bir türden) devre elemanı döndürülür."}
            },
            "required": []
        }
    },
    {
        "name": "pico_bilesen_tasi_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki bir "
                        "devre elemanını sağa, sola, yukarı ya da aşağı taşır — sanki elle "
                        "sürükleyip bırakmış gibi. Breadboard'a takılı elemanlarda 'yukarı'/"
                        "'aşağı' komşu satıra (a-e ya da f-j şeridi İÇİNDE), 'sağa'/'sola' komşu "
                        "sütuna taşır; serbest duran elemanlarda (servo, ultrasonik, OLED, DC "
                        "motor, motor sürücü, pil, güneş paneli) dört yöne de serbestçe taşınır. "
                        "'LED'i sağa taşı', 'servoyu 3 birim yukarı kaydır', 'son eklenen devre "
                        "elemanını sola taşı' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen": {"type": "STRING", "description": "İsteğe bağlı: taşınacak devre elemanı türü. Boş bırakılırsa en son eklenen (herhangi bir türden) devre elemanı taşınır."},
                "yon": {"type": "STRING", "description": "'sağ' | 'sol' | 'yukarı' | 'aşağı'"},
                "miktar": {"type": "STRING", "description": "İsteğe bağlı: kaç adım taşınacağı (verilmezse 1)."}
            },
            "required": ["yon"]
        }
    },
    {
        "name": "pico_kablo_sil_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki "
                        "bir kabloyu siler. Uç bilgileri (pico_bagla_command ile AYNI kurallar: "
                        "bileşen türü boşsa kart pini) verilirse o iki uç arasındaki kablo "
                        "bulunup silinir; hiçbir uç verilmezse EN SON ÇEKİLEN kablo silinir. "
                        "'son kabloyu sil', 'LED'in eksi bacağı ile GND arasındaki kabloyu sil' "
                        "gibi komutlarla tetiklenir. DİKKAT: pico_bilesen_sil_command'dan "
                        "TAMAMEN FARKLI — bu SADECE kabloyu/bağlantıyı siler, elemanın "
                        "kendisine dokunmaz."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen1": {"type": "STRING", "description": "İsteğe bağlı: birinci ucun devre elemanı türü. Boşsa (ya da 'kart' denirse) kart pinidir."},
                "pin1": {"type": "STRING", "description": "İsteğe bağlı: birinci ucun pin adı (kart pini ör. 'GND'/'GP2', ya da bileşene özgü 'artı'/'eksi'/'a' vb.)."},
                "bilesen2": {"type": "STRING", "description": "İsteğe bağlı: ikinci ucun devre elemanı türü."},
                "pin2": {"type": "STRING", "description": "İsteğe bağlı: ikinci ucun pin adı."}
            },
            "required": []
        }
    },
    {
        "name": "pico_blok_ekle_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN VE Blok Modu'ndayken, Blockly "
                        "çalışma alanına ('süresiz' döngüsünün içine) yeni bir kodlama bloğu "
                        "ekler — tıpkı sol menüden sürükleyip bırakmış gibi. DİKKAT: bu, "
                        "'GP2 pinini yüksek yap' gibi anlık bir eylem DEĞİL — amaç bloğu "
                        "GÖRSEL PROGRAMA eklemek. Cümlede AÇIKÇA 'blok/bloğu ekle' geçtiğinde "
                        "kullan. 'dijital yaz bloğu ekle', 'PWM yaz bloğu ekle', 'servo döndür "
                        "bloğu ekle', 'ton çal bloğu ekle', 'yerleşik LED bloğu ekle', 'bekle "
                        "bloğu ekle', 'seri yazdır bloğu ekle', 'motor sürücü çalıştır bloğu "
                        "ekle', 'ekrana yaz bloğu ekle', 'ekranı temizle bloğu ekle' gibi."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "blok": {"type": "STRING",
                         "description": ("Eklenecek bloğun dahili adı — biri: pico_digital_write | "
                                         "pico_pwm_write | pico_servo_write | pico_tone_write | "
                                         "pico_tone_stop | pico_onboard_led | pico_wait | "
                                         "pico_serial_print | pico_motor_write | "
                                         "pico_display_write | pico_display_clear")},
                "pin": {"type": "STRING", "description": "İsteğe bağlı: ana pin adı (ör. 'GP2', 'D13', 'A0'). Motor/ekran bloklarında IN1/SDA karşılığıdır."},
                "pin2": {"type": "STRING", "description": "İsteğe bağlı: ikinci pin (motor sürücü için IN2, ekran için SCL)."},
                "deger": {"type": "STRING", "description": "İsteğe bağlı: bloğun sayısal/metin değeri (PWM için 0-255, servo için 0-180 derece, ton için Hz, bekle için süre, seri/ekran yazdırma için serbest metin)."},
                "yon": {"type": "STRING", "description": "İsteğe bağlı: 'HIGH'/'LOW' (dijital yaz, yerleşik LED) ya da 'FWD'/'BACK'/'STOP' (motor sürücü yönü)."},
                "birim": {"type": "STRING", "description": "İsteğe bağlı: bekle bloğu için 'MS' ya da 'S'."}
            },
            "required": ["blok"]
        }
    },
    {
        "name": "pico_blok_sil_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, Blockly çalışma alanındaki en "
                        "son eklenen kodlama bloğunu siler ('başlangıçta'/'süresiz' bloklarına "
                        "dokunmaz). 'bloğu sil', 'son bloğu sil' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_mod_degistir_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, görünümü Blok Modu (Blockly) "
                        "ile Kod Modu (o an seçili karta göre üretilen gerçek MicroPython ya da "
                        "Arduino C++ kodu) arasında değiştirir. 'blok moduna geç', 'kod moduna "
                        "geç', 'python koduna geç', 'kodu göster' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"mod": {"type": "STRING", "description": "'blok' ya da 'kod'."}},
            "required": ["mod"]
        }
    },
    {
        "name": "pico_tema_degistir_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, arayüz temasını değiştirir. "
                        "'temayı yeşil yap', 'krem temaya geç', 'mavi temaya dön' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"tema": {"type": "STRING", "description": "'mavi' | 'yeşil' | 'krem'"}},
            "required": ["tema"]
        }
    },
    {
        "name": "pico_yakinlastir_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard görünümünü "
                        "yakınlaştırır, uzaklaştırır ya da sıfırlar. 'yakınlaştır', "
                        "'uzaklaştır', 'yakınlaştırmayı sıfırla' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"yon": {"type": "STRING", "description": "'in' (yakınlaştır) | 'out' (uzaklaştır) | 'reset' (sıfırla)"}},
            "required": ["yon"]
        }
    },
    {
        "name": "pico_calistir_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, devrenin canlı simülasyonunu "
                        "başlatır ('Simülasyonu Başlat' düğmesine basmış gibi). 'simülasyonu "
                        "başlat', 'devreyi çalıştır' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_durdur_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, çalışmakta olan simülasyonu "
                        "durdurur. 'simülasyonu durdur', 'devreyi durdur' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_kaydet_command",
        "description": ("Pico Devre Atölyesindeki projeyi (seçili kart, tüm devre elemanları/"
                        "kablolar ve Blockly programıyla birlikte) Çalışmalarım/Devre-Atolyesi "
                        "klasörüne bir .yerpico dosyası olarak kaydeder. 'devre projesini "
                        "kaydet', 'projeyi çalışmalarıma kaydet' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_ac_command",
        "description": ("Çalışmalarım/Devre-Atolyesi klasöründe verilen isme uyan (ya da isim "
                        "verilmezse en son kaydedilen) bir .yerpico proje dosyasını bulup Pico "
                        "Devre Atölyesine yükler. 'devre projemi aç', 'son kaydettiğim devre "
                        "projesini aç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı: açılacak .yerpico dosyasının adı ya da adının bir kısmı."}
            },
            "required": []
        }
    },
    {
        "name": "pico_kodu_indir_command",
        "description": ("Pico Devre Atölyesinde o an seçili karta göre üretilen GERÇEK kodu "
                        "(Pico/Pico W için MicroPython .py, Arduino Nano/ESP32 için Arduino C++ "
                        ".ino) Çalışmalarım/Devre-Atolyesi klasörüne kaydeder. 'kodu indir', "
                        "'python kodunu kaydet', 'arduino kodunu çalışmalarıma kaydet' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "pico_bagla_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, breadboard/serbest alandaki "
                        "iki ucu (bir devre elemanının belirli bir pini VE/YA DA kartın bir "
                        "pini) bir kabloyla birbirine bağlar — sanki elle kablo çekmiş gibi. "
                        "'LED'in artı bacağını GP2'ye bağla', 'LED'in eksi ucunu GND'ye bağla', "
                        "'direncin bir ucunu LED'in eksi bacağına bağla', 'servonun sinyal "
                        "pinini GP15'e bağla', 'butonun bir ucunu 3V3'e bağla' gibi komutlarla "
                        "tetiklenir. Cümlede AÇIKÇA 'bağla'/'kabloyla bağla' geçtiğinde kullan."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "bilesen1": {"type": "STRING", "description": "Birinci ucun ait olduğu devre elemanı türü (led, direnç, buton, buzzer, potansiyometre, ışık sensörü, servo, ultrasonik, oled, dc motor, motor sürücü, pil, güneş paneli). Boş bırakılırsa (ya da 'kart' denirse) bu bir KART pinidir."},
                "pin1": {"type": "STRING", "description": "Birinci ucun pin adı — bilesen1 boşsa kartın pin adı (ör. 'GND', 'GP2', '3V3', 'D13', 'A0'); doluysa o bileşene özgü uç adı (ör. 'artı', 'eksi', 'sinyal', 'a', 'b', 'in1')."},
                "bilesen2": {"type": "STRING", "description": "İkinci ucun ait olduğu devre elemanı türü. Boş bırakılırsa (ya da 'kart' denirse) bu bir KART pinidir."},
                "pin2": {"type": "STRING", "description": "İkinci ucun pin adı — bilesen2 boşsa kartın pin adı, doluysa o bileşene özgü uç adı."}
            },
            "required": ["bilesen1", "pin1", "pin2"]
        }
    },
    {
        "name": "pico_seri_monitor_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, Seri Monitör panelini açar "
                        "ya da kapatır (kod içindeki 'seri yazdır' bloklarının çıktısını "
                        "gösteren panel). 'seri monitörü aç', 'seri port ekranını göster', "
                        "'seri monitörü kapat' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "durum": {"type": "STRING", "description": "'ac' (aç, varsayılan) ya da 'kapat'."}
            },
            "required": []
        }
    },
    {
        "name": "pico_kapat_command",
        "description": ("Pico Devre Atölyesi tarayıcıda AÇIKKEN, o sekmeyi kapatmayı dener. "
                        "'pico devre atölyesini kapat', 'aracı kapat' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_tema_command",
        "description": ("3B Tasarım Stüdyosu YA DA Robot Tasarım Atölyesi tarayıcıda AÇIKKEN "
                        "(ikisi de aynı köprüyü paylaşır, hangisi açıksa o etkilenir), arayüz "
                        "temasını değiştirir. 'temayı yeşil yap', 'krem temaya geç' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {"tema": {"type": "STRING", "description": "'mavi' | 'yeşil' | 'krem'"}},
            "required": ["tema"]
        }
    },
    {
        "name": "tasarim_kapat_command",
        "description": ("3B Tasarım Stüdyosu YA DA Robot Tasarım Atölyesi tarayıcıda AÇIKKEN "
                        "(ikisi de aynı köprüyü paylaşır, hangisi açıksa o etkilenir), o sekmeyi "
                        "kapatmayı dener. 'tasarım stüdyosunu kapat', 'robot tasarım aracını "
                        "kapat', 'aracı kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_ekle_sekil_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "sahneye yeni bir temel şekil ekler (dişli çark ve genel sensör "
                        "şekilleri dahil). Sadece bu araçlardan biri açıkken anlamlıdır. "
                        "'küp ekle', 'bir silindir ekle', 'küre ekle', 'koni ekle', "
                        "'piramit ekle', 'simit ekle', 'dişli ekle' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "sekil": {
                    "type": "STRING",
                    "description": "Eklenecek şekil: küp, silindir, küre, koni, piramit, simit ya da dişli."
                }
            },
            "required": ["sekil"]
        }
    },
    {
        "name": "tasarim_robot_parca_ekle_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "hazır renk/ölçek/malzeme ön ayarlarıyla bir ROBOT PARÇASI ekler "
                        "(gövde, tekerlek, eklem, kol, dişli çark, motor, sensör, ultrasonik "
                        "mesafe sensörü, PIR hareket sensörü, ışık sensörü). Sadece bu "
                        "araçlardan biri açıkken anlamlıdır. 'gövde ekle', 'tekerlek ekle', "
                        "'ultrasonik sensör ekle', 'ışık sensörü ekle' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "parca": {
                    "type": "STRING",
                    "description": "Eklenecek robot parçası: gövde, tekerlek, eklem, kol, dişli, motor, sensör, ultrasonik, pir, ışık sensörü."
                }
            },
            "required": ["parca"]
        }
    },
    {
        "name": "tasarim_renk_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesnenin "
                        "rengini değiştirir. Sadece bu araç açıkken ve bir nesne seçiliyken "
                        "anlamlıdır. 'rengini kırmızı yap', 'onu mavi yap', 'nesneyi yeşile boya' "
                        "gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "renk": {
                    "type": "STRING",
                    "description": "Renk adı: kırmızı, mavi, yeşil, sarı, turuncu, mor, pembe, siyah, beyaz, gri, kahverengi."
                }
            },
            "required": ["renk"]
        }
    },
    {
        "name": "tasarim_malzeme_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesnenin malzemesini (düz renk, ahşap, metal, "
                        "plastik ya da cam) değiştirir. Sadece bu araçlardan biri açıkken "
                        "ve bir nesne seçiliyken anlamlıdır. 'ahşap yap', 'metal görünümü ver', "
                        "'plastik yap', 'cam yap' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "malzeme": {
                    "type": "STRING",
                    "description": "Malzeme: düz, ahşap, metal, plastik ya da cam."
                }
            },
            "required": ["malzeme"]
        }
    },
    {
        "name": "tasarim_doku_uygula_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesneye hazır bir resim dokusu uygular (kullanıcının "
                        "kendi resim yüklemesine gerek kalmadan) — ahşap, halı (desenli ya da "
                        "tüylü), koltuk, minder, deri, duvar/taş, kiremit (düz ya da eski/"
                        "yıpranmış). Sadece bu araçlardan biri açıkken ve bir nesne seçiliyken "
                        "anlamlıdır. 'ahşap dokusu uygula', 'halı yap', 'deri kapla', 'taş görünümü "
                        "ver', 'kiremit dokusu ekle' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "doku": {
                    "type": "STRING",
                    "description": "Doku: ahşap, halı, halı tüylü, koltuk, minder, deri, duvar, taş, kiremit ya da eski kiremit."
                }
            },
            "required": ["doku"]
        }
    },
    {
        "name": "tasarim_tasi_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesneyi "
                        "belirtilen yönde bir adım taşır. Sadece bu araç açıkken ve bir "
                        "nesne seçiliyken anlamlıdır. 'nesneyi sağa taşı', 'onu sola kaydır', "
                        "'yukarı götür', 'ileri taşı' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "yon": {
                    "type": "STRING",
                    "description": "Yön: sağ, sol, yukarı, aşağı, ileri veya geri."
                }
            },
            "required": ["yon"]
        }
    },
    {
        "name": "tasarim_boyutlandir_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesneyi "
                        "büyütür ya da küçültür. Sadece bu araç açıkken ve bir nesne "
                        "seçiliyken anlamlıdır. 'nesneyi büyüt', 'onu küçült', "
                        "'genişliğini büyüt', 'yüksekliğini küçült' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "yon": {"type": "STRING", "description": "'büyüt' ya da 'küçült'."},
                "eksen": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: genişlik, yükseklik veya derinlik. Belirtilmezse üç eksende birden uygulanır."
                }
            },
            "required": ["yon"]
        }
    },
    {
        "name": "tasarim_dondur_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesneyi "
                        "45 derece döndürür. 'sağa'/'sola' yatayda (Y ekseni) döndürür; "
                        "'yukarı'/'aşağı'/'öne'/'arkaya'/'dikey' ise nesneyi dikey (X ekseni) "
                        "olarak devirir. Sadece bu araç açıkken ve bir nesne seçiliyken "
                        "anlamlıdır. 'nesneyi sağa döndür', 'onu dikey döndür', "
                        "'yukarı devir' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "yon": {
                    "type": "STRING",
                    "description": "sağa, sola (yatay) ya da yukarı, aşağı, öne, arkaya, dikey (düşey)."
                }
            },
            "required": ["yon"]
        }
    },
    {
        "name": "tasarim_donusu_baslat_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesneyi KENDİ EKSENİNDE SÜREKLİ döndürmeye başlar "
                        "(canlı önizleme — 45 derecelik tek seferlik döndürmeden farklı olarak "
                        "durana kadar dönmeye devam eder; STL/Blender'a aktarımda gerçek "
                        "animasyona dönüşür). Eksen olarak x, y, z ya da birkaçı/hepsi "
                        "belirtilebilir. Sadece bu araçlardan biri açıkken ve bir nesne "
                        "seçiliyken anlamlıdır. 'kendi ekseninde döndür', 'x ekseninde döndürmeye "
                        "başla', 'her eksende döndür' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "eksen": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: x, y, z, 'x ve z' gibi bir kombinasyon ya da 'hepsi'. Belirtilmezse y (yatay) kullanılır."
                }
            },
            "required": []
        }
    },
    {
        "name": "tasarim_donusu_durdur_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesnenin kendi ekseni etrafındaki sürekli dönüşünü "
                        "durdurur. 'dönüşü durdur', 'kendi ekseninde dönmeyi durdur' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_yorunge_baslat_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesneyi, sahnedeki en son eklenen BAŞKA nesnenin "
                        "etrafında yörüngeye sokar (canlı önizleme, bir gezegen gibi). Eksen "
                        "olarak x, y, z ya da birkaçı/hepsi belirtilebilir — birden fazla eksen "
                        "seçilirse daha karmaşık, sallanan bir yörünge yolu oluşur. Sadece bu "
                        "araçlardan biri açıkken, sahnede en az 2 nesne varken ve biri "
                        "seçiliyken anlamlıdır. 'başka nesnenin etrafında döndür', 'yörüngeye "
                        "sok', 'gezegen gibi döndür' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "eksen": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: x, y, z, bir kombinasyon ya da 'hepsi'. Belirtilmezse y kullanılır."
                }
            },
            "required": []
        }
    },
    {
        "name": "tasarim_yorunge_durdur_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesnenin yörünge (başka bir nesnenin etrafında dönme) "
                        "hareketini durdurur. 'yörüngeyi durdur', 'etrafında dönmeyi durdur' "
                        "gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_nesne_sec_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "verilen tanıma ve/veya renge uyan bir nesneyi seçer — 'son'/'ilk' "
                        "(eklenme sırasına göre), bir şekil/robot parçası adı (küp, tekerlek, "
                        "gövde, dişli, vb.) ve/veya bir renk (kırmızı olanı seç gibi) kabul "
                        "eder. Birden fazla eşleşme varsa en son eklenmiş olanı seçer. Sadece "
                        "bu araçlardan biri açıkken anlamlıdır. 'son eklenen nesneyi seç', "
                        "'tekerleği seç', 'kırmızı olanı seç', 'mavi küpü seç' gibi komutlarla "
                        "tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "tanim": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: 'son', 'ilk' ya da bir şekil/parça adı. Belirtilmezse en son eklenen nesne seçilir."
                },
                "renk": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: seçilecek nesnenin rengi (kırmızı, mavi, yeşil, sarı, turuncu, mor, pembe, siyah, beyaz, gri)."
                }
            },
            "required": []
        }
    },
    {
        "name": "tasarim_stl_kaydet_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "tasarımı tarayıcı indirmesi yerine DOĞRUDAN masaüstündeki "
                        "Çalışmalarım/STL klasörüne bir .stl dosyası olarak kaydeder (delikler "
                        "otomatik uygulanır). 'STL'i çalışmalarıma kaydet', 'tasarımı "
                        "masaüstüme kaydet', 'STL dosyasını kaydet' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "isim": {"type": "STRING", "description": "İsteğe bağlı: kaydedilecek dosyanın adı (uzantısız)."}
            },
            "required": []
        }
    },
    {
        "name": "tasarim_stl_ac_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "Çalışmalarım/STL klasöründe verilen isme uyan (ya da isim verilmezse "
                        "en son kaydedilen) bir .stl dosyasını bulup tasarım aracına yükler "
                        "(üzerinde çalışmaya devam edilebilir). 'kaydettiğim STL dosyasını aç', "
                        "'son STL'i aç', 'şu tasarımı aç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı: açılacak .stl dosyasının adı ya da adının bir kısmı."}
            },
            "required": []
        }
    },
    {
        "name": "tasarim_glb_kaydet_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "tasarımı (renk/malzeme/doku dahil) tarayıcı indirmesi yerine "
                        "DOĞRUDAN masaüstündeki Çalışmalarım/GLB klasörüne bir .glb dosyası "
                        "olarak kaydeder. GLB, STL'den farklı olarak rengi ve dokuyu da "
                        "saklar. 'ekle', 'çalışmalarıma ekle', 'GLB'yi çalışmalarıma kaydet', "
                        "'dokulu dosyayı kaydet', 'tasarımı GLB olarak kaydet' gibi "
                        "komutlarla tetiklenir. DİKKAT: 'ekle' tek başına genelde YENİ BİR "
                        "ŞEKİL eklemek (ekle_sekil_command / robot_parca_ekle_command) "
                        "anlamına gelir — bu aracı sadece kullanıcı hiçbir şekil/parça adı "
                        "söylemeden, tasarımı tamamladıktan sonra 'çalışmalarıma ekle' ya "
                        "da benzer bir bağlamla kaydetmek istediğini belirttiğinde kullan."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "isim": {"type": "STRING", "description": "İsteğe bağlı: kaydedilecek dosyanın adı (uzantısız)."}
            },
            "required": []
        }
    },
    {
        "name": "tasarim_glb_ac_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "Çalışmalarım/GLB klasöründe verilen isme uyan (ya da isim verilmezse "
                        "en son kaydedilen) bir .glb dosyasını bulup tasarım aracına yükler "
                        "(renk/malzeme/doku dahil, üzerinde çalışmaya devam edilebilir). "
                        "'kaydettiğim GLB dosyasını aç', 'son GLB'yi aç', 'dokulu tasarımı "
                        "geri aç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı: açılacak .glb dosyasının adı ya da adının bir kısmı."}
            },
            "required": []
        }
    },
    {
        "name": "tasarim_glb_indir_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "tasarımı (renk/malzeme/doku dahil) GLB dosyası olarak tarayıcıya "
                        "indirir. 'indir', 'GLB indir', 'dokulu dosyayı indir', 'tasarımı GLB "
                        "olarak indir' gibi komutlarla tetiklenir. Kullanıcı sadece 'indir' "
                        "derse ve hangi formatı istediği belirsizse: az önce STL'den "
                        "bahsedildiyse tasarim_stl_indir_command'ı, bahsedilmediyse (rengi de "
                        "koruduğu için) bu aracı tercih et."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_nesne_ortala_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an SEÇİLİ olan nesneyi sahnenin (ekranın) tam ortasına taşır — "
                        "yatay eksenlerde (X/Z) sıfırlar, yüksekliğini (Y) korur ki nesne "
                        "yerde/tabanda kalmaya devam etsin. Sadece bu araçlardan biri "
                        "açıkken ve bir nesne seçiliyken anlamlıdır. 'seçili nesneyi ekranda "
                        "ortala', 'nesneyi ortala', 'ortaya al', 'ekranın ortasına taşı' gibi "
                        "komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_kopyala_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesnenin "
                        "bir kopyasını oluşturur (kopya hafifçe kaydırılmış konumda belirir "
                        "ve otomatik olarak seçilir). Sadece bu araç açıkken ve bir nesne "
                        "seçiliyken anlamlıdır. 'nesneyi kopyala', 'bunun bir kopyasını çıkar', "
                        "'aynısından bir tane daha yap' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_kenar_yumusat_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesnenin "
                        "(küp, silindir, koni ya da piramit — küre ve simit zaten pürüzsüz "
                        "olduğundan bunlarda etkisi yoktur) kenarlarını/köşelerini yuvarlatır. "
                        "Sadece bu araç açıkken ve bir nesne seçiliyken anlamlıdır. "
                        "'kenarları yumuşat', 'köşeleri yuvarlat', 'kenarları biraz/çok yumuşat' "
                        "gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "miktar": {
                    "type": "STRING",
                    "description": "İsteğe bağlı: 'az', 'orta', 'çok', 'tam' ya da doğrudan bir sayı (0 ile ~1.9 arası). Belirtilmezse 'orta' kullanılır."
                }
            },
            "required": []
        }
    },
    {
        "name": "tasarim_birlestir_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, sahnedeki TÜM katı (delik "
                        "olmayan) nesneleri gerçek bir boolean birleşim (union) ile tek bir "
                        "parçada birleştirir. En az 2 katı nesne gerekir. "
                        "'nesneleri birleştir', 'şekilleri tek parça yap', 'hepsini birleştir' "
                        "gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_birlestirmeyi_geri_al_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesne daha "
                        "önce 'Nesneleri Birleştir' ile oluşturulmuş bir birleşimse, onu tekrar "
                        "orijinal ayrı parçalarına ayırır. Seçili nesne bir birleşim değilse "
                        "hiçbir şey yapmaz. Sadece bu araç açıkken ve bir nesne seçiliyken "
                        "anlamlıdır. 'birleştirmeyi geri al', 'birleşimi geri çöz/ayır', "
                        "'parçalarına ayır' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_nesne_sil_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "o an seçili olan nesneyi sahneden siler. "
                        "'tasarımdaki nesneyi sil', 'seçili şekli sil', 'küpü sil', 'seçiliyi sil' "
                        "gibi komutlarla tetiklenir. ÖNEMLİ: Blender AÇIK DEĞİLSE (yani sadece "
                        "3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi açıksa), bare "
                        "'küpü sil' / 'seçiliyi sil' gibi ifadeler HER ZAMAN bu aracı "
                        "tetiklemeli — blender_scene(action=delete_cube/delete_selected) aracını "
                        "SADECE Blender gerçekten açıkken kullan."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_delik_yap_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan nesneyi "
                        "'delik' olarak işaretler (başka bir katı nesneden boolean kesme "
                        "ile çıkarılacak). Sadece bu araç açıkken ve bir nesne seçiliyken "
                        "anlamlıdır. 'bunu delik yap', 'nesneyi delik yap' komutlarıyla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_kati_yap_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o an seçili olan 'delik' "
                        "nesneyi tekrar normal katı nesneye çevirir. "
                        "'bunu katı yap', 'nesneyi katı yap' komutlarıyla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_delikleri_uygula_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, işaretlenmiş tüm delik "
                        "nesnelerini üzerine bindikleri katı nesnelerden kalıcı olarak keser. "
                        "'delikleri uygula', 'delikleri kes' komutlarıyla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_stl_indir_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, tasarımı STL dosyası "
                        "olarak indirir (delikler otomatik uygulanmış olarak). "
                        "'STL indir', 'tasarımı indir', 'dosyayı kaydet' (bu araç bağlamında) "
                        "komutlarıyla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_temizle_command",
        "description": ("3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi tarayıcıda AÇIKKEN, "
                        "sahnedeki TÜM nesneleri kaldırır. "
                        "'sahneyi temizle', 'tasarım sahnesini temizle', '3B tasarımı temizle' "
                        "gibi komutlarla tetiklenir. ÖNEMLİ: Blender AÇIK DEĞİLSE (yani sadece "
                        "3B Tasarım Stüdyosu ya da Robot Tasarım Atölyesi açıksa), bare "
                        "'sahneyi temizle' ifadesi HER ZAMAN bu aracı tetiklemeli — "
                        "blender_scene(action=clear) aracını SADECE Blender gerçekten açıkken kullan. "
                        "SES TANIMA NOTU: 'sahneyi' konuşma tanımada bazen 'saniyeyi' şeklinde "
                        "duyulabilir ('saniyeyi temizle' anlamsızdır) — bu araç açıkken bunu "
                        "HER ZAMAN 'sahneyi temizle' olarak yorumla."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "tasarim_blendere_aktar_command",
        "description": ("3B Tasarım Stüdyosu tarayıcıda AÇIKKEN, o anki tasarımı (tüm "
                        "nesneleri, konum/döndürme/boyutlarını, renk ve malzemelerini, "
                        "'kendi ekseninde dön' ya da 'başka nesnenin etrafında dön' gibi "
                        "animasyonlarını) gerçek bir Blender dosyasına (.blend) aktarır: "
                        "Blender'ı (henüz açık değilse) açar, nesneleri orada yeniden "
                        "oluşturur, animasyonları gerçek Blender keyframe'lerine çevirir "
                        "ve 'Çalışmalarım/Blender' klasörüne kaydeder. İçe aktarılmış STL "
                        "modelleri bu aktarıma dahil edilmez. "
                        "'tasarımı Blender'a aktar', 'bunu blend olarak kaydet', "
                        "'tasarımı gerçek Blender dosyasına çevir' gibi komutlarla tetiklenir. "
                        "Sırf Blender'da bir şey kaydetmek isteniyorsa (3B Tasarım Stüdyosu "
                        "bağlamı yoksa) bu aracı DEĞİL, mevcut 'blender_save' aracını kullan."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "isim": {"type": "STRING", "description": "İsteğe bağlı: kaydedilecek dosyanın adı (uzantısız)."}
            },
            "required": []
        }
    },
    {
        "name": "tasarim_blend_ac_command",
        "description": ("Çalışmalarım/Blender klasöründeki, isme uyan (ya da isim "
                        "verilmezse en son kaydedilen) bir .blend dosyasını bulup "
                        "Blender'da canlı komut köprüsüyle açar. Bu, 3B Tasarım "
                        "Stüdyosu'nun ürettiği ya da başka bir Blender projesinin "
                        "kaydedilmiş .blend dosyasını açmak içindir. "
                        "'şu blend dosyasını aç', 'geçen tasarımı Blender'da aç', "
                        "'son kaydettiğim Blender dosyasını aç' gibi komutlarla tetiklenir."),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı: açılacak .blend dosyasının adı ya da adının bir kısmı."}
            },
            "required": []
        }
    },
    {
        "name": "obs_kayit_baslat_command",
        "description": ("OBS Studio'da ekran kaydını uzaktan başlatır (obs-websocket "
                        "protokolüyle). OBS'in açık ve obs-websocket sunucusunun etkin "
                        "olması gerekir (varsayılan olarak etkindir). "
                        "'ekran kaydı başlat' / 'kayıt başlat' bu aracı çalıştırır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "obs_kayit_duraklat_command",
        "description": ("OBS Studio'da devam eden ekran kaydını duraklatır. "
                        "'kaydı duraklat' / 'ekran kaydını duraklat' bu aracı çalıştırır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "obs_kayit_devam_command",
        "description": ("OBS Studio'da duraklatılmış ekran kaydını kaldığı yerden "
                        "sürdürür. 'kaydı devam ettir' / 'kayda devam et' bu aracı "
                        "çalıştırır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "obs_kayit_bitir_command",
        "description": ("OBS Studio'da ekran kaydını tamamen durdurur ve dosyayı "
                        "kaydeder. 'ekran kaydını bitir' / 'kaydı sonlandır' / "
                        "'kaydı durdur' bu aracı çalıştırır."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "egitim_baslat_command",
        "description": ("YERİNDE'nin kendi 'model-egitimi' klasöründeki, daha önce "
                        "kurulmuş (sanal ortam hazır) eğitim ortamında, güncel eğitim "
                        "verisiyle LoRA ince ayarını ve (llama.cpp varsa) GGUF "
                        "dönüşümünü YENİ bir terminal penceresinde başlatır. 'eğitimi "
                        "başlat', 'modelimi eğit', 'ggufa dönüştür', 'eğitimi ggufa "
                        "çevir' gibi komutlarla tetiklenir. NOT: sanal ortam henüz "
                        "kurulmadıysa (ilk kullanım), önce kurulum dosyasını "
                        "çalıştırman gerektiğini söyler, hiçbir şey başlatmaz."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "egitim_verisi_command",
        "description": ("YERİNDE kullandıkça arka planda biriken etkileşim verisini "
                        "(HabitLearner) yönetir — bu veri, kullanıcının KENDİ çevrimdışı "
                        "modelini eğitmek (fine-tuning / LoRA-QLoRA, sonra GGUF'a çevirme) "
                        "için tasarlanmıştır. 'eğitim verimi dışa aktar'→export (YERİNDE'nin "
                        "kendi kurulum klasöründeki 'model-egitimi' klasörüne, eğitim "
                        "scriptiyle AYNI yere, bir JSONL dosyası üretir — Alpaca/ShareGPT "
                        "tarzı ince ayar araçlarıyla doğrudan kullanılabilir), 'ne kadar "
                        "eğitim verisi birikti'/'eğitim verisi durumu'→stats (kaç örnek var, "
                        "hangi rotalarda), 'eğitim verisini içe aktar'/'yedekten eğitim "
                        "verisi al'→import (model-egitimi klasöründe verilen isme uyan — ya "
                        "da isim verilmezse en son değiştirilen — bir .jsonl dosyasını bulup "
                        "mevcut veriyle birleştirir; tekrar eden örnekler atlanır)."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "export | stats | import"},
            "dosya_adi": {"type": "STRING", "description": "İsteğe bağlı (sadece import için): içe aktarılacak .jsonl dosyasının adı ya da adının bir kısmı. Verilmezse model-egitimi klasöründeki en son değiştirilen .jsonl dosyası kullanılır."}},
            "required": ["action"]}
    },
    {
        "name": "blockly_command",
        "description": ("Blockly Games'i (Labirent, Kuş, Gölet, Kaplumbağa, Bulmaca, "
                        "Film, Müzik — Google'ın Türkçe kodlama bulmacaları, TARAYICIDA "
                        "çalışan bir web sitesi, Scratch gibi masaüstü uygulaması DEĞİL) "
                        "sesle açar. 'labirent aç'→key='labirent' (maze.html'i tarayıcıda "
                        "açar), 'blockly games aç'→key='' (oyun merkezinin ana sayfasını "
                        "açar). Bloklar fare ile sürüklenerek yapılır — bu araç SADECE "
                        "doğru oyunu/sayfayı AÇAR, blok yazmaz/çalıştırmaz."),
        "parameters": {"type": "OBJECT", "properties": {
            "key": {"type": "STRING", "description": "oyun adı: labirent | kuş | gölet | kaplumbağa | bulmaca | film | müzik | (boş = ana sayfa)"}},
            "required": []}
    },
    {
        "name": "blockly_games_kapat_command",
        "description": ("Blockly Games (labirent, kuş, gölet, kaplumbağa, bulmaca, film, "
                        "müzik ya da ana sayfa) tarayıcıda AÇIKKEN, o sekmeyi kapatmayı "
                        "dener. 'blockly games'i kapat', 'labirent oyununu kapat', 'aracı "
                        "kapat' gibi komutlarla tetiklenir."),
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "blockly_solve",
        "description": ("Blockly Games Labirent bulmacasının BELİRLİ bir seviyesini GERÇEK "
                        "Blockly bloklarına çevirip tarayıcıda ÇÖZER — kaydedilmiş, "
                        "önceden doğrulanmış çözümleri kullanır (1-10 arası seviyeler). "
                        "'labirentin 3. seviyesini çöz'→level=3. Tarayıcı otomasyonu "
                        "(Selenium) kullanır — Chrome kurulu olmalı. Sadece Labirent "
                        "için çalışır, diğer oyunlar (Kuş, Kaplumbağa vb.) için henüz yok."),
        "parameters": {"type": "OBJECT", "properties": {
            "level": {"type": "STRING", "description": "seviye numarası (1-10)"},
            "alt": {"type": "STRING", "description": "10. seviye için alternatif çözümü kullan: '1' ya da boş"}},
            "required": ["level"]}
    },
    {
        "name": "blockly_describe",
        "description": ("Labirent bulmacasının BELİRLİ bir seviyesinin çözümünü DOĞAL "
                        "TÜRKÇE olarak anlatır ('ileri git, sonra sola dön...') — tarayıcı "
                        "otomasyonu KULLANMAZ, %100 güvenilirdir (blockly_solve'un aksine). "
                        "ÖNERİLEN yöntem budur: öğrenci çözümü dinler/okur, blokları KENDİSİ "
                        "sürükler, oyunun kendi doğrulaması çalışır. "
                        "'labirentin 3. seviyesinin çözümünü söyle'→level=3."),
        "parameters": {"type": "OBJECT", "properties": {
            "level": {"type": "STRING", "description": "seviye numarası (1-10)"},
            "alt": {"type": "STRING", "description": "10. seviye için alternatif çözümü kullan: '1' ya da boş"}},
            "required": ["level"]}
    },
    {
        "name": "piper_dataset",
        "description": ("Piper ses klonlama için EĞİTİM SETİ hazırlar (XTTS'in aksine gerçek "
                        "veri kümesi ister). 'eğitim için ses kaydet'→record, 'eğitim setinin "
                        "durumunu söyle'→status, 'eğitim setini paketle'→package, "
                        "'N. cümleyi tekrar kaydet'→redo, 'eğitim setini sıfırla'→reset."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "record | status | package | redo | reset"},
            "index": {"type": "NUMBER", "description": "redo için cümle numarası (1'den başlar)"}},
            "required": ["action"]}
    },
    {
        "name": "mic_test",
        "description": ("Mikrofonu test eder: 3 saniye kaydeder, hangi aygıtı kullandığını, "
                        "ses seviyesini ve ne duyduğunu söyler. 'mikrofonu test et', "
                        "'beni duyuyor musun' dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "seconds": {"type": "NUMBER", "description": "kayıt süresi (varsayılan 3)"}},
            "required": []}
    },
    {
        "name": "toggle_detection",
        "description": ("Kameradaki NESNE ALGILAMAYI (YOLO) açar/kapatır. "
                        "'nesne algılamayı aç/kapat', 'yolo aç/kapat', "
                        "'nesneleri tanıma' dendiğinde kullan. Kamera açık kalır."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "start | stop"}},
            "required": ["action"]}
    },
    {
        "name": "slideshow",
        "description": ("Sunum gösterisini yönetir: 'sunumu başlat'/'tam ekran yap'→start, "
                        "'sonraki slayt'→next, 'önceki slayt'→prev, 'başa dön'→first, "
                        "'ekranı karart'→black, 'sunumu bitir'→end."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "start | next | prev | first | black | end"}},
            "required": ["action"]}
    },
    {
        "name": "slide_edit",
        "description": ("Slayt siler ya da son işlemi geri alır. 'bu slaydı sil'→delete, "
                        "'geri al' / 'sildiğimi geri getir'→undo."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "delete | undo"}},
            "required": ["action"]}
    },
    {
        "name": "add_transition",
        "description": ("Slaytlara GEÇİŞ efekti ekler. 'geçiş ekle'→rastgele; isim verilebilir: "
                        "solma, itme, kaydırma, bölme, açılma, şerit, dama, büyütme, çevirme, küp, kapı."),
        "parameters": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING", "description": "efekt adı (varsayılan rastgele)"},
            "all_slides": {"type": "BOOLEAN", "description": "tüm slaytlara mı (varsayılan true)"}},
            "required": []}
    },
    {
        "name": "add_animation",
        "description": ("Slayttaki öğelere giriş ANİMASYONU ekler: belirme, solarak, uçarak, "
                        "büyüyerek, dönerek, zıplayarak, rastgele."),
        "parameters": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING", "description": "animasyon adı (varsayılan solarak)"},
            "all_slides": {"type": "BOOLEAN", "description": "tüm slaytlara mı (varsayılan true)"}},
            "required": []}
    },
    {
        "name": "clear_effects",
        "description": ("Eklenen animasyon ve/veya geçişleri TEMİZLER. 'animasyonları temizle'→animations, "
                        "'geçişleri temizle'→transitions, 'efektleri temizle'→all."),
        "parameters": {"type": "OBJECT", "properties": {
            "what": {"type": "STRING", "description": "animations | transitions | all"}},
            "required": []}
    },
    {
        "name": "write_topic",
        "description": ("Bir KONUYU araştırıp açık sunuma slaytlar ya da Word belgesine bölümler "
                        "olarak YAZAR. Çevrimiçiyse Vikipedi'den, değilse yerel modelden içerik "
                        "üretir. 'sunuma yapay zeka konusunu ekle', 'word'e donanım bileşenlerini yaz' "
                        "dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "topic": {"type": "STRING", "description": "konu (örn. 'yapay zeka', 'donanım bileşenleri')"},
            "target": {"type": "STRING", "description": "auto | powerpoint | word"}},
            "required": ["topic"]}
    },
    {
        "name": "image_adjust",
        "description": ("Sunumdaki/belgedeki resmi ayarlar: döndürme, aynalama, "
                        "büyütme/küçültme, hizalama. 'resmi döndür'→rotate_right, "
                        "'resmi sola döndür'→rotate_left, 'resmi büyüt'→bigger, "
                        "'resmi ortala'→center, 'resmi aynala'→flip_h."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "rotate_right | rotate_left | reset | flip_h | flip_v | bigger | smaller | center | left | right | top | bottom"},
            "value": {"type": "STRING", "description": "döndürme derecesi (opsiyonel, varsayılan 90)"}},
            "required": ["action"]}
    },
    {
        "name": "word_export_pdf",
        "description": ("Açık Word belgesini VEYA PowerPoint sunumunu PDF olarak "
                        "'Çalışmalarım' klasörüne kaydeder."),
        "parameters": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING", "description": "dosya adı (opsiyonel)"}},
            "required": []}
    },
    {
        "name": "excel_command",
        "description": ("Excel: toplama ('topla'→sum), ortalama (average), PUAN TABLOSU "
                        "(score_table), seçili tablodan GRAFİK ('grafik oluştur'→chart; "
                        "value ile tür: sütun/çizgi/pasta), HÜCRE ARALIĞI SEÇME "
                        "('A1'den D10'a kadar seç'→select_range, value='A1:D10')."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "sum | average | score_table | chart | select_range"},
            "value": {"type": "STRING", "description": "opsiyonel"}},
            "required": ["action"]}
    },
    {
        "name": "press_key",
        "description": ("Klavye tuşuna basar. 'escape/esc', 'enter', 'sil/delete', "
                        "'geri sil/backspace', 'tab', 'alt tab' (pencere değiştir), 'alt f4' (pencereyi kapat), "
                        "'windows tab', 'ctrl tab' / 'kontrol tab' (SEKMELER ARASI İLERİ geçiş — "
                        "tarayıcı/uygulama sekmesi değiştir), 'ctrl shift tab' (sekmeler arası GERİ geçiş), "
                        "ok tuşları (yukarı/aşağı/sol/sağ), 'boşluk', "
                        "'kopyala/kes/yapıştır/geri al/ileri al/tümünü seç', "
                        "'masaüstünü göster' (win+d), 'başlat'a tıkla' / 'başlat menüsünü aç' / "
                        "'windows tuşuna bas' (win — Başlat menüsünü açar), 'F11' (tam ekran aç/çık), "
                        "'yeniden adlandır' (F2), 'büyük yap' (caps lock) için kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "key": {"type": "STRING", "description": "esc | enter | delete | backspace | tab | alt_tab | alt_f4 | win_tab | ctrl_tab | ctrl_shift_tab | win_d | win (Başlat menüsü) | f11 | f2 | up | down | left | right | space | home | end | pageup | pagedown | copy | cut | paste | undo | redo | select_all | capslock | parent_folder"},
            "times": {"type": "NUMBER", "description": "kaç kez basılacak (varsayılan 1)"}},
            "required": ["key"]}
    },
    {
        "name": "save_blender_project",
        "description": ("Açık Blender sahnesini 'Çalışmalarım/Blender' klasörüne .blend "
                        "olarak kaydeder. 'blender tasarımını kaydet' dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING", "description": "dosya adı (opsiyonel)"}},
            "required": []}
    },
    {
        "name": "blender_scene",
        "description": ("Blender tarayıcıda/uygulamada AÇIKKEN, sahne silme/temizleme: "
                        "'sahneyi temizle'→clear, 'küpü sil'→delete_cube, "
                        "'seçiliyi sil'→delete_selected, 'hepsini seç'→select_all. Yeni nesne "
                        "ÇİZMEK için blender_exec kullan. ÖNEMLİ: bu aracı SADECE Blender "
                        "gerçekten açıkken kullan — 3B Tasarım Stüdyosu ya da Robot Tasarım "
                        "Atölyesi açıksa (Blender değil), aynı ifadeler ('sahneyi temizle', "
                        "'küpü sil', 'seçiliyi sil') için KENDİ karşılıklarını "
                        "(tasarim_temizle_command / tasarim_nesne_sil_command) kullan. "
                        "SES TANIMA NOTU: 'sahneyi' bazen 'saniyeyi' şeklinde duyulabilir "
                        "('saniyeyi temizle' anlamsızdır) — Blender açıkken bunu HER ZAMAN "
                        "'sahneyi temizle' (clear) olarak yorumla."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "clear | delete_cube | delete_selected | select_all"}},
            "required": ["action"]}
    },
    {
        "name": "blender_exec",
        "description": (
            "Verilen bpy (Blender Python) kodunu AÇIK Blender'ın içinde canlı çalıştırır "
            "— nesne anında sahnede belirir. Kullanıcı 'masa çiz', 'küp oluştur', "
            "'sandalye modelle' dediğinde bpy kodunu SEN yaz ve bu araca ver. "
            "Blender kapalıysa otomatik köprüyle açılır."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "code": {"type": "STRING", "description": "Çalıştırılacak tam bpy kodu"}},
            "required": ["code"]}
    },
    {
        "name": "save_freecad_project",
        "description": ("Açık FreeCAD belgesini 'Çalışmalarım/FreeCAD' klasörüne .FCStd "
                        "olarak kaydeder. 'FreeCAD tasarımını kaydet' dendiğinde kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING", "description": "dosya adı (opsiyonel)"}},
            "required": []}
    },
    {
        "name": "freecad_scene",
        "description": ("FreeCAD'de belge yönetimi: 'yeni tasarıma başla'/'temizle'→clear "
                        "(yeni boş belge açar), 'seçiliyi sil'→delete_selected, "
                        "'hepsini seç'→select_all. Yeni nesne ÇİZMEK için freecad_exec kullan."),
        "parameters": {"type": "OBJECT", "properties": {
            "action": {"type": "STRING", "description": "clear | delete_selected | select_all"}},
            "required": ["action"]}
    },
    {
        "name": "freecad_exec",
        "description": (
            "Verilen FreeCAD Python kodunu (App/FreeCAD, Gui/FreeCADGui, Part, "
            "Sketcher, Draft, PartDesign modülleri hazır) AÇIK FreeCAD'in içinde "
            "canlı çalıştırır — nesne anında sahnede belirir. Kullanıcı 'masa çiz', "
            "'dişli modelle', 'kutu oluştur', 'mil tasarla' gibi 3D CAD/mekanik "
            "parça tasarımı istediğinde ilgili FreeCAD Python kodunu SEN yaz ve bu "
            "araca ver (örn. Part.makeBox, Part.makeCylinder ile parametrik "
            "geometri). FreeCAD kapalıysa otomatik köprüyle açılır. Belge yoksa "
            "önce App.newDocument(...) ile bir tane oluştur."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "code": {"type": "STRING", "description": "Çalıştırılacak tam FreeCAD Python kodu"}},
            "required": ["code"]}
    },
    {
        "name": "shutdown_assistant",
        "description": "YERINDE'yi tamamen kapatır. 'kendini kapat', 'yerinde kapan', 'programı kapat' dendiğinde kullan.",
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    }
]


def _gemini_type_to_json_schema(t: str) -> str:
    return {
        "OBJECT": "object",
        "STRING": "string",
        "NUMBER": "number",
        "BOOLEAN": "boolean",
        "ARRAY": "array",
    }.get(str(t).upper(), "string")


def _convert_params(params: dict) -> dict:
    props = {}
    for key, spec in (params.get("properties") or {}).items():
        props[key] = {
            "type": _gemini_type_to_json_schema(spec.get("type", "STRING")),
            "description": spec.get("description", ""),
        }
    return {
        "type": "object",
        "properties": props,
        "required": params.get("required", []),
    }


# ─────────────────────────────────────────────────────────────────────────
# Çevrimdışı (Ollama) modda LLM'e sunulan araç alt kümesi.
#
# NEDEN: TOOL_DECLARATIONS'ın tamamı ~165 araç ve tek başına ~30.000 token
# tutuyor — varsayılan num_ctx (8192) değerinin bile 3,5 katı. Bu devasa
# şema HER TEK Ollama isteğinde (basit bir "saat kaç" sorusunda bile)
# modele gönderiliyordu; küçük modellerde (1.5B gibi) bu, her turda saniyeler
# süren gereksiz prompt-işleme gecikmesine ve context taşmasına yol açıyordu.
#
# Bu araçların büyük çoğunluğu (tasarim_*, pico_*, kukla_*, bilisim_*,
# video_atolyesi_*, resim_pdf_*, blockly_*, obs_kayit_*, vb. workshop'a özgü
# ~140 komut) zaten core/intent_parser.py içinde desen eşleştirmeyle
# YAKALANIYOR ve ollama_assistant._handle_turn() bunları LLM'e hiç
# göndermeden doğrudan çalıştırıyor. Yani LLM zaten bu araçları pratikte
# kullanmıyordu — sadece prompt'u şişiriyorlardı.
#
# Aşağıdaki küme, intent_parser'ın YAKALAMADIĞI genel/serbest-konuşma
# senaryolarında modelin gerçekten ihtiyaç duyabileceği araçlarla sınırlı.
# Belirli bir workshop açma komutunun bazı söyleniş biçimlerde
# intent_parser tarafından yakalanmadığını fark edersen, ilgili
# '..._command' adını buraya ekleyebilirsin — ama her araç eklemek prompt
# boyutunu tekrar büyütür, bu yüzden ölçülü ekle.
OLLAMA_CORE_TOOL_NAMES = {
    "open_app", "close_app", "sys_info", "get_weather", "get_forecast",
    "get_calendar_events", "add_calendar_event", "delete_calendar_event",
    "get_reminders", "add_reminder", "browser_control", "shell_run",
    "toggle_webcam", "play_media", "save_memory", "delete_memory",
    "toggle_garden_cam", "wake_garden_cam", "garden_ptz",
    "garden_ptz_start", "garden_ptz_stop", "garden_horn",
    "garden_talk",
    "send_whatsapp_message", "save_whatsapp_contact", "take_photo",
    "record_video", "type_text", "system_volume", "media_control",
    "mouse_control", "whatsapp_call", "calibrate_whatsapp",
    "play_stream", "press_key", "shutdown_assistant", "arkaplan_command",
    "tema_command", "zumre_tutanagi_olustur", "referans_belge_kaydet", "sinav_olustur", "gunluk_plan_olustur",
    "kulup_calisma_plani_olustur", "yillik_plan_guncelle", "olcek_hazirla",
}


def get_ollama_tools(include_all: bool = False) -> list[dict]:
    """
    TOOL_DECLARATIONS'i (Gemini formati) Ollama'nin /api/chat 'tools'
    parametresinin bekledigi OpenAI-uyumlu JSON semasina cevirir.
    Cevrimdisi (Ollama) mod bu fonksiyonu kullanir.

    Varsayılan olarak sadece OLLAMA_CORE_TOOL_NAMES kümesindeki genel amaçlı
    araçlar gönderilir (bkz. yukarıdaki açıklama). Tüm araçları (ör. hata
    ayıklama amaçlı) almak istersen include_all=True ver.
    """
    tools = []
    for decl in TOOL_DECLARATIONS:
        if not include_all and decl["name"] not in OLLAMA_CORE_TOOL_NAMES:
            continue
        tools.append({
            "type": "function",
            "function": {
                "name": decl["name"],
                "description": decl.get("description", ""),
                "parameters": _convert_params(decl.get("parameters", {}) or {}),
            },
        })
    return tools
