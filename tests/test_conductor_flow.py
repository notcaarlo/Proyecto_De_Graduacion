# tests/test_conductor_flow.py
from database.conexion import db
from app.models import Usuario, Vehiculo
from flask_login import login_user

def login_as(client, app, usuario):
    with app.test_request_context():
        login_user(usuario)

def test_iniciar_finalizar_jornada(client, app, monkeypatch):
    # Mockear detector para que no abra cámara en tests
    monkeypatch.setattr("app.routes.conductor.iniciar_detector", lambda *a, **k: None)
    monkeypatch.setattr("app.routes.conductor.detener_detector", lambda *a, **k: None)

    with app.app_context():
        u = Usuario(nombre="C", username="c1", password_hash="h", rol="conductor")
        v = Vehiculo(codigo="T01")
        db.session.add_all([u, v]); db.session.commit()
        uid, vid = u.id, v.id

    # Forzar sesión (si usás flask_login en rutas)
    with client.session_transaction() as sess:
        sess["_user_id"] = str(uid)

    # Iniciar (POST)
    r = client.post("/perfil/iniciar", data={"vehiculo_id": str(vid)}, follow_redirects=True)
    assert r.status_code == 200
    assert b"Jornada iniciada" in r.data

    # Finalizar (POST)
    r2 = client.post("/perfil/finalizar", follow_redirects=True)
    assert r2.status_code == 200
    assert b"Jornada finalizada" in r2.data