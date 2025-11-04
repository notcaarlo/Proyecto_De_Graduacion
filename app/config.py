import os
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

# --- NUEVO: Definir el directorio base de la app ---
# (Esto asume que config.py está dentro de la carpeta 'app')
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuración de Flask-Mail
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    
    # Email de destino para las alertas
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

    # =========================================================
    # === INICIO: NUEVA CARPETA DE UPLOAD ===
    # =========================================================
    # Crea una carpeta 'evidencia' dentro de 'app/static/'
    UPLOAD_FOLDER = os.path.join(basedir, 'static/evidencia')
    # =========================================================
    # === FIN: NUEVA CARPETA DE UPLOAD ===
    # =========================================================