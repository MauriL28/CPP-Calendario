from unittest.mock import patch

from app import create_app
from seguridad import emitir_token


class Cursor:
    def __init__(self):
        self.sql_mandos = ""
        self._fila = None
        self._filas = []

    def execute(self, sql, _params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": "d60"}
        elif texto.startswith("SELECT departamento_id FROM usuario"):
            self._fila = {"departamento_id": "d60"}
        elif texto.startswith("SELECT DISTINCT"):
            self._filas = [{"codigo": "60I"}, {"codigo": "05I"}]
        elif "usa_horario_habitual" in texto:
            self._filas = [
                fila("60I", "d60"),
                fila("05I", "d05"),
            ]
        elif "AS propio" in texto:
            self.sql_mandos = texto
            personas = [
                mando("60I", "Ana Ríos", "ana.rios", None, False, True),
                mando("05I", "Bea Ríos", "bea.rios", "101", True, False),
            ]
            if "AND u.activo" in texto:
                personas = [persona for persona in personas if persona["activo"]]
            self._filas = personas

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


def fila(delegacion, identificador):
    return {
        "delegacion": delegacion,
        "id": identificador,
        "codigo": "trafico",
        "nombre": "Tráfico",
        "orden": 1,
        "usa_horario_habitual": True,
        "seccion_id": None,
        "seccion": None,
    }


def mando(delegacion, nombre, login, numero_sap, activo, propio):
    return {
        "delegacion": delegacion,
        "departamento": "trafico",
        "nombre": nombre,
        "login": login,
        "numero_sap": numero_sap,
        "activo": activo,
        "propio": propio,
    }


def token(app, rol):
    with app.app_context():
        return emitir_token("93c2848c-a3e7-406f-b4aa-63a70c353b31", rol, ["60I", "05I"], "Admin", None)


def lista(cliente, acceso):
    return cliente.get("/departamentos", headers={"Authorization": f"Bearer {acceso}"})


def test_el_mando_enlazado_sale_en_el_otro_departamento_y_el_inactivo_tambien():
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    with patch("rutas.departamentos.cursor", return_value=Conexion(cursor)):
        respuesta = lista(cliente, token(app, "admin"))

    assert respuesta.status_code == 200
    assert "mando_departamento" in cursor.sql_mandos
    assert "AND u.activo" not in cursor.sql_mandos
    sedes = {item["delegacion"]: item for item in respuesta.get_json()}
    assert sedes["05I"]["mandos"] == [
        {
            "nombre": "Bea Ríos",
            "login": "bea.rios",
            "numero_sap": "101",
            "activo": True,
            "propio": False,
        }
    ]
    assert sedes["60I"]["mandos"] == [
        {
            "nombre": "Ana Ríos",
            "login": "ana.rios",
            "numero_sap": None,
            "activo": False,
            "propio": True,
        }
    ]
    assert sedes["60I"]["trabajadores"] == []


def test_un_mando_no_ve_los_inactivos():
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    with patch("rutas.departamentos.cursor", return_value=Conexion(cursor)):
        respuesta = lista(cliente, token(app, "mando"))

    assert respuesta.status_code == 200
    assert "AND u.activo" in cursor.sql_mandos
    sedes = {item["delegacion"]: item for item in respuesta.get_json()}
    assert sedes["60I"]["mandos"] == []
    assert sedes["05I"]["mandos"][0]["login"] == "bea.rios"
