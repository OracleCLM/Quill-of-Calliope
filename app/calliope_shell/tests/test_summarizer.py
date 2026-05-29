import pytest

from app.calliope_shell.summarizer import (
    default_summarizer,
    summarize_range,
    compress_history,
    apply_ghosting,
    CompressionResult,
)
from app.calliope_shell.scene_model import SceneChat, SceneMessage


def msgs(n):
    """Crea una lista di n messaggi di esempio."""
    return [
        SceneMessage(
            author="Aria",
            content=f"Event {i}. Detail one. Detail two."
        )
        for i in range(n)
    ]


def scene(n):
    """Crea una scena con n messaggi."""
    return SceneChat(
        id="s1",
        name="T",
        members=["Aria"],
        directive="Goal",
        messages=msgs(n)
    )


@pytest.mark.unit
def test_default_summarizer_prefix_and_bounded():
    text = "A. B. C. D."
    first = default_summarizer(text)
    second = default_summarizer(text)

    # Deve iniziare con il prefisso corretto
    assert first.startswith("Summary:")

    # Lunghezza massima (incluso prefisso) intorno ai 220 caratteri
    assert len(first) <= 220

    # Deterministico: due chiamate con lo stesso input restituiscono lo stesso output
    assert first == second


@pytest.mark.unit
def test_summarize_range_uses_injected_fn():
    # Funzione fittizia che restituisce la lunghezza del testo ricevuto
    def fake_fn(t):
        return f"FAKE:{len(t)}"
    result = summarize_range(msgs(6), summarizer_fn=fake_fn)

    assert result.startswith("FAKE:")


@pytest.mark.unit
def test_summarize_range_default():
    result = summarize_range(msgs(4))  # usa il summarizer di default

    # Deve restituire una stringa non vuota che inizia con il prefisso
    assert result
    assert result.startswith("Summary:")


@pytest.mark.unit
def test_compress_history_per_range():
    sc = scene(20)
    cr = compress_history(sc, keep_recent_n=6, range_size=6)

    # Verifica i messaggi mantenuti
    assert isinstance(cr, CompressionResult)
    assert len(cr.kept) == 6

    # Messaggi compressi
    assert cr.ghosted_count == 14

    # Numero di blocchi di riassunto (14 vecchi -> 6,6,2)
    assert len(cr.summaries) == 3

    # La scena originale non deve essere mutata
    assert all(not m.ghost for m in sc.messages)


@pytest.mark.unit
def test_apply_ghosting_immutable():
    sc = scene(10)
    g = apply_ghosting(sc, keep_recent_n=4)

    # Il risultato deve contenere 6 messaggi ghosted e 4 non ghosted
    ghosted = [m for m in g.messages if m.ghost]
    non_ghosted = [m for m in g.messages if not m.ghost]
    assert len(ghosted) == 6
    assert len(non_ghosted) == 4

    # La scena originale deve rimanere intatta (tutti i messaggi non ghost)
    assert all(not m.ghost for m in sc.messages)
