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

-- Registro de cada importación. Idempotente: initdb no vuelve a ejecutar esquema.sql.
CREATE TABLE IF NOT EXISTS fichaje_importacion (
    id BIGSERIAL PRIMARY KEY
);

ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS usuario_id UUID REFERENCES usuario (id);
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS momento TIMESTAMPTZ NOT NULL DEFAULT now();
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS nombre_archivo TEXT;
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS filas_leidas INTEGER;
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS filas_insertadas_o_actualizadas INTEGER;
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS filas_sin_emparejar INTEGER;
ALTER TABLE fichaje_importacion ADD COLUMN IF NOT EXISTS dias_incidencia INTEGER;

ALTER TABLE fichaje_importacion ALTER COLUMN usuario_id SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN momento SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN nombre_archivo SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN filas_leidas SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN filas_insertadas_o_actualizadas SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN filas_sin_emparejar SET NOT NULL;
ALTER TABLE fichaje_importacion ALTER COLUMN dias_incidencia SET NOT NULL;

GRANT SELECT, INSERT, UPDATE, DELETE ON fichaje_importacion TO calendario;
GRANT USAGE, SELECT ON SEQUENCE fichaje_importacion_id_seq TO calendario;
