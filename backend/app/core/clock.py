"""Single source of 'now'. Always timezone-aware UTC, so it can be compared with the
timestamptz columns SQLAlchemy returns (mixing naive and aware datetimes raises TypeError)."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
