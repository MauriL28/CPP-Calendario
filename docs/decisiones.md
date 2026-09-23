# Decisiones de producto (CCP-Calendario)

Cerradas con Mauricio el 22 sep 2026. Sustituyen supuestos SUP-01, SUP-02, SUP-03 y el tratamiento de retención/notificaciones. El acceso (`admin` / `mando` / `trabajador`) sustituye el par Editor / Consulta y el supuesto de que un usuario nunca es un empleado. El modelo de datos y la API (`data-model-and-api.md`) y el contexto (`project-context.md`) deben coincidir con esta lista.

## Cerrado

- **Parámetros personales:** van en el usuario: días de vacaciones al año, horas de contrato (semana) y horas de convenio (año). Login y clave se dibujan; si el acceso cambia, se quitan. No hay entidad Parámetro ni Puesto. La franja nocturna es de la empresa, igual para todos.
- **Departamento:** `orden` es el orden de la rejilla del prototipo. El **responsable** es una relación a un Usuario (un mando), no un texto. Siguen pudiendo haber varios mandos en el mismo depto.
- **Turno:** un usuario y un día. `horas_nocturnas` derivado (óvalo discontinuo). Fichaje no lleva horas nocturnas. Horario o ausencia, no las dos.
- **Ajuste:** dos relaciones a Usuario: afecta (a quién) y registra (quién lo apunta). El mando lo aplica directo.
- **Departamentos:** lista del prototipo, en este orden de `sort_order`: `trafico` Tráfico, `sac` SAC, `muelle` Muelle, `choferes` Chóferes, `mandos` Mandos + Funcionales, `mantenimiento` Mantenimiento. Secciones, grupos y campos de empleado: `prototipo-extraido.md`.
- **Acceso:** una tabla Usuario, rol `admin` | `mando` | `trabajador`. Sin herencia y sin entidad Empleado.
  - Admin crea mandos. Su departamento queda nulo por ahora.
  - Cada mando pertenece a un departamento, crea los trabajadores de su equipo y edita el cuadrante de ese departamento.
  - El trabajador es la Consulta: entra y ve solo sus datos. No ve coste ETT.
  - Quien está en el cuadrante es un usuario. Sin clave si todavía no entra.
  - Varios mandos por departamento. No hay jefe único.
- **Ausencias:** enum en el turno (L, D, V, B, F, P). No hay tabla de códigos.
- **Semana:** no es entidad. El turno tiene fecha. La vista semanal agrupa por fecha.
- **Festivo:** sí es entidad pequeña (fecha + nombre), suelta, para saber qué días son festivo.
- **Retención:** no es un bloqueo. No se implementa borrado automático de cuadrantes.
- **Notificaciones:** sí habrá avisos. El canal y los eventos se definen más adelante; no bloquean el ER. No hay tablas de notificación en el ER.
- **Fichajes SAP:** se pueden ver y, como requisito principal de v1, **se comparan** con lo planificado (no solo referencia).
- **Preguntas al solicitante:** no enviar cuestionarios técnicos. Traducir a lenguaje de negocio o resolver en el equipo.

## Sigue pendiente (cuando haya material)

- Cómo llegará el extracto SAP (fichero, columnas, quién lo carga) — se detalla al implementar la importación, no hace falta para el primer ER.
- Cómo se hacen los avisos (pantalla, correo, MY STEF).
