from datetime import datetime

JORNADA_DIA = 7.5
HORAS_CONVENIO_ANO = 1770
JORNADA_COMPLETA_SEM = 37.5


def horas_computables(ausencia, horas_planificadas):
    """Horas que cuenta la ficha. Las planificadas pueden ser 0."""
    if ausencia in (None, "", "ST", "FT"):
        if horas_planificadas is None:
            return 0.0
        return float(horas_planificadas)
    if ausencia in ("B", "HS", "PEND"):
        return JORNADA_DIA
    return 0.0


def convenio_anual(horas_convenio, horas_contrato):
    """Horas de convenio del año. Si no hay cifra, se prorratea la jornada."""
    if horas_convenio is not None:
        return float(horas_convenio)
    contrato = 0.0 if horas_contrato is None else float(horas_contrato)
    return HORAS_CONVENIO_ANO * contrato / JORNADA_COMPLETA_SEM


def minutos(valor):
    return valor.hour * 60 + valor.minute


def horas_de_turno(inicio, fin, noche_inicio, noche_fin, pausa_minutos=0):
    start = minutos(inicio)
    end = minutos(fin)
    if end <= start:
        end += 24 * 60
    pausa = 0 if not pausa_minutos else int(pausa_minutos)
    planificadas = (end - start - pausa) / 60
    ni = minutos(noche_inicio)
    nf = minutos(noche_fin)
    if nf < ni:
        franjas = [(ni, 24 * 60), (24 * 60, 24 * 60 + nf), (0, nf)]
    elif nf > ni:
        franjas = [(ni, nf), (ni + 24 * 60, nf + 24 * 60)]
    else:
        franjas = []
    nocturnas = 0
    for desde, hasta in franjas:
        nocturnas += max(0, min(end, hasta) - max(start, desde))
    return round(planificadas, 2), round(nocturnas / 60, 2)


def hora_texto(valor):
    if valor is None:
        return None
    return valor.strftime("%H:%M")


def parse_hora(valor):
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str):
        return "mal"
    texto = valor.strip()
    for formato in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(texto, formato).time()
        except ValueError:
            continue
    return "mal"
