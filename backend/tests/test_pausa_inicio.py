from datetime import date, datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
LUNES = date(2026, 11, 2)


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


class Cursor:
    def __init__(self, pausa=30, pausa_habitual=None):
        self.pausa = pausa
        self.pausa_habitual = pausa_habitual
        self.turnos = {}
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id") and "rol = 'trabajador'" in texto:
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": DEPARTAMENTO}
            self._filas = []
        elif texto.startswith("SELECT id, nombre, login, grupo, activo"):
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": "STEF",
                "activo": True,
            }
        elif texto.startswith("SELECT id, departamento_id"):
            self._fila = {"id": TRABAJADOR, "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT u.id, u.nombre, u.grupo"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "grupo": "STEF",
                    "seccion": None,
                }
            ]
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "login": "nerea.lago",
                    "grupo": "STEF",
                    "activo": True,
                    "tarifas_ett": None,
                    "seccion": None,
                    "pausa_habitual": self.pausa_habitual,
                }
            ]
        elif texto.startswith("SELECT pausa_minutos") or "pausa_minutos" in texto and texto.startswith("SELECT u.id"):
            if texto.startswith("SELECT u.id"):
                self._filas = [
                    {
                        "id": TRABAJADOR,
                        "usa_horario_habitual": True,
                        "pausa_minutos": self.pausa,
                    }
                ]
            else:
                self._fila = {"pausa_minutos": self.pausa}
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
        elif texto.startswith("SELECT vacaciones"):
            self._fila = {"vacaciones": None}
        elif "FROM turno" in texto and texto.startswith("SELECT"):
            self._filas = [
                fila
                for fila in self.turnos.values()
                if params[1] <= fila["fecha"] <= params[2]
            ]
        elif "FROM horario_version" in texto:
            self._filas = [
                {
                    "usuario_id": TRABAJADOR,
                    "desde": date(2026, 1, 1),
                    "dia_semana": 1,
                    "horario_inicio": time(8, 0),
                    "horario_fin": time(16, 0),
                }
            ]
        elif "FROM festivo" in texto or "FROM ajuste" in texto:
            self._filas = []
        elif texto.startswith("INSERT INTO turno"):
            fila = {
                "usuario_id": params[0],
                "fecha": params[1],
                "ausencia": params[2],
                "hora_inicio": params[3],
                "hora_fin": params[4],
                "horas_planificadas": params[5],
                "horas_nocturnas": params[6],
                "pausa_inicio": params[7],
            }
            self.turnos[(params[0], params[1])] = fila
            self._fila = fila
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


def token(app, rol, usuario):
    with app.app_context():
        nombre = "Nerea" if rol == "trabajador" else "Mando"
        return emitir_token(usuario, rol, ["60I"], nombre, "Tráfico")


def put(cuerpo, pausa=30, rol="mando"):
    app = create_app()
    cursor = Cursor(pausa)
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/turnos",
            json=cuerpo,
            headers={"Authorization": f"Bearer {token(app, rol, MANDO if rol == 'mando' else TRABAJADOR)}"},
        )
    return respuesta, cursor


def horario(**extra):
    cuerpo = {
        "login": "nerea.lago",
        "fecha": "2026-11-02",
        "hora_inicio": "08:00",
        "hora_fin": "16:00",
    }
    cuerpo.update(extra)
    return cuerpo


def test_guarda_una_pausa_dentro_del_turno():
    respuesta, cursor = put(horario(pausa_inicio="12:00"))

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_inicio"] == "12:00"
    fila = cursor.turnos[(TRABAJADOR, LUNES)]
    assert fila["pausa_inicio"] == time(12, 0)
    assert fila["horas_planificadas"] == 7.5
    assert fila["horas_nocturnas"] == 0


def test_sin_pausa_inicio_queda_en_null():
    respuesta, cursor = put(horario())

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_inicio"] is None
    assert cursor.turnos[(TRABAJADOR, LUNES)]["pausa_inicio"] is None


def test_sin_pausa_asignada_da_400():
    respuesta, _cursor = put(horario(pausa_inicio="12:00"), pausa=0)

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "El trabajador no tiene pausa"


def test_una_ausencia_sin_horario_no_admite_pausa():
    respuesta, cursor = put(
        {
            "login": "nerea.lago",
            "fecha": "2026-11-02",
            "ausencia": "V",
            "pausa_inicio": "12:00",
        }
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "La pausa solo se indica con un horario"
    assert cursor.turnos == {}


def test_la_pausa_fuera_del_turno_da_400():
    respuesta, _cursor = put(horario(pausa_inicio="15:45"))

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "La pausa tiene que estar dentro del turno"


def test_un_turno_nocturno_acepta_la_pausa_de_madrugada():
    respuesta, cursor = put(
        horario(hora_inicio="22:00", hora_fin="06:00", pausa_inicio="01:00"),
        pausa=60,
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_inicio"] == "01:00"
    assert cursor.turnos[(TRABAJADOR, LUNES)]["horas_planificadas"] == 7


def test_st_admite_pausa():
    respuesta, _cursor = put(
        {
            "login": "nerea.lago",
            "fecha": "2026-11-02",
            "ausencia": "ST",
            "hora_inicio": "10:00",
            "hora_fin": "19:00",
            "pausa_inicio": "12:00",
        },
        pausa=60,
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_inicio"] == "12:00"
    assert respuesta.get_json()["horas_planificadas"] == 8


def test_la_lectura_devuelve_pausa_inicio_y_el_habitual_la_deja_vacia():
    app = create_app()
    cursor = Cursor()
    cursor.turnos[(TRABAJADOR, LUNES)] = {
        "usuario_id": TRABAJADOR,
        "fecha": LUNES,
        "ausencia": None,
        "hora_inicio": time(8, 0),
        "hora_fin": time(16, 0),
        "horas_planificadas": 7.5,
        "horas_nocturnas": 0,
        "pausa_inicio": time(12, 0),
    }
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            "/turnos?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )

    assert respuesta.status_code == 200
    dias = respuesta.get_json()["trabajadores"][0]["dias"]
    lunes = next(dia for dia in dias if dia["fecha"] == "2026-11-02")
    martes = next(dia for dia in dias if dia["fecha"] == "2026-11-03")
    assert lunes["turno"]["pausa_inicio"] == "12:00"
    assert martes["origen"] == "habitual"
    assert martes["turno"]["pausa_inicio"] is None


def test_el_companero_no_recibe_pausa_inicio():
    app = create_app()
    hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
    lunes = hoy - timedelta(days=hoy.weekday())
    cursor = Cursor()
    cursor.turnos[(TRABAJADOR, lunes)] = {
        "usuario_id": TRABAJADOR,
        "fecha": lunes,
        "ausencia": None,
        "hora_inicio": time(8, 0),
        "hora_fin": time(16, 0),
        "horas_planificadas": 7.5,
        "horas_nocturnas": 0,
        "pausa_inicio": time(12, 0),
    }
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            f"/turnos/departamento?desde={lunes.isoformat()}",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )

    assert respuesta.status_code == 200
    dia = next(
        item
        for item in respuesta.get_json()["trabajadores"][0]["dias"]
        if item["fecha"] == lunes.isoformat()
    )
    assert dia["turno"] == {"hora_inicio": "08:00", "hora_fin": "16:00"}
    assert "pausa_inicio" not in dia["turno"]


def test_el_cuadrante_trae_pausa_minutos_y_el_propio_no():
    app = create_app()
    cliente = app.test_client()
    cursor = Cursor(pausa=30)
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        semana = cliente.get(
            "/turnos?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )
        mensual = cliente.get(
            "/turnos/mes?anio=2026&mes=11",
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )
        mios = cliente.get(
            "/turnos/mios?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )

    assert semana.status_code == 200
    assert mensual.status_code == 200
    assert mios.status_code == 200
    assert semana.get_json()["trabajadores"][0]["pausa_minutos"] == 30
    assert mensual.get_json()["trabajadores"][0]["pausa_minutos"] == 30
    assert "pausa_minutos" not in mios.get_json()["trabajadores"][0]
