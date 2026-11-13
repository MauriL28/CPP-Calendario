-- Hora a la que suele empezar la pausa del trabajador. La duración sigue en pausa_minutos.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/usuario_pausa_habitual.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/usuario_pausa_habitual.sql

ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS pausa_habitual TIME;

ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_pausa_habitual;

ALTER TABLE usuario
    ADD CONSTRAINT usuario_pausa_habitual CHECK (
        pausa_habitual IS NULL OR pausa_minutos > 0
    );
