from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
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
        if texto.startswith("SELECT id, rol, departamento_id"):
            persona = next((usuario for usuario in self.usuarios if usuario["login"] == params[0]), None)
            if persona and persona["rol"] in ("mando", "trabajador"):
                self._fila = {
                    "id": persona["id"],
                    "rol": persona["rol"],
                    "departamento_id": persona["departamento_id"],
                }
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


def token(app, rol):
    with app.app_context():
        return emitir_token("admin-1", rol, ["60I"], "Admin", None)


def test_un_admin_edita_nombre_y_sap_de_un_mando():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "mando-1",
                "login": "ana.rios",
                "rol": "mando",
                "nombre": "Ana Ríos",
                "numero_sap": "100",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            }
        ]
    )
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/ana.rios",
            json={"nombre": " Ana Nueva ", "numero_sap": "101"},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "login": "ana.rios",
        "rol": "mando",
        "nombre": "Ana Nueva",
        "numero_sap": "101",
    }
    assert len(cursor.updates) == 1
    texto, params = cursor.updates[0]
    assert texto == "UPDATE usuario SET nombre = %s, numero_sap = %s WHERE id = %s"
    assert params == ("Ana Nueva", "101", "mando-1")


def test_un_admin_edita_grupo_vacaciones_y_seccion_de_un_trabajador():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "trab-1",
                "login": "nerea.lago",
                "rol": "trabajador",
                "nombre": "Nerea Lago",
                "numero_sap": "200",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            }
        ],
        secciones={(SECCION, DEPARTAMENTO)},
    )
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/nerea.lago",
            json={"grupo": "ETT", "vacaciones": 18, "seccion_id": SECCION},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "login": "nerea.lago",
        "rol": "trabajador",
        "grupo": "ETT",
        "vacaciones": 18.0,
        "seccion_id": SECCION,
    }
    assert len(cursor.updates) == 1
    texto, params = cursor.updates[0]
    assert "grupo = %s" in texto
    assert "vacaciones = %s" in texto
    assert "seccion_id = %s" in texto
    assert params[0] == "ETT"
    assert params[1] == 18.0
    assert str(params[2]) == SECCION
    assert params[3] == "trab-1"


def test_el_admin_guarda_y_borra_horas_convenio():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "trab-1",
                "login": "nerea.lago",
                "rol": "trabajador",
                "nombre": "Nerea Lago",
                "numero_sap": "200",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            }
        ]
    )
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'admin')}"}
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        guardado = cliente.put(
            "/usuarios/nerea.lago",
            json={"horas_convenio": 1600},
            headers=cabecera,
        )
        borrado = cliente.put(
            "/usuarios/nerea.lago",
            json={"horas_convenio": None},
            headers=cabecera,
        )
        negativo = cliente.put(
            "/usuarios/nerea.lago",
            json={"horas_convenio": -1},
            headers=cabecera,
        )

    assert guardado.status_code == 200
    assert guardado.get_json()["horas_convenio"] == 1600.0
    assert cursor.updates[0][1] == (1600.0, "trab-1")
    assert "horas_convenio = %s" in cursor.updates[0][0]
    assert borrado.status_code == 200
    assert borrado.get_json()["horas_convenio"] is None
    assert cursor.updates[1][1] == (None, "trab-1")
    assert negativo.status_code == 400
    assert len(cursor.updates) == 2


def test_grupo_en_un_mando_da_400_y_no_guarda():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "mando-1",
                "login": "ana.rios",
                "rol": "mando",
                "nombre": "Ana Ríos",
                "numero_sap": "100",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            }
        ]
    )
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/ana.rios",
            json={"grupo": "ETT", "nombre": "Otra"},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Campo no permitido"
    assert cursor.updates == []
    assert cursor.usuarios[0]["nombre"] == "Ana Ríos"


def test_sap_duplicado_da_409_y_no_cambia_nada():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "mando-1",
                "login": "ana.rios",
                "rol": "mando",
                "nombre": "Ana Ríos",
                "numero_sap": "100",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            },
            {
                "id": "mando-2",
                "login": "bea.rios",
                "rol": "mando",
                "nombre": "Bea Ríos",
                "numero_sap": "200",
                "departamento_id": DEPARTAMENTO,
                "clave": "secreta",
                "activo": True,
            },
        ]
    )
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/ana.rios",
            json={"nombre": "Ana Nueva", "numero_sap": "200"},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 409
    assert respuesta.get_json()["error"] == "Ese número de personal ya está asignado a otra persona"
    assert cursor.updates == []
    assert cursor.usuarios[0]["nombre"] == "Ana Ríos"
    assert cursor.usuarios[0]["numero_sap"] == "100"


def test_la_clave_nueva_permite_entrar():
    app = create_app()
    cursor = Cursor(
        [
            {
                "id": "trab-1",
                "login": "nerea.lago",
                "rol": "trabajador",
                "nombre": "Nerea Lago",
                "numero_sap": "200",
                "departamento_id": DEPARTAMENTO,
                "clave": "vieja",
                "activo": True,
            }
        ]
    )
    conexion = Conexion(cursor)
    cliente = app.test_client()
    with (
        patch("rutas.usuarios.cursor", return_value=conexion),
        patch("rutas.auth.cursor", return_value=conexion),
    ):
        cambio = cliente.put(
            "/usuarios/nerea.lago",
            json={"clave": "nueva"},
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )
        entrada = cliente.post("/login", json={"login": "nerea.lago", "clave": "nueva"})

    assert cambio.status_code == 200
    texto, params = cursor.updates[0]
    assert "clave = crypt(%s, gen_salt('bf'))" in texto
    assert params == ("nueva", "trab-1")
    assert entrada.status_code == 200


def test_quien_no_es_admin_recibe_403():
    app = create_app()
    with patch("rutas.usuarios.cursor") as cursor:
        respuesta = app.test_client().put(
            "/usuarios/ana.rios",
            json={"nombre": "Ana"},
            headers={"Authorization": f"Bearer {token(app, 'mando')}"},
        )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["error"] == "No autorizado"
    cursor.assert_not_called()
