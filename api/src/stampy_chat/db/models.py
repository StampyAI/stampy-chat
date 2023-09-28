import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BINARY, JSON, DateTime, Integer, String, and_, func, select
)
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)


class UUID(TypeDecorator):

    impl = BINARY(16)

    def process_bind_param(self, value, dialect):
        if not value:
            value = uuid.uuid4()
        elif not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)

        if dialect.name == "mysql":
            return value.bytes
        return value

    def process_result_value(self, value, dialect):
        if value and dialect.name == "mysql":
            return uuid.UUID(value.hex())
        return value


class Base(DeclarativeBase):
    pass


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column("id", primary_key=True)

    # The session_id is set once per session, so can be easily used to extract whole histories
    session_id: Mapped[str] = mapped_column(UUID(), default=uuid.uuid4)

    # The 0-indexed number of the current conversation pair, where a conversation pair is a prompt + its response.
    # The system prompt isn't counted as part of the interaction list
    interaction_no: Mapped[int] = mapped_column(Integer)

    # The actual query provided by the user
    query: Mapped[str] = mapped_column(String(1028))

    # The full prompt as sent to the LLM
    prompt: Mapped[Optional[str]] = mapped_column(LONGTEXT)

    # Whatever the LLM returns
    response: Mapped[Optional[str]] = mapped_column(LONGTEXT)

    # The ids of the chunks used for the prompt
    chunks: Mapped[Optional[str]] = mapped_column(String(1028))  # TODO: Change this to a proper format
    date_created: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Any moderation data
    moderation: Mapped[Optional[JSON]] = mapped_column(JSON, default="{}")

    @hybrid_property
    def history(self):
        return Session.object_session(self).query(Interaction).filter(
            and_(
                Interaction.session_id == self.session_id,
                Interaction.interaction_no < self.interaction_no
            )
        )

    @history.expression
    def history(cls):
        # This part is for the class level expression
        return (
            select([Interaction]).
            where(
                and_(
                    Interaction.session_id == cls.session_id,
                    Interaction.interaction_no < cls.interaction_no
                )
            )
        )

    def __repr__(self) -> str:
        return f"Interaction(session={self.session_id!r}, no={self.interaction_no!r}, query={self.query!r}, response={self.response!r})"
