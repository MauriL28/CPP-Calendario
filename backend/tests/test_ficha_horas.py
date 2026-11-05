from datetime import date, time
from unittest.mock import patch

from app import create_app
from horas import convenio_anual, horas_computables
from seguridad import emitir_token

TRABAJADOR = "11111111-1111-1111-1111-111111111111"
MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
DEPARTAMENTO = "22222222-2222-2222-2222-222222222222"
OTRO = "33333333-3333-3333-3333-333333333333"


def test_horas_computables_de_turno_ft_baja_y_vacaciones():
    assert horas_computables(None, 8) == 8
    assert horas_computables("FT", 6) == 6
    assert horas_computables("B", 0) == 7.5
    assert horas_computables("V", 0) == 0


def test_convenio_informado_y_vacio():
    assert convenio_anual(1600, 37.5) == 1600
    assert convenio_anual(None, 37.5) == 1770
    assert convenio_anual(None, 18.75) == 885


class Cursor:
    def __init__(self, convenio=1600, contrato=37.5, departamento=DEPARTAMENTO, existe=True):
        self.convenio = convenio
        self.contrato = contrato
        self.departamento = departamento
        self.existe = existe
        self.turnos = {}
        self.ajustes = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT u.id, u.nombre"):
            if not self.existe:
                return
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "grupo": "STEF",
                "departamento_id": self.departamento,
                "horas_convenio": self.convenio,
                "horas_contrato": self.contrato,
                "departamento": "Tráfico",
            }
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT fecha, ausencia"):
            self._filas = [
                {"fecha": fecha, **fila}
                for fecha, fila in self.turnos.items()
            ]
        elif texto.startswith("SELECT v.usuario_id"):
            self._filas = []
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
        elif texto.startswith("SELECT u.id, d.usa_horario_habitual"):
            self._filas = [{"id": TRABAJADOR, "usa_horario_habitual": False}]
        elif texto.startswith("SELECT fecha, horas"):
            self._filas = list(self.ajustes)
        elif texto.startswith("SELECT fecha FROM festivo"):
            self._filas = []
        elif texto.startswith("SELECT COUNT"):
            self._fila = {
                "usados": sum(1 for fila in self.turnos.values() if fila["ausencia"] == "V")
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

    def __exit__(self, tipo, *_args):
        return False


def fila(ausencia, horas, inicio=None, fin=None):
    return {
        "ausencia": ausencia,
        "hora_inicio": inicio,
        "hora_fin": fin,
        "horas_planificadas": horas,
        "horas_nocturnas": 0,
    }


def cursor_de_enero():
    cursor = Cursor()
    cursor.turnos[date(2026, 1, 5)] = fila(None, 8, time(8, 0), time(16, 0))
    cursor.turnos[date(2026, 1, 6)] = fila("FT", 6, time(6, 0), time(12, 0))
    cursor.turnos[date(2026, 1, 7)] = fila("B", 0)
    cursor.turnos[date(2026, 1, 8)] = fila("V", 0)
    cursor.ajustes.append(
        {"fecha": date(2026, 1, 15), "horas": -1.5, "motivo": "corrección"}
    )
    return cursor


def pedir(cursor, rol, identidad):
    app = create_app()
    with app.app_context():
        token = emitir_token(identidad, rol, ["60I"], "Nerea", "Tráfico")
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        return app.test_client().get(
            "/trabajadores/nerea.lago/ficha?anio=2026",
            headers={"Authorization": f"Bearer {token}"},
        )


def test_la_ficha_suma_turno_ft_baja_vacaciones_y_ajuste():
    cursor = cursor_de_enero()
    respuesta = pedir(cursor, "mando", MANDO)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["horas_por_mes"][0] == 8
    assert cuerpo["horas_realizadas_por_mes"][0] == 20
    assert cuerpo["horas_realizadas_por_mes"][1:] == [0] * 11
    assert cuerpo["horas_realizadas"] == 20
    assert cuerpo["convenio_anual"] == 1600
    assert cuerpo["saldo"] == -1580
    assert cuerpo["ausencias"]["V"] == 1

    cursor.convenio = None
    cuerpo = pedir(cursor, "mando", MANDO).get_json()
    assert cuerpo["convenio_anual"] == 1770
    assert cuerpo["saldo"] == round(20 - 1770, 2)


def test_el_admin_recibe_el_saldo_de_cualquier_trabajador():
    respuesta = pedir(cursor_de_enero(), "admin", ADMIN)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["horas_realizadas"] == 20
    assert cuerpo["convenio_anual"] == 1600
    assert cuerpo["saldo"] == -1580
    assert cuerpo["horas_realizadas_por_mes"][0] == 20


def test_el_admin_no_encuentra_un_login_inexistente():
    respuesta = pedir(Cursor(existe=False), "admin", ADMIN)
    assert respuesta.status_code == 404


def test_el_mando_de_otro_departamento_no_ve_la_ficha():
    respuesta = pedir(Cursor(departamento=OTRO), "mando", MANDO)
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "Ese trabajador no es de tu departamento"


def test_el_trabajador_no_recibe_las_horas_realizadas():
    respuesta = pedir(cursor_de_enero(), "trabajador", TRABAJADOR)
    assert respuesta.status_code == 200
    cuerpo = respuesta.get_json()
    assert cuerpo["horas_por_mes"][0] == 8
    assert "horas_realizadas" not in cuerpo
    assert "horas_realizadas_por_mes" not in cuerpo
    assert "convenio_anual" not in cuerpo
    assert "saldo" not in cuerpo
