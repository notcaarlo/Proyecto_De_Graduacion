from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
# Importamos todos los modelos
from app.models import Alerta, Usuario, Vehiculo, SesionConduccion
from database.conexion import db
# Importamos funciones SQL avanzadas y 'request'
from sqlalchemy import func, desc
from datetime import datetime, timedelta, date

dashboard_bp = Blueprint('dashboard', __name__)


# ==========================
# DASHBOARD PRINCIPAL (CON FILTROS DE FECHA)
# ==========================
@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    # 🔐 Solo administradores pueden acceder
    if current_user.rol != 'admin':
        flash('Acceso denegado: solo administradores pueden ver el dashboard.', 'danger')
        return redirect(url_for('web_login.perfil_usuario'))

    # === 0. LÓGICA DE FILTROS DE FECHA ===
    rango = request.args.get('rango', 'todo') # Por defecto, 'todo'
    today = date.today()
    start_date = None
    # Usamos datetime.now() para end_date para incluir siempre la hora actual
    end_date = datetime.now() 

    if rango == 'hoy':
        start_date = datetime(today.year, today.month, today.day) # Hoy a las 00:00
    elif rango == 'semana':
        # Hoy y los 6 días anteriores (total 7 días)
        start_date = datetime.combine(today - timedelta(days=6), datetime.min.time())
    elif rango == 'mes':
        start_date = datetime(today.year, today.month, 1) # Primer día del mes actual

    # Creamos listas de filtros para aplicar a las consultas
    alerta_filter = []
    sesion_filter = []
    
    if start_date:
        alerta_filter = [Alerta.fecha >= start_date, Alerta.fecha <= end_date]
        # Para sesiones, filtramos por fecha de inicio
        # y permitimos las que terminaron en el rango O las que siguen activas
        sesion_filter = [
            SesionConduccion.fecha_inicio >= start_date,
            (SesionConduccion.fecha_fin <= end_date) | (SesionConduccion.fecha_fin == None)
        ]


    # === 1. MÉTRICAS DE TARJETAS (Sin filtro) ===
    # (Estas métricas suelen ser globales y no de rango)
    total_usuarios = Usuario.query.filter(Usuario.rol != 'inactivo').count()
    total_conductores = Usuario.query.filter_by(rol='conductor').count()
    total_vehiculos = Vehiculo.query.count()
    vehiculos_activos = Vehiculo.query.filter_by(estado='activo').count() 
    sesiones_activas_count = SesionConduccion.query.filter_by(estado='activa').count() 

    
    # === 2. GRÁFICO 1: "ALERTAS POR HORA DEL DÍA" (Corregido) ===
    hora_col = func.extract('hour', Alerta.hora)
    alertas_por_hora_db = (
        db.session.query(
            hora_col.label('hora'), 
            func.count(Alerta.id).label('cantidad')
        )
        .filter(*alerta_filter) # Aplicamos el filtro de fecha
        .group_by(hora_col)
        .all()
    )
    horas_labels = [f"{h:02d}:00" for h in range(24)]
    horas_data = [0] * 24
    for h in alertas_por_hora_db:
        if h.hora is not None:
            horas_data[int(h.hora)] = h.cantidad

            
    # === 3. GRÁFICO 2: "TASA DE RIESGO" (Filtrado) ===
    
    # Subconsulta A: Total de horas conducidas (Filtrada)
    sub_horas = (
        db.session.query(
            SesionConduccion.id_usuario,
            (func.sum(
                func.extract('epoch', func.coalesce(SesionConduccion.fecha_fin, func.now())) - 
                func.extract('epoch', SesionConduccion.fecha_inicio)
            ) / 3600.0).label('total_horas')
        )
        .filter(*sesion_filter) # Aplicamos el filtro de fecha
        .group_by(SesionConduccion.id_usuario)
        .subquery()
    )

    # Subconsulta B: Total de alertas (Filtrada)
    sub_alertas = (
        db.session.query(
            Alerta.id_usuario,
            func.count(Alerta.id).label('total_alertas')
        )
        .filter(*alerta_filter) # Aplicamos el filtro de fecha
        .group_by(Alerta.id_usuario)
        .subquery()
    )

    # Consulta Principal: Unimos todo
    data_riesgo = (
        db.session.query(
            Usuario.nombre,
            func.coalesce(sub_alertas.c.total_alertas, 0).label('alertas'),
            func.coalesce(sub_horas.c.total_horas, 0.0).label('horas')
        )
        .outerjoin(sub_alertas, Usuario.id == sub_alertas.c.id_usuario)
        .outerjoin(sub_horas, Usuario.id == sub_horas.c.id_usuario)
        .filter(Usuario.rol == 'conductor')
        .all()
    )
    
    riesgo_calculado = []
    for d in data_riesgo:
        tasa = (d.alertas / d.horas) if d.horas > 0 else 0
        riesgo_calculado.append({'nombre': d.nombre, 'tasa': round(tasa, 2)})
        
    top_5_riesgo = sorted(riesgo_calculado, key=lambda x: x['tasa'], reverse=True)[:5]

    riesgo_labels = [d['nombre'] for d in top_5_riesgo]
    riesgo_data = [d['tasa'] for d in top_5_riesgo]
    

    # === 4. TABLA 1: "ÚLTIMAS ALERTAS" (Filtrada) ===
    ultimas_alertas = (
        db.session.query(Alerta, Usuario.nombre, Vehiculo.codigo)
        .join(Usuario, Alerta.id_usuario == Usuario.id, isouter=True)
        .join(Vehiculo, Alerta.id_vehiculo == Vehiculo.id, isouter=True)
        .filter(*alerta_filter) # Aplicamos el filtro de fecha
        .order_by(Alerta.id.desc())
        .limit(10)
        .all()
    )

    
    # === 5. TABLA 2: "JORNADAS ACTIVAS" (Sin filtro) ===
    jornadas_activas = (
        db.session.query(Usuario.nombre, Vehiculo.codigo, SesionConduccion.fecha_inicio)
        .join(Usuario, SesionConduccion.id_usuario == Usuario.id)
        .join(Vehiculo, SesionConduccion.id_vehiculo == Vehiculo.id)
        .filter(SesionConduccion.estado == 'activa')
        .order_by(SesionConduccion.fecha_inicio.desc())
        .all()
    )

    # =========================================================
    # === INICIO: LÍNEA CORREGIDA PARA NOTIFICACIONES ===
    # =========================================================
    # Obtenemos el ID de la alerta más reciente en la base de datos
    last_seen_alert_id = db.session.query(func.max(Alerta.id)).scalar() or 0
    # =========================================================
    # === FIN: LÍNEA CORREGIDA ===
    # =========================================================

    # === 6. RENDERIZAMOS TODO ===
    return render_template(
        'dashboard.html',
        user=current_user, # Añadido para el saludo
        
        # Métricas de Tarjetas
        total_usuarios=total_usuarios,
        total_conductores=total_conductores,
        total_vehiculos=total_vehiculos,
        vehiculos_activos=vehiculos_activos,
        sesiones_activas=sesiones_activas_count,
        
        # Gráfico 1 (Horas)
        horas_labels=horas_labels,
        horas_data=horas_data,
        
        # Gráfico 2 (Riesgo)
        riesgo_labels=riesgo_labels,
        riesgo_data=riesgo_data,
        
        # Tablas
        ultimas_alertas=ultimas_alertas,
        jornadas_activas=jornadas_activas,
        
        # Variable de estado para los botones
        rango_activo=rango,

        # --- AÑADIDA LA VARIABLE QUE FALTABA ---
        last_seen_alert_id=last_seen_alert_id 
    )


# ==========================
# ENDPOINT: ESTADÍSTICAS POR USUARIO (Sin cambios)
# ==========================
@dashboard_bp.route('/api/admin/estadisticas/<int:id_usuario>')
@login_required
def estadisticas_usuario(id_usuario):
    # (Tu código original va aquí, no necesita cambios)
    pass # Solo como placeholder