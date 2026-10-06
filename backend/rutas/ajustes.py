from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import UUID

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor

bp = Blueprint("ajustes", __name__)


@bp.post("/ajustes")
@jwt_required()
def crear():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("usuario_afectado")
    if not isinstance(login_nombre, str) or not login_nombre.strip():
        return jsonify(error="Faltan datos"), 400
    fecha, error = _fecha(cuerpo.get("fecha"))
    if error:
        return error
    horas, error = _horas(cuerpo.get("horas"))
    if error:
        return error
    motivo, error = _motivo(cuerpo.get("motivo"))
    if error:
        return error

    try:
        with cursor() as cur:
            mando = _mando(cur)
            if mando is None:
                return jsonify(error="No autorizado"), 403
            trabajador = _trabajador(cur, login_nombre.strip(), mando["departamento_id"])
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                """
                INSERT INTO ajuste (
                    fecha, horas, motivo, usuario_afectado_id, usuario_registra_id
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (fecha, horas, motivo, trabajador["id"], mando["id"]),
            )
            creado = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(_fila(creado["id"], fecha, horas, motivo, login_nombre.strip(), mando["nombre"])), 201


@bp.get("/ajustes")
@jwt_required()
def listar():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    login_nombre = request.args.get("usuario_afectado")
    if login_nombre is not None and not login_nombre.strip():
        login_nombre = None
    desde, error = _fecha_opcional(request.args.get("desde"))
    if error:
        return error
    hasta, error = _fecha_opcional(request.args.get("hasta"))
    if error:
        return error
    if desde is not None and hasta is not None and desde > hasta:
        return jsonify(error="desde no puede ser posterior a hasta"), 400

    try:
        with cursor() as cur:
            mando = _mando(cur)
            if mando is None:
                return jsonify(error="No autorizado"), 403
            trabajador_id = None
            if login_nombre is not None:
                trabajador = _trabajador(cur, login_nombre.strip(), mando["departamento_id"])
                if trabajador is None:
                    return jsonify(error="Ese trabajador no es de tu departamento"), 404
                trabajador_id = trabajador["id"]
            clausulas = ["afectado.departamento_id = %s", "afectado.rol = 'trabajador'"]
            params = [mando["departamento_id"]]
            if trabajador_id is not None:
                clausulas.append("a.usuario_afectado_id = %s")
                params.append(trabajador_id)
            if desde is not None:
                clausulas.append("a.fecha >= %s")
                params.append(desde)
            if hasta is not None:
                clausulas.append("a.fecha <= %s")
                params.append(hasta)
            cur.execute(
                f"""
                SELECT a.id, a.fecha, a.horas, a.motivo,
                       afectado.login AS usuario_afectado,
                       registra.nombre AS registra
                FROM ajuste a
                JOIN usuario afectado ON afectado.id = a.usuario_afectado_id
                JOIN usuario registra ON registra.id = a.usuario_registra_id
                WHERE {" AND ".join(clausulas)}
                ORDER BY a.fecha, a.id
                """,
                params,
            )
            filas = [_fila_bd(fila) for fila in cur.fetchall()]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(filas)


@bp.delete("/ajustes/<ajuste_id>")
@jwt_required()
def borrar(ajuste_id):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    try:
        identificador = UUID(ajuste_id)
    except ValueError:
        return jsonify(error="No se ha encontrado el ajuste"), 404

    try:
        with cursor() as cur:
            mando = _mando(cur)
            if mando is None:
                return jsonify(error="No autorizado"), 403
            cur.execute(
                """
                DELETE FROM ajuste AS a
                USING usuario AS afectado
                WHERE a.id = %s
                  AND a.usuario_afectado_id = afectado.id
                  AND afectado.rol = 'trabajador'
                  AND afectado.departamento_id = %s
                RETURNING a.id
                """,
                (identificador, mando["departamento_id"]),
            )
            if cur.fetchone() is None:
                return jsonify(error="No se ha encontrado el ajuste"), 404
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return "", 204


def _mando(cur):
    cur.execute(
        """
        SELECT id, nombre, departamento_id
        FROM usuario
        WHERE id = %s AND rol = 'mando'
        """,
        (get_jwt_identity(),),
    )
    mando = cur.fetchone()
    if mando is None or mando["departamento_id"] is None:
        return None
    return mando


def _trabajador(cur, login_nombre, departamento_id):
    cur.execute(
        """
        SELECT id
        FROM usuario
        WHERE login = %s
          AND rol = 'trabajador'
          AND departamento_id = %s
        """,
        (login_nombre, departamento_id),
    )
    return cur.fetchone()


def _fila(identificador, fecha, horas, motivo, login_nombre, registra):
    return {
        "id": str(identificador),
        "fecha": fecha.isoformat(),
        "horas": float(horas),
        "motivo": motivo,
        "usuario_afectado": login_nombre,
        "registra": registra,
    }


def _fila_bd(fila):
    return _fila(
        fila["id"],
        fila["fecha"],
        fila["horas"],
        fila["motivo"],
        fila["usuario_afectado"],
        fila["registra"],
    )


def _fecha(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, (jsonify(error="La fecha no es válida"), 400)


def _fecha_opcional(valor):
    if valor is None or valor == "":
        return None, None
    return _fecha(valor)


def _horas(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        horas = Decimal(str(valor)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None, (jsonify(error="Faltan datos"), 400)
    if horas == 0:
        return None, (jsonify(error="Las horas no pueden ser 0"), 400)
    if abs(horas) >= Decimal("1000000"):
        return None, (jsonify(error="Faltan datos"), 400)
    return horas, None


def _motivo(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None, (jsonify(error="Faltan datos"), 400)
    texto = valor.strip()
    if len(texto) > 500:
        return None, (jsonify(error="El motivo es demasiado largo"), 400)
    return texto, None
