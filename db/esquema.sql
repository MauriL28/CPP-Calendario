-- CPP-Calendario — esquema PostgreSQL
-- Sale del ER y del diagrama de clases (sep 2026).
-- Un usuario = como mucho un departamento. Varios mandos por departamento.
-- Turno: horario XOR ausencia. Fichaje no apunta a Turno (cruce por usuario + fecha).

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE rol_usuario AS ENUM ('admin', 'mando', 'trabajador');
CREATE TYPE grupo_persona AS ENUM ('STEF', 'ETT');
CREATE TYPE codigo_ausencia AS ENUM ('L', 'D', 'V', 'B', 'F', 'P');
CREATE TYPE estado_cruce AS ENUM ('ok', 'descuadre', 'sin_plan', 'sin_emparejar');

-- Franja de noche de la empresa (no es caja del ER: dos números).
-- horas_nocturnas del turno se calculan con esto.
CREATE TABLE empresa (
    id            SMALLINT PRIMARY KEY CHECK (id = 1),
    noche_inicio  TIME NOT NULL DEFAULT '22:00',
    noche_fin     TIME NOT NULL DEFAULT '06:00'
);

INSERT INTO empresa (id) VALUES (1);

CREATE TABLE delegacion (
    id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo  VARCHAR(16)  NOT NULL UNIQUE,
    nombre  VARCHAR(120) NOT NULL
);

CREATE TABLE departamento (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delegacion_id   UUID         NOT NULL REFERENCES delegacion (id),
    codigo          VARCHAR(32)  NOT NULL,
    nombre          VARCHAR(120) NOT NULL,
    orden           INTEGER      NOT NULL DEFAULT 0,
    UNIQUE (delegacion_id, codigo)
);

CREATE TABLE seccion (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    departamento_id  UUID         NOT NULL REFERENCES departamento (id),
    nombre           VARCHAR(120) NOT NULL,
    UNIQUE (departamento_id, nombre)
);

CREATE TABLE usuario (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    departamento_id    UUID REFERENCES departamento (id),
    seccion_id         UUID REFERENCES seccion (id),
    nombre             VARCHAR(160) NOT NULL,
    login              VARCHAR(80)  NOT NULL UNIQUE,
    clave              VARCHAR(255),
    rol                rol_usuario  NOT NULL,
    grupo              grupo_persona,
    vacaciones         NUMERIC(5, 2),
    horas_contrato     NUMERIC(8, 2),
    horas_convenio     NUMERIC(8, 2),
    tarifas_ett        NUMERIC(10, 4),
    numero_sap         VARCHAR(40),
    activo             BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT usuario_depto_segun_rol CHECK (
        (rol = 'admin' AND departamento_id IS NULL)
        OR (rol <> 'admin' AND departamento_id IS NOT NULL)
    ),
    CONSTRAINT usuario_seccion_mismo_depto CHECK (seccion_id IS NULL OR departamento_id IS NOT NULL)
);

-- Responsable: un departamento, como mucho un jefe. Ese usuario, como mucho un depto.
ALTER TABLE departamento
    ADD COLUMN responsable_id UUID UNIQUE REFERENCES usuario (id);

CREATE UNIQUE INDEX usuario_sap_por_depto
    ON usuario (departamento_id, numero_sap)
    WHERE numero_sap IS NOT NULL;

CREATE TABLE turno (
    usuario_id          UUID NOT NULL REFERENCES usuario (id),
    fecha               DATE NOT NULL,
    ausencia            codigo_ausencia,
    hora_inicio         TIME,
    hora_fin            TIME,
    horas_planificadas  NUMERIC(8, 2) NOT NULL DEFAULT 0,
    -- Derivado: se guarda ya calculado (franja de empresa + horario). No lo escribe el mando.
    horas_nocturnas     NUMERIC(8, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id, fecha),
    CONSTRAINT turno_horario_o_ausencia CHECK (
        (
            ausencia IS NOT NULL
            AND hora_inicio IS NULL
            AND hora_fin IS NULL
        )
        OR (
            ausencia IS NULL
            AND hora_inicio IS NOT NULL
            AND hora_fin IS NOT NULL
        )
    )
);

CREATE TABLE ajuste (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fecha                 DATE          NOT NULL,
    horas                 NUMERIC(8, 2) NOT NULL CHECK (horas <> 0),
    motivo                VARCHAR(500)  NOT NULL,
    usuario_afectado_id   UUID          NOT NULL REFERENCES usuario (id),
    usuario_registra_id   UUID          NOT NULL REFERENCES usuario (id)
);

CREATE INDEX ajuste_afectado_fecha ON ajuste (usuario_afectado_id, fecha);

CREATE TABLE fichaje (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id      UUID REFERENCES usuario (id),
    fecha           DATE          NOT NULL,
    horas_fichadas  NUMERIC(8, 2) NOT NULL DEFAULT 0,
    coincide        estado_cruce  NOT NULL,
    CONSTRAINT fichaje_sin_usuario CHECK (
        (coincide = 'sin_emparejar' AND usuario_id IS NULL)
        OR (coincide <> 'sin_emparejar' AND usuario_id IS NOT NULL)
    )
);

CREATE INDEX fichaje_usuario_fecha ON fichaje (usuario_id, fecha);

CREATE TABLE festivo (
    fecha   DATE PRIMARY KEY,
    nombre  VARCHAR(120) NOT NULL
);
