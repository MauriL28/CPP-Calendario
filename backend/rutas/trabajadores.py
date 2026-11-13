from datetime import date, datetime, timedelta
from uuid import UUID

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from errores import error_bd
from mandos import departamento_lectura, departamento_permitido, departamentos_del_mando
from horas import convenio_anual, hora_texto, horas_computables, parse_hora
from exportar_turnos import _texto_celda
from turnos_base import _agrupar_versiones, _franja, _habituales, resolver_turno
from vacaciones import dias_v_usados
import validaciones
from usuarios_edicion import campos_desconocidos, editar_campos
from validaciones import (
    comprobar_seccion,
    error_unico,
    coste_hora,
    grupo_valido,
    leer_seccion_id,
    numero,
    sap_ocupado,
)

bp = Blueprint("trabajadores", __name__)


@bp.post("/trabajadores")
@jwt_required()
def crear_trabajador():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    nombre = cuerpo.get("nombre")
    login_nombre = cuerpo.get("login")
    clave = cuerpo.get("clave")
    grupo = cuerpo.get("grupo")
    vacaciones = numero(cuerpo.get("vacaciones"))
    horas_contrato = numero(cuerpo.get("horas_contrato"))
    if not all(isinstance(valor, str) and valor.strip() for valor in (nombre, login_nombre, clave)):
        return jsonify(error="Faltan datos"), 400
    error = grupo_valido(grupo)
    if error:
        return error
    if vacaciones is None or horas_contrato is None or vacaciones == "mal" or horas_contrato == "mal":
        return jsonify(error="Faltan datos"), 400
    horario_pedido = cuerpo.get("horario_dias")
    sin_horario = horario_pedido is None or horario_pedido == []
    filas = []
    desde = None
    if not sin_horario:
        filas, error = _horario_dias(horario_pedido)
        if error:
            return error
        desde, error = _desde(cuerpo.get("desde"))
        if error:
            return error
    if "pausa_minutos" in cuerpo and cuerpo.get("pausa_minutos") not in (None, ""):
        pausa = validaciones.pausa_minutos(cuerpo.get("pausa_minutos"))
        if pausa is None:
            return jsonify(error="La pausa tiene que ser 0, 30 o 60"), 400
    else:
        pausa = 0
    numero_sap, error = validaciones.numero_sap(cuerpo.get("numero_sap"))
    if error:
        return error
    seccion_id, error = leer_seccion_id(cuerpo, opcional=True)
    if error:
        return error
    if "coste" in cuerpo:
        coste = coste_hora(cuerpo.get("coste"))
        if coste == "mal":
            return jsonify(
                error="El coste tiene que ser un número mayor o igual que cero, con hasta 4 decimales"
            ), 400
    else:
        coste = None
    if grupo != "ETT":
        coste = None

    try:
        with cursor() as cur:
            departamento_id, error = _departamento_alta(cur, cuerpo.get("departamento_id"))
            if error:
                return error
            cur.execute(
                """
                SELECT usa_horario_habitual
                FROM departamento
                WHERE id = %s
                """,
                (departamento_id,),
            )
            departamento = cur.fetchone()
            if sin_horario and (departamento is None or departamento["usa_horario_habitual"]):
                return jsonify(error="Faltan datos"), 400
            error = comprobar_seccion(cur, departamento_id, seccion_id)
            if error:
                return error
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
                INSERT INTO usuario (
                    nombre, login, clave, rol, grupo, departamento_id,
                    vacaciones, horas_contrato, numero_sap, seccion_id, pausa_minutos,
                    tarifas_ett
                )
                VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'trabajador', %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, nombre, login, rol, grupo, vacaciones, horas_contrato, numero_sap, seccion_id
                """,
                (
                    nombre.strip(),
                    login_nombre.strip(),
                    clave,
                    grupo,
                    departamento_id,
                    vacaciones,
                    horas_contrato,
                    numero_sap,
                    seccion_id,
                    pausa,
                    coste,
                ),
            )
            creado = cur.fetchone()
            if not sin_horario:
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
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        nombre=creado["nombre"],
        login=creado["login"],
        rol=creado["rol"],
        grupo=creado["grupo"],
        vacaciones=float(creado["vacaciones"]),
        horas_contrato=float(creado["horas_contrato"]),
        numero_sap=creado["numero_sap"],
        seccion_id=str(creado["seccion_id"]) if creado["seccion_id"] else None,
        coste=coste,
    ), 201


@bp.put("/trabajadores/<login_nombre>")
@jwt_required()
def editar_trabajador(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    if not isinstance(cuerpo, dict):
        return jsonify(error="Faltan datos"), 400
    if campos_desconocidos(cuerpo):
        return jsonify(error="Campo no permitido"), 400

    try:
        with cursor() as cur:
            trabajador = _trabajador_permitido(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            persona = {
                "id": trabajador["id"],
                "rol": "trabajador",
                "departamento_id": trabajador["departamento_id"],
                "grupo": trabajador.get("grupo"),
            }
            cambios, error = editar_campos(cur, persona, cuerpo)
            if error:
                return error
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, rol="trabajador", **cambios), 200


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
            trabajador = _trabajador_permitido(cur, login_nombre)
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
        return error_bd(exc)

    return jsonify(login=login_nombre, activo=False, desde=desde.isoformat())


@bp.get("/trabajadores/inactivos")
@jwt_required()
def listar_inactivos():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403

    try:
        with cursor() as cur:
            departamento_id, error = departamento_lectura(
                cur, get_jwt_identity(), request.args.get("departamento_id")
            )
            if error:
                return error
            cur.execute(
                """
                SELECT u.nombre, u.login, u.grupo, s.nombre AS seccion
                FROM usuario u
                LEFT JOIN seccion s ON s.id = u.seccion_id
                WHERE u.rol = 'trabajador'
                  AND u.activo = false
                  AND u.departamento_id = %s
                ORDER BY u.nombre
                """,
                (departamento_id,),
            )
            filas = cur.fetchall()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        [
            {
                "nombre": fila["nombre"],
                "login": fila["login"],
                "grupo": fila["grupo"],
                "seccion": fila["seccion"],
            }
            for fila in filas
        ]
    )


@bp.put("/trabajadores/<login_nombre>/alta")
@jwt_required()
def dar_de_alta(login_nombre):
    rol = get_jwt().get("rol")
    if rol not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403

    try:
        with cursor() as cur:
            if rol == "admin":
                cur.execute(
                    """
                    SELECT id
                    FROM usuario
                    WHERE login = %s AND rol = 'trabajador'
                    """,
                    (login_nombre,),
                )
                trabajador = cur.fetchone()
                if trabajador is None:
                    return jsonify(error="No se ha encontrado el trabajador"), 404
            else:
                trabajador = _trabajador_permitido(cur, login_nombre)
                if trabajador is None:
                    return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                "UPDATE usuario SET activo = true WHERE id = %s",
                (trabajador["id"],),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, activo=True)


@bp.put("/trabajadores/<login_nombre>/numero-sap")
@jwt_required()
def cambiar_numero_sap(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    numero_sap, error = validaciones.numero_sap(cuerpo.get("numero_sap"))
    if error:
        return error

    try:
        with cursor() as cur:
            trabajador = _trabajador_permitido(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            if sap_ocupado(cur, numero_sap, trabajador["id"]):
                return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
            cur.execute(
                "UPDATE usuario SET numero_sap = %s WHERE id = %s",
                (numero_sap, trabajador["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.errors.UniqueViolation as exc:
        return error_unico(exc)
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, numero_sap=numero_sap)


@bp.put("/trabajadores/<login_nombre>/clave")
@jwt_required()
def cambiar_clave(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    clave = cuerpo.get("clave")
    if not isinstance(clave, str) or not clave.strip():
        return jsonify(error="Faltan datos"), 400

    try:
        with cursor() as cur:
            trabajador = _trabajador_permitido(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                """
                UPDATE usuario
                SET clave = crypt(%s, gen_salt('bf'))
                WHERE id = %s
                """,
                (clave, trabajador["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre)


@bp.put("/trabajadores/<login_nombre>/seccion")
@jwt_required()
def cambiar_seccion(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    seccion_id, error = leer_seccion_id(cuerpo, opcional=False)
    if error:
        return error

    try:
        with cursor() as cur:
            trabajador = _trabajador_permitido(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            error = comprobar_seccion(cur, trabajador["departamento_id"], seccion_id)
            if error:
                return error
            cur.execute(
                """
                UPDATE usuario
                SET seccion_id = %s
                WHERE id = %s
                """,
                (seccion_id, trabajador["id"]),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        login=login_nombre,
        seccion_id=str(seccion_id) if seccion_id else None,
    )


def guardar_horario(cur, usuario_id, cuerpo):
    """Valida el horario y, si hay cursor, lo escribe. Sin cursor solo valida."""
    filas, error = _horario_dias(None if not isinstance(cuerpo, dict) else cuerpo.get("horario_dias"))
    if error:
        return None, error
    desde, error = _desde_futuro(None if not isinstance(cuerpo, dict) else cuerpo.get("desde"))
    if error:
        return None, error
    if cur is not None:
        cur.execute(
            """
            DELETE FROM horario_dia
            WHERE usuario_id = %s AND desde = %s
            """,
            (usuario_id, desde),
        )
        cur.execute(
            """
            INSERT INTO horario_version (usuario_id, desde)
            VALUES (%s, %s)
            ON CONFLICT (usuario_id, desde) DO NOTHING
            """,
            (usuario_id, desde),
        )
        for dia, inicio, fin in filas:
            cur.execute(
                """
                INSERT INTO horario_dia (
                    usuario_id, desde, dia_semana, horario_inicio, horario_fin
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (usuario_id, desde, dia, inicio, fin),
            )
    return {
        "desde": desde.isoformat(),
        "horario": [
            {
                "dia_semana": dia,
                "inicio": hora_texto(inicio),
                "fin": hora_texto(fin),
            }
            for dia, inicio, fin in filas
        ],
    }, None


