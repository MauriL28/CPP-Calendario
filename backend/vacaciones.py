from datetime import date


def dias_v_usados(cur, usuario_id, anio):
    """Días con ausencia V guardada en el año natural."""
    cur.execute(
        """
        SELECT COUNT(*) AS usados
        FROM turno
        WHERE usuario_id = %s
          AND ausencia = 'V'
          AND fecha >= %s
          AND fecha <= %s
        """,
        (usuario_id, date(anio, 1, 1), date(anio, 12, 31)),
    )
    return int(cur.fetchone()["usados"])


def _numero(valor):
    numero = float(valor)
    if numero.is_integer():
        return str(int(numero))
    return str(numero)


def _fechas_v(cur, usuario_id, fechas):
    if not fechas:
        return set()
    cur.execute(
        """
        SELECT fecha
        FROM turno
        WHERE usuario_id = %s
          AND ausencia = 'V'
          AND fecha = ANY(%s)
        """,
        (usuario_id, list(fechas)),
    )
    return {fila["fecha"] for fila in cur.fetchall()}


def error_cupo_vacaciones(cur, usuario_id, fechas_escritas, fechas_v, nombre=None):
    """None si cabe. Si no, el texto del 409. No escribe nada.

    fechas_escritas son los días que esta petición sustituye o borra.
    fechas_v son los que quedarán con ausencia V.
    """
    fechas_v = list(fechas_v)
    if not fechas_v:
        return None
    cupo = cupo_vacaciones(cur, usuario_id)
    if cupo is None:
        return None
    escritas = list(dict.fromkeys([*fechas_escritas, *fechas_v]))
    ya = _fechas_v(cur, usuario_id, escritas)
    anios = sorted({fecha.year for fecha in escritas})
    for anio in anios:
        pasan = [fecha for fecha in fechas_v if fecha.year == anio]
        if not pasan:
            continue
        ya_anio = sum(1 for fecha in escritas if fecha.year == anio and fecha in ya)
        if len(pasan) <= ya_anio:
            continue
        usados = dias_v_usados(cur, usuario_id, anio)
        usados_tras = usados - ya_anio + len(pasan)
        if usados_tras > cupo:
            restantes = cupo - (usados - ya_anio)
            texto = (
                f"Solo quedan {_numero(restantes)} días de vacaciones"
                f" y intentas asignar {_numero(len(pasan))}"
            )
            if nombre:
                texto = f"{nombre}: {texto}"
            return texto
    return None


def cupo_vacaciones(cur, usuario_id):
    """Cupo anual en días, o None si el usuario no tiene valor."""
    cur.execute(
        """
        SELECT vacaciones
        FROM usuario
        WHERE id = %s
        """,
        (usuario_id,),
    )
    fila = cur.fetchone()
    if fila is None or fila["vacaciones"] is None:
        return None
    return float(fila["vacaciones"])
