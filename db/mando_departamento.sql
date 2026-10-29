-- Departamentos permitidos de un mando.
-- initdb no vuelve a ejecutar esquema.sql. Este script es idempotente.
-- Semilla: el departamento propio de cada mando.

CREATE TABLE IF NOT EXISTS mando_departamento (
    usuario_id       UUID NOT NULL REFERENCES usuario (id),
    departamento_id  UUID NOT NULL REFERENCES departamento (id),
    PRIMARY KEY (usuario_id, departamento_id)
);

INSERT INTO mando_departamento (usuario_id, departamento_id)
SELECT id, departamento_id
FROM usuario
WHERE rol = 'mando'
  AND departamento_id IS NOT NULL
ON CONFLICT DO NOTHING;
