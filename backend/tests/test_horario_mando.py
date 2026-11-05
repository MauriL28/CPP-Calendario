from datetime import date, datetime, timedelta
from unittest.mock import patch

from app import create_app
from seguridad import emitir_token

MANDO = "93c2848c-a3e7-406f-b4aa-63a70c353b31"
DELEGACION = "delegacion-60"


class Cursor:
    def __init__(self):
        self.dias = []
        self.inserts = 0
        self._fila = None
        self._filas = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        params = params or ()
        self._fila = None
        self._filas = []
        if "WHERE login = %s AND rol = 'mando'" in texto:
            if params[0] == "ana.rios":
                self._fila = {
                    "id": MANDO,
                    "departamento_id": "depto",
                    "activo": True,
                }
        elif "WHERE u.id = %s AND u.rol = 'mando'" in texto:
            if params[0] == MANDO:
                self._fila = {"delegacion_id": DELEGACION}
        elif "codigo = 'mandos'" in texto:
            self._fila = None
        elif texto.startswith("SELECT u.id, u.nombre"):
            self._filas = [
                {
                    "id": MANDO,
                    "nombre": "Ana Ríos",
                    "grupo": "STEF",
                    "seccion": None,
                }
            ]
        elif "FROM turno" in texto:
            self._filas = []
        elif "FROM horario_version" in texto:
            fin = params[-1]
            ids = set(params[0])
            self._filas = [
                fila
                for fila in self.dias
                if fila["usuario_id"] in ids and fila["desde"] <= fin
            ]
        elif "FROM empresa" in texto:
            self._fila = {
                "noche_inicio": datetime.strptime("22:00", "%H:%M").time(),
                "noche_fin": datetime.strptime("06:00", "%H:%M").time(),
            }
        elif "usa_horario_habitual" in texto:
            self._filas = [{"id": MANDO, "usa_horario_habitual": True}]
        elif texto.startswith("DELETE FROM horario_dia"):
            self.dias = [
                fila
                for fila in self.dias
                if not (fila["usuario_id"] == params[0] and fila["desde"] == params[1])
            ]
        elif texto.startswith("INSERT INTO horario_version"):
            self.inserts += 1
        elif texto.startswith("INSERT INTO horario_dia"):
            self.inserts += 1
            self.dias.append(
                {
                    "usuario_id": params[0],
                    "desde": params[1],
                    "dia_semana": params[2],
                    "horario_inicio": params[3],
                    "horario_fin": params[4],
                }
            )
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


def token(app, rol, usuario=MANDO):
    with app.app_context():
        return emitir_token(usuario, rol, ["60I"], "Ana", "Tráfico")


def horario(dia):
    return {
        "horario_dias": [
            {"dia_semana": dia, "hora_inicio": "08:00", "hora_fin": "16:00"},
        ],
        "desde": date.today().isoformat(),
    }


def pedir(cliente, app, cursor, metodo, ruta, cuerpo, rol, usuario=MANDO):
    conexion = Conexion(cursor)
    with (
        patch("rutas.usuarios.cursor", return_value=conexion),
        patch("rutas.trabajadores.cursor", return_value=conexion),
        patch("rutas.turnos.cursor", return_value=conexion),
    ):
        respuesta = cliente.open(
            ruta,
            method=metodo,
            json=cuerpo,
            headers={"Authorization": f"Bearer {token(app, rol, usuario)}"},
        )
    return respuesta


def test_el_admin_fija_el_horario_y_el_cuadrante_lo_muestra_habitual():
    app = create_app()
    cursor = Cursor()
    cliente = app.test_client()
    hoy = date.today()
    respuesta = pedir(
        cliente,
        app,
        cursor,
        "PUT",
        "/usuarios/ana.rios/horario",
        horario(hoy.weekday()),
        "admin",
        "admin-1",
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["horario"] == [
        {"dia_semana": hoy.weekday(), "inicio": "08:00", "fin": "16:00"}
    ]
    lunes = hoy - timedelta(days=hoy.weekday())
    cuadrante = pedir(
        cliente,
        app,
        cursor,
        "GET",
        f"/turnos/mandos?desde={lunes.isoformat()}",
        None,
        "mando",
    )

    assert cuadrante.status_code == 200
    persona = cuadrante.get_json()["trabajadores"][0]
    dia = next(item for item in persona["dias"] if item["fecha"] == hoy.isoformat())
    assert dia["origen"] == "habitual"
    assert dia["turno"]["hora_inicio"] == "08:00"
    assert dia["turno"]["hora_fin"] == "16:00"


def test_el_mando_cambia_el_suyo():
    app = create_app()
    cursor = Cursor()
    respuesta = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        "/mandos/propio/horario",
        {
            "horario_dias": [
                {"dia_semana": date.today().weekday(), "hora_inicio": "09:00", "hora_fin": "17:00"},
            ],
            "desde": date.today().isoformat(),
        },
        "mando",
    )

    assert respuesta.status_code == 200
    assert respuesta.get_json()["horario"][0]["inicio"] == "09:00"
    assert cursor.dias[0]["usuario_id"] == MANDO
    assert cursor.dias[0]["horario_fin"].strftime("%H:%M") == "17:00"


def test_un_mando_no_puede_cambiar_el_de_otro():
    app = create_app()
    cursor = Cursor()
    cuerpo = horario(date.today().weekday())
    cuerpo["login"] = "otro.mando"
    respuesta = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        "/mandos/propio/horario",
        cuerpo,
        "mando",
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "Campo no permitido"
    assert cursor.inserts == 0
    assert cursor.dias == []


def test_desde_anterior_a_hoy_da_400():
    app = create_app()
    cursor = Cursor()
    cuerpo = horario(0)
    cuerpo["desde"] = (date.today() - timedelta(days=1)).isoformat()
    respuesta = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        "/mandos/propio/horario",
        cuerpo,
        "mando",
    )

    assert respuesta.status_code == 400
    assert respuesta.get_json()["error"] == "desde no puede ser anterior a hoy"
    assert cursor.inserts == 0


def test_admin_recibe_404_si_no_es_mando():
    app = create_app()
    cursor = Cursor()
    respuesta = pedir(
        app.test_client(),
        app,
        cursor,
        "PUT",
        "/usuarios/nerea.lago/horario",
        horario(date.today().weekday()),
        "admin",
        "admin-1",
    )

    assert respuesta.status_code == 404
    assert respuesta.get_json()["error"] == "No se ha encontrado el mando"
    assert cursor.inserts == 0
