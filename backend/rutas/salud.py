import psycopg
from flask import jsonify

from db import url


def registrar(app):
    @app.get("/health")
    def health():
        direccion = url()
        if not direccion:
            return jsonify(status="ok", database="unconfigured")
        try:
            with psycopg.connect(direccion, connect_timeout=3) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
        except psycopg.Error:
            return jsonify(status="degraded", database="down"), 503
        return jsonify(status="ok", database="up")
