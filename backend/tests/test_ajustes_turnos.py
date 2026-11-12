from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

ADMIN = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
TRABAJADOR = "11111111-1111-1111-1111-111111111111"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
LUNES = date(2026, 11, 2)
MARTES = date(2026, 11, 3)
MIERCOLES = date(2026, 11, 4)
JUEVES = date(2026, 11, 5)
PRIMERO = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SEGUNDO = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

AJUSTES = [
    {
        "id": SEGUNDO,
        "usuario_afectado_id": TRABAJADOR,
        "fecha": MARTES,
        "horas": Decimal("2.00"),
        "motivo": "Segundo",
    },
    {
        "id": PRIMERO,
        "usuario_afectado_id": TRABAJADOR,
        "fecha": MARTES,
        "horas": Decimal("0.50"),
        "motivo": "Primero",
    },
    {
        "id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "usuario_afectado_id": TRABAJADOR,
        "fecha": LUNES,
        "horas": Decimal("1.50"),
        "motivo": "Extra",
    },
    {
        "id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
        "usuario_afectado_id": TRABAJADOR,
        "fecha": JUEVES,
        "horas": Decimal("-1.25"),
        "motivo": "Corrección",
    },
]


class Cursor:
    def __init__(self):
        self.consultas = []
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
                    "grupo": "STEF",
                    "activo": True,
                    "seccion": None,
                    "tarifas_ett": None,
                }
            ]
        elif "grupo, activo" in texto:
            self._fila = {
                "id": TRABAJADOR,
                "nombre": "Nerea Lago",
                "login": "nerea.lago",
                "grupo": "STEF",
                "activo": True,
            }
        elif "FROM ajuste" in texto:
            self.consultas.append(params)
            ids, inicio, fin = params
            filas = [
                fila
                for fila in AJUSTES
                if str(fila["usuario_afectado_id"]) in {str(identificador) for identificador in ids}
                and inicio <= fila["fecha"] <= fin
            ]
            if "ORDER BY fecha, id" in texto:
                filas.sort(key=lambda fila: (fila["fecha"], fila["id"]))
            else:
                filas.reverse()
            self._filas = filas
        elif "FROM turno" in texto or "FROM horario_version" in texto or "FROM festivo" in texto:
            self._filas = []
        elif "usa_horario_habitual" in texto:
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


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        return self.cursor

    def __exit__(self, *_args):
        return False


def token(app, rol, usuario):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Nerea", "Tráfico")


def dias_de(ruta, rol="admin", usuario=ADMIN):
    app = create_app()
    cursor = Cursor()
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        respuesta = app.test_client().get(
            ruta,
            headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
        )
    assert respuesta.status_code == 200
    return respuesta.get_json()["trabajadores"][0]["dias"], cursor


def dia(dias, fecha):
    return next(item for item in dias if item["fecha"] == fecha.isoformat())


def test_un_dia_con_un_ajuste_en_la_semana_y_el_mes():
    semana = f"/turnos?desde={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}"
    mes = f"/turnos/mes?anio=2026&mes=11&departamento_id={DEPARTAMENTO}"
    for ruta in (semana, mes):
        dias, cursor = dias_de(ruta)
        encontrado = dia(dias, LUNES)
        assert len(cursor.consultas) == 1
        assert encontrado["ajustes"] == [{"horas": 1.5, "motivo": "Extra"}]
        assert type(encontrado["ajustes"][0]["horas"]) is float
        assert encontrado["turno"] is None


def test_un_dia_con_dos_ajustes_sale_en_orden_de_creacion():
    dias, _cursor = dias_de(f"/turnos?desde={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}")
    assert dia(dias, MARTES)["ajustes"] == [
        {"horas": 0.5, "motivo": "Primero"},
        {"horas": 2.0, "motivo": "Segundo"},
    ]


def test_un_dia_sin_ajuste_no_lleva_la_clave():
    dias, _cursor = dias_de(f"/turnos?desde={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}")
    assert "ajustes" not in dia(dias, MIERCOLES)


def test_un_ajuste_negativo_sale_como_numero():
    dias, _cursor = dias_de(f"/turnos?desde={LUNES.isoformat()}&departamento_id={DEPARTAMENTO}")
    ajuste = dia(dias, JUEVES)["ajustes"][0]
    assert ajuste["horas"] == -1.25
    assert type(ajuste["horas"]) is float
    assert ajuste["motivo"] == "Corrección"


def test_turnos_mios_no_trae_ajustes():
    dias, cursor = dias_de(f"/turnos/mios?desde={LUNES.isoformat()}", "trabajador", TRABAJADOR)
    assert all("ajustes" not in dia for dia in dias)
    assert all("FROM ajuste" not in texto for texto in cursor.sql)
