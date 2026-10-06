from datetime import datetime

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, jwt_required

from db import SinBaseDeDatos, cursor

bp = Blueprint("festivos", __name__)


@bp.get("/festivos")
@jwt_required()
def listar():
    try:
        with cursor() as cur:
            cur.execute("SELECT fecha, nombre FROM festivo ORDER BY fecha")
            filas = cur.fetchall()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503
    return jsonify([_fila(fila["fecha"], fila["nombre"]) for fila in filas])


@bp.post("/festivos")
@jwt_required()
def crear():
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    fecha, error = _fecha(cuerpo.get("fecha"))
    if error:
        return error
    nombre, error = _nombre(cuerpo.get("nombre"))
    if error:
        return error
    try:
        with cursor() as cur:
            cur.execute("SELECT 1 FROM festivo WHERE fecha = %s", (fecha,))
            if cur.fetchone() is not None:
                return jsonify(error="Ya hay un festivo en esa fecha"), 409
            cur.execute(
                "INSERT INTO festivo (fecha, nombre) VALUES (%s, %s)",
                (fecha, nombre),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation:
        return jsonify(error="Ya hay un festivo en esa fecha"), 409
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503
    return jsonify(_fila(fecha, nombre)), 201


@bp.delete("/festivos/<fecha_texto>")
@jwt_required()
def borrar(fecha_texto):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403
    fecha, error = _fecha(fecha_texto)
    if error:
        return error
    try:
        with cursor() as cur:
            cur.execute("DELETE FROM festivo WHERE fecha = %s", (fecha,))
            if cur.rowcount == 0:
                return jsonify(error="No se ha encontrado el festivo"), 404
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503
    return "", 204


def _fila(fecha, nombre):
    return {"fecha": fecha.isoformat(), "nombre": nombre}


def _fecha(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, (jsonify(error="La fecha no es válida"), 400)


def _nombre(valor):
    if not isinstance(valor, str) or not valor.strip():
        return None, (jsonify(error="Faltan datos"), 400)
    texto = valor.strip()
    if len(texto) > 120:
        return None, (jsonify(error="El nombre es demasiado largo"), 400)
    return texto, None
