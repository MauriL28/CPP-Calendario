from datetime import date, datetime, timedelta

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from horas import hora_texto, parse_hora
from rutas.turnos import _agrupar_versiones, _franja, _texto_celda, resolver_turno

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
    numero_sap, error = _numero_sap(cuerpo.get("numero_sap"))
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
            if _sap_ocupado(cur, numero_sap):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                """
                INSERT INTO usuario (
                    nombre, login, clave, rol, grupo, departamento_id,
                    vacaciones, horas_contrato, numero_sap
                )
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'trabajador', %s, %s, %s, %s, %s)
                RETURNING id, nombre, login, rol, grupo, vacaciones, horas_contrato, numero_sap
                """,
                (
                    nombre.strip(),
                    login_nombre.strip(),
                    clave,
                    grupo,
                    mando["departamento_id"],
                    vacaciones,
                    horas_contrato,
                    numero_sap,
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
    except psycopg.errors.UniqueViolation as exc:
        return _error_unico(exc)
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        nombre=creado["nombre"],
        login=creado["login"],
        rol=creado["rol"],
        grupo=creado["grupo"],
        vacaciones=float(creado["vacaciones"]),
        horas_contrato=float(creado["horas_contrato"]),
        numero_sap=creado["numero_sap"],
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


@bp.put("/trabajadores/<login_nombre>/numero-sap")
@jwt_required()
def cambiar_numero_sap(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    numero_sap, error = _numero_sap(cuerpo.get("numero_sap"))
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
            if _sap_ocupado(cur, numero_sap, trabajador["id"]):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                "UPDATE usuario SET numero_sap = %s WHERE id = %s",
                (numero_sap, trabajador["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return _error_unico(exc)
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(login=login_nombre, numero_sap=numero_sap)


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


def _numero_sap(valor):
    if valor is None or valor == "":
        return None, None
    if not isinstance(valor, str):
        return None, (jsonify(error="Faltan datos"), 400)
    texto = valor.strip()
    if not texto:
        return None, None
    if len(texto) > 40:
        return None, (jsonify(error="El número de personal es demasiado largo"), 400)
    return texto, None


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


@bp.get("/trabajadores/<login_nombre>/ficha")
@jwt_required()
def ficha(login_nombre):
    rol = get_jwt().get("rol")
    if rol not in ("mando", "trabajador"):
        return jsonify(error="No autorizado"), 403
    anio, error = _anio(request.args.get("anio"))
    if error:
        return error
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    try:
        with cursor() as cur:
            mando = None
            if rol == "mando":
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
                SELECT u.id, u.nombre, u.grupo, u.departamento_id,
                       d.nombre AS departamento
                FROM usuario u
                JOIN departamento d ON d.id = u.departamento_id
                WHERE u.login = %s AND u.rol = 'trabajador'
                """,
                (login_nombre,),
            )
            trabajador = cur.fetchone()
            if rol == "trabajador":
                if trabajador is None or str(trabajador["id"]) != get_jwt_identity():
                    return jsonify(error="No autorizado"), 403
            elif trabajador is None or trabajador["departamento_id"] != mando["departamento_id"]:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                """
                SELECT fecha, ausencia::text AS ausencia, hora_inicio, hora_fin,
                       horas_planificadas, horas_nocturnas
                FROM turno
                WHERE usuario_id = %s AND fecha >= %s AND fecha <= %s
                """,
                (trabajador["id"], inicio, fin),
            )
            turnos = {fila["fecha"]: fila for fila in cur.fetchall()}
            cur.execute(
                """
                SELECT v.usuario_id, v.desde, d.dia_semana, d.horario_inicio, d.horario_fin
                FROM horario_version v
                LEFT JOIN horario_dia d
                  ON d.usuario_id = v.usuario_id AND d.desde = v.desde
                WHERE v.usuario_id = %s AND v.desde <= %s
                """,
                (trabajador["id"], fin),
            )
            versiones = _agrupar_versiones(cur.fetchall()).get(trabajador["id"], [])
            noche_inicio, noche_fin = _franja(cur)
            cur.execute(
                "SELECT fecha FROM festivo WHERE fecha >= %s AND fecha <= %s",
                (inicio, fin),
            )
            festivos = {fila["fecha"] for fila in cur.fetchall()}
            cur.execute(
                """
                SELECT fecha, horas, motivo
                FROM ajuste
                WHERE usuario_afectado_id = %s AND fecha >= %s AND fecha <= %s
                ORDER BY fecha, id
                """,
                (trabajador["id"], inicio, fin),
            )
            ajustes = [
                {
                    "fecha": fila["fecha"].isoformat(),
                    "horas": float(fila["horas"]),
                    "motivo": fila["motivo"],
                }
                for fila in cur.fetchall()
            ]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    horas_mes = [0.0] * 12
    ausencias = {"V": 0, "B": 0, "P": 0, "F": 0}
    festivos_trabajados = 0
    sabados_trabajados = 0
    dias = []
    dia = inicio
    while dia <= fin:
        turno, _origen = resolver_turno(
            dia, turnos.get(dia), versiones, noche_inicio, noche_fin
        )
        dias.append(
            {
                "fecha": dia.isoformat(),
                "semana": dia.isocalendar().week,
                "texto": _texto_celda(turno),
            }
        )
        if turno is not None and turno["ausencia"]:
            if turno["ausencia"] in ausencias:
                ausencias[turno["ausencia"]] += 1
        elif turno is not None:
            horas_mes[dia.month - 1] += float(turno["horas_planificadas"])
            if dia in festivos:
                festivos_trabajados += 1
            if dia.weekday() == 5:
                sabados_trabajados += 1
        dia += timedelta(days=1)

    return jsonify(
        nombre=trabajador["nombre"],
        departamento=trabajador["departamento"],
        grupo=trabajador["grupo"],
        horas_por_mes=[round(valor, 2) for valor in horas_mes],
        ausencias=ausencias,
        festivos_trabajados=festivos_trabajados,
        sabados_trabajados=sabados_trabajados,
        ajustes=ajustes,
        dias=dias,
    )


def _anio(texto):
    if texto is None or str(texto).strip() == "":
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        anio = int(str(texto))
    except (TypeError, ValueError):
        return None, (jsonify(error="anio no es válido"), 400)
    if anio < 1 or anio > 9999:
        return None, (jsonify(error="anio no es válido"), 400)
    return anio, None


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
