from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from tests.test_coste_ett import (
    DEPARTAMENTO,
    MANDO,
    CursorAlta,
    CursorEdicion,
    CursorLista,
    alta,
    cuerpo,
    token,
)
from tests.test_coste_turnos import ADMIN, LUNES, TRABAJADOR, Conexion

MENSAJE = "La tarifa nocturna tiene que ser un número mayor o igual que cero, con hasta 4 decimales"


class CursorAltaTarifa(CursorAlta):
    def __init__(self):
        super().__init__()
        self.tarifas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        if texto.startswith("INSERT INTO usuario"):
            self.tarifas.append((params or ())[-2])
        super().execute(sql, params)


class CursorTurnos:
    def __init__(self, grupo, tarifa):
        self.grupo = grupo
        self.tarifa = tarifa
        self.sql = []
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self.sql.append(texto)
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT id FROM departamento"):
            self._fila = {"id": params[0]}
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": TRABAJADOR,
                    "nombre": "Nerea Lago",
                    "login": "nerea.lago",
                    "grupo": self.grupo,
                    "activo": True,
                    "seccion": None,
                    "tarifas_ett": Decimal("12.5000"),
                    "tarifa_nocturna": self.tarifa,
                }
            ]
        elif "grupo, activo" in texto:
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": self.grupo,
                "activo": True,
            }
        elif "FROM turno" in texto or "FROM horario_version" in texto or "FROM festivo" in texto:
            self._filas = []
        elif "usa_horario_habitual" in texto or "FROM ajuste" in texto:
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


class CursorDepartamentos(CursorLista):
    def execute(self, sql, params=None):
        super().execute(sql, params)
        for fila in self._filas:
            if isinstance(fila, dict) and "tarifas_ett" in fila:
                fila["tarifa_nocturna"] = Decimal("2.2500")


def test_alta_ett_guarda_la_tarifa_nocturna():
    app = create_app()
    cursor = CursorAltaTarifa()
    respuesta = alta(app.test_client(), token(app, "admin"), cuerpo(tarifa_nocturna=3.25), cursor)
    assert respuesta.status_code == 201
    assert respuesta.get_json()["tarifa_nocturna"] == 3.25
    assert type(respuesta.get_json()["tarifa_nocturna"]) is float
    assert cursor.tarifas == [3.25]


def test_alta_ett_sin_tarifa_nocturna_queda_en_null():
    app = create_app()
    cursor = CursorAltaTarifa()
    respuesta = alta(app.test_client(), token(app, "admin"), cuerpo(), cursor)
    assert respuesta.status_code == 201
    assert respuesta.get_json()["tarifa_nocturna"] is None
    assert cursor.tarifas == [None]


def test_alta_stef_descarta_la_tarifa_nocturna():
    app = create_app()
    cursor = CursorAltaTarifa()
    respuesta = alta(
        app.test_client(),
        token(app, "admin"),
        cuerpo(grupo="STEF", tarifa_nocturna=4),
        cursor,
    )
    assert respuesta.status_code == 201
    assert respuesta.get_json()["tarifa_nocturna"] is None
    assert cursor.tarifas == [None]


def test_tarifa_nocturna_negativa_o_no_numerica_da_400():
    app = create_app()
    cliente = app.test_client()
    acceso = token(app, "admin")
    for valor in (-1, "abc"):
        cursor = CursorAltaTarifa()
        respuesta = alta(cliente, acceso, cuerpo(tarifa_nocturna=valor), cursor)
        assert respuesta.status_code == 400
        assert respuesta.get_json()["error"] == MENSAJE
        assert cursor.tarifas == []


def test_la_edicion_pone_y_quita_la_tarifa_nocturna():
    app = create_app()
    cursor = CursorEdicion("ETT")
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token(app, 'mando', MANDO)}"}
    with patch("rutas.trabajadores.cursor", return_value=Conexion(cursor)):
        puesto = cliente.put(
            "/trabajadores/nerea.lago",
            json={"tarifa_nocturna": 4.5},
            headers=cabecera,
        )
        quitado = cliente.put(
            "/trabajadores/nerea.lago",
            json={"tarifa_nocturna": None},
            headers=cabecera,
        )
    assert puesto.status_code == 200
    assert puesto.get_json()["tarifa_nocturna"] == 4.5
    assert quitado.status_code == 200
    assert quitado.get_json()["tarifa_nocturna"] is None
    assert cursor.updates[0] == (
        "UPDATE usuario SET tarifa_nocturna = %s WHERE id = %s",
        (4.5, "trab-1"),
    )
    assert cursor.updates[1][1] == (None, "trab-1")


def test_turnos_devuelve_la_tarifa_nocturna_y_mios_no():
    app = create_app()
    semana = f"/turnos?desde={LUNES}&departamento_id={DEPARTAMENTO}"
    mes = f"/turnos/mes?anio=2026&mes=11&departamento_id={DEPARTAMENTO}"
    for ruta in (semana, mes):
        cursor = CursorTurnos("ETT", Decimal("4.5000"))
        with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
            respuesta = app.test_client().get(
                ruta,
                headers={"Authorization": f"Bearer {token(app, 'admin', ADMIN)}"},
            )
        assert respuesta.status_code == 200
        tarifa = respuesta.get_json()["trabajadores"][0]["tarifa_nocturna"]
        assert tarifa == 4.5
        assert type(tarifa) is float

    cursor = CursorTurnos("ETT", Decimal("4.5000"))
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        mios = app.test_client().get(
            f"/turnos/mios?desde={LUNES}",
            headers={"Authorization": f"Bearer {token(app, 'trabajador', TRABAJADOR)}"},
        )
    assert mios.status_code == 200
    assert "tarifa_nocturna" not in mios.get_json()["trabajadores"][0]
    assert all("tarifa_nocturna" not in texto for texto in cursor.sql)


def test_departamentos_de_admin_incluye_la_tarifa_nocturna():
    app = create_app()
    cursor = CursorDepartamentos()
    with patch("rutas.departamentos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            "/departamentos",
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )
    assert respuesta.status_code == 200
    tarifa = respuesta.get_json()[0]["trabajadores"][0]["tarifa_nocturna"]
    assert tarifa == 2.25
    assert type(tarifa) is float
