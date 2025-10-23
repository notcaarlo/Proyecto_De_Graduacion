# Este archivo solo marca la carpeta 'routes' como paquete importable
# y puede usarse para importar todos los blueprints si lo deseas.

from app.routes.auth import auth_bp

__all__ = ['auth_bp']
