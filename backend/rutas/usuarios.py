import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from horas import hora_texto

bp = Blueprint("usuarios", __name__)


def _decimal(valor):
    if valor is None:
        return None
    return float(valor)


def listar_del_departamento(cur, filtro, params):
    cur.execute(
        f"""
        SELECT g.codigo AS delegacion, d.codigo AS departamento,
               u.nombre, u.login, u.numero_sap
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
               u.nombre, u.login, u.grupo, u.horas_contrato, u.vacaciones, u.numero_sap
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
            "vacaciones": _decimal(trabajador["vacaciones"]),
            "numero_sap": trabajador["numero_sap"],
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
    numero_sap, error = _numero_sap(cuerpo.get("numero_sap"))
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
            cur.execute(
                "SELECT 1 FROM usuario WHERE login = %s",
                (login_nombre.strip(),),
            )
            if cur.fetchone() is not None:
                return jsonify(error="El login ya existe"), 409
            if _sap_ocupado(cur, numero_sap):
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
        return _error_unico(exc)
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

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
    numero_sap, error = _numero_sap(cuerpo.get("numero_sap"))
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
            if mando is None or mando["departamento_id"] is None:
                return jsonify(error="No autorizado"), 404
            if _sap_ocupado(cur, numero_sap, mando["id"]):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                "UPDATE usuario SET numero_sap = %s WHERE id = %s",
                (numero_sap, mando["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return _error_unico(exc)
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(login=login_nombre, numero_sap=numero_sap)


def _numero_sap(valor):
    if valor is None or valor == "":
        return None, None
    if not isinstance(valor, str):
        return None, (jsonify(error="Faltan datos"), 400)
    if len(valor.strip()) > 40:
        return None, (jsonify(error="El número de personal es demasiado largo"), 400)
    texto = valor.strip()
    return (texto or None), None


def _sap_ocupado(cur, numero, excepto_id=None):
    if numero is None:
        return False
    cur.execute(
        """
        SELECT 1
        FROM usuario
        WHERE numero_sap = %s
          AND id IS DISTINCT FROM %s
        """,
        (numero, excepto_id),
    )
    return cur.fetchone() is not None


def _error_unico(exc):
    if getattr(exc.diag, "constraint_name", None) == "usuario_numero_sap":
        return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
    return jsonify(error=str(exc)), 503
