from datetime import date, datetime
from unittest.mock import patch

import psycopg

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "f655754e-7511-41bf-8188-f11ef2ed928f"
LUNES = date(2026, 11, 2)


class Cursor:
    def __init__(self, departamento_id=DEPARTAMENTO, fallar_en=None):
        self.departamento_id = departamento_id
        self.fallar_en = fallar_en
        self.turnos = {}
        self.inserts = 0
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT id, departamento_id"):
            self._fila = {
                "id": "trab-1",
                "departamento_id": self.departamento_id,
            }
        elif texto.startswith("SELECT vacaciones"):
            self._fila = {"vacaciones": None}
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {
                "noche_inicio": datetime.strptime("22:00", "%H:%M").time(),
                "noche_fin": datetime.strptime("06:00", "%H:%M").time(),
            }
        elif texto.startswith("INSERT INTO turno"):
            self.inserts += 1
            if self.fallar_en is not None and self.inserts == self.fallar_en:
                raise psycopg.Error("fallo")
            fila = {
                "usuario_id": params[0],
                "fecha": params[1],
                "ausencia": params[2],
                "hora_inicio": params[3],
                "hora_fin": params[4],
                "horas_planificadas": params[5],
                "horas_nocturnas": params[6],
            }
            self.turnos[(params[0], params[1])] = fila
            self._fila = fila
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor
        self.confirmada = False

    def __enter__(self):
        return self.cursor

    def __exit__(self, tipo, *_args):
        self.confirmada = tipo is None
        if tipo is not None:
            self.cursor.turnos.clear()
        return False


def token(app):
    with app.app_context():
        return emitir_token(MANDO, "mando", ["60I"], "Mando", "Tráfico")


def pedir(cliente, app, cursor, cuerpo):
    conexion = Conexion(cursor)
    with patch("rutas.turnos.cursor", return_value=conexion):
        respuesta = cliente.put(
            "/turnos/varios",
            json=cuerpo,
            headers={"Authorization": f"Bearer {token(app)}"},
        )
    return respuesta, conexion


def test_guarda_varios_dias_con_horario():
    app = create_app()
    cursor = Cursor()
    fechas = ["2026-11-02", "2026-11-03", "2026-11-04"]
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": fechas,
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 3}
    assert conexion.confirmada
    assert len(cursor.turnos) == 3
    for texto in fechas:
        fila = cursor.turnos[("trab-1", date.fromisoformat(texto))]
        assert fila["ausencia"] is None
        assert fila["hora_inicio"].strftime("%H:%M") == "08:00"
        assert fila["hora_fin"].strftime("%H:%M") == "16:00"
        assert fila["horas_planificadas"] == 8


def test_guarda_varios_dias_con_ausencia():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-03"],
            "ausencia": "V",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 2}
    for fila in cursor.turnos.values():
        assert fila["ausencia"] == "V"
        assert fila["hora_inicio"] is None
        assert fila["hora_fin"] is None
        assert fila["horas_planificadas"] == 0
        assert fila["horas_nocturnas"] == 0


def test_sustituye_un_dia_que_ya_tenia_turno():
    app = create_app()
    cursor = Cursor()
    cursor.turnos[("trab-1", LUNES)] = {
        "ausencia": "L",
        "hora_inicio": None,
        "hora_fin": None,
    }
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02"],
            "hora_inicio": "09:00",
            "hora_fin": "17:00",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 1}
    fila = cursor.turnos[("trab-1", LUNES)]
    assert fila["ausencia"] is None
    assert fila["hora_inicio"].strftime("%H:%M") == "09:00"
    assert len(cursor.turnos) == 1


def test_fechas_de_dos_semanas_da_400():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-09"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 400
    assert cursor.inserts == 0
    assert cursor.turnos == {}


def test_trabajador_de_otro_departamento_da_404():
    app = create_app()
    cursor = Cursor(departamento_id=OTRO)
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "Ese trabajador no es de tu departamento"
    assert cursor.inserts == 0
    assert conexion.confirmada


def test_si_una_fecha_falla_no_se_guarda_ninguna():
    app = create_app()
    cursor = Cursor(fallar_en=2)
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-03"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 503
    assert not conexion.confirmada
    assert cursor.turnos == {}
