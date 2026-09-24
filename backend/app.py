from flask import Flask

from rutas.auth import bp as auth_bp
from rutas.departamentos import bp as departamentos_bp
from rutas.salud import registrar as registrar_salud
from rutas.trabajadores import bp as trabajadores_bp
from rutas.turnos import bp as turnos_bp
from rutas.usuarios import bp as usuarios_bp
from seguridad import configurar_jwt


def create_app():
    app = Flask(__name__)
    configurar_jwt(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(departamentos_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(trabajadores_bp)
    app.register_blueprint(turnos_bp)
    registrar_salud(app)
    return app


app = create_app()
