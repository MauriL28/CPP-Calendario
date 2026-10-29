from uuid import UUID

from mandos import departamento_permitido

PROPIO = UUID("bdc0a198-ac3a-47ef-84f3-d834f2adf608")
CHOFERES = UUID("f655754e-7511-41bf-8188-f11ef2ed928f")
MUELLE = UUID("7cc6e41e-83fa-46d2-bef9-6d471d773dc8")


class Cursor:
    def __init__(self, usuario, departamentos=()):
        self.usuario = usuario
        self.departamentos = [{"departamento_id": departamento} for departamento in departamentos]
        self.consultas = 0

    def execute(self, _sql, _params=None):
        self.consultas += 1

    def fetchone(self):
        return self.usuario

    def fetchall(self):
        return self.departamentos


def test_el_departamento_propio_esta_permitido_aunque_no_este_en_la_tabla():
    cursor = Cursor({"rol": "mando", "departamento_id": PROPIO}, [])
    assert departamento_permitido(cursor, "mando", str(PROPIO)) is True


def test_un_departamento_de_la_tabla_esta_permitido():
    cursor = Cursor({"rol": "mando", "departamento_id": PROPIO}, [CHOFERES])
    assert departamento_permitido(cursor, "mando", CHOFERES) is True


def test_un_departamento_ajeno_no_esta_permitido():
    cursor = Cursor({"rol": "mando", "departamento_id": PROPIO}, [CHOFERES])
    assert departamento_permitido(cursor, "mando", MUELLE) is False


def test_un_usuario_inexistente_no_tiene_departamentos():
    cursor = Cursor(None)
    assert departamento_permitido(cursor, "nadie", PROPIO) is False
    assert cursor.consultas == 1


def test_un_usuario_que_no_es_mando_no_tiene_departamentos():
    cursor = Cursor({"rol": "trabajador", "departamento_id": PROPIO}, [PROPIO])
    assert departamento_permitido(cursor, "trabajador", PROPIO) is False


def test_departamento_nulo_no_esta_permitido():
    cursor = Cursor({"rol": "mando", "departamento_id": PROPIO})
    assert departamento_permitido(cursor, "mando", None) is False
