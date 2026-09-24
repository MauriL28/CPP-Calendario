import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from horas import hora_texto

bp = Blueprint("usuarios", __name__)


def listar_del_departamento(cur, filtro, params):
    cur.execute(
        f"""
        SELECT g.codigo AS delegacion, d.codigo AS departamento,
               u.nombre, u.login
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE u.rol = 'mando'
          AND g.codigo = ANY(%s)
          {filtro}
        ORDER BY u.nombre
        """,
        params,
    )
    mandos = cur.fetchall()
    cur.execute(
        f"""
        SELECT g.codigo AS delegacion, d.codigo AS departamento,
               u.nombre, u.login, u.grupo
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE u.rol = 'trabajador'
          AND g.codigo = ANY(%s)
          {filtro}
        ORDER BY u.nombre
        """,
        params,
    )
    trabajadores = cur.fetchall()
    cur.execute(
        f"""
        SELECT u.login, t.fecha, t.ausencia::text AS ausencia,
               t.hora_inicio, t.hora_fin,
               t.horas_planificadas, t.horas_nocturnas
        FROM turno t
        JOIN usuario u ON u.id = t.usuario_id
        JOIN departamento d ON d.id = u.departamento_id
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE u.rol = 'trabajador'
          AND g.codigo = ANY(%s)
          {filtro}
        ORDER BY t.fecha
        """,
        params,
    )
    turnos = cur.fetchall()
    return mandos, trabajadores, turnos


def adjuntar_personas(departamentos, por_codigo, mandos, trabajadores, turnos):
    for mando in mandos:
        item = por_codigo.get((mando["delegacion"], mando["departamento"]))
        if item is not None:
            item["mandos"].append({"nombre": mando["nombre"], "login": mando["login"]})
    por_login = {}
    for trabajador in trabajadores:
        item = por_codigo.get((trabajador["delegacion"], trabajador["departamento"]))
        if item is None:
            continue
        persona = {
            "nombre": trabajador["nombre"],
            "login": trabajador["login"],
            "grupo": trabajador["grupo"],
            "turnos": [],
        }
        por_login[trabajador["login"]] = persona
        item["trabajadores"].append(persona)
    for turno in turnos:
        persona = por_login.get(turno["login"])
        if persona is None:
            continue
        persona["turnos"].append(
            {
                "fecha": turno["fecha"].isoformat(),
                "ausencia": turno["ausencia"],
                "hora_inicio": hora_texto(turno["hora_inicio"]),
                "hora_fin": hora_texto(turno["hora_fin"]),
                "horas_planificadas": float(turno["horas_planificadas"]),
                "horas_nocturnas": float(turno["horas_nocturnas"]),
            }
        )
    return departamentos


@bp.post("/usuarios")
@jwt_required()
def crear_usuario():
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    nombre = cuerpo.get("nombre")
    login_nombre = cuerpo.get("login")
    clave = cuerpo.get("clave")
    delegacion = cuerpo.get("delegacion")
    departamento = cuerpo.get("departamento")
    campos = (nombre, login_nombre, clave, delegacion, departamento)
    if not all(isinstance(valor, str) and valor.strip() for valor in campos):
        return jsonify(error="Faltan datos"), 400

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT d.id
                FROM departamento d
                JOIN delegacion g ON g.id = d.delegacion_id
                WHERE g.codigo = %s AND d.codigo = %s
                """,
                (delegacion.strip(), departamento.strip()),
            )
            depto = cur.fetchone()
            if depto is None:
                return jsonify(
                    error=f"No hay departamento {departamento.strip()} en la delegación {delegacion.strip()}"
                ), 404
            cur.execute(
                "SELECT 1 FROM usuario WHERE login = %s",
                (login_nombre.strip(),),
            )
            if cur.fetchone() is not None:
                return jsonify(error="El login ya existe"), 409
            cur.execute(
                """
                INSERT INTO usuario (nombre, login, clave, rol, departamento_id)
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'mando', %s)
                RETURNING nombre, login, rol
                """,
                (nombre.strip(), login_nombre.strip(), clave, depto["id"]),
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
        delegacion=delegacion.strip(),
        departamento=departamento.strip(),
    ), 201