@bp.put("/trabajadores/<login_nombre>/horario")
@jwt_required()
def cambiar_horario(login_nombre):
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    _datos, error = guardar_horario(None, None, cuerpo)
    if error:
        return error

    try:
        with cursor() as cur:
            trabajador = _trabajador_permitido(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            datos, error = guardar_horario(cur, trabajador["id"], cuerpo)
            if error:
                return error
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre, **datos)


@bp.put("/mandos/propio/horario")
@jwt_required()
def cambiar_horario_propio():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    if cuerpo.get("login") not in (None, ""):
        return jsonify(error="Campo no permitido"), 400
    _datos, error = guardar_horario(None, None, cuerpo)
    if error:
        return error

    try:
        with cursor() as cur:
            datos, error = guardar_horario(cur, get_jwt_identity(), cuerpo)
            if error:
                return error
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(**datos)


@bp.get("/trabajadores/<login_nombre>/ficha")
@jwt_required()
def ficha(login_nombre):
    rol = get_jwt().get("rol")
    if rol not in ("mando", "trabajador", "admin"):
        return jsonify(error="No autorizado"), 403
    anio, error = _anio(request.args.get("anio"))
    if error:
        return error
    inicio = date(anio, 1, 1)
    fin = date(anio, 12, 31)

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.nombre, u.grupo, u.departamento_id,
                       u.horas_convenio, u.horas_contrato,
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
            elif rol == "admin":
                if trabajador is None:
                    return jsonify(error="No se ha encontrado el trabajador"), 404
            elif trabajador is None or not departamento_permitido(
                cur, get_jwt_identity(), trabajador["departamento_id"]
            ):
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
            habituales, pausas = _habituales(cur, [trabajador["id"]])
            habitual = habituales.get(trabajador["id"], True)
            pausa = pausas.get(trabajador["id"], 0)
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
            usados_v = dias_v_usados(cur, trabajador["id"], anio)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    horas_mes = [0.0] * 12
    realizadas_mes = [0.0] * 12
    ausencias = {"V": 0, "B": 0, "P": 0, "F": 0}
    festivos_trabajados = 0
    sabados_trabajados = 0
    dias = []
    dia = inicio
    while dia <= fin:
        turno, _origen = resolver_turno(
            dia, turnos.get(dia), versiones, noche_inicio, noche_fin, habitual, pausa
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
        if turno is not None:
            realizadas_mes[dia.month - 1] += horas_computables(
                turno["ausencia"], turno["horas_planificadas"]
            )
        dia += timedelta(days=1)
    ausencias["V"] = usados_v
    for ajuste in ajustes:
        fecha = date.fromisoformat(ajuste["fecha"])
        realizadas_mes[fecha.month - 1] += ajuste["horas"]

    respuesta = {
        "nombre": trabajador["nombre"],
        "departamento": trabajador["departamento"],
        "grupo": trabajador["grupo"],
        "horas_por_mes": [round(valor, 2) for valor in horas_mes],
        "ausencias": ausencias,
        "festivos_trabajados": festivos_trabajados,
        "sabados_trabajados": sabados_trabajados,
        "ajustes": ajustes,
        "dias": dias,
    }
    if rol in ("mando", "admin"):
        realizadas = round(sum(realizadas_mes), 2)
        convenio = round(
            convenio_anual(trabajador["horas_convenio"], trabajador["horas_contrato"]),
            2,
        )
        respuesta["horas_realizadas_por_mes"] = [round(valor, 2) for valor in realizadas_mes]
        respuesta["horas_realizadas"] = realizadas
        respuesta["convenio_anual"] = convenio
        respuesta["saldo"] = round(realizadas - convenio, 2)
    return jsonify(respuesta)


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


def _departamento_alta(cur, pedido):
    if get_jwt().get("rol") == "admin":
        if pedido in (None, ""):
            return None, (jsonify(error="Faltan datos"), 400)
        try:
            identificador = UUID(str(pedido).strip())
        except (ValueError, AttributeError):
            return None, (jsonify(error="No se ha encontrado el departamento"), 404)
        cur.execute("SELECT 1 FROM departamento WHERE id = %s", (identificador,))
        if cur.fetchone() is None:
            return None, (jsonify(error="No se ha encontrado el departamento"), 404)
        return identificador, None
    ids = departamentos_del_mando(cur, get_jwt_identity())
    if not ids:
        return None, (jsonify(error="No autorizado"), 403)
    if pedido in (None, ""):
        if len(ids) != 1:
            return None, (jsonify(error="Faltan datos"), 400)
        return ids[0], None
    if not departamento_permitido(cur, get_jwt_identity(), pedido):
        return None, (jsonify(error="No se ha encontrado el departamento"), 404)
    return pedido, None


def _trabajador_permitido(cur, login_nombre):
    cur.execute(
        """
        SELECT id, departamento_id, grupo
        FROM usuario
        WHERE login = %s AND rol = 'trabajador'
        """,
        (login_nombre,),
    )
    trabajador = cur.fetchone()
    if trabajador is None or not departamento_permitido(
        cur, get_jwt_identity(), trabajador["departamento_id"]
    ):
        return None
    return trabajador
