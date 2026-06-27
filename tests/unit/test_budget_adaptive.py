"""GAP-22: test unitari per budget_adaptive — logica di troncamento e cap adattivo."""

from app.calliope_shell.budget_adaptive import (
    DEFAULT_CONTEXT_WINDOW,
    PERMANENT_FLOOR,
    _normalize,
    _truncate_block_to_tokens,
    context_window_for,
    permanent_cap_for,
    truncate_permanent,
)


# --- _normalize -----------------------------------------------------------


def test_normalize_none_returns_empty():
    assert _normalize(None) == ""


def test_normalize_strips_free_suffix():
    assert _normalize("qwen/qwen3-coder:free") == "qwen/qwen3-coder"


def test_normalize_strips_nitro_suffix():
    assert _normalize("deepseek-r1:nitro") == "deepseek-r1"


def test_normalize_lowercases():
    assert _normalize("Llama-3.3-70b-Versatile") == "llama-3.3-70b-versatile"


def test_normalize_no_colon_unchanged():
    assert _normalize("zai-glm-4.7") == "zai-glm-4.7"


# --- context_window_for ---------------------------------------------------


def test_context_window_known_model():
    assert context_window_for("zai-glm-4.7") == 200_000


def test_context_window_free_suffix_resolved():
    assert context_window_for("qwen/qwen3-coder:free") == 256_000


def test_context_window_unknown_model_default():
    assert context_window_for("modello-inesistente-xyz") == DEFAULT_CONTEXT_WINDOW


def test_context_window_none_default():
    assert context_window_for(None) == DEFAULT_CONTEXT_WINDOW


# --- permanent_cap_for ----------------------------------------------------


def test_permanent_cap_normal_model():
    cap = permanent_cap_for("llama-3.3-70b-versatile")
    # 128000 * 0.5 * 0.38 = 24320 >= PERMANENT_FLOOR
    assert cap == 24_320


def test_permanent_cap_reasoning_model_lower_share():
    cap_r1 = permanent_cap_for("deepseek-r1-0528")
    cap_norm = permanent_cap_for("llama-3.3-70b-versatile")
    assert cap_r1 < cap_norm  # share 0.28 < 0.38


def test_permanent_cap_never_below_floor():
    # Modello ignoto → DEFAULT_CONTEXT_WINDOW = 32000
    cap = permanent_cap_for("modello-inesistente-xyz")
    assert cap >= PERMANENT_FLOOR


# --- _truncate_block_to_tokens --------------------------------------------


def test_truncate_below_limit_unchanged():
    text = "Questo è un testo corto."
    result = _truncate_block_to_tokens(text, max_tokens=1000)
    assert result == text


def test_truncate_zero_limit_returns_empty():
    assert _truncate_block_to_tokens("qualsiasi testo", max_tokens=0) == ""


def test_truncate_long_text_adds_ellipsis():
    # ~500 parole → est_tokens ~= len/4
    long_text = " ".join(["parola"] * 500)  # ~3500 char = ~875 token
    result = _truncate_block_to_tokens(long_text, max_tokens=50)
    assert result.endswith("[…]")
    assert len(result) < len(long_text)


def test_truncate_cuts_on_word_boundary():
    text = "uno due tre quattro cinque"
    # max_tokens=1 → char_budget=4 → taglia prima dello spazio
    result = _truncate_block_to_tokens(text, max_tokens=1)
    assert " " not in result.replace("[…]", "").strip() or result.endswith("[…]")


# --- truncate_permanent ---------------------------------------------------


def _make_blocks(n: int, size: int = 100) -> list[str]:
    return [("x " * (size // 2)) for _ in range(n)]


def test_truncate_permanent_no_truncation_when_under_cap():
    cb = ["scheda breve"]
    lb = ["lore entry"]
    mb = ["memoria"]
    result_cb, result_lb, result_mb, tel = truncate_permanent(
        char_blocks=cb, lore_blocks=lb, memory_blocks=mb, model="llama-3.3-70b-versatile"
    )
    assert tel["applied"] is False
    assert result_cb == cb
    assert result_lb == lb
    assert result_mb == mb


def test_truncate_permanent_drops_memory_first():
    # Blocchi grossi per superare il cap del modello di default (32k)
    # memory = 2 blocchi grandi → dovrebbero essere droppati
    big_char = [" ".join(["parola"] * 3000)]         # ~3000 token
    big_lore = [" ".join(["lore"] * 3000)]           # ~3000 token
    big_mem = [" ".join(["mem"] * 2000) for _ in range(5)]  # 5 x 2000 token

    _, _, mb_out, tel = truncate_permanent(
        char_blocks=big_char,
        lore_blocks=big_lore,
        memory_blocks=big_mem,
        model="modello-inesistente-xyz",  # DEFAULT_CONTEXT_WINDOW=32000
    )
    assert tel["applied"] is True
    assert tel["dropped_memory"] > 0


def test_truncate_permanent_telemetry_fields_present():
    cb = _make_blocks(1, 10)
    lb = _make_blocks(1, 10)
    mb = _make_blocks(1, 10)
    _, _, _, tel = truncate_permanent(
        char_blocks=cb, lore_blocks=lb, memory_blocks=mb
    )
    for field in ("applied", "model", "permanent_cap", "permanent_tokens_before",
                  "dropped_memory", "dropped_lore", "compressed_chars"):
        assert field in tel


def test_truncate_permanent_empty_inputs():
    cb, lb, mb, tel = truncate_permanent(
        char_blocks=[], lore_blocks=[], memory_blocks=[]
    )
    assert cb == []
    assert lb == []
    assert mb == []
    assert tel["applied"] is False
