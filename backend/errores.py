import logging

from flask import jsonify

logger = logging.getLogger(__name__)


def error_bd(exc):
    """503 genérico. El detalle de la base queda solo en el log."""
    logger.exception("Error de base de datos: %s", exc)
    return jsonify(error="Error de base de datos"), 503
