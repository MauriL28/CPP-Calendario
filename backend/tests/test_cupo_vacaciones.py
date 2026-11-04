from datetime import date, time
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
TRABAJADOR = "trab-1"


class Cursor:
    def __init__(self, cupo=2):
        self.cupo = cupo
        self.turnos = {}
        self.inserts = 0
        self.escrituras = 0
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT departamento_id") and "rol = 'mando'" in texto:
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT id, departamento_id"):
            self._fila = {"id": TRABAJADOR, "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT id, nombre"):
            self._filas = [{"id": TRABAJADOR, "nombre": "Nerea Lago"}]
        elif texto.startswith("SELECT usuario_id, fecha"):
            inicio, fin = params[1], params[2]
            self._filas = [
                {"usuario_id": usuario, "fecha": fecha, "ausencia": ausencia}
                for (usuario, fecha), ausencia in self.turnos.items()
                if inicio <= fecha <= fin
            ]
        elif texto.startswith("SELECT vacaciones"):
            self._fila = {"vacaciones": self.cupo}
        elif texto.startswith("SELECT fecha"):
            pedidas = set(params[1])
            self._filas = [
                {"fecha": fecha}
                for (usuario, fecha), ausencia in self.turnos.items()
                if usuario == params[0] and ausencia == "V" and fecha in pedidas
            ]
        elif texto.startswith("SELECT COUNT"):
            inicio, fin = params[1], params[2]
            usados = sum(
                1
                for (usuario, fecha), ausencia in self.turnos.items()
                if usuario == params[0]
                and ausencia == "V"
                and inicio <= fecha <= fin
            )
            self._fila = {"usados": usados}
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
        elif texto.startswith("INSERT INTO turno"):
            self.inserts += 1
            self.escrituras += 1
            self.turnos[(params[0], params[1])] = params[2]
            self._fila = {
                "fecha": params[1],
                "ausencia": params[2],
                "hora_inicio": params[3],
                "hora_fin": params[4],
                "horas_planificadas": params[5],
                "horas_nocturnas": params[6],
            }
        elif texto.startswith("DELETE FROM turno"):
            self.escrituras += 1
        else:
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

    def __exit__(self, tipo, *_args):
        return False


def token(app, rol="mando"):
    with app.app_context():
        return emitir_token(MANDO, rol, ["60I"], "Mando", "Tráfico")


def pedir(metodo, ruta, cuerpo, cursor, rol="mando"):
    app = create_app()
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = getattr(app.test_client(), metodo)(
            ruta,
            json=cuerpo,
            headers={"Authorization": f"Bearer {token(app, rol)}"},
        )
    return respuesta


def test_asignar_hasta_el_cupo_exacto_funciona_y_uno_mas_no_cambia_nada():
    cursor = Cursor(cupo=2)
    fechas = ["2026-11-02", "2026-11-03"]
    respuesta = pedir(
        "put",
        "/turnos/varios",
        {"login": "nerea.lago", "fechas": fechas, "ausencia": "V"},
        cursor,
    )

    assert respuesta.status_code == 200
    assert cursor.inserts == 2

    antes = dict(cursor.turnos)
    respuesta = pedir(
        "put",
        "/turnos",
        {"login": "nerea.lago", "fecha": "2026-11-04", "ausencia": "V"},
        cursor,
    )

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == (
        "Solo quedan 0 días de vacaciones y intentas asignar 1"
    )
    assert cursor.turnos == antes
    assert cursor.inserts == 2


def test_varios_con_cinco_dias_y_tres_restantes_no_guarda_ninguno():
    cursor = Cursor(cupo=3)
    respuesta = pedir(
        "put",
        "/turnos/varios",
        {
            "login": "nerea.lago",
            "fechas": [
                "2026-11-02",
                "2026-11-03",
                "2026-11-04",
                "2026-11-05",
                "2026-11-06",
            ],
            "ausencia": "V",
        },
        cursor,
    )

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == (
        "Solo quedan 3 días de vacaciones y intentas asignar 5"
    )
    assert cursor.turnos == {}
    assert cursor.inserts == 0


def test_reescribir_un_v_existente_no_cuenta():
    cursor = Cursor(cupo=1)
    cuerpo = {"login": "nerea.lago", "fecha": "2026-11-02", "ausencia": "V"}
    assert pedir("put", "/turnos", cuerpo, cursor).status_code == 200
    respuesta = pedir("put", "/turnos", cuerpo, cursor)

    assert respuesta.status_code == 200
    assert cursor.turnos == {(TRABAJADOR, date(2026, 11, 2)): "V"}


def test_copiar_semana_con_exceso_nombra_al_trabajador_y_no_escribe():
    cursor = Cursor(cupo=2)
    cursor.turnos[(TRABAJADOR, date(2026, 11, 2))] = "V"
    cursor.turnos[(TRABAJADOR, date(2026, 11, 3))] = "V"
    antes = dict(cursor.turnos)

    respuesta = pedir("post", "/turnos/copiar-semana", {"desde": "2026-11-09"}, cursor)

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == (
        "Nerea Lago: Solo quedan 0 días de vacaciones y intentas asignar 2"
    )
    assert cursor.turnos == antes
    assert cursor.escrituras == 0


def test_un_mando_con_cupo_nulo_no_se_limita():
    cursor = Cursor(cupo=None)
    fechas = [f"2026-11-0{dia}" for dia in range(2, 9)]
    respuesta = pedir(
        "put",
        "/turnos/mandos/propio",
        {"fechas": fechas, "ausencia": "V"},
        cursor,
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["guardados"] == 7
    assert cursor.inserts == 7


def test_una_semana_que_cruza_de_ano_cuenta_cada_ano_por_separado():
    cursor = Cursor(cupo=2)
    exceso = ["2026-12-28", "2026-12-29", "2026-12-30", "2027-01-01"]
    respuesta = pedir(
        "put",
        "/turnos/varios",
        {"login": "nerea.lago", "fechas": exceso, "ausencia": "V"},
        cursor,
    )

    assert respuesta.status_code == 409
    assert "asignar 3" in respuesta.get_json()["error"]
    assert cursor.turnos == {}

    justas = ["2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02"]
    respuesta = pedir(
        "put",
        "/turnos/varios",
        {"login": "nerea.lago", "fechas": justas, "ausencia": "V"},
        cursor,
    )

    assert respuesta.status_code == 200
    assert cursor.inserts == 4
    assert {fecha.year for _, fecha in cursor.turnos} == {2026, 2027}
