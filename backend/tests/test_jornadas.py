from datetime import date, datetime, time, timedelta
from decimal import Decimal

from fichajes import _partir_jornadas, calcular_dia, segundos_pausa_con_huecos


def evento(tipo, hora, fecha, orden):
    return {"tipo": tipo, "hora": hora, "fecha": fecha, "orden": orden}


def tipos(jornada):
    return [evento["tipo"] for evento in jornada]


def test_jornada_simple():
    dia = date(2026, 9, 3)
    jornadas = _partir_jornadas(
        [
            evento("Llegada", time(8, 0), dia, 1),
            evento("Salida", time(16, 0), dia, 2),
        ]
    )
    assert [tipos(jornada) for jornada in jornadas] == [["Llegada", "Salida"]]


def test_comida_de_taha_sigue_en_la_misma_jornada():
    # Taha Fraoui, 03/09/2026. El hueco 14:25:19 → 15:33:30 es 1 h 08 min 11 s.
    dia = date(2026, 9, 3)
    marcas = [
        evento("Llegada", time(11, 8, 0), dia, 1),
        evento("Salida", time(14, 25, 19), dia, 2),
        evento("Llegada", time(15, 33, 30), dia, 3),
        evento("Salida", time(20, 10, 52), dia, 4),
    ]
    jornadas = _partir_jornadas(marcas)
    assert len(jornadas) == 1
    assert tipos(jornadas[0]) == ["Llegada", "Salida", "Llegada", "Salida"]

    calculo = calcular_dia(marcas)
    assert calculo["incidencia"] is False
    # 7 h 54 min 41 s, los 7 h 55 min del ejemplo, redondeados a 7,91 h.
    assert calculo["horas_trabajadas"] == Decimal("7.91")
    assert calculo["horas_pausa"] == Decimal("0.00")
    assert segundos_pausa_con_huecos(marcas) == Decimal(4091)


def test_noche_de_sap_101882_cruza_medianoche_en_una_jornada():
    # 07/09 20:21 → 08/09 04:00 son 7 h 39 min. La llegada de las 20:22 ya es otra.
    primera = date(2026, 9, 7)
    segunda = date(2026, 9, 8)
    marcas = [
        evento("Llegada", time(20, 21), primera, 1),
        evento("Salida", time(4, 0), segunda, 2),
        evento("Llegada", time(20, 22), segunda, 3),
    ]
    jornadas = _partir_jornadas(marcas)
    assert [tipos(jornada) for jornada in jornadas] == [
        ["Llegada", "Salida"],
        ["Llegada"],
    ]
    assert jornadas[0][0]["fecha"] == primera

    calculo = calcular_dia(jornadas[0])
    assert calculo["incidencia"] is False
    assert calculo["horas_trabajadas"] == Decimal("7.65")


def test_hueco_de_exactamente_cuatro_horas_sigue_en_la_misma_jornada():
    dia = date(2026, 9, 3)
    salida = time(14, 0)
    llegada = (datetime.combine(dia, salida) + timedelta(hours=4)).time()
    jornadas = _partir_jornadas(
        [
            evento("Llegada", time(8, 0), dia, 1),
            evento("Salida", salida, dia, 2),
            evento("Llegada", llegada, dia, 3),
        ]
    )
    assert len(jornadas) == 1


def test_hueco_de_mas_de_cuatro_horas_abre_otra_jornada():
    dia = date(2026, 9, 3)
    jornadas = _partir_jornadas(
        [
            evento("Llegada", time(8, 0), dia, 1),
            evento("Salida", time(12, 0), dia, 2),
            evento("Llegada", time(16, 0, 1), dia, 3),
            evento("Salida", time(20, 0), dia, 4),
        ]
    )
    assert [tipos(jornada) for jornada in jornadas] == [
        ["Llegada", "Salida"],
        ["Llegada", "Salida"],
    ]


def test_llegada_sin_salida_a_mas_de_dieciseis_horas():
    llegada = date(2026, 9, 7)
    salida = date(2026, 9, 8)
    jornadas = _partir_jornadas(
        [
            evento("Llegada", time(8, 0), llegada, 1),
            evento("Salida", time(0, 0, 1), salida, 2),
        ]
    )
    assert [tipos(jornada) for jornada in jornadas] == [["Llegada"], ["Salida"]]


def test_salida_suelta():
    dia = date(2026, 9, 8)
    jornadas = _partir_jornadas([evento("Salida", time(4, 0), dia, 1)])
    assert [tipos(jornada) for jornada in jornadas] == [["Salida"]]


def test_pausa_fichada():
    dia = date(2026, 9, 3)
    marcas = [
        evento("Llegada", time(8, 0), dia, 1),
        evento("Inicio Pausa", time(12, 0), dia, 2),
        evento("Final Pausa", time(13, 0), dia, 3),
        evento("Salida", time(16, 0), dia, 4),
    ]
    assert segundos_pausa_con_huecos(marcas) == Decimal(3600)


def test_hueco_ya_cubierto_por_pausa_no_se_cuenta_dos_veces():
    dia = date(2026, 9, 3)
    marcas = [
        evento("Llegada", time(8, 0), dia, 1),
        evento("Salida", time(12, 0), dia, 2),
        evento("Inicio Pausa", time(12, 10), dia, 3),
        evento("Final Pausa", time(13, 0), dia, 4),
        evento("Llegada", time(13, 8), dia, 5),
    ]
    # Hueco 12:00→13:08 (68 min). La pausa de 50 min ya está dentro: total 68 min, no 118.
    assert segundos_pausa_con_huecos(marcas) == Decimal(68 * 60)


def test_sin_eventos_la_pausa_no_se_calcula():
    assert segundos_pausa_con_huecos([]) is None
