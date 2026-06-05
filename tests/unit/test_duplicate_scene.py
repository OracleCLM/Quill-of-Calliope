from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.messages import (
    Base,
    Scene,
    Character,
    duplicate_scene,
    add_message,
    list_messages_for_scene,
)

# Configurazione del database in memoria per i test
engine = create_engine("sqlite:///:memory:", future=True)
Base.metadata.create_all(engine)
TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_duplicate_scene_creates_new_scene_with_messages():
    session = TestSessionLocal()

    # Crea scena sorgente e personaggio
    src_scene = Scene(name="Scena Originale")
    char = Character(name="Eroe")
    session.add(src_scene)
    session.add(char)
    session.commit()

    # Aggiungi messaggi alla scena sorgente
    add_message(session, src_scene.id, char.id, "L1", 1)
    add_message(session, src_scene.id, char.id, "L2", 2)
    add_message(session, src_scene.id, char.id, "L3", 3)

    # Esegui la duplicazione
    new_scene_id = duplicate_scene(session, src_scene.id, "Variante")

    # Verifica che la nuova scena esista con il nome corretto
    new_scene = session.get(Scene, new_scene_id)
    assert new_scene is not None
    assert new_scene.name == "Variante"

    # Verifica che i messaggi siano stati copiati correttamente
    new_messages = list_messages_for_scene(session, new_scene_id)
    assert len(new_messages) == 3
    assert [m.content for m in new_messages] == ["L1", "L2", "L3"]
    assert [m.position_order for m in new_messages] == [1, 2, 3]

    # Verifica che gli ID dei messaggi siano diversi (clone reale)
    src_messages = list_messages_for_scene(session, src_scene.id)
    src_ids = {m.id for m in src_messages}
    new_ids = {m.id for m in new_messages}
    assert src_ids.isdisjoint(new_ids)

    # Verifica che la scena sorgente sia intatta
    assert len(src_messages) == 3

    session.close()


def test_duplicate_scene_non_existent_source_creates_empty_scene():
    session = TestSessionLocal()

    # Tenta di duplicare una scena che non esiste
    fake_id = "nonexistent"
    new_scene_id = duplicate_scene(session, fake_id, "Vuota")

    # Verifica che la scena sia stata creata vuota
    new_scene = session.get(Scene, new_scene_id)
    assert new_scene is not None
    assert new_scene.name == "Vuota"

    new_messages = list_messages_for_scene(session, new_scene_id)
    assert len(new_messages) == 0

    session.close()
