import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from horas import hora_texto, parse_hora

bp = Blueprint("trabajadores", __name__)


@bp.post("/trabajadores")
@jwt_required()
def crear_trabajador():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    nombre = cuerpo.get("nombre")
    login_nombre = cuerpo.get("login")
    clave = cuerpo.get("clave")
    grupo = cuerpo.get("grupo")
    hora_inicio = parse_hora(cuerpo.get("hora_inicio"))
    hora_fin = parse_hora(cuerpo.get("hora_fin"))
    vacaciones = _numero(cuerpo.get("vacaciones"))
    horas_contrato = _numero(cuerpo.get("horas_contrato"))
    if not all(isinstance(valor, str) and valor.strip() for valor in (nombre, login_nombre, clave)):
        return jsonify(error="Faltan datos"), 400
    if grupo not in ("STEF", "ETT"):
        return jsonify(error="El grupo tiene que ser STEF o ETT"), 400
    if hora_inicio == "mal" or hora_fin == "mal":
        return jsonify(error="La hora no es válida"), 400
    if hora_inicio is None or hora_fin is None or vacaciones is None or horas_contrato is None:
        return jsonify(error="Faltan datos"), 400
    if vacaciones == "mal" or horas_contrato == "mal":
        return jsonify(error="Faltan datos"), 400

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT departamento_id
                FROM usuario
                WHERE id = %s AND rol = 'mando'
                """,
                (get_jwt_identity(),),
            )
            mando = cur.fetchone()
            if mando is None or mando["departamento_id"] is None:
                return jsonify(error="No autorizado"), 403
            cur.execute(
                "SELECT 1 FROM usuario WHERE login = %s",
                (login_nombre.strip(),),
            )
            if cur.fetchone() is not None:
                return jsonify(error="El login ya existe"), 409
            cur.execute(
                """
                INSERT INTO usuario (
                    nombre, login, clave, rol, grupo, departamento_id,
                    horario_inicio, horario_fin, vacaciones, horas_contrato
                )
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'trabajador', %s, %s, %s, %s, %s, %s)
                RETURNING nombre, login, rol, grupo,
                          horario_inicio, horario_fin, vacaciones, horas_contrato
                """,
                (
                    nombre.strip(),
                    login_nombre.strip(),
                    clave,
                    grupo,
                    mando["departamento_id"],
                    hora_inicio,
                    hora_fin,
                    vacaciones,
                    horas_contrato,
                ),
            )
            creado = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        nombre=creado["nombre"],
        login=creado["login"],
        rol=creado["rol"],
        grupo=creado["grupo"],
        hora_inicio=hora_texto(creado["horario_inicio"]),
        hora_fin=hora_texto(creado["horario_fin"]),
        vacaciones=float(creado["vacaciones"]),
        horas_contrato=float(creado["horas_contrato"]),
    ), 201


def _numero(valor):
    if isinstance(valor, bool) or valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        if valor < 0:
            return "mal"
        return float(valor)
    if isinstance(valor, str):
        try:
            numero = float(valor.strip().replace(",", "."))
        except ValueError:
            return "mal"
        if numero < 0:
            return "mal"
        return numero
    return "mal"
