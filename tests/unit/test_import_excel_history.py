import pytest
pytest.importorskip("pandas")
import sys
from pathlib import Path
import pandas as pd
import numpy as np

try:
    pd.Series({"_test": "ok"})
    _PANDAS_SERIES_OK = True
except Exception:
    _PANDAS_SERIES_OK = False

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from import_excel_history import normalize_character_name, safe_str, classify_row, ts_to_iso

def test_normalize_hp_stripped():
    assert normalize_character_name("Philip 75/100%") == "Philip"

def test_normalize_no_change():
    assert normalize_character_name("Aurora of Winter") == "Aurora of Winter"

def test_normalize_none():
    assert normalize_character_name(None) is None

def test_normalize_empty():
    result = normalize_character_name("")
    assert result == "" or result is None

def test_safe_str_none():
    assert safe_str(None) is None

def test_safe_str_string():
    assert safe_str("hello") == "hello"

def test_safe_str_nan():
    assert safe_str(np.nan) is None

@pytest.mark.skipif(not _PANDAS_SERIES_OK, reason="pd.Series({}) rotto: numpy/pandas incompatibili su py3.13")
def test_classify_row_ic():
    row = pd.Series({"player": "Horo", "character": "Aurora", "message": "She walks", "type": "message"})
    assert classify_row(row) == "IC"

@pytest.mark.skipif(not _PANDAS_SERIES_OK, reason="pd.Series({}) rotto: numpy/pandas incompatibili su py3.13")
def test_classify_row_ooc():
    row = pd.Series({"player": "Horo", "character": None, "message": "(Let's break)", "type": "message"})
    assert classify_row(row) == "OOC"

@pytest.mark.skipif(not _PANDAS_SERIES_OK, reason="pd.Series({}) rotto: numpy/pandas incompatibili su py3.13")
def test_classify_row_system():
    row = pd.Series({"system message": "Server joined", "character": None})
    assert classify_row(row) == "system"

def test_ts_to_iso_none():
    assert ts_to_iso(None) is None

def test_ts_to_iso_valid():
    ts = pd.Timestamp("2024-01-15 10:30:00")
    result = ts_to_iso(ts)
    assert result is not None and "2024" in result
