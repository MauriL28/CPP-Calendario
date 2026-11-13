from datetime import time
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token
from tests.test_ficha_horas import TRABAJADOR, cursor_de_enero, pedir

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
MENSAJE = "El coste tiene que ser un número mayor o igual que cero, con hasta 4 decimales"


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


class CursorAlta:
    def __init__(self):
        self.costes = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT 1 FROM departamento"):
            self._fila = (1,)
        elif "usa_horario_habitual" in texto:
            self._fila = {"usa_horario_habitual": False}
        elif texto.startswith("SELECT 1 FROM usuario"):
            self._fila = None
        elif texto.startswith("INSERT INTO usuario"):
            self.costes.append(params[-1])
            self._fila = {
                "id": "trab-1",
                "nombre": params[0],
                "login": params[1],
                "rol": "trabajador",
                "grupo": params[3],
                "vacaciones": params[5],
                "horas_contrato": params[6],
                "numero_sap": params[7],
                "seccion_id": params[8],
            }
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorEdicion:
    def __init__(self, grupo):
        self.grupo = grupo
        self.updates = []
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
        elif texto.startswith("SELECT id, departamento_id, grupo"):
            self._fila = {
                "id": "trab-1",
                "departamento_id": DEPARTAMENTO,
                "grupo": self.grupo,
            }
        elif texto.startswith("SELECT id, rol, departamento_id"):
            self._fila = {
                "id": "trab-1",
                "rol": "trabajador",
                "departamento_id": DEPARTAMENTO,
                "grupo": self.grupo,
            }
        elif texto.startswith("UPDATE usuario SET"):
            self.updates.append((texto, params))
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorLista:
    def execute(self, sql, _params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif "mando_departamento" in texto:
            self._filas = []
        elif texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT DISTINCT"):
            self._filas = [{"codigo": "60I"}]
        elif "usa_horario_habitual" in texto:
            self._filas = [
                {
                    "delegacion": "60I",
                    "id": DEPARTAMENTO,
                    "codigo": "trafico",
                    "nombre": "Tráfico",
                    "orden": 1,
                    "usa_horario_habitual": True,
                    "seccion_id": None,
                    "seccion": None,
                }
            ]
        elif "AS propio" in texto:
            self._filas = []
        elif "tarifas_ett" in texto:
            self._filas = [
                {
                    "delegacion": "60I",
                    "departamento": "trafico",
                    "nombre": "Nerea Lago",
                    "login": "nerea.lago",
                    "grupo": "ETT",
                    "horas_contrato": 40,
                    "horas_convenio": None,
                    "pausa_minutos": 0,
                    "vacaciones": 22,
                    "numero_sap": None,
                    "seccion_id": None,
                    "tarifas_ett": Decimal("10.5000"),
                    "pausa_habitual": time(14, 0),
                }
            ]
        elif "FROM turno" in texto or "horario_dia" in texto:
            self._filas = []
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorMios:
    def __init__(self):
        self.sql = []

    def execute(self, sql, _params=None):
        texto = " ".join(sql.split())
        self.sql.append(texto)
        self._fila = None
        self._filas = []
        if "grupo, activo" in texto:
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": "ETT",
                "activo": True,
            }

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


def token(app, rol, usuario_id="admin-1"):
    with app.app_context():
        return emitir_token(usuario_id, rol, ["60I"], "Nerea", "Tráfico")


def cuerpo(**extra):
    datos = {
        "nombre": "Nerea Lago",
        "login": "nerea.lago",
        "clave": "secreta",
        "grupo": "ETT",
        "vacaciones": 22,
        "horas_contrato": 40,
        "departamento_id": DEPARTAMENTO,
    }
    datos.update(extra)
    return datos


def alta(cliente, acceso, datos, cursor):
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        return cliente.post(
            "/trabajadores",
            json=datos,
            headers={"Authorization": f"Bearer {acceso}"},
        )


def test_alta_ett_guarda_el_coste():
    app = create_app()
    cursor = CursorAlta()
    respuesta = alta(
        app.test_client(),
        token(app, "admin"),
        cuerpo(coste="10,1234"),
        cursor,
    )

    assert respuesta.status_code == 201
    assert respuesta.get_json()["coste"] == 10.1234
    assert cursor.costes == [10.1234]


