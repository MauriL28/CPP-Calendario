-- Segunda magnitud de la semana: pales, junto a toneladas.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/seguimiento_pales.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/seguimiento_pales.sql

ALTER TABLE seguimiento_semana
    ALTER COLUMN toneladas DROP NOT NULL;

ALTER TABLE seguimiento_semana
    ADD COLUMN IF NOT EXISTS pales NUMERIC(12, 2);

ALTER TABLE seguimiento_semana
    DROP CONSTRAINT IF EXISTS seguimiento_semana_pales_check;

ALTER TABLE seguimiento_semana
    ADD CONSTRAINT seguimiento_semana_pales_check CHECK (pales >= 0);

ALTER TABLE seguimiento_semana
    ADD COLUMN IF NOT EXISTS detalle_pales JSONB;

ALTER TABLE seguimiento_semana
    ADD COLUMN IF NOT EXISTS fila_base_pales TEXT;
