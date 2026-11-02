from datetime import date, time

import openpyxl

from fichajes import _insertar_eventos, leer_excel


def libro(ruta, filas):
    wb = openpyxl.Workbook()
    hoja = wb.active
    hoja.title = "Data"
    hoja.append(
        ["Nº pers.", "Nombre del empleado o candidat", "Texto CHT", "Fe.lóg.", "Hora"]
    )
    for fila in filas:
        hoja.append(fila)
    wb.save(ruta)
    wb.close()


class Tabla:
    """fichaje_evento en memoria. No abre la base de desarrollo."""

    def __init__(self):
        self.filas = []
        self._resultado = []

    def execute(self, sql, params=None):
        texto = " ".join(sql.split())
        if texto.startswith("SELECT orden"):
            self._resultado = list(self.filas)
            return
        if texto.startswith("DELETE FROM fichaje_evento"):
            desde, hasta = params
            self.filas = [
                fila
                for fila in self.filas
                if fila["fecha"] is not None and not (desde <= fila["fecha"] <= hasta)
            ]
            return
        if texto.startswith("UPDATE fichaje_evento"):
            return
        raise AssertionError(texto)

    def executemany(self, sql, filas):
        texto = " ".join(sql.split())
        if not texto.startswith("INSERT INTO fichaje_evento"):
            raise AssertionError(texto)
        for orden, numero_sap, tipo, fecha, hora in filas:
            self.filas.append(
                {
                    "orden": orden,
                    "numero_sap": numero_sap,
                    "tipo": tipo,
                    "fecha": fecha,
                    "hora": hora,
                }
            )

    def fetchall(self):
        return self._resultado


def claves(filas):
    return sorted(
        (fila["numero_sap"], fila["tipo"], fila["fecha"], fila["hora"]) for fila in filas
    )


def test_agosto_y_septiembre_se_acumulan_y_reimportar_no_duplica(tmp_path):
    agosto = tmp_path / "agosto.xlsx"
    septiembre = tmp_path / "septiembre.xlsx"
    libro(
        agosto,
        [
            [101882, "Amaia", "Llegada", date(2026, 8, 3), time(8, 0)],
            [101882, "Amaia", "Salida", date(2026, 8, 3), time(16, 0)],
        ],
    )
    libro(
        septiembre,
        [
            [101882, "Amaia", "Llegada", date(2026, 9, 7), time(20, 21)],
            [101882, "Amaia", "Salida", date(2026, 9, 8), time(4, 0)],
        ],
    )
    tabla = Tabla()
    nuevas, actualizadas = _insertar_eventos(tabla, leer_excel(agosto)[2])
    assert (nuevas, actualizadas) == (2, 0)
    nuevas, actualizadas = _insertar_eventos(tabla, leer_excel(septiembre)[2])
    assert (nuevas, actualizadas) == (2, 0)
    esperado = [
        ("101882", "Llegada", date(2026, 8, 3), time(8, 0)),
        ("101882", "Llegada", date(2026, 9, 7), time(20, 21)),
        ("101882", "Salida", date(2026, 8, 3), time(16, 0)),
        ("101882", "Salida", date(2026, 9, 8), time(4, 0)),
    ]
    assert claves(tabla.filas) == esperado

    nuevas, actualizadas = _insertar_eventos(tabla, leer_excel(septiembre)[2])
    assert (nuevas, actualizadas) == (0, 0)
    assert claves(tabla.filas) == esperado
