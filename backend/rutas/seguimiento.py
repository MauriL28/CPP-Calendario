import math
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from psycopg.types.json import Json

from db import SinBaseDeDatos, cursor
from errores import error_bd
from mandos import departamento_lectura

bp = Blueprint("seguimiento", __name__)


def _lunes(texto):
    if texto in (None, ""):
        return None, (jsonify(error="Faltan datos"), 400)
    try:
        fecha = datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None, (jsonify(error="La fecha no es válida"), 400)
    return fecha - timedelta(days=fecha.weekday()), None


def _toneladas(valor):
    if isinstance(valor, bool) or valor is None or valor == "":
        return None
    if isinstance(valor, str):
        texto = valor.strip().replace(",", ".")
        if not texto:
            return None
        try:
            cantidad = Decimal(texto)
        except InvalidOperation:
            return None
    elif isinstance(valor, int):
        cantidad = Decimal(valor)
    elif isinstance(valor, float):
        cantidad = Decimal(str(valor))
    else:
        return None
    if not cantidad.is_finite() or cantidad < 0 or cantidad.as_tuple().exponent < -2:
        return None
    return float(cantidad)


def _kilos(valor):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    if isinstance(valor, float) and (not math.isfinite(valor) or not valor.is_integer()):
        return None
    if valor < 0:
        return None
    return int(valor)


def _detalle(valor):
    if not isinstance(valor, dict) or not isinstance(valor.get("filas"), list):
        return None, (jsonify(error="El detalle no es válido"), 400)
    if len(valor["filas"]) > 10:
        return None, (jsonify(error="El detalle admite como máximo 10 filas"), 400)
    filas = []
    for cruda in valor["filas"]:
        if not isinstance(cruda, dict):
            return None, (jsonify(error="El detalle no es válido"), 400)
        nombre = cruda.get("nombre")
        if not isinstance(nombre, str) or not nombre.strip() or len(nombre.strip()) > 60:
            return None, (jsonify(error="Cada fila necesita un nombre de hasta 60 caracteres"), 400)
        dias = cruda.get("dias")
        if not isinstance(dias, list) or len(dias) != 6:
            return None, (jsonify(error="Cada fila tiene que traer 6 días, de lunes a sábado"), 400)
        kilos = [_kilos(dia) for dia in dias]
        total = _kilos(cruda.get("total"))
        if total is None or any(dia is None for dia in kilos):
            return None, (
                jsonify(error="Los kilos tienen que ser números enteros mayores o iguales que cero"),
                400,
            )
        filas.append({"nombre": nombre.strip(), "total": total, "dias": kilos})
    return {"filas": filas}, None


def _fila_base(valor, detalle):
    if not isinstance(valor, str) or not valor.strip() or len(valor.strip()) > 60:
        return None, (jsonify(error="La fila base no es válida"), 400)
    nombre = valor.strip()
    nombres = [fila["nombre"] for fila in (detalle or {}).get("filas", [])]
    if nombre not in nombres:
        return None, (jsonify(error="La fila base no está en el detalle"), 400)
    return nombre, None


def _magnitud(valor, por_defecto):
    if valor in (None, ""):
        return por_defecto, None
    if valor not in ("toneladas", "pales"):
        return None, (jsonify(error="La magnitud no es válida"), 400)
    return valor, None


def _combinar_detalle(cuerpo, anterior, columna_detalle, columna_fila):
    if "detalle" in cuerpo:
        detalle, error = _detalle(cuerpo.get("detalle"))
        if error:
            return None, None, error
    else:
        detalle = None if anterior is None else anterior[columna_detalle]
    if "fila_base" not in cuerpo:
        fila_base = None if anterior is None else anterior[columna_fila]
        if fila_base is not None:
            nombres = [fila["nombre"] for fila in (detalle or {}).get("filas", [])]
            if fila_base not in nombres:
                return None, None, (jsonify(error="La fila base no está en el detalle"), 400)
        return detalle, fila_base, None
    fila_base, error = _fila_base(cuerpo.get("fila_base"), detalle)
    if error:
        return None, None, error
    return detalle, fila_base, None


def _numero(fila, campo):
    if fila is None or fila[campo] is None:
        return None
    return float(fila[campo])


_LECTURA = """
    SELECT toneladas, detalle, fila_base, pales, detalle_pales, fila_base_pales
    FROM seguimiento_semana
    WHERE departamento_id = %s AND semana_inicio = %s
"""


def _departamento(cur):
    opcional = request.args.get("departamento_id")
    if request.method == "PUT":
        cuerpo = request.get_json(silent=True) or {}
        if "departamento_id" in cuerpo:
            opcional = cuerpo.get("departamento_id")
    return departamento_lectura(cur, get_jwt_identity(), opcional)


def _exigir_marca(cur, departamento_id):
    cur.execute(
        "SELECT usa_seguimiento FROM departamento WHERE id = %s",
        (departamento_id,),
    )
    fila = cur.fetchone()
    if fila is None or not fila["usa_seguimiento"]:
        return jsonify(error="Este departamento no tiene seguimiento"), 404
    return None


