from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from calendar import monthrange

import psycopg
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from exportar_turnos import _libro, _nombre_archivo
from errores import error_bd
from horas import hora_texto, horas_de_turno, parse_hora
from mandos import departamento_lectura, departamento_permitido
from turnos_base import _material_rango, resolver_turno
from vacaciones import error_cupo_vacaciones

bp = Blueprint("turnos", __name__)

AUSENCIAS = {"L", "D", "V", "B", "F", "P", "SR", "FR", "HS", "PEND", "ST", "FT"}
AUSENCIAS_PROPIAS = {"V", "B", "P", "F", "L"}
CON_HORARIO = {"ST", "FT"}


def _lunes(texto, admite_tipo):
    try:
        desde = datetime.strptime(texto, "%Y-%m-%d").date()
    except (TypeError, ValueError) if admite_tipo else ValueError:
        return None, (jsonify(error="desde no es una fecha válida"), 400)
    if desde.weekday() != 0:
        return None, (jsonify(error="desde tiene que ser lunes"), 400)
    return desde, None


def _material_semana(cur, ids, dias):
    return _material_rango(cur, ids, dias[0], dias[6])


def _festivos_rango(cur, inicio, fin):
    cur.execute(
        """
        SELECT fecha, nombre
        FROM festivo
        WHERE fecha >= %s AND fecha <= %s
        """,
        (inicio, fin),
    )
    return {fila["fecha"]: fila["nombre"] for fila in cur.fetchall()}


def _festivos_semana(cur, dias):
    return _festivos_rango(cur, dias[0], dias[6])


def _dias_resueltos(
    usuario_id,
    dias,
    turnos,
    versiones,
    noche_inicio,
    noche_fin,
    festivos,
    habituales=None,
    pausas=None,
):
    suyas = versiones.get(usuario_id, [])
    habitual = True if habituales is None else habituales.get(usuario_id, True)
    pausa = 0 if pausas is None else pausas.get(usuario_id, 0)
    resultado = []
    for dia in dias:
        turno, origen = resolver_turno(
            dia,
            turnos.get((usuario_id, dia)),
            suyas,
            noche_inicio,
            noche_fin,
            habitual,
            pausa,
        )
        entrada = {"fecha": dia.isoformat(), "turno": turno, "festivo": dia in festivos}
        if origen is not None:
            entrada["origen"] = origen
        if dia in festivos:
            entrada["nombre"] = festivos[dia]
        resultado.append(entrada)
    return resultado


def _semana(desde):
    return [desde + timedelta(days=i) for i in range(7)]


def _mes(anio_texto, mes_texto):
    if anio_texto in (None, "") or mes_texto in (None, ""):
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        anio = int(anio_texto)
        mes = int(mes_texto)
        inicio = datetime(anio, mes, 1).date()
    except (TypeError, ValueError):
        return None, (jsonify(error="La fecha no es válida"), 400)
    ultimo = monthrange(anio, mes)[1]
    return [inicio + timedelta(days=i) for i in range(ultimo)], None


def _ajustes_del_periodo(cur, ids, inicio, fin):
    if not ids:
        return {}
    cur.execute(
        """
        SELECT usuario_afectado_id, fecha, horas, motivo
        FROM ajuste
        WHERE usuario_afectado_id = ANY(%s)
          AND fecha >= %s
          AND fecha <= %s
        ORDER BY fecha, id
        """,
        (list(ids), inicio, fin),
    )
    grupos = {}
    for fila in cur.fetchall():
        fecha = fila["fecha"].isoformat() if hasattr(fila["fecha"], "isoformat") else str(fila["fecha"])
        grupos.setdefault((str(fila["usuario_afectado_id"]), fecha), []).append(
            {"horas": float(fila["horas"]), "motivo": fila["motivo"]}
        )
    return grupos


def _anotar_ajustes(personas, trabajadores, ajustes):
    for persona, trabajador in zip(personas, trabajadores):
        for dia in persona["dias"]:
            lista = ajustes.get((str(trabajador["id"]), dia["fecha"]))
            if lista:
                dia["ajustes"] = lista


def _coste(trabajador):
    if trabajador.get("grupo") != "ETT":
        return None
    valor = trabajador.get("tarifas_ett")
    if valor is None:
        return None
    return float(valor)


def _trabajadores_resueltos(
    trabajadores,
    dias,
    turnos,
    versiones,
    noche_inicio,
    noche_fin,
    festivos,
    habituales=None,
    pausas=None,
):
    return [
        {
            "nombre": trabajador["nombre"],
            "login": trabajador["login"],
            "grupo": trabajador["grupo"],
            "dias": _dias_resueltos(
                trabajador["id"],
                dias,
                turnos,
                versiones,
                noche_inicio,
                noche_fin,
                festivos,
                habituales,
                pausas,
            ),
        }
        for trabajador in trabajadores
    ]


def _visible_en_semana(trabajador, dias, turnos):
    if trabajador["activo"]:
        return True
    return any((trabajador["id"], dia) in turnos for dia in dias)


def _departamento_lectura(cur):
    return departamento_lectura(cur, get_jwt_identity(), request.args.get("departamento_id"))


@bp.get("/turnos")
@jwt_required()
def listar_turnos():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403
    desde, error = _lunes(request.args.get("desde", ""), False)
    if error:
        return error
    dias = _semana(desde)

    try:
        with cursor() as cur:
            departamento_id, error = _departamento_lectura(cur)
            if error:
                return error
            cur.execute(
                """
                SELECT u.id, u.nombre, u.login, u.grupo, u.activo, u.tarifas_ett,
                       s.nombre AS seccion
                FROM usuario u
                LEFT JOIN seccion s ON s.id = u.seccion_id
                WHERE u.rol = 'trabajador' AND u.departamento_id = %s
                ORDER BY u.nombre
                """,
                (departamento_id,),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_semana(
                cur, [trabajador["id"] for trabajador in trabajadores], dias
            )
            festivos = _festivos_semana(cur, dias)
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
            ajustes = _ajustes_del_periodo(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    personas = [
        {
            "nombre": trabajador["nombre"],
            "login": trabajador["login"],
            "grupo": trabajador["grupo"],
            "seccion": trabajador["seccion"],
            "coste": _coste(trabajador),
            "dias": _dias_resueltos(
                trabajador["id"],
                dias,
                turnos,
                versiones,
                noche_inicio,
                noche_fin,
                festivos,
                habituales,
                pausas,
            ),
        }
        for trabajador in trabajadores
    ]
    _anotar_ajustes(personas, trabajadores, ajustes)
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
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
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE id = %s AND rol = 'trabajador'
                """,
                (get_jwt_identity(),),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="No autorizado"), 403
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_semana(
                cur, [trabajador["id"]], dias
            )
            festivos = _festivos_semana(cur, dias)
            if not _visible_en_semana(trabajador, dias, turnos):
                trabajador = None
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    personas = []
    if trabajador is not None:
        personas.append(
            {
                "nombre": trabajador["nombre"],
                "login": trabajador["login"],
                "grupo": trabajador["grupo"],
                "dias": _dias_resueltos(
                    trabajador["id"],
                    dias,
                    turnos,
                    versiones,
                    noche_inicio,
                    noche_fin,
                    festivos,
                    habituales,
                    pausas,
                ),
            }
        )
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
    )


def _turno_visible(turno, propio):
    if turno is None:
        return None
    ausencia = turno["ausencia"]
    if ausencia:
        if ausencia == "B" and not propio:
            ausencia = "A"
        if ausencia in CON_HORARIO:
            return {
                "ausencia": ausencia,
                "hora_inicio": turno["hora_inicio"],
                "hora_fin": turno["hora_fin"],
            }
        return {"ausencia": ausencia}
    return {
        "hora_inicio": turno["hora_inicio"],
        "hora_fin": turno["hora_fin"],
    }


def _dias_departamento(
    usuario_id,
    dias,
    turnos,
    versiones,
    noche_inicio,
    noche_fin,
    propio,
    habituales=None,
    con_origen=False,
    pausas=None,
):
    suyas = versiones.get(usuario_id, [])
    habitual = True if habituales is None else habituales.get(usuario_id, True)
    pausa = 0 if pausas is None else pausas.get(usuario_id, 0)
    resultado = []
    for dia in dias:
        turno, origen = resolver_turno(
            dia,
            turnos.get((usuario_id, dia)),
            suyas,
            noche_inicio,
            noche_fin,
            habitual,
            pausa,
        )
        entrada = {
            "fecha": dia.isoformat(),
            "turno": _turno_visible(turno, propio),
        }
        if con_origen:
            entrada["origen"] = origen or "vacio"
        resultado.append(entrada)
    return resultado


@bp.get("/turnos/departamento")
@jwt_required()
def listar_turnos_departamento():
    if get_jwt().get("rol") != "trabajador":
        return jsonify(error="No autorizado"), 403
    desde, error = _lunes(request.args.get("desde", ""), False)
    if error:
        return error
    hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    if desde != lunes_actual:
        return jsonify(error="Solo puedes consultar la semana actual"), 403
    dias = _semana(desde)
    yo = get_jwt_identity()

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT departamento_id
                FROM usuario
                WHERE id = %s AND rol = 'trabajador'
                """,
                (yo,),
            )
            propio = cur.fetchone()
            if propio is None or propio["departamento_id"] is None:
                return jsonify(error="No autorizado"), 403
            cur.execute(
                """
                SELECT u.id, u.nombre, u.grupo, s.nombre AS seccion
                FROM usuario u
                LEFT JOIN seccion s ON s.id = u.seccion_id
                WHERE u.rol = 'trabajador'
                  AND u.activo
                  AND u.departamento_id = %s
                ORDER BY u.nombre
                """,
                (propio["departamento_id"],),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_semana(
                cur, [trabajador["id"] for trabajador in trabajadores], dias
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=[
            {
                "id": str(trabajador["id"]),
                "nombre": trabajador["nombre"],
                "grupo": trabajador["grupo"],
                "seccion": trabajador["seccion"],
                "dias": _dias_departamento(
                    trabajador["id"],
                    dias,
                    turnos,
                    versiones,
                    noche_inicio,
                    noche_fin,
                    str(trabajador["id"]) == yo,
                    habituales,
                    pausas=pausas,
                ),
            }
            for trabajador in trabajadores
        ],
    )


@bp.get("/turnos/mes")
@jwt_required()
def listar_turnos_mes():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403
    dias, error = _mes(request.args.get("anio"), request.args.get("mes"))
    if error:
        return error

    try:
        with cursor() as cur:
            departamento_id, error = _departamento_lectura(cur)
            if error:
                return error
            cur.execute(
                """
                SELECT u.id, u.nombre, u.login, u.grupo, u.activo, u.tarifas_ett,
                       s.nombre AS seccion
                FROM usuario u
                LEFT JOIN seccion s ON s.id = u.seccion_id
                WHERE u.rol = 'trabajador' AND u.departamento_id = %s
                ORDER BY u.nombre
                """,
                (departamento_id,),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_rango(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
            ajustes = _ajustes_del_periodo(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    personas = _trabajadores_resueltos(
        trabajadores, dias, turnos, versiones, noche_inicio, noche_fin, festivos, habituales, pausas
    )
    for persona, trabajador in zip(personas, trabajadores):
        persona["seccion"] = trabajador["seccion"]
        persona["coste"] = _coste(trabajador)
    _anotar_ajustes(personas, trabajadores, ajustes)
    return jsonify(
        desde=dias[0].isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
    )


@bp.get("/turnos/mios/mes")
@jwt_required()
def listar_turnos_mios_mes():
    if get_jwt().get("rol") != "trabajador":
        return jsonify(error="No autorizado"), 403
    dias, error = _mes(request.args.get("anio"), request.args.get("mes"))
    if error:
        return error

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE id = %s AND rol = 'trabajador'
                """,
                (get_jwt_identity(),),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="No autorizado"), 403
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_rango(
                cur, [trabajador["id"]], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            if not _visible_en_semana(trabajador, dias, turnos):
                trabajador = None
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    personas = []
    if trabajador is not None:
        personas = _trabajadores_resueltos(
            [trabajador], dias, turnos, versiones, noche_inicio, noche_fin, festivos, habituales, pausas
        )
    return jsonify(
        desde=dias[0].isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
    )


def _delegacion_mando(cur, usuario_id):
    """Delegación del departamento al que pertenece el mando."""
    cur.execute(
        """
        SELECT d.delegacion_id
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        WHERE u.id = %s AND u.rol = 'mando'
        """,
        (usuario_id,),
    )
    fila = cur.fetchone()
    if fila is None or fila["delegacion_id"] is None:
        return None
    return fila["delegacion_id"]


def _personas_mandos(cur, delegacion_id):
    """Mandos activos de esa delegación y quien esté en su departamento mandos."""
    cur.execute(
        """
        SELECT id
        FROM departamento
        WHERE codigo = 'mandos' AND delegacion_id = %s
        """,
        (delegacion_id,),
    )
    mandos = cur.fetchone()
    depto_mandos = mandos["id"] if mandos else None
    cur.execute(
        """
        SELECT u.id, u.nombre, u.grupo, s.nombre AS seccion
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        LEFT JOIN seccion s ON s.id = u.seccion_id
        WHERE u.activo
          AND d.delegacion_id = %s
          AND (
                u.rol = 'mando'
             OR (%s IS NOT NULL AND u.departamento_id = %s)
          )
        ORDER BY u.nombre
        """,
        (delegacion_id, depto_mandos, depto_mandos),
    )
    return cur.fetchall()


def _cuadrante_mandos(cur, yo, dias):
    delegacion_id = _delegacion_mando(cur, yo)
    if delegacion_id is None:
        return None
    personas = _personas_mandos(cur, delegacion_id)
    turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_rango(
        cur, [persona["id"] for persona in personas], dias[0], dias[-1]
    )
    return [
        {
            "id": str(persona["id"]),
            "nombre": persona["nombre"],
            "grupo": persona["grupo"],
            "seccion": persona["seccion"],
            "dias": _dias_departamento(
                persona["id"],
                dias,
                turnos,
                versiones,
                noche_inicio,
                noche_fin,
                str(persona["id"]) == str(yo),
                habituales,
                con_origen=str(persona["id"]) == str(yo),
                pausas=pausas,
            ),
        }
        for persona in personas
    ]


@bp.get("/turnos/mandos")
@jwt_required()
def listar_turnos_mandos():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    desde, error = _lunes(request.args.get("desde", ""), False)
    if error:
        return error
    dias = _semana(desde)
    try:
        with cursor() as cur:
            trabajadores = _cuadrante_mandos(cur, get_jwt_identity(), dias)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    if trabajadores is None:
        return jsonify(error="No autorizado"), 403
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=trabajadores,
    )


@bp.get("/turnos/mandos/mes")
@jwt_required()
def listar_turnos_mandos_mes():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    dias, error = _mes(request.args.get("anio"), request.args.get("mes"))
    if error:
        return error
    try:
        with cursor() as cur:
            trabajadores = _cuadrante_mandos(cur, get_jwt_identity(), dias)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    if trabajadores is None:
        return jsonify(error="No autorizado"), 403
    return jsonify(
        desde=dias[0].isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=trabajadores,
    )


@bp.put("/turnos/mandos/vacaciones")
@jwt_required()
def guardar_vacaciones_mando():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    yo = get_jwt_identity()
    for clave in ("usuario", "usuario_id", "id"):
        valor = cuerpo.get(clave)
        if valor not in (None, "") and str(valor) != str(yo):
            return jsonify(error="No autorizado"), 403
    ausencia = cuerpo.get("ausencia")
    if ausencia == "":
        ausencia = None
    if ausencia not in (None, "V"):
        return jsonify(error="No autorizado"), 403
    codigo = cuerpo.get("codigo")
    if codigo not in (None, "", "V"):
        return jsonify(error="No autorizado"), 403
    vacaciones = cuerpo.get("vacaciones")
    if not isinstance(vacaciones, bool):
        return jsonify(error="Faltan datos"), 400
    hora_inicio = parse_hora(cuerpo.get("hora_inicio"))
    hora_fin = parse_hora(cuerpo.get("hora_fin"))
    if hora_inicio == "mal" or hora_fin == "mal":
        return jsonify(error="La hora no es válida"), 400
    if hora_inicio is not None or hora_fin is not None:
        return jsonify(error="Indica horario o ausencia, no las dos"), 400
    try:
        fecha = datetime.strptime(cuerpo.get("fecha"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify(error="La fecha no es válida"), 400

    try:
        with cursor() as cur:
            if isinstance(cuerpo.get("login"), str) and cuerpo["login"].strip():
                cur.execute(
                    """
                    SELECT id
                    FROM usuario
                    WHERE id = %s AND login = %s AND rol = 'mando'
                    """,
                    (yo, cuerpo["login"].strip()),
                )
                if cur.fetchone() is None:
                    return jsonify(error="No autorizado"), 403
            if _delegacion_mando(cur, yo) is None:
                return jsonify(error="No autorizado"), 403
            if vacaciones:
                texto = error_cupo_vacaciones(cur, yo, [fecha], [fecha])
                if texto:
                    return jsonify(error=texto), 409
                cur.execute(
                    """
                    INSERT INTO turno (
                        usuario_id, fecha, ausencia, hora_inicio, hora_fin,
                        horas_planificadas, horas_nocturnas
                    )
                    VALUES (%s, %s, 'V', NULL, NULL, 0, 0)
                    ON CONFLICT (usuario_id, fecha) DO UPDATE SET
                        ausencia = 'V',
                        hora_inicio = NULL,
                        hora_fin = NULL,
                        horas_planificadas = 0,
                        horas_nocturnas = 0
                    """,
                    (yo, fecha),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM turno
                    WHERE usuario_id = %s AND fecha = %s AND ausencia = 'V'
                    """,
                    (yo, fecha),
                )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(fecha=fecha.isoformat(), vacaciones=vacaciones)


def _sin_otro_usuario(cuerpo):
    for clave in ("login", "usuario"):
        valor = cuerpo.get(clave)
        if valor not in (None, ""):
            return jsonify(error="Campo no permitido"), 400
    return None


@bp.put("/turnos/mandos/propio")
@jwt_required()
def guardar_turno_mando():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    error = _sin_otro_usuario(cuerpo)
    if error:
        return error
    fechas, error = _fechas_semana(cuerpo.get("fechas"))
    if error:
        return error
    pedido, error = _pedido_turno(cuerpo)
    if error:
        return error
    if pedido["ausencia"] is not None and pedido["ausencia"] not in AUSENCIAS_PROPIAS:
        return jsonify(error="La ausencia no es válida"), 400
    yo = get_jwt_identity()
    fechas_v = fechas if pedido["ausencia"] == "V" else []

    try:
        with cursor() as cur:
            texto = error_cupo_vacaciones(cur, yo, fechas, fechas_v)
            if texto:
                return jsonify(error=texto), 409
            for fecha in fechas:
                _insertar_turno(cur, yo, fecha, pedido)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(guardados=len(fechas))


@bp.delete("/turnos/mandos/propio")
@jwt_required()
def borrar_turno_mando():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    try:
        fecha = datetime.strptime(cuerpo.get("fecha"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify(error="La fecha no es válida"), 400

    try:
        with cursor() as cur:
            cur.execute(
                """
                DELETE FROM turno
                WHERE usuario_id = %s AND fecha = %s
                RETURNING fecha
                """,
                (get_jwt_identity(), fecha),
            )
            if cur.fetchone() is None:
                return jsonify(error="No se ha encontrado el turno"), 404
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(fecha=fecha.isoformat())


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
            departamento_id, error = departamento_lectura(
                cur, get_jwt_identity(), cuerpo.get("departamento_id")
            )
            if error:
                return error
            texto = _error_copia_vacaciones(cur, departamento_id, desde, anterior, hasta)
            if texto:
                return jsonify(error=texto), 409
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
                (departamento_id, desde, hasta),
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
                (departamento_id, anterior, desde),
            )
            dias_copiados = cur.rowcount
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(desde=desde.isoformat(), dias_copiados=dias_copiados)


def _error_copia_vacaciones(cur, departamento_id, desde, anterior, hasta):
    cur.execute(
        """
        SELECT id, nombre
        FROM usuario
        WHERE rol = 'trabajador' AND departamento_id = %s
        """,
        (departamento_id,),
    )
    personas = cur.fetchall()
    if not personas:
        return None
    cur.execute(
        """
        SELECT usuario_id, fecha, ausencia::text AS ausencia
        FROM turno
        WHERE usuario_id = ANY(%s)
          AND fecha >= %s
          AND fecha <= %s
        """,
        ([persona["id"] for persona in personas], anterior, hasta),
    )
    por_usuario = {}
    for fila in cur.fetchall():
        por_usuario.setdefault(fila["usuario_id"], {})[fila["fecha"]] = fila["ausencia"]
    dias = [desde + timedelta(days=indice) for indice in range(7)]
    for persona in personas:
        suyos = por_usuario.get(persona["id"], {})
        fechas_v = [
            dia
            for dia in dias
            if suyos.get(dia - timedelta(days=7)) == "V"
        ]
        texto = error_cupo_vacaciones(
            cur, persona["id"], dias, fechas_v, persona["nombre"]
        )
        if texto:
            return texto
    return None


def _pedido_turno(cuerpo):
    ausencia = cuerpo.get("ausencia")
    if ausencia == "":
        ausencia = None
    hora_inicio = parse_hora(cuerpo.get("hora_inicio"))
    hora_fin = parse_hora(cuerpo.get("hora_fin"))
    if hora_inicio == "mal" or hora_fin == "mal":
        return None, (jsonify(error="La hora no es válida"), 400)
    hay_ausencia = ausencia is not None
    if hay_ausencia:
        if ausencia not in AUSENCIAS:
            return None, (jsonify(error="La ausencia no es válida"), 400)
        if ausencia in CON_HORARIO:
            if hora_inicio is None or hora_fin is None:
                return None, (jsonify(error="Indica el horario"), 400)
        elif hora_inicio is not None or hora_fin is not None:
            return None, (jsonify(error="Indica horario o ausencia, no las dos"), 400)
        else:
            hora_inicio = None
            hora_fin = None
    elif hora_inicio is None or hora_fin is None:
        return None, (jsonify(error="Indica un horario o una ausencia"), 400)
    return {
        "ausencia": ausencia,
        "hora_inicio": hora_inicio,
        "hora_fin": hora_fin,
    }, None


def _fechas_semana(valor):
    if not isinstance(valor, list) or not 1 <= len(valor) <= 7:
        return None, (jsonify(error="Faltan datos"), 400)
    fechas = []
    for texto in valor:
        try:
            fechas.append(datetime.strptime(texto, "%Y-%m-%d").date())
        except (TypeError, ValueError):
            return None, (jsonify(error="La fecha no es válida"), 400)
    if len(set(fechas)) != len(fechas):
        return None, (jsonify(error="Faltan datos"), 400)
    lunes = fechas[0] - timedelta(days=fechas[0].weekday())
    if any(fecha < lunes or fecha > lunes + timedelta(days=6) for fecha in fechas):
        return None, (jsonify(error="Faltan datos"), 400)
    return fechas, None


def _insertar_turno(cur, usuario_id, fecha, pedido):
    ausencia = pedido["ausencia"]
    hora_inicio = pedido["hora_inicio"]
    hora_fin = pedido["hora_fin"]
    if ausencia is not None and ausencia not in CON_HORARIO:
        planificadas, nocturnas = 0, 0
    else:
        cur.execute("SELECT noche_inicio, noche_fin FROM empresa WHERE id = 1")
        franja = cur.fetchone()
        if franja is None:
            noche_inicio = datetime.strptime("22:00", "%H:%M").time()
            noche_fin = datetime.strptime("06:00", "%H:%M").time()
        else:
            noche_inicio = franja["noche_inicio"]
            noche_fin = franja["noche_fin"]
        cur.execute(
            "SELECT pausa_minutos FROM usuario WHERE id = %s",
            (usuario_id,),
        )
        persona = cur.fetchone()
        pausa = 0 if persona is None else int(persona.get("pausa_minutos") or 0)
        planificadas, nocturnas = horas_de_turno(
            hora_inicio, hora_fin, noche_inicio, noche_fin, pausa
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
            usuario_id,
            fecha,
            ausencia,
            hora_inicio,
            hora_fin,
            planificadas,
            nocturnas,
        ),
    )
    return cur.fetchone()


def _trabajador_del_turno(cur, login_nombre):
    cur.execute(
        """
        SELECT id, departamento_id
        FROM usuario
        WHERE login = %s
          AND rol = 'trabajador'
        """,
        (login_nombre.strip(),),
    )
    trabajador = cur.fetchone()
    if trabajador is None or not departamento_permitido(
        cur, get_jwt_identity(), trabajador["departamento_id"]
    ):
        return None
    return trabajador


@bp.put("/turnos")
@jwt_required()
def guardar_turno():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("login")
    if not isinstance(login_nombre, str) or not login_nombre.strip():
        return jsonify(error="Faltan datos"), 400
    try:
        fecha = datetime.strptime(cuerpo.get("fecha"), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify(error="La fecha no es válida"), 400
    pedido, error = _pedido_turno(cuerpo)
    if error:
        return error

    try:
        with cursor() as cur:
            trabajador = _trabajador_del_turno(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            fechas_v = [fecha] if pedido["ausencia"] == "V" else []
            texto = error_cupo_vacaciones(cur, trabajador["id"], [fecha], fechas_v)
            if texto:
                return jsonify(error=texto), 409
            guardado = _insertar_turno(cur, trabajador["id"], fecha, pedido)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(
        login=login_nombre.strip(),
        fecha=guardado["fecha"].isoformat(),
        ausencia=guardado["ausencia"],
        hora_inicio=hora_texto(guardado["hora_inicio"]),
        hora_fin=hora_texto(guardado["hora_fin"]),
        horas_planificadas=float(guardado["horas_planificadas"]),
        horas_nocturnas=float(guardado["horas_nocturnas"]),
    )


@bp.put("/turnos/varios")
@jwt_required()
def guardar_turnos():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("login")
    if not isinstance(login_nombre, str) or not login_nombre.strip():
        return jsonify(error="Faltan datos"), 400
    fechas, error = _fechas_semana(cuerpo.get("fechas"))
    if error:
        return error
    pedido, error = _pedido_turno(cuerpo)
    if error:
        return error

    try:
        with cursor() as cur:
            trabajador = _trabajador_del_turno(cur, login_nombre)
            if trabajador is None:
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            fechas_v = fechas if pedido["ausencia"] == "V" else []
            texto = error_cupo_vacaciones(cur, trabajador["id"], fechas, fechas_v)
            if texto:
                return jsonify(error=texto), 409
            for fecha in fechas:
                _insertar_turno(cur, trabajador["id"], fecha, pedido)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(guardados=len(fechas))


@bp.delete("/turnos")
@jwt_required()
def borrar_turno():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403

    cuerpo = request.get_json(silent=True) or {}
    login_nombre = cuerpo.get("login")
    fecha_texto = cuerpo.get("fecha")
    if not isinstance(login_nombre, str) or not login_nombre.strip():
        return jsonify(error="Faltan datos"), 400
    try:
        fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return jsonify(error="La fecha no es válida"), 400

    try:
        with cursor() as cur:
            cur.execute(
                """
                SELECT id, departamento_id
                FROM usuario
                WHERE login = %s
                  AND rol = 'trabajador'
                """,
                (login_nombre.strip(),),
            )
            trabajador = cur.fetchone()
            if trabajador is None or not departamento_permitido(
                cur, get_jwt_identity(), trabajador["departamento_id"]
            ):
                return jsonify(error="Ese trabajador no es de tu departamento"), 404
            cur.execute(
                "DELETE FROM turno WHERE usuario_id = %s AND fecha = %s",
                (trabajador["id"], fecha),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return jsonify(login=login_nombre.strip(), fecha=fecha.isoformat())


@bp.get("/turnos/exportar")
@jwt_required()
def exportar_turnos():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    anio = request.args.get("anio")
    mes = request.args.get("mes")
    if anio not in (None, "") or mes not in (None, ""):
        dias, error = _mes(anio, mes)
        mensual = True
    elif request.args.get("desde"):
        desde, error = _lunes(request.args.get("desde", ""), False)
        dias = None if error else _semana(desde)
        mensual = False
    else:
        return jsonify(error="Faltan datos"), 400
    if error:
        return error

    try:
        with cursor() as cur:
            departamento_id, error = _departamento_lectura(cur)
            if error:
                return error
            cur.execute(
                "SELECT codigo FROM departamento WHERE id = %s",
                (departamento_id,),
            )
            departamento = cur.fetchone()
            if departamento is None:
                return jsonify(error="No se ha encontrado el departamento"), 404
            cur.execute(
                """
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE rol = 'trabajador' AND departamento_id = %s
                ORDER BY nombre
                """,
                (departamento_id,),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin, habituales, pausas = _material_rango(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
            resueltos = _trabajadores_resueltos(
                trabajadores, dias, turnos, versiones, noche_inicio, noche_fin, festivos, habituales, pausas
            )
            codigo = departamento["codigo"]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)

    return send_file(
        _libro(resueltos, dias, mensual),
        as_attachment=True,
        download_name=_nombre_archivo(codigo, dias, mensual),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
