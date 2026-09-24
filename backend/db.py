import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


class SinBaseDeDatos(Exception):
    pass


def url():
    return os.environ.get("DATABASE_URL")


@contextmanager
def cursor():
    direccion = url()
    if not direccion:
        raise SinBaseDeDatos()
    with psycopg.connect(direccion, connect_timeout=3) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            yield cur
