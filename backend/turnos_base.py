from datetime import datetime

from db import cursor
from horas import hora_texto, horas_de_turno


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


def resolver_turno(fecha, fila, versiones, noche_inicio, noche_fin, usa_horario_habitual=True):
    if fila is not None:
        return _turno(fila), "guardado"
    if not usa_horario_habitual:
        return None, "vacio"
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
        habitual = _habituales(cur, [usuario]).get(usuario, True)
    return resolver_turno(fecha, None, versiones, noche_inicio, noche_fin, habitual)[0]


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
    return turnos, versiones, noche_inicio, noche_fin, _habituales(cur, ids)


def _habituales(cur, ids):
    if not ids:
        return {}
    cur.execute(
        """
        SELECT u.id, d.usa_horario_habitual
        FROM usuario u
        JOIN departamento d ON d.id = u.departamento_id
        WHERE u.id = ANY(%s)
        """,
        (list(ids),),
    )
    return {fila["id"]: fila["usa_horario_habitual"] for fila in cur.fetchall()}
