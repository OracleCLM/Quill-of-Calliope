import pytest
from app.calliope_shell import characters_service as cs


@pytest.mark.unit
def test_list_cards_shape():
    cards = cs.list_cards()
    if not cards:
        pytest.skip("no character cards")
    assert isinstance(cards, list)
    for item in cards:
        assert isinstance(item, dict)
        for key in ("stem", "name", "compact", "tags"):
            assert key in item
        assert isinstance(item["tags"], list)


@pytest.mark.unit
def test_get_card_v3_full_and_extensions():
    cards = cs.list_cards()
    if not cards:
        pytest.skip("no character cards")
    chosen = None
    for c in cards:
        v = cs.get_card_v3(c["stem"])
        if v and v.get("extensions"):
            chosen = v
            break
    if chosen is None:
        pytest.skip("no card with extensions")
    assert "name" in chosen
    extensions = chosen["extensions"]
    assert isinstance(extensions, dict) and extensions


@pytest.mark.unit
def test_import_v3_roundtrip():
    card = cs.import_card_v3({"name": "Zeta", "extensions": {"k": "v"}})
    assert card.name == "Zeta"
    assert isinstance(card.extensions, dict)
    assert card.extensions.get("k") == "v"


@pytest.mark.unit
def test_get_card_v3_missing_returns_none():
    assert cs.get_card_v3("___nonexistent_stem___") is None


@pytest.mark.unit
def test_export_alias():
    cards = cs.list_cards()
    if not cards:
        pytest.skip("no character cards")
    stem = cards[0]["stem"]
    assert cs.export_card_v3(stem) == cs.get_card_v3(stem)
