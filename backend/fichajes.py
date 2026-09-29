"""Carga de fichajes: un evento por fila del Excel y las horas del día.

No cruza con el turno y no rellena coincide. Horas en NUMERIC(8,2):
segundos / 3600, redondeo half-up a 2 decimales, sin sumar 24 h.
"""

import sys
from collections import defaultdict
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP

import openpyxl

from db import cursor

TIPOS = ("Llegada", "Salida", "Inicio Pausa", "Final Pausa")
COLUMNAS = ("Nº pers.", "Texto CHT", "Fe.lóg.", "Hora")


def _sap(valor):
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, int):
        return str(valor)
    if valor is None:
        return ""
    return str(valor).strip()


def _tipo(valor):
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _fecha(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    raise ValueError(f"Fe.lóg. no es una fecha: {valor!r}")


def _hora(valor):
    if isinstance(valor, datetime):
        return valor.time()
    if isinstance(valor, time):
        return valor
    raise ValueError(f"Hora ausente o no válida: {valor!r}")


def leer_excel(ruta):
    """Devuelve (filas_leidas, filas_saltadas, eventos). No escribe el xlsx."""
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        if "Data" not in wb.sheetnames:
            raise ValueError("el libro no tiene la hoja Data")
        filas = wb["Data"].iter_rows(values_only=True)
        cabecera = next(filas, None)
        if cabecera is None:
            raise ValueError("la hoja Data está vacía")
        indice = {nombre: i for i, nombre in enumerate(cabecera)}
        faltan = [nombre for nombre in COLUMNAS if nombre not in indice]
        if faltan:
            raise ValueError("faltan columnas: " + ", ".join(faltan))
        leidas = 0
        saltadas = 0
        eventos = []
        for numero_fila, fila in enumerate(filas, start=2):
            leidas += 1
            tipo = _tipo(fila[indice["Texto CHT"]])
            fecha = _fecha(fila[indice["Fe.lóg."]])
            if tipo is None and fecha is None:
                saltadas += 1
                continue
            sap = _sap(fila[indice["Nº pers."]])
            if not sap:
                raise ValueError(f"fila {numero_fila}: Nº pers. vacío")
            eventos.append(
                {
                    "orden": numero_fila,
                    "numero_sap": sap,
                    "tipo": tipo,
                    "fecha": fecha,
                    "hora": _hora(fila[indice["Hora"]]),
                }
            )
        return leidas, saltadas, eventos
    finally:
        wb.close()


def _segundos(inicio, fin):
    def total(valor):
        entero = valor.hour * 3600 + valor.minute * 60 + valor.second
        return Decimal(entero) + Decimal(valor.microsecond) / Decimal(1000000)

    return total(fin) - total(inicio)


def _horas(segundos):
    return (segundos / Decimal(3600)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _incidencia(motivo):
    return {
        "incidencia": True,
        "motivo": motivo,
        "horas_trabajadas": None,
        "horas_pausa": None,
    }


def calcular_dia(eventos):
    """Dos máquinas independientes. Empiezan cerradas. Eventos ya ordenados.

    Abrir abierto, cerrar cerrado, seguir abierto al final del día, tipo
    vacío o distinto de los cuatro, o un cierre con el reloj hacia atrás
    (sin sumar 24 h): el día es incidencia y las horas quedan vacías.
    """
    trabajo_desde = None
    pausa_desde = None
    segundos_trabajo = Decimal(0)
    segundos_pausa = Decimal(0)
    for ev in eventos:
        tipo = ev["tipo"]
        hora = ev["hora"]
        if tipo not in TIPOS:
            return _incidencia(f"tipo no válido ({tipo or 'vacío'}) a las {hora}")
        if tipo == "Llegada":
            if trabajo_desde is not None:
                return _incidencia(
                    f"Llegada a las {hora} con la jornada ya abierta desde {trabajo_desde}"
                )
            trabajo_desde = hora
        elif tipo == "Salida":
            if trabajo_desde is None:
                return _incidencia(f"Salida a las {hora} sin Llegada")
            delta = _segundos(trabajo_desde, hora)
            if delta < 0:
                return _incidencia(
                    f"Salida a las {hora} anterior a la Llegada de las {trabajo_desde}"
                )
            segundos_trabajo += delta
            trabajo_desde = None
        elif tipo == "Inicio Pausa":
            if pausa_desde is not None:
                return _incidencia(
                    f"Inicio Pausa a las {hora} con la pausa ya abierta desde {pausa_desde}"
                )
            pausa_desde = hora
        else:
            if pausa_desde is None:
                return _incidencia(f"Final Pausa a las {hora} sin Inicio Pausa")
            delta = _segundos(pausa_desde, hora)
            if delta < 0:
                return _incidencia(
                    f"Final Pausa a las {hora} anterior al Inicio Pausa de las {pausa_desde}"
                )
            segundos_pausa += delta
            pausa_desde = None
    abiertos = []
    if trabajo_desde is not None:
        abiertos.append(f"Llegada a las {trabajo_desde} sin Salida")
    if pausa_desde is not None:
        abiertos.append(f"Inicio Pausa a las {pausa_desde} sin Final Pausa")
    if abiertos:
        return _incidencia("; ".join(abiertos))
    return {
        "incidencia": False,
        "motivo": None,
        "horas_trabajadas": _horas(segundos_trabajo),
        "horas_pausa": _horas(segundos_pausa),
    }


def agrupar_dias(eventos):
    """Persona: usuario_id si está, si no el numero_sap. Orden: hora, luego orden."""
    grupos = defaultdict(list)
    for ev in eventos:
        persona = ev["usuario_id"] if ev["usuario_id"] else ev["numero_sap"]
        grupos[(persona, ev["fecha"])].append(ev)
    dias = []
    for (persona, fecha), lista in grupos.items():
        lista.sort(key=lambda ev: (ev["hora"], ev["orden"]))
        calculo = calcular_dia(lista)
        usuario_id = lista[0]["usuario_id"]
        dias.append(
            {
                "persona": persona,
                "usuario_id": usuario_id,
                "numero_sap": lista[0]["numero_sap"],
                "fecha": fecha,
                "eventos": lista,
                **calculo,
            }
        )
    return dias


def _borrar_fichajes_previos(cur):
    cur.execute(
        """
        DELETE FROM fichaje AS f
        WHERE f.coincide IS NULL
          AND EXISTS (
              SELECT 1
              FROM fichaje_evento AS e
              WHERE e.usuario_id = f.usuario_id
                AND e.fecha = f.fecha
          )
        """
    )


def _insertar_eventos(cur, eventos):
    cur.execute("DELETE FROM fichaje_evento")
    cur.executemany(
        """
        INSERT INTO fichaje_evento (orden, numero_sap, tipo, fecha, hora)
        VALUES (%s, %s, %s, %s, %s)
        """,
        [
            (ev["orden"], ev["numero_sap"], ev["tipo"], ev["fecha"], ev["hora"])
            for ev in eventos
        ],
    )
    cur.execute(
        """
        UPDATE fichaje_evento AS e
        SET usuario_id = m.id
        FROM (
            SELECT numero_sap, (array_agg(id))[1] AS id
            FROM usuario
            WHERE numero_sap IS NOT NULL
            GROUP BY numero_sap
            HAVING COUNT(*) = 1
        ) AS m
        WHERE e.numero_sap = m.numero_sap
        """
    )


def _leer_eventos(cur):
    cur.execute(
        """
        SELECT orden, numero_sap, usuario_id, tipo, fecha, hora
        FROM fichaje_evento
        ORDER BY orden
        """
    )
    return list(cur.fetchall())


def _insertar_fichajes(cur, dias):
    insertados = 0
    for dia in dias:
        if dia["usuario_id"] is None or dia["fecha"] is None:
            continue
        cur.execute(
            """
            SELECT COUNT(*) AS n
            FROM fichaje
            WHERE usuario_id = %s AND fecha = %s AND coincide IS NOT NULL
            """,
            (dia["usuario_id"], dia["fecha"]),
        )
        if cur.fetchone()["n"]:
            continue
        cur.execute(
            """
            DELETE FROM fichaje
            WHERE usuario_id = %s AND fecha = %s AND coincide IS NULL
            """,
            (dia["usuario_id"], dia["fecha"]),
        )
        cur.execute(
            """
            INSERT INTO fichaje (
                usuario_id, fecha, horas_fichadas,
                horas_trabajadas, horas_pausa, incidencia, coincide
            )
            VALUES (%s, %s, 0, %s, %s, %s, NULL)
            """,
            (
                dia["usuario_id"],
                dia["fecha"],
                dia["horas_trabajadas"],
                dia["horas_pausa"],
                dia["incidencia"],
            ),
        )
        insertados += 1
    return insertados


def _numeros_ambiguos(cur):
    cur.execute(
        """
        SELECT u.numero_sap
        FROM usuario AS u
        JOIN (SELECT DISTINCT numero_sap FROM fichaje_evento) AS e
          ON e.numero_sap = u.numero_sap
        GROUP BY u.numero_sap
        HAVING COUNT(*) > 1
        """
    )
    return {fila["numero_sap"] for fila in cur.fetchall()}


def cargar(ruta):
    leidas, saltadas, eventos = leer_excel(ruta)
    with cursor() as cur:
        _borrar_fichajes_previos(cur)
        _insertar_eventos(cur, eventos)
        guardados = _leer_eventos(cur)
        ambiguos = _numeros_ambiguos(cur)
        dias = agrupar_dias(guardados)
        fichajes = _insertar_fichajes(cur, dias)
        cur.execute(
            "SELECT COUNT(*) AS n FROM usuario WHERE numero_sap IS NOT NULL"
        )
        usuarios_con_sap = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM fichaje_evento")
        filas_evento = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM fichaje")
        filas_fichaje = cur.fetchone()["n"]
    con_usuario = [ev for ev in guardados if ev["usuario_id"] is not None]
    sin_coincidencia = [
        ev
        for ev in guardados
        if ev["usuario_id"] is None and ev["numero_sap"] not in ambiguos
    ]
    filas_ambiguas = [
        ev for ev in guardados if ev["numero_sap"] in ambiguos
    ]
    dias_resueltos = [dia for dia in dias if dia["usuario_id"] is not None]
    return {
        "filas_leidas": leidas,
        "filas_saltadas": saltadas,
        "filas_insertadas": filas_evento,
        "filas_con_usuario": len(con_usuario),
        "filas_sin_coincidencia": len(sin_coincidencia),
        "filas_ambiguas": len(filas_ambiguas),
        "numeros_ambiguos": len(ambiguos),
        "personas_excel": len({ev["numero_sap"] for ev in guardados}),
        "personas_emparejadas": len({ev["numero_sap"] for ev in con_usuario}),
        "usuarios_con_sap": usuarios_con_sap,
        "dias": len(dias),
        "dias_resueltos": len(dias_resueltos),
        "incidencias": sum(1 for dia in dias if dia["incidencia"]),
        "incidencias_resueltas": sum(1 for dia in dias_resueltos if dia["incidencia"]),
        "fichajes_insertados": fichajes,
        "fichajes_en_tabla": filas_fichaje,
        "dias_detalle": dias,
    }


def _texto_eventos(dia):
    return ", ".join(f"{ev['tipo']} {ev['hora']}" for ev in dia["eventos"])


def _imprimir_dia(titulo, dia):
    if dia is None:
        print(f"{titulo}: ninguno")
        return
    print(
        f"{titulo}: sap={dia['numero_sap']} fecha={dia['fecha']} "
        f"trabajadas={dia['horas_trabajadas']} pausa={dia['horas_pausa']} "
        f"incidencia={dia['incidencia']} motivo={dia['motivo']}"
    )
    print(f"  {_texto_eventos(dia)}")


def main():
    if len(sys.argv) != 2:
        print("uso: python fichajes.py RUTA.xlsx", file=sys.stderr)
        return 2
    comprobar_calcular_dia()
    resultado = cargar(sys.argv[1])
    print(f"filas_leidas={resultado['filas_leidas']}")
    print(f"filas_saltadas={resultado['filas_saltadas']}")
    print(f"filas_insertadas={resultado['filas_insertadas']}")
    print(f"filas_con_usuario={resultado['filas_con_usuario']}")
    print(f"filas_sin_coincidencia={resultado['filas_sin_coincidencia']}")
    print(f"filas_ambiguas={resultado['filas_ambiguas']}")
    print(f"numeros_ambiguos={resultado['numeros_ambiguos']}")
    print(f"personas_excel={resultado['personas_excel']}")
    print(f"personas_emparejadas={resultado['personas_emparejadas']}")
    print(f"usuarios_con_sap={resultado['usuarios_con_sap']}")
    print(f"dias={resultado['dias']}")
    print(f"dias_resueltos={resultado['dias_resueltos']}")
    print(f"incidencias={resultado['incidencias']}")
    print(f"incidencias_resueltas={resultado['incidencias_resueltas']}")
    print(f"fichajes_insertados={resultado['fichajes_insertados']}")
    print(f"fichajes_en_tabla={resultado['fichajes_en_tabla']}")
    dias = resultado["dias_detalle"]
    normal = next(
        (
            dia
            for dia in sorted(dias, key=lambda d: (d["numero_sap"], d["fecha"] or date.min))
            if not dia["incidencia"]
            and dia["horas_trabajadas"] > 0
            and dia["horas_pausa"] > 0
        ),
        None,
    )
    incidencia = next(
        (
            dia
            for dia in sorted(dias, key=lambda d: (d["numero_sap"], d["fecha"] or date.min))
            if dia["incidencia"]
        ),
        None,
    )
    _imprimir_dia("ejemplo_normal", normal)
    _imprimir_dia("ejemplo_incidencia", incidencia)
    return 0


def comprobar_calcular_dia():
    normal = calcular_dia(
        [
            {"tipo": "Llegada", "hora": time(5, 59, 40)},
            {"tipo": "Inicio Pausa", "hora": time(12, 43, 38)},
            {"tipo": "Final Pausa", "hora": time(13, 2, 53)},
            {"tipo": "Salida", "hora": time(13, 42, 46)},
        ]
    )
    if (
        normal["incidencia"]
        or normal["horas_trabajadas"] != Decimal("7.72")
        or normal["horas_pausa"] != Decimal("0.32")
    ):
        raise AssertionError(normal)
    noche = calcular_dia(
        [
            {"tipo": "Llegada", "hora": time(22, 0, 0)},
            {"tipo": "Salida", "hora": time(0, 30, 0)},
        ]
    )
    if not noche["incidencia"] or noche["horas_trabajadas"] is not None:
        raise AssertionError(noche)
    abierta = calcular_dia([{"tipo": "Llegada", "hora": time(20, 21, 10)}])
    if not abierta["incidencia"] or "sin Salida" not in abierta["motivo"]:
        raise AssertionError(abierta)
    rara = calcular_dia([{"tipo": None, "hora": time(8, 0, 0)}])
    if not rara["incidencia"] or rara["horas_trabajadas"] is not None:
        raise AssertionError(rara)


if __name__ == "__main__":
    sys.exit(main())
