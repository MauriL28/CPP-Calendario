import psycopg
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from rutas.usuarios import adjuntar_personas, listar_del_departamento

bp = Blueprint("departamentos", __name__)


@bp.get("/departamentos")
@jwt_required()
def departamentos():
    codigos = get_jwt().get("delegaciones")
    if not isinstance(codigos, list) or not codigos:
        return jsonify(error="Delegación no presente"), 401

    try:
        with cursor() as cur:
            filtro = ""
            params = [codigos]
            if get_jwt().get("rol") == "mando":
                cur.execute(
                    "SELECT departamento_id FROM usuario WHERE id = %s",
                    (get_jwt_identity(),),
                )
                propio = cur.fetchone()
                if propio is None or propio["departamento_id"] is None:
                    return jsonify(error="No autorizado"), 403
                filtro = "AND d.id = %s"
                params.append(propio["departamento_id"])
            cur.execute(
                f"""
                SELECT g.codigo AS delegacion, d.codigo, d.nombre, d.orden,
                       s.nombre AS seccion
                FROM departamento d
                JOIN delegacion g ON g.id = d.delegacion_id
                LEFT JOIN seccion s ON s.departamento_id = d.id
                WHERE g.codigo = ANY(%s)
                  {filtro}
                ORDER BY g.codigo = '60I' DESC, g.codigo, d.orden, s.nombre
                """,
                params,
            )
            filas = cur.fetchall()
            mandos, trabajadores, turnos = listar_del_departamento(cur, filtro, params)
    except SinBaseDeDatos:
        return jsonify(error="Base de datos no configurada"), 503
    except psycopg.Error as exc:
        return jsonify(error=str(exc)), 503

    lista = []
    por_codigo = {}
    for fila in filas:
        clave = (fila["delegacion"], fila["codigo"])
        item = por_codigo.get(clave)
        if item is None:
            item = {
                "delegacion": fila["delegacion"],
                "codigo": fila["codigo"],
                "nombre": fila["nombre"],
                "orden": fila["orden"],
                "secciones": [],
                "mandos": [],
                "trabajadores": [],
            }
            por_codigo[clave] = item
            lista.append(item)
        if fila["seccion"] is not None:
            item["secciones"].append({"nombre": fila["seccion"]})
    return jsonify(adjuntar_personas(lista, por_codigo, mandos, trabajadores, turnos))
