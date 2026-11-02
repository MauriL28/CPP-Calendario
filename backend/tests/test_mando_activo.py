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
    """Mandos y asignaciones en memoria. No abre la base de desarrollo."""

    def __init__(self):
        self.usuarios = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT d.id"):
            identificador = DEPARTAMENTOS.get((params[0], params[1]))
            self._fila = {"id": identificador} if identificador else None
        elif texto.startswith("SELECT id, departamento_id, activo"):
            self._fila = self._por_login(params[0])
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = self._por_id(params[0])
        elif texto.startswith("SELECT departamento_id"):
            usuario = self._por_id(params[0])
            extras = usuario["extra"] if usuario else []
            self._filas = [{"departamento_id": extra} for extra in extras]
        elif texto.startswith("SELECT 1") and "mando_departamento" in texto:
            self._fila = (1,) if self._hay_mando(str(params[0]), params[2]) else None
        elif texto.startswith("SELECT 1"):
            self._fila = (1,) if self._por_login(params[0]) else None
        elif texto.startswith("INSERT INTO usuario"):
            self.usuarios.append(
                {
                    "id": f"mando-{len(self.usuarios) + 1}",
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
        elif texto.startswith("INSERT INTO mando_departamento"):
            self._por_id(params[0])["extra"].append(str(params[1]))
        elif texto.startswith("UPDATE usuario SET activo"):
            self._por_id(params[1])["activo"] = params[0]
        elif texto.startswith("DELETE FROM mando_departamento"):
            usuario = self._por_id(params[0])
            buscado = str(params[1])
            if buscado in usuario["extra"]:
                usuario["extra"].remove(buscado)
                self._fila = {"departamento_id": buscado}
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas

    def _por_login(self, login):
        return next((usuario for usuario in self.usuarios if usuario["login"] == login), None)

    def _por_id(self, identificador):
        return next((usuario for usuario in self.usuarios if usuario["id"] == identificador), None)

    def _hay_mando(self, departamento_id, excluir_login):
        return any(
            usuario["rol"] == "mando"
            and usuario["activo"]
            and usuario["login"] != excluir_login
            and (
                str(usuario["departamento_id"]) == departamento_id
                or departamento_id in usuario["extra"]
            )
            for usuario in self.usuarios
        )


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


def token(app, rol):
    with app.app_context():
        return emitir_token("93c2848c-a3e7-406f-b4aa-63a70c353b31", rol, [], "Admin", None)


def crear(cliente, acceso, login, delegacion):
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


def test_desactivar_y_reactivar_y_el_conflicto_da_409():
    app = create_app()
    cursor = Cursor()
    acceso = token(app, "admin")
    cliente = app.test_client()
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        assert crear(cliente, acceso, "ana.rios", "60I").status_code == 201
        baja = cliente.put(
            "/usuarios/ana.rios/activo",
            json={"activo": False},
            headers={"Authorization": f"Bearer {acceso}"},
        )
        alta = cliente.put(
            "/usuarios/ana.rios/activo",
            json={"activo": True},
            headers={"Authorization": f"Bearer {acceso}"},
        )
        assert baja.status_code == 200
        assert baja.get_json()["activo"] is False
        assert alta.status_code == 200
        assert alta.get_json()["activo"] is True

        cliente.put(
            "/usuarios/ana.rios/activo",
            json={"activo": False},
            headers={"Authorization": f"Bearer {acceso}"},
        )
        assert crear(cliente, acceso, "bea.rios", "60I").status_code == 201
        conflicto = cliente.put(
            "/usuarios/ana.rios/activo",
            json={"activo": True},
            headers={"Authorization": f"Bearer {acceso}"},
        )

    assert conflicto.status_code == 409
    assert conflicto.get_json()["error"] == "Este departamento ya tiene un mando en esta delegación"
    ana = next(usuario for usuario in cursor.usuarios if usuario["login"] == "ana.rios")
    assert ana["activo"] is False


def test_asignar_la_otra_delegacion_y_un_segundo_mando_da_409():
    app = create_app()
    cursor = Cursor()
    acceso = token(app, "admin")
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {acceso}"}
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        assert crear(cliente, acceso, "ana.rios", "60I").status_code == 201
        asignada = cliente.post(
            "/usuarios/ana.rios/departamentos",
            json={"delegacion": "05I", "departamento": "trafico"},
            headers=cabecera,
        )
        repetida = cliente.post(
            "/usuarios/ana.rios/departamentos",
            json={"delegacion": "05I", "departamento": "trafico"},
            headers=cabecera,
        )
        segundo = crear(cliente, acceso, "cira.rios", "05I")

    assert asignada.status_code == 201
    assert repetida.status_code == 200
    assert segundo.status_code == 409
    assert segundo.get_json()["error"] == "Este departamento ya tiene un mando en esta delegación"
    ana = cursor.usuarios[0]
    assert ana["extra"] == [TRAFICO_05]


def test_quitar_la_asignacion_funciona_y_el_propio_da_400():
    app = create_app()
    cursor = Cursor()
    acceso = token(app, "admin")
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {acceso}"}
    with patch("rutas.usuarios.cursor", return_value=Conexion(cursor)):
        assert crear(cliente, acceso, "ana.rios", "60I").status_code == 201
        assert (
            cliente.post(
                "/usuarios/ana.rios/departamentos",
                json={"delegacion": "05I", "departamento": "trafico"},
                headers=cabecera,
            ).status_code
            == 201
        )
        quitada = cliente.delete(
            f"/usuarios/ana.rios/departamentos/{TRAFICO_05}",
            headers=cabecera,
        )
        propio = cliente.delete(
            f"/usuarios/ana.rios/departamentos/{TRAFICO_60}",
            headers=cabecera,
        )

    assert quitada.status_code == 200
    assert propio.status_code == 400
    assert propio.get_json()["error"] == "No se quita el departamento propio"
    assert cursor.usuarios[0]["extra"] == []
    assert cursor.usuarios[0]["departamento_id"] == TRAFICO_60


def test_quien_no_es_admin_recibe_403_en_los_tres():
    app = create_app()
    acceso = token(app, "mando")
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {acceso}"}
    with patch("rutas.usuarios.cursor") as cursor:
        activo = cliente.put(
            "/usuarios/ana.rios/activo",
            json={"activo": False},
            headers=cabecera,
        )
        asignar = cliente.post(
            "/usuarios/ana.rios/departamentos",
            json={"delegacion": "05I", "departamento": "trafico"},
            headers=cabecera,
        )
        quitar = cliente.delete(
            f"/usuarios/ana.rios/departamentos/{TRAFICO_05}",
            headers=cabecera,
        )

    assert activo.status_code == 403
    assert asignar.status_code == 403
    assert quitar.status_code == 403
    cursor.assert_not_called()
