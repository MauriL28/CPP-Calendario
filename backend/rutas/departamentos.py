import psycopg
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from db import SinBaseDeDatos, cursor
from mandos import departamentos_del_mando
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
            propio_id = None
            orden = "g.codigo = '60I' DESC, g.codigo, d.orden, s.nombre"
            if get_jwt().get("rol") == "mando":
                yo = get_jwt_identity()
                ids = departamentos_del_mando(cur, yo)
                if not ids:
                    return jsonify(error="No autorizado"), 403
                cur.execute(
                    "SELECT departamento_id FROM usuario WHERE id = %s",
                    (yo,),
                )
                propio = cur.fetchone()
                propio_id = propio["departamento_id"] if propio else None
                cur.execute(
                    """
                    SELECT DISTINCT g.codigo
                    FROM departamento d
                    JOIN delegacion g ON g.id = d.delegacion_id
                    WHERE d.id = ANY(%s)
                    """,
                    (ids,),
                )
                params = [[fila["codigo"] for fila in cur.fetchall()], ids]
                filtro = "AND d.id = ANY(%s)"
                if propio_id is not None:
                    orden = "(d.id = %s) DESC, " + orden
            cur.execute(
                f"""
                SELECT g.codigo AS delegacion, d.id, d.codigo, d.nombre, d.orden,
                       d.usa_horario_habitual,
                       s.id AS seccion_id, s.nombre AS seccion
                FROM departamento d
                JOIN delegacion g ON g.id = d.delegacion_id
                LEFT JOIN seccion s ON s.departamento_id = d.id
                WHERE g.codigo = ANY(%s)
                  {filtro}
                ORDER BY {orden}
                """,
                params + ([propio_id] if filtro and propio_id is not None else []),
            )
            filas = cur.fetchall()
            mandos, trabajadores, turnos, horarios = listar_del_departamento(cur, filtro, params)
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
                "id": str(fila["id"]),
                "delegacion": fila["delegacion"],
                "codigo": fila["codigo"],
                "nombre": fila["nombre"],
                "orden": fila["orden"],
                "usa_horario_habitual": fila["usa_horario_habitual"],
                "secciones": [],
                "mandos": [],
                "trabajadores": [],
            }
            por_codigo[clave] = item
            lista.append(item)
        if fila["seccion"] is not None:
            item["secciones"].append({"id": str(fila["seccion_id"]), "nombre": fila["seccion"]})
    return jsonify(adjuntar_personas(lista, por_codigo, mandos, trabajadores, turnos, horarios))
