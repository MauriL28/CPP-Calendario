from datetime import date, time
from unittest.mock import patch

from app import create_app
from horas import horas_de_turno
from rutas.turnos import _pausa_cabe
from turnos_base import resolver_turno
from tests.test_alta_trabajador import DEPARTAMENTO, Conexion, Cursor, cuerpo, token
from tests.test_edicion_usuarios import _cambiar_pausa, _cursor_pausa, _turno_pausa
from tests.test_pausa_inicio import LUNES, TRABAJADOR, horario, put

MENSAJE = "La pausa tiene que ser un múltiplo de 5 minutos, de 0 a 180"
NOCHE_INICIO = time(22, 0)
NOCHE_FIN = time(6, 0)


class CursorAlta(Cursor):
    def __init__(self, departamentos):
        super().__init__(departamentos)
        self.pausa = None

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        if texto.startswith("INSERT INTO usuario"):
            self.pausa = (params or ())[9]
        super().execute(sql, params)


def _alta(minutos):
    app = create_app()
    cursor = CursorAlta([DEPARTAMENTO])
    datos = cuerpo()
    datos["pausa_minutos"] = minutos
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().post(
            "/trabajadores",
            json=datos,
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )
    return respuesta, cursor


def test_el_alta_acepta_15_45_y_90():
    for minutos in (15, 45, 90):
        respuesta, cursor = _alta(minutos)
        assert respuesta.status_code == 201
        assert cursor.pausa == minutos


def test_el_alta_rechaza_7_y_200():
    for minutos in (7, 200):
        respuesta, cursor = _alta(minutos)
        assert respuesta.status_code == 400
        assert respuesta.get_json()["error"] == MENSAJE
        assert cursor.insertados == []


def test_la_edicion_acepta_15_45_y_90():
    for minutos in (15, 45, 90):
        cursor = _cursor_pausa()
        respuesta = _cambiar_pausa(cursor, minutos)
        assert respuesta.status_code == 200
        assert respuesta.get_json()["pausa_minutos"] == minutos


def test_la_edicion_rechaza_7_y_200():
    for minutos in (7, 200):
        cursor = _cursor_pausa()
        respuesta = _cambiar_pausa(cursor, minutos)
        assert respuesta.status_code == 400
        assert respuesta.get_json()["error"] == MENSAJE
        assert cursor.updates == []


def test_quince_minutos_de_pausa_restan_un_cuarto():
    assert horas_de_turno(time(8, 0), time(16, 0), NOCHE_INICIO, NOCHE_FIN, 15) == (7.75, 0.0)
    habitual = [{"desde": date(2026, 1, 1), "dias": {0: (time(8, 0), time(16, 0))}}]
    turno, origen = resolver_turno(
        date(2026, 11, 9), None, habitual, NOCHE_INICIO, NOCHE_FIN, True, 15
    )
    assert origen == "habitual"
    assert turno["horas_planificadas"] == 7.75


def test_una_franja_de_45_minutos_tiene_que_caber_en_el_turno():
    assert _pausa_cabe(time(8, 0), time(16, 0), time(15, 15), 45)
    assert not _pausa_cabe(time(8, 0), time(16, 0), time(15, 30), 45)

    aceptada, cursor = put(horario(pausa_inicio="15:15"), pausa=45)
    assert aceptada.status_code == 200
    assert cursor.turnos[(TRABAJADOR, LUNES)]["pausa_inicio"] == time(15, 15)
    assert cursor.turnos[(TRABAJADOR, LUNES)]["horas_planificadas"] == 7.25

    rechazada, _cursor = put(horario(pausa_inicio="15:30"), pausa=45)
    assert rechazada.status_code == 400
    assert rechazada.get_json()["error"] == "La pausa tiene que estar dentro del turno"


def test_cambiar_de_30_a_45_recalcula_y_borra_la_franja_si_no_cabe():
    cursor = _cursor_pausa()
    hoy = date.today()
    cursor.turnos = [_turno_pausa(hoy, time(15, 30), horas=7.5)]

    respuesta = _cambiar_pausa(cursor, 45)

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_minutos"] == 45
    assert cursor.turnos[0]["pausa_inicio"] is None
    assert cursor.turnos[0]["horas_planificadas"] == 7.25
