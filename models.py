from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Junction table for note <-> tags
note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", Integer, ForeignKey("notes.id", ondelete="CASCADE")),
    Column("tag_id",  Integer, ForeignKey("tags.id",  ondelete="CASCADE")),
)

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)

    notes = relationship("Note", back_populates="user", cascade="all, delete")
    tags  = relationship("Tag",  back_populates="user", cascade="all, delete")


class Note(Base):
    __tablename__ = "notes"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title      = Column(String, nullable=False, default="Untitled")
    content    = Column(Text, default="")
    is_pinned  = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary=note_tags, back_populates="notes")


class Tag(Base):
    __tablename__ = "tags"

    id      = Column(Integer, primary_key=True, index=True)
    name    = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    user  = relationship("User", back_populates="tags")
    notes = relationship("Note", secondary=note_tags, back_populates="tags")
