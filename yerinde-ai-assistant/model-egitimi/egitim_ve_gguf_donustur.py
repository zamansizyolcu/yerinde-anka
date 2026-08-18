#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egitim_ve_gguf_donustur.py — YERİNDE'nin biriktirdiği eğitim verisiyle
(memory/egitim_verisi.jsonl) küçük bir temel dil modelini LoRA ile ince
ayarlar (fine-tune), ağırlıkları birleştirir (merge) ve isteğe bağlı olarak
llama.cpp ile GGUF dosyasına çevirir.

BU SCRIPT YERİNDE'NİN İÇİNDEN OTOMATİK ÇALIŞTIRILMAZ — kendi bilgisayarında,
bir terminalden SEN çalıştırırsın. Sebep: gerçek bir model eğitmek internetten
model indirmeyi (birkaç yüz MB - birkaç GB), gerçek işlemci/ekran kartı
zamanını (dakikalar - saatler) ve YERİNDE'nin şu anki hafif/çevrimdışı-asistan
mimarisinin dışında kalan ağır Python kütüphanelerini (torch, transformers,
peft) gerektirir. YERİNDE bunu arka planda sessizce yapmaya kalkarsa
bilgisayarını uzun süre kilitleyebilir — bu yüzden bilinçli olarak SENİN
kontrolünde, ayrı bir terminal penceresinde çalışacak şekilde tasarlandı.

────────────────────────────────────────────────────────────────────────
KULLANIM (adım adım):
────────────────────────────────────────────────────────────────────────
1) Gerekli kütüphaneleri kur (bir kere, aynı klasördeki requirements-egitim.txt
   ile):
       pip install -r requirements-egitim.txt

   NOT (Windows): Eğer ekran kartın (NVIDIA) varsa, kurulumdan ÖNCE
   https://pytorch.org/get-started/locally/ adresinden kendi CUDA
   sürümüne uygun torch komutunu çalıştır — yoksa CPU'da (çok daha yavaş)
   çalışır (küçük bir veri kümesi için yine de birkaç dakika sürebilir).

2) (İsteğe bağlı ama GGUF için ZORUNLU) llama.cpp'yi klonla:
       git clone https://github.com/ggerganov/llama.cpp.git
       pip install -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt

3) Scripti çalıştır (en basit hâli - varsayılan küçük çok dilli model ile):
       python egitim_ve_gguf_donustur.py --llama-cpp-path ./llama.cpp

   Varsayılan olarak şunları yapar:
     - memory/egitim_verisi.jsonl dosyasını okur (YERİNDE Ayarlar > Eğitim
       Verisi > "Dışa Aktar" ile üretilmiş olmalı; yoksa önce onu çalıştır)
     - Qwen/Qwen2.5-1.5B-Instruct temel modelini (ilk seferde ~3 GB, internet
       gerekir) LoRA ile ince ayarlar
     - İnce ayarlı ağırlıkları birleştirir (merge)
     - llama.cpp ile GGUF dosyasına çevirir (--llama-cpp-path verildiyse)

4) Üretilen .gguf dosyasını Ollama'ya tanıtmak için, çıktı klasöründeki
   Modelfile'ı kullan:
       ollama create benim-modelim -f Modelfile
       ollama run benim-modelim

────────────────────────────────────────────────────────────────────────
DÜRÜST BEKLENTİ YÖNETİMİ:
────────────────────────────────────────────────────────────────────────
  • Birkaç düzine örnekle eğitilen bir LoRA, modelin "kişiliğini" tamamen
    değiştirmez — küçük, gözle görülür ama SINIRLI bir etki bekle. Daha
    belirgin bir fark için YERİNDE'yi kullanmaya devam edip verinin (ideal
    olarak birkaç yüz - birkaç bin örnek) birikmesini beklemek en iyisi.
  • Bu script HER ZAMAN başarılı GGUF üretimini garanti etmez — temel model
    değişirse, llama.cpp güncellenmezse ya da format uyumsuzluğu olursa
    hata verebilir; hata mesajını okuyup (gerekirse YERİNDE'ye/Claude'a
    göstererek) birlikte çözebiliriz.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _err_exit(msg: str) -> None:
    print(f"\n❌ {msg}\n", file=sys.stderr)
    sys.exit(1)


def check_dependencies() -> None:
    eksik = []
    for mod in ("torch", "transformers", "peft", "datasets"):
        try:
            __import__(mod)
        except ImportError:
            eksik.append(mod)
    if eksik:
        _err_exit(
            "Şu kütüphaneler eksik: " + ", ".join(eksik) + "\n"
            "Kurmak için (bu klasörde):\n"
            "    pip install -r requirements-egitim.txt"
        )


