-- JWT cerrados a mano. Se rechazan hasta que expiran.
-- initdb no vuelve a ejecutar esquema.sql si el volumen de Postgres ya existe.
-- En una base que ya está creada, desde la raíz del repo:
--   docker compose exec -T db psql -U calendario -d calendario < db/token_revocado.sql
-- o, con la URL de esa base:
--   psql "$DATABASE_URL" -f db/token_revocado.sql

CREATE TABLE IF NOT EXISTS token_revocado (
    jti     TEXT PRIMARY KEY,
    expira  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS token_revocado_expira ON token_revocado (expira);
