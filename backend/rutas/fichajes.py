import os
import tempfile
import zipfile
from datetime import datetime
from uuid import UUID

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from openpyxl.utils.exceptions import InvalidFileException

from db import SinBaseDeDatos, cursor
from fichajes import cargar

bp = Blueprint("fichajes", __name__)

LIMITE_BYTES = 10 * 1024 * 1024
MARGEN_MULTIPARTE = 1024 * 1024
ESTADOS = ("ok", "descuadre", "sin_plan", "sin_emparejar")


def _nombre(archivo):
    bruto = archivo.filename or ""
    return os.path.basename(bruto.replace("\\", "/")).strip()


@bp.post("/fichajes/importar")
@jwt_required()
def importar():
    if get_jwt().get("rol") != "admin":
        return jsonify(error="No autorizado"), 403

    archivos = [item for item in request.files.values() if item is not None]
    if len(archivos) != 1:
        return jsonify(error="Hay que enviar un solo archivo"), 400
    archivo = archivos[0]
    nombre = _nombre(archivo)
    if not nombre.lower().endswith(".xlsx"):
        return jsonify(error="El archivo tiene que ser .xlsx"), 400

    contenido = archivo.read(LIMITE_BYTES + 1)
    if len(contenido) > LIMITE_BYTES:
        return jsonify(error="El archivo supera 10 MiB"), 400

    temporal = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(contenido)
            temporal = tmp.name
        resultado = cargar(
            temporal,
            registro={
                "usuario_id": get_jwt_identity(),
                "nombre_archivo": nombre,
            },
        )
    except ValueError as exc:
        texto = str(exc).strip() or "El archivo no es un libro Excel válido"
        return jsonify(error=texto), 400
    except (InvalidFileException, zipfile.BadZipFile):
        return jsonify(error="El archivo no es un libro Excel válido"), 400
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503
    finally:
        if temporal and os.path.exists(temporal):
            os.remove(temporal)

    return jsonify(
        filas_leidas=resultado["filas_leidas"],
        emparejadas=resultado["filas_con_usuario"],
        sin_emparejar=resultado["sin_emparejar"],
        dias_con_incidencia=resultado["incidencias"],
        filas_nuevas=resultado["filas_nuevas"],
    )


def _fecha(texto):
    if texto is None or texto == "":
        return None
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        return False


def _numero(valor):
    if valor is None:
        return None
    return float(valor)


@bp.get("/fichajes/analisis")
@jwt_required()
def analisis():
    rol = get_jwt().get("rol")
    if rol not in ("admin", "mando"):
        return jsonify(error="No autorizado"), 403
    codigos = get_jwt().get("delegaciones")
    if not isinstance(codigos, list) or not codigos:
        return jsonify(error="Delegación no presente"), 401

    desde = _fecha(request.args.get("desde"))
    hasta = _fecha(request.args.get("hasta"))
    if desde is False or hasta is False:
        return jsonify(error="La fecha no es válida"), 400
    if desde is not None and hasta is not None and desde > hasta:
        return jsonify(error="desde no puede ser posterior a hasta"), 400

    estado = request.args.get("coincide") or ""
    if estado and estado not in ESTADOS:
        return jsonify(error="coincide no es válido"), 400

    departamento = request.args.get("departamento_id") or ""
    if rol == "admin" and departamento:
        try:
            UUID(departamento)
        except ValueError:
            return jsonify(error="departamento_id no es válido"), 400

    try:
        with cursor() as cur:
            if rol == "mando":
                cur.execute(
                    "SELECT departamento_id FROM usuario WHERE id = %s",
                    (get_jwt_identity(),),
                )
                propio = cur.fetchone()
                if propio is None or propio["departamento_id"] is None:
                    return jsonify(error="No autorizado"), 403
                departamento = str(propio["departamento_id"])
            elif departamento:
                cur.execute(
                    """
                    SELECT d.id
                    FROM departamento d
                    JOIN delegacion g ON g.id = d.delegacion_id
                    WHERE d.id = %s
                      AND g.codigo = ANY(%s)
                    """,
                    (departamento, codigos),
                )
                if cur.fetchone() is None:
                    return jsonify(error="No autorizado"), 403

            clausulas = ["f.coincide IS NOT NULL"]
            params = []
            if rol == "mando" or departamento:
                clausulas.append("u.departamento_id = %s")
                params.append(departamento)
            else:
                clausulas.append("(f.usuario_id IS NULL OR g.codigo = ANY(%s))")
                params.append(codigos)
            if estado:
                clausulas.append("f.coincide = %s")
                params.append(estado)
            if desde is not None:
                clausulas.append("f.fecha >= %s")
                params.append(desde)
            if hasta is not None:
                clausulas.append("f.fecha <= %s")
                params.append(hasta)
            donde = " AND ".join(clausulas)
            cur.execute(
                f"""
                SELECT
                    CASE
                        WHEN f.usuario_id IS NULL THEN f.numero_sap
                        ELSE u.nombre
                    END AS nombre,
                    CASE
                        WHEN f.usuario_id IS NULL THEN NULL
                        ELSE d.nombre
                    END AS departamento,
                    f.fecha,
                    f.horas_planificadas,
                    f.horas_trabajadas,
                    f.horas_pausa,
                    CASE
                        WHEN f.horas_planificadas IS NULL THEN NULL
                        ELSE f.horas_trabajadas - f.horas_planificadas
                    END AS diferencia,
                    f.coincide::text AS coincide
                FROM fichaje f
                LEFT JOIN usuario u ON u.id = f.usuario_id
                LEFT JOIN departamento d ON d.id = u.departamento_id
                LEFT JOIN delegacion g ON g.id = d.delegacion_id
                WHERE {donde}
                ORDER BY f.fecha, nombre
                """,
                params,
            )
            filas = [
                {
                    "nombre": fila["nombre"],
                    "departamento": fila["departamento"],
                    "fecha": fila["fecha"].isoformat(),
                    "horas_planificadas": _numero(fila["horas_planificadas"]),
                    "horas_trabajadas": _numero(fila["horas_trabajadas"]),
                    "horas_pausa": _numero(fila["horas_pausa"]),
                    "diferencia": _numero(fila["diferencia"]),
                    "coincide": fila["coincide"],
                }
                for fila in cur.fetchall()
            ]
            cur.execute(
                f"""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE f.coincide = 'ok') AS ok,
                    COUNT(*) FILTER (WHERE f.coincide = 'descuadre') AS descuadre,
                    COUNT(*) FILTER (WHERE f.coincide = 'sin_plan') AS sin_plan,
                    COUNT(*) FILTER (WHERE f.coincide = 'sin_emparejar') AS sin_emparejar
                FROM fichaje f
                LEFT JOIN usuario u ON u.id = f.usuario_id
                LEFT JOIN departamento d ON d.id = u.departamento_id
                LEFT JOIN delegacion g ON g.id = d.delegacion_id
                WHERE {donde}
                """,
                params,
            )
            totales = cur.fetchone()
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    return jsonify(
        filas=filas,
        totales={
            "total": totales["total"],
            "ok": totales["ok"],
            "descuadre": totales["descuadre"],
            "sin_plan": totales["sin_plan"],
            "sin_emparejar": totales["sin_emparejar"],
        },
    )
