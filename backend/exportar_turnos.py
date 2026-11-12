from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

MESES_ARCHIVO = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
DIAS_LARGOS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
DIAS_CORTOS = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
GRUPOS_EXCEL = (("STEF", "Personal STEF"), ("ETT", "ETT"))


def _hora_compacta(hora):
    horas, minutos = hora.split(":")
    texto = str(int(horas))
    if int(minutos) == 0:
        return texto
    return f"{texto}:{minutos}"


def _texto_celda(turno):
    if not turno:
        return ""
    if turno["ausencia"]:
        return turno["ausencia"]
    return f"{_hora_compacta(turno['hora_inicio'])}-{_hora_compacta(turno['hora_fin'])}"


def _nombre_archivo(codigo, dias, mensual):
    depto = "".join(caracter if caracter.isalnum() else "_" for caracter in codigo).strip("_").upper()
    if not depto:
        depto = "CUADRANTE"
    if mensual:
        return f"{depto}_{MESES_ARCHIVO[dias[0].month - 1]}_{dias[0].year}.xlsx"
    semana = dias[0].isocalendar()
    return f"{depto}_semana_{semana.week}_{semana.year}.xlsx"


def _cabecera_dia(dia, mensual):
    if mensual:
        return f"{DIAS_CORTOS[dia.weekday()]}\n{dia.day}"
    return f"{DIAS_LARGOS[dia.weekday()]}\n{dia.strftime('%d/%m')}"


def _filas_excel(trabajadores):
    filas = []
    vistos = set()
    for grupo, titulo in GRUPOS_EXCEL:
        personas = [trabajador for trabajador in trabajadores if trabajador["grupo"] == grupo]
        if not personas:
            continue
        filas.append(("grupo", titulo))
        for trabajador in personas:
            vistos.add(trabajador["login"])
            filas.append(("persona", trabajador))
    for trabajador in trabajadores:
        if trabajador["login"] not in vistos:
            filas.append(("persona", trabajador))
    return filas


def _fuente_base(libro):
    libro._fonts[0] = Font(name="Arial", size=12)


def _libro(trabajadores, dias, mensual):
    libro = Workbook()
    _fuente_base(libro)
    hoja = libro.active
    hoja.title = "Cuadrante"
    hoja.freeze_panes = "B2"
    fuente = Font(name="Arial", size=12)
    cabecera = Font(name="Arial", size=12, bold=True)
    centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
    grupo_fondo = PatternFill("solid", fgColor="F2F2F2")
    hoja.cell(1, 1, "Trabajador").font = cabecera
    for indice, dia in enumerate(dias, start=2):
        celda = hoja.cell(1, indice, _cabecera_dia(dia, mensual))
        celda.font = cabecera
        celda.alignment = centro
    fila_excel = 2
    for tipo, contenido in _filas_excel(trabajadores):
        if tipo == "grupo":
            celda = hoja.cell(fila_excel, 1, contenido)
            celda.font = cabecera
            celda.fill = grupo_fondo
            if dias:
                hoja.merge_cells(
                    start_row=fila_excel,
                    start_column=1,
                    end_row=fila_excel,
                    end_column=len(dias) + 1,
                )
                for columna in range(2, len(dias) + 2):
                    vacia = hoja.cell(fila_excel, columna)
                    vacia.font = fuente
                    vacia.fill = grupo_fondo
        else:
            hoja.cell(fila_excel, 1, contenido["nombre"]).font = fuente
            for indice, dia in enumerate(contenido["dias"], start=2):
                celda = hoja.cell(fila_excel, indice, _texto_celda(dia["turno"]))
                celda.font = fuente
                celda.alignment = centro
        fila_excel += 1
    hoja.column_dimensions["A"].width = 24
    ancho = 12 if not mensual else 6
    for indice in range(2, len(dias) + 2):
        hoja.column_dimensions[hoja.cell(1, indice).column_letter].width = ancho
    hoja.row_dimensions[1].height = 30
    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer
