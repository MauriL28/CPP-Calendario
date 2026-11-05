from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "f655754e-7511-41bf-8188-f11ef2ed928f"
SECCION = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class Cursor:
    def __init__(self, usuarios, secciones=None):
        self.usuarios = usuarios
        self.secciones = secciones or set()
        self.updates = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if "rol = 'trabajador'" in texto:
            persona = next((usuario for usuario in self.usuarios if usuario["login"] == params[0]), None)
            if persona and persona["rol"] == "trabajador":
                self._fila = {
                    "id": persona["id"],
                    "departamento_id": persona["departamento_id"],
                }
            return
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
            return
        if texto.startswith("SELECT departamento_id"):
            self._filas = []
            return
        if texto.startswith("SELECT 1 FROM seccion WHERE departamento_id"):
            self._fila = (1,) if any(depto == str(params[0]) for _, depto in self.secciones) else None
            return
        if "FROM seccion" in texto and "id = %s" in texto:
            clave = (str(params[0]), str(params[1]))
            self._fila = (1,) if clave in self.secciones else None
            return
        if "IS DISTINCT FROM" in texto:
            ocupado = any(
                usuario["numero_sap"] == params[0] and usuario["id"] != params[1]
                for usuario in self.usuarios
            )
            self._fila = (1,) if ocupado else None
            return
        if texto.startswith("UPDATE usuario SET"):
            self.updates.append((texto, params))
            persona = next(usuario for usuario in self.usuarios if usuario["id"] == params[-1])
            if "clave = crypt(%s, gen_salt('bf'))" in texto:
                persona["clave"] = params[0]
            return
        if "u.clave = crypt(%s, u.clave)" in texto:
            persona = next((usuario for usuario in self.usuarios if usuario["login"] == params[0]), None)
            if persona and persona["activo"] and persona["clave"] == params[1]:
                self._fila = {
                    "id": persona["id"],
                    "nombre": persona["nombre"],
                    "rol": persona["rol"],
                    "departamento": "Tráfico",
                    "delegacion": "60I",
                }
            return
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


def token(app, rol, usuario_id="admin-1"):
    with app.app_context():
        return emitir_token(usuario_id, rol, ["60I"], "Mando", "Tráfico")


def trabajador(login="nerea.lago", departamento_id=DEPARTAMENTO, numero_sap="200", nombre="Nerea Lago"):
    return {
        "id": f"id-{login}",
        "login": login,
        "rol": "trabajador",
        "nombre": nombre,
        "numero_sap": numero_sap,
        "departamento_id": departamento_id,
        "clave": "vieja",
        "activo": True,
    }


def test_el_mando_edita_nombre_grupo_y_seccion():
    app = create_app()
    cursor = Cursor([trabajador()], secciones={(SECCION, DEPARTAMENTO)})
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/trabajadores/nerea.lago",
            json={"nombre": " Nerea Nueva ", "grupo": "ETT", "seccion_id": SECCION},
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "login": "nerea.lago",
        "rol": "trabajador",
        "nombre": "Nerea Nueva",
        "grupo": "ETT",
        "seccion_id": SECCION,
    }
    assert len(cursor.updates) == 1
    texto, params = cursor.updates[0]
    assert texto == "UPDATE usuario SET nombre = %s, grupo = %s, seccion_id = %s WHERE id = %s"
    assert params[0] == "Nerea Nueva"
    assert params[1] == "ETT"
    assert str(params[2]) == SECCION


def test_sap_duplicado_da_409_y_no_cambia_nada():
    app = create_app()
    cursor = Cursor(
        [
            trabajador(nombre="Nerea Lago", numero_sap="200"),
            trabajador(login="bea.rios", nombre="Bea Ríos", numero_sap="300"),
        ]
    )
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/trabajadores/nerea.lago",
            json={"nombre": "Nerea Nueva", "numero_sap": "300"},
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == "Ese número de personal ya está asignado a otra persona"
    assert cursor.updates == []
    assert cursor.usuarios[0]["nombre"] == "Nerea Lago"
    assert cursor.usuarios[0]["numero_sap"] == "200"


def test_trabajador_de_otro_departamento_da_404():
    app = create_app()
    cursor = Cursor([trabajador(departamento_id=OTRO)])
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/trabajadores/nerea.lago",
            json={"nombre": "Otra"},
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )

    assert respuesta.status_code == 404
    assert cursor.updates == []


def test_login_o_rol_dan_400():
    app = create_app()
    cursor = Cursor([trabajador()])
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'mando', MANDO)}"}
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        por_login = cliente.put(
            "/trabajadores/nerea.lago",
            json={"login": "otro"},
            headers=cabecera,
        )
        por_rol = cliente.put(
            "/trabajadores/nerea.lago",
            json={"rol": "admin"},
            headers=cabecera,
        )

    assert por_login.status_code == 400
    assert por_login.get_json()["error"] == "Campo no permitido"
    assert por_rol.status_code == 400
    assert por_rol.get_json()["error"] == "Campo no permitido"
    assert cursor.updates == []


def test_trabajador_o_admin_reciben_403():
    app = create_app()
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor") as cursor:
        trabajador_respuesta = cliente.put(
            "/trabajadores/nerea.lago",
            json={"nombre": "Otra"},
            headers={"Authorization": f"Bearer {token(app, 'trabajador')}"},
        )
        admin_respuesta = cliente.put(
            "/trabajadores/nerea.lago",
            json={"nombre": "Otra"},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert trabajador_respuesta.status_code == 403
    assert admin_respuesta.status_code == 403
    cursor.assert_not_called()


def test_la_clave_nueva_permite_entrar():
    app = create_app()
    cursor = Cursor([trabajador()])
    conexion = Conexion(cursor)
    cliente = app.test_client()
    with (
        patch("rutas.trabajadores.cursor", return_value=conexion),
        patch("rutas.auth.cursor", return_value=conexion),
    ):
        cambio = cliente.put(
            "/trabajadores/nerea.lago",
            json={"clave": "nueva"},
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )
        entrada = cliente.post("/login", json={"login": "nerea.lago", "clave": "nueva"})

    assert cambio.status_code == 200
    texto, params = cursor.updates[0]
    assert "clave = crypt(%s, gen_salt('bf'))" in texto
    assert params == ("nueva", "id-nerea.lago")
    assert entrada.status_code == 200


def test_el_mando_guarda_y_borra_horas_convenio():
    app = create_app()
    cursor = Cursor([trabajador()])
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'mando', MANDO)}"}
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        guardado = cliente.put(
            "/trabajadores/nerea.lago",
            json={"horas_convenio": 1600},
            headers=cabecera,
        )
        borrado = cliente.put(
            "/trabajadores/nerea.lago",
            json={"horas_convenio": ""},
            headers=cabecera,
        )
        negativo = cliente.put(
            "/trabajadores/nerea.lago",
            json={"horas_convenio": -1},
            headers=cabecera,
        )

    assert guardado.status_code == 200
    assert guardado.get_json()["horas_convenio"] == 1600.0
    assert cursor.updates[0][1] == (1600.0, "id-nerea.lago")
    assert borrado.status_code == 200
    assert borrado.get_json()["horas_convenio"] is None
    assert cursor.updates[1][1] == (None, "id-nerea.lago")
    assert negativo.status_code == 400
    assert len(cursor.updates) == 2
