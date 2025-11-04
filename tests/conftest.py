# tests/conftest.py
import os
import sys
import pytest
import sqlalchemy as sa
os.environ["APP_DISABLE_DETECTOR"] = "1"

# 1) Asegurar que la raíz del proyecto esté en el PYTHONPATH
#    .../Proyecto detector de somnolencia/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 2) Forzar BD de pruebas en memoria ANTES de crear la app
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'          # si tu create_app lee DATABASE_URL
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # por si tu app usa esta directamente
os.environ['FLASK_ENV'] = 'testing'
os.environ['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'test-secret')

from app import create_app
from database.conexion import db as _db

@pytest.fixture(scope='session')
def app():
    """App de pruebas con SQLite en memoria."""
    app = create_app()
    # Refuerza config por si create_app ignora las variables de entorno
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        WTF_CSRF_ENABLED=False,
        SERVER_NAME='localhost.localdomain'  # evita warnings de URL building
    )
    # Crea el esquema una sola vez para toda la sesión de tests
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
        # Desactiva claves foráneas en SQLite para truncar cómodamente
        if db.engine.dialect.name == "sqlite":
            db.session.execute(sa.text("PRAGMA foreign_keys=OFF;"))
        # Borrar en orden inverso para respetar FKs
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        if db.engine.dialect.name == "sqlite":
            db.session.execute(sa.text("PRAGMA foreign_keys=ON;"))
# tests/conftest.py