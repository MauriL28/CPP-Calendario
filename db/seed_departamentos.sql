-- Delegaciones, departamentos y admins de desarrollo. Idempotente.

INSERT INTO delegacion (codigo, nombre) VALUES
    ('60I', 'San Sebastián'),
    ('05I', 'Irún')
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO departamento (delegacion_id, codigo, nombre, orden)
SELECT g.id, dep.codigo, dep.nombre, dep.orden
FROM delegacion g
CROSS JOIN (VALUES
    ('trafico',        'Tráfico',                 1),
    ('sac',            'SAC',                     2),
    ('muelle',         'Muelle',                  3),
    ('choferes',       'Chóferes',                4),
    ('mandos',         'Mandos + Funcionales',    5),
    ('mantenimiento',  'Mantenimiento',           6)
) AS dep(codigo, nombre, orden)
ON CONFLICT (delegacion_id, codigo) DO NOTHING;

INSERT INTO seccion (departamento_id, nombre)
SELECT dep.id, s.nombre
FROM departamento dep
CROSS JOIN (VALUES
    ('Administración'),
    ('Nacional'),
    ('Exportación'),
    ('Agrupaciones')
) AS s(nombre)
WHERE dep.codigo = 'trafico'
ON CONFLICT (departamento_id, nombre) DO NOTHING;

INSERT INTO usuario (nombre, login, clave, rol)
VALUES ('Admin', 'admin', crypt('admin', gen_salt('bf')), 'admin')
ON CONFLICT (login) DO NOTHING;
