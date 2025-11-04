from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database.conexion import db
from app.models import Usuario

# Crear el blueprint
auth_bp = Blueprint('auth', __name__)

# ------------------ REGISTRO ------------------
@auth_bp.route('/api/registro', methods=['POST'])
def registro():
    data = request.get_json()

    nombre = data.get('nombre')
    correo = data.get('correo')
    username = data.get('username')
    password = data.get('password')

    if not all([nombre, username, password]):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    # Verificar si el usuario ya existe
    if Usuario.query.filter_by(username=username).first():
        return jsonify({'error': 'El usuario ya existe'}), 400

    # Cifrar la contraseña
    password_hash = generate_password_hash(password)

    nuevo_usuario = Usuario(
        nombre=nombre,
        correo=correo,
        username=username,
        password_hash=password_hash
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({'message': 'Usuario registrado correctamente'}), 201


# ------------------ LOGIN ------------------
@auth_bp.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    usuario = Usuario.query.filter_by(username=username).first()

    if not usuario or not check_password_hash(usuario.password_hash, password):
        return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401

    return jsonify({'message': f'Bienvenido, {usuario.nombre}', 'id': usuario.id}), 200