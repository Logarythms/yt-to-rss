import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class EpisodeStatus(PyEnum):
    pending = "pending"
    downloading = "downloading"
    ready = "ready"
    failed = "failed"


class Feed(Base):
    __tablename__ = "feeds"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    author = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    artwork_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    episodes = relationship("Episode", back_populates="feed", cascade="all, delete-orphan")


class Episode(Base):
    __tablename__ = "episodes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    feed_id = Column(String(36), ForeignKey("feeds.id"), nullable=False)
    youtube_id = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    audio_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # bytes
    duration = Column(Integer, nullable=True)  # seconds
    published_at = Column(DateTime, nullable=True)
    status = Column(Enum(EpisodeStatus), default=EpisodeStatus.pending)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    feed = relationship("Feed", back_populates="episodes")
