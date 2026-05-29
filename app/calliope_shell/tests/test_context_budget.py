import pytest

from app.calliope_shell.context_budget import (
    assemble_context,
    est_tokens,
)
from app.calliope_shell.scene_model import SceneChat, SceneMessage, CharacterCard


def make_scene(n: int, body: str = "msg "):
    """
    Crea una scena con ``n`` messaggi di contenuto ``body`` + indice.
    Un solo membro (Aria) è presente nella lista ``members``.
    """
    msgs = [
        SceneMessage(author="Aria", content=f"{body}{i}")
        for i in range(n)
    ]
    return SceneChat(
        id="s1",
        name="T",
        members=["Aria"],
        directive="Reach the castle",
        messages=msgs,
    )


# Card di esempio per il membro "Aria"
cards = {"Aria": CharacterCard(name="Aria", personality="brave knight")}


@pytest.mark.unit
def test_est_tokens_positive():
    # Un testo vuoto deve restituire almeno 1 token (funzione garantita)
    assert est_tokens("") >= 1

    # 40 caratteri dovrebbero produrre circa 10 token (4 caratteri per token)
    tokens = est_tokens("x" * 40)
    assert 8 <= tokens <= 12


@pytest.mark.unit
def test_directive_last_and_permanent_present():
    scene = make_scene(10)
    bundle = assemble_context(
        scene,
        cards,
        model_window=2000,
        reply_reserve=500,
        system_prompt="Narr",
    )

    # Il primo blocco deve essere di tipo "system"
    assert bundle.blocks[0].kind == "system"

    # Deve esserci almeno un blocco di tipo "card"
    assert any(b.kind == "card" for b in bundle.blocks)

    # L'ultimo blocco deve essere di tipo "directive"
    assert bundle.blocks[-1].kind == "directive"


@pytest.mark.unit
def test_budget_respected():
    scene = make_scene(10)
    bundle = assemble_context(
        scene,
        cards,
        model_window=2000,
        reply_reserve=500,
        system_prompt="Narr",
    )

    # Il token estimate totale non deve superare la finestra del modello
    assert bundle.token_estimate <= bundle.meter["window"]

    # Il dizionario meter deve contenere tutte le chiavi richieste
    expected_keys = {
        "window",
        "reply_reserve",
        "permanent_tokens",
        "history_tokens",
        "free_tokens",
    }
    assert expected_keys.issubset(set(bundle.meter.keys()))


@pytest.mark.unit
def test_ghosting_under_tight_budget():
    # Messaggi lunghi per forzare il superamento del budget
    scene = make_scene(
        40,
        body="a fairly long message body " * 3,
    )
    bundle = assemble_context(
        scene,
        cards,
        model_window=300,
        reply_reserve=100,
        system_prompt="Narr",
    )

    # Deve esserci almeno un ghost block
    assert bundle.ghosted_count > 0
    assert any(b.kind == "ghost" for b in bundle.blocks)

    # Il numero di blocchi di tipo "message" deve essere inferiore al totale dei messaggi
    message_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(message_blocks) < len(scene.messages)

    # Il blocco directive deve rimanere l'ultimo
    assert bundle.blocks[-1].kind == "directive"


@pytest.mark.unit
def test_no_ghost_when_fits():
    scene = make_scene(3)
    bundle = assemble_context(
        scene,
        cards,
        model_window=4000,
        reply_reserve=500,
        system_prompt="Narr",
    )

    # Nessun messaggio dovrebbe essere ghosted
    assert bundle.ghosted_count == 0
    assert not any(b.kind == "ghost" for b in bundle.blocks)
