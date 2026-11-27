from datetime import date
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "00000000-0000-0000-0000-000000000099"
LUNES = date(2026, 11, 23)
MIERCOLES = "2026-11-25"


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


class Cursor:
    def __init__(self, seguimiento=True, propio=DEPARTAMENTO):
        self.seguimiento = seguimiento
        self.propio = propio
        self.filas = {}
        self.autor = None
        self._fila = None

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]} if str(params[0]) == DEPARTAMENTO else None
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": self.propio}
        elif texto.startswith("SELECT departamento_id FROM mando_departamento"):
            self._fila = None
        elif texto.startswith("SELECT departamento_id"):
            self._fila = {"departamento_id": self.propio}
        elif texto.startswith("SELECT usa_seguimiento"):
            self._fila = {"usa_seguimiento": self.seguimiento}
        elif texto.startswith("SELECT toneladas"):
            self._fila = self._completa(self.filas.get((str(params[0]), params[1])))
        elif texto.startswith("UPDATE seguimiento_semana"):
            clave = (str(params[1]), params[2])
            fila = self.filas.get(clave)
            if fila is not None and "detalle_pales = NULL" in texto:
                fila["pales"] = None
                fila["detalle_pales"] = None
                fila["fila_base_pales"] = None
            elif fila is not None:
                fila["toneladas"] = None
                fila["detalle"] = None
                fila["fila_base"] = None
        elif texto.startswith("DELETE FROM seguimiento_semana"):
            clave = (str(params[0]), params[1])
            fila = self.filas.get(clave)
            if "toneladas IS NULL" not in texto or (
                fila is not None and fila.get("toneladas") is None and fila.get("pales") is None
            ):
                self.filas.pop(clave, None)
        elif texto.startswith("INSERT INTO seguimiento_semana"):
            clave = (str(params[0]), params[1])
            previo = self._completa(self.filas.get(clave)) or self._vacia()
            detalle = params[3].obj if params[3] is not None and hasattr(params[3], "obj") else params[3]
            if "detalle_pales" in texto:
                previo["pales"] = params[2]
                previo["detalle_pales"] = detalle
                previo["fila_base_pales"] = params[4]
            else:
                previo["toneladas"] = params[2]
                previo["detalle"] = detalle
                previo["fila_base"] = params[4]
            self.filas[clave] = previo
            self.autor = params[5]
        else:
            raise AssertionError(texto)

    def _vacia(self):
        return {
            "toneladas": None,
            "detalle": None,
            "fila_base": None,
            "pales": None,
            "detalle_pales": None,
            "fila_base_pales": None,
        }

    def _completa(self, fila):
        if fila is None:
            return None
        return {**self._vacia(), **fila}

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return []


def token(app, rol, usuario):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Ana", "Tráfico")


def pedir(metodo, ruta, rol, usuario, cursor, json=None):
    app = create_app()
    with patch("rutas.seguimiento.cursor", return_value=Conexion(cursor)):
        return getattr(app.test_client(), metodo)(
            ruta,
            json=json,
            headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
        )


def test_la_lectura_vacia_devuelve_toneladas_null():
    respuesta = pedir(
        "get",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        Cursor(),
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {
        "semana_inicio": "2026-11-23",
        "toneladas": None,
        "detalle": None,
        "fila_base": None,
        "pales": None,
        "detalle_pales": None,
        "fila_base_pales": None,
    }


def test_guardar_y_releer():
    cursor = Cursor()
    guardado = pedir(
        "put",
        "/seguimiento",
        "mando",
        MANDO,
        cursor,
        {"semana": LUNES.isoformat(), "toneladas": 12.5},
    )
    leido = pedir(
        "get",
        f"/seguimiento?semana={LUNES.isoformat()}",
        "mando",
        MANDO,
        cursor,
    )
    assert guardado.status_code == 200
    assert guardado.get_json() == {"semana_inicio": "2026-11-23", "toneladas": 12.5}
    assert leido.get_json()["toneladas"] == 12.5
    assert cursor.autor == MANDO


def test_una_fecha_a_mitad_de_semana_cae_en_el_lunes():
    cursor = Cursor()
    pedir(
        "put",
        "/seguimiento",
        "admin",
        ADMIN,
        cursor,
        {"semana": MIERCOLES, "toneladas": 3, "departamento_id": DEPARTAMENTO},
    )
    respuesta = pedir(
        "get",
        f"/seguimiento?semana={MIERCOLES}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        cursor,
    )
    assert respuesta.status_code == 200
    assert respuesta.get_json()["semana_inicio"] == "2026-11-23"
    assert respuesta.get_json()["toneladas"] == 3


def test_toneladas_no_validas_dan_400():
    cursor = Cursor()
    for toneladas in (-1, 1.234, "abc", True):
        respuesta = pedir(
            "put",
            "/seguimiento",
            "admin",
            ADMIN,
            cursor,
            {"semana": LUNES.isoformat(), "toneladas": toneladas, "departamento_id": DEPARTAMENTO},
        )
        assert respuesta.status_code == 400


def test_el_mando_no_escribe_en_otro_departamento():
    respuesta = pedir(
        "put",
        "/seguimiento",
        "mando",
        MANDO,
        Cursor(),
        {"semana": LUNES.isoformat(), "toneladas": 1, "departamento_id": OTRO},
    )
    assert respuesta.status_code == 404


def test_el_admin_necesita_departamento_y_con_el_lee():
    cursor = Cursor()
    sin_dato = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "admin", ADMIN, cursor)
    con_dato = pedir(
        "get",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        cursor,
    )
    assert sin_dato.status_code == 400
    assert con_dato.status_code == 200


