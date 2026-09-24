FROM postgres:16-alpine

COPY esquema.sql /docker-entrypoint-initdb.d/01-esquema.sql
COPY seed_departamentos.sql /docker-entrypoint-initdb.d/02-seed_departamentos.sql
