from flask import jsonify


def departamento_lectura(cur, usuario_id, departamento_id_opcional):
    """Departamento del cuadrante. El propio si no llega departamento_id."""
    if departamento_id_opcional in (None, ""):
        cur.execute(
            """
            SELECT departamento_id
            FROM usuario
            WHERE id = %s AND rol = 'mando'
            """,
            (usuario_id,),
        )
        mando = cur.fetchone()
        if mando is None or mando["departamento_id"] is None:
            return None, (jsonify(error="No autorizado"), 403)
        return mando["departamento_id"], None
    if not departamento_permitido(cur, usuario_id, departamento_id_opcional):
        return None, (jsonify(error="No se ha encontrado el departamento"), 404)
    return departamento_id_opcional, None


def departamentos_del_mando(cur, usuario_id):
    """Ids de mando_departamento. Siempre incluye el departamento propio. [] si no es mando."""
    cur.execute(
        """
        SELECT rol, departamento_id
        FROM usuario
        WHERE id = %s
        """,
        (usuario_id,),
    )
    usuario = cur.fetchone()
    if usuario is None or usuario["rol"] != "mando":
        return []
    cur.execute(
        """
        SELECT departamento_id
        FROM mando_departamento
        WHERE usuario_id = %s
        """,
        (usuario_id,),
    )
    ids = [fila["departamento_id"] for fila in cur.fetchall()]
    propio = usuario["departamento_id"]
    if propio is not None and propio not in ids:
        ids.append(propio)
    return ids


def tiene_mando_activo(cur, departamento_id, excluir_login=None):
    """True si ese departamento ya tiene un mando activo, propio o enlazado.

    excluir_login no cuenta: sirve para reactivar a ese mismo mando.
    """
    cur.execute(
        """
        SELECT 1
        FROM usuario AS u
        WHERE u.rol = 'mando'
          AND u.activo
          AND (
            u.departamento_id = %s
            OR EXISTS (
                SELECT 1
                FROM mando_departamento AS m
                WHERE m.usuario_id = u.id
                  AND m.departamento_id = %s
            )
          )
          AND (CAST(%s AS text) IS NULL OR u.login IS DISTINCT FROM %s)
        LIMIT 1
        """,
        (departamento_id, departamento_id, excluir_login, excluir_login),
    )
    return cur.fetchone() is not None


def departamento_permitido(cur, usuario_id, departamento_id):
    if departamento_id is None:
        return False
    permitidos = {str(identificador) for identificador in departamentos_del_mando(cur, usuario_id)}
    return str(departamento_id) in permitidos
