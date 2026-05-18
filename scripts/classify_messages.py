#!/usr/bin/env python3
"""
classify_messages.py - Batch classify Discord messages into IC, OOC, meta, or art tags.

Usage:
    python classify_messages.py --input messages_clean.jsonl --output messages_classified.jsonl
"""

import argparse
import json
import logging
import os
import sys
from typing import Any

import requests
from tqdm import tqdm


# Set up logging with UTF-8 encoding
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True,
)
logger = logging.getLogger(__name__)


# Classification prompt template
SYSTEM_PROMPT = (
    "You are a Discord RP message classifier. Classify each message as:\n"
    "IC = in-character roleplay narrative\n"
    "OOC = out-of-character player comment (often in parentheses)\n"
    "meta = server meta discussion, rules, announcements\n"
    "art = image/art sharing with minimal text\n"
    "Return ONLY a JSON array of strings, one per message, in the same order."
)


def rule_based_fallback(message: dict[str, Any]) -> str:
    """Simple rule-based classifier as fallback."""
    content = (message.get("content") or "").strip()
    if content.startswith("("):
        return "OOC"
    if any(keyword in content.lower() for keyword in ["server", "rule", "announce", "mod", "admin"]):
        return "meta"
    if any(keyword in content.lower() for keyword in ["image", "art", "pic", "draw", "img"]):
        return "art"
    return "IC"


def classify_batch(messages: list[dict[str, Any]], provider: str, model: str) -> list[str]:
    """
    Classify a batch of messages using an LLM via HTTP API.

    Args:
        messages: List of message dicts with at least 'content' field.
        provider: One of 'cerebras', 'groq', 'local'.
        model: Model identifier to use.

    Returns:
        List of classification tags (IC/OOC/meta/art) in same order as input.
    """
    # Build prompt with truncated message content
    prompt_lines = []
    for i, msg in enumerate(messages):
        content = msg.get("content", "") or ""
        truncated = content.strip()[:200].replace("\n", " ")
        prompt_lines.append(f"{i}: {truncated}")

    user_prompt = "\n".join(prompt_lines)

    headers = {"Content-Type": "application/json"}
    data: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }

    url = ""
    if provider == "cerebras":
        url = "https://api.cerebras.ai/v1/chat/completions"
        api_key = os.getenv("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable is required for provider 'cerebras'")
        headers["Authorization"] = f"Bearer {api_key}"
    elif provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required for provider 'groq'")
        headers["Authorization"] = f"Bearer {api_key}"
    elif provider == "local":
        url = "http://localhost:11434/api/chat"
        data = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.0},
        }
    else:
        raise ValueError(f"Unsupported provider: {provider}")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        resp_json = response.json()

        # Extract assistant message
        if provider == "local":
            content = resp_json.get("message", {}).get("content", "")
        else:
            content = resp_json["choices"][0]["message"]["content"]

        # Try parsing as JSON array first
        try:
            tags = json.loads(content.strip())
            if isinstance(tags, list):
                return [str(tag).strip() for tag in tags]
        except json.JSONDecodeError:
            pass

        # Fallback: split by lines and clean
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        tags = []
        for line in lines:
            cleaned = line.split(":", 1)[-1].strip() if ":" in line else line
            cleaned = cleaned.lstrip("0123456789.-* \t")
            if "IC" in cleaned.upper():
                tags.append("IC")
            elif "OOC" in cleaned.upper():
                tags.append("OOC")
            elif "META" in cleaned.upper():
                tags.append("meta")
            elif "ART" in cleaned.upper():
                tags.append("art")
            else:
                tags.append("IC")
        return tags

    except Exception as e:
        logger.warning(f"LLM classification failed: {e}. Using rule-based fallback.")
        return [rule_based_fallback(msg) for msg in messages]


def read_jsonl(file_path: str) -> list[dict[str, Any]]:
    """Read JSONL file into list of dicts."""
    data = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping invalid JSON line: {e}")
    return data


def write_jsonl(data: list[dict[str, Any]], file_path: str) -> None:
    """Write list of dicts to JSONL file."""
    with open(file_path, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify Discord messages in batch")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file path")
    parser.add_argument("--output", type=str, required=True, help="Output JSONL file path")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for classification")
    parser.add_argument(
        "--provider",
        type=str,
        default="cerebras",
        choices=["cerebras", "groq", "local"],
        help="LLM provider",
    )
    parser.add_argument("--model", type=str, default="qwen-3-235b-a22b-instruct-2507", help="Model name to use")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output, just print sample")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    logger.info(f"Reading messages from {args.input}")
    messages = read_jsonl(args.input)

    logger.info(f"Loaded {len(messages)} messages. Starting classification...")

    batch_size = args.batch_size
    classified_messages: list[dict[str, Any]] = []

    for i in tqdm(range(0, len(messages), batch_size), desc="Classifying batches"):
        batch = messages[i : i + batch_size]
        try:
            tags = classify_batch(batch, provider=args.provider, model=args.model)
            if len(tags) != len(batch):
                logger.warning(f"Tag count mismatch: expected {len(batch)}, got {len(tags)}. Using fallbacks.")
                while len(tags) < len(batch):
                    tags.append(rule_based_fallback(batch[len(tags)]))
            for msg, tag in zip(batch, tags):
                msg_copy = msg.copy()
                msg_copy["classified_tag"] = tag
                classified_messages.append(msg_copy)
        except Exception as e:
            logger.error(f"Failed to classify batch {i // batch_size}: {e}")
            for msg in batch:
                msg_copy = msg.copy()
                msg_copy["classified_tag"] = rule_based_fallback(msg)
                classified_messages.append(msg_copy)

    if args.dry_run:
        logger.info("Dry run: not writing output. Sample results:")
        for msg in classified_messages[:3]:
            print(json.dumps(msg, ensure_ascii=False, indent=2))
    else:
        logger.info(f"Writing {len(classified_messages)} classified messages to {args.output}")
        write_jsonl(classified_messages, args.output)
        logger.info("Done.")

    logger.info("Classification completed.")


if __name__ == "__main__":
    main()
