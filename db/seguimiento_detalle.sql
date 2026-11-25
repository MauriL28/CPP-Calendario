-- Detalle de la tabla de previsión pegada por el mando.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/seguimiento_detalle.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/seguimiento_detalle.sql

ALTER TABLE seguimiento_semana
    ADD COLUMN IF NOT EXISTS detalle JSONB;

ALTER TABLE seguimiento_semana
    ADD COLUMN IF NOT EXISTS fila_base TEXT;
