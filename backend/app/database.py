import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # SQLite specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Run database migrations for schema updates."""
    migrations = [
        # Add author column to feeds table
        ("feeds", "author", "ALTER TABLE feeds ADD COLUMN author VARCHAR(255)"),
        # Add file_size column to episodes table
        ("episodes", "file_size", "ALTER TABLE episodes ADD COLUMN file_size INTEGER"),
        # Add source_type column for uploaded audio support
        ("episodes", "source_type", "ALTER TABLE episodes ADD COLUMN source_type VARCHAR(10) DEFAULT 'youtube'"),
        # Add original_filename column for uploaded audio
        ("episodes", "original_filename", "ALTER TABLE episodes ADD COLUMN original_filename VARCHAR(500)"),
        # Add thumbnail_path column for local episode thumbnails
        ("episodes", "thumbnail_path", "ALTER TABLE episodes ADD COLUMN thumbnail_path VARCHAR(500)"),
    ]

    with engine.connect() as conn:
        for table, column, sql in migrations:
            # Check if column exists
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in result.fetchall()]

            if column not in columns:
                logger.info(f"Adding column {column} to {table}")
                conn.execute(text(sql))
                conn.commit()


def init_db():
    """Create all tables and run migrations."""
    Base.metadata.create_all(bind=engine)
    run_migrations()
