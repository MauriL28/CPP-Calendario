import os

from flask_jwt_extended import JWTManager, create_access_token


def configurar_jwt(app):
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-calendario")
    JWTManager(app)


def emitir_token(usuario_id, rol, delegaciones):
    return create_access_token(
        identity=str(usuario_id),
        additional_claims={"rol": rol, "delegaciones": delegaciones},
    )
