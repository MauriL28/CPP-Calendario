from datetime import date, time
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "00000000-0000-0000-0000-000000000099"


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


class Cursor:
    def __init__(self, trabajadores, turnos=None, habitual=None, festivos=None, propio=DEPARTAMENTO):
        self.trabajadores = trabajadores
        self.turnos = turnos or []
        self.habitual = habitual or []
        self.festivos = festivos or []
        self.propio = propio
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]} if str(params[0]) == DEPARTAMENTO else None
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": self.propio}
        elif texto.startswith("SELECT departamento_id FROM mando_departamento"):
            self._filas = []
        elif texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": self.propio}
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = list(self.trabajadores)
        elif "FROM turno" in texto:
            self._filas = list(self.turnos)
        elif "FROM horario_version" in texto:
            self._filas = list(self.habitual)
        elif "FROM festivo" in texto:
            self._filas = list(self.festivos)
        elif "usa_horario_habitual" in texto:
            self._filas = [
                {
                    "id": trabajador["id"],
                    "usa_horario_habitual": True,
                    "pausa_minutos": 0,
                }
                for trabajador in self.trabajadores
            ]
        elif "FROM empresa" in texto:
            self._fila = {
                "noche_inicio": time(22, 0),
                "noche_fin": time(6, 0),
            }
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


def token(app, rol, usuario):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Ana", "Tráfico")


def pedir(ruta, rol, usuario, cursor):
    app = create_app()
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        return app.test_client().get(
            ruta,
            headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
        )


def trabajador(identificador=TRABAJADOR, activo=True):
    return {
        "id": identificador,
        "nombre": "Nerea Lago",
        "login": "nerea.lago",
        "grupo": "STEF",
        "activo": activo,
        "seccion": "Muelle",
    }


def horario(identificador=TRABAJADOR):
    return {
        "usuario_id": identificador,
        "desde": date(2020, 1, 1),
        "dia_semana": 0,
        "horario_inicio": time(8, 0),
        "horario_fin": time(16, 0),
    }


def turno(fecha, ausencia, inicio=None, fin=None, horas=0):
    return {
        "usuario_id": TRABAJADOR,
        "fecha": fecha,
        "ausencia": ausencia,
        "hora_inicio": inicio,
        "hora_fin": fin,
        "horas_planificadas": horas,
        "horas_nocturnas": 0,
    }


def test_el_anio_devuelve_un_valor_corto_por_dia():
    cursor = Cursor(
        [trabajador()],
        turnos=[
            turno(date(2026, 1, 7), "V"),
            turno(date(2026, 1, 8), "ST", time(6, 0), time(14, 0), 8),
        ],
        habitual=[horario()],
        festivos=[{"fecha": date(2026, 1, 6), "nombre": "Reyes"}],
    )
    respuesta = pedir(f"/turnos/anio?anio=2026&departamento_id={DEPARTAMENTO}", "admin", ADMIN, cursor)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["anio"] == 2026
    assert cuerpo["dias"][0] == "2026-01-01"
    assert cuerpo["dias"][-1] == "2026-12-31"
    assert len(cuerpo["dias"]) == 365
    assert cuerpo["festivos"] == {"2026-01-06": "Reyes"}
    persona = cuerpo["trabajadores"][0]
    assert persona["nombre"] == "Nerea Lago"
    assert persona["login"] == "nerea.lago"
    assert persona["grupo"] == "STEF"
    assert persona["seccion"] == "Muelle"
    assert set(persona) == {"nombre", "login", "grupo", "seccion", "dias"}
    assert len(persona["dias"]) == 365
    valores = dict(zip(cuerpo["dias"], persona["dias"]))
    assert valores["2026-01-02"] == ""
    assert valores["2026-01-04"] == "D"
    assert valores["2026-01-05"] == "08:00-16:00"
    assert valores["2026-01-06"] == "F"
    assert valores["2026-01-07"] == "V"
    assert valores["2026-01-08"] == "ST 06:00-14:00"


def test_admin_sin_departamento_recibe_400_y_con_el_recibe_200():
    cursor = Cursor([trabajador()])
    sin_dato = pedir("/turnos/anio?anio=2026", "admin", ADMIN, cursor)
    con_dato = pedir(
        f"/turnos/anio?anio=2026&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        cursor,
    )
    assert sin_dato.status_code == 400
    assert con_dato.status_code == 200


def test_el_mando_no_lee_otro_departamento():
    respuesta = pedir(
        f"/turnos/anio?anio=2026&departamento_id={OTRO}",
        "mando",
        MANDO,
        Cursor([trabajador()]),
    )
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "No se ha encontrado el departamento"


def test_el_trabajador_recibe_403():
    respuesta = pedir(
        f"/turnos/anio?anio=2026&departamento_id={DEPARTAMENTO}",
        "trabajador",
        TRABAJADOR,
        Cursor([trabajador()]),
    )
    assert respuesta.status_code == 403


def test_un_anio_fuera_de_rango_da_400():
    for anio in ("1999", "2101", "abc"):
        respuesta = pedir(
            f"/turnos/anio?anio={anio}&departamento_id={DEPARTAMENTO}",
            "admin",
            ADMIN,
            Cursor([trabajador()]),
        )
        assert respuesta.status_code == 400


def test_el_anio_bisiesto_tiene_366_dias():
    respuesta = pedir(
        f"/turnos/anio?anio=2024&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        Cursor([trabajador()]),
    )
    assert respuesta.status_code == 200
    dias = respuesta.get_json()["dias"]
    assert len(dias) == 366
    assert dias[0] == "2024-01-01"
    assert dias[-1] == "2024-12-31"
    assert "2024-02-29" in dias


def test_cuarenta_trabajadores_caben_en_la_respuesta():
    gente = []
    horarios = []
    for indice in range(40):
        identificador = f"trab-{indice}"
        gente.append(
            {
                "id": identificador,
                "nombre": f"Persona {indice}",
                "login": f"persona.{indice}",
                "grupo": "ETT" if indice % 2 else "STEF",
                "activo": True,
                "seccion": None,
            }
        )
        for dia_semana in range(5):
            horarios.append(
                {
                    "usuario_id": identificador,
                    "desde": date(2020, 1, 1),
                    "dia_semana": dia_semana,
                    "horario_inicio": time(8, 0),
                    "horario_fin": time(16, 0),
                }
            )
    respuesta = pedir(
        f"/turnos/anio?anio=2026&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        Cursor(gente, habitual=horarios),
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert len(cuerpo["trabajadores"]) == 40
    assert len(cuerpo["trabajadores"][0]["dias"]) == 365
