-- Rango de fechas de cada importación. NULL si el Excel no trae fechas.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.

ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS fecha_desde DATE;
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS fecha_hasta DATE;
