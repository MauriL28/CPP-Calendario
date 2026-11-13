from datetime import date, datetime, time
from unittest.mock import patch

import psycopg

from app import create_app
from rutas.turnos import _dias_departamento
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DEPARTAMENTO = "bdc0a198-ac3a-47ef-84f3-d834f2adf608"
OTRO = "f655754e-7511-41bf-8188-f11ef2ed928f"
LUNES = date(2026, 11, 2)


class Cursor:
    def __init__(self, departamento_id=DEPARTAMENTO, fallar_en=None):
        self.departamento_id = departamento_id
        self.fallar_en = fallar_en
        self.turnos = {}
        self.inserts = 0
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if texto.startswith("SELECT rol, departamento_id"):
            self._fila = {"rol": "mando", "departamento_id": DEPARTAMENTO}
        elif texto.startswith("SELECT departamento_id"):
            self._filas = []
        elif texto.startswith("SELECT id, departamento_id"):
            self._fila = {
                "id": "trab-1",
                "departamento_id": self.departamento_id,
            }
        elif texto.startswith("SELECT vacaciones"):
            self._fila = {"vacaciones": None}
        elif texto.startswith("SELECT pausa_minutos"):
            self._fila = {"pausa_minutos": 0}
        elif texto.startswith("SELECT noche_inicio"):
            self._fila = {
                "noche_inicio": datetime.strptime("22:00", "%H:%M").time(),
                "noche_fin": datetime.strptime("06:00", "%H:%M").time(),
            }
        elif texto.startswith("INSERT INTO turno"):
            self.inserts += 1
            if self.fallar_en is not None and self.inserts == self.fallar_en:
                raise psycopg.Error("fallo")
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
        elif texto.startswith("DELETE FROM turno"):
            self._fila = self.turnos.pop((params[0], params[1]), None)
        else:
            raise AssertionError(texto)

    def fetchone(self):
        return self._fila

    def fetchall(self):
        return self._filas


class Conexion:
    def __init__(self, cursor):
        self.cursor = cursor
        self.confirmada = False

    def __enter__(self):
        return self.cursor

    def __exit__(self, tipo, *_args):
        self.confirmada = tipo is None
        if tipo is not None:
            self.cursor.turnos.clear()
        return False


NOCHE = time(22, 0)


def token(app, rol="mando", usuario=MANDO):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Mando", "Tráfico")


def pedir(cliente, app, cursor, cuerpo_o_metodo, cuerpo=None, rol="mando"):
    conexion = Conexion(cursor)
    with patch("rutas.turnos.cursor", return_value=conexion):
        if isinstance(cuerpo_o_metodo, str):
            respuesta = cliente.open(
                "/turnos/mandos/propio",
                method=cuerpo_o_metodo,
                json=cuerpo,
                headers={"Authorization": f"Bearer {token(app, rol)}"},
            )
        else:
            respuesta = cliente.put(
                "/turnos/varios",
                json=cuerpo_o_metodo,
                headers={"Authorization": f"Bearer {token(app)}"},
            )
    return respuesta, conexion


def test_guarda_varios_dias_con_horario():
    app = create_app()
    cursor = Cursor()
    fechas = ["2026-11-02", "2026-11-03", "2026-11-04"]
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": fechas,
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 3, "pausa_inicio": None}
    assert conexion.confirmada
    assert len(cursor.turnos) == 3
    for texto in fechas:
        fila = cursor.turnos[("trab-1", date.fromisoformat(texto))]
        assert fila["ausencia"] is None
        assert fila["hora_inicio"].strftime("%H:%M") == "08:00"
        assert fila["hora_fin"].strftime("%H:%M") == "16:00"
        assert fila["horas_planificadas"] == 8


def test_guarda_varios_dias_con_ausencia():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-03"],
            "ausencia": "V",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 2, "pausa_inicio": None}
    for fila in cursor.turnos.values():
        assert fila["ausencia"] == "V"
        assert fila["hora_inicio"] is None
        assert fila["hora_fin"] is None
        assert fila["horas_planificadas"] == 0
        assert fila["horas_nocturnas"] == 0


def test_sustituye_un_dia_que_ya_tenia_turno():
    app = create_app()
    cursor = Cursor()
    cursor.turnos[("trab-1", LUNES)] = {
        "ausencia": "L",
        "hora_inicio": None,
        "hora_fin": None,
    }
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02"],
            "hora_inicio": "09:00",
            "hora_fin": "17:00",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 1, "pausa_inicio": None}
    fila = cursor.turnos[("trab-1", LUNES)]
    assert fila["ausencia"] is None
    assert fila["hora_inicio"].strftime("%H:%M") == "09:00"
    assert len(cursor.turnos) == 1


