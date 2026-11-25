-- Seguimiento de toneladas previstas por semana y departamento.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/seguimiento.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/seguimiento.sql

ALTER TABLE departamento
    ADD COLUMN IF NOT EXISTS usa_seguimiento BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE departamento
SET usa_seguimiento = TRUE
WHERE codigo = 'muelle';

CREATE TABLE IF NOT EXISTS seguimiento_semana (
    departamento_id  UUID NOT NULL REFERENCES departamento (id),
    semana_inicio    DATE NOT NULL,
    toneladas        NUMERIC(10, 2) NOT NULL CHECK (toneladas >= 0),
    actualizado_por  UUID REFERENCES usuario (id),
    actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (departamento_id, semana_inicio)
);
