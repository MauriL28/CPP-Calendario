import os
from datetime import datetime, timedelta, timezone

from flask_jwt_extended import JWTManager, create_access_token

from db import SinBaseDeDatos, cursor


def horas_sesion():
    texto = os.environ.get("SESION_HORAS", "12")
    try:
        horas = float(texto)
    except (TypeError, ValueError):
        return timedelta(hours=12)
    if horas <= 0:
        return timedelta(hours=12)
    return timedelta(hours=horas)


def configurar_jwt(app):
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-calendario")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = horas_sesion()
    jwt = JWTManager(app)

    @jwt.token_in_blocklist_loader
    def token_revocado(_cabecera, payload):
        return esta_revocado(payload)


def emitir_token(usuario_id, rol, delegaciones, nombre, departamento, login_nombre=""):
    return create_access_token(
        identity=str(usuario_id),
        additional_claims={
            "rol": rol,
            "delegaciones": delegaciones,
            "nombre": nombre,
            "departamento": departamento,
            "login": login_nombre,
        },
        expires_delta=horas_sesion(),
    )


def revocar_token(payload):
    expira = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    with cursor() as cur:
        cur.execute("DELETE FROM token_revocado WHERE expira <= now()")
        cur.execute(
            """
            INSERT INTO token_revocado (jti, expira)
            VALUES (%s, %s)
            ON CONFLICT (jti) DO NOTHING
            """,
            (payload["jti"], expira),
        )


def esta_revocado(payload):
    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT
                    EXISTS (SELECT 1 FROM token_revocado WHERE jti = %s) AS revocado,
                    u.activo,
                    u.rol::text AS rol
                FROM usuario u
                WHERE u.id = %s::uuid
                """,
                (payload.get("jti"), payload.get("sub")),
            )
            fila = cur.fetchone()
    except SinBaseDeDatos:
        return False
    if fila is None:
        return True
    return (
        bool(fila["revocado"])
        or not fila["activo"]
        or fila["rol"] != payload.get("rol")
    )
