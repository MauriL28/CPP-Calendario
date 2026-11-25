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
            cur.execute(
                """
                SELECT toneladas, detalle, fila_base
                FROM seguimiento_semana
                WHERE departamento_id = %s AND semana_inicio = %s
                """,
                (departamento_id, lunes),
            )
            fila = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    return jsonify(
        semana_inicio=lunes.isoformat(),
        toneladas=None if fila is None else float(fila["toneladas"]),
        detalle=None if fila is None else fila["detalle"],
        fila_base=None if fila is None else fila["fila_base"],
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
    toneladas = _toneladas(cuerpo.get("toneladas"))
    if toneladas is None:
        return jsonify(
            error="Las toneladas tienen que ser un número mayor o igual que cero, con hasta 2 decimales"
        ), 400
    if "detalle" in cuerpo:
        detalle, error = _detalle(cuerpo.get("detalle"))
        if error:
            return error
    else:
        detalle = None
    if "fila_base" in cuerpo:
        fila_base_nueva = cuerpo.get("fila_base")
    else:
        fila_base_nueva = None
    try:
        with cursor() as cur:
            departamento_id, error = _departamento(cur)
            if error:
                return error
            error = _exigir_marca(cur, departamento_id)
            if error:
                return error
            cur.execute(
                """
                SELECT detalle, fila_base
                FROM seguimiento_semana
                WHERE departamento_id = %s AND semana_inicio = %s
                """,
                (departamento_id, lunes),
            )
            anterior = cur.fetchone()
            if "detalle" not in cuerpo:
                detalle = None if anterior is None else anterior["detalle"]
            if "fila_base" not in cuerpo:
                fila_base = None if anterior is None else anterior["fila_base"]
            else:
                fila_base, error = _fila_base(fila_base_nueva, detalle)
                if error:
                    return error
            if fila_base is not None and "fila_base" not in cuerpo:
                nombres = [fila["nombre"] for fila in (detalle or {}).get("filas", [])]
                if fila_base not in nombres:
                    return jsonify(error="La fila base no está en el detalle"), 400
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
                    toneladas,
                    None if detalle is None else Json(detalle),
                    fila_base,
                    get_jwt_identity(),
                ),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    return jsonify(semana_inicio=lunes.isoformat(), toneladas=toneladas)


@bp.delete("/seguimiento")
@jwt_required()
def borrar_seguimiento():
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
            cur.execute(
                """
                DELETE FROM seguimiento_semana
                WHERE departamento_id = %s AND semana_inicio = %s
                """,
                (departamento_id, lunes),
            )
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return error_bd(exc)
    return "", 204
