from datetime import datetime


def minutos(valor):
    return valor.hour * 60 + valor.minute


def horas_de_turno(inicio, fin, noche_inicio, noche_fin):
    start = minutos(inicio)
    end = minutos(fin)
    if end <= start:
        end += 24 * 60
    planificadas = (end - start) / 60
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
