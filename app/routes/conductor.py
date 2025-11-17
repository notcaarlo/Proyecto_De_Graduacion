from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask import Response
import time
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from database.conexion import db
from app.models import Vehiculo, SesionConduccion, Alerta
from app.utils.detector_launcher import iniciar_detector, detener_detector, camera_buffer

conductor_bp = Blueprint('conductor', __name__)

# =======PERFIL DEL CONDUCTOR==============
@conductor_bp.route('/perfil')
@login_required
def perfil_conductor():
    if current_user.rol != 'conductor':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    sesion_activa = (SesionConduccion.query
                         .filter_by(id_usuario=current_user.id, estado='activa')
                         .order_by(SesionConduccion.id.desc())
                         .first())
    vehiculos_asignados = (Vehiculo.query
                             .filter_by(id_usuario=current_user.id, estado='activo')
                             .order_by(Vehiculo.codigo.asc())
                             .all())

    tiene_asignacion = len(vehiculos_asignados) > 0

    return render_template(
        'perfil.html',
        sesion_activa=sesion_activa,
        vehiculos=vehiculos_asignados,
        tiene_asignacion=tiene_asignacion
    )

# ============INICIAR JORNADA=================
@conductor_bp.route('/perfil/iniciar', methods=['GET', 'POST'])
@login_required
def iniciar_jornada():
    if current_user.rol != 'conductor':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))
    
    existente = SesionConduccion.query.filter_by(
        id_usuario=current_user.id, estado='activa'
    ).first()
    if existente:
        flash('Ya tienes una jornada activa.', 'warning')
        return redirect(url_for('conductor.perfil_conductor'))
    
    vehiculos_asignados = (Vehiculo.query
                             .filter_by(id_usuario=current_user.id, estado='activo')
                             .order_by(Vehiculo.codigo.asc())
                             .all())

    if request.method == 'GET':
        if not vehiculos_asignados:
            flash('No tienes un vehículo asignado. Contacta a un administrador.', 'warning')
            return redirect(url_for('conductor.perfil_conductor'))
        return render_template('iniciar_jornada.html', vehiculos=vehiculos_asignados)
    
    vehiculo_id = request.form.get('vehiculo_id', type=int)
    if not vehiculo_id:
        flash('Debes seleccionar un vehículo asignado.', 'warning')
        return redirect(url_for('conductor.iniciar_jornada'))

    vehiculo = Vehiculo.query.get(vehiculo_id)
    if not vehiculo or vehiculo.id_usuario != current_user.id or vehiculo.estado != 'activo':
        flash('Vehículo inválido, no asignado o inactivo.', 'danger')
        return redirect(url_for('conductor.iniciar_jornada'))

    nueva = SesionConduccion(
        id_usuario=current_user.id,
        id_vehiculo=vehiculo.id,
        fecha_inicio=datetime.now(),
        estado='activa'
    )
    db.session.add(nueva)
    db.session.commit()
    
    try:
        iniciar_detector(current_user.id, vehiculo.id)
    except Exception as e:
        print(f"[Detector] No se pudo iniciar: {e}")

    flash(f'Jornada iniciada con el vehículo {vehiculo.codigo}.', 'success')
    return redirect(url_for('conductor.perfil_conductor'))

# ===========FINALIZAR JORNADA==================
@conductor_bp.route('/perfil/finalizar', methods=['POST'])
@login_required
def finalizar_jornada():
    if current_user.rol != 'conductor':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    sesion = SesionConduccion.query.filter_by(
        id_usuario=current_user.id, estado='activa'
    ).first()

    if not sesion:
        flash('No tienes una jornada activa.', 'warning')
        return redirect(url_for('conductor.perfil_conductor'))

    sesion.fecha_fin = datetime.now()
    sesion.estado = 'finalizada'
    db.session.commit()
    
    try:
        detener_detector()
    except Exception as e:
        print(f"[Detector] No se pudo detener: {e}")

    flash('Jornada finalizada correctamente. Cámara desactivada.', 'success')
    return redirect(url_for('conductor.perfil_conductor'))

def generate_frames():
    """
    Generador que lee desde el búfer global 'camera_buffer' 
    y transmite los frames al navegador.
    """
    print("[Streaming] Iniciando stream para el navegador.")
    while True:
        time.sleep(0.05)
        frame_bytes = camera_buffer.get_frame_bytes()
        if not frame_bytes:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@conductor_bp.route('/video_feed')
@login_required
def video_feed():
    """Ruta que sirve el video en vivo."""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# ============HISTORIAL DE JORNADAS=================
@conductor_bp.route('/perfil/historial_json', methods=['GET'])
@login_required
def historial_json():
    if current_user.rol != 'conductor':
        return jsonify({'sesiones': []})
    sesiones = (SesionConduccion.query
                .filter_by(id_usuario=current_user.id)
                .order_by(SesionConduccion.id.desc())
                .limit(50).all())
    data = []
    for s in sesiones:
        total_alertas = db.session.query(func.count(Alerta.id))\
            .filter(Alerta.id_sesion == s.id).scalar() or 0
        data.append({
            'id': s.id,
            'vehiculo': s.vehiculo.codigo if s.vehiculo else '-',
            'inicio': s.fecha_inicio.strftime('%d/%m/%Y %H:%M'),
            'fin': s.fecha_fin.strftime('%d/%m/%Y %H:%M') if s.fecha_fin else '—',
            'estado': s.estado,
            'alertas': total_alertas
        })
    return jsonify({'sesiones': data})