from datetime import time

import pytest

from horas import horas_de_turno

NOCHE_INICIO = time(22, 0)
NOCHE_FIN = time(6, 0)


def test_turno_de_dia_no_tiene_horas_nocturnas():
    planificadas, nocturnas = horas_de_turno(time(8, 0), time(16, 0), NOCHE_INICIO, NOCHE_FIN)
    assert (planificadas, nocturnas) == (8.0, 0.0)


def test_turno_que_cruza_medianoche_cuenta_la_noche():
    # SAP 101882: 20:21 → 04:00 son 7 h 39 min. De 22:00 a 04:00 son nocturnas.
    planificadas, nocturnas = horas_de_turno(time(20, 21), time(4, 0), NOCHE_INICIO, NOCHE_FIN)
    assert (planificadas, nocturnas) == (7.65, 6.0)


def test_turno_entero_dentro_de_la_franja_nocturna():
    planificadas, nocturnas = horas_de_turno(time(22, 0), time(6, 0), NOCHE_INICIO, NOCHE_FIN)
    assert (planificadas, nocturnas) == (8.0, 8.0)


def test_misma_hora_de_entrada_y_salida_cuenta_veinticuatro_horas():
    # fin <= inicio se trata como cruce de medianoche: no existe un resultado de 0 h.
    planificadas, nocturnas = horas_de_turno(time(8, 0), time(8, 0), NOCHE_INICIO, NOCHE_FIN)
    assert planificadas == 24.0
    assert nocturnas == 8.0


def test_horario_invalido_no_se_interpreta():
    with pytest.raises(AttributeError):
        horas_de_turno("08:00", time(16, 0), NOCHE_INICIO, NOCHE_FIN)
