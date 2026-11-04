-- Nuevos códigos de ausencia. ST y FT llevan horario; el resto no.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente y no borra filas.
-- Cada ADD VALUE va en su propia sentencia, fuera de transacción: el valor nuevo
-- no se puede usar en el CHECK hasta que esa sentencia haya confirmado.
-- No ejecutar con psql --single-transaction.

ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'SR';
ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'FR';
ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'HS';
ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'PEND';
ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'ST';
ALTER TYPE codigo_ausencia ADD VALUE IF NOT EXISTS 'FT';

ALTER TABLE turno DROP CONSTRAINT IF EXISTS turno_horario_o_ausencia;

ALTER TABLE turno ADD CONSTRAINT turno_horario_o_ausencia CHECK (
    (
        ausencia IN ('ST', 'FT')
        AND hora_inicio IS NOT NULL
        AND hora_fin IS NOT NULL
    )
    OR (
        ausencia IS NOT NULL
        AND ausencia NOT IN ('ST', 'FT')
        AND hora_inicio IS NULL
        AND hora_fin IS NULL
    )
    OR (
        ausencia IS NULL
        AND hora_inicio IS NOT NULL
        AND hora_fin IS NOT NULL
    )
);