def test_fechas_de_dos_semanas_da_400():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-09"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 400
    assert cursor.inserts == 0
    assert cursor.turnos == {}


def test_trabajador_de_otro_departamento_da_404():
    app = create_app()
    cursor = Cursor(departamento_id=OTRO)
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "Ese trabajador no es de tu departamento"
    assert cursor.inserts == 0
    assert conexion.confirmada


def test_si_una_fecha_falla_no_se_guarda_ninguna():
    app = create_app()
    cursor = Cursor(fallar_en=2)
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        {
            "login": "nerea.lago",
            "fechas": ["2026-11-02", "2026-11-03"],
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 503
    assert not conexion.confirmada
    assert cursor.turnos == {}


def test_guarda_v_en_varios_dias():
    app = create_app()
    cursor = Cursor()
    fechas = ["2026-11-02", "2026-11-03", "2026-11-04"]
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {"fechas": fechas, "ausencia": "V"},
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 3}
    assert conexion.confirmada
    assert cursor.inserts == 3
    for texto in fechas:
        fila = cursor.turnos[(MANDO, date.fromisoformat(texto))]
        assert fila["ausencia"] == "V"
        assert fila["hora_inicio"] is None
        assert fila["hora_fin"] is None
        assert fila["horas_planificadas"] == 0
        assert fila["horas_nocturnas"] == 0


def test_guarda_b_en_un_dia():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {"fechas": ["2026-11-02"], "ausencia": "B"},
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 1}
    fila = cursor.turnos[(MANDO, LUNES)]
    assert fila["ausencia"] == "B"
    assert fila["horas_planificadas"] == 0
    assert fila["horas_nocturnas"] == 0


def test_ausencia_no_permitida_da_400():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {"fechas": ["2026-11-02"], "ausencia": "D"},
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "La ausencia no es válida"
    assert cursor.inserts == 0


def test_borrar_funciona_y_404_si_no_hay_fila():
    app = create_app()
    cursor = Cursor()
    cursor.turnos[(MANDO, LUNES)] = {"ausencia": "V"}
    cliente = app.test_client()
    borrado, conexion = pedir(cliente, app, cursor, "DELETE", {"fecha": "2026-11-02"})

    assert borrado.status_code == 200
    assert borrado.get_json() == {"fecha": "2026-11-02"}
    assert (MANDO, LUNES) not in cursor.turnos
    assert conexion.confirmada

    vacio, _conexion = pedir(cliente, app, cursor, "DELETE", {"fecha": "2026-11-02"})
    assert vacio.status_code == 404
    assert vacio.get_json()["error"] == "No se ha encontrado el turno"


def test_no_mando_da_403():
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    guardado, _conexion = pedir(
        cliente,
        app,
        cursor,
        "PUT",
        {"fechas": ["2026-11-02"], "ausencia": "V"},
        rol="trabajador",
    )
    borrado, _conexion = pedir(
        cliente, app, cursor, "DELETE", {"fecha": "2026-11-02"}, rol="trabajador"
    )

    assert guardado.status_code == 403
    assert borrado.status_code == 403
    assert cursor.inserts == 0
    assert cursor.turnos == {}


def test_guarda_horario_en_varios_dias():
    app = create_app()
    cursor = Cursor()
    fechas = ["2026-11-02", "2026-11-03", "2026-11-04"]
    respuesta, conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {"fechas": fechas, "hora_inicio": "08:00", "hora_fin": "16:00"},
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"guardados": 3}
    assert conexion.confirmada
    for texto in fechas:
        fila = cursor.turnos[(MANDO, date.fromisoformat(texto))]
        assert fila["ausencia"] is None
        assert fila["hora_inicio"].strftime("%H:%M") == "08:00"
        assert fila["hora_fin"].strftime("%H:%M") == "16:00"
        assert fila["horas_planificadas"] == 8
        assert fila["horas_nocturnas"] == 0


def test_horario_con_horas_invalidas_da_400():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {"fechas": ["2026-11-02"], "hora_inicio": "25:00", "hora_fin": "16:00"},
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "La hora no es válida"
    assert cursor.inserts == 0


def test_horario_y_ausencia_a_la_vez_da_400():
    app = create_app()
    cursor = Cursor()
    respuesta, _conexion = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        {
            "fechas": ["2026-11-02"],
            "ausencia": "V",
            "hora_inicio": "08:00",
            "hora_fin": "16:00",
        },
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Indica horario o ausencia, no las dos"
    assert cursor.inserts == 0


