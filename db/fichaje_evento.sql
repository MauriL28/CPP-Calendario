-- Carga de fichajes sobre una base ya inicializada.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente.
-- No toca el índice usuario_sap_por_depto.

CREATE TABLE IF NOT EXISTS fichaje_evento (
    id          BIGSERIAL PRIMARY KEY,
    orden       INTEGER NOT NULL UNIQUE,
    numero_sap  TEXT    NOT NULL,
    usuario_id  UUID REFERENCES usuario (id),
    tipo        TEXT,
    fecha       DATE,
    hora        TIME    NOT NULL
);

CREATE INDEX IF NOT EXISTS fichaje_evento_sap_fecha
    ON fichaje_evento (numero_sap, fecha);

ALTER TABLE fichaje ADD COLUMN IF NOT EXISTS horas_trabajadas NUMERIC(8, 2);
ALTER TABLE fichaje ADD COLUMN IF NOT EXISTS horas_pausa NUMERIC(8, 2);
ALTER TABLE fichaje ADD COLUMN IF NOT EXISTS incidencia BOOLEAN;

-- Filas viejas (la semilla no crea ninguna): sin horas de este paso, son incidencia.
UPDATE fichaje
SET incidencia = TRUE
WHERE incidencia IS NULL;

ALTER TABLE fichaje ALTER COLUMN incidencia SET NOT NULL;
ALTER TABLE fichaje ALTER COLUMN coincide DROP NOT NULL;

ALTER TABLE fichaje DROP CONSTRAINT IF EXISTS fichaje_sin_usuario;
ALTER TABLE fichaje ADD CONSTRAINT fichaje_sin_usuario CHECK (
    coincide IS NULL
    OR (coincide = 'sin_emparejar' AND usuario_id IS NULL)
    OR (coincide <> 'sin_emparejar' AND usuario_id IS NOT NULL)
);

ALTER TABLE fichaje DROP CONSTRAINT IF EXISTS fichaje_horas_incidencia;
ALTER TABLE fichaje ADD CONSTRAINT fichaje_horas_incidencia CHECK (
    (
        incidencia
        AND horas_trabajadas IS NULL
        AND horas_pausa IS NULL
    )
    OR (
        NOT incidencia
        AND horas_trabajadas IS NOT NULL
        AND horas_pausa IS NOT NULL
    )
);
