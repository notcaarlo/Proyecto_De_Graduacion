from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from database.conexion import db
from app.models import SesionConduccion, Usuario, Vehiculo
from datetime import datetime

admin_sesiones_bp = Blueprint('admin_sesiones', __name__)

@admin_sesiones_bp.route('/dashboard/sesiones')
@login_required
def listar_sesiones():
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores.', 'danger')
        return redirect(url_for('web_login.login'))

    sesiones = (
        db.session.query(SesionConduccion, Usuario.nombre, Vehiculo.codigo)
        .join(Usuario, SesionConduccion.id_usuario == Usuario.id, isouter=True)
        .join(Vehiculo, SesionConduccion.id_vehiculo == Vehiculo.id, isouter=True)
        .order_by(SesionConduccion.id.desc())
        .all()
    )
    return render_template('admin_sesiones.html', sesiones=sesiones)

@admin_sesiones_bp.route('/dashboard/sesiones/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_sesion(id):
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores.', 'danger')
        return redirect(url_for('web_login.login'))

    sesion = SesionConduccion.query.get_or_404(id)

    if sesion.estado == 'activa':
        sesion.estado = 'finalizada'
        sesion.fecha_fin = datetime.now()
        flash(f'Sesión {id} finalizada.', 'success')
    else:
        sesion.estado = 'activa'
        sesion.fecha_fin = None
        flash(f'Sesión {id} activada.', 'warning')

    db.session.commit()
    return redirect(url_for('admin_sesiones.listar_sesiones'))

@admin_sesiones_bp.route('/dashboard/sesiones/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_sesion(id):
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores.', 'danger')
        return redirect(url_for('web_login.login'))

    sesion = SesionConduccion.query.get_or_404(id)
    db.session.delete(sesion)
    db.session.commit()
    flash(f'Sesión {id} eliminada.', 'info')
    return redirect(url_for('admin_sesiones.listar_sesiones'))
