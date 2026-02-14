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
        # Add original_published_at column for date override support
        ("episodes", "original_published_at", "ALTER TABLE episodes ADD COLUMN original_published_at DATETIME"),
        # Add original_title and original_description for title/description editing
        ("episodes", "original_title", "ALTER TABLE episodes ADD COLUMN original_title VARCHAR(500)"),
        ("episodes", "original_description", "ALTER TABLE episodes ADD COLUMN original_description TEXT"),
    ]

    with engine.connect() as conn:
        # Create migrations tracking table if it doesn't exist
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _migrations (
                name VARCHAR(255) PRIMARY KEY,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.commit()

        # Run column migrations
        for table, column, sql in migrations:
            # Check if column exists
            result = conn.execute(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in result.fetchall()]

            if column not in columns:
                logger.info(f"Adding column {column} to {table}")
                conn.execute(text(sql))
                conn.commit()

        # Data migration: populate original_published_at for existing episodes
        migration_name = "populate_original_published_at"
        result = conn.execute(
            text("SELECT 1 FROM _migrations WHERE name = :name"),
            {"name": migration_name}
        )
        if not result.fetchone():
            result = conn.execute(text(
                "SELECT id, published_at, created_at FROM episodes WHERE original_published_at IS NULL"
            ))
            rows = result.fetchall()
            if rows:
                logger.info(f"Migrating original_published_at for {len(rows)} existing episodes")
                for row in rows:
                    original_date = row[1] if row[1] else row[2]  # published_at or created_at
                    if original_date:
                        conn.execute(
                            text("UPDATE episodes SET original_published_at = :date WHERE id = :id"),
                            {"date": original_date, "id": row[0]}
                        )
                conn.commit()
            # Mark migration as complete
            conn.execute(
                text("INSERT INTO _migrations (name) VALUES (:name)"),
                {"name": migration_name}
            )
            conn.commit()
            logger.info(f"Data migration '{migration_name}' completed")

        # Data migration: populate original_title and original_description for existing episodes
        migration_name = "populate_original_title_description"
        result = conn.execute(
            text("SELECT 1 FROM _migrations WHERE name = :name"),
            {"name": migration_name}
        )
        if not result.fetchone():
            result = conn.execute(text(
                "SELECT id, title, description FROM episodes WHERE original_title IS NULL"
            ))
            rows = result.fetchall()
            if rows:
                logger.info(f"Migrating original_title/description for {len(rows)} existing episodes")
                for row in rows:
                    conn.execute(
                        text("UPDATE episodes SET original_title = :title, original_description = :desc WHERE id = :id"),
                        {"title": row[1], "desc": row[2], "id": row[0]}
                    )
                conn.commit()
            # Mark migration as complete
            conn.execute(
                text("INSERT INTO _migrations (name) VALUES (:name)"),
                {"name": migration_name}
            )
            conn.commit()
            logger.info(f"Data migration '{migration_name}' completed")


def run_schema_migrations():
    """Run schema-altering migrations that require table recreation (SQLite)."""
    with engine.connect() as conn:
        # Migration: make youtube_id nullable for uploaded audio support
        migration_name = "make_youtube_id_nullable"
        result = conn.execute(
            text("SELECT 1 FROM _migrations WHERE name = :name"),
            {"name": migration_name}
        )
        if not result.fetchone():
            # Check if youtube_id column has NOT NULL constraint
            result = conn.execute(text("PRAGMA table_info(episodes)"))
            columns = result.fetchall()
            youtube_id_info = next((col for col in columns if col[1] == 'youtube_id'), None)

            if youtube_id_info and youtube_id_info[3] == 1:  # notnull flag = 1
                logger.info("Migrating episodes table: making youtube_id nullable")
                col_names = [col[1] for col in columns]
                col_list = ', '.join(col_names)

                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("CREATE TABLE _episodes_backup AS SELECT * FROM episodes"))
                conn.execute(text("DROP TABLE episodes"))
                conn.commit()

                # Recreate from model definition (youtube_id is nullable)
                Base.metadata.tables['episodes'].create(bind=engine)

                conn.execute(text(
                    f"INSERT INTO episodes ({col_list}) SELECT {col_list} FROM _episodes_backup"
                ))
                conn.execute(text("DROP TABLE _episodes_backup"))
                conn.execute(text("PRAGMA foreign_keys=ON"))
                conn.commit()
                logger.info("Successfully made youtube_id nullable")

            conn.execute(
                text("INSERT INTO _migrations (name) VALUES (:name)"),
                {"name": migration_name}
            )
            conn.commit()


def init_db():
    """Create all tables and run migrations."""
    Base.metadata.create_all(bind=engine)
    run_migrations()
    run_schema_migrations()
