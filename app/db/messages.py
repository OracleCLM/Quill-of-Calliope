from __future__ import annotations

import uuid
from typing import List

from sqlalchemy import (
    Column,
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