def test_sin_la_marca_responde_404():
    cursor = Cursor(seguimiento=False)
    lectura = pedir(
        "get",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        cursor,
    )
    escritura = pedir(
        "put",
        "/seguimiento",
        "admin",
        ADMIN,
        cursor,
        {"semana": LUNES.isoformat(), "toneladas": 1, "departamento_id": DEPARTAMENTO},
    )
    assert lectura.status_code == 404
    assert escritura.status_code == 404


DETALLE = {
    "filas": [
        {
            "nombre": "Prévision 2026",
            "total": 1126870,
            "dias": [13777, 143718, 213675, 166712, 168205, 420783],
        }
    ]
}


def _guardar(cursor, cuerpo):
    return pedir(
        "put",
        "/seguimiento",
        "mando",
        MANDO,
        cursor,
        {"semana": LUNES.isoformat(), **cuerpo},
    )


def test_guardar_y_releer_el_detalle():
    cursor = Cursor()
    guardado = _guardar(
        cursor,
        {"toneladas": 1126.87, "detalle": DETALLE, "fila_base": "Prévision 2026"},
    )
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor)
    assert guardado.status_code == 200
    assert leido.status_code == 200
    assert leido.get_json()["toneladas"] == 1126.87
    assert leido.get_json()["detalle"] == DETALLE
    assert leido.get_json()["fila_base"] == "Prévision 2026"


def test_el_detalle_invalido_da_400():
    cursor = Cursor()
    corta = {"filas": [{"nombre": "Prévision 2026", "total": 10, "dias": [1, 2, 3, 4, 5]}]}
    negativa = {"filas": [{"nombre": "Prévision 2026", "total": -1, "dias": [0, 0, 0, 0, 0, 0]}]}
    dia_negativo = {"filas": [{"nombre": "Prévision 2026", "total": 0, "dias": [0, 0, -1, 0, 0, 0]}]}
    muchas = {
        "filas": [
            {"nombre": f"Fila {indice}", "total": 0, "dias": [0, 0, 0, 0, 0, 0]}
            for indice in range(11)
        ]
    }
    for cuerpo in (
        {"toneladas": 1, "detalle": corta, "fila_base": "Prévision 2026"},
        {"toneladas": 1, "detalle": negativa},
        {"toneladas": 1, "detalle": dia_negativo},
        {"toneladas": 1, "detalle": muchas},
        {"toneladas": 1, "detalle": DETALLE, "fila_base": "No existe"},
    ):
        assert _guardar(cursor, cuerpo).status_code == 400


def test_un_put_sin_detalle_no_borra_el_que_hay():
    cursor = Cursor()
    primero = _guardar(
        cursor,
        {"toneladas": 1126.87, "detalle": DETALLE, "fila_base": "Prévision 2026"},
    )
    segundo = _guardar(cursor, {"toneladas": 10})
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor)
    assert primero.status_code == 200
    assert segundo.status_code == 200
    assert leido.get_json()["toneladas"] == 10
    assert leido.get_json()["detalle"] == DETALLE
    assert leido.get_json()["fila_base"] == "Prévision 2026"


def test_borrar_y_releer():
    cursor = Cursor()
    _guardar(
        cursor,
        {"toneladas": 1126.87, "detalle": DETALLE, "fila_base": "Prévision 2026"},
    )
    borrado = pedir("delete", f"/seguimiento?semana={MIERCOLES}", "mando", MANDO, cursor)
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor)
    assert borrado.status_code == 204
    assert leido.get_json()["toneladas"] is None
    assert leido.get_json()["detalle"] is None
    assert leido.get_json()["fila_base"] is None


