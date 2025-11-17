from flask import Blueprint, request, jsonify, current_app
from database.conexion import db
from app.models import Alerta, Usuario, Vehiculo, SesionConduccion
from datetime import datetime
from threading import Thread
from flask_mail import Message
import os
import uuid
from werkzeug.utils import secure_filename

alertas_bp = Blueprint('alertas', __name__)

def _send_async_email(app, msg):
    """Función que se ejecuta en un hilo para enviar el email."""
    with app.app_context():
        from app import mail 
        try:
            mail.send(msg)
            print("[API] Email de alerta enviado exitosamente.")
        except Exception as e:
            print(f"[API] ERROR al enviar email: {e}")
            
def enviar_email_alerta_critica(app, alerta, usuario, vehiculo, evidencia_path=None):
    """Prepara y envía el email de alerta en un hilo separado."""
    
    admin_email = app.config.get('ADMIN_EMAIL')
    sender_email = app.config.get('MAIL_USERNAME')

    if not admin_email:
        print("[API] ERROR: ADMIN_EMAIL no está configurado en .env. No se puede enviar email.")
        return
    if not sender_email:
        print("[API] ERROR: MAIL_USERNAME no está configurado en .env. No se puede enviar email.")
        return

    # ------------------Contenido del email------------------------
    subject = f"ALERTA CRÍTICA: Conductor {usuario.nombre}"
    body = f"""
    Se ha detectado una alerta de somnolencia Nivel CRÍTICO.
    Por favor, contacte al conductor de inmediato.

    --- DETALLES DE LA ALERTA ---
    Conductor: {usuario.nombre} (ID: {usuario.id})
    Vehículo: {vehiculo.codigo} (Placa: {vehiculo.placa or 'N/A'})
    
    Fecha: {alerta.fecha.strftime('%d/%m/%Y')}
    Hora: {alerta.hora.strftime('%H:%M:%S')}
    Duración del evento: {alerta.duracion} segundos
    Nota: {alerta.nota or 'Alerta automática del detector.'}
    
    Se adjunta imagen de evidencia.
    """
    
    msg = Message(subject, sender=sender_email, recipients=[admin_email])
    msg.body = body

    if evidencia_path and os.path.exists(evidencia_path):
        try:
            with open(evidencia_path, 'rb') as fp:
                msg.attach(
                    filename=os.path.basename(evidencia_path),
                    content_type='image/jpeg',
                    data=fp.read()
                )
            print(f"[API] Adjuntando evidencia: {evidencia_path}")
        except Exception as e:
            print(f"[API] ERROR al adjuntar imagen al email: {e}")
    elif evidencia_path:
        print(f"[API] ADVERTENCIA: Se esperaba evidencia pero no se encontró en {evidencia_path}")
        
    thr = Thread(target=_send_async_email, args=[app, msg])
    thr.start()
    
@alertas_bp.route('/api/alertas', methods=['POST'])
def crear_alerta():
    
    data = request.form.to_dict() or {}
    try:
        id_usuario = int(data.get('id_usuario'))
        id_vehiculo = int(data.get('id_vehiculo'))
        duracion = float(data.get('duracion'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Faltan campos obligatorios o tienen formato incorrecto'}), 400

    nota = data.get('nota')
    nivel_somnolencia = data.get('nivel_somnolencia', 'bajo').lower()
    usuario = db.session.get(Usuario, id_usuario)
    vehiculo = db.session.get(Vehiculo, id_vehiculo)

    if not usuario:
        return jsonify({'error': f'El usuario ID {id_usuario} no existe'}), 404
    if not vehiculo:
        return jsonify({'error': 'El vehículo no existe'}), 404
    
    evidencia_filename = None
    evidencia_path_para_email = None
    
    if 'evidencia_img' in request.files:
        file = request.files['evidencia_img']
        
        if file and file.filename != '':
            try:
                # 1. Crear nombre de archivo seguro y único
                ext = os.path.splitext(secure_filename(file.filename))[1]
                evidencia_filename = f"{uuid.uuid4().hex}{ext}"
                
                # 2. Obtener ruta de guardado
                upload_folder = current_app.config['UPLOAD_FOLDER']
                
                # 3. Asegurarse que la carpeta exista
                os.makedirs(upload_folder, exist_ok=True)
                
                # 4. Guardar el archivo
                evidencia_path_para_email = os.path.join(upload_folder, evidencia_filename)
                file.save(evidencia_path_para_email)
                
                print(f"[API] Imagen de evidencia guardada en: {evidencia_path_para_email}")
                
            except Exception as e:
                print(f"[API] ERROR al guardar la imagen: {e}")
                evidencia_filename = None
                evidencia_path_para_email = None
                
    sesion_activa = (
        db.session.query(SesionConduccion)
        .filter_by(id_usuario=id_usuario, estado='activa')
        .first()
    )

    if not sesion_activa:
        sesion_activa = SesionConduccion(
            id_usuario=id_usuario,
            id_vehiculo=id_vehiculo,
            fecha_inicio=datetime.now(),
            estado='activa'
        )
        db.session.add(sesion_activa)
        db.session.commit() 
        print(f"[API] Nueva sesión creada automáticamente para usuario {id_usuario}")

    nueva_alerta = Alerta(
        id_usuario=id_usuario,
        id_vehiculo=id_vehiculo,
        id_sesion=sesion_activa.id,
        fecha=datetime.now().date(),
        hora=datetime.now().time(),
        duracion=duracion,
        nota=nota,
        nivel_somnolencia=nivel_somnolencia,
        evidencia_url=evidencia_filename
    )

    db.session.add(nueva_alerta)
    db.session.commit()
    
    if nueva_alerta.nivel_somnolencia == 'critico':
        print(f"[API] Alerta CRÍTICA (ID: {nueva_alerta.id}) detectada. Preparando email...")
        app = current_app._get_current_object() 
        enviar_email_alerta_critica(
            app, nueva_alerta, usuario, vehiculo, evidencia_path_para_email
        )
    
    print(f"[API] Alerta registrada correctamente (sesión {sesion_activa.id})")

    return jsonify({'message': 'Alerta registrada correctamente'}), 201

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
            'nivel_somnolencia': a.nivel_somnolencia,
            'evidencia_url': a.evidencia_url
        })
    return jsonify(lista), 200