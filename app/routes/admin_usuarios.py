from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask import jsonify, current_app 
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from sqlalchemy import func, desc 
from database.conexion import db
from app.models import Usuario, Alerta, SesionConduccion, Vehiculo
import pandas as pd
import io
import requests 
from datetime import datetime

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
    niveles = {(nivel or 'N/A').lower(): count for nivel, count in nivel_counts}

    # Últimas alertas registradas
    ultimas_alertas = (
        Alerta.query.filter_by(id_usuario=u.id)
        .order_by(Alerta.id.desc())
        .limit(10)
        .all()
    )
    return render_template(
        'admin_usuario_detalle.html',
        user=u,
        total_sesiones=total_sesiones,
        total_alertas=total_alertas,
        vehiculos_top=vehiculos_top,
        niveles=niveles,
        ultimas_alertas=ultimas_alertas
    )
    
@admin_usuarios_bp.route('/dashboard/usuarios/<int:id>/exportar_excel')
@login_required
def exportar_excel(id):
    if not _solo_admin():
        return redirect(url_for('web_login.perfil_redirect'))
    try:
        u = Usuario.query.get_or_404(id)
        # ... (código de excel omitido por brevedad) ...
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
            .all()
        )
        # Alertas agrupadas por nivel
        nivel_counts = (
            db.session.query(Alerta.nivel_somnolencia, func.count(Alerta.id))
            .filter(Alerta.id_usuario == u.id)
            .group_by(Alerta.nivel_somnolencia)
            .all()
        )
        niveles = {(nivel or 'N/A').lower(): count for nivel, count in nivel_counts}
        # Últimas alertas registradas
        todas_las_alertas = (
            Alerta.query.filter_by(id_usuario=u.id)
            .order_by(Alerta.id.desc())
            .all()
        )
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Pestaña 1: Resumen
            df_resumen = pd.DataFrame([
                ("Usuario", u.nombre),
                ("Username", u.username),
                ("Total de Sesiones", total_sesiones),
                ("Total de Alertas", total_alertas)
            ], columns=["Métrica", "Valor"])
            df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
            # Pestaña 2: Alertas por Nivel
            if niveles:
                df_niveles = pd.DataFrame(list(niveles.items()), columns=['Nivel', 'Cantidad'])
            else:
                df_niveles = pd.DataFrame(columns=['Nivel', 'Cantidad'])
            df_niveles.to_excel(writer, sheet_name='Alertas por Nivel', index=False)
            # Pestaña 3: Vehículos Usados
            if vehiculos_top:
                df_vehiculos = pd.DataFrame(vehiculos_top, columns=['Vehículo', 'Sesiones'])
            else:
                df_vehiculos = pd.DataFrame(columns=['Vehículo', 'Sesiones'])
            df_vehiculos.to_excel(writer, sheet_name='Vehículos Usados', index=False)
            # Pestaña 4: Historial de Alertas
            if todas_las_alertas:
                alertas_data = [
                    {
                        "ID": a.id,
                        "Fecha": a.fecha.strftime('%d/%m/%Y') if a.fecha else None,
                        "Hora": a.hora.strftime('%H:%M:%S') if a.hora else None,
                        "Nivel": a.nivel_somnolencia,
                        "Nota": a.nota,
                        "ID Vehículo": a.id_vehiculo
                    } for a in todas_las_alertas
                ]
                df_alertas = pd.DataFrame(alertas_data)
            else:
                df_alertas = pd.DataFrame(columns=["ID", "Fecha", "Hora", "Nivel", "Nota", "ID Vehículo"])
            
            df_alertas.to_excel(writer, sheet_name='Historial de Alertas', index=False)
            
        output.seek(0)
        fecha_hoy = datetime.now().strftime('%Y-%m-%d')
        filename = f"reporte_usuario_{u.username}_{fecha_hoy}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        flash(f'Error al generar el archivo Excel: {e}', 'danger')
        return redirect(url_for('admin_usuarios.ver_usuario', id=id))

def _call_gemini_api(prompt_text):
    """
    Llama a la API REST de Gemini. No usa la librería de Python para evitar conflictos.
    """
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        return "Error: GEMINI_API_KEY no está configurada en el servidor."

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro-latest:generateContent?key={api_key}"
    
    headers = {"Content-Type": "application/json"}
    
    data = {
        "contents": [{
            "parts": [{"text": prompt_text}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=20)
        response.raise_for_status() # Lanza un error si la respuesta es 4xx o 5xx
        
        # Extraer el texto de la respuesta
        result = response.json()
        return result['candidates'][0]['content']['parts'][0]['text']
        
    except requests.exceptions.RequestException as e:
        print(f"[Gemini API] Error en la solicitud: {e}")
        return f"Error al contactar la API de Gemini: {e}"
    except (KeyError, IndexError) as e:
        print(f"[Gemini API] Error al parsear la respuesta: {e}")
        print(f"[Gemini API] Respuesta recibida: {response.text}")
        return "Error: La API de IA devolvió una respuesta inesperada."


@admin_usuarios_bp.route('/api/usuario/<int:id>/generar_recomendacion', methods=['GET'])
@login_required
def generar_recomendacion(id):
    if not _solo_admin():
        return jsonify({"error": "No autorizado"}), 403

    u = Usuario.query.get_or_404(id)
    
    # Métricas de tarjetas
    total_sesiones = db.session.query(func.count(SesionConduccion.id)) \
        .filter(SesionConduccion.id_usuario == u.id).scalar() or 0
    total_alertas = db.session.query(func.count(Alerta.id)) \
        .filter(Alerta.id_usuario == u.id).scalar() or 0

    # Alertas por nivel
    nivel_counts = (
        db.session.query(Alerta.nivel_somnolencia, func.count(Alerta.id))
        .filter(Alerta.id_usuario == u.id)
        .group_by(Alerta.nivel_somnolencia)
        .all()
    )
    # Convertir a un string legible
    niveles_str = ", ".join([f"{count} {nivel}" for nivel, count in nivel_counts]) or "Ninguna"

    # Alertas por hora (similar a dashboard.py, pero para un usuario)
    hora_col = func.extract('hour', Alerta.hora)
    alertas_por_hora_db = (
        db.session.query(
            hora_col.label('hora'), 
            func.count(Alerta.id).label('cantidad')
        )
        .filter(Alerta.id_usuario == u.id)
        .group_by(hora_col)
        .order_by(desc('cantidad'))
        .limit(3) # Top 3 horas de mayor riesgo
        .all()
    )
    horas_riesgo_str = ", ".join([f"{int(h.cantidad)} alertas a las {int(h.hora):02d}:00" for h in alertas_por_hora_db]) or "Sin patrón claro"

    # Tasa de Riesgo (Alertas por Hora)
    total_horas = (
        db.session.query(
            (func.sum(
                func.extract('epoch', func.coalesce(SesionConduccion.fecha_fin, func.now())) - 
                func.extract('epoch', SesionConduccion.fecha_inicio)
            ) / 3600.0)
        )
        .filter(SesionConduccion.id_usuario == u.id)
        .scalar() or 0.0
    )
    tasa_riesgo = (total_alertas / total_horas) if total_horas > 0 else 0
    
    # --- Prompt ---
    prompt = f"""
    Eres un analista experto en seguridad de flotas de transporte pesado.
    Tu trabajo es analizar los datos de un conductor y generar una recomendación clara y accionable para un administrador.
    
    Responde en español y usa Markdown para formatear tu respuesta. 
    Tu respuesta debe ser un análisis profesional en 3 secciones:
    1.  **Diagnóstico General:** Un resumen del perfil de riesgo del conductor.
    2.  **Puntos Clave de Riesgo:** 2 o 3 viñetas identificando los patrones peligrosos.
    3.  **Recomendación Accionable:** 1 o 2 acciones claras que el administrador debe tomar.

    Aquí están los datos del conductor '{u.nombre}':

    --- DATOS DE RENDIMIENTO ---
    - Tasa de Riesgo (Alertas por Hora): {tasa_riesgo:.2f}
    - Total de Jornadas Conducidas: {total_sesiones}
    - Total de Alertas Acumuladas: {total_alertas}
    - Desglose de Alertas por Nivel: {niveles_str}
    - Horas de Mayor Riesgo (Patrones): {horas_riesgo_str}
    --- FIN DE DATOS ---

    Genera el análisis.
    """

    # --- 3. Llamar a la API y devolver la respuesta ---
    try:
        recomendacion = _call_gemini_api(prompt)
        return jsonify({'recomendacion': recomendacion})
    except Exception as e:
        return jsonify({"error": f"Error al generar la recomendación: {e}"}), 500