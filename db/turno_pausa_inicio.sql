-- Hora a la que empieza la pausa de un turno. La duración sigue en usuario.pausa_minutos.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/turno_pausa_inicio.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/turno_pausa_inicio.sql

ALTER TABLE turno
    ADD COLUMN IF NOT EXISTS pausa_inicio TIME;

ALTER TABLE turno DROP CONSTRAINT IF EXISTS turno_pausa_inicio;

ALTER TABLE turno
    ADD CONSTRAINT turno_pausa_inicio CHECK (
        pausa_inicio IS NULL
        OR (hora_inicio IS NOT NULL AND hora_fin IS NOT NULL)
    );
