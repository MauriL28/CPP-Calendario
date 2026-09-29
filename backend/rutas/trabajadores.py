from datetime import date, datetime

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
    vacaciones = _numero(cuerpo.get("vacaciones"))
    horas_contrato = _numero(cuerpo.get("horas_contrato"))
    if not all(isinstance(valor, str) and valor.strip() for valor in (nombre, login_nombre, clave)):
        return jsonify(error="Faltan datos"), 400
    if grupo not in ("STEF", "ETT"):
        return jsonify(error="El grupo tiene que ser STEF o ETT"), 400
    if vacaciones is None or horas_contrato is None or vacaciones == "mal" or horas_contrato == "mal":
        return jsonify(error="Faltan datos"), 400
    filas, error = _horario_dias(cuerpo.get("horario_dias"))
    if error:
        return error
    desde, error = _desde(cuerpo.get("desde"))
    if error:
        return error

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
                    vacaciones, horas_contrato
                )
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'trabajador', %s, %s, %s, %s)
                RETURNING id, nombre, login, rol, grupo, vacaciones, horas_contrato
                """,
                (
                    nombre.strip(),
                    login_nombre.strip(),
                    clave,
                    grupo,
                    mando["departamento_id"],
                    vacaciones,
                    horas_contrato,
                ),
            )
            creado = cur.fetchone()
            cur.execute(
                """
                INSERT INTO horario_version (usuario_id, desde)
                VALUES (%s, %s)
                """,
                (creado["id"], desde),
            )
            for dia, inicio, fin in filas:
                cur.execute(
                    """
                    INSERT INTO horario_dia (
                        usuario_id, desde, dia_semana, horario_inicio, horario_fin
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (creado["id"], desde, dia, inicio, fin),
                )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        nombre=creado["nombre"],
        login=creado["login"],
        rol=creado["rol"],
        grupo=creado["grupo"],
        vacaciones=float(creado["vacaciones"]),
        horas_contrato=float(creado["horas_contrato"]),
    ), 201


@bp.put("/trabajadores/<login_nombre>/baja")
@jwt_required()
def dar_de_baja(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    desde, error = _desde(cuerpo.get("desde"))
    if error:
        return error

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
                """
                SELECT id
                FROM usuario
                WHERE login = %s
                  AND rol = 'trabajador'
                  AND departamento_id = %s
                """,
                (login_nombre, mando["departamento_id"]),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                "UPDATE usuario SET activo = false WHERE id = %s",
                (trabajador["id"],),
            )
            cur.execute(
                """
                DELETE FROM horario_dia
                WHERE usuario_id = %s AND desde = %s
                """,
                (trabajador["id"], desde),
            )
            cur.execute(
                """
                INSERT INTO horario_version (usuario_id, desde)
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, desde) DO NOTHING
                """,
                (trabajador["id"], desde),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(login=login_nombre, activo=False, desde=desde.isoformat())


@bp.put("/trabajadores/<login_nombre>/horario")
@jwt_required()
def cambiar_horario(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    filas, error = _horario_dias(cuerpo.get("horario_dias"))
    if error:
        return error
    desde, error = _desde_futuro(cuerpo.get("desde"))
    if error:
        return error

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
                """
                SELECT id
                FROM usuario
                WHERE login = %s
                  AND rol = 'trabajador'
                  AND departamento_id = %s
                """,
                (login_nombre, mando["departamento_id"]),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                """
                DELETE FROM horario_dia
                WHERE usuario_id = %s AND desde = %s
                """,
                (trabajador["id"], desde),
            )
            cur.execute(
                """
                INSERT INTO horario_version (usuario_id, desde)
                VALUES (%s, %s)
                ON CONFLICT (usuario_id, desde) DO NOTHING
                """,
                (trabajador["id"], desde),
            )
            for dia, inicio, fin in filas:
                cur.execute(
                    """
                    INSERT INTO horario_dia (
                        usuario_id, desde, dia_semana, horario_inicio, horario_fin
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (trabajador["id"], desde, dia, inicio, fin),
                )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        login=login_nombre,
        desde=desde.isoformat(),
        horario=[
            {
                "dia_semana": dia,
                "inicio": hora_texto(inicio),
                "fin": hora_texto(fin),
            }
            for dia, inicio, fin in filas
        ],
    )


def _desde(valor):
    if valor is None or valor == "":
        return date.today(), None
    if not isinstance(valor, str):
        return None, (jsonify(error="desde no es una fecha válida"), 400)
    try:
        return datetime.strptime(valor.strip(), "%Y-%m-%d").date(), None
    except ValueError:
        return None, (jsonify(error="desde no es una fecha válida"), 400)


def _desde_futuro(valor):
    if valor is None or valor == "":
        return None, (jsonify(error="Faltan datos"), 400)
    desde, error = _desde(valor)
    if error:
        return None, error
    if desde < date.today():
        return None, (jsonify(error="desde no puede ser anterior a hoy"), 400)
    return desde, None


def _horario_dias(valor):
    if not isinstance(valor, list):
        return None, (jsonify(error="Faltan datos"), 400)
    vistos = set()
    filas = []
    for item in valor:
        if not isinstance(item, dict):
            return None, (jsonify(error="Faltan datos"), 400)
        dia = item.get("dia_semana")
        if isinstance(dia, bool) or not isinstance(dia, int) or not 0 <= dia <= 6:
            return None, (jsonify(error="Faltan datos"), 400)
        if dia in vistos:
            return None, (jsonify(error="Faltan datos"), 400)
        vistos.add(dia)
        inicio = parse_hora(item.get("hora_inicio"))
        fin = parse_hora(item.get("hora_fin"))
        if inicio == "mal" or fin == "mal":
            return None, (jsonify(error="La hora no es válida"), 400)
        if inicio is None or fin is None:
            return None, (jsonify(error="Faltan datos"), 400)
        filas.append((dia, inicio, fin))
    if not filas:
        return None, (jsonify(error="Faltan datos"), 400)
    return filas, None


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
