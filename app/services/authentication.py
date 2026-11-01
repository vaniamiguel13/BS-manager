"""Database-backed login attempt limits, shared across web workers."""
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import timedelta

from flask_login import UserMixin
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from .. import db
from ..attendance_time import utc_now
from ..models import LoginThrottle, User

MAX_FAILURES = 10
LOCKOUT_SECONDS = 15 * 60
# A real password hash avoids a cheap account-existence timing signal.
from werkzeug.security import generate_password_hash, check_password_hash
DUMMY_HASH = generate_password_hash(secrets.token_hex(32))


@dataclass(frozen=True)
class VerifiedLogin(UserMixin):
    """The session identity paired with the password that was verified."""
    token: str = field(repr=False)

    def get_id(self):
        return self.token


def authenticate(email, password):
    now = utc_now()
    key = hashlib.sha256(email.encode()).hexdigest()
    insert = pg_insert if db.engine.dialect.name == 'postgresql' else sqlite_insert
    db.session.execute(insert(LoginThrottle).values(key=key, failures=0, window_start=now)
                       .on_conflict_do_nothing(index_elements=['key']))
    attempt = db.session.execute(select(LoginThrottle).where(LoginThrottle.key == key).with_for_update()).scalar_one()
    if attempt.blocked_until and attempt.blocked_until > now:
        db.session.commit()
        return None, True
    if (now - attempt.window_start).total_seconds() >= LOCKOUT_SECONDS:
        attempt.failures, attempt.window_start, attempt.blocked_until = 0, now, None
    # Hold the attempt row lock through password verification so competing workers
    # cannot each receive a fresh allowance. SQLite's upsert takes its write lock.
    user = User.query.filter_by(email=email).first()
    valid = check_password_hash(user.password_hash if user else DUMMY_HASH, password)
    if user and user.active and valid:
        principal = VerifiedLogin(user.session_token)
        attempt.failures, attempt.window_start, attempt.blocked_until = 0, now, None
        db.session.commit()
        return principal, False
    attempt.failures += 1
    if attempt.failures >= MAX_FAILURES:
        attempt.blocked_until = now + timedelta(seconds=LOCKOUT_SECONDS)
    # Remove expired unknown-account buckets; keep active lockouts.
    db.session.execute(delete(LoginThrottle).where(LoginThrottle.window_start < now-timedelta(days=1),
        (LoginThrottle.blocked_until.is_(None)) | (LoginThrottle.blocked_until < now)))
    db.session.commit()
    return None, False
