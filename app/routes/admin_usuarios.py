from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func  # <-- necesario para agregados
from database.conexion import db
from app.models import Usuario, Alerta, SesionConduccion, Vehiculo

admin_usuarios_bp = Blueprint('admin_usuarios', __name__)

def _solo_admin():
    if not current_user.is_authenticated or current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores.', 'danger')
        return False
    return True

@admin_usuarios_bp.route('/dashboard/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))
    usuarios = Usuario.query.order_by(Usuario.id.desc()).all()
    return render_template('admin_usuarios.html', usuarios=usuarios)

@admin_usuarios_bp.route('/dashboard/usuarios/crear', methods=['POST'])
@login_required
def crear_usuario():
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))
    nombre = (request.form.get('nombre') or '').strip()
    username = (request.form.get('username') or '').strip()
    correo = (request.form.get('correo') or '').strip()
    password = (request.form.get('password') or '').strip()
    rol = (request.form.get('rol') or 'conductor').strip().lower()
    if not nombre or not username or not password:
        flash('Nombre, usuario y contraseña son obligatorios.', 'warning')
        return redirect(url_for('admin_usuarios.listar_usuarios'))
    if Usuario.query.filter_by(username=username).first():
        flash('Ese nombre de usuario ya existe.', 'warning')
        return redirect(url_for('admin_usuarios.listar_usuarios'))
    if rol not in ('admin', 'conductor'):
        rol = 'conductor'
    user = Usuario(
        nombre=nombre, username=username, correo=correo or None,
        password_hash=generate_password_hash(password), rol=rol
    )
    db.session.add(user); db.session.commit()
    flash(f'Usuario {username} creado correctamente.', 'success')
    return redirect(url_for('admin_usuarios.listar_usuarios'))

@admin_usuarios_bp.route('/dashboard/usuarios/<int:id>/rol', methods=['POST'])
@login_required
def cambiar_rol(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))
    nuevo_rol = (request.form.get('rol') or '').strip().lower()
    if nuevo_rol not in ('admin', 'conductor'):
        flash('Rol inválido.', 'warning')
        return redirect(url_for('admin_usuarios.listar_usuarios'))
    u = Usuario.query.get_or_404(id)
    if u.id == current_user.id and nuevo_rol != 'admin':
        flash('No puedes quitarte el rol de admin a ti mismo.', 'warning')
        return redirect(url_for('admin_usuarios.listar_usuarios'))
    u.rol = nuevo_rol
    db.session.commit()
    flash(f'Rol de {u.username} cambiado a {nuevo_rol}.', 'success')
    return redirect(url_for('admin_usuarios.listar_usuarios'))

@admin_usuarios_bp.route('/dashboard/usuarios/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_estado(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))
    u = Usuario.query.get_or_404(id)
    if u.rol == 'admin':
        flash('No puedes desactivar una cuenta admin desde aquí.', 'warning')
        return redirect(url_for('admin_usuarios.listar_usuarios'))
    if u.rol == 'inactivo':
        u.rol = 'conductor'; estado_txt = 'activado'
    else:
        u.rol = 'inactivo'; estado_txt = 'desactivado'
    db.session.commit()
    flash(f'Usuario {u.username} {estado_txt}.', 'success')
    return redirect(url_for('admin_usuarios.listar_usuarios'))

@admin_usuarios_bp.route('/dashboard/usuarios/<int:id>', methods=['GET'])
@login_required
def ver_usuario(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))

    u = Usuario.query.get_or_404(id)

    # Total de sesiones
    total_sesiones = db.session.query(func.count(SesionConduccion.id)) \
        .filter(SesionConduccion.id_usuario == u.id).scalar() or 0

    # Total de alertas
    total_alertas = db.session.query(func.count(Alerta.id)) \
        .filter(Alerta.id_usuario == u.id).scalar() or 0

    # Vehículos más usados por el conductor
    vehiculos_top = (
        db.session.query(Vehiculo.codigo, func.count(SesionConduccion.id))
        .join(SesionConduccion, Vehiculo.id == SesionConduccion.id_vehiculo)
        .filter(SesionConduccion.id_usuario == u.id)
        .group_by(Vehiculo.codigo)
        .order_by(func.count(SesionConduccion.id).desc())
        .limit(5)
        .all()
    )

    # Alertas agrupadas por nivel (bajo, medio, alto)
    nivel_counts = (
        db.session.query(Alerta.nivel_somnolencia, func.count(Alerta.id))
        .filter(Alerta.id_usuario == u.id)
        .group_by(Alerta.nivel_somnolencia)
        .all()
    )

    # Convertimos a diccionario con clave en minúsculas (para colores)
    niveles = {(nivel or 'N/A').lower(): count for nivel, count in nivel_counts}

    # Últimas alertas registradas
    ultimas_alertas = (
        Alerta.query.filter_by(id_usuario=u.id)
        .order_by(Alerta.id.desc())
        .limit(10)
        .all()
    )

    # Renderizamos sin enviar las sesiones (ya no se usan en el HTML)
    return render_template(
        'admin_usuario_detalle.html',
        user=u,
        total_sesiones=total_sesiones,
        total_alertas=total_alertas,
        vehiculos_top=vehiculos_top,
        niveles=niveles,
        ultimas_alertas=ultimas_alertas
    )
