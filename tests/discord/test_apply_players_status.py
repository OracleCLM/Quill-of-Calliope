import sys
from pathlib import Path
import json
import hashlib

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.apply_players_status import load_players_mapping, process_messages  # noqa: E402


def make_yaml(tmp_path: Path, players_list: list) -> Path:
    """Write players YAML to tmp_path/players.yaml and return path."""
    import yaml

    yaml_content = {"players": players_list}
    players_yaml = tmp_path / "players.yaml"
    with open(players_yaml, "w", encoding="utf-8") as f:
        yaml.safe_dump(yaml_content, f)
    return players_yaml


def make_jsonl(tmp_path: Path, messages_list: list) -> Path:
    """Write messages as JSONL to tmp_path/messages.jsonl and return path."""
    messages_file = tmp_path / "messages.jsonl"
    with open(messages_file, "w", encoding="utf-8") as f:
        for msg in messages_list:
            f.write(json.dumps(msg) + "\n")
    return messages_file


def test_exact_match(tmp_path):
    """Test exact nickname match with player name."""
    players = [
        {"name": "Drako", "aliases": []},
    ]
    yaml_path = make_yaml(tmp_path, players)

    messages = [
        {
            "message_id": "1",
            "author_name": "drako_user",
            "author_nick": "Drako",
            "content": "Hello",
        }
    ]
    input_path = make_jsonl(tmp_path, messages)
    output_path = tmp_path / "output.jsonl"

    players_mapping = load_players_mapping(yaml_path)
    process_messages(input_path, output_path, players_mapping, threshold=0.7, dry_run=False)

    with open(output_path, encoding="utf-8") as f:
        result = json.loads(f.readline())

    assert result["player_status"] == "active"
    assert result["player_match_name"] == "Drako"
    assert result["player_match_score"] > 0.7


def test_alias_match(tmp_path):
    """Test match via alias."""
    players = [
        {
            "name": "Horo'sLittlePinkWaifu",
            "aliases": ["little pink rin", "HorosLittlePinkWaifu"],
        }
    ]
    yaml_path = make_yaml(tmp_path, players)

    messages = [
        {
            "message_id": "2",
            "author_name": "some_user",
            "author_nick": "little pink rin",
            "content": "Hi!",
        }
    ]
    input_path = make_jsonl(tmp_path, messages)
    output_path = tmp_path / "output.jsonl"

    players_mapping = load_players_mapping(yaml_path)
    process_messages(input_path, output_path, players_mapping, threshold=0.7, dry_run=False)

    with open(output_path, encoding="utf-8") as f:
        result = json.loads(f.readline())

    assert result["player_match_name"] == "Horo'sLittlePinkWaifu"
    assert result["player_status"] == "active"


def test_e5kimo_variant(tmp_path):
    """Test case-insensitive match on alias (E5K1M0 → e5k1m0 → The E5kimo).

    WRatio("E5K1M0", "e5k1m0") ≈ 50, so threshold=0.45 is used to confirm
    that the best candidate resolves to the correct player name.
    """
    players = [
        {"name": "The E5kimo", "aliases": ["E5kimo", "e5k1m0"]},
    ]
    yaml_path = make_yaml(tmp_path, players)

    messages = [
        {
            "message_id": "3",
            "author_name": "e5kimo_user",
            "author_nick": "E5K1M0",
            "content": "Let's go!",
        }
    ]
    input_path = make_jsonl(tmp_path, messages)
    output_path = tmp_path / "output.jsonl"

    players_mapping = load_players_mapping(yaml_path)
    # threshold=0.45 — WRatio("E5K1M0","e5k1m0")≈0.50, above cutoff; best
    # candidate maps back to "The E5kimo" via players_mapping.
    process_messages(input_path, output_path, players_mapping, threshold=0.45, dry_run=False)

    with open(output_path, encoding="utf-8") as f:
        result = json.loads(f.readline())

    assert result["player_match_name"] == "The E5kimo"
    assert result["player_status"] == "active"


def test_below_threshold(tmp_path):
    """Test no match when similarity is below threshold."""
    players = [
        {"name": "Drako", "aliases": []},
        {
            "name": "Horo'sLittlePinkWaifu",
            "aliases": ["little pink rin", "HorosLittlePinkWaifu"],
        },
        {"name": "The E5kimo", "aliases": ["E5kimo", "e5k1m0"]},
    ]
    yaml_path = make_yaml(tmp_path, players)

    messages = [
        {
            "message_id": "4",
            "author_name": "mystery_user",
            "author_nick": "XxUnknownPlayerxX",
            "content": "??",
        }
    ]
    input_path = make_jsonl(tmp_path, messages)
    output_path = tmp_path / "output.jsonl"

    players_mapping = load_players_mapping(yaml_path)
    process_messages(input_path, output_path, players_mapping, threshold=0.7, dry_run=False)

    with open(output_path, encoding="utf-8") as f:
        result = json.loads(f.readline())

    assert result["player_status"] == "unknown"
    assert result["player_match_name"] is None
    assert result["player_match_score"] == 0.0


def test_idempotency(tmp_path):
    """Running process_messages twice on the same output file yields identical bytes."""
    players = [
        {"name": "Drako", "aliases": []},
        {
            "name": "Horo'sLittlePinkWaifu",
            "aliases": ["little pink rin"],
        },
    ]
    yaml_path = make_yaml(tmp_path, players)

    messages = [
        {
            "message_id": "5",
            "author_name": "drako_user",
            "author_nick": "Drako",
            "content": "First",
        },
        {
            "message_id": "6",
            "author_name": "some_user",
            "author_nick": "little pink rin",
            "content": "Second",
        },
    ]
    input_path = make_jsonl(tmp_path, messages)
    output_path = tmp_path / "output.jsonl"

    players_mapping = load_players_mapping(yaml_path)

    # First run
    process_messages(input_path, output_path, players_mapping, threshold=0.7, dry_run=False)
    with open(output_path, "rb") as f:
        hash1 = hashlib.sha256(f.read()).hexdigest()

    # Second run: output becomes input (idempotency — already has player_* fields)
    process_messages(output_path, output_path, players_mapping, threshold=0.7, dry_run=False)
    with open(output_path, "rb") as f:
        hash2 = hashlib.sha256(f.read()).hexdigest()

    assert hash1 == hash2
