"""MASCOT-SWITCH regression: mascot.js ha fallback a mao quando il modello richiesto manca."""
from __future__ import annotations
from pathlib import Path


def _mascot_js() -> str:
    return (Path(__file__).parents[2]
            / "app/calliope_shell/static/js/mascot.js").read_text()


def test_fallback_to_mao_on_load_failure():
    js = _mascot_js()
    assert "fallback a mao" in js, "deve contenere messaggio di fallback mao"
    assert "key !== 'mao'" in js, "deve controllare se il modello non e' gia' mao"


def test_unknown_model_returns_mao_via_selected():
    js = _mascot_js()
    assert "MASCOT_MODELS[q]" in js, "selectedModelKey deve validare il parametro ?model= vs registry"
    assert "return 'mao'" in js, "selectedModelKey deve fare fallback a mao se chiave sconosciuta"


def test_console_warn_on_model_load_failure():
    js = _mascot_js()
    assert "[mascot] model" in js and "failed to load" in js, (
        "deve loggare warning con il nome modello fallito"
    )
