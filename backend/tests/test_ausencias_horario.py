from datetime import date, time, timedelta
from unittest.mock import patch

from app import create_app
from rutas.turnos import _turno_visible
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
TRABAJADOR = "trab-1"
LUNES = date(2026, 11, 2)


class Cursor:
    def __init__(self, cupo=0, pausa=0):
        self.cupo = cupo
        self.pausa = pausa
        self.turnos = {}
        self.inserts = 0
        self.rowcount = 0
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT departamento_id") and "rol = 'mando'" in texto:
            self._fila = {"departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT id, departamento_id"):
            self._fila = {"id": TRABAJADOR, "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT id, nombre"):
            self._filas = [{"id": TRABAJADOR, "nombre": "Nerea Lago"}]
        elif texto.startswith("SELECT usuario_id, fecha"):
            inicio, fin = params[1], params[2]
            self._filas = [
                {"usuario_id": usuario, "fecha": fecha, "ausencia": fila["ausencia"]}
                for (usuario, fecha), fila in self.turnos.items()
                if inicio <= fecha <= fin
            ]
        elif texto.startswith("SELECT vacaciones"):
            self._fila = {"vacaciones": self.cupo}
        elif texto.startswith("SELECT fecha"):
            pedidas = set(params[1])
            self._filas = [
                {"fecha": fecha}
                for (usuario, fecha), fila in self.turnos.items()
                if usuario == params[0] and fila["ausencia"] == "V" and fecha in pedidas
            ]
        elif texto.startswith("SELECT COUNT"):
            inicio, fin = params[1], params[2]
            usados = sum(
                1
                for (usuario, fecha), fila in self.turnos.items()
                if usuario == params[0]
                and fila["ausencia"] == "V"
                and inicio <= fecha <= fin
            )
            self._fila = {"usados": usados}
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {"noche_inicio": time(22, 0), "noche_fin": time(6, 0)}
        elif texto.startswith("SELECT pausa_minutos"):
            self._fila = {"pausa_minutos": self.pausa}
        elif texto.startswith("DELETE FROM turno"):
            desde, hasta = params[1], params[2]
            for clave, fila in list(self.turnos.items()):
                usuario, fecha = clave
                if desde <= fecha <= hasta and (usuario, fecha - timedelta(days=7)) not in self.turnos:
                    del self.turnos[clave]
            self.rowcount = 0
        elif texto.startswith("INSERT INTO turno") and "fecha + 7" in texto:
            anterior, desde = params[1], params[2]
            copiados = 0
            for (usuario, fecha), fila in list(self.turnos.items()):
                if anterior <= fecha < desde:
                    self.turnos[(usuario, fecha + timedelta(days=7))] = dict(fila)
                    copiados += 1
            self.rowcount = copiados
        elif texto.startswith("INSERT INTO turno"):
            self.inserts += 1
            fila = {
                "usuario_id": params[0],
                "fecha": params[1],
                "ausencia": params[2],
                "hora_inicio": params[3],
                "hora_fin": params[4],
                "horas_planificadas": params[5],
                "horas_nocturnas": params[6],
            }
            self.turnos[(params[0], params[1])] = fila
            self._fila = fila
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

    def __exit__(self, tipo, *_args):
        return False


def pedir(metodo, ruta, cuerpo, cursor):
    app = create_app()
    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        with app.app_context():
            token = emitir_token(MANDO, "mando", ["60I"], "Mando", "Tráfico")
        return getattr(app.test_client(), metodo)(
            ruta,
            json=cuerpo,
            headers={"Authorization": f"Bearer {token}"},
        )