def load_jsonl_examples(path: Path, min_len: int = 3) -> list[dict]:
    if not path.exists():
        _err_exit(
            f"Eğitim verisi bulunamadı: {path}\n"
            "Önce YERİNDE'de Ayarlar > 🎓 Eğitim Verisi > "
            "'📤 JSONL Olarak Dışa Aktar' düğmesine bas, sonra bu scripti "
            "tekrar çalıştır (ya da --jsonl ile başka bir dosya yolu ver)."
        )
    examples = []
    bozuk = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                bozuk += 1
                continue
            instr = (rec.get("instruction") or "").strip()
            out = (rec.get("output") or "").strip()
            if len(instr) < min_len or not out:
                continue
            examples.append({"instruction": instr, "output": out})
    if bozuk:
        print(f"⚠️  {bozuk} bozuk satır atlandı.")
    if not examples:
        _err_exit(f"{path} içinde kullanılabilir hiç örnek bulunamadı.")
    if len(examples) < 20:
        print(f"⚠️  Sadece {len(examples)} örnek var — bu, gerçek bir davranış "
              "değişikliği için genelde YETERSİZ. Yine de devam edilecek, ama "
              "sonuçların çok belirgin olmasını bekleme. YERİNDE'yi kullanmaya "
              "devam edip veri biriktirmen önerilir.")
    else:
        print(f"✅ {len(examples)} eğitim örneği yüklendi.")
    return examples


def format_example(tokenizer, instr: str, out: str) -> str:
    """Temel modelin KENDİ sohbet şablonu varsa onu kullanır (en doğru
    sonucu verir); yoksa basit bir Alpaca tarzı talimat şablonuna düşer."""
    try:
        messages = [
            {"role": "user", "content": instr},
            {"role": "assistant", "content": out},
        ]
        return tokenizer.apply_chat_template(messages, tokenize=False)
    except Exception:
        return f"### Talimat:\n{instr}\n\n### Yanıt:\n{out}"


