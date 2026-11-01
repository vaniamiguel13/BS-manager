import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.schema import CreateSchema, DropSchema


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    # Tests must not inherit real database or administrator settings.
    for name in ("DATABASE_HOST", "DATABASE_USER", "DATABASE_PASSWORD", "DATABASE_NAME", "DATABASE_URL", "ADMIN_EMAIL", "ADMIN_PASSWORD", "ADMIN_NAME", "SECRET_KEY", "FLASK_DEBUG"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def database_url(tmp_path):
    """Use a temporary SQLite file or an isolated schema in a PostgreSQL test database."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        yield f"sqlite:///{tmp_path / 'test.db'}"
        return

    url = make_url(test_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("TEST_DATABASE_URL must point to a dedicated PostgreSQL test database.")
    url = url.set(drivername="postgresql+psycopg")
    engine = create_engine(url)
    schema = f"bs_manager_test_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    options = f"{url.query.get('options', '')} -csearch_path={schema}".strip()
    try:
        yield url.update_query_dict({"options": options}).render_as_string(hide_password=False)
    finally:
        # Drop only the random schema created above; never reset the database.
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
