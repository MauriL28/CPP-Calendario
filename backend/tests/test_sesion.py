from datetime import timedelta
from unittest.mock import patch

import psycopg
from flask_jwt_extended import create_access_token, decode_token

from app import create_app
from seguridad import emitir_token


USUARIO = "11111111-1111-1111-1111-111111111111"


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *args):
        return False


class CursorLogin:
    def __init__(self):
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        self._fila = None
        self._filas = []
        if "FROM usuario" in texto and params[1] == "secreta":
            self._fila = {
                "id": USUARIO,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "rol": "trabajador",
                "departamento": "Tráfico",
                "delegacion": "60I",
            }

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class CursorRevocados:
    def __init__(self, fallo=False):
        self.revocados = set()
        self.fallo = fallo
        self._fila = None

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        if texto.startswith("DELETE"):
            return
        if texto.startswith("INSERT"):
            if self.fallo:
                raise psycopg.Error("fallo")
            self.revocados.add(params[0])
            return
        if "FROM token_revocado" in texto:
            self._fila = {
                "revocado": params[0] in self.revocados,
                "activo": True,
                "rol": "admin",
            }

    def fetchone(self):
        return self._fila


class CursorFestivos:
    def execute(self, sql, params=None):
        return None

    def fetchall(self):
        return []

    def fetchone(self):
        return None


def cabecera(token):
    return {"Authorization": f"Bearer {token}"}


def test_el_login_incluye_el_login_y_dura_doce_horas(monkeypatch):
    monkeypatch.delenv("SESION_HORAS", raising=False)
    app = create_app()
    cliente = app.test_client()
    with patch("rutas.auth.cursor", return_value=Conexion(CursorLogin())):
        respuesta = cliente.post("/login", json={"login": "nerea.lago", "clave": "secreta"})

    assert respuesta.status_code == 200
    token = respuesta.get_json()["access_token"]
    with app.app_context():
        carga = decode_token(token)
    assert carga["login"] == "nerea.lago"
    assert carga["rol"] == "trabajador"
    assert carga["nombre"] == "Nerea Lago"
    assert carga["exp"] - carga["iat"] == 12 * 3600


def test_sesion_horas_cambia_la_caducidad(monkeypatch):
    monkeypatch.setenv("SESION_HORAS", "2")
    app = create_app()
    with app.app_context():
        token = emitir_token(USUARIO, "mando", ["60I"], "Ana", "Tráfico", "ana.rios")
        carga = decode_token(token)
    assert carga["login"] == "ana.rios"
    assert carga["exp"] - carga["iat"] == 2 * 3600


def test_un_token_valido_entra_y_uno_caducado_no():
    app = create_app()
    cliente = app.test_client()
    with app.app_context():
        valido = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
        caducado = create_access_token(
            identity=USUARIO,
            additional_claims={"rol": "admin", "login": "ana"},
            expires_delta=timedelta(seconds=-30),
        )
    with patch("rutas.festivos.cursor", return_value=Conexion(CursorFestivos())):
        bien = cliente.get("/festivos", headers=cabecera(valido))
        mal = cliente.get("/festivos", headers=cabecera(caducado))

    assert bien.status_code == 200
    assert mal.status_code == 401
    assert mal.get_json()["msg"] == "Token has expired"


def test_logout_revoca_el_token_y_no_se_puede_reutilizar():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorRevocados()
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    with (
        patch("seguridad.cursor", return_value=Conexion(cursor)),
        patch("rutas.festivos.cursor", return_value=Conexion(CursorFestivos())),
    ):
        salida = cliente.post("/logout", headers=cabecera(token))
        otra = cliente.get("/festivos", headers=cabecera(token))

    assert salida.status_code == 204
    assert len(cursor.revocados) == 1
    assert otra.status_code == 401
    assert otra.get_json()["msg"] == "Token has been revoked"


def test_si_logout_falla_el_token_sigue_valiendo():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorRevocados(fallo=True)
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    with (
        patch("seguridad.cursor", return_value=Conexion(cursor)),
        patch("rutas.festivos.cursor", return_value=Conexion(CursorFestivos())),
    ):
        salida = cliente.post("/logout", headers=cabecera(token))
        sigue = cliente.get("/festivos", headers=cabecera(token))

    assert salida.status_code == 503
    assert cursor.revocados == set()
    assert sigue.status_code == 200


class CursorEstadoUsuario:
    def __init__(self, existe=True, activo=True, rol="admin", revocado=False):
        self.existe = existe
        self.activo = activo
        self.rol = rol
        self.revocado = revocado
        self.consultas = []
        self._fila = None

    def execute(self, sql, params=None):
        self.consultas.append(" ".join(sql.split()))
        if not self.existe:
            self._fila = None
            return
        self._fila = {
            "revocado": self.revocado,
            "activo": self.activo,
            "rol": self.rol,
        }

    def fetchone(self):
        return self._fila


def _entrar(cliente, cursor, token):
    with (
        patch("seguridad.cursor", return_value=Conexion(cursor)),
        patch("rutas.festivos.cursor", return_value=Conexion(CursorFestivos())),
    ):
        return cliente.get("/festivos", headers=cabecera(token))


def test_un_usuario_activo_con_el_mismo_rol_entra():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorEstadoUsuario()
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    respuesta = _entrar(cliente, cursor, token)

    assert respuesta.status_code == 200
    assert len(cursor.consultas) == 1
    assert "token_revocado" in cursor.consultas[0]
    assert "FROM usuario" in cursor.consultas[0]


def test_un_usuario_desactivado_queda_revocado():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorEstadoUsuario(activo=False)
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    respuesta = _entrar(cliente, cursor, token)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["msg"] == "Token has been revoked"


def test_un_cambio_de_rol_revoca_el_token():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorEstadoUsuario(rol="trabajador")
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    respuesta = _entrar(cliente, cursor, token)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["msg"] == "Token has been revoked"


def test_un_usuario_inexistente_queda_revocado():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorEstadoUsuario(existe=False)
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    respuesta = _entrar(cliente, cursor, token)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["msg"] == "Token has been revoked"
    assert len(cursor.consultas) == 1


def test_un_jti_revocado_se_rechaza_aunque_el_usuario_siga_activo():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorEstadoUsuario(revocado=True)
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    respuesta = _entrar(cliente, cursor, token)

    assert respuesta.status_code == 401
    assert respuesta.get_json()["msg"] == "Token has been revoked"


def test_sin_base_de_datos_el_token_sigue_entrando(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app = create_app()
    cliente = app.test_client()
    with app.app_context():
        token = emitir_token(USUARIO, "admin", ["60I"], "Ana", None, "ana")
    with patch("rutas.festivos.cursor", return_value=Conexion(CursorFestivos())):
        respuesta = cliente.get("/festivos", headers=cabecera(token))

    assert respuesta.status_code == 200
