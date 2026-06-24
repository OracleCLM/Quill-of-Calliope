"""Unit test per scripts/route_scene.py.

Copre:
  - route_scene() — decision engine (pura, no HTTP)
  - load_config() — YAML validation
  - BlockedContentError — attributi custom
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import yaml

from scripts.route_scene import (
    DEFAULT_CONFIG,
    BlockedContentError,
    _call_claude_subprocess,
    _call_gateway,
    _call_ollama,
    dispatch_to_tier,
    load_config,
    main,
    route_scene,
)

_MOD = "scripts.route_scene"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_score(**kwargs) -> dict:
    """Score con tutti i valori a 0, sovrascrivi solo i campi richiesti."""
    base = {"non_consent": 0, "minors_adjacent": 0, "violence": 0, "explicit": 0}
    base.update(kwargs)
    return base


# ── BlockedContentError ───────────────────────────────────────────────────────

def test_blocked_error_attrs():
    err = BlockedContentError("troppo violento", "non_consent", 4)
    assert err.dimension == "non_consent"
    assert err.score == 4
    assert "troppo violento" in str(err)


# ── route_scene — blocchi hard ────────────────────────────────────────────────

def test_route_scene_block_non_consent():
    with pytest.raises(BlockedContentError) as exc_info:
        route_scene("romantic_fade_to_black", _clean_score(non_consent=3))
    assert exc_info.value.dimension == "non_consent"


def test_route_scene_block_minors_adjacent():
    with pytest.raises(BlockedContentError) as exc_info:
        route_scene("action_combat", _clean_score(minors_adjacent=3))
    assert exc_info.value.dimension == "minors_adjacent"


def test_route_scene_block_threshold_not_reached():
    # nc=2 < 3 → no eccezione
    result = route_scene("action_combat", _clean_score(non_consent=2))
    assert "tier" in result


# ── route_scene — nsfw force (ollama) ────────────────────────────────────────

def test_route_scene_nsfw_force_ollama():
    result = route_scene("action_combat", _clean_score(explicit=2))  # >= nsfw_threshold=2
    assert result["provider"] == "ollama"
    assert "nsfw-forced" in result["rationale"]


def test_route_scene_nsfw_just_below_threshold():
    result = route_scene("action_combat", _clean_score(explicit=1))  # < 2
    # deve usare la matrice, non ollama forzato
    assert result["provider"] == "cerebras"


# ── route_scene — matrix lookup ───────────────────────────────────────────────

def test_route_scene_known_type_action_combat():
    result = route_scene("action_combat", _clean_score())
    assert result["tier"] == "cerebras_workhorse"
    assert result["provider"] == "cerebras"


def test_route_scene_known_type_ooc_meta():
    result = route_scene("ooc_meta", _clean_score())
    assert result["provider"] == "groq"


def test_route_scene_known_type_lore_exposition():
    result = route_scene("lore_exposition", _clean_score())
    assert result["provider"] == "openrouter"


def test_route_scene_unknown_type_falls_back_to_default():
    result = route_scene("unknown_scene_type_xyz", _clean_score())
    # default = cerebras_workhorse
    assert result["tier"] == DEFAULT_CONFIG["matrix"]["default"]["tier"]


# ── route_scene — char_relevance → lora_candidate ────────────────────────────

def test_route_scene_lora_candidate_high():
    result = route_scene("action_combat", _clean_score(), char_relevance="high")
    assert result.get("lora_candidate") is True


def test_route_scene_no_lora_candidate_low():
    result = route_scene("action_combat", _clean_score(), char_relevance="low")
    assert "lora_candidate" not in result


def test_route_scene_nsfw_force_lora_candidate():
    result = route_scene("action_combat", _clean_score(explicit=2), char_relevance="high")
    assert result.get("lora_candidate") is True


def test_route_scene_invalid_char_relevance():
    with pytest.raises(ValueError, match="char_relevance"):
        route_scene("action_combat", _clean_score(), char_relevance="medium")


# ── load_config ───────────────────────────────────────────────────────────────

def test_load_config_valid(tmp_path):
    cfg_data = {
        "matrix": {"default": {"tier": "t", "provider": "p", "model": "m"}},
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }
    cfg_path = tmp_path / "routing.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    cfg = load_config(str(cfg_path))
    assert cfg["nsfw_threshold"] == 2
    assert "default" in cfg["matrix"]


def test_load_config_missing_matrix_key(tmp_path):
    cfg_data = {
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
        # matrix mancante
    }
    cfg_path = tmp_path / "bad.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    with pytest.raises(ValueError, match="matrix"):
        load_config(str(cfg_path))


def test_load_config_missing_default_entry(tmp_path):
    cfg_data = {
        "matrix": {"action_combat": {"tier": "t", "provider": "p", "model": "m"}},
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }
    cfg_path = tmp_path / "nodefault.yaml"
    cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")
    with pytest.raises(ValueError, match="default"):
        load_config(str(cfg_path))


# ── coverage gaps: dispatch_to_tier + _call_* + main() ───────────────────────


@pytest.fixture()
def matrix_config():
    return {
        "matrix": {
            "t_cerebras": {"tier": "cerebras", "provider": "cerebras", "model": "m1"},
            "t_groq":     {"tier": "groq",     "provider": "groq",     "model": "m2"},
            "t_ollama":   {"tier": "ollama",   "provider": "ollama",   "model": "m3"},
            "t_claude":   {"tier": "claude",   "provider": "claude",   "model": "m4"},
            "default":    {"tier": "unknown",  "provider": "unknown",  "model": "m5"},
        },
        "nsfw_threshold": 2,
        "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
    }


def test_load_config_missing_block_threshold(tmp_path):
    """Line 59: block_thresholds senza 'non_consent'."""
    cfg = {
        "matrix": {"default": {"tier": "t", "provider": "p", "model": "m"}},
        "nsfw_threshold": 2,
        "block_thresholds": {"minors_adjacent": 3},
    }
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.dump(cfg), encoding="utf-8")
    with pytest.raises(ValueError, match="non_consent"):
        load_config(str(p))


def test_dispatch_to_tier_cerebras(matrix_config):
    with patch(f"{_MOD}._call_gateway", return_value="ok") as gw:
        res = dispatch_to_tier("cerebras", "prompt", config=matrix_config)
    assert res == "ok"
    assert gw.call_args[0][1] == "llm_code"


def test_dispatch_to_tier_groq(matrix_config):
    with patch(f"{_MOD}._call_gateway", return_value="ok") as gw:
        res = dispatch_to_tier("groq", "prompt", config=matrix_config)
    assert res == "ok"
    assert gw.call_args[0][1] == "llm_ask"


def test_dispatch_to_tier_ollama(matrix_config):
    with patch(f"{_MOD}._call_ollama", return_value="local"):
        res = dispatch_to_tier("ollama", "prompt", config=matrix_config)
    assert res == "local"


def test_dispatch_to_tier_ollama_retry(matrix_config):
    with patch(f"{_MOD}._call_ollama", side_effect=[OSError("fail"), "ok"]) as mo:
        res = dispatch_to_tier("ollama", "prompt", config=matrix_config)
    assert res == "ok"
    assert mo.call_count == 2


def test_dispatch_to_tier_ollama_all_fail(matrix_config):
    with patch(f"{_MOD}._call_ollama", side_effect=OSError("fail")):
        with pytest.raises(RuntimeError, match="All ollama models failed"):
            dispatch_to_tier("ollama", "prompt", config=matrix_config)


def test_dispatch_to_tier_claude(matrix_config):
    with patch(f"{_MOD}._call_claude_subprocess", return_value="claude_out"):
        res = dispatch_to_tier("claude", "prompt", config=matrix_config)
    assert res == "claude_out"


def test_dispatch_to_tier_unknown_provider(matrix_config):
    with pytest.raises(ValueError, match="Unknown provider"):
        dispatch_to_tier("nonexistent", "prompt", config=matrix_config)


def _mock_urlopen(body: dict):
    resp = MagicMock()
    resp.read.return_value = json.dumps(body).encode()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_call_gateway_success():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"content": "ok"})):
        res = _call_gateway("http://url", "llm_code", "cerebras", "p", 30, 3)
    assert res == "ok"


def test_call_gateway_retry():
    resp = _mock_urlopen({"content": "ok"})
    with patch("urllib.request.urlopen", side_effect=[OSError("fail"), resp]), \
         patch("time.sleep"):
        res = _call_gateway("http://url", "llm_code", "prov", "p", 30, 3)
    assert res == "ok"


def test_call_gateway_all_fail():
    with patch("urllib.request.urlopen", side_effect=OSError("fail")), \
         patch("time.sleep"):
        with pytest.raises(RuntimeError, match="Gateway call to"):
            _call_gateway("http://url", "llm_code", "prov", "p", 30, 3)


def test_call_ollama_success():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen({"response": "testo"})):
        res = _call_ollama("http://url", "model", "prompt", 30)
    assert res == "testo"


def test_call_claude_subprocess_success():
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "  result  "
    with patch("subprocess.run", return_value=mock_result):
        res = _call_claude_subprocess("prompt", "claude-opus", 30)
    assert res == "result"


def test_call_claude_subprocess_failure():
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "error message"
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="claude subprocess failed"):
            _call_claude_subprocess("prompt", "claude-opus", 30)


def test_main_config_load_fails_uses_default(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["route_scene.py", "--scene-type", "action_combat"])
    with patch(f"{_MOD}.load_config", side_effect=FileNotFoundError("no file")), \
         patch(f"{_MOD}.route_scene", return_value={"tier": "t", "rationale": "r"}):
        main()
    out = capsys.readouterr().out
    assert "tier" in out


def test_main_invalid_nsfw_json_exits_1(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["route_scene.py", "--nsfw-score", "{bad}"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "invalid JSON" in capsys.readouterr().err


def test_main_blocked_content_exits_2(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["route_scene.py"])
    with patch(f"{_MOD}.load_config", side_effect=FileNotFoundError()), \
         patch(f"{_MOD}.route_scene", side_effect=BlockedContentError("Blocked", "non_consent", 3)):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 2
    assert "BLOCKED" in capsys.readouterr().err


def test_main_success_prints_json(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["route_scene.py", "--scene-type", "ooc_meta"])
    with patch(f"{_MOD}.load_config", side_effect=FileNotFoundError()), \
         patch(f"{_MOD}.route_scene", return_value={"tier": "groq_fast", "rationale": "r"}):
        main()
    out = capsys.readouterr().out
    assert "groq_fast" in out


def test_main_speak_flag_prints_stub(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["route_scene.py", "--speak"])
    with patch(f"{_MOD}.load_config", side_effect=FileNotFoundError()), \
         patch(f"{_MOD}.route_scene", return_value={"tier": "t", "rationale": "speak rationale"}):
        main()
    err = capsys.readouterr().err
    assert "--speak stub" in err


def test_dispatch_to_tier_no_config_uses_default():
    """Line 146: config=None → DEFAULT_CONFIG usato internamente."""
    with patch(f"{_MOD}._call_gateway", return_value="ok"):
        res = dispatch_to_tier("cerebras_workhorse", "prompt")
    assert res == "ok"


def test_call_gateway_empty_content_retries():
    """Line 192: content vuoto → ValueError → retry → RuntimeError finale."""
    empty_resp = _mock_urlopen({"content": ""})
    with patch("urllib.request.urlopen", return_value=empty_resp), \
         patch("time.sleep"):
        with pytest.raises(RuntimeError, match="Gateway call to"):
            _call_gateway("http://url", "llm_code", "prov", "p", 30, 2)


def test_main_generic_exception_exits_1(monkeypatch, capsys):
    """Lines 265-267: route_scene lancia Exception generica → sys.exit(1)."""
    monkeypatch.setattr("sys.argv", ["route_scene.py"])
    with patch(f"{_MOD}.load_config", side_effect=FileNotFoundError()), \
         patch(f"{_MOD}.route_scene", side_effect=ValueError("generic error")):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
    assert "generic error" in capsys.readouterr().err
