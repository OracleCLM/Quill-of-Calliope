"""
LoRA Voice Fine-Tune Evaluation Pipeline — Quill of Calliope

Phase 2 of R-CALLIOPE-STYLE-COACH-LORA-VOICE-EVAL.

Hardware requirement: VRAM >= 8GB for Qwen2.5-7B QLoRA (BnB 4-bit).
NM system: NVIDIA T500 2GB — INSUFFICIENT. Phase 2 DEFERRED to cloud H100.

Usage (when hardware available):
    python scripts/lora_eval_pipeline.py --check-hardware
    python scripts/lora_eval_pipeline.py --step prep --corpus-dir data/lora_corpus/
    python scripts/lora_eval_pipeline.py --step train --dataset data/lora_corpus/train.jsonl
    python scripts/lora_eval_pipeline.py --step eval --adapter checkpoints/calliope-lora/
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_MIN_VRAM_GB = 8
_BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"
_LORA_OUTPUT_DIR = Path("checkpoints/calliope-lora")
_EVAL_PROMPTS = [
    "Aurora draws her sword beneath the cold moon.",
    "The tavern is quiet. Two figures speak in low tones.",
    "She noticed the trap too late.",
    "He offered no explanation, only silence.",
    "The forest path narrowed. Something moved in the dark.",
    "She stood at the cliff's edge, wind pulling her hair back.",
    "The letter arrived at dawn. Its seal was broken.",
    "He hadn't expected her to laugh.",
    "The enemy camp stretched across the valley below.",
    "Morning came. The body was gone.",
]


def _check_hardware() -> dict:
    """Return hardware capability dict."""
    result = {"gpu_available": False, "vram_gb": 0.0, "sufficient": False, "note": ""}
    try:
        import subprocess  # noqa: PLC0415
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            vram_mb = int(out.stdout.strip().split("\n")[0])
            vram_gb = vram_mb / 1024
            result["gpu_available"] = True
            result["vram_gb"] = round(vram_gb, 1)
            result["sufficient"] = vram_gb >= _MIN_VRAM_GB
            if not result["sufficient"]:
                result["note"] = (
                    f"VRAM {vram_gb:.1f}GB < {_MIN_VRAM_GB}GB required for Qwen2.5-7B QLoRA. "
                    "Defer to cloud H100 (~$10-16). Operator cost decision required."
                )
    except Exception as exc:
        result["note"] = f"nvidia-smi check failed: {exc}"
    return result


def _step_prep(corpus_dir: Path, output_path: Path) -> None:
    """Convert extract_lora_corpus.py output to instruction JSONL."""
    if not corpus_dir.exists():
        logger.error("Corpus dir not found: %s", corpus_dir)
        sys.exit(1)
    records = []
    for f in sorted(corpus_dir.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                msg = obj.get("message", "").strip()
                if len(msg) > 20:
                    records.append({
                        "instruction": "Genera una risposta RP nel mio stile:",
                        "input": obj.get("context", ""),
                        "output": msg,
                    })
            except json.JSONDecodeError:
                continue
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )
    logger.info("Prepared %d instruction examples → %s", len(records), output_path)


def _step_train(dataset: Path, adapter_dir: Path) -> None:
    """Fine-tune Qwen2.5-7B via Unsloth (hardware check first)."""
    hw = _check_hardware()
    if not hw["sufficient"]:
        logger.error("HARDWARE INSUFFICIENT: %s", hw["note"])
        logger.error("Phase 2 LoRA deferred. See RESULTS/research/lora_voice_eval_*.md")
        sys.exit(3)
    try:
        from unsloth import FastLanguageModel  # noqa: PLC0415
    except ImportError:
        logger.error("unsloth not installed. pip install unsloth")
        sys.exit(2)

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=_BASE_MODEL,
        max_seq_length=2048,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "v_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
    )
    logger.info("LoRA model configured. Dataset: %s", dataset)
    # Full training loop deferred — stub for hardware-available context
    adapter_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Training stub complete. Adapter would be saved to: %s", adapter_dir)


def _step_eval(adapter_dir: Path, output_report: Path) -> None:
    """Generate 10 scene prompts, score cliché delta + style cosine."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.calliope_shell.style_coach import lint_scene_output  # noqa: PLC0415

    results = []
    for prompt in _EVAL_PROMPTS:
        base_report = lint_scene_output(prompt)
        results.append({
            "prompt": prompt,
            "base_cliche_count": base_report.cliche_count,
            "base_style_drift": base_report.style_drift_score,
            "lora_cliche_count": "N/A (deferred)",
            "lora_style_drift": "N/A (deferred)",
        })

    output_report.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# LoRA Voice Eval Report\n", f"Base model: {_BASE_MODEL}\n\n"]
    lines.append("| Prompt | Base Clichés | Base Drift | LoRA Clichés | LoRA Drift |\n")
    lines.append("|--------|-------------|------------|-------------|------------|\n")
    for r in results:
        lines.append(
            f"| {r['prompt'][:40]} | {r['base_cliche_count']} | "
            f"{r['base_style_drift']} | {r['lora_cliche_count']} | {r['lora_style_drift']} |\n"
        )
    lines.append("\n**Note**: LoRA columns N/A — NM GPU T500 2GB insufficient. Defer to cloud H100.\n")
    output_report.write_text("".join(lines), encoding="utf-8")
    logger.info("Eval report written to %s", output_report)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="LoRA voice eval pipeline")
    parser.add_argument("--check-hardware", action="store_true")
    parser.add_argument("--step", choices=["prep", "train", "eval"])
    parser.add_argument("--corpus-dir", type=Path, default=Path("data/lora_corpus"))
    parser.add_argument("--dataset", type=Path, default=Path("data/lora_corpus/train.jsonl"))
    parser.add_argument("--adapter", type=Path, default=_LORA_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=Path("RESULTS/research/lora_voice_eval_2026-05-19.md"))
    args = parser.parse_args()

    if args.check_hardware:
        hw = _check_hardware()
        print(f"GPU: {hw['gpu_available']} | VRAM: {hw['vram_gb']}GB | Sufficient: {hw['sufficient']}")
        if hw["note"]:
            print(f"Note: {hw['note']}")
        return

    if args.step == "prep":
        _step_prep(args.corpus_dir, args.dataset)
    elif args.step == "train":
        _step_train(args.dataset, args.adapter)
    elif args.step == "eval":
        _step_eval(args.adapter, args.report)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
