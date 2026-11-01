from flask_migrate import upgrade
from sqlalchemy import inspect, text
from app import create_app, db


def test_readiness_requires_current_schema_without_creating_it(database_url):
    app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': database_url})
    client = app.test_client()
    assert client.get('/health/ready').status_code == 503
    with app.app_context():
        assert inspect(db.engine).get_table_names() == []
        upgrade()
    response = client.get('/health/ready')
    assert response.status_code == 200
    assert response.json == {'status': 'ok'}
    assert response.headers['Cache-Control'] == 'no-store'
    with app.app_context():
        db.session.execute(text("UPDATE alembic_version SET version_num='outdated'"))
        db.session.commit()
    assert client.get('/health/ready').status_code == 503
