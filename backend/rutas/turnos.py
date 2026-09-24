from datetime import datetime, timedelta

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from horas import hora_texto, horas_de_turno, parse_hora

bp = Blueprint("turnos", __name__)

AUSENCIAS = {"L", "D", "V", "B", "F", "P"}


def _lunes(texto, admite_tipo):
    try:
        desde = datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError) if admite_tipo else ValueError:
        return None, (jsonify(error="desde no es una fecha válida"), 400)
    if desde.weekday() != 0:
        return None, (jsonify(error="desde tiene que ser lunes"), 400)
    return desde, None


def _turno(fila):
    return {
        "ausencia": fila["ausencia"],
        "hora_inicio": hora_texto(fila["hora_inicio"]),
        "hora_fin": hora_texto(fila["hora_fin"]),
        "horas_planificadas": float(fila["horas_planificadas"]),
        "horas_nocturnas": float(fila["horas_nocturnas"]),
    }


def _semana(desde):
    return [desde + timedelta(days=i) for i in range(7)]


@bp.get("/turnos")
@jwt_required()
def listar_turnos():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    desde, error = _lunes(request.args.get("desde", ""), False)
    if error:
        return error
    dias = _semana(desde)

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
                SELECT nombre, login, grupo
                FROM usuario
                WHERE rol = 'trabajador' AND departamento_id = %s
                ORDER BY nombre
                """,
                (mando["departamento_id"],),
            )
            trabajadores = cur.fetchall()
            cur.execute(
                """
                SELECT u.login, t.fecha, t.ausencia::text AS ausencia,
                       t.hora_inicio, t.hora_fin,
                       t.horas_planificadas, t.horas_nocturnas
                FROM turno t
                JOIN usuario u ON u.id = t.usuario_id
                WHERE u.rol = 'trabajador'
                  AND u.departamento_id = %s
                  AND t.fecha >= %s
                  AND t.fecha <= %s
                """,
                (mando["departamento_id"], dias[0], dias[6]),
            )
            filas = cur.fetchall()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    por_login_fecha = {}
    for fila in filas:
        por_login_fecha[(fila["login"], fila["fecha"])] = _turno(fila)
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=[
            {
                "nombre": trabajador["nombre"],
                "login": trabajador["login"],
                "grupo": trabajador["grupo"],
                "dias": [
                    {
                        "fecha": dia.isoformat(),
                        "turno": por_login_fecha.get((trabajador["login"], dia)),
                    }
                    for dia in dias
                ],
            }
            for trabajador in trabajadores
        ],
    )


@bp.get("/turnos/mios")
@jwt_required()
def listar_turnos_mios():
    if get_jwt().get("rol") != "trabajador":
        return jsonify(error="No autorizado"), 403
    desde, error = _lunes(request.args.get("desde", ""), False)
    if error:
        return error
    dias = _semana(desde)

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT nombre, login, grupo
                FROM usuario
                WHERE id = %s AND rol = 'trabajador'
                """,
                (get_jwt_identity(),),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="No autorizado"), 403
            cur.execute(
                """
                SELECT t.fecha, t.ausencia::text AS ausencia,
                       t.hora_inicio, t.hora_fin,
                       t.horas_planificadas, t.horas_nocturnas
                FROM turno t
                JOIN usuario u ON u.id = t.usuario_id
                WHERE u.id = %s
                  AND t.fecha >= %s
                  AND t.fecha <= %s
                """,
                (get_jwt_identity(), dias[0], dias[6]),
            )
            filas = cur.fetchall()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    por_fecha = {fila["fecha"]: _turno(fila) for fila in filas}
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=[
            {
                "nombre": trabajador["nombre"],
                "login": trabajador["login"],
                "grupo": trabajador["grupo"],
                "dias": [
                    {"fecha": dia.isoformat(), "turno": por_fecha.get(dia)}
                    for dia in dias
                ],
            }
        ],
    )


