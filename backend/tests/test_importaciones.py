from datetime import date, datetime, timezone
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token


class Cursor:
    def __init__(self, filas):
        self.filas = filas
        self.sql = ""

    def execute(self, sql, _params=None):
        self.sql = " ".join(sql.split())

    def fetchall(self):
        return self.filas


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


def test_un_admin_recibe_las_ultimas_importaciones():
    app = create_app()
    momento = datetime(2026, 9, 1, 10, 30, tzinfo=timezone.utc)
    cursor = Cursor(
        [
            {
                "momento": momento,
                "nombre_archivo": "septiembre.xlsx",
                "nombre": "Admin",
                "filas_leidas": 12,
                "filas_sin_emparejar": 1,
                "dias_incidencia": 2,
                "fecha_desde": date(2026, 9, 1),
                "fecha_hasta": None,
            }
        ]
    )
    with patch("rutas.fichajes.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            "/fichajes/importaciones",
            headers={"Authorization": f"Bearer {token(app, 'admin')}"},
        )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == [
        {
            "momento": "2026-09-01T10:30:00+00:00",
            "nombre_archivo": "septiembre.xlsx",
            "nombre": "Admin",
            "filas_leidas": 12,
            "filas_sin_emparejar": 1,
            "dias_incidencia": 2,
            "fecha_desde": "2026-09-01",
            "fecha_hasta": None,
        }
    ]
    assert "ORDER BY i.momento DESC" in cursor.sql
    assert "LIMIT 10" in cursor.sql


def test_quien_no_es_admin_recibe_403():
    app = create_app()
    with patch("rutas.fichajes.cursor") as cursor:
        respuesta = app.test_client().get(
            "/fichajes/importaciones",
            headers={"Authorization": f"Bearer {token(app, 'mando')}"},
        )

    assert respuesta.status_code == 403
    assert respuesta.get_json()["error"] == "No autorizado"
    cursor.assert_not_called()
