from datetime import datetime
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
INEXISTENTE = "00000000-0000-0000-0000-000000000000"
LUNES = "2026-11-02"


class Cursor:
    def __init__(self, existe=True):
        self.existe = existe
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]} if self.existe else None
        elif "rol = 'mando'" in texto and texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "login": "nerea.lago",
                    "grupo": "STEF",
                    "activo": True,
                    "seccion": None,
                }
            ]
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
        return emitir_token(usuario, rol, ["60I"], "Ana", "Tráfico")


def pedir(cliente, app, ruta, rol, usuario, existe=True):
    with patch("rutas.turnos.cursor", return_value=Conexion(Cursor(existe))):
        return cliente.get(
            ruta,
            headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
        )


def test_admin_lee_el_cuadrante_de_un_departamento():
    app = create_app()
    cliente = app.test_client()
    admin = pedir(
        cliente,
        app,
        f"/turnos?desde={LUNES}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
    )
    mando = pedir(cliente, app, f"/turnos?desde={LUNES}", "mando", MANDO)
    assert admin.status_code == 200
    assert mando.status_code == 200
    assert admin.get_json() == mando.get_json()
    assert admin.get_json()["desde"] == LUNES
    assert len(admin.get_json()["dias"]) == 7
    assert admin.get_json()["trabajadores"][0]["login"] == "nerea.lago"


def test_admin_lee_el_mes_igual_que_el_mando():
    app = create_app()
    cliente = app.test_client()
    ruta_admin = f"/turnos/mes?anio=2026&mes=11&departamento_id={DEPARTAMENTO}"
    admin = pedir(cliente, app, ruta_admin, "admin", ADMIN)
    mando = pedir(cliente, app, "/turnos/mes?anio=2026&mes=11", "mando", MANDO)
    assert admin.status_code == 200
    assert admin.get_json() == mando.get_json()


def test_admin_sin_departamento_recibe_400():
    app = create_app()
    respuesta = pedir(app.test_client(), app, f"/turnos?desde={LUNES}", "admin", ADMIN)
    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Faltan datos"


def test_admin_con_departamento_inexistente_recibe_404():
    app = create_app()
    respuesta = pedir(
        app.test_client(),
        app,
        f"/turnos?desde={LUNES}&departamento_id={INEXISTENTE}",
        "admin",
        ADMIN,
        existe=False,
    )
    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "No se ha encontrado el departamento"


def test_admin_no_escribe_ni_exporta():
    app = create_app()
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'admin', ADMIN)}"}
    put = cliente.put("/turnos", json={"login": "nerea.lago", "fecha": LUNES}, headers=cabecera)
    exportar = cliente.get(f"/turnos/exportar?desde={LUNES}", headers=cabecera)
    assert put.status_code == 403
    assert exportar.status_code == 403


def test_trabajador_no_lee_el_cuadrante():
    app = create_app()
    respuesta = pedir(
        app.test_client(),
        app,
        f"/turnos?desde={LUNES}&departamento_id={DEPARTAMENTO}",
        "trabajador",
        TRABAJADOR,
    )
    assert respuesta.status_code == 403
