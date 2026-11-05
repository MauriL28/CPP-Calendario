from datetime import date, datetime, time
from decimal import Decimal

import pytest

from fichajes import _cruce, _turnos_resueltos

USUARIO = "trab-1"
LUNES = date(2026, 11, 2)


def evento(tipo, hora, orden):
    return {
        "tipo": tipo,
        "hora": hora,
        "fecha": LUNES,
        "orden": orden,
        "usuario_id": USUARIO,
        "numero_sap": "200",
    }


def dia(eventos, horas):
    return {
        "usuario_id": USUARIO,
        "numero_sap": "200",
        "fecha": LUNES,
        "incidencia": False,
        "motivo": None,
        "horas_trabajadas": Decimal(horas),
        "eventos": eventos,
    }


def turno(plan, ausencia=None, inicio="10:00", fin="19:00"):
    return {
        "ausencia": ausencia,
        "hora_inicio": inicio,
        "hora_fin": fin,
        "horas_planificadas": plan,
        "horas_nocturnas": 0,
    }


def cruce(jornada, plan, pausa, ausencia=None, inicio="10:00", fin="19:00"):
    turnos = {(USUARIO, LUNES): (turno(plan, ausencia, inicio, fin), "habitual", pausa)}
    return _cruce(jornada, turnos)


class Cursor:
    def __init__(self, pausa):
        self.pausa = pausa
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT usuario_id, fecha"):
            return
        if "FROM horario_version" in texto:
            self._filas = [
                {
                    "usuario_id": USUARIO,
                    "desde": date(2026, 1, 1),
                    "dia_semana": 0,
                    "horario_inicio": time(10, 0),
                    "horario_fin": time(19, 0),
                }
            ]
            return
        if texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
            return
        if "pausa_minutos" in texto:
            self._filas = [
                {
                    "id": USUARIO,
                    "usa_horario_habitual": True,
                    "pausa_minutos": self.pausa,
                }
            ]
            return
        raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


@pytest.mark.parametrize(
    ("eventos", "horas", "resuelve", "plan_esperado"),
    [
        pytest.param(
            [evento("Llegada", time(10, 0), 1), evento("Salida", time(19, 0), 2)],
            "9.00",
            True,
            Decimal("8.00"),
            id="sin-pausa-fichada",
        ),
        pytest.param(
            [
                evento("Llegada", time(10, 0), 1),
                evento("Salida", time(14, 0), 2),
                evento("Llegada", time(15, 0), 3),
                evento("Salida", time(19, 0), 4),
            ],
            "8.00",
            False,
            None,
            id="hueco-de-comer",
        ),
        pytest.param(
            [
                evento("Llegada", time(10, 0), 1),
                evento("Inicio Pausa", time(13, 0), 2),
                evento("Final Pausa", time(14, 0), 3),
                evento("Salida", time(19, 0), 4),
            ],
            "9.00",
            False,
            None,
            id="pausa-fichada",
        ),
    ],
)
def test_el_cruce_con_pausa_asignada_da_ok(eventos, horas, resuelve, plan_esperado):
    jornada = dia(eventos, horas)
    if resuelve:
        estado, plan = _cruce(jornada, _turnos_resueltos(Cursor(60), [jornada]))
    else:
        estado, plan = cruce(jornada, 8, 60)
    assert estado == "ok"
    if plan_esperado is not None:
        assert plan == plan_esperado


def test_pausa_cero_compara_las_horas_trabajadas_como_antes():
    jornada = dia(
        [evento("Llegada", time(10, 0), 1), evento("Salida", time(19, 0), 2)],
        "9.00",
    )
    assert cruce(jornada, 9, 0)[0] == "ok"


def test_nueve_horas_con_pausa_cero_y_plan_ocho_es_descuadre():
    jornada = dia(
        [evento("Llegada", time(10, 0), 1), evento("Salida", time(19, 0), 2)],
        "9.00",
    )
    assert cruce(jornada, 8, 0)[0] == "descuadre"


