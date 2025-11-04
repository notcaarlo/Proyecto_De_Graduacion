# tests/test_alertas_api.py
from database.conexion import db
from app.models import Usuario, Vehiculo

def test_crear_alerta_201(client, app):
    with app.app_context():
        u = Usuario(nombre="Conductor X", username="cx", password_hash="h")
        v = Vehiculo(codigo="T01")
        db.session.add_all([u, v]); db.session.commit()
        uid, vid = u.id, v.id

    payload = {
        "id_usuario": uid,
        "id_vehiculo": vid,
        "duracion": 2.3,
        "nota": "test",
        "nivel_somnolencia": "medio"
    }
    r = client.post("/api/alertas", json=payload)
    assert r.status_code == 201
    assert "Alerta" in r.get_json().get("message","")

def test_crear_alerta_400(client):
    r = client.post("/api/alertas", json={"id_usuario": 1})
    assert r.status_code == 400