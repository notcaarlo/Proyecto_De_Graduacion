from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database.conexion import db
from app.models import Vehiculo, Usuario

admin_vehiculos_bp = Blueprint('admin_vehiculos', __name__)

# ================================
# VERIFICAR ROL ADMINISTRADOR
# ================================
def _solo_admin():
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores pueden acceder.', 'danger')
        return False
    return True


# ================================
# LISTAR VEHÍCULOS
# ================================
@admin_vehiculos_bp.route('/dashboard/vehiculos')
@login_required
def listar_vehiculos():
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    vehiculos = Vehiculo.query.order_by(Vehiculo.id.desc()).all()
    conductores = Usuario.query.filter_by(rol='conductor').order_by(Usuario.nombre.asc()).all()

    return render_template(
        'admin_vehiculos.html',
        vehiculos=vehiculos,
        conductores=conductores
    )


# ================================
# CREAR VEHÍCULO
# ================================
@admin_vehiculos_bp.route('/dashboard/vehiculos/crear', methods=['POST'])
@login_required
def crear_vehiculo():
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    codigo = (request.form.get('codigo') or '').strip()
    marca = (request.form.get('marca') or '').strip()
    modelo = (request.form.get('modelo') or '').strip()
    anio = request.form.get('anio', type=int)
    placa = (request.form.get('placa') or '').strip()
    estado = (request.form.get('estado') or 'activo').strip().lower()
    id_usuario = request.form.get('id_usuario', type=int)  # puede ser 0

    if not codigo:
        flash('El código del vehículo es obligatorio.', 'warning')
        return redirect(url_for('admin_vehiculos.listar_vehiculos'))

    if Vehiculo.query.filter_by(codigo=codigo).first():
        flash(f'Ya existe un vehículo con código {codigo}.', 'warning')
        return redirect(url_for('admin_vehiculos.listar_vehiculos'))

    if estado not in ('activo', 'inactivo'):
        estado = 'activo'

    # OJO: aceptar 0 como válido -> usar "is not None"
    if id_usuario is not None:
        conductor = Usuario.query.get(id_usuario)
        if not conductor or conductor.rol != 'conductor':
            flash('El usuario seleccionado no es un conductor válido.', 'warning')
            return redirect(url_for('admin_vehiculos.listar_vehiculos'))
    else:
        conductor = None

    v = Vehiculo(
        codigo=codigo,
        marca=marca or None,
        modelo=modelo or None,
        anio=anio,
        placa=placa or None,
        estado=estado,
        id_usuario=id_usuario if conductor else None
    )

    db.session.add(v)
    db.session.commit()

    flash(f'Vehículo {codigo} creado correctamente.', 'success')
    return redirect(url_for('admin_vehiculos.listar_vehiculos'))


# ================================
# ACTIVAR / DESACTIVAR VEHÍCULO
# ================================
@admin_vehiculos_bp.route('/dashboard/vehiculos/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_vehiculo(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    v = Vehiculo.query.get_or_404(id)
    v.estado = 'inactivo' if (v.estado or '').lower() == 'activo' else 'activo'
    db.session.commit()

    flash(f'Vehículo {v.codigo} ahora está {v.estado}.', 'success')
    return redirect(url_for('admin_vehiculos.listar_vehiculos'))


# ================================
# ELIMINAR VEHÍCULO
# ================================
@admin_vehiculos_bp.route('/dashboard/vehiculos/<int:id>/eliminar', methods=['POST'])
@login_required
def eliminar_vehiculo(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    v = Vehiculo.query.get_or_404(id)
    codigo = v.codigo
    db.session.delete(v)
    db.session.commit()
    flash(f'Vehículo {codigo} eliminado.', 'success')
    return redirect(url_for('admin_vehiculos.listar_vehiculos'))


# ================================
# ASIGNAR / DESASIGNAR CONDUCTOR
# ================================
@admin_vehiculos_bp.route('/dashboard/vehiculos/<int:id>/asignar', methods=['POST'])
@login_required
def asignar_vehiculo(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    v = Vehiculo.query.get_or_404(id)
    id_usuario = request.form.get('id_usuario', type=int)  # puede ser 0

    # Aceptar 0 -> usar "is not None"
    if id_usuario is not None:
        conductor = Usuario.query.get(id_usuario)
        if not conductor or conductor.rol != 'conductor':
            flash('El usuario seleccionado no es un conductor válido.', 'warning')
            return redirect(url_for('admin_vehiculos.listar_vehiculos'))

        v.id_usuario = id_usuario
        db.session.commit()
        flash(f'Vehículo {v.codigo} asignado a {conductor.nombre}.', 'success')
    else:
        v.id_usuario = None
        db.session.commit()
        flash(f'Asignación removida del vehículo {v.codigo}.', 'info')

    return redirect(url_for('admin_vehiculos.listar_vehiculos'))
