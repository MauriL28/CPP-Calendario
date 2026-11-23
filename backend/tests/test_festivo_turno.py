from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from app import create_app
from seguridad import emitir_token

TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"


class Cursor:
    def __init__(self, festivo):
        self.festivo = festivo
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "grupo": "STEF",
                    "seccion": None,
                }
            ]
        elif "FROM turno" in texto or "FROM horario_version" in texto:
            self._filas = []
        elif "usa_horario_habitual" in texto:
            self._filas = [
                {"id": TRABAJADOR, "usa_horario_habitual": True, "pausa_minutos": 0}
            ]
        elif "FROM empresa" in texto:
            self._fila = {
                "noche_inicio": datetime.strptime("22:00", "%H:%M").time(),
                "noche_fin": datetime.strptime("06:00", "%H:%M").time(),
            }
        elif "FROM festivo" in texto:
            self._filas = [{"fecha": self.festivo, "nombre": "Navidad"}]
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


def test_turnos_departamento_marca_el_festivo_y_lo_resuelve_como_f():
    hoy = datetime.now(ZoneInfo("Europe/Madrid")).date()
    lunes = hoy - timedelta(days=hoy.weekday())
    app = create_app()
    with app.app_context():
        token = emitir_token(TRABAJADOR, "trabajador", ["60I"], "Nerea", "Tráfico")
    with patch("rutas.turnos.cursor", return_value=Conexion(Cursor(lunes))):
        respuesta = app.test_client().get(
            f"/turnos/departamento?desde={lunes.isoformat()}",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert respuesta.status_code == 200
    dia = next(
        item
        for item in respuesta.get_json()["trabajadores"][0]["dias"]
        if item["fecha"] == lunes.isoformat()
    )
    assert dia["festivo"] is True
    assert dia["nombre"] == "Navidad"
    assert dia["turno"] == {"ausencia": "F"}
