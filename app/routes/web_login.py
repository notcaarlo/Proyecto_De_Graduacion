from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app.models import Usuario

web_login_bp = Blueprint('web_login', __name__)

@web_login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        usuario = Usuario.query.filter_by(username=username).first()
        if not usuario or not check_password_hash(usuario.password_hash, password):
            flash('Usuario o contraseña incorrectos.', 'danger')
            return render_template('login.html')

        login_user(usuario)
        flash(f'Bienvenido {usuario.nombre} ({usuario.rol})', 'success')

        if usuario.rol == 'admin':
            return redirect(url_for('dashboard.dashboard'))
        else:
            return redirect(url_for('conductor.perfil_conductor'))

    return render_template('login.html')

@web_login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('web_login.login'))

@web_login_bp.route('/perfil_redirect')
@login_required
def perfil_redirect():
    if current_user.rol == 'admin':
        return redirect(url_for('dashboard.dashboard'))
    elif current_user.rol == 'conductor':
        return redirect(url_for('conductor.perfil_conductor'))
    else:
        flash('Rol desconocido o sin permisos.', 'danger')
        return redirect(url_for('web_login.logout'))