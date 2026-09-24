# CPP-Calendario

Calendario de turnos de los departamentos STEF. Sustituye los Excel por una app (Vue + Flask + PostgreSQL).

- Repo: [github.com/MauriL28/CPP-Calendario](https://github.com/MauriL28/CPP-Calendario)
- Carpeta local: `~/Documents/Practicas/CPP_Calendario`

## Levantar

Hace falta Docker con Compose.

```bash
docker compose up --build
```

| Servicio | Dónde |
|---|---|
| Frontend | http://localhost:8080 |
| Backend | http://localhost:5001/health |
| PostgreSQL | `localhost:5432`, base y usuario `calendario`, clave `calendario` |

La primera vez Postgres ejecuta `db/esquema.sql` y crea las tablas. Es un esqueleto: la pantalla solo muestra el nombre y el backend solo responde el health. No hay login, SAP ni cuadrante.

Parar los contenedores:

```bash
docker compose down
```

## Documentación

**Todo está en [`docs/`](docs/).** Empieza por [docs/README.md](docs/README.md).

- [Contexto del proyecto](docs/project-context.md)
- [Decisiones](docs/decisiones.md)
- [ER (imagen)](docs/diagramas/er.png) · [Clases (imagen)](docs/diagramas/clases.png)
