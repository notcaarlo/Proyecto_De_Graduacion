# tests/conftest.py
import os
import sys
import pytest
import sqlalchemy as sa
os.environ["APP_DISABLE_DETECTOR"] = "1"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
    
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test-secret')

from app import create_app
from database.conexion import db as _db

@pytest.fixture(scope='session')
def app():
    """App de pruebas con SQLite en memoria."""
    app = create_app()
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=False,
        SERVER_NAME='localhost.localdomain'
    )
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def db(app):
    return _db

@pytest.fixture(autouse=True)
def _clean_db(app):
    from database.conexion import db
    with app.app_context():
        if db.engine.dialect.name == "sqlite":
            db.session.execute(sa.text("PRAGMA foreign_keys=OFF;"))
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        if db.engine.dialect.name == "sqlite":
            db.session.execute(sa.text("PRAGMA foreign_keys=ON;"))
