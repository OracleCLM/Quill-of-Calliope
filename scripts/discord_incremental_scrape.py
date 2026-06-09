import json
from pathlib import Path


def filter_since(records: list[dict], last_ts: str | None) -> list[dict]:
    """Filtra i record mantenendo quelli con timestamp successivo a last_ts."""
    if last_ts is None:
        return records
    return [r for r in records if r["timestamp"] > last_ts]


def load_last_ts(json_path: Path) -> str | None:
    """Legge il timestamp dell'ultimo scrape dal file JSON."""
    if not json_path.exists():
        return None
    data = json.loads(json_path.read_text())
    return data.get("last_ts")


def save_last_ts(json_path: Path, ts: str) -> None:
    """Salva il timestamp dell'ultimo scrape nel file JSON."""
    json_path.write_text(json.dumps({"last_ts": ts}))