class CursorCuadrante(Cursor):
    def __init__(self):
        super().__init__()
        self._filas = []
        self.habitual = [
            {
                "usuario_id": MANDO,
                "desde": date(2026, 1, 1),
                "dia_semana": dia,
                "horario_inicio": time(9, 0),
                "horario_fin": time(17, 0),
            }
            for dia in range(5)
        ]

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._filas = []
        if "WHERE u.id = %s AND u.rol = 'mando'" in texto:
            self._fila = {"delegacion_id": "delegacion-60"}
            return
        if "codigo = 'mandos'" in texto:
            self._fila = None
            return
        if texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [{"id": MANDO, "nombre": "Ana Ríos", "grupo": "STEF", "seccion": None}]
            self._fila = None
            return
        if "FROM turno" in texto and texto.startswith("SELECT"):
            inicio, fin = params[1], params[2]
            ids = set(params[0])
            self._filas = [
                fila
                for (usuario, fecha), fila in self.turnos.items()
                if usuario in ids and inicio <= fecha <= fin
            ]
            self._fila = None
            return
        if "FROM horario_version" in texto:
            fin = params[-1]
            ids = set(params[0])
            self._filas = [
                fila
                for fila in self.habitual
                if fila["usuario_id"] in ids and fila["desde"] <= fin
            ]
            self._fila = None
            return
        if "usa_horario_habitual" in texto:
            self._filas = [{"id": MANDO, "usa_horario_habitual": True}]
            self._fila = None
            return
        super().execute(sql, params)

    def fetchall(self):
        return self._filas


def _dia(respuesta, fecha):
    persona = respuesta.get_json()["trabajadores"][0]
    return next(item for item in persona["dias"] if item["fecha"] == fecha)


def test_el_cuadrante_muestra_guardado_y_al_borrar_vuelve_al_habitual():
    app = create_app()
    cursor = CursorCuadrante()
    cliente = app.test_client()
    guardado, _conexion = pedir(
        cliente,
        app,
        cursor,
        "PUT",
        {"fechas": ["2026-11-02", "2026-11-03"], "hora_inicio": "08:00", "hora_fin": "16:00"},
    )
    assert guardado.status_code == 200

    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        cuadrante = cliente.get(
            "/turnos/mandos?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app)}"},
        )
    assert cuadrante.status_code == 200
    lunes = _dia(cuadrante, "2026-11-02")
    assert lunes["origen"] == "guardado"
    assert lunes["turno"] == {"hora_inicio": "08:00", "hora_fin": "16:00"}

    borrado, _conexion = pedir(cliente, app, cursor, "DELETE", {"fecha": "2026-11-02"})
    assert borrado.status_code == 200

    with patch("rutas.turnos.cursor", return_value=Conexion(cursor)):
        otra_vez = cliente.get(
            "/turnos/mandos?desde=2026-11-02",
            headers={"Authorization": f"Bearer {token(app)}"},
        )
    assert otra_vez.status_code == 200
    lunes = _dia(otra_vez, "2026-11-02")
    assert lunes["origen"] == "habitual"
    assert lunes["turno"]["hora_inicio"] == "09:00"
    assert lunes["turno"]["hora_fin"] == "17:00"
    martes = _dia(otra_vez, "2026-11-03")
    assert martes["origen"] == "guardado"
    assert martes["turno"]["hora_inicio"] == "08:00"


def test_origen_solo_en_la_fila_del_mando():
    versiones = [{"desde": date(2026, 1, 1), "dias": {0: (time(8, 0), time(16, 0))}}]
    guardado = {
        "ausencia": "V",
        "hora_inicio": None,
        "hora_fin": None,
        "horas_planificadas": 0,
        "horas_nocturnas": 0,
    }
    propio = _dias_departamento(
        "yo",
        [LUNES],
        {("yo", LUNES): guardado},
        {"yo": versiones},
        NOCHE,
        time(6, 0),
        True,
        con_origen=True,
    )
    habitual = _dias_departamento(
        "yo",
        [LUNES],
        {},
        {"yo": versiones},
        NOCHE,
        time(6, 0),
        True,
        con_origen=True,
    )
    vacio = _dias_departamento(
        "yo",
        [LUNES],
        {},
        {},
        NOCHE,
        time(6, 0),
        True,
        {"yo": False},
        con_origen=True,
    )
    ajeno = _dias_departamento(
        "otro",
        [LUNES],
        {("otro", LUNES): guardado},
        {},
        NOCHE,
        time(6, 0),
        False,
    )

    assert propio[0]["origen"] == "guardado"
    assert propio[0]["turno"] == {"ausencia": "V"}
    assert habitual[0]["origen"] == "habitual"
    assert habitual[0]["turno"]["hora_inicio"] == "08:00"
    assert vacio[0]["origen"] == "vacio"
    assert vacio[0]["turno"] is None
    assert "origen" not in ajeno[0]
    assert ajeno[0]["turno"] == {"ausencia": "V"}
