"""
Contract test (father-authored acceptance) — WI-7.

Il worker Efesto deve far passare questi test creando
`scripts/discord_incremental_scrape.py` con le tre funzioni:

    filter_since(records: list[dict], last_ts: str | None) -> list[dict]
        Funzione PURA — ritorna solo record con record["timestamp"] > last_ts.
        Se last_ts è None ritorna tutti i record.

    load_last_ts(json_path: Path) -> str | None
        Legge {"last_ts": "..."} da file JSON.
        Ritorna None se il file non esiste o last_ts è null.

    save_last_ts(json_path: Path, ts: str) -> None
        Scrive {"last_ts": ts} nel file JSON (sovrascrive).

NON modificare le assertion: sono il contratto di accettazione.
"""
import json
import sys
from pathlib import Path

import pytest

# scripts/ non è un package installato — aggiunge la root al path di import
sys.path.insert(0, str(Path(__file__).parents[2]))

try:
    from scripts.discord_incremental_scrape import (  # noqa: E402
        filter_since,
        load_last_ts,
        save_last_ts,
    )

    _MODULE_MISSING = False
except ImportError:
    _MODULE_MISSING = True


@pytest.fixture(autouse=True)
def require_module():
    if _MODULE_MISSING:
        pytest.fail(
            "scripts/discord_incremental_scrape.py mancante — "
            "implementare filter_since, load_last_ts, save_last_ts"
        )


# --- Messaggi sintetici ------------------------------------------------------

_RECORDS = [
    {"timestamp": "2024-01-15T10:00:00+00:00", "content": "old msg A"},
    {"timestamp": "2024-04-01T12:00:00+00:00", "content": "new msg B"},
    {"timestamp": "2025-01-01T00:00:00+00:00", "content": "new msg C"},
]

_CUTOFF = "2024-03-01T00:00:00+00:00"


# --- filter_since (pura) -----------------------------------------------------

def test_filter_since_returns_only_newer():
    result = filter_since(_RECORDS, _CUTOFF)
    assert len(result) == 2
    contents = {r["content"] for r in result}
    assert "new msg B" in contents
    assert "new msg C" in contents
    assert "old msg A" not in contents


def test_filter_since_none_last_ts_returns_all():
    result = filter_since(_RECORDS, None)
    assert len(result) == len(_RECORDS)


def test_filter_since_empty_records():
    assert filter_since([], _CUTOFF) == []


def test_filter_since_all_older_returns_empty():
    cutoff_future = "2099-01-01T00:00:00+00:00"
    assert filter_since(_RECORDS, cutoff_future) == []


def test_filter_since_is_pure_does_not_mutate():
    original = [r.copy() for r in _RECORDS]
    filter_since(_RECORDS, _CUTOFF)
    assert _RECORDS == original


# --- load_last_ts / save_last_ts ---------------------------------------------

def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "last_scrape.json"
    ts = "2025-06-01T08:00:00+00:00"
    save_last_ts(p, ts)
    assert load_last_ts(p) == ts


def test_load_missing_file_returns_none(tmp_path):
    p = tmp_path / "nonexistent.json"
    assert load_last_ts(p) is None


def test_load_null_value_returns_none(tmp_path):
    p = tmp_path / "last_scrape.json"
    p.write_text(json.dumps({"last_ts": None}))
    assert load_last_ts(p) is None


def test_save_overwrites_existing(tmp_path):
    p = tmp_path / "last_scrape.json"
    save_last_ts(p, "2024-01-01T00:00:00+00:00")
    save_last_ts(p, "2025-06-10T00:00:00+00:00")
    assert load_last_ts(p) == "2025-06-10T00:00:00+00:00"


# --- Integrazione: filtra + aggiorna last_scrape.json -----------------------

def test_integration_filter_and_update(tmp_path):
    """Simula il workflow completo: leggi last_ts, filtra, salva nuovo max."""
    p = tmp_path / "last_scrape.json"
    save_last_ts(p, _CUTOFF)

    last = load_last_ts(p)
    fresh = filter_since(_RECORDS, last)

    assert len(fresh) == 2  # solo msg B e C

    new_max = max(r["timestamp"] for r in fresh)
    save_last_ts(p, new_max)

    assert load_last_ts(p) == "2025-01-01T00:00:00+00:00"
