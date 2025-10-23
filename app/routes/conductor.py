from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import func
from database.conexion import db
from app.models import Vehiculo, SesionConduccion, Alerta
from app.utils.detector_launcher import iniciar_detector, detener_detector

conductor_bp = Blueprint('conductor', __name__)

# =============================
# PERFIL DEL CONDUCTOR
# =============================
@conductor_bp.route('/perfil')
@login_required
def perfil_conductor():
    if current_user.rol != 'conductor':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    # Sesión activa (si existe)
    sesion_activa = (SesionConduccion.query
                     .filter_by(id_usuario=current_user.id, estado='activa')
                     .order_by(SesionConduccion.id.desc())
                     .first())

    # Vehículos asignados AL CONDUCTOR (solo activos)
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

# =============================
# INICIAR JORNADA  (GET muestra selector, POST crea sesión)
# =============================
@conductor_bp.route('/perfil/iniciar', methods=['GET', 'POST'])
@login_required
def iniciar_jornada():
    if current_user.rol != 'conductor':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard.dashboard'))

    # Evitar dos jornadas simultáneas
    existente = SesionConduccion.query.filter_by(
        id_usuario=current_user.id, estado='activa'
    ).first()
    if existente:
        flash('Ya tienes una jornada activa.', 'warning')
        return redirect(url_for('conductor.perfil_conductor'))

    # Lista de vehículos asignados y activos (para GET y validación en POST)
    vehiculos_asignados = (Vehiculo.query
                           .filter_by(id_usuario=current_user.id, estado='activo')
                           .order_by(Vehiculo.codigo.asc())
                           .all())

    if request.method == 'GET':
        if not vehiculos_asignados:
            flash('No tienes un vehículo asignado. Contacta a un administrador.', 'warning')
            return redirect(url_for('conductor.perfil_conductor'))
        return render_template('iniciar_jornada.html', vehiculos=vehiculos_asignados)

    # POST
    vehiculo_id = request.form.get('vehiculo_id', type=int)
    if not vehiculo_id:
        flash('Debes seleccionar un vehículo asignado.', 'warning')
        return redirect(url_for('conductor.iniciar_jornada'))

    vehiculo = Vehiculo.query.get(vehiculo_id)
    if not vehiculo:
        flash('Vehículo no encontrado.', 'danger')
        return redirect(url_for('conductor.iniciar_jornada'))

    # Validar asignación y estado
    if vehiculo.id_usuario != current_user.id:
        flash('Ese vehículo no está asignado a tu usuario.', 'danger')
        return redirect(url_for('conductor.iniciar_jornada'))

    if (vehiculo.estado or 'activo').lower() != 'activo':
        flash('Ese vehículo está inactivo. Contacta a un administrador.', 'danger')
        return redirect(url_for('conductor.iniciar_jornada'))

    # Crear sesión
    nueva = SesionConduccion(
        id_usuario=current_user.id,
        id_vehiculo=vehiculo.id,
        fecha_inicio=datetime.utcnow(),
        estado='activa'
    )
    db.session.add(nueva)
    db.session.commit()

    # Arrancar detector (no bloquear si falla)
    try:
        iniciar_detector(current_user.id, vehiculo.id)
    except Exception as e:
        print(f"[Detector] No se pudo iniciar: {e}")

    flash(f'Jornada iniciada con el vehículo {vehiculo.codigo}.', 'success')
    return redirect(url_for('conductor.perfil_conductor'))

# =============================
# FINALIZAR JORNADA
# =============================
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

    sesion.fecha_fin = datetime.utcnow()
    sesion.estado = 'finalizada'
    db.session.commit()

    try:
        detener_detector()
    except Exception as e:
        print(f"[Detector] No se pudo detener: {e}")

    flash('Jornada finalizada correctamente. Cámara desactivada.', 'success')
    return redirect(url_for('conductor.perfil_conductor'))

# =============================
# HISTORIAL (JSON para la tabla)
# =============================
@conductor_bp.route('/perfil/historial_json', methods=['GET'])
@login_required
def historial_json():
    if current_user.rol != 'conductor':
        return jsonify({'sesiones': []})

    sesiones = (SesionConduccion.query
                .filter_by(id_usuario=current_user.id)
                .order_by(SesionConduccion.id.desc())
                .limit(50)
                .all())

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
