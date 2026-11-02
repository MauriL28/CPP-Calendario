-- orden deja de identificar el evento. La columna se queda, solo informativa.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.

ALTER TABLE fichaje_evento DROP CONSTRAINT IF EXISTS fichaje_evento_orden_key;

CREATE INDEX IF NOT EXISTS fichaje_evento_fecha ON fichaje_evento (fecha);
