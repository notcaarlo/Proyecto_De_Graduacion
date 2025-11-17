from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from flask_mail import Mail
from app.config import Config
from database.conexion import db

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)
    db.init_app(app)
    
    mail.init_app(app)

    from app import models
    from app.models import Usuario

    login_manager = LoginManager(app)
    login_manager.login_view = 'web_login.login'
    login_manager.login_message = "Por favor, inicia sesión para acceder al panel."

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))
    
    from app.routes.auth import auth_bp
    from app.routes.vehiculos import vehiculos_bp
    from app.routes.alertas import alertas_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.web_login import web_login_bp
    from app.routes.admin_usuarios import admin_usuarios_bp
    from app.routes.admin_sesiones import admin_sesiones_bp
    from app.routes.conductor import conductor_bp
    from app.routes.admin_vehiculos import admin_vehiculos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(vehiculos_bp)
    app.register_blueprint(alertas_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(web_login_bp)
    app.register_blueprint(admin_usuarios_bp)
    app.register_blueprint(admin_sesiones_bp)
    app.register_blueprint(conductor_bp)
    app.register_blueprint(admin_vehiculos_bp)
    
    @app.route('/')
    def home():
        return {"message": "Servidor Flask funcionando correctamente"}

    return app