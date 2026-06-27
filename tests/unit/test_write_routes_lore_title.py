"""GAP-7 regression: _lore_blocks() include il titolo della voce lore (come GAP-2 per scene_refine)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_entry(title: str, content: str):
    e = MagicMock()
    e.title = title
    e.content = content
    return e


def test_lore_blocks_includes_title():
    entries = [_make_entry("Drago", "Antico custode della caverna.")]
    store_mock = MagicMock()
    store_mock.triggered_entries.return_value = entries

    with patch("app.calliope_shell.lore_kb.LoreStore", return_value=store_mock):
        from app.calliope_shell.write_routes import _lore_blocks
        blocks = _lore_blocks("drago")

    assert len(blocks) == 1
    assert "Drago" in blocks[0], f"titolo mancante in lore_block: {blocks[0]!r}"
    assert "Antico custode" in blocks[0]


def test_lore_blocks_no_title_fallback():
    entries = [_make_entry("", "Solo contenuto.")]
    store_mock = MagicMock()
    store_mock.triggered_entries.return_value = entries

    with patch("app.calliope_shell.lore_kb.LoreStore", return_value=store_mock):
        from app.calliope_shell.write_routes import _lore_blocks
        blocks = _lore_blocks("query")

    assert len(blocks) == 1
    assert blocks[0] == "Solo contenuto."
