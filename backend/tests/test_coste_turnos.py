from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
LUNES = "2026-11-02"


class Cursor:
    def __init__(self, grupo, tarifas_ett):
        self.grupo = grupo
        self.tarifas_ett = tarifas_ett
        self.sql = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self.sql.append(texto)
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]}
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "login": "nerea.lago",
                    "grupo": self.grupo,
                    "activo": True,
                    "seccion": None,
                    "tarifas_ett": self.tarifas_ett,
                }
            ]
        elif "grupo, activo" in texto:
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": self.grupo,
                "activo": True,
            }
        elif "FROM turno" in texto or "FROM horario_version" in texto or "FROM festivo" in texto:
            self._filas = []
        elif "usa_horario_habitual" in texto:
            self._filas = []
        elif "FROM ajuste" in texto:
            self._filas = []
        elif "FROM empresa" in texto:
            self._fila = {
                "noche_inicio": datetime.strptime("22:00", "%H:%M").time(),
                "noche_fin": datetime.strptime("06:00", "%H:%M").time(),
            }
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

    def __exit__(self, *_args):
        return False


def token(app, rol, usuario):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Nerea", "Tráfico")


def coste_de(grupo, tarifas_ett, ruta):
    app = create_app()
    cursor = Cursor(grupo, tarifas_ett)
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            ruta,
            headers={"Authorization": f"Bearer {token(app, 'admin', ADMIN)}"},
        )
    assert respuesta.status_code == 200
    return respuesta.get_json()["trabajadores"][0]["coste"]


def test_un_ett_con_coste_sale_como_numero_en_la_semana_y_el_mes():
    semana = f"/turnos?desde={LUNES}&departamento_id={DEPARTAMENTO}"
    mes = f"/turnos/mes?anio=2026&mes=11&departamento_id={DEPARTAMENTO}"
    for ruta in (semana, mes):
        coste = coste_de("ETT", Decimal("12.5000"), ruta)
        assert coste == 12.5
        assert type(coste) is float


def test_un_ett_sin_coste_sale_null():
    ruta = f"/turnos?desde={LUNES}&departamento_id={DEPARTAMENTO}"
    assert coste_de("ETT", None, ruta) is None


def test_un_stef_sale_con_coste_null():
    ruta = f"/turnos/mes?anio=2026&mes=11&departamento_id={DEPARTAMENTO}"
    assert coste_de("STEF", Decimal("12.5000"), ruta) is None


def test_turnos_mios_no_trae_coste():
    app = create_app()
    cursor = Cursor("ETT", Decimal("12.5000"))
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            f"/turnos/mios?desde={LUNES}",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )
    assert respuesta.status_code == 200
    assert "coste" not in respuesta.get_json()["trabajadores"][0]
    assert all("tarifas_ett" not in texto for texto in cursor.sql)
