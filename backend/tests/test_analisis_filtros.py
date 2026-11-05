from unittest.mock import patch

import pytest

from app import create_app
from seguridad import emitir_token


class Cursor:
    def __init__(self):
        self.consultas = []

    def execute(self, sql, params=None):
        self.consultas.append((" ".join(sql.split()), params))

    def fetchall(self):
        return []

    def fetchone(self):
        return {
            "total": 0,
            "ok": 0,
            "descuadre": 0,
            "sin_plan": 0,
            "sin_emparejar": 0,
        }


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


def token(app):
    with app.app_context():
        return emitir_token(
            "93c2848c-a3e7-406f-b4aa-63a70c353b31",
            "admin",
            ["60I", "05I"],
            "Admin",
            None,
        )


def pedir(ruta, consulta):
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    with patch("rutas.fichajes.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.get(
            ruta,
            query_string=consulta,
            headers={"Authorization": f"Bearer {token(app)}"},
        )
    return respuesta, cursor


def filtro(cursor):
    texto, params = cursor.consultas[0]
    return texto, params


@pytest.mark.parametrize(
    ("consulta", "incluye", "excluye", "final"),
    [
        (
            {"delegacion": "60I"},
            ("g.codigo = %s",),
            ("d.codigo = %s",),
            ("60I",),
        ),
        (
            {"codigo": "trafico"},
            ("d.codigo = %s", "g.codigo = ANY(%s)"),
            ("g.codigo = %s",),
            ("trafico",),
        ),
        (
            {
                "delegacion": "60I",
                "codigo": "trafico",
                "coincide": "descuadre",
                "desde": "2026-09-01",
                "hasta": "2026-09-30",
            },
            (
                "g.codigo = %s",
                "d.codigo = %s",
                "f.coincide = %s",
                "f.fecha >= %s",
                "f.fecha <= %s",
            ),
            (),
            ("60I", "trafico", "descuadre", "2026-09-01", "2026-09-30"),
        ),
    ],
)
def test_delegacion_y_codigo_se_combinan_con_estado_y_fechas(consulta, incluye, excluye, final):
    respuesta, cursor = pedir("/fichajes/analisis", consulta)

    assert respuesta.status_code == 200
    texto, params = filtro(cursor)
    for fragmento in incluye:
        assert fragmento in texto
    for fragmento in excluye:
        assert fragmento not in texto
    assert "f.usuario_id IS NULL OR" not in texto
    assert tuple(str(valor) for valor in params[-len(final) :]) == final


def test_delegacion_fuera_del_token_es_404():
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    with patch("rutas.fichajes.cursor", return_value=Conexion(cursor)):
        respuesta = cliente.get(
            "/fichajes/analisis",
            query_string={"delegacion": "99Z"},
            headers={"Authorization": f"Bearer {token(app)}"},
        )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "No se ha encontrado la delegación"
    assert cursor.consultas == []


def test_exportar_respeta_delegacion_y_codigo():
    respuesta, cursor = pedir(
        "/fichajes/analisis/exportar",
        {"delegacion": "05I", "codigo": "muelle"},
    )

    assert respuesta.status_code == 200
    texto, params = filtro(cursor)
    assert "g.codigo = %s" in texto
    assert "d.codigo = %s" in texto
    assert "f.usuario_id IS NULL OR" not in texto
    assert params[-2:] == ["05I", "muelle"]
    assert len(cursor.consultas) == 1