def test_una_ausencia_sin_horas_no_descuenta_la_pausa():
    jornada = dia(
        [evento("Llegada", time(10, 0), 1), evento("Salida", time(11, 0), 2)],
        "1.00",
    )
    assert cruce(jornada, 0, 60, ausencia="V", inicio=None, fin=None)[0] == "descuadre"

from datetime import datetime
from io import BytesIO
from unittest.mock import patch

from openpyxl import load_workbook

from app import create_app
from seguridad import emitir_token

USUARIO_ANALISIS = "11111111-1111-1111-1111-111111111111"
DIA = date(2026, 11, 2)


class CursorAnalisis:
    def __init__(self):
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if "COUNT(*)" in texto:
            self._fila = {
                "total": 1,
                "ok": 0,
                "descuadre": 1,
                "sin_plan": 0,
                "sin_emparejar": 0,
            }
            return
        if "FROM fichaje f" in texto:
            self._filas = [
                {
                    "usuario_id": USUARIO_ANALISIS,
                    "numero_sap": "200",
                    "nombre": "Nerea Lago",
                    "departamento": "Tráfico",
                    "fecha": DIA,
                    "incidencia": False,
                    "horas_planificadas": Decimal("8.00"),
                    "horas_trabajadas": Decimal("8.00"),
                    "horas_pausa": Decimal("0.00"),
                    "coincide": "descuadre",
                }
            ]
            return
        if "MIN(fecha + hora)" in texto:
            self._fila = {
                "inicio": datetime(2026, 11, 2, 10, 0),
                "fin": datetime(2026, 11, 2, 18, 0),
            }
            return
        if "FROM fichaje_evento" in texto:
            self._filas = [
                {
                    "numero_sap": "200",
                    "usuario_id": USUARIO_ANALISIS,
                    "tipo": "Llegada",
                    "fecha": DIA,
                    "hora": time(10, 0),
                    "orden": 1,
                },
                {
                    "numero_sap": "200",
                    "usuario_id": USUARIO_ANALISIS,
                    "tipo": "Salida",
                    "fecha": DIA,
                    "hora": time(18, 0),
                    "orden": 2,
                },
            ]
            return
        if texto.startswith("SELECT usuario_id, fecha"):
            self._filas = [
                {
                    "usuario_id": USUARIO_ANALISIS,
                    "fecha": DIA,
                    "ausencia": None,
                    "hora_inicio": time(10, 0),
                    "hora_fin": time(19, 0),
                    "horas_planificadas": Decimal("8.00"),
                    "horas_nocturnas": Decimal("0.00"),
                }
            ]
            return
        if "FROM horario_version" in texto:
            return
        if texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
            return
        if "pausa_minutos" in texto:
            self._filas = [
                {"id": USUARIO_ANALISIS, "usa_horario_habitual": True, "pausa_minutos": 60}
            ]
            return
        raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


def token(app):
    with app.app_context():
        return emitir_token(USUARIO_ANALISIS, "admin", ["60I"], "Admin", None)


def pedir(ruta):
    app = create_app()
    with patch("rutas.fichajes.cursor", return_value=Conexion(CursorAnalisis())):
        return app.test_client().get(
            ruta,
            headers={"Authorization": f"Bearer {token(app)}"},
        )


def test_listado_detalle_y_excel_usan_la_misma_diferencia():
    listado = pedir("/fichajes/analisis")
    excel = pedir("/fichajes/analisis/exportar")

    assert listado.status_code == 200
    fila = listado.get_json()["filas"][0]
    assert fila["diferencia"] == -1.0
    assert fila["fichado_min"] == 420
    assert fila["previsto_min"] == 480
    assert fila["diferencia_min"] == -60
    assert fila["pausa_min"] == 0
    assert round(fila["diferencia"] * 60) == fila["diferencia_min"]

    assert excel.status_code == 200
    hoja = load_workbook(BytesIO(excel.data)).active
    assert hoja.cell(2, 7).value == "-1,0"
    assert hoja.cell(2, 12).value == fila["previsto_min"]
    assert hoja.cell(2, 13).value == fila["fichado_min"]
    assert hoja.cell(2, 14).value == fila["pausa_min"]
    assert hoja.cell(2, 15).value == fila["diferencia_min"]