@bp.post("/turnos/copiar-semana")
@jwt_required()
def copiar_semana():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    desde, error = _lunes(cuerpo.get("desde", ""), True)
    if error:
        return error
    anterior = desde - timedelta(days=7)
    hasta = desde + timedelta(days=6)

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
                DELETE FROM turno t
                USING usuario u
                WHERE t.usuario_id = u.id
                  AND u.rol = 'trabajador'
                  AND u.departamento_id = %s
                  AND t.fecha >= %s
                  AND t.fecha <= %s
                  AND NOT EXISTS (
                      SELECT 1
                      FROM turno previo
                      WHERE previo.usuario_id = t.usuario_id
                        AND previo.fecha = t.fecha - 7
                  )
                """,
                (mando["departamento_id"], desde, hasta),
            )
            cur.execute(
                """
                INSERT INTO turno (
                    usuario_id, fecha, ausencia, hora_inicio, hora_fin,
                    horas_planificadas, horas_nocturnas
                )
                SELECT t.usuario_id, t.fecha + 7, t.ausencia, t.hora_inicio, t.hora_fin,
                       t.horas_planificadas, t.horas_nocturnas
                FROM turno t
                JOIN usuario u ON u.id = t.usuario_id
                WHERE u.rol = 'trabajador'
                  AND u.departamento_id = %s
                  AND t.fecha >= %s
                  AND t.fecha < %s
                ON CONFLICT (usuario_id, fecha) DO UPDATE SET
                    ausencia = EXCLUDED.ausencia,
                    hora_inicio = EXCLUDED.hora_inicio,
                    hora_fin = EXCLUDED.hora_fin,
                    horas_planificadas = EXCLUDED.horas_planificadas,
                    horas_nocturnas = EXCLUDED.horas_nocturnas
                """,
                (mando["departamento_id"], anterior, desde),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(desde=desde.isoformat())


@bp.put("/turnos")
@jwt_required()
def guardar_turno():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("login")
    fecha_texto = cuerpo.get("fecha")
    ausencia = cuerpo.get("ausencia")
    if ausencia == "":
        ausencia = None
    hora_inicio = parse_hora(cuerpo.get("hora_inicio"))
    hora_fin = parse_hora(cuerpo.get("hora_fin"))
    if hora_inicio == "mal" or hora_fin == "mal":
        return jsonify(error="La hora no es válida"), 400
    if not isinstance(login_nombre, str) or not login_nombre.strip():
        return jsonify(error="Faltan datos"), 400
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify(error="La fecha no es válida"), 400

    hay_horario = hora_inicio is not None or hora_fin is not None
    hay_ausencia = ausencia is not None
    if hay_horario and hay_ausencia:
        return jsonify(error="Indica horario o ausencia, no las dos"), 400
    if hay_ausencia:
        if ausencia not in AUSENCIAS:
            return jsonify(error="La ausencia no es válida"), 400
        if hora_inicio is not None or hora_fin is not None:
            return jsonify(error="Indica horario o ausencia, no las dos"), 400
    elif hora_inicio is None or hora_fin is None:
        return jsonify(error="Indica un horario o una ausencia"), 400

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
                (login_nombre.strip(), mando["departamento_id"]),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            if hay_ausencia:
                planificadas, nocturnas = 0, 0
                hora_inicio = None
                hora_fin = None
            else:
                cur.execute("SELECT noche_inicio, noche_fin FROM empresa WHERE id = 1")
                franja = cur.fetchone()
                if franja is None:
                    noche_inicio = datetime.strptime("22:00", "%H:%M").time()
                    noche_fin = datetime.strptime("06:00", "%H:%M").time()
                else:
                    noche_inicio = franja["noche_inicio"]
                    noche_fin = franja["noche_fin"]
                planificadas, nocturnas = horas_de_turno(
                    hora_inicio, hora_fin, noche_inicio, noche_fin
                )
            cur.execute(
                """
                INSERT INTO turno (
                    usuario_id, fecha, ausencia, hora_inicio, hora_fin,
                    horas_planificadas, horas_nocturnas
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (usuario_id, fecha) DO UPDATE SET
                    ausencia = EXCLUDED.ausencia,
                    hora_inicio = EXCLUDED.hora_inicio,
                    hora_fin = EXCLUDED.hora_fin,
                    horas_planificadas = EXCLUDED.horas_planificadas,
                    horas_nocturnas = EXCLUDED.horas_nocturnas
                RETURNING fecha, ausencia::text AS ausencia, hora_inicio, hora_fin,
                          horas_planificadas, horas_nocturnas
                """,
                (
                    trabajador["id"],
                    fecha,
                    ausencia,
                    hora_inicio,
                    hora_fin,
                    planificadas,
                    nocturnas,
                ),
            )
            guardado = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        login=login_nombre.strip(),
        fecha=guardado["fecha"].isoformat(),
        ausencia=guardado["ausencia"],
        hora_inicio=hora_texto(guardado["hora_inicio"]),
        hora_fin=hora_texto(guardado["hora_fin"]),
        horas_planificadas=float(guardado["horas_planificadas"]),
        horas_nocturnas=float(guardado["horas_nocturnas"]),
    )
