import os
import tempfile
import zipfile

import psycopg
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from openpyxl.utils.exceptions import InvalidFileException

from db import SinBaseDeDatos
from fichajes import cargar

bp = Blueprint("fichajes", __name__)

LIMITE_BYTES = 10 * 1024 * 1024
MARGEN_MULTIPARTE = 1024 * 1024


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
