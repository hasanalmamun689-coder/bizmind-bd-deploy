from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# PostgreSQL is the only supported runtime datastore (MASTER PROMPT section 6).
# pool_pre_ping avoids stale-connection errors after idle periods.
# pool_recycle: Neon closes idle connections and suspends compute when idle, so recycle
# connections before they go stale. Small pool: Neon limits concurrent connections.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=5,
    max_overflow=5,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
