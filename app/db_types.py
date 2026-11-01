import sqlite3
from datetime import timezone

from sqlalchemy import DateTime, event
from sqlalchemy.engine import Engine
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """UTC-aware instants on both PostgreSQL and SQLite; never infer a naive timezone."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Attendance timestamps must be timezone-aware')
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == 'sqlite' else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@event.listens_for(Engine, 'connect')
def enforce_sqlite_foreign_keys(connection, record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()
