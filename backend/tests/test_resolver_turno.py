from datetime import date, time
from decimal import Decimal

from rutas.turnos import resolver_turno

NOCHE_INICIO = time(22, 0)
NOCHE_FIN = time(6, 0)
LUNES = date(2026, 10, 26)
DOMINGO = date(2026, 10, 25)


def versiones(desde, dias):
    return [{"desde": desde, "dias": dias}]


def test_un_turno_guardado_no_usa_el_horario_habitual():
    fila = {
        "ausencia": "L",
        "hora_inicio": None,
        "hora_fin": None,
        "horas_planificadas": Decimal("0"),
        "horas_nocturnas": Decimal("0"),
    }
    habitual = versiones(date(2026, 1, 1), {0: (time(8, 0), time(16, 0))})
    turno, origen = resolver_turno(LUNES, fila, habitual, NOCHE_INICIO, NOCHE_FIN, False)
    assert origen == "guardado"
    assert turno["ausencia"] == "L"
    assert turno["horas_planificadas"] == 0.0


def test_sin_turno_guardado_usa_el_horario_de_ese_dia():
    habitual = versiones(date(2026, 1, 1), {0: (time(8, 0), time(16, 0))})
    turno, origen = resolver_turno(LUNES, None, habitual, NOCHE_INICIO, NOCHE_FIN)
    assert origen == "habitual"
    assert turno["ausencia"] is None
    assert turno["hora_inicio"] == "08:00"
    assert turno["hora_fin"] == "16:00"
    assert turno["horas_planificadas"] == 8.0
    assert turno["horas_nocturnas"] == 0.0


def test_el_domingo_sin_plan_es_descanso_automatico():
    turno, origen = resolver_turno(DOMINGO, None, [], NOCHE_INICIO, NOCHE_FIN)
    assert origen == "habitual"
    assert turno == {
        "ausencia": "D",
        "hora_inicio": None,
        "hora_fin": None,
        "horas_planificadas": 0.0,
        "horas_nocturnas": 0.0,
    }


def test_sin_horario_habitual_el_dia_queda_vacio_tambien_en_domingo():
    habitual = versiones(date(2026, 1, 1), {6: (time(8, 0), time(14, 0))})
    turno, origen = resolver_turno(DOMINGO, None, habitual, NOCHE_INICIO, NOCHE_FIN, False)
    assert (turno, origen) == (None, "vacio")


def test_la_version_vigente_depende_de_la_fecha():
    horario = [
        {"desde": date(2026, 1, 1), "dias": {0: (time(8, 0), time(16, 0))}},
        {"desde": date(2026, 11, 2), "dias": {0: (time(9, 0), time(17, 0))}},
    ]
    anterior, origen_anterior = resolver_turno(
        LUNES, None, horario, NOCHE_INICIO, NOCHE_FIN
    )
    posterior, origen_posterior = resolver_turno(
        date(2026, 11, 2), None, horario, NOCHE_INICIO, NOCHE_FIN
    )
    assert origen_anterior == origen_posterior == "habitual"
    assert anterior["hora_inicio"] == "08:00"
    assert posterior["hora_inicio"] == "09:00"
    assert posterior["hora_fin"] == "17:00"


def test_un_horario_posterior_a_la_fecha_no_se_aplica():
    futuro = versiones(date(2026, 11, 2), {0: (time(9, 0), time(17, 0))})
    assert resolver_turno(LUNES, None, futuro, NOCHE_INICIO, NOCHE_FIN) == (None, None)
