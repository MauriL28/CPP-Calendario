from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

TRAFICO_60 = "11111111-1111-1111-1111-111111111111"
TRAFICO_05 = "22222222-2222-2222-2222-222222222222"
DEPARTAMENTOS = {
    ("60I", "trafico"): TRAFICO_60,
    ("05I", "trafico"): TRAFICO_05,
}


class Cursor:
    """Departamento y mandos en memoria. No abre la base de desarrollo."""

    def __init__(self):
        self.usuarios = []
        self.inserts = 0
        self._fila = None

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        if "FROM departamento" in texto:
            identificador = DEPARTAMENTOS.get((params[0], params[1]))
            self._fila = {"id": identificador} if identificador else None
            return
        if "mando_departamento" in texto:
            departamento_id = params[0]
            hay = any(
                usuario["rol"] == "mando"
                and usuario["activo"]
                and (
                    usuario["departamento_id"] == departamento_id
                    or departamento_id in usuario["extra"]
                )
                for usuario in self.usuarios
            )
            self._fila = (1,) if hay else None
            return
        if "WHERE login" in texto:
            self._fila = (1,) if any(usuario["login"] == params[0] for usuario in self.usuarios) else None
            return
        if texto.startswith("INSERT INTO usuario"):
            self.inserts += 1
            self.usuarios.append(
                {
                    "login": params[1],
                    "rol": "mando",
                    "activo": True,
                    "departamento_id": params[3],
                    "extra": [],
                }
            )
            self._fila = {
                "nombre": params[0],
                "login": params[1],
                "rol": "mando",
                "numero_sap": params[4],
            }
            return
        raise AssertionError(texto)

    def fetchone(self):
        return self._fila


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


def token(app):
    with app.app_context():
        return emitir_token("93c2848c-a3e7-406f-b4aa-63a70c353b31", "admin", [], "Admin", None)


def alta(cliente, acceso, login, delegacion):
    return cliente.post(
        "/usuarios",
        json={
            "nombre": "Ana Ríos",
            "login": login,
            "clave": "secreta",
            "delegacion": delegacion,
            "departamento": "trafico",
        },
        headers={"Authorization": f"Bearer {acceso}"},
    )


def test_el_primer_mando_entra_el_segundo_no_y_la_otra_delegacion_si():
    app = create_app()
    cursor = Cursor()
    acceso = token(app)
    cliente = app.test_client()
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        primero = alta(cliente, acceso, "ana.rios", "60I")
        segundo = alta(cliente, acceso, "bea.rios", "60I")
        otra = alta(cliente, acceso, "cira.rios", "05I")

    assert primero.status_code == 201
    assert segundo.status_code == 409
    assert segundo.get_json()["error"] == "Este departamento ya tiene un mando en esta delegación"
    assert otra.status_code == 201
    assert cursor.inserts == 2
    assert [usuario["departamento_id"] for usuario in cursor.usuarios] == [TRAFICO_60, TRAFICO_05]
