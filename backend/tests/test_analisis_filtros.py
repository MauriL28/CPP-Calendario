from unittest.mock import patch

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


def test_delegacion_sola_deja_fuera_los_fichajes_sin_usuario():
    respuesta, cursor = pedir("/fichajes/analisis", {"delegacion": "60I"})

    assert respuesta.status_code == 200
    texto, params = filtro(cursor)
    assert "g.codigo = %s" in texto
    assert "f.usuario_id IS NULL OR" not in texto
    assert params[-1] == "60I"


def test_codigo_solo_filtra_por_la_columna_del_departamento():
    respuesta, cursor = pedir("/fichajes/analisis", {"codigo": "trafico"})

    assert respuesta.status_code == 200
    texto, params = filtro(cursor)
    assert "d.codigo = %s" in texto
    assert "f.usuario_id IS NULL OR" not in texto
    assert "g.codigo = ANY(%s)" in texto
    assert params[-1] == "trafico"


def test_delegacion_y_codigo_se_combinan_con_estado_y_fechas():
    respuesta, cursor = pedir(
        "/fichajes/analisis",
        {
            "delegacion": "60I",
            "codigo": "trafico",
            "coincide": "descuadre",
            "desde": "2026-09-01",
            "hasta": "2026-09-30",
        },
    )

    assert respuesta.status_code == 200
    texto, params = filtro(cursor)
    assert "g.codigo = %s" in texto
    assert "d.codigo = %s" in texto
    assert "f.coincide = %s" in texto
    assert "f.fecha >= %s" in texto
    assert "f.fecha <= %s" in texto
    assert "f.usuario_id IS NULL OR" not in texto
    assert params[-5:] == ["60I", "trafico", "descuadre", params[-2], params[-1]]
    assert str(params[-2]) == "2026-09-01"
    assert str(params[-1]) == "2026-09-30"


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
