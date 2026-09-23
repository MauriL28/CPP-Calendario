import os

import psycopg
from flask import Flask, jsonify


def create_app():
    app = Flask(__name__)

    @app.get("/health")
    def health():
        url = os.environ.get("DATABASE_URL")
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

    return app


app = create_app()