def test_guarda_ft_con_horario():
    cursor = Cursor()
    respuesta = pedir(
        "put",
        "/turnos",
        {
            "login": "nerea.lago",
            "fecha": "2026-11-02",
            "ausencia": "FT",
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
        cursor,
    )

    assert respuesta.status_code == 200
    fila = cursor.turnos[(TRABAJADOR, LUNES)]
    assert fila["ausencia"] == "FT"
    assert fila["hora_inicio"].strftime("%H:%M") == "08:00"
    assert fila["hora_fin"].strftime("%H:%M") == "16:00"
    assert fila["horas_planificadas"] == 8
    assert fila["horas_nocturnas"] == 0


def test_ft_sin_horario_da_400():
    cursor = Cursor()
    respuesta = pedir(
        "put",
        "/turnos",
        {"login": "nerea.lago", "fecha": "2026-11-02", "ausencia": "FT"},
        cursor,
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Indica el horario"
    assert cursor.inserts == 0


def test_sr_con_horas_da_400():
    cursor = Cursor()
    respuesta = pedir(
        "put",
        "/turnos",
        {
            "login": "nerea.lago",
            "fecha": "2026-11-02",
            "ausencia": "SR",
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
        cursor,
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Indica horario o ausencia, no las dos"
    assert cursor.inserts == 0


def test_hs_y_pend_sin_horas():
    cursor = Cursor()
    for codigo, dia in (("HS", "2026-11-02"), ("PEND", "2026-11-03")):
        respuesta = pedir(
            "put",
            "/turnos",
            {"login": "nerea.lago", "fecha": dia, "ausencia": codigo},
            cursor,
        )
        assert respuesta.status_code == 200
        fila = cursor.turnos[(TRABAJADOR, date.fromisoformat(dia))]
        assert fila["ausencia"] == codigo
        assert fila["hora_inicio"] is None
        assert fila["hora_fin"] is None
        assert fila["horas_planificadas"] == 0
        assert fila["horas_nocturnas"] == 0


def test_copiar_semana_conserva_st():
    cursor = Cursor()
    origen = {
        "ausencia": "ST",
        "hora_inicio": time(8, 0),
        "hora_fin": time(16, 0),
        "horas_planificadas": 8,
        "horas_nocturnas": 0,
    }
    cursor.turnos[(TRABAJADOR, LUNES)] = origen

    respuesta = pedir("post", "/turnos/copiar-semana", {"desde": "2026-11-09"}, cursor)

    assert respuesta.status_code == 200
    copiado = cursor.turnos[(TRABAJADOR, date(2026, 11, 9))]
    assert copiado["ausencia"] == "ST"
    assert copiado["hora_inicio"] == time(8, 0)
    assert copiado["hora_fin"] == time(16, 0)
    assert copiado["horas_planificadas"] == 8
    assert cursor.turnos[(TRABAJADOR, LUNES)] == origen


def test_st_con_pausa_resta_las_horas_planificadas():
    cursor = Cursor(pausa=60)
    respuesta = pedir(
        "put",
        "/turnos",
        {
            "login": "nerea.lago",
            "fecha": "2026-11-02",
            "ausencia": "ST",
            "hora_inicio": "10:00",
            "hora_fin": "19:00",
        },
        cursor,
    )

    assert respuesta.status_code == 200
    fila = cursor.turnos[(TRABAJADOR, LUNES)]
    assert fila["ausencia"] == "ST"
    assert fila["horas_planificadas"] == 8
    assert fila["horas_nocturnas"] == 0


def test_turno_visible_conserva_codigo_y_horario_de_st_y_ft():
    turno = {"ausencia": "ST", "hora_inicio": "08:00", "hora_fin": "16:00"}
    assert _turno_visible(turno, False) == {
        "ausencia": "ST",
        "hora_inicio": "08:00",
        "hora_fin": "16:00",
    }
    turno["ausencia"] = "FT"
    assert _turno_visible(turno, True)["ausencia"] == "FT"
    assert _turno_visible(turno, True)["hora_inicio"] == "08:00"
    assert _turno_visible({"ausencia": "SR", "hora_inicio": None, "hora_fin": None}, True) == {
        "ausencia": "SR",
    }
