"""Tests for scripts/merge_char_sources.py — fixtures for tupper-only, all-3-sources, discord-only."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import merge_char_sources as mcs  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _make_tupper(name: str, desc: str, last_used: str = "2024-06-01T00:00:00+00:00") -> dict:
    return {
        "id": 123,
        "name": name,
        "description": desc,
        "last_used": last_used,
        "created_at": "2024-01-01T00:00:00+00:00",
        "brackets": [f"{name}:", ""],
        "avatar_url": None,
        "avatar": None,
        "banner": None,
        "posts": 5,
        "show_brackets": False,
        "birthday": None,
        "tag": None,
        "nick": None,
        "group_id": None,
    }


def _make_sheet(
    char_name: str,
    sheet_text: str,
    last_updated: str = "2025-01-01T00:00:00+00:00",
    thread_id: str = "thread_001",
    author_id: str = "author_001",
) -> dict:
    return {
        "char_name": char_name,
        "thread_id": thread_id,
        "thread_name": char_name,
        "author_id": author_id,
        "author_username": "testuser",
        "sheet_text": sheet_text,
        "created_at": "2024-12-01T00:00:00+00:00",
        "last_updated": last_updated,
        "msg_count_in_thread": 3,
    }


def _make_corpus(char_name: str, n: int = 30, ts: str = "2024-11-15T00:00:00Z") -> dict:
    return {char_name: {"messages": [f"sample msg {i}" for i in range(n)], "last_ts": ts}}


# ---------------------------------------------------------------------------
# Test slugify + fuzzy
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert mcs.slugify("Aurora of Winter") == "aurora-of-winter"
    assert mcs.slugify("  Haruki Ansel  ") == "haruki-ansel"


def test_fuzzy_match_finds_close():
    candidates = ["Aurora of Winter", "Haruki Ansel", "Rusty"]
    assert mcs.fuzzy_match_chars("Aurora Of Winter", candidates) == "Aurora of Winter"
    assert mcs.fuzzy_match_chars("completely_unrelated_xyz", candidates) is None


def test_prefix_word_match_aurora():
    """'Aurora of Winter' should match corpus key 'Aurora' via prefix-word match."""
    corpus_keys = ["Aurora", "Filomena", "NARRATOR", "Pdor"]
    # Tupperbox name → corpus key (find voice samples direction)
    assert mcs.fuzzy_match_chars("Aurora of Winter", corpus_keys) == "Aurora"
    # Reverse direction: corpus name → tupper key
    tupper_keys = ["Aurora of Winter", 'Filomena Exilio "Cold  Wind"', "Grimm"]
    assert mcs.fuzzy_match_chars("Aurora", tupper_keys) == "Aurora of Winter"
    assert mcs.fuzzy_match_chars("Filomena", tupper_keys) == 'Filomena Exilio "Cold  Wind"'


def test_alias_map_overrides_prefix_match():
    """Explicit alias_map entry takes priority over prefix-word match."""
    candidates = ["Aurora of Winter", "Aurora Borealis", "Grimm"]
    # Without alias_map: prefix match picks first "Aurora of Winter"
    assert mcs.fuzzy_match_chars("Aurora", candidates) == "Aurora of Winter"
    # With alias_map: operator forces different canonical name
    alias = {"aurora": "Aurora Borealis"}
    assert mcs.fuzzy_match_chars("Aurora", candidates, alias_map=alias) == "Aurora Borealis"
    # alias_map miss → falls through to prefix match
    assert mcs.fuzzy_match_chars("Grimm", candidates, alias_map=alias) == "Grimm"


# ---------------------------------------------------------------------------
# Test merge_char — tupper-only
# ---------------------------------------------------------------------------

class TestMergeCharTupperOnly:
    def setup_method(self):
        self.tupper = _make_tupper("Grimm", "Imposing black creature, 4m tall", "2024-06-01T00:00:00+00:00")

    def test_physical_from_tupper(self):
        result = mcs.merge_char(self.tupper, None, {})
        assert result["physical"] == "Imposing black creature, 4m tall"
        assert result["metadata"]["physical"]["source"] == "tupperbox"
        assert result["metadata"]["lore"]["source"] == "tupperbox"
        assert "deprecated_physical_v1" not in result

    def test_schema_fields_present(self):
        result = mcs.merge_char(self.tupper, None, {})
        for field in ("name", "slug", "author_id", "metadata", "physical", "lore", "voice_samples"):
            assert field in result
        assert result["name"] == "Grimm"
        assert result["slug"] == "grimm"
        assert result["voice_samples"] == []
        assert result["metadata"]["voice"]["sample_count"] == 0

    def test_no_source_raises(self):
        with pytest.raises(ValueError):
            mcs.merge_char(None, None, {})


# ---------------------------------------------------------------------------
# Test merge_char — discord-only
# ---------------------------------------------------------------------------

class TestMergeCharDiscordOnly:
    def setup_method(self):
        self.sheet = _make_sheet(
            "Rusty",
            "Name: Rusty\nRace: Artificial Construct\nAge: Unknown",
            last_updated="2025-03-01T00:00:00+00:00",
        )

    def test_lore_from_discord(self):
        result = mcs.merge_char(None, self.sheet, {})
        assert result["lore"] == self.sheet["sheet_text"]
        assert result["metadata"]["lore"]["source"] == "discord-thread"
        assert result["metadata"]["lore"]["thread_id"] == "thread_001"

    def test_physical_excerpt_from_sheet(self):
        result = mcs.merge_char(None, self.sheet, {})
        assert result["physical"] == self.sheet["sheet_text"][:500]
        assert result["metadata"]["physical"]["source"] == "discord-thread"


# ---------------------------------------------------------------------------
# Test merge_char — all 3 sources, recency-weighted
# ---------------------------------------------------------------------------

class TestMergeCharAllSources:
    def setup_method(self):
        # Tupper: last_used 2024-01-01 (old)
        self.tupper = _make_tupper(
            "Aurora of Winter",
            "Old physical desc from Tupperbox",
            last_used="2024-01-01T00:00:00+00:00",
        )
        # Discord sheet: last_updated 2025-09-01 (>180 days newer → wins)
        self.sheet = _make_sheet(
            "Aurora of Winter",
            "Aurora: Full RP sheet — Okami-mimi female, 5ft 5in...",
            last_updated="2025-09-01T00:00:00+00:00",
            thread_id="thread_aurora",
            author_id="player_horo",
        )
        self.corpus = _make_corpus("Aurora of Winter", 50, "2024-11-30T00:00:00Z")

    def test_discord_wins_physical_recency(self):
        result = mcs.merge_char(self.tupper, self.sheet, self.corpus.get("Aurora of Winter", {}))
        # Discord is >180 days newer → should win physical
        assert result["metadata"]["physical"]["source"] == "discord-thread"
        assert result["deprecated_physical_v1"] == "Old physical desc from Tupperbox"

    def test_lore_always_discord(self):
        result = mcs.merge_char(self.tupper, self.sheet, self.corpus.get("Aurora of Winter", {}))
        assert result["lore"] == self.sheet["sheet_text"]
        assert result["metadata"]["lore"]["source"] == "discord-thread"

    def test_voice_samples_populated(self):
        result = mcs.merge_char(self.tupper, self.sheet, self.corpus.get("Aurora of Winter", {}))
        assert result["metadata"]["voice"]["sample_count"] == 50
        assert result["metadata"]["voice"]["source"] == "corpus"
        assert result["metadata"]["voice"]["last_msg"] == "2024-11-30"
        assert len(result["voice_samples"]) == 50

    def test_author_id_from_sheet(self):
        result = mcs.merge_char(self.tupper, self.sheet, self.corpus.get("Aurora of Winter", {}))
        assert result["author_id"] == "player_horo"

    def test_tupper_wins_when_older_discord(self):
        # Tupper: 2025-09-01 (recent), Discord: 2024-01-01 (old, >180 days gap)
        tupper_new = _make_tupper("TestChar", "New tupper desc", last_used="2025-09-01T00:00:00+00:00")
        sheet_old = _make_sheet("TestChar", "Old discord sheet", last_updated="2024-01-01T00:00:00+00:00")
        result = mcs.merge_char(tupper_new, sheet_old, {})
        assert result["metadata"]["physical"]["source"] == "tupperbox"
        assert result["deprecated_physical_v1"] == "Old discord sheet"[:500]

    def test_llm_merge_called_when_close_dates(self):
        # Both ~same date (within 180 days) → llm_merge_fn called
        tupper_close = _make_tupper("CloseChar", "Tupper desc", last_used="2025-01-01T00:00:00+00:00")
        sheet_close = _make_sheet("CloseChar", "Discord sheet", last_updated="2025-02-01T00:00:00+00:00")

        mock_llm = MagicMock(return_value="Intelligently merged text")
        result = mcs.merge_char(tupper_close, sheet_close, {}, llm_merge_fn=mock_llm)

        mock_llm.assert_called_once()
        assert result["physical"] == "Intelligently merged text"
        assert result["metadata"]["physical"]["source"] == "merged"
        assert "deprecated_physical_v1" not in result


# ---------------------------------------------------------------------------
# Test merge_all integration
# ---------------------------------------------------------------------------

class TestMergeAll:
    def test_merge_all_writes_yaml(self, tmp_path):
        tuppers = [_make_tupper("Grimm", "Black creature")]
        sheets = [_make_sheet("Rusty", "Robot char sheet")]
        corpus: dict = {}

        mcs.merge_all(tuppers, sheets, corpus, str(tmp_path))

        # Both chars should produce YAML files
        yaml_files = list(tmp_path.glob("*.yaml"))
        assert len(yaml_files) == 2

        names_written = {f.stem for f in yaml_files}
        assert "grimm" in names_written
        assert "rusty" in names_written

    def test_merge_all_returns_list(self, tmp_path):
        tuppers = [_make_tupper("Aurora of Winter", "Aurora desc")]
        results = mcs.merge_all(tuppers, [], {}, str(tmp_path))
        assert len(results) == 1
        assert results[0]["slug"] == "aurora-of-winter"

    def test_yaml_output_valid(self, tmp_path):
        tupper = _make_tupper("Koibo", "Small fox spirit")
        mcs.merge_all([tupper], [], {}, str(tmp_path))
        yaml_file = tmp_path / "koibo.yaml"
        assert yaml_file.exists()
        data = yaml.safe_load(yaml_file.read_text())
        assert data["name"] == "Koibo"
        assert "metadata" in data
        assert "physical" in data
