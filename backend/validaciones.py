from decimal import Decimal, InvalidOperation
from uuid import UUID

from flask import jsonify

from errores import error_bd


def numero_sap(valor):
    if valor is None or valor == "":
        return None, None
    if not isinstance(valor, str):
        return None, (jsonify(error="Faltan datos"), 400)
    texto = valor.strip()
    if not texto:
        return None, None
    if len(texto) > 40:
        return None, (jsonify(error="El número de personal es demasiado largo"), 400)
    return texto, None


def sap_ocupado(cur, numero, excepto_id=None):
    if numero is None:
        return False
    cur.execute(
        """
        SELECT 1
        FROM usuario
        WHERE numero_sap = %s
          AND id IS DISTINCT FROM %s
        """,
        (numero, excepto_id),
    )
    return cur.fetchone() is not None


def error_unico(exc):
    if getattr(exc.diag, "constraint_name", None) == "usuario_numero_sap":
        return jsonify(error="Ese número de personal ya está asignado a otra persona"), 409
    return error_bd(exc)


def coste_hora(valor):
    """Coste por hora. None si viene vacío. 'mal' si no es un número válido."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return "mal"
    if isinstance(valor, str):
        texto = valor.strip().replace(",", ".")
        if not texto:
            return None
        try:
            cantidad = Decimal(texto)
        except InvalidOperation:
            return "mal"
    elif isinstance(valor, int):
        cantidad = Decimal(valor)
    elif isinstance(valor, float):
        cantidad = Decimal(str(valor))
    else:
        return "mal"
    if not cantidad.is_finite() or cantidad < 0 or cantidad.as_tuple().exponent < -4:
        return "mal"
    return float(cantidad)


def grupo_valido(valor):
    if valor not in ("STEF", "ETT"):
        return jsonify(error="El grupo tiene que ser STEF o ETT"), 400
    return None


def leer_seccion_id(cuerpo, opcional):
    if "seccion_id" not in cuerpo:
        if opcional:
            return None, None
        return None, (jsonify(error="Faltan datos"), 400)
    valor = cuerpo.get("seccion_id")
    if valor is None:
        return None, None
    if not isinstance(valor, str) or not valor.strip():
        return None, (jsonify(error="La sección no es válida"), 400)
    try:
        return UUID(valor.strip()), None
    except ValueError:
        return None, (jsonify(error="La sección no es válida"), 400)


def comprobar_seccion(cur, departamento_id, seccion_id):
    if seccion_id is None:
        return None
    cur.execute(
        "SELECT 1 FROM seccion WHERE departamento_id = %s LIMIT 1",
        (departamento_id,),
    )
    if cur.fetchone() is None:
        return jsonify(error="Este departamento no tiene secciones"), 400
    cur.execute(
        """
        SELECT 1
        FROM seccion
        WHERE id = %s AND departamento_id = %s
        """,
        (seccion_id, departamento_id),
    )
    if cur.fetchone() is None:
        return jsonify(error="La sección no es de tu departamento"), 400
    return None


def pausa_minutos(valor):
    if isinstance(valor, bool):
        return None
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto.isdigit():
            return None
        valor = int(texto)
    elif isinstance(valor, float):
        if not valor.is_integer():
            return None
        valor = int(valor)
    if isinstance(valor, int) and valor in (0, 30, 60):
        return valor
    return None


def numero(valor):
    if isinstance(valor, bool) or valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        if valor < 0:
            return "mal"
        return float(valor)
    if isinstance(valor, str):
        try:
            numero = float(valor.strip().replace(",", "."))
        except ValueError:
            return "mal"
        if numero < 0:
            return "mal"
        return numero
    return "mal"
