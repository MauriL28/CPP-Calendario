import psycopg
from flask import Blueprint, jsonify, request

from db import SinBaseDeDatos, cursor
from seguridad import emitir_token

bp = Blueprint("auth", __name__)


@bp.post("/login")
def login():
    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("login")
    clave = cuerpo.get("clave")
    if not isinstance(login_nombre, str) or not isinstance(clave, str):
        return jsonify(error="Credenciales incorrectas"), 401

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.rol, g.codigo AS delegacion
                FROM usuario u
                LEFT JOIN departamento d ON d.id = u.departamento_id
                LEFT JOIN delegacion g ON g.id = d.delegacion_id
                WHERE u.login = %s
                  AND u.clave IS NOT NULL
                  AND u.clave = crypt(%s, u.clave)
                """,
                (login_nombre, clave),
            )
            fila = cur.fetchone()
            if fila is None:
                return jsonify(error="Credenciales incorrectas"), 401
            if fila["rol"] == "admin":
                cur.execute(
                    """
                    SELECT codigo
                    FROM delegacion
                    ORDER BY codigo = '60I' DESC, codigo
                    """
                )
                delegaciones = [row["codigo"] for row in cur.fetchall()]
            elif fila["delegacion"]:
                delegaciones = [fila["delegacion"]]
            else:
                return jsonify(error="Credenciales incorrectas"), 401
            rol = fila["rol"]
            usuario_id = fila["id"]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(access_token=emitir_token(usuario_id, rol, delegaciones))
