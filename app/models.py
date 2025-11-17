from flask_login import UserMixin
from database.conexion import db
from datetime import datetime
class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='conductor')
    fecha_registro = db.Column(db.DateTime, default=datetime.now)

    alertas = db.relationship('Alerta', backref='usuario', lazy=True)
    vehiculos = db.relationship('Vehiculo', backref='usuario', lazy=True)
    sesiones = db.relationship('SesionConduccion', backref='usuario', lazy=True)

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<Usuario {self.username}>'
class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)
    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    anio = db.Column(db.Integer)
    placa = db.Column(db.String(20))
    estado = db.Column(db.String(20), default='activo')
    
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    alertas = db.relationship('Alerta', backref='vehiculo', lazy=True)
    sesiones = db.relationship('SesionConduccion', backref='vehiculo', lazy=True)

    def __repr__(self):
        return f'<Vehiculo {self.codigo}>'
class Alerta(db.Model):
    __tablename__ = 'alertas'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    id_vehiculo = db.Column(db.Integer, db.ForeignKey('vehiculos.id'))
    id_sesion = db.Column(db.Integer, db.ForeignKey('sesiones_conduccion.id'))
    fecha = db.Column(db.Date, default=datetime.now)
    hora = db.Column(db.Time, default=lambda: datetime.now().time())
    duracion = db.Column(db.Float)
    nota = db.Column(db.String(255))
    nivel_somnolencia = db.Column(db.String(20))
    evidencia_url = db.Column(db.String(255), nullable=True)
    
    def __repr__(self):
        return f'<Alerta {self.id} - Usuario {self.id_usuario}>'
class SesionConduccion(db.Model):
    __tablename__ = 'sesiones_conduccion'

    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    id_vehiculo = db.Column(db.Integer, db.ForeignKey('vehiculos.id'))
    fecha_inicio = db.Column(db.DateTime, default=datetime.now)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.String(20), default='activa')

    def finalizar(self):
        self.fecha_fin = datetime.now()
        self.estado = 'finalizada'

    def __repr__(self):
        return f'<Sesion {self.id} - Usuario {self.id_usuario}>'