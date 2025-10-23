from flask import Blueprint, request, jsonify
from database.conexion import db
from app.models import Vehiculo, Usuario

vehiculos_bp = Blueprint('vehiculos', __name__)

# Crear un nuevo vehículo
@vehiculos_bp.route('/api/vehiculos', methods=['POST'])
def crear_vehiculo():
    data = request.get_json()

    codigo = data.get('codigo')
    marca = data.get('marca')
    modelo = data.get('modelo')
    anio = data.get('anio')
    placa = data.get('placa')
    estado = data.get('estado', 'activo')
    asignado_a = data.get('asignado_a')  # id del usuario

    if not codigo:
        return jsonify({'error': 'El código del vehículo es obligatorio'}), 400

    if Vehiculo.query.filter_by(codigo=codigo).first():
        return jsonify({'error': 'El código del vehículo ya existe'}), 400

    nuevo = Vehiculo(
        codigo=codigo,
        marca=marca,
        modelo=modelo,
        anio=anio,
        placa=placa,
        estado=estado,
        asignado_a=asignado_a
    )

    db.session.add(nuevo)
    db.session.commit()

    return jsonify({'message': 'Vehículo registrado correctamente'}), 201


# Obtener todos los vehículos
@vehiculos_bp.route('/api/vehiculos', methods=['GET'])
def obtener_vehiculos():
    vehiculos = Vehiculo.query.all()
    lista = []
    for v in vehiculos:
        lista.append({
            'id': v.id,
            'codigo': v.codigo,
            'marca': v.marca,
            'modelo': v.modelo,
            'anio': v.anio,
            'placa': v.placa,
            'estado': v.estado,
            'asignado_a': v.asignado_a
        })
    return jsonify(lista), 200
