from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import Alerta, Usuario, Vehiculo, SesionConduccion
from database.conexion import db
from sqlalchemy import func
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__)


# ==========================
# DASHBOARD PRINCIPAL
# ==========================
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # 🔐 Solo administradores pueden acceder
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores pueden ver el dashboard.', 'danger')
        return redirect(url_for('web_login.perfil_usuario'))

    # Cargar todos los usuarios tipo conductor
    usuarios = Usuario.query.filter_by(rol='conductor').all()

    # Obtener conteo global de alertas (para carga inicial)
    conteos = (
        db.session.query(Alerta.nivel_somnolencia, func.count(Alerta.id))
        .group_by(Alerta.nivel_somnolencia)
        .all()
    )
    niveles = [c[0] for c in conteos]
    cantidades = [c[1] for c in conteos]
    resumen = list(zip(niveles, cantidades))

    # Últimas alertas globales
    alertas = (
        db.session.query(Alerta, Usuario.nombre, Vehiculo.codigo)
        .join(Usuario, Alerta.id_usuario == Usuario.id, isouter=True)
        .join(Vehiculo, Alerta.id_vehiculo == Vehiculo.id, isouter=True)
        .order_by(Alerta.id.desc())
        .limit(50)
        .all()
    )

    return render_template(
        'dashboard.html',
        usuarios=usuarios,
        alertas=alertas,
        niveles=niveles,
        cantidades=cantidades,
        resumen=resumen
    )


# ==========================
# ENDPOINT: ESTADÍSTICAS POR USUARIO
# ==========================
@dashboard_bp.route('/api/admin/estadisticas/<int:id_usuario>')
@login_required
def estadisticas_usuario(id_usuario):
    if current_user.rol != 'admin':
        return jsonify({'error': 'No autorizado'}), 403

    # SQLAlchemy 2.x: Session.get en lugar de Model.query.get
    usuario = db.session.get(Usuario, id_usuario)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    sesiones = db.session.query(SesionConduccion).filter_by(id_usuario=id_usuario).all()
    alertas = db.session.query(Alerta).filter_by(id_usuario=id_usuario).all()

    total_alertas = len(alertas)
    total_sesiones = len(sesiones)
    promedio_duracion = (
        sum(a.duracion for a in alertas) / total_alertas if total_alertas > 0 else 0
    )

    niveles = {"bajo": 0, "medio": 0, "critico": 0}
    for a in alertas:
        niveles[a.nivel_somnolencia] = niveles.get(a.nivel_somnolencia, 0) + 1

    data = {
        "usuario": usuario.nombre,
        "total_alertas": total_alertas,
        "total_sesiones": total_sesiones,
        "promedio_duracion": round(promedio_duracion, 2),
        "niveles": niveles,
        "alertas": [
            {
                "fecha": a.fecha.strftime("%Y-%m-%d"),
                "hora": a.hora.strftime("%H:%M:%S"),
                "duracion": a.duracion,
                "nivel": a.nivel_somnolencia,
                "vehiculo": a.id_vehiculo,
            }
            for a in alertas
        ],
    }

    return jsonify(data), 200