def test_borrar_lo_que_no_existe_responde_igual():
    respuesta = pedir(
        "delete",
        f"/seguimiento?semana={LUNES.isoformat()}",
        "mando",
        MANDO,
        Cursor(),
    )
    assert respuesta.status_code == 204


def test_el_mando_no_borra_en_otro_departamento():
    respuesta = pedir(
        "delete",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={OTRO}",
        "mando",
        MANDO,
        Cursor(),
    )
    assert respuesta.status_code == 404


def test_borrar_sin_la_marca_responde_404():
    respuesta = pedir(
        "delete",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}",
        "admin",
        ADMIN,
        Cursor(seguimiento=False),
    )
    assert respuesta.status_code == 404


DETALLE_PALES = {
    "filas": [
        {
            "nombre": "Pales",
            "total": 40,
            "dias": [5, 5, 10, 5, 5, 10],
        }
    ]
}


def test_guardar_pales_y_releer():
    cursor = Cursor()
    guardado = _guardar(
        cursor,
        {"magnitud": "pales", "pales": 4.5, "detalle": DETALLE_PALES, "fila_base": "Pales"},
    )
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor)
    assert guardado.status_code == 200
    assert guardado.get_json() == {"semana_inicio": "2026-11-23", "pales": 4.5}
    cuerpo = leido.get_json()
    assert cuerpo["pales"] == 4.5
    assert cuerpo["detalle_pales"] == DETALLE_PALES
    assert cuerpo["fila_base_pales"] == "Pales"
    assert cuerpo["toneladas"] is None
    assert cuerpo["detalle"] is None
    assert cuerpo["fila_base"] is None


def test_toneladas_y_pales_de_la_misma_semana_no_se_pisan():
    cursor = Cursor()
    _guardar(
        cursor,
        {"toneladas": 10, "detalle": DETALLE, "fila_base": "Prévision 2026"},
    )
    _guardar(
        cursor,
        {"magnitud": "pales", "pales": 3.5, "detalle": DETALLE_PALES, "fila_base": "Pales"},
    )
    _guardar(cursor, {"toneladas": 11})
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor).get_json()
    assert leido["toneladas"] == 11
    assert leido["detalle"] == DETALLE
    assert leido["fila_base"] == "Prévision 2026"
    assert leido["pales"] == 3.5
    assert leido["detalle_pales"] == DETALLE_PALES
    assert leido["fila_base_pales"] == "Pales"
    _guardar(cursor, {"magnitud": "pales", "pales": 4})
    despues = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor).get_json()
    assert despues["toneladas"] == 11
    assert despues["detalle"] == DETALLE
    assert despues["pales"] == 4
    assert despues["detalle_pales"] == DETALLE_PALES


def test_pales_no_validos_dan_400():
    cursor = Cursor()
    corta = {"filas": [{"nombre": "Pales", "total": 10, "dias": [1, 2, 3, 4, 5]}]}
    for cuerpo in (
        {"magnitud": "pales", "pales": -1},
        {"magnitud": "pales", "pales": 1, "detalle": corta, "fila_base": "Pales"},
        {"magnitud": "pales", "pales": 1, "detalle": DETALLE_PALES, "fila_base": "No existe"},
        {"magnitud": "cajas", "pales": 1},
    ):
        assert _guardar(cursor, cuerpo).status_code == 400


def test_borrar_una_magnitud_deja_la_otra():
    cursor = Cursor()
    _guardar(cursor, {"toneladas": 10, "detalle": DETALLE, "fila_base": "Prévision 2026"})
    _guardar(
        cursor,
        {"magnitud": "pales", "pales": 3.5, "detalle": DETALLE_PALES, "fila_base": "Pales"},
    )
    borrado = pedir(
        "delete",
        f"/seguimiento?semana={LUNES.isoformat()}&magnitud=pales",
        "mando",
        MANDO,
        cursor,
    )
    leido = pedir("get", f"/seguimiento?semana={LUNES.isoformat()}", "mando", MANDO, cursor).get_json()
    assert borrado.status_code == 204
    assert leido["toneladas"] == 10
    assert leido["detalle"] == DETALLE
    assert leido["pales"] is None
    assert leido["detalle_pales"] is None
    assert leido["fila_base_pales"] is None


def test_el_trabajador_recibe_403():
    respuesta = pedir(
        "get",
        f"/seguimiento?semana={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}",
        "trabajador",
        TRABAJADOR,
        Cursor(),
    )
    assert respuesta.status_code == 403
