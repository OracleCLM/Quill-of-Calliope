"""GAP-35: test unitari per context_budget — est_tokens, assemble_context, ContextBundle."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.context_budget import ContextBundle, assemble_context, est_tokens
from app.calliope_shell.scene_model import CharacterCard, SceneChat, SceneMessage


# ── Helpers ──────────────────────────────────────────────────────────────────

def _scene(members=None, messages=None, directive=""):
    return SceneChat(
        id="s1",
        name="Test",
        members=members or [],
        messages=messages or [],
        directive=directive,
    )


def _msg(author, content, ghost=False):
    return SceneMessage(author=author, content=content, ghost=ghost)


def _card(name, personality="breve") -> CharacterCard:
    return CharacterCard(name=name, personality=personality)


# ── est_tokens ───────────────────────────────────────────────────────────────


def test_est_tokens_empty_returns_one():
    assert est_tokens("") == 1


def test_est_tokens_four_chars_returns_one():
    assert est_tokens("abcd") == 1


def test_est_tokens_approx_divided_by_four():
    assert est_tokens("a" * 400) == 100


# ── assemble_context — bundle type ───────────────────────────────────────────


def test_returns_context_bundle():
    bundle = assemble_context(_scene(), {}, model_window=4096, reply_reserve=512)
    assert isinstance(bundle, ContextBundle)


# ── system prompt block ───────────────────────────────────────────────────────


def test_system_prompt_block_included():
    bundle = assemble_context(
        _scene(), {}, model_window=4096, reply_reserve=512,
        system_prompt="Sei un narratore."
    )
    kinds = [b.kind for b in bundle.blocks]
    assert "system" in kinds


def test_system_prompt_block_first():
    bundle = assemble_context(
        _scene(), {}, model_window=4096, reply_reserve=512,
        system_prompt="Sei un narratore."
    )
    assert bundle.blocks[0].kind == "system"


def test_no_system_prompt_no_system_block():
    bundle = assemble_context(_scene(), {}, model_window=4096, reply_reserve=512)
    kinds = [b.kind for b in bundle.blocks]
    assert "system" not in kinds


# ── card blocks ───────────────────────────────────────────────────────────────


def test_card_block_for_member():
    scene = _scene(members=["Aurora"])
    cards = {"Aurora": _card("Aurora", personality="guerriera")}
    bundle = assemble_context(scene, cards, model_window=4096, reply_reserve=512)
    card_blocks = [b for b in bundle.blocks if b.kind == "card"]
    assert len(card_blocks) == 1
    assert card_blocks[0].label == "Aurora"


def test_no_card_for_absent_member():
    scene = _scene(members=["Aurora"])
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    card_blocks = [b for b in bundle.blocks if b.kind == "card"]
    assert card_blocks == []


def test_two_members_two_card_blocks():
    scene = _scene(members=["Aurora", "Koko"])
    cards = {"Aurora": _card("Aurora"), "Koko": _card("Koko")}
    bundle = assemble_context(scene, cards, model_window=4096, reply_reserve=512)
    card_blocks = [b for b in bundle.blocks if b.kind == "card"]
    assert len(card_blocks) == 2


# ── directive block ───────────────────────────────────────────────────────────


def test_directive_block_last():
    scene = _scene(directive="Scrivi in terza persona.")
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    assert bundle.blocks[-1].kind == "directive"
    assert "terza persona" in bundle.blocks[-1].text


def test_no_directive_no_directive_block():
    bundle = assemble_context(_scene(), {}, model_window=4096, reply_reserve=512)
    kinds = [b.kind for b in bundle.blocks]
    assert "directive" not in kinds


# ── lore entries ──────────────────────────────────────────────────────────────


def test_lore_blocks_included():
    lore = [{"content": "Il castello è antico."}, {"content": "La foresta è magica."}]
    bundle = assemble_context(_scene(), {}, model_window=4096, reply_reserve=512, lore_entries=lore)
    lore_blocks = [b for b in bundle.blocks if b.kind == "lore"]
    assert len(lore_blocks) == 2


def test_lore_budget_cap():
    big_lore = [{"content": "x" * 400}] * 20
    bundle = assemble_context(
        _scene(), {}, model_window=4096, reply_reserve=512,
        lore_entries=big_lore, lore_cap_frac=0.10
    )
    lore_blocks = [b for b in bundle.blocks if b.kind == "lore"]
    assert len(lore_blocks) < 20


# ── message blocks ────────────────────────────────────────────────────────────


def test_message_blocks_included():
    scene = _scene(messages=[_msg("A", "ciao"), _msg("B", "salve")])
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(msg_blocks) == 2


def test_ghost_messages_excluded():
    scene = _scene(messages=[_msg("A", "vecchio", ghost=True), _msg("B", "nuovo")])
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(msg_blocks) == 1
    assert msg_blocks[0].label == "B"


def test_messages_chronological_order():
    msgs = [_msg(f"C{i}", f"msg{i}") for i in range(5)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert msg_blocks[0].text == "msg0"
    assert msg_blocks[-1].text == "msg4"


# ── ghost block ───────────────────────────────────────────────────────────────


def test_ghost_block_when_messages_cut():
    msgs = [_msg("C", f"{'x'*200}") for _ in range(20)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(scene, {}, model_window=512, reply_reserve=128)
    kinds = [b.kind for b in bundle.blocks]
    assert "ghost" in kinds


def test_ghosted_count_correct():
    msgs = [_msg("C", f"{'x'*200}") for _ in range(20)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(scene, {}, model_window=512, reply_reserve=128)
    assert bundle.ghosted_count > 0


def test_no_ghost_block_when_all_fit():
    msgs = [_msg("C", "breve") for _ in range(3)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(scene, {}, model_window=8192, reply_reserve=512)
    kinds = [b.kind for b in bundle.blocks]
    assert "ghost" not in kinds
    assert bundle.ghosted_count == 0


# ── recent_verbatim_min guarantee ────────────────────────────────────────────


def test_recent_verbatim_min_always_included():
    msgs = [_msg("C", "x" * 800) for _ in range(10)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(
        scene, {}, model_window=256, reply_reserve=64,
        recent_verbatim_min=4
    )
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(msg_blocks) >= 4


# ── meter fields ──────────────────────────────────────────────────────────────


def test_meter_has_required_keys():
    bundle = assemble_context(_scene(), {}, model_window=4096, reply_reserve=512)
    for key in ("window", "reply_reserve", "permanent_tokens", "history_tokens", "free_tokens"):
        assert key in bundle.meter


def test_meter_window_equals_model_window():
    bundle = assemble_context(_scene(), {}, model_window=8192, reply_reserve=1024)
    assert bundle.meter["window"] == 8192


def test_meter_free_tokens_non_negative():
    msgs = [_msg("C", "x" * 1000) for _ in range(50)]
    scene = _scene(messages=msgs)
    bundle = assemble_context(scene, {}, model_window=512, reply_reserve=128)
    assert bundle.meter["free_tokens"] >= 0


# ── block order: system → cards → lore → ghost → messages → directive ────────


def test_block_order_full_pipeline():
    scene = _scene(
        members=["Aurora"],
        messages=[_msg("Aurora", "testo"), _msg("Koko", "risposta")],
        directive="Continua.",
    )
    cards = {"Aurora": _card("Aurora")}
    lore = [{"content": "Storia del regno."}]
    bundle = assemble_context(
        scene, cards, model_window=8192, reply_reserve=512,
        system_prompt="Sei un narratore.", lore_entries=lore
    )
    kinds = [b.kind for b in bundle.blocks]
    order = [(k, kinds.index(k)) for k in ("system", "card", "lore", "message", "directive") if k in kinds]
    indices = [v for _, v in order]
    assert indices == sorted(indices)
