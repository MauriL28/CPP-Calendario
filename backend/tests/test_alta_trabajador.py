from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"


class Cursor:
    def __init__(self, departamentos, mando=None):
        self.departamentos = {str(identificador) for identificador in departamentos}
        self.mando = mando
        self.insertados = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT 1 FROM departamento"):
            self._fila = (1,) if str(params[0]) in self.departamentos else None
        elif texto.startswith("SELECT rol, departamento_id"):
            if self.mando and self.mando["id"] == str(params[0]):
                self._fila = self.mando
        elif texto.startswith("SELECT departamento_id"):
            extras = self.mando["extra"] if self.mando else []
            self._filas = [{"departamento_id": extra} for extra in extras]
        elif texto.startswith("SELECT 1 FROM usuario"):
            self._fila = None
        elif texto.startswith("INSERT INTO usuario"):
            self.insertados.append({"login": params[1], "departamento_id": str(params[4])})
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
        elif texto.startswith("INSERT INTO horario"):
            return
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


def token(app, rol, usuario_id="admin-1"):
    with app.app_context():
        return emitir_token(usuario_id, rol, ["60I"], "Admin", None)


def cuerpo(departamento_id=DEPARTAMENTO, incluir_departamento=True):
    datos = {
        "nombre": "Nerea Lago",
        "login": "nerea.lago",
        "clave": "secreta",
        "grupo": "STEF",
        "vacaciones": 22,
        "horas_contrato": 40,
        "horario_dias": [{"dia_semana": 0, "hora_inicio": "08:00", "hora_fin": "16:00"}],
    }
    if incluir_departamento:
        datos["departamento_id"] = departamento_id
    return datos


def test_un_admin_crea_un_trabajador_con_departamento():
    app = create_app()
    cursor = Cursor([DEPARTAMENTO])
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.post(
            "/trabajadores",
            json=cuerpo(),
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 201
    assert respuesta.get_json()["login"] == "nerea.lago"
    assert cursor.insertados == [{"login": "nerea.lago", "departamento_id": DEPARTAMENTO}]


def test_un_admin_sin_departamento_recibe_400():
    app = create_app()
    cursor = Cursor([DEPARTAMENTO])
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.post(
            "/trabajadores",
            json=cuerpo(incluir_departamento=False),
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Faltan datos"
    assert cursor.insertados == []


def test_un_mando_sigue_creando_en_su_departamento():
    app = create_app()
    cursor = Cursor(
        [DEPARTAMENTO],
        mando={"id": MANDO, "rol": "mando", "departamento_id": DEPARTAMENTO, "extra": []},
    )
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.post(
            "/trabajadores",
            json=cuerpo(),
            headers={"Authorization": f"Bearer {token(app, 'mando', MANDO)}"},
        )

    assert respuesta.status_code == 201
    assert cursor.insertados == [{"login": "nerea.lago", "departamento_id": DEPARTAMENTO}]


def test_un_trabajador_no_puede_crear():
    app = create_app()
    cliente = app.test_client()
    with patch("rutas.trabajadores.cursor") as cursor:
        respuesta = cliente.post(
            "/trabajadores",
            json=cuerpo(),
            headers={"Authorization": f"Bearer {token(app, 'trabajador')}"},
        )

    assert respuesta.status_code == 403
    cursor.assert_not_called()


class CursorLogin:
    def __init__(self, usuario):
        self.usuario = usuario
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if "FROM usuario" not in texto:
            self._filas = [{"codigo": "60I"}]
            return
        if "u.activo" not in texto:
            raise AssertionError(texto)
        if params[1] != self.usuario["clave"] or not self.usuario["activo"]:
            return
        self._fila = self.usuario

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


def test_un_usuario_inactivo_no_puede_entrar():
    app = create_app()
    cliente = app.test_client()
    inactivo = CursorLogin(
        {
            "id": "user-1",
            "nombre": "Ana Ríos",
            "rol": "trabajador",
            "departamento": "Tráfico",
            "delegacion": "60I",
            "clave": "secreta",
            "activo": False,
        }
    )
    with patch("rutas.auth.cursor", return_value=Conexion(inactivo)):
        respuesta = cliente.post("/login", json={"login": "ana.rios", "clave": "secreta"})

    assert respuesta.status_code == 401
    assert respuesta.get_json()["error"] == "Credenciales incorrectas"
