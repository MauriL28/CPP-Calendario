from datetime import time
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "f655754e-7511-41bf-8188-f11ef2ed928f"


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


def cabecera(app, rol, usuario):
    return {"Authorization": f"Bearer {token(app, rol, usuario)}"}


class CursorLista:
    def __init__(self):
        self.personas = [
            {
                "nombre": "Bea Ríos",
                "login": "bea.rios",
                "grupo": "STEF",
                "seccion": "Muelles",
                "activo": False,
                "departamento_id": DEPARTAMENTO,
            },
            {
                "nombre": "Ana Costa",
                "login": "ana.costa",
                "grupo": "ETT",
                "seccion": None,
                "activo": False,
                "departamento_id": DEPARTAMENTO,
            },
            {
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": "STEF",
                "seccion": "Muelles",
                "activo": True,
                "departamento_id": DEPARTAMENTO,
            },
            {
                "nombre": "Luis Orta",
                "login": "luis.orta",
                "grupo": "STEF",
                "seccion": None,
                "activo": False,
                "departamento_id": OTRO,
            },
        ]
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]} if params[0] == DEPARTAMENTO else None
            return
        if texto.startswith("SELECT departamento_id FROM usuario"):
            self._fila = {"departamento_id": DEPARTAMENTO}
            return
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
            return
        if texto.startswith("SELECT departamento_id FROM mando_departamento"):
            self._filas = []
            return
        if "FROM usuario u" in texto:
            personas = self.personas
            if "u.activo = false" in texto:
                personas = [persona for persona in personas if not persona["activo"]]
            if "u.departamento_id = %s" in texto:
                personas = [
                    persona
                    for persona in personas
                    if persona["departamento_id"] == params[0]
                ]
            if "ORDER BY u.nombre" in texto:
                personas = sorted(personas, key=lambda persona: persona["nombre"])
            self._filas = [
                {
                    "nombre": persona["nombre"],
                    "login": persona["login"],
                    "grupo": persona["grupo"],
                    "seccion": persona["seccion"],
                }
                for persona in personas
            ]
            return
        raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorAlta:
    def __init__(self, departamento_id=DEPARTAMENTO, activo=False, rol="trabajador"):
        self.persona = {
            "id": TRABAJADOR,
            "login": "nerea.lago",
            "rol": rol,
            "departamento_id": departamento_id,
            "activo": activo,
        }
        self.updates = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if "rol = 'trabajador'" in texto:
            if self.persona["rol"] == "trabajador" and self.persona["login"] == params[0]:
                self._fila = {
                    "id": self.persona["id"],
                    "departamento_id": self.persona["departamento_id"],
                    "grupo": "STEF",
                }
            return
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
            return
        if texto.startswith("SELECT departamento_id"):
            self._filas = []
            return
        if texto.startswith("UPDATE usuario SET activo = true"):
            self.updates.append(params)
            self.persona["activo"] = True
            return
        raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorFicha:
    """La ficha no filtra por activo: si la consulta lo exige, no hay fila."""

    def __init__(self):
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT u.id, u.nombre"):
            if "u.activo" in texto:
                return
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "grupo": "STEF",
                "departamento_id": DEPARTAMENTO,
                "horas_convenio": 1600,
                "horas_contrato": 37.5,
                "departamento": "Tráfico",
            }
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT fecha, ausencia"):
            self._filas = []
        elif texto.startswith("SELECT v.usuario_id"):
            self._filas = []
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
        elif texto.startswith("SELECT u.id, d.usa_horario_habitual"):
            self._filas = [{"id": TRABAJADOR, "usa_horario_habitual": False, "pausa_minutos": 0}]
        elif texto.startswith("SELECT fecha FROM festivo"):
            self._filas = []
        elif texto.startswith("SELECT fecha, horas"):
            self._filas = []
        elif texto.startswith("SELECT COUNT"):
            self._fila = {"usados": 0}
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


