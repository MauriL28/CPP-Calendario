from uuid import UUID

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from errores import error_bd
from mandos import departamento_permitido, departamentos_del_mando, tiene_mando_activo
from horas import hora_texto
import validaciones
from rutas.trabajadores import guardar_horario
from usuarios_edicion import campos_desconocidos, editar_campos
from validaciones import error_unico, sap_ocupado

bp = Blueprint("usuarios", __name__)


def _decimal(valor):
    if valor is None:
        return None
    return float(valor)


def listar_del_departamento(cur, filtro, params, solo_mandos_activos=False):
    activos = "AND u.activo" if solo_mandos_activos else ""
    cur.execute(
        f"""
        SELECT g.codigo AS delegacion, d.codigo AS departamento,
               u.nombre, u.login, u.numero_sap, u.activo,
               (u.departamento_id = d.id) AS propio
        FROM usuario u
        JOIN departamento d
          ON d.id = u.departamento_id
          OR EXISTS (
            SELECT 1
            FROM mando_departamento md
            WHERE md.usuario_id = u.id
              AND md.departamento_id = d.id
          )
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE u.rol = 'mando'
          AND g.codigo = ANY(%s)
          {activos}
          {filtro}
        ORDER BY u.nombre
        """,
        params,
    )
    mandos = cur.fetchall()
    cur.execute(
        f"""
        SELECT g.codigo AS delegacion, d.codigo AS departamento,
               u.nombre, u.login, u.grupo, u.horas_contrato, u.horas_convenio,
               u.pausa_minutos, u.vacaciones, u.numero_sap,
               u.seccion_id
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE u.rol = 'trabajador'
          AND u.activo
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
    cur.execute(
        f"""
        SELECT u.login, hd.dia_semana, hd.horario_inicio, hd.horario_fin
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        JOIN delegacion g ON g.id = d.delegacion_id
        JOIN LATERAL (
            SELECT v.desde
            FROM horario_version v
            WHERE v.usuario_id = u.id
              AND v.desde <= CURRENT_DATE
            ORDER BY v.desde DESC
            LIMIT 1
        ) vig ON true
        JOIN horario_dia hd
          ON hd.usuario_id = u.id AND hd.desde = vig.desde
        WHERE u.rol = 'trabajador'
          AND g.codigo = ANY(%s)
          {filtro}
        ORDER BY u.login, hd.dia_semana
        """,
        params,
    )
    horarios = cur.fetchall()
    return mandos, trabajadores, turnos, horarios


def adjuntar_personas(departamentos, por_codigo, mandos, trabajadores, turnos, horarios):
    for mando in mandos:
        item = por_codigo.get((mando["delegacion"], mando["departamento"]))
        if item is not None:
            item["mandos"].append(
                {
                    "nombre": mando["nombre"],
                    "login": mando["login"],
                    "numero_sap": mando["numero_sap"],
                    "activo": bool(mando["activo"]),
                    "propio": bool(mando["propio"]),
                }
            )
    por_login = {}
    for trabajador in trabajadores:
        item = por_codigo.get((trabajador["delegacion"], trabajador["departamento"]))
        if item is None:
            continue
        persona = {
            "nombre": trabajador["nombre"],
            "login": trabajador["login"],
            "grupo": trabajador["grupo"],
            "horario": [],
            "horas_contrato": _decimal(trabajador["horas_contrato"]),
            "horas_convenio": _decimal(trabajador["horas_convenio"]),
            "pausa_minutos": int(trabajador.get("pausa_minutos") or 0),
            "vacaciones": _decimal(trabajador["vacaciones"]),
            "numero_sap": trabajador["numero_sap"],
            "seccion_id": str(trabajador["seccion_id"]) if trabajador["seccion_id"] else None,
            "turnos": [],
        }
        por_login[trabajador["login"]] = persona
        item["trabajadores"].append(persona)
    for fila in horarios:
        persona = por_login.get(fila["login"])
        if persona is None:
            continue
        persona["horario"].append(
            {
                "dia_semana": fila["dia_semana"],
                "inicio": hora_texto(fila["horario_inicio"]),
                "fin": hora_texto(fila["horario_fin"]),
            }
        )
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
    numero_sap, error = validaciones.numero_sap(cuerpo.get("numero_sap"))
    if error:
        return error

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
            if tiene_mando_activo(cur, depto["id"]):
                return jsonify(
                    error="Este departamento ya tiene un mando en esta delegación"
                ), 409
            cur.execute(
                "SELECT 1 FROM usuario WHERE login = %s",
                (login_nombre.strip(),),
            )
            if cur.fetchone() is not None:
                return jsonify(error="El login ya existe"), 409
            if sap_ocupado(cur, numero_sap):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                """
                INSERT INTO usuario (nombre, login, clave, rol, departamento_id, numero_sap)
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'mando', %s, %s)
                RETURNING nombre, login, rol, numero_sap
                """,
                (nombre.strip(), login_nombre.strip(), clave, depto["id"], numero_sap),
            )
            creado = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        nombre=creado["nombre"],
        login=creado["login"],
        rol=creado["rol"],
        delegacion=delegacion.strip(),
        departamento=departamento.strip(),
        numero_sap=creado["numero_sap"],
    ), 201


@bp.put("/usuarios/<login_nombre>/numero-sap")
@jwt_required()
def cambiar_numero_sap_mando(login_nombre):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    numero_sap, error = validaciones.numero_sap(cuerpo.get("numero_sap"))
    if error:
        return error

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, departamento_id
                FROM usuario
                WHERE login = %s AND rol = 'mando'
                """,
                (login_nombre,),
            )
            mando = cur.fetchone()
            if mando is None or not departamento_permitido(
                cur, mando["id"], mando["departamento_id"]
            ):
                return jsonify(error="No autorizado"), 404
            if sap_ocupado(cur, numero_sap, mando["id"]):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                "UPDATE usuario SET numero_sap = %s WHERE id = %s",
                (numero_sap, mando["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, numero_sap=numero_sap)


@bp.put("/usuarios/<login_nombre>")
@jwt_required()
def editar_usuario(login_nombre):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    if not isinstance(cuerpo, dict):
        return jsonify(error="Faltan datos"), 400
    if campos_desconocidos(cuerpo):
        return jsonify(error="Campo no permitido"), 400

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, rol, departamento_id
                FROM usuario
                WHERE login = %s AND rol IN ('mando', 'trabajador')
                """,
                (login_nombre,),
            )
            persona = cur.fetchone()
            if persona is None:
                return jsonify(error="No se ha encontrado el usuario"), 404
            cambios, error = editar_campos(cur, persona, cuerpo)
            if error:
                return error
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, rol=persona["rol"], **cambios), 200


def _mando(cur, login_nombre):
    cur.execute(
        """
        SELECT id, departamento_id, activo
        FROM usuario
        WHERE login = %s AND rol = 'mando'
        """,
        (login_nombre,),
    )
    return cur.fetchone()


def _departamento(cur, delegacion, codigo):
    cur.execute(
        """
        SELECT d.id
        FROM departamento d
        JOIN delegacion g ON g.id = d.delegacion_id
        WHERE g.codigo = %s AND d.codigo = %s
        """,
        (delegacion, codigo),
    )
    return cur.fetchone()


@bp.put("/usuarios/<login_nombre>/horario")
@jwt_required()
def cambiar_horario_mando(login_nombre):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    _datos, error = guardar_horario(None, None, cuerpo)
    if error:
        return error

    try:
        with cursor() as cur:
            mando = _mando(cur, login_nombre)
            if mando is None:
                return jsonify(error="No se ha encontrado el mando"), 404
            datos, error = guardar_horario(cur, mando["id"], cuerpo)
            if error:
                return error
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, **datos)


@bp.put("/usuarios/<login_nombre>/activo")
@jwt_required()
def cambiar_activo_mando(login_nombre):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    activo = cuerpo.get("activo")
    if not isinstance(activo, bool):
        return jsonify(error="Faltan datos"), 400

    try:
        with cursor() as cur:
            mando = _mando(cur, login_nombre)
            if mando is None:
                return jsonify(error="No se ha encontrado el mando"), 404
            if activo:
                for departamento_id in departamentos_del_mando(cur, mando["id"]):
                    if tiene_mando_activo(cur, departamento_id, excluir_login=login_nombre):
                        return jsonify(
                            error="Este departamento ya tiene un mando en esta delegación"
                        ), 409
            cur.execute(
                "UPDATE usuario SET activo = %s WHERE id = %s",
                (activo, mando["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, activo=activo)


@bp.post("/usuarios/<login_nombre>/departamentos")
@jwt_required()
def asignar_departamento(login_nombre):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    delegacion = cuerpo.get("delegacion")
    departamento = cuerpo.get("departamento")
    if not all(isinstance(valor, str) and valor.strip() for valor in (delegacion, departamento)):
        return jsonify(error="Faltan datos"), 400

    try:
        with cursor() as cur:
            mando = _mando(cur, login_nombre)
            if mando is None:
                return jsonify(error="No se ha encontrado el mando"), 404
            if not mando["activo"]:
                return jsonify(error="El mando no está activo"), 409
            depto = _departamento(cur, delegacion.strip(), departamento.strip())
            if depto is None:
                return jsonify(
                    error=f"No hay departamento {departamento.strip()} en la delegación {delegacion.strip()}"
                ), 404
            if depto["id"] in departamentos_del_mando(cur, mando["id"]):
                return jsonify(
                    login=login_nombre,
                    delegacion=delegacion.strip(),
                    departamento=departamento.strip(),
                ), 200
            if tiene_mando_activo(cur, depto["id"]):
                return jsonify(
                    error="Este departamento ya tiene un mando en esta delegación"
                ), 409
            cur.execute(
                """
                INSERT INTO mando_departamento (usuario_id, departamento_id)
                VALUES (%s, %s)
                """,
                (mando["id"], depto["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        login=login_nombre,
        delegacion=delegacion.strip(),
        departamento=departamento.strip(),
    ), 201


@bp.delete("/usuarios/<login_nombre>/departamentos/<departamento_id>")
@jwt_required()
def quitar_departamento(login_nombre, departamento_id):
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    try:
        buscado = UUID(departamento_id)
    except ValueError:
        return jsonify(error="No hay esa asignación"), 404

    try:
        with cursor() as cur:
            mando = _mando(cur, login_nombre)
            if mando is None:
                return jsonify(error="No se ha encontrado el mando"), 404
            if mando["departamento_id"] is not None and str(mando["departamento_id"]) == str(buscado):
                return jsonify(error="No se quita el departamento propio"), 400
            cur.execute(
                """
                DELETE FROM mando_departamento
                WHERE usuario_id = %s AND departamento_id = %s
                RETURNING departamento_id
                """,
                (mando["id"], buscado),
            )
            if cur.fetchone() is None:
                return jsonify(error="No hay esa asignación"), 404
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, departamento_id=str(buscado))
