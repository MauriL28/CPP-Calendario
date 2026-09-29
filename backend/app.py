from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from rutas.auth import bp as auth_bp
from rutas.departamentos import bp as departamentos_bp
from rutas.fichajes import LIMITE_BYTES, MARGEN_MULTIPARTE
from rutas.fichajes import bp as fichajes_bp
from rutas.salud import registrar as registrar_salud
from rutas.trabajadores import bp as trabajadores_bp
from rutas.turnos import bp as turnos_bp
from rutas.usuarios import bp as usuarios_bp
from seguridad import configurar_jwt


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = LIMITE_BYTES + MARGEN_MULTIPARTE
    configurar_jwt(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(departamentos_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(trabajadores_bp)
    app.register_blueprint(turnos_bp)
    app.register_blueprint(fichajes_bp)
    registrar_salud(app)

    @app.errorhandler(RequestEntityTooLarge)
    def archivo_demasiado_grande(_error):
        return jsonify(error="El archivo supera 10 MiB"), 400

    return app


app = create_app()
