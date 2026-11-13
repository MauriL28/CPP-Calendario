-- Pausa no computable del usuario, en minutos.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.

ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS pausa_minutos SMALLINT NOT NULL DEFAULT 0;

ALTER TABLE usuario DROP CONSTRAINT IF EXISTS usuario_pausa_minutos;

ALTER TABLE usuario
    ADD CONSTRAINT usuario_pausa_minutos CHECK (
        pausa_minutos BETWEEN 0 AND 180 AND pausa_minutos % 5 = 0
    );
