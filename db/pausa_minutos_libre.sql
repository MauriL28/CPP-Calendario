-- La pausa pasa de 0, 30 o 60 a cualquier múltiplo de 5 entre 0 y 180.
-- La restricción vieja se llama usuario_pausa_minutos.
-- usuario_pausa_habitual no se toca: la hora sigue exigiendo pausa_minutos > 0.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/pausa_minutos_libre.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/pausa_minutos_libre.sql

ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_pausa_minutos;

ALTER TABLE usuario
    ADD CONSTRAINT usuario_pausa_minutos CHECK (
        pausa_minutos BETWEEN 0 AND 180 AND pausa_minutos % 5 = 0
    );