@bp.get("/seguimiento")
@jwt_required()
def leer_seguimiento():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403
    lunes, error = _lunes(request.args.get("semana"))
    if error:
        return error
    try:
        with cursor() as cur:
            departamento_id, error = _departamento(cur)
            if error:
                return error
            error = _exigir_marca(cur, departamento_id)
            if error:
                return error
            cur.execute(_LECTURA, (departamento_id, lunes))
            fila = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    return jsonify(
        semana_inicio=lunes.isoformat(),
        toneladas=_numero(fila, "toneladas"),
        detalle=None if fila is None else fila["detalle"],
        fila_base=None if fila is None else fila["fila_base"],
        pales=_numero(fila, "pales"),
        detalle_pales=None if fila is None else fila["detalle_pales"],
        fila_base_pales=None if fila is None else fila["fila_base_pales"],
    )


@bp.put("/seguimiento")
@jwt_required()
def guardar_seguimiento():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403
    cuerpo = request.get_json(silent=True) or {}
    lunes, error = _lunes(cuerpo.get("semana"))
    if error:
        return error
    magnitud, error = _magnitud(cuerpo.get("magnitud"), "toneladas")
    if error:
        return error
    if magnitud == "pales":
        cantidad = _toneladas(cuerpo.get("pales"))
        if cantidad is None:
            return jsonify(
                error="Los pales tienen que ser un número mayor o igual que cero, con hasta 2 decimales"
            ), 400
    else:
        cantidad = _toneladas(cuerpo.get("toneladas"))
        if cantidad is None:
            return jsonify(
                error="Las toneladas tienen que ser un número mayor o igual que cero, con hasta 2 decimales"
            ), 400
    try:
        with cursor() as cur:
            departamento_id, error = _departamento(cur)
            if error:
                return error
            error = _exigir_marca(cur, departamento_id)
            if error:
                return error
            cur.execute(_LECTURA, (departamento_id, lunes))
            anterior = cur.fetchone()
            if magnitud == "pales":
                detalle, fila_base, error = _combinar_detalle(
                    cuerpo, anterior, "detalle_pales", "fila_base_pales"
                )
            else:
                detalle, fila_base, error = _combinar_detalle(
                    cuerpo, anterior, "detalle", "fila_base"
                )
            if error:
                return error
            if magnitud == "pales":
                cur.execute(
                    """
                    INSERT INTO seguimiento_semana (
                        departamento_id, semana_inicio, pales, detalle_pales,
                        fila_base_pales, actualizado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (departamento_id, semana_inicio)
                    DO UPDATE SET pales = EXCLUDED.pales,
                                  detalle_pales = EXCLUDED.detalle_pales,
                                  fila_base_pales = EXCLUDED.fila_base_pales,
                                  actualizado_por = EXCLUDED.actualizado_por,
                                  actualizado_en = now()
                    """,
                    (
                        departamento_id,
                        lunes,
                        cantidad,
                        None if detalle is None else Json(detalle),
                        fila_base,
                        get_jwt_identity(),
                    ),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO seguimiento_semana (
                        departamento_id, semana_inicio, toneladas, detalle, fila_base, actualizado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (departamento_id, semana_inicio)
                    DO UPDATE SET toneladas = EXCLUDED.toneladas,
                                  detalle = EXCLUDED.detalle,
                                  fila_base = EXCLUDED.fila_base,
                                  actualizado_por = EXCLUDED.actualizado_por,
                                  actualizado_en = now()
                    """,
                    (
                        departamento_id,
                        lunes,
                        cantidad,
                        None if detalle is None else Json(detalle),
                        fila_base,
                        get_jwt_identity(),
                    ),
                )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    if magnitud == "pales":
        return jsonify(semana_inicio=lunes.isoformat(), pales=cantidad)
    return jsonify(semana_inicio=lunes.isoformat(), toneladas=cantidad)


@bp.delete("/seguimiento")
@jwt_required()
def borrar_seguimiento():
    if get_jwt().get("rol") not in ("mando", "admin"):
        return jsonify(error="No autorizado"), 403
    lunes, error = _lunes(request.args.get("semana"))
    if error:
        return error
    magnitud, error = _magnitud(request.args.get("magnitud"), "ambas")
    if error:
        return error
    try:
        with cursor() as cur:
            departamento_id, error = _departamento(cur)
            if error:
                return error
            error = _exigir_marca(cur, departamento_id)
            if error:
                return error
            if magnitud == "ambas":
                cur.execute(
                    """
                    DELETE FROM seguimiento_semana
                    WHERE departamento_id = %s AND semana_inicio = %s
                    """,
                    (departamento_id, lunes),
                )
            else:
                columnas = (
                    "toneladas = NULL, detalle = NULL, fila_base = NULL"
                    if magnitud == "toneladas"
                    else "pales = NULL, detalle_pales = NULL, fila_base_pales = NULL"
                )
                cur.execute(
                    f"""
                    UPDATE seguimiento_semana
                    SET {columnas},
                        actualizado_por = %s,
                        actualizado_en = now()
                    WHERE departamento_id = %s AND semana_inicio = %s
                    """,
                    (get_jwt_identity(), departamento_id, lunes),
                )
                cur.execute(
                    """
                    DELETE FROM seguimiento_semana
                    WHERE departamento_id = %s AND semana_inicio = %s
                      AND toneladas IS NULL
                      AND pales IS NULL
                    """,
                    (departamento_id, lunes),
                )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    return "", 204
