from __future__ import annotations

from typing import List

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from app.db import new_id

# ----------------------------------------------------------------------
# Database setup (in‑memory SQLite – sufficiente per i test unitari)
# ----------------------------------------------------------------------
engine = create_engine("sqlite:///:memory:", future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# ----------------------------------------------------------------------
# Modelli ORM
# ----------------------------------------------------------------------
class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String, nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    scene_id: Mapped[str] = mapped_column(
        String, ForeignKey("scenes.id"), nullable=False, index=True
    )
    character_id: Mapped[str] = mapped_column(
        String, ForeignKey("characters.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    position_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Relazioni opzionali (non strettamente necessarie per i test)
    scene: Mapped[Scene] = relationship("Scene", lazy="joined")
    character: Mapped[Character] = relationship("Character", lazy="joined")


# ----------------------------------------------------------------------
# Funzioni di utilità
# ----------------------------------------------------------------------
def add_message(
    session: Session,
    scene_id: str,
    character_id: str,
    content: str,
    position_order: int,
) -> str:
    """
    Inserisce un nuovo messaggio nella tabella ``messages`` e restituisce il suo ``id``.
    """
    msg = Message(
        scene_id=scene_id,
        character_id=character_id,
        content=content,
        position_order=position_order,
    )
    session.add(msg)
    session.commit()
    return msg.id


def insert_message_at(
    session: Session,
    scene_id: str,
    character_id: str,
    content: str,
    position: int,
) -> str:
    """
    Inserisce un nuovo messaggio alla posizione specificata.
    Sposta in avanti (position_order + 1) i messaggi esistenti
    con position_order >= position per evitare collisioni.
    Ritorna l'id del nuovo messaggio.
    """
    session.query(Message).filter(
        Message.scene_id == scene_id, Message.position_order >= position
    ).update({Message.position_order: Message.position_order + 1})

    msg = Message(
        scene_id=scene_id,
        character_id=character_id,
        content=content,
        position_order=position,
    )
    session.add(msg)
    session.commit()
    return msg.id


def list_messages_for_scene(session: Session, scene_id: str) -> List[Message]:
    """
    Restituisce tutti i messaggi associati a ``scene_id`` ordinati per ``position_order``.
    """
    return (
        session.query(Message)
        .filter(Message.scene_id == scene_id)
        .order_by(Message.position_order)
        .all()
    )

def count_messages_for_scene(session: Session, scene_id: str) -> int:
    """
    Restituisce il numero di messaggi associati a ``scene_id``.
    """
    return (
        session.query(Message)
        .filter(Message.scene_id == scene_id)
        .count()
    )

def get_message_by_id(session: Session, message_id: str) -> Message | None:
    """
    Restituisce il messaggio con l'ID specificato o None se non trovato.
    """
    return session.query(Message).filter(Message.id == message_id).first()

def get_scene_message_page(
    session: Session,
    scene_id: str,
    limit: int,
    offset: int = 0
) -> dict:
    """
    Restituisce una pagina paginata dei messaggi per uno scenario come un dizionario semplice.
    """
    total = count_messages_for_scene(session, scene_id)
    rows = (
        session.query(Message)
        .filter(Message.scene_id == scene_id)
        .order_by(Message.position_order)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        'messages': rows,
        'total': total,
        'limit': limit,
        'offset': offset,
        'has_more': (offset + len(rows)) < total
    }

def delete_message(session: Session, message_id: str) -> bool:
    """
    Elimina il messaggio con l'ID specificato.
    """
    msg = get_message_by_id(session, message_id)
    if msg:
        session.delete(msg)
        session.commit()
        return True
    else:
        return False

def move_message(session: Session, message_id: str, new_position: int) -> bool:
    """
    Sposta il messaggio identificato da message_id alla posizione new_position
    all'interno della sua scena e ribilancia il position_order di tutti gli altri
    messaggi affinché le posizioni siano una sequenza contigua 1..N.
    Ritorna False se message_id non esiste; True dopo aver fatto session.commit().
    """
    msg = get_message_by_id(session, message_id)
    if not msg:
        return False

    # Recupera tutti i messaggi della scena ordinati per posizione corrente
    messages = list_messages_for_scene(session, msg.scene_id)

    # Rimuovi il messaggio target dalla lista (in memoria)
    other_messages = [m for m in messages if m.id != msg.id]

    # Calcola l'indice di inserimento (gestisce posizioni fuori range)
    # new_position è 1-based, l'indice della lista è 0-based
    insert_index = new_position - 1
    if insert_index < 0:
        insert_index = 0
    if insert_index > len(other_messages):
        insert_index = len(other_messages)

    # Inserisci il messaggio target nella nuova posizione
    other_messages.insert(insert_index, msg)

    # Aggiorna position_order per tutta la lista (ribilanciamento)
    for i, m in enumerate(other_messages):
        m.position_order = i + 1

    session.commit()
    return True

def compact_scene_positions(session: Session, scene_id: str) -> int:
    """
    Rinumera il position_order di tutti i messaggi della scena a una sequenza
    contigua 1..N preservando l'ordine corrente.
    Ritorna il numero di messaggi rinumerati.
    """
    messages = (
        session.query(Message)
        .filter(Message.scene_id == scene_id)
        .order_by(Message.position_order)
        .all()
    )
    for i, msg in enumerate(messages):
        msg.position_order = i + 1
    session.commit()
    return len(messages)

def move_message_to_scene(session: Session, message_id: str, target_scene_id: str, new_position: int) -> bool:
    """
    Sposta il messaggio message_id in un'ALTRA scena target_scene_id, inserendolo alla posizione 1-based new_position.
    """
    msg = get_message_by_id(session, message_id)
    if not msg:
        return False

    if msg.scene_id == target_scene_id:
        return move_message(session, message_id, new_position)

    # Clamp new_position
    target_count = count_messages_for_scene(session, target_scene_id)
    if new_position < 1:
        new_position = 1
    elif new_position > target_count + 1:
        new_position = target_count + 1

    # Shift target scene messages
    session.query(Message).filter(
        Message.scene_id == target_scene_id,
        Message.position_order >= new_position
    ).update({Message.position_order: Message.position_order + 1}, synchronize_session="fetch")

    # Update moved message
    original_scene_id = msg.scene_id
    msg.scene_id = target_scene_id
    msg.position_order = new_position

    # Compact source scene
    compact_scene_positions(session, original_scene_id)

    session.commit()
    return True

def duplicate_scene(session: Session, scene_id: str, new_name: str) -> str:
    """
    Clona una scena esistente creando una nuova Scene con new_name.
    Copia tutti i messaggi della scena sorgente nella nuova scena,
    preservando il contenuto, il character_id e l'ordine (position_order).
    Genera nuovi ID per la scena e per i messaggi.
    """
    new_scene = Scene(name=new_name)
    session.add(new_scene)
    # Flush per assicurarsi che l'ID della nuova scena sia generato
    # prima di usarlo come chiave esterna per i messaggi.
    session.flush()

    source_messages = list_messages_for_scene(session, scene_id)

    for i, msg in enumerate(source_messages):
        new_msg = Message(
            scene_id=new_scene.id,
            character_id=msg.character_id,
            content=msg.content,
            position_order=i + 1,
        )
        session.add(new_msg)

    session.commit()
    return new_scene.id

def merge_scenes(session: Session, scene_id_a: str, scene_id_b: str, new_name: str) -> str:
    """
    Crea una nuova scena unendo i messaggi di scene_id_a e scene_id_b.
    I messaggi di A vengono prima, seguiti da quelli di B.
    Genera nuovi ID per la scena e i messaggi.
    """
    new_scene = Scene(name=new_name)
    session.add(new_scene)
    session.flush()

    messages_a = list_messages_for_scene(session, scene_id_a)
    messages_b = list_messages_for_scene(session, scene_id_b)

    current_position = 1

    for msg in messages_a:
        session.add(
            Message(
                scene_id=new_scene.id,
                character_id=msg.character_id,
                content=msg.content,
                position_order=current_position,
            )
        )
        current_position += 1

    for msg in messages_b:
        session.add(
            Message(
                scene_id=new_scene.id,
                character_id=msg.character_id,
                content=msg.content,
                position_order=current_position,
            )
        )
        current_position += 1

    session.commit()
    return new_scene.id
