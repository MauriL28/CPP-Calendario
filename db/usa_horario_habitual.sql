-- Departamento sin horario habitual (Muelle).
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente.

ALTER TABLE departamento
    ADD COLUMN IF NOT EXISTS usa_horario_habitual BOOLEAN NOT NULL DEFAULT TRUE;

UPDATE departamento
SET usa_horario_habitual = FALSE
WHERE codigo = 'muelle';