def train_and_merge(args) -> Path:
    import torch
    from datasets import Dataset
    from transformers import (AutoModelForCausalLM, AutoTokenizer,
                              DataCollatorForLanguageModeling, Trainer,
                              TrainingArguments)
    from peft import LoraConfig, TaskType, get_peft_model

    examples = load_jsonl_examples(Path(args.jsonl), min_len=args.min_len)

    print(f"\n📦 Temel model indiriliyor/yükleniyor: {args.base_model}")
    print("   (ilk çalıştırmada birkaç dakika sürebilir, internet gerekir)")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        print("⚠️  Ekran kartı (CUDA) bulunamadı — CPU üzerinde eğitilecek, "
              "bu ÖNEMLİ ÖLÇÜDE daha yavaş olur.")
    dtype = torch.float16 if device == "cuda" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(args.base_model, dtype=dtype)
    model.to(device)

    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_r, lora_alpha=args.lora_r * 2, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    texts = [format_example(tokenizer, e["instruction"], e["output"]) for e in examples]

    def tokenize_fn(batch):
        enc = tokenizer(batch["text"], truncation=True, max_length=args.max_length,
                        padding="max_length")
        enc["labels"] = enc["input_ids"].copy()
        return enc

    ds = Dataset.from_dict({"text": texts}).map(tokenize_fn, batched=True,
                                                 remove_columns=["text"])

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter_dir = out_dir / "lora_adapter"
    merged_dir = out_dir / "merged_model"

    training_args = TrainingArguments(
        output_dir=str(out_dir / "egitim_gecici"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=max(1, 8 // args.batch_size),
        learning_rate=args.learning_rate,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        fp16=(device == "cuda"),
    )
    trainer = Trainer(
        model=model, args=training_args, train_dataset=ds,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )

    print(f"\n🚀 Eğitim başlıyor ({args.epochs} epoch, {len(examples)} örnek)...\n")
    trainer.train()

    print(f"\n💾 LoRA adaptörü kaydediliyor: {adapter_dir}")
    model.save_pretrained(adapter_dir)

    print(f"🔗 Ağırlıklar birleştiriliyor (merge) ve kaydediliyor: {merged_dir}")
    merged = model.merge_and_unload()
    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)

    return merged_dir


def convert_to_gguf(merged_dir: Path, llama_cpp_path: Path, out_dir: Path,
                    outtype: str, quantize: str | None) -> Path | None:
    convert_script = llama_cpp_path / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        print(f"⚠️  {convert_script} bulunamadı — GGUF dönüşümü atlanıyor. "
              "llama.cpp klasörünün doğru yolunu --llama-cpp-path ile verdiğinden emin ol.")
        return None

    gguf_path = out_dir / "model-f16.gguf"
    print(f"\n🔄 GGUF'a çevriliyor (llama.cpp/convert_hf_to_gguf.py)...")
    result = subprocess.run(
        [sys.executable, str(convert_script), str(merged_dir),
         "--outfile", str(gguf_path), "--outtype", outtype],
        capture_output=True, text=True,
    )
    print(result.stdout[-3000:])
    if result.returncode != 0:
        print(result.stderr[-3000:], file=sys.stderr)
        print("\n⚠️  GGUF dönüşümü başarısız oldu (yukarıdaki hataya bak). "
              "Bu hatayı YERİNDE/Claude'a gösterirsen birlikte çözebiliriz.")
        return None
    print(f"✅ GGUF üretildi: {gguf_path}")

    final_path = gguf_path
    if quantize:
        quant_bin = llama_cpp_path / "build" / "bin" / "llama-quantize"
        if not quant_bin.exists():
            print(f"⚠️  Niceleme (quantize) aracı bulunamadı ({quant_bin}) — "
                  "llama.cpp'yi 'cmake -B build && cmake --build build --config Release' "
                  "ile derlemen gerekiyor. Şimdilik f16 GGUF kullanılabilir "
                  "(daha büyük dosya, ama çalışır).")
        else:
            quant_path = out_dir / f"model-{quantize}.gguf"
            qresult = subprocess.run(
                [str(quant_bin), str(gguf_path), str(quant_path), quantize],
                capture_output=True, text=True,
            )
            print(qresult.stdout[-1500:])
            if qresult.returncode == 0:
                print(f"✅ Nicelenmiş GGUF üretildi: {quant_path}")
                final_path = quant_path
            else:
                print(qresult.stderr[-1500:], file=sys.stderr)
                print("⚠️  Niceleme başarısız oldu, f16 GGUF kullanılabilir.")
    return final_path


def write_modelfile(out_dir: Path, gguf_path: Path, base_model: str) -> None:
    modelfile = out_dir / "Modelfile"
    modelfile.write_text(
        f'FROM {gguf_path.name}\n\n'
        f'# YERİNDE eğitim verisiyle ince ayarlanmış, {base_model} tabanlı model.\n'
        f'PARAMETER temperature 0.7\n'
        f'PARAMETER num_ctx 4096\n',
        encoding="utf-8",
    )
    print(f"\n📄 Modelfile hazırlandı: {modelfile}")
    print("   Ollama'ya tanıtmak için (bu klasörde):")
    print(f"       ollama create benim-modelim -f Modelfile")
    print(f"       ollama run benim-modelim")


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jsonl", default="egitim_verisi.jsonl",
                   help="YERİNDE'den dışa aktarılan eğitim verisi (.jsonl) — "
                        "varsayılan olarak scriptle AYNI klasörde arar")
    p.add_argument("--base-model", default="Qwen/Qwen2.5-1.5B-Instruct",
                   help="HuggingFace temel model adı (küçük, çok dilli, Türkçe destekli)")
    p.add_argument("--output-dir", default="./cikti",
                   help="Eğitilmiş model ve GGUF dosyalarının yazılacağı klasör")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=2)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--min-len", type=int, default=3)
    p.add_argument("--llama-cpp-path", default=None,
                   help="GGUF'a çevirmek için klonlanmış llama.cpp klasörünün yolu")
    p.add_argument("--outtype", default="f16", choices=["f16", "f32", "bf16"])
    p.add_argument("--quantize", default=None,
                   help="İsteğe bağlı niceleme türü, ör. Q4_K_M, Q8_0 (llama.cpp derlenmiş olmalı)")
    p.add_argument("--skip-training", action="store_true",
                   help="Eğitimi atla, --output-dir/merged_model klasöründeki "
                        "HAZIR bir modeli doğrudan GGUF'a çevir")
    args = p.parse_args()

    check_dependencies()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.skip_training:
        merged_dir = out_dir / "merged_model"
        if not merged_dir.exists():
            _err_exit(f"--skip-training verildi ama {merged_dir} bulunamadı.")
    else:
        merged_dir = train_and_merge(args)

    if args.llama_cpp_path:
        gguf_path = convert_to_gguf(merged_dir, Path(args.llama_cpp_path), out_dir,
                                    args.outtype, args.quantize)
        if gguf_path:
            write_modelfile(out_dir, gguf_path, args.base_model)
    else:
        print("\nℹ️  --llama-cpp-path verilmedi, GGUF dönüşümü atlandı. "
              f"İnce ayarlı model burada: {merged_dir}")

    print("\n🎉 Tamamlandı.")


if __name__ == "__main__":
    main()
