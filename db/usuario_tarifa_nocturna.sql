-- Tarifa por hora nocturna del trabajador ETT. Opcional. El coste diurno sigue en tarifas_ett.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/usuario_tarifa_nocturna.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/usuario_tarifa_nocturna.sql

ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS tarifa_nocturna NUMERIC(10, 4);