def test_mando_y_admin_ven_solo_los_inactivos_de_su_departamento():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorLista()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        mando = cliente.get(
            f"/trabajadores/inactivos?departamento_id={DEPARTAMENTO}",
            headers=cabecera(app, "mando", MANDO),
        )
        admin = cliente.get(
            f"/trabajadores/inactivos?departamento_id={DEPARTAMENTO}",
            headers=cabecera(app, "admin", ADMIN),
        )
        propio = cliente.get(
            "/trabajadores/inactivos",
            headers=cabecera(app, "mando", MANDO),
        )

    assert mando.status_code == 200
    assert admin.status_code == 200
    assert propio.status_code == 200
    logins = [persona["login"] for persona in mando.get_json()]
    assert logins == ["ana.costa", "bea.rios"]
    assert admin.get_json() == mando.get_json()
    assert propio.get_json() == mando.get_json()
    assert set(mando.get_json()[0]) == {"nombre", "login", "grupo", "seccion"}
    assert mando.get_json()[0]["seccion"] is None


def test_admin_sin_departamento_recibe_400():
    app = create_app()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(CursorLista())):
        respuesta = app.test_client().get(
            "/trabajadores/inactivos",
            headers=cabecera(app, "admin", ADMIN),
        )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Faltan datos"


def test_reactivar_pone_activo_y_repetir_sigue_en_200():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorAlta(activo=False)
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        alta = cliente.put(
            "/trabajadores/nerea.lago/alta",
            headers=cabecera(app, "mando", MANDO),
        )
        otra = cliente.put(
            "/trabajadores/nerea.lago/alta",
            headers=cabecera(app, "mando", MANDO),
        )

    assert alta.status_code == 200
    assert alta.get_json()["activo"] is True
    assert otra.status_code == 200
    assert otra.get_json()["activo"] is True
    assert cursor.persona["activo"] is True


def test_el_admin_reactiva_a_cualquier_trabajador():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorAlta(departamento_id=OTRO)
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.put(
            "/trabajadores/nerea.lago/alta",
            headers=cabecera(app, "admin", ADMIN),
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["activo"] is True
    assert cursor.persona["activo"] is True


def test_el_admin_no_reactiva_un_login_inexistente_ni_un_mando():
    app = create_app()
    cliente = app.test_client()
    inexistente = CursorAlta()
    mando = CursorAlta(rol="mando")
    with patch("rutas.trabajadores.cursor", return_value=Conexion(inexistente)):
        nadie = cliente.put(
            "/trabajadores/nadie/alta",
            headers=cabecera(app, "admin", ADMIN),
        )
    with patch("rutas.trabajadores.cursor", return_value=Conexion(mando)):
        otro_rol = cliente.put(
            "/trabajadores/nerea.lago/alta",
            headers=cabecera(app, "admin", ADMIN),
        )

    assert nadie.status_code == 404
    assert otro_rol.status_code == 404
    assert inexistente.updates == []
    assert mando.updates == []


def test_reactivar_uno_de_otro_departamento_da_404():
    app = create_app()
    cursor = CursorAlta(departamento_id=OTRO)
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/trabajadores/nerea.lago/alta",
            headers=cabecera(app, "mando", MANDO),
        )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "Ese trabajador no es de tu departamento"
    assert cursor.updates == []


def test_un_trabajador_no_lista_ni_reactiva():
    app = create_app()
    cliente = app.test_client()
    headers = cabecera(app, "trabajador", TRABAJADOR)
    with patch("rutas.trabajadores.cursor", return_value=Conexion(CursorLista())):
        lista = cliente.get("/trabajadores/inactivos", headers=headers)
        alta = cliente.put("/trabajadores/nerea.lago/alta", headers=headers)

    assert lista.status_code == 403
    assert alta.status_code == 403


def test_la_ficha_de_un_inactivo_responde_a_mando_y_admin():
    app = create_app()
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(CursorFicha())):
        mando = cliente.get(
            "/trabajadores/nerea.lago/ficha?anio=2026",
            headers=cabecera(app, "mando", MANDO),
        )
        admin = cliente.get(
            "/trabajadores/nerea.lago/ficha?anio=2026",
            headers=cabecera(app, "admin", ADMIN),
        )

    assert mando.status_code == 200
    assert admin.status_code == 200
    assert mando.get_json()["nombre"] == "Nerea Lago"
    assert admin.get_json()["nombre"] == "Nerea Lago"
