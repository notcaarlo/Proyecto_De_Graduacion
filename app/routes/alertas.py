from flask import Blueprint, request, jsonify
from database.conexion import db
from app.models import Alerta, Usuario, Vehiculo, SesionConduccion
from datetime import datetime

alertas_bp = Blueprint('alertas', __name__)

# ===========================
# Registrar una nueva alerta
# ===========================
@alertas_bp.route('/api/alertas', methods=['POST'])
def crear_alerta():
    data = request.get_json() or {}

    id_usuario = data.get('id_usuario')
    id_vehiculo = data.get('id_vehiculo')
    duracion = data.get('duracion')
    nota = data.get('nota')
    nivel_somnolencia = data.get('nivel_somnolencia', 'bajo')

    if not all([id_usuario, id_vehiculo, duracion]):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    # Verificar que existan usuario y vehículo (SQLAlchemy 2.x: Session.get)
    usuario = db.session.get(Usuario, id_usuario)
    vehiculo = db.session.get(Vehiculo, id_vehiculo)

    if not usuario:
        return jsonify({'error': 'El usuario no existe'}), 404
    if not vehiculo:
        return jsonify({'error': 'El vehículo no existe'}), 404

    # Buscar la sesión activa del usuario
    sesion_activa = (
        db.session.query(SesionConduccion)
        .filter_by(id_usuario=id_usuario, estado='activa')
        .first()
    )

    # Si no hay sesión activa, crear una automáticamente
    if not sesion_activa:
        sesion_activa = SesionConduccion(
            id_usuario=id_usuario,
            id_vehiculo=id_vehiculo,
            fecha_inicio=datetime.utcnow(),
            estado='activa'
        )
        db.session.add(sesion_activa)
        db.session.commit()
        print(f"[API] Nueva sesión creada automáticamente para usuario {id_usuario}")

    # Crear alerta vinculada a la sesión activa
    nueva_alerta = Alerta(
        id_usuario=id_usuario,
        id_vehiculo=id_vehiculo,
        id_sesion=sesion_activa.id,
        fecha=datetime.utcnow().date(),
        hora=datetime.utcnow().time(),
        duracion=duracion,
        nota=nota,
        nivel_somnolencia=nivel_somnolencia
    )

    db.session.add(nueva_alerta)
    db.session.commit()

    print(f"[API] Alerta registrada correctamente (sesión {sesion_activa.id})")

    return jsonify({'message': 'Alerta registrada correctamente'}), 201


# ===========================
# Obtener todas las alertas
# ===========================
@alertas_bp.route('/api/alertas', methods=['GET'])
def obtener_alertas():
    alertas = db.session.query(Alerta).all()
    lista = []
    for a in alertas:
        lista.append({
            'id': a.id,
            'usuario': a.id_usuario,
            'vehiculo': a.id_vehiculo,
            'sesion': a.id_sesion,
            'fecha': a.fecha.strftime('%Y-%m-%d'),
            'hora': a.hora.strftime('%H:%M:%S'),
            'duracion': a.duracion,
            'nota': a.nota,
            'nivel_somnolencia': a.nivel_somnolencia
        })
    return jsonify(lista), 200