def test_alta_ett_sin_coste_guarda_null():
    app = create_app()
    cursor = CursorAlta()
    respuesta = alta(app.test_client(), token(app, "admin"), cuerpo(), cursor)

    assert respuesta.status_code == 201
    assert respuesta.get_json()["coste"] is None
    assert cursor.costes == [None]


def test_alta_stef_descarta_el_coste():
    app = create_app()
    cursor = CursorAlta()
    respuesta = alta(
        app.test_client(),
        token(app, "admin"),
        cuerpo(grupo="STEF", coste=15),
        cursor,
    )

    assert respuesta.status_code == 201
    assert respuesta.get_json()["grupo"] == "STEF"
    assert respuesta.get_json()["coste"] is None
    assert cursor.costes == [None]


def test_coste_negativo_da_400():
    app = create_app()
    cursor = CursorAlta()
    respuesta = alta(
        app.test_client(),
        token(app, "admin"),
        cuerpo(coste=-1),
        cursor,
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == MENSAJE
    assert cursor.costes == []


def test_coste_no_numerico_da_400():
    app = create_app()
    cursor = CursorAlta()
    respuesta = alta(
        app.test_client(),
        token(app, "admin"),
        cuerpo(coste="doce"),
        cursor,
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == MENSAJE
    assert cursor.costes == []


def test_el_mando_pone_y_quita_el_coste():
    app = create_app()
    cursor = CursorEdicion("ETT")
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'mando', MANDO)}"}
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        puesto = cliente.put(
            "/trabajadores/nerea.lago",
            json={"coste": 12.5},
            headers=cabecera,
        )
        quitado = cliente.put(
            "/trabajadores/nerea.lago",
            json={"coste": None},
            headers=cabecera,
        )

    assert puesto.status_code == 200
    assert puesto.get_json()["coste"] == 12.5
    assert quitado.status_code == 200
    assert quitado.get_json()["coste"] is None
    assert cursor.updates[0] == (
        "UPDATE usuario SET tarifas_ett = %s WHERE id = %s",
        (12.5, "trab-1"),
    )
    assert cursor.updates[1][1] == (None, "trab-1")


def test_el_admin_deja_el_coste_en_null_si_el_grupo_pasa_a_stef():
    app = create_app()
    cursor = CursorEdicion("ETT")
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/nerea.lago",
            json={"grupo": "STEF", "coste": 9},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["grupo"] == "STEF"
    assert respuesta.get_json()["coste"] is None
    texto, params = cursor.updates[0]
    assert texto == "UPDATE usuario SET grupo = %s, tarifas_ett = %s WHERE id = %s"
    assert params == ("STEF", None, "trab-1")


def test_el_listado_de_admin_y_mando_incluye_el_coste():
    app = create_app()
    cliente = app.test_client()
    for rol, usuario in (("admin", "admin-1"), ("mando", MANDO)):
        cursor = CursorLista()
        with patch("rutas.departamentos.cursor", return_value=Conexion(cursor)):
            respuesta = cliente.get(
                "/departamentos",
                headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
            )
        assert respuesta.status_code == 200
        assert respuesta.get_json()[0]["trabajadores"][0]["coste"] == 10.5


def test_el_trabajador_no_recibe_el_coste():
    ficha = pedir(cursor_de_enero(), "trabajador", TRABAJADOR)
    assert ficha.status_code == 200
    assert "coste" not in ficha.get_json()

    app = create_app()
    cursor = CursorLista()
    with patch("rutas.departamentos.cursor", return_value=Conexion(cursor)):
        departamentos = app.test_client().get(
            "/departamentos",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )
    assert departamentos.status_code == 200
    assert "coste" not in departamentos.get_json()[0]["trabajadores"][0]

    cursor_mios = CursorMios()
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor_mios)):
        mios = app.test_client().get(
            "/turnos/mios?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )
    assert mios.status_code == 200
    assert "coste" not in mios.get_json()["trabajadores"][0]
    assert all("tarifas_ett" not in texto for texto in cursor_mios.sql)
