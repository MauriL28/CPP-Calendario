import os
from datetime import datetime

import psycopg
from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, get_jwt, get_jwt_identity, jwt_required
from psycopg.rows import dict_row


AUSENCIAS = {"L", "D", "V", "B", "F", "P"}


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


def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "dev-calendario")
    JWTManager(app)

    def database_url():
        return os.environ.get("DATABASE_URL")

    @app.get("/health")
    def health():
        url = database_url()
        if not url:
            return jsonify(status="ok", database="unconfigured")
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        except psycopg.Error:
            return jsonify(status="degraded", database="down"), 503
        return jsonify(status="ok", database="up")

    @app.get("/departamentos")
    @jwt_required()
    def departamentos():
        codigos = get_jwt().get("delegaciones")
        if not isinstance(codigos, list) or not codigos:
            return jsonify(error="Delegación no presente"), 401
        url = database_url()
        if not url:
            return jsonify(error="Base de datos no configurada"), 503
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
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
                    cur.execute(
                        f"""
                        SELECT g.codigo AS delegacion, d.codigo AS departamento,
                               u.nombre, u.login
                        FROM usuario u
                        JOIN departamento d ON d.id = u.departamento_id
                        JOIN delegacion g ON g.id = d.delegacion_id
                        WHERE u.rol = 'mando'
                          AND g.codigo = ANY(%s)
                          {filtro}
                        ORDER BY u.nombre
                        """,
                        params,
                    )
                    mandos = cur.fetchall()
                    cur.execute(
                        f"""
                        SELECT g.codigo AS delegacion, d.codigo AS departamento,
                               u.nombre, u.login, u.grupo
                        FROM usuario u
                        JOIN departamento d ON d.id = u.departamento_id
                        JOIN delegacion g ON g.id = d.delegacion_id
                        WHERE u.rol = 'trabajador'
                          AND g.codigo = ANY(%s)
                          {filtro}
                        ORDER BY u.nombre
                        """,
                        params,
                    )
                    trabajadores = cur.fetchall()
                    cur.execute(
                        f"""
                        SELECT u.login, t.fecha, t.ausencia::text AS ausencia,
                               t.hora_inicio, t.hora_fin,
                               t.horas_planificadas, t.horas_nocturnas
                        FROM turno t
                        JOIN usuario u ON u.id = t.usuario_id
                        JOIN departamento d ON d.id = u.departamento_id
                        JOIN delegacion g ON g.id = d.delegacion_id
                        WHERE u.rol = 'trabajador'
                          AND g.codigo = ANY(%s)
                          {filtro}
                        ORDER BY t.fecha
                        """,
                        params,
                    )
                    turnos = cur.fetchall()
        except psycopg.Error as exc:
            return jsonify(error=str(exc)), 503

        departamentos = []
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
                departamentos.append(item)
            if fila["seccion"] is not None:
                item["secciones"].append({"nombre": fila["seccion"]})
        for mando in mandos:
            item = por_codigo.get((mando["delegacion"], mando["departamento"]))
            if item is not None:
                item["mandos"].append({"nombre": mando["nombre"], "login": mando["login"]})
        por_login = {}
        for trabajador in trabajadores:
            item = por_codigo.get((trabajador["delegacion"], trabajador["departamento"]))
            if item is None:
                continue
            persona = {
                "nombre": trabajador["nombre"],
                "login": trabajador["login"],
                "grupo": trabajador["grupo"],
                "turnos": [],
            }
            por_login[trabajador["login"]] = persona
            item["trabajadores"].append(persona)
        for turno in turnos:
            persona = por_login.get(turno["login"])
            if persona is None:
                continue
            persona["turnos"].append(
                {
                    "fecha": turno["fecha"].isoformat(),
                    "ausencia": turno["ausencia"],
                    "hora_inicio": hora_texto(turno["hora_inicio"]),
                    "hora_fin": hora_texto(turno["hora_fin"]),
                    "horas_planificadas": float(turno["horas_planificadas"]),
                    "horas_nocturnas": float(turno["horas_nocturnas"]),
                }
            )
        return jsonify(departamentos)

    @app.post("/login")
    def login():
        cuerpo = request.get_json(silent=True) or {}
        login_nombre = cuerpo.get("login")
        clave = cuerpo.get("clave")
        if not isinstance(login_nombre, str) or not isinstance(clave, str):
            return jsonify(error="Credenciales incorrectas"), 401

        url = database_url()
        if not url:
            return jsonify(error="Base de datos no configurada"), 503
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT u.id, u.rol, g.codigo AS delegacion
                        FROM usuario u
                        LEFT JOIN departamento d ON d.id = u.departamento_id
                        LEFT JOIN delegacion g ON g.id = d.delegacion_id
                        WHERE u.login = %s
                          AND u.clave IS NOT NULL
                          AND u.clave = crypt(%s, u.clave)
                        """,
                        (login_nombre, clave),
                    )
                    fila = cur.fetchone()
                    if fila is None:
                        return jsonify(error="Credenciales incorrectas"), 401
                    if fila["rol"] == "admin":
                        cur.execute(
                            """
                            SELECT codigo
                            FROM delegacion
                            ORDER BY codigo = '60I' DESC, codigo
                            """
                        )
                        delegaciones = [row["codigo"] for row in cur.fetchall()]
                    elif fila["delegacion"]:
                        delegaciones = [fila["delegacion"]]
                    else:
                        return jsonify(error="Credenciales incorrectas"), 401
        except psycopg.Error as exc:
            return jsonify(error=str(exc)), 503

        token = create_access_token(
            identity=str(fila["id"]),
            additional_claims={"rol": fila["rol"], "delegaciones": delegaciones},
        )
        return jsonify(access_token=token)

    @app.post("/usuarios")
    @jwt_required()
    def crear_usuario():
        if get_jwt().get("rol") != "admin":
            return jsonify(error="No autorizado"), 403

        cuerpo = request.get_json(silent=True) or {}
        nombre = cuerpo.get("nombre")
        login_nombre = cuerpo.get("login")
        clave = cuerpo.get("clave")
        delegacion = cuerpo.get("delegacion")
        departamento = cuerpo.get("departamento")
        campos = (nombre, login_nombre, clave, delegacion, departamento)
        if not all(isinstance(valor, str) and valor.strip() for valor in campos):
            return jsonify(error="Faltan datos"), 400

        url = database_url()
        if not url:
            return jsonify(error="Base de datos no configurada"), 503
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT d.id
                        FROM departamento d
                        JOIN delegacion g ON g.id = d.delegacion_id
                        WHERE g.codigo = %s AND d.codigo = %s
                        """,
                        (delegacion.strip(), departamento.strip()),
                    )
                    depto = cur.fetchone()
                    if depto is None:
                        return jsonify(
                            error=f"No hay departamento {departamento.strip()} en la delegación {delegacion.strip()}"
                        ), 404
                    cur.execute(
                        "SELECT 1 FROM usuario WHERE login = %s",
                        (login_nombre.strip(),),
                    )
                    if cur.fetchone() is not None:
                        return jsonify(error="El login ya existe"), 409
                    cur.execute(
                        """
                        INSERT INTO usuario (nombre, login, clave, rol, departamento_id)
                        VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'mando', %s)
                        RETURNING nombre, login, rol
                        """,
                        (nombre.strip(), login_nombre.strip(), clave, depto["id"]),
                    )
                    creado = cur.fetchone()
        except psycopg.Error as exc:
            return jsonify(error=str(exc)), 503

        return jsonify(
            nombre=creado["nombre"],
            login=creado["login"],
            rol=creado["rol"],
            delegacion=delegacion.strip(),
            departamento=departamento.strip(),
        ), 201

    @app.post("/trabajadores")
    @jwt_required()
    def crear_trabajador():
        if get_jwt().get("rol") != "mando":
            return jsonify(error="No autorizado"), 403

        cuerpo = request.get_json(silent=True) or {}
        nombre = cuerpo.get("nombre")
        login_nombre = cuerpo.get("login")
        clave = cuerpo.get("clave")
        grupo = cuerpo.get("grupo")
        if not all(isinstance(valor, str) and valor.strip() for valor in (nombre, login_nombre, clave)):
            return jsonify(error="Faltan datos"), 400
        if grupo not in ("STEF", "ETT"):
            return jsonify(error="El grupo tiene que ser STEF o ETT"), 400

        url = database_url()
        if not url:
            return jsonify(error="Base de datos no configurada"), 503
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT departamento_id
                        FROM usuario
                        WHERE id = %s AND rol = 'mando'
                        """,
                        (get_jwt_identity(),),
                    )
                    mando = cur.fetchone()
                    if mando is None or mando["departamento_id"] is None:
                        return jsonify(error="No autorizado"), 403
                    cur.execute(
                        "SELECT 1 FROM usuario WHERE login = %s",
                        (login_nombre.strip(),),
                    )
                    if cur.fetchone() is not None:
                        return jsonify(error="El login ya existe"), 409
                    cur.execute(
                        """
                        INSERT INTO usuario (nombre, login, clave, rol, grupo, departamento_id)
                        VALUES (%s, %s, crypt(%s, gen_salt('bf')), 'trabajador', %s, %s)
                        RETURNING nombre, login, rol, grupo
                        """,
                        (
                            nombre.strip(),
                            login_nombre.strip(),
                            clave,
                            grupo,
                            mando["departamento_id"],
                        ),
                    )
                    creado = cur.fetchone()
        except psycopg.Error as exc:
            return jsonify(error=str(exc)), 503

        return jsonify(
            nombre=creado["nombre"],
            login=creado["login"],
            rol=creado["rol"],
            grupo=creado["grupo"],
        ), 201

    @app.put("/turnos")
    @jwt_required()
    def guardar_turno():
        if get_jwt().get("rol") != "mando":
            return jsonify(error="No autorizado"), 403

        cuerpo = request.get_json(silent=True) or {}
        login_nombre = cuerpo.get("login")
        fecha_texto = cuerpo.get("fecha")
        ausencia = cuerpo.get("ausencia")
        if ausencia == "":
            ausencia = None
        hora_inicio = _parse_hora(cuerpo.get("hora_inicio"))
        hora_fin = _parse_hora(cuerpo.get("hora_fin"))
        if hora_inicio == "mal" or hora_fin == "mal":
            return jsonify(error="La hora no es válida"), 400
        if not isinstance(login_nombre, str) or not login_nombre.strip():
            return jsonify(error="Faltan datos"), 400
        try:
            fecha = datetime.strptime(fecha_texto, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return jsonify(error="La fecha no es válida"), 400

        hay_horario = hora_inicio is not None or hora_fin is not None
        hay_ausencia = ausencia is not None
        if hay_horario and hay_ausencia:
            return jsonify(error="Indica horario o ausencia, no las dos"), 400
        if hay_ausencia:
            if ausencia not in AUSENCIAS:
                return jsonify(error="La ausencia no es válida"), 400
            if hora_inicio is not None or hora_fin is not None:
                return jsonify(error="Indica horario o ausencia, no las dos"), 400
        elif hora_inicio is None or hora_fin is None:
            return jsonify(error="Indica un horario o una ausencia"), 400

        url = database_url()
        if not url:
            return jsonify(error="Base de datos no configurada"), 503
        try:
            with psycopg.connect(url, connect_timeout=3) as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    cur.execute(
                        """
                        SELECT departamento_id
                        FROM usuario
                        WHERE id = %s AND rol = 'mando'
                        """,
                        (get_jwt_identity(),),
                    )
                    mando = cur.fetchone()
                    if mando is None or mando["departamento_id"] is None:
                        return jsonify(error="No autorizado"), 403
                    cur.execute(
                        """
                        SELECT id
                        FROM usuario
                        WHERE login = %s
                          AND rol = 'trabajador'
                          AND departamento_id = %s
                        """,
                        (login_nombre.strip(), mando["departamento_id"]),
                    )
                    trabajador = cur.fetchone()
                    if trabajador is None:
                        return jsonify(error="Ese trabajador no es de tu departamento"), 404
                    if hay_ausencia:
                        planificadas, nocturnas = 0, 0
                        hora_inicio = None
                        hora_fin = None
                    else:
                        cur.execute(
                            "SELECT noche_inicio, noche_fin FROM empresa WHERE id = 1"
                        )
                        franja = cur.fetchone()
                        if franja is None:
                            noche_inicio = datetime.strptime("22:00", "%H:%M").time()
                            noche_fin = datetime.strptime("06:00", "%H:%M").time()
                        else:
                            noche_inicio = franja["noche_inicio"]
                            noche_fin = franja["noche_fin"]
                        planificadas, nocturnas = horas_de_turno(
                            hora_inicio, hora_fin, noche_inicio, noche_fin
                        )
                    cur.execute(
                        """
                        INSERT INTO turno (
                            usuario_id, fecha, ausencia, hora_inicio, hora_fin,
                            horas_planificadas, horas_nocturnas
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (usuario_id, fecha) DO UPDATE SET
                            ausencia = EXCLUDED.ausencia,
                            hora_inicio = EXCLUDED.hora_inicio,
                            hora_fin = EXCLUDED.hora_fin,
                            horas_planificadas = EXCLUDED.horas_planificadas,
                            horas_nocturnas = EXCLUDED.horas_nocturnas
                        RETURNING fecha, ausencia::text AS ausencia, hora_inicio, hora_fin,
                                  horas_planificadas, horas_nocturnas
                        """,
                        (
                            trabajador["id"],
                            fecha,
                            ausencia,
                            hora_inicio,
                            hora_fin,
                            planificadas,
                            nocturnas,
                        ),
                    )
                    guardado = cur.fetchone()
        except psycopg.Error as exc:
            return jsonify(error=str(exc)), 503

        return jsonify(
            login=login_nombre.strip(),
            fecha=guardado["fecha"].isoformat(),
            ausencia=guardado["ausencia"],
            hora_inicio=hora_texto(guardado["hora_inicio"]),
            hora_fin=hora_texto(guardado["hora_fin"]),
            horas_planificadas=float(guardado["horas_planificadas"]),
            horas_nocturnas=float(guardado["horas_nocturnas"]),
        )

    return app


def _parse_hora(valor):
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


app = create_app()
