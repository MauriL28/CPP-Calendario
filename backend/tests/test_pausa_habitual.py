from datetime import time
from unittest.mock import patch

from app import create_app
from tests.test_alta_trabajador import DEPARTAMENTO, Cursor as CursorAlta, cuerpo
from tests.test_alta_trabajador import token as token_alta
from tests.test_coste_ett import MANDO, CursorLista
from tests.test_coste_ett import token as token_lista
from tests.test_edicion_usuarios import Cursor as CursorEdicion, trabajador
from tests.test_edicion_usuarios import token as token_edicion
from tests.test_pausa_inicio import TRABAJADOR, Cursor as CursorTurnos
from tests.test_pausa_inicio import token as token_turnos
from tests.test_alta_trabajador import Conexion as ConexionAlta
from tests.test_coste_ett import Conexion as ConexionLista
from tests.test_edicion_usuarios import Conexion as ConexionEdicion
from tests.test_pausa_inicio import Conexion as ConexionTurnos


def test_el_alta_guarda_pausa_habitual():
    app = create_app()
    cursor = CursorAlta([DEPARTAMENTO])
    datos = cuerpo()
    datos["pausa_minutos"] = 30
    datos["pausa_habitual"] = "14:00"
    with patch("rutas.trabajadores.cursor", return_value=ConexionAlta(cursor)):
        respuesta = app.test_client().post(
            "/trabajadores",
            json=datos,
            headers={"Authorization": f"Bearer {token_alta(app, 'admin')}"},
        )

    assert respuesta.status_code == 201
    assert cursor.pausa_habitual == time(14, 0)


def test_el_alta_con_pausa_cero_y_hora_da_400():
    app = create_app()
    cursor = CursorAlta([DEPARTAMENTO])
    datos = cuerpo()
    datos["pausa_minutos"] = 0
    datos["pausa_habitual"] = "14:00"
    with patch("rutas.trabajadores.cursor", return_value=ConexionAlta(cursor)):
        respuesta = app.test_client().post(
            "/trabajadores",
            json=datos,
            headers={"Authorization": f"Bearer {token_alta(app, 'admin')}"},
        )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Indica primero la duración de la pausa"
    assert cursor.insertados == []


def test_la_edicion_pone_y_quita_la_hora():
    app = create_app()
    persona = trabajador()
    persona["pausa_minutos"] = 30
    cursor = CursorEdicion([persona])
    cliente = app.test_client()
    cabecera = {"Authorization": f"Bearer {token_edicion(app, 'admin')}"}
    with patch("rutas.usuarios.cursor", return_value=ConexionEdicion(cursor)):
        puesta = cliente.put(
            "/usuarios/nerea.lago",
            json={"pausa_habitual": "14:00"},
            headers=cabecera,
        )
        quitada = cliente.put(
            "/usuarios/nerea.lago",
            json={"pausa_habitual": None},
            headers=cabecera,
        )

    assert puesta.status_code == 200
    assert puesta.get_json()["pausa_habitual"] == "14:00"
    assert cursor.updates[0][1] == (time(14, 0), persona["id"])
    assert quitada.status_code == 200
    assert quitada.get_json()["pausa_habitual"] is None
    assert cursor.updates[1][1] == (None, persona["id"])


def test_poner_la_pausa_a_cero_borra_la_hora():
    app = create_app()
    persona = trabajador()
    persona["pausa_minutos"] = 30
    cursor = CursorEdicion([persona])
    with patch("rutas.usuarios.cursor", return_value=ConexionEdicion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/nerea.lago",
            json={"pausa_minutos": 0},
            headers={"Authorization": f"Bearer {token_edicion(app, 'admin')}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["pausa_minutos"] == 0
    assert respuesta.get_json()["pausa_habitual"] is None
    assert cursor.updates[0][1] == (0, None, persona["id"])


def test_pausa_habitual_con_formato_invalido_da_400():
    app = create_app()
    persona = trabajador()
    persona["pausa_minutos"] = 30
    cursor = CursorEdicion([persona])
    with patch("rutas.usuarios.cursor", return_value=ConexionEdicion(cursor)):
        respuesta = app.test_client().put(
            "/usuarios/nerea.lago",
            json={"pausa_habitual": "25:00"},
            headers={"Authorization": f"Bearer {token_edicion(app, 'admin')}"},
        )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "La hora no es válida"
    assert cursor.updates == []


def test_turnos_y_departamentos_devuelven_pausa_habitual():
    app = create_app()
    cliente = app.test_client()
    cursor = CursorTurnos(pausa=30, pausa_habitual=time(14, 0))
    with patch("rutas.turnos.cursor", return_value=ConexionTurnos(cursor)):
        semana = cliente.get(
            "/turnos?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token_turnos(app, 'mando', MANDO)}"},
        )
        mensual = cliente.get(
            "/turnos/mes?anio=2026&mes=11",
            headers={"Authorization": f"Bearer {token_turnos(app, 'mando', MANDO)}"},
        )
        mios = cliente.get(
            "/turnos/mios?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token_turnos(app, 'trabajador', TRABAJADOR)}"},
        )
    with patch("rutas.departamentos.cursor", return_value=ConexionLista(CursorLista())):
        departamentos = cliente.get(
            "/departamentos",
            headers={"Authorization": f"Bearer {token_lista(app, 'mando', MANDO)}"},
        )
        propio = cliente.get(
            "/departamentos",
            headers={"Authorization": f"Bearer {token_lista(app, 'trabajador', TRABAJADOR)}"},
        )

    assert semana.status_code == 200
    assert mensual.status_code == 200
    assert departamentos.status_code == 200
    persona = semana.get_json()["trabajadores"][0]
    assert persona["pausa_minutos"] == 30
    assert persona["pausa_habitual"] == "14:00"
    assert mensual.get_json()["trabajadores"][0]["pausa_habitual"] == "14:00"
    assert "pausa_habitual" not in mios.get_json()["trabajadores"][0]
    assert departamentos.get_json()[0]["trabajadores"][0]["pausa_habitual"] == "14:00"
    assert "pausa_habitual" not in propio.get_json()[0]["trabajadores"][0]
