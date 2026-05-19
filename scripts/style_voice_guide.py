"""
Lightweight operator voice-style adapter.

Loads operator voice samples from data/operator_voice_samples.txt (or stubs)
and builds a system-prompt prefix for style-matching LLM calls.

Usage:
    from scripts.style_voice_guide import build_style_prefix
    prefix = build_style_prefix()   # inject at top of LLM system prompt
    # CLI: python3 scripts/style_voice_guide.py --output data/operator_voice_samples.txt
"""

import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)

_SAMPLES_PATH = Path(__file__).parent.parent / "data" / "operator_voice_samples.txt"

_STUB_SAMPLES = [
    "Aurora si mosse senza fretta, la mano già sulla guardia della lama.",
    "Il silenzio tra i due non era imbarazzante — era deliberato.",
    "Niente armature d'oro, niente sguardi che 'trafiggono l'anima'. Solo fatti.",
]


def _load_samples_from_chromadb(n: int = 20) -> list[str]:
    """Try to pull operator messages from ChromaDB calliope_messages collection."""
    try:
        import chromadb  # noqa: PLC0415

        client = chromadb.PersistentClient(
            str(Path(__file__).parent.parent / "data" / "chromadb")
        )
        col = client.get_collection("calliope_messages")
        results = col.get(limit=200, include=["documents", "metadatas"])
        docs = results.get("documents") or []
        metas = results.get("metadatas") or []
        operator_docs = [
            d
            for d, m in zip(docs, metas)
            if m and m.get("author_type") == "operator"
        ]
        if not operator_docs:
            # Fallback: random sample (no author metadata)
            operator_docs = docs
        sample = random.sample(operator_docs, min(n, len(operator_docs)))
        logger.info("Loaded %d operator voice samples from ChromaDB", len(sample))
        return sample
    except Exception as exc:
        logger.warning("ChromaDB voice sample load failed (stub fallback): %s", exc)
        return []


def build_samples_file(output_path: Path = _SAMPLES_PATH, n: int = 20) -> Path:
    """Extract samples and write to output_path. Returns path written."""
    samples = _load_samples_from_chromadb(n)
    if not samples:
        logger.warning("Using stub voice samples (ChromaDB unavailable)")
        samples = _STUB_SAMPLES
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n---\n".join(samples), encoding="utf-8")
    logger.info("Voice samples written to %s (%d samples)", output_path, len(samples))
    return output_path


def load_samples(path: Path = _SAMPLES_PATH, k: int = 5) -> list[str]:
    """Load k random samples from file (or stubs if file missing)."""
    if not path.exists():
        logger.warning("Voice samples file not found — using stubs")
        return _STUB_SAMPLES[:k]
    raw = path.read_text(encoding="utf-8").split("---")
    samples = [s.strip() for s in raw if s.strip()]
    return random.sample(samples, min(k, len(samples)))


def build_style_prefix(k: int = 5) -> str:
    """Return a system-prompt prefix for operator voice-matching."""
    samples = load_samples(k=k)
    examples = "\n".join(f"  - {s}" for s in samples)
    return (
        "Write in this style — direct, understated, no grandiloquent descriptions.\n"
        "Example passages:\n"
        f"{examples}\n"
    )


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Build operator voice samples file")
    parser.add_argument(
        "--output",
        type=Path,
        default=_SAMPLES_PATH,
        help="Output path for voice samples",
    )
    parser.add_argument("--n", type=int, default=20, help="Number of samples to extract")
    args = parser.parse_args()
    build_samples_file(args.output, args.n)
