from app import create_app
from database.conexion import db
import webbrowser
from threading import Timer

# Crear la aplicación Flask
app = create_app()

# Contexto de aplicación para base de datos
with app.app_context():
    db.create_all()
    
def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/login")
    
# --- Ejecución principal ---
if __name__ == "__main__":
    Timer(1, open_browser).start()
    app.run(host="0.0.0.0", port=5000, debug=False)