from datetime import datetime, timedelta
from calendar import monthrange
from io import BytesIO

import psycopg
from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

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


def _franja(cur):
    cur.execute("SELECT noche_inicio, noche_fin FROM empresa WHERE id = 1")
    franja = cur.fetchone()
    if franja is None:
        return (
            datetime.strptime("22:00", "%H:%M").time(),
            datetime.strptime("06:00", "%H:%M").time(),
        )
    return franja["noche_inicio"], franja["noche_fin"]


def _agrupar_versiones(filas):
    grupos = {}
    for fila in filas:
        clave = (fila["usuario_id"], fila["desde"])
        version = grupos.get(clave)
        if version is None:
            version = {"desde": fila["desde"], "dias": {}}
            grupos[clave] = version
        if fila["dia_semana"] is not None:
            version["dias"][fila["dia_semana"]] = (fila["horario_inicio"], fila["horario_fin"])
    por_usuario = {}
    for (usuario_id, _), version in grupos.items():
        por_usuario.setdefault(usuario_id, []).append(version)
    for versiones in por_usuario.values():
        versiones.sort(key=lambda version: version["desde"])
    return por_usuario


def _horas_habituales(fecha, versiones):
    version = None
    for candidata in versiones:
        if candidata["desde"] <= fecha:
            version = candidata
        else:
            break
    if version is None or not version["dias"]:
        return None
    return version["dias"].get(fecha.weekday())


def _domingo_libre():
    return {
        "ausencia": "D",
        "hora_inicio": None,
        "hora_fin": None,
        "horas_planificadas": 0.0,
        "horas_nocturnas": 0.0,
    }, "habitual"


def resolver_turno(fecha, fila, versiones, noche_inicio, noche_fin):
    if fila is not None:
        return _turno(fila), "guardado"
    horas = _horas_habituales(fecha, versiones)
    if horas is None:
        if fecha.weekday() == 6:
            return _domingo_libre()
        return None, None
    inicio, fin = horas
    planificadas, nocturnas = horas_de_turno(inicio, fin, noche_inicio, noche_fin)
    return {
        "ausencia": None,
        "hora_inicio": hora_texto(inicio),
        "hora_fin": hora_texto(fin),
        "horas_planificadas": planificadas,
        "horas_nocturnas": nocturnas,
    }, "habitual"


def turno_efectivo(usuario, fecha):
    with cursor() as cur:
        cur.execute(
            """
            SELECT ausencia::text AS ausencia, hora_inicio, hora_fin,
                   horas_planificadas, horas_nocturnas
            FROM turno
            WHERE usuario_id = %s AND fecha = %s
            """,
            (usuario, fecha),
        )
        fila = cur.fetchone()
        if fila is not None:
            return resolver_turno(fecha, fila, [], None, None)[0]
        cur.execute(
            """
            SELECT v.usuario_id, v.desde, d.dia_semana, d.horario_inicio, d.horario_fin
            FROM horario_version v
            LEFT JOIN horario_dia d
              ON d.usuario_id = v.usuario_id AND d.desde = v.desde
            WHERE v.usuario_id = %s AND v.desde <= %s
            """,
            (usuario, fecha),
        )
        agrupadas = _agrupar_versiones(cur.fetchall())
        versiones = next(iter(agrupadas.values()), [])
        noche_inicio, noche_fin = _franja(cur)
    return resolver_turno(fecha, None, versiones, noche_inicio, noche_fin)[0]


def _material_rango(cur, ids, inicio, fin):
    turnos = {}
    versiones = {}
    if ids:
        cur.execute(
            """
            SELECT usuario_id, fecha, ausencia::text AS ausencia,
                   hora_inicio, hora_fin, horas_planificadas, horas_nocturnas
            FROM turno
            WHERE usuario_id = ANY(%s)
              AND fecha >= %s
              AND fecha <= %s
            """,
            (ids, inicio, fin),
        )
        for fila in cur.fetchall():
            turnos[(fila["usuario_id"], fila["fecha"])] = fila
        cur.execute(
            """
            SELECT v.usuario_id, v.desde, d.dia_semana, d.horario_inicio, d.horario_fin
            FROM horario_version v
            LEFT JOIN horario_dia d
              ON d.usuario_id = v.usuario_id AND d.desde = v.desde
            WHERE v.usuario_id = ANY(%s)
              AND v.desde <= %s
            """,
            (ids, fin),
        )
        versiones = _agrupar_versiones(cur.fetchall())
    noche_inicio, noche_fin = _franja(cur)
    return turnos, versiones, noche_inicio, noche_fin


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


def _dias_resueltos(usuario_id, dias, turnos, versiones, noche_inicio, noche_fin, festivos):
    suyas = versiones.get(usuario_id, [])
    resultado = []
    for dia in dias:
        turno, origen = resolver_turno(
            dia,
            turnos.get((usuario_id, dia)),
            suyas,
            noche_inicio,
            noche_fin,
        )
        entrada = {"fecha": dia.isoformat(), "turno": turno, "festivo": dia in festivos}
        if turno is not None:
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


def _trabajadores_resueltos(trabajadores, dias, turnos, versiones, noche_inicio, noche_fin, festivos):
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
            ),
        }
        for trabajador in trabajadores
    ]


def _visible_en_semana(trabajador, dias, turnos):
    if trabajador["activo"]:
        return True
    return any((trabajador["id"], dia) in turnos for dia in dias)


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
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE rol = 'trabajador' AND departamento_id = %s
                ORDER BY nombre
                """,
                (mando["departamento_id"],),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin = _material_semana(
                cur, [trabajador["id"] for trabajador in trabajadores], dias
            )
            festivos = _festivos_semana(cur, dias)
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=[
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
                ),
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
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE id = %s AND rol = 'trabajador'
                """,
                (get_jwt_identity(),),
            )
            trabajador = cur.fetchone()
            if trabajador is None:
                return jsonify(error="No autorizado"), 403
            turnos, versiones, noche_inicio, noche_fin = _material_semana(
                cur, [trabajador["id"]], dias
            )
            festivos = _festivos_semana(cur, dias)
            if not _visible_en_semana(trabajador, dias, turnos):
                trabajador = None
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

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
                ),
            }
        )
    return jsonify(
        desde=desde.isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
    )


@bp.get("/turnos/mes")
@jwt_required()
def listar_turnos_mes():
    if get_jwt().get("rol") != "mando":
        return jsonify(error="No autorizado"), 403
    dias, error = _mes(request.args.get("anio"), request.args.get("mes"))
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
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE rol = 'trabajador' AND departamento_id = %s
                ORDER BY nombre
                """,
                (mando["departamento_id"],),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin = _material_rango(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        desde=dias[0].isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=_trabajadores_resueltos(
            trabajadores, dias, turnos, versiones, noche_inicio, noche_fin, festivos
        ),
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
            turnos, versiones, noche_inicio, noche_fin = _material_rango(
                cur, [trabajador["id"]], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            if not _visible_en_semana(trabajador, dias, turnos):
                trabajador = None
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    personas = []
    if trabajador is not None:
        personas = _trabajadores_resueltos(
            [trabajador], dias, turnos, versiones, noche_inicio, noche_fin, festivos
        )
    return jsonify(
        desde=dias[0].isoformat(),
        dias=[dia.isoformat() for dia in dias],
        trabajadores=personas,
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
            cur.execute(
                "DELETE FROM turno WHERE usuario_id = %s AND fecha = %s",
                (trabajador["id"], fecha),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(login=login_nombre.strip(), fecha=fecha.isoformat())


MESES_ARCHIVO = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
DIAS_LARGOS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
DIAS_CORTOS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
GRUPOS_EXCEL = (("STEF", "Personal STEF"), ("ETT", "ETT"))


def _hora_compacta(hora):
    horas, minutos = hora.split(":")
    texto = str(int(horas))
    if int(minutos) == 0:
        return texto
    return f"{texto}:{minutos}"


def _texto_celda(turno):
    if not turno:
        return ""
    if turno["ausencia"]:
        return turno["ausencia"]
    return f"{_hora_compacta(turno['hora_inicio'])}-{_hora_compacta(turno['hora_fin'])}"


def _nombre_archivo(codigo, dias, mensual):
    depto = "".join(caracter if caracter.isalnum() else "_" for caracter in codigo).strip("_").upper()
    if not depto:
        depto = "CUADRANTE"
    if mensual:
        return f"{depto}_{MESES_ARCHIVO[dias[0].month - 1]}_{dias[0].year}.xlsx"
    semana = dias[0].isocalendar()
    return f"{depto}_semana_{semana.week}_{semana.year}.xlsx"


def _cabecera_dia(dia, mensual):
    if mensual:
        return f"{DIAS_CORTOS[dia.weekday()]}\n{dia.day}"
    return f"{DIAS_LARGOS[dia.weekday()]}\n{dia.strftime('%d/%m')}"


def _filas_excel(trabajadores):
    filas = []
    vistos = set()
    for grupo, titulo in GRUPOS_EXCEL:
        personas = [trabajador for trabajador in trabajadores if trabajador["grupo"] == grupo]
        if not personas:
            continue
        filas.append(("grupo", titulo))
        for trabajador in personas:
            vistos.add(trabajador["login"])
            filas.append(("persona", trabajador))
    for trabajador in trabajadores:
        if trabajador["login"] not in vistos:
            filas.append(("persona", trabajador))
    return filas


def _fuente_base(libro):
    libro._fonts[0] = Font(name="Arial", size=12)


def _libro(trabajadores, dias, mensual):
    libro = Workbook()
    _fuente_base(libro)
    hoja = libro.active
    hoja.title = "Cuadrante"
    hoja.freeze_panes = "B2"
    fuente = Font(name="Arial", size=12)
    cabecera = Font(name="Arial", size=12, bold=True)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    grupo_fondo = PatternFill("solid", fgColor="F2F2F2")
    hoja.cell(1, 1, "Trabajador").font = cabecera
    for indice, dia in enumerate(dias, start=2):
        celda = hoja.cell(1, indice, _cabecera_dia(dia, mensual))
        celda.font = cabecera
        celda.alignment = centro
    fila_excel = 2
    for tipo, contenido in _filas_excel(trabajadores):
        if tipo == "grupo":
            celda = hoja.cell(fila_excel, 1, contenido)
            celda.font = cabecera
            celda.fill = grupo_fondo
            if dias:
                hoja.merge_cells(
                    start_row=fila_excel,
                    start_column=1,
                    end_row=fila_excel,
                    end_column=len(dias) + 1,
                )
                for columna in range(2, len(dias) + 2):
                    vacia = hoja.cell(fila_excel, columna)
                    vacia.font = fuente
                    vacia.fill = grupo_fondo
        else:
            hoja.cell(fila_excel, 1, contenido["nombre"]).font = fuente
            for indice, dia in enumerate(contenido["dias"], start=2):
                celda = hoja.cell(fila_excel, indice, _texto_celda(dia["turno"]))
                celda.font = fuente
                celda.alignment = centro
        fila_excel += 1
    hoja.column_dimensions["A"].width = 24
    ancho = 12 if not mensual else 6
    for indice in range(2, len(dias) + 2):
        hoja.column_dimensions[hoja.cell(1, indice).column_letter].width = ancho
    hoja.row_dimensions[1].height = 30
    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer


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
            cur.execute(
                """
                SELECT u.departamento_id, d.codigo AS departamento
                FROM usuario u
                JOIN departamento d ON d.id = u.departamento_id
                WHERE u.id = %s AND u.rol = 'mando'
                """,
                (get_jwt_identity(),),
            )
            mando = cur.fetchone()
            if mando is None or mando["departamento_id"] is None:
                return jsonify(error="No autorizado"), 403
            cur.execute(
                """
                SELECT id, nombre, login, grupo, activo
                FROM usuario
                WHERE rol = 'trabajador' AND departamento_id = %s
                ORDER BY nombre
                """,
                (mando["departamento_id"],),
            )
            trabajadores = cur.fetchall()
            turnos, versiones, noche_inicio, noche_fin = _material_rango(
                cur, [trabajador["id"] for trabajador in trabajadores], dias[0], dias[-1]
            )
            festivos = _festivos_rango(cur, dias[0], dias[-1])
            trabajadores = [
                trabajador
                for trabajador in trabajadores
                if _visible_en_semana(trabajador, dias, turnos)
            ]
            resueltos = _trabajadores_resueltos(
                trabajadores, dias, turnos, versiones, noche_inicio, noche_fin, festivos
            )
            codigo = mando["departamento"]
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return send_file(
        _libro(resueltos, dias, mensual),
        as_attachment=True,
        download_name=_nombre_archivo(codigo, dias, mensual),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
