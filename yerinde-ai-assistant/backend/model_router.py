"""
backend/model_router.py — Orkestra şefi.

Akış:
  1) classify(): Gemma 2'ye KATI bir sınıflandırma promptu ile isteğin türü
     sorulur → {"route": "chat|code|vision|camera_on|camera_off"}. Model JSON
     dışına çıkarsa regex sezgileri (blender/bpy/godot/kamera...) devralır —
     yani yönlendirme hiçbir zaman "boşa düşmez".
  2) route'a göre:
     • chat      → Gemma 2 (sohbet geçmişiyle)
     • code      → Qwen 2.5-Coder → CodeBlock ayıklanır (```...``` temiz)
     • vision    → VisionEngine'den güncel kare → Qwen2-VL analizi
     • camera_*  → SystemController kamera aç/kapat (YOLO11 canlı takip)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .config import Settings
from .ollama_client import OllamaClient

_CLASSIFIER_SYSTEM = (
    "Sen bir istek sınıflandırıcısısın. Kullanıcının Türkçe isteğini oku ve "
    "SADECE şu JSON'u döndür, başka hiçbir şey yazma:\n"
    '{"route": "<chat|code|vision|camera_on|camera_off>"}\n'
    "Kurallar:\n"
    "- Python, Blender (bpy), Godot (GDScript) veya herhangi bir KOD YAZMA "
    "isteği → code\n"
    "- 'kamerayı aç/başlat' → camera_on ; 'kamerayı kapat' → camera_off\n"
    "- Kameradaki/gösterilen nesnenin NE OLDUĞUNU sorma, tarif etme isteği → vision\n"
    "- Diğer her şey (sohbet, bilgi, hava, saat...) → chat"
)

_CODE_SYSTEM = (
    "Sen uzman bir Python/Blender(bpy)/Godot(GDScript) geliştiricisisin. "
    "İstenen kodu ÜRET; açıklamayı kısa tut ve kodu mutlaka tek bir "
    "```dil\n...\n``` bloğu içinde ver. Kod çalıştırılmaya hazır olmalı."
)

# Sınıflandırıcı çuvallarsa devreye giren güvenlik ağı
_CODE_HINTS = re.compile(r"\b(kod|script|python|bpy|blender.*(script|kod)|gdscript|godot.*(script|kod)|fonksiyon yaz|program yaz)\b", re.I)
_CAM_ON = re.compile(r"kamera\w*\s*(aç|başlat)|(aç|başlat)\w*\s*kamera", re.I)
_CAM_OFF = re.compile(r"kamera\w*\s*(kapat|durdur)", re.I)
_VISION_HINTS = re.compile(r"\b(ne görüyorsun|bu ne|elimde(ki)? ne|nesneyi (tanı|analiz)|gösterdiğim)\b", re.I)


@dataclass
class CodeBlock:
    language: str
    code: str
    explanation: str


class ModelRouter:
    def __init__(self, settings: Settings, client: OllamaClient):
        self.s = settings
        self.client = client
        self.history: list[dict] = []       # sohbet hafızası (chat rotası)
        self.max_history = 20

    # ── 1) Sınıflandırma ────────────────────────────────────────────────────
    async def classify(self, user_text: str) -> str:
        # Önce ucuz sezgiler (LLM çağrısı bile gerektirmez, ~0 ms):
        if _CAM_OFF.search(user_text):
            return "camera_off"
        if _CAM_ON.search(user_text):
            return "camera_on"
        if _CODE_HINTS.search(user_text):
            return "code"
        if _VISION_HINTS.search(user_text):
            return "vision"

        try:
            raw = await self.client.chat(
                self.s.chat_model,
                [{"role": "system", "content": _CLASSIFIER_SYSTEM},
                 {"role": "user", "content": user_text}],
                # num_predict: sınıflandırıcı sadece kısa bir JSON döner
                # ({"route": "..."}) — üretimi ~24 token'da kesmek zayıf/
                # gömülü donanımda (ör. Orange Pi) gereksiz gevezeliği
                # önleyip yanıt süresini belirgin şekilde kısaltır.
                options={"temperature": 0, "num_predict": 24},
            )
            match = re.search(r'\{.*?\}', raw, re.S)
            route = json.loads(match.group(0))["route"] if match else "chat"
            # GÜVENLİK AĞI: küçük/zayıf modeller (ör. 3B) bazen metinde hiç
            # "kamera" geçmediği halde camera_on/camera_off seçebiliyor (ör.
            # "masaüstünü göster" gibi alakasız bir komutu kamerayla
            # karıştırma). Bu iki rota YALNIZCA metinde gerçekten kamera
            # kelimesi geçiyorsa kabul edilir; yoksa güvenli tarafta kalıp
            # sohbete düşülür.
            if route in ("camera_on", "camera_off") and not re.search(
                    r"kamera|webcam", user_text, re.I):
                return "chat"
            if route in ("chat", "code", "vision", "camera_on", "camera_off"):
                return route
        except Exception:
            pass
        return "chat"

    # ── 2a) Sohbet (Gemma 2) ────────────────────────────────────────────────
    async def chat(self, user_text: str, system_prompt: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-self.max_history:]
        messages = [{"role": "system", "content": system_prompt}] + self.history
        # NOT: classify()'de num_predict sınırlıydı ama burada HİÇ yoktu —
        # yani asıl sohbet yanıtı üretimi SINIRSIZDI. Küçük modeller (1.5B
        # gibi) bazen tekrar döngüsüne girip gereğinden uzun yanıt üretebilir;
        # zayıf donanımda bu "yanıt geldi ama çok geç geldi" hissi yaratan en
        # büyük gizli sebeplerden biri. Makul bir tavan koyuyoruz — normal bir
        # sohbet yanıtı için fazlasıyla yeterli, ama sonsuz üretimi engelliyor.
        answer = await self.client.chat(
            self.s.chat_model, messages,
            options={"num_predict": 400},
        )
        self.history.append({"role": "assistant", "content": answer})
        return answer

    # ── 2b) Kod (Qwen 2.5-Coder) ────────────────────────────────────────────
    async def generate_code(self, user_text: str) -> CodeBlock:
        raw = await self.client.chat(
            self.s.coder_model,
            [{"role": "system", "content": _CODE_SYSTEM},
             {"role": "user", "content": user_text}],
            options={"temperature": 0.2},
        )
        return self._extract_code(raw)

    @staticmethod
    def _extract_code(raw: str) -> CodeBlock:
        """```dil ... ``` bloklarını metinden TEMİZCE ayıklar; blok yoksa
        satır sezgisiyle kod/açıklama ayrımı dener."""
        m = re.search(r"```([a-zA-Z0-9_+-]*)\n(.*?)```", raw, re.S)
        if m:
            lang = (m.group(1) or "python").lower()
            code = m.group(2).strip()
            explanation = (raw[:m.start()] + raw[m.end():]).strip()
            return CodeBlock(language=lang, code=code, explanation=explanation[:400])
        # Blok yoksa: girintili/anahtar-kelimeli satırları kod say
        lines = raw.splitlines()
        code_lines = [l for l in lines if l.startswith(("import ", "from ", "def ",
                                                        "class ", "    ", "\t", "extends ", "func "))]
        if code_lines:
            return CodeBlock("python", "\n".join(code_lines).strip(), "")
        return CodeBlock("python", raw.strip(), "")

    # ── 2c) Görü (Qwen2-VL / Llama-3.2-Vision) ─────────────────────────────
    async def analyze_image(self, user_text: str, jpeg_bytes: bytes) -> str:
        prompt = user_text.strip() or "Bu görüntüde ne var? Türkçe, kısa ve net anlat."
        return await self.client.chat(
            self.s.vision_model,
            [{"role": "user", "content": prompt}],
            images_b64=[OllamaClient.encode_image(jpeg_bytes)],
        )
