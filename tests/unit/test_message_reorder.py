import unittest

from app.db.messages import (
    Base,
    engine,
    SessionLocal,
    Scene,
    Character,
    add_message,
    list_messages_for_scene,
    move_message,
)


class TestMessageReorder(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(engine)
        self.session = SessionLocal()

    def tearDown(self):
        self.session.close()
        Base.metadata.drop_all(engine)

    def test_move_message_rebalance(self):
        session = self.session

        # Crea Scene e Character
        scene = Scene(name="Test Scene")
        character = Character(name="Test Character")
        session.add(scene)
        session.add(character)
        session.commit()

        # Inserisci 3 messaggi A, B, C con posizioni 1, 2, 3
        # Non assegniamo il risultato per A e B perché non ci serve
        add_message(session, scene.id, character.id, "A", 1)
        add_message(session, scene.id, character.id, "B", 2)
        # Assegniamo l'ID di C per usarlo nel test
        msg_c_id = add_message(session, scene.id, character.id, "C", 3)

        # Sposta il messaggio C alla posizione 1
        result = move_message(session, msg_c_id, 1)
        self.assertTrue(result)

        # Recupera i messaggi e verifica l'ordinamento
        messages = list_messages_for_scene(session, scene.id)
        contents = [m.content for m in messages]
        positions = [m.position_order for m in messages]

        # Verifica che l'ordine dei contenuti sia C, A, B
        self.assertEqual(contents, ["C", "A", "B"])
        # Verifica che le posizioni siano 1, 2, 3 contigue
        self.assertEqual(positions, [1, 2, 3])
