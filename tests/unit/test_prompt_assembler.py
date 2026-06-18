"""GAP-23: test unitari per prompt_assembler — funzioni pure e assemble."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.prompt_assembler import (
    DEFAULT_SYSTEM_BASE,
    AssembledContext,
    _card_block,
    _render_prompt,
    assemble,
    post_history_from_cards,
    system_from_cards,
)


def _card(name="Aria", description="", personality="", scenario="",
          mes_example="", system_prompt="", post_history="",
          speech=None, backstory=""):
    ext = {}
    if speech is not None:
        ext["speech_pattern"] = speech
    if backstory:
        ext["backstory"] = backstory
    return {
        "data": {
            "name": name,
            "description": description,
            "personality": personality,
            "scenario": scenario,
            "mes_example": mes_example,
            "system_prompt": system_prompt,
            "post_history_instructions": post_history,
            "extensions": {"calliope": ext},
        }
    }


# --- _card_block ----------------------------------------------------------


def test_card_block_name_header():
    block = _card_block(_card("Aria"))
    assert block.startswith("[Aria]")


def test_card_block_description_included():
    block = _card_block(_card("Aria", description="Una guerriera"))
    assert "Una guerriera" in block


def test_card_block_speech_dict_formatted():
    block = _card_block(_card("Aria", speech={"tone": "brusco", "pace": "lento"}))
    assert "Speech:" in block
    assert "brusco" in block


def test_card_block_speech_string():
    block = _card_block(_card("Aria", speech="parla in rima"))
    assert "Speech: parla in rima" in block


def test_card_block_minimal_card_no_empty_lines():
    block = _card_block(_card("Mao"))
    assert block.strip() == "[Mao]"


def test_card_block_mes_example():
    block = _card_block(_card("Mao", mes_example="Mao: Ciao\nUser: Ciao"))
    assert "Example dialogue:" in block


# --- system_from_cards ----------------------------------------------------


def test_system_from_cards_base_always_present():
    result = system_from_cards([])
    assert DEFAULT_SYSTEM_BASE in result


def test_system_from_cards_appends_system_prompts():
    cards = [_card("A", system_prompt="Sei gentile"), _card("B", system_prompt="Sei forte")]
    result = system_from_cards(cards)
    assert "Sei gentile" in result
    assert "Sei forte" in result


def test_system_from_cards_empty_system_prompt_skipped():
    cards = [_card("A", system_prompt=""), _card("B", system_prompt="  ")]
    result = system_from_cards(cards)
    assert result == DEFAULT_SYSTEM_BASE


# --- post_history_from_cards ----------------------------------------------


def test_post_history_from_empty_cards():
    assert post_history_from_cards([]) == ""


def test_post_history_concatenates_non_empty():
    cards = [_card("A", post_history="Ricorda: tema oscuro"),
             _card("B", post_history="Tono poetico")]
    result = post_history_from_cards(cards)
    assert "tema oscuro" in result
    assert "Tono poetico" in result


# --- _render_prompt -------------------------------------------------------


def test_render_prompt_system_first():
    prompt = _render_prompt(
        system="SYSTEM", char_blocks=[], lore_blocks=[], memory_blocks=[],
        history="", post_history="", user_text="", verb_instruction="",
    )
    assert prompt.startswith("SYSTEM")


def test_render_prompt_sections_order():
    prompt = _render_prompt(
        system="SYS",
        char_blocks=["[CHAR]"],
        lore_blocks=["LORE1"],
        memory_blocks=["MEM1"],
        history="HIST",
        post_history="POST",
        user_text="USER",
        verb_instruction="VERB",
    )
    positions = {k: prompt.index(k) for k in ["SYS", "CHAR", "LORE", "MEM", "HIST", "POST", "USER", "VERB"]}
    assert positions["SYS"] < positions["CHAR"] < positions["LORE"]
    assert positions["LORE"] < positions["MEM"] < positions["HIST"]
    assert positions["HIST"] < positions["POST"] < positions["USER"]
    assert positions["USER"] < positions["VERB"]


def test_render_prompt_empty_sections_omitted():
    prompt = _render_prompt(
        system="SYS", char_blocks=[], lore_blocks=[], memory_blocks=[],
        history="", post_history="", user_text="USER", verb_instruction="",
    )
    assert "CHARACTERS" not in prompt
    assert "USER" in prompt


# --- assemble (con card iniettate, senza DB) ------------------------------


def test_assemble_returns_assembled_context():
    ctx = assemble(
        conn=None,
        cards=[_card("Aurora", description="guerriera")],
        history="Aurora: Eccomi.",
        user_text="Continua la scena.",
        lore_blocks=["Il tempio è antico."],
        memory_blocks=[],
        verb_instruction="Write the next beat.",
        apply_budget=False,
    )
    assert isinstance(ctx, AssembledContext)
    assert "Aurora" in ctx.full_prompt
    assert "CHARACTERS" in ctx.full_prompt
    assert "LORE" in ctx.full_prompt


def test_assemble_meta_fields():
    ctx = assemble(
        conn=None,
        cards=[_card("A"), _card("B")],
        lore_blocks=["lore1", "lore2"],
        apply_budget=False,
    )
    assert ctx.meta["active_chars"] == 2
    assert ctx.meta["lore_blocks"] == 2


def test_assemble_apply_budget_false_skips_truncation():
    ctx = assemble(conn=None, cards=[], apply_budget=False)
    assert ctx.truncation == {"applied": False}


def test_assemble_collect_active_cards_skips_missing(tmp_path):
    from app.db import get_db, init_schema
    conn = get_db(str(tmp_path / "test.db"))
    init_schema(conn)
    ctx = assemble(
        conn=conn,
        active_char_names=["NomeInesistente"],
        apply_budget=False,
    )
    assert ctx.meta["active_chars"] == 0
    conn.close()


def test_assemble_active_char_names_loads_from_db(tmp_path):
    import json as _json
    from app.db import get_db, init_schema, new_id
    conn = get_db(str(tmp_path / "test.db"))
    init_schema(conn)
    card_json = _json.dumps({
        "spec": "chara_card_v2",
        "spec_version": "2.0",
        "data": {"name": "Aurora", "description": "guerriera"},
    })
    conn.execute(
        "INSERT INTO characters (id, name, kind, card_json) VALUES (?, ?, ?, ?)",
        (new_id(), "Aurora", "npc", card_json),
    )
    conn.commit()
    ctx = assemble(
        conn=conn,
        active_char_names=["Aurora"],
        apply_budget=False,
    )
    conn.close()
    assert ctx.meta["active_chars"] == 1
    assert "Aurora" in ctx.full_prompt
