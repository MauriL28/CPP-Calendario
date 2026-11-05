from datetime import date, datetime

from flask import jsonify

import validaciones
from horas import horas_de_turno
from validaciones import comprobar_seccion, sap_ocupado

CAMPOS_COMUNES = {"nombre", "numero_sap", "clave"}
CAMPOS_TRABAJADOR = {
    "grupo",
    "vacaciones",
    "horas_contrato",
    "horas_convenio",
    "pausa_minutos",
    "seccion_id",
}
CAMPOS_USUARIO = CAMPOS_COMUNES | CAMPOS_TRABAJADOR
ORDEN_USUARIO = (
    "nombre",
    "numero_sap",
    "clave",
    "grupo",
    "vacaciones",
    "horas_contrato",
    "horas_convenio",
    "pausa_minutos",
    "seccion_id",
)


def campos_desconocidos(cuerpo):
    return any(clave not in CAMPOS_USUARIO for clave in cuerpo)


def editar_campos(cur, persona, cuerpo):
    if persona["rol"] == "mando" and any(clave in CAMPOS_TRABAJADOR for clave in cuerpo):
        return None, (jsonify(error="Campo no permitido"), 400)
    cambios, error = _cambios_usuario(cuerpo)
    if error:
        return None, error
    if "seccion_id" in cambios:
        error = comprobar_seccion(cur, persona["departamento_id"], cambios["seccion_id"])
        if error:
            return None, error
    if "numero_sap" in cuerpo and sap_ocupado(cur, cambios["numero_sap"], persona["id"]):
        return None, (jsonify(error="Ese número de personal ya está asignado a otra persona"), 409)
    if cambios:
        _guardar_usuario(cur, persona["id"], cambios)
    if "pausa_minutos" in cambios:
        _recalcular_planificadas(cur, persona["id"], cambios["pausa_minutos"])
    return _respuesta_usuario(cambios), None


def _cambios_usuario(cuerpo):
    cambios = {}
    if "nombre" in cuerpo:
        nombre = cuerpo["nombre"]
        if not isinstance(nombre, str) or not nombre.strip():
            return None, (jsonify(error="Faltan datos"), 400)
        nombre = nombre.strip()
        if len(nombre) > 100:
            return None, (jsonify(error="El nombre es demasiado largo"), 400)
        cambios["nombre"] = nombre
    if "numero_sap" in cuerpo:
        numero, error = validaciones.numero_sap(cuerpo["numero_sap"])
        if error:
            return None, error
        cambios["numero_sap"] = numero
    if "clave" in cuerpo:
        clave = cuerpo["clave"]
        if not isinstance(clave, str) or not clave.strip():
            return None, (jsonify(error="Faltan datos"), 400)
        cambios["clave"] = clave
    if "grupo" in cuerpo:
        error = validaciones.grupo_valido(cuerpo["grupo"])
        if error:
            return None, error
        cambios["grupo"] = cuerpo["grupo"]
    for campo in ("vacaciones", "horas_contrato"):
        if campo not in cuerpo:
            continue
        valor = validaciones.numero(cuerpo[campo])
        if valor is None or valor == "mal":
            return None, (jsonify(error="Faltan datos"), 400)
        cambios[campo] = valor
    if "horas_convenio" in cuerpo:
        valor = validaciones.numero(cuerpo["horas_convenio"])
        if valor == "mal":
            return None, (jsonify(error="Faltan datos"), 400)
        cambios["horas_convenio"] = valor
    if "pausa_minutos" in cuerpo:
        valor = validaciones.pausa_minutos(cuerpo["pausa_minutos"])
        if valor is None:
            return None, (jsonify(error="La pausa tiene que ser 0, 30 o 60"), 400)
        cambios["pausa_minutos"] = valor
    if "seccion_id" in cuerpo:
        seccion_id, error = validaciones.leer_seccion_id(cuerpo, opcional=False)
        if error:
            return None, error
        cambios["seccion_id"] = seccion_id
    return cambios, None


def _guardar_usuario(cur, usuario_id, cambios):
    columnas = []
    params = []
    for campo in ORDEN_USUARIO:
        if campo not in cambios:
            continue
        if campo == "clave":
            columnas.append("clave = crypt(%s, gen_salt('bf'))")
        else:
            columnas.append(f"{campo} = %s")
        params.append(cambios[campo])
    params.append(usuario_id)
    cur.execute(
        f"UPDATE usuario SET {', '.join(columnas)} WHERE id = %s",
        tuple(params),
    )


def _recalcular_planificadas(cur, usuario_id, pausa):
    cur.execute("SELECT noche_inicio, noche_fin FROM empresa WHERE id = 1")
    franja = cur.fetchone()
    if franja is None:
        noche_inicio = datetime.strptime("22:00", "%H:%M").time()
        noche_fin = datetime.strptime("06:00", "%H:%M").time()
    else:
        noche_inicio = franja["noche_inicio"]
        noche_fin = franja["noche_fin"]
    cur.execute(
        """
        SELECT fecha, hora_inicio, hora_fin
        FROM turno
        WHERE usuario_id = %s
          AND fecha >= %s
          AND hora_inicio IS NOT NULL
          AND hora_fin IS NOT NULL
        """,
        (usuario_id, date.today()),
    )
    for fila in cur.fetchall():
        planificadas, _nocturnas = horas_de_turno(
            fila["hora_inicio"],
            fila["hora_fin"],
            noche_inicio,
            noche_fin,
            pausa,
        )
        cur.execute(
            """
            UPDATE turno
            SET horas_planificadas = %s
            WHERE usuario_id = %s AND fecha = %s
            """,
            (planificadas, usuario_id, fila["fecha"]),
        )


def _respuesta_usuario(cambios):
    visible = {campo: valor for campo, valor in cambios.items() if campo != "clave"}
    if visible.get("seccion_id") is not None:
        visible["seccion_id"] = str(visible["seccion_id"])
    return visible
