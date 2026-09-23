# CCP-CALENDARIO — Contexto del proyecto

## Qué es

Aplicación web para gestionar el calendario de turnos/horas de los departamentos de STEF (logística). Sustituye un conjunto de Excels independientes por un **calendario de delegación único**, con persistencia centralizada y accesible desde el portal corporativo **MY STEF**.

Parte de un prototipo funcional en HTML/JS/CSS puro (un solo archivo, ~1500 líneas, sin backend, datos en `localStorage`) que ya valida la lógica de negocio y la UX. El objetivo actual es reconstruirlo como aplicación real.

- Solicitante del proyecto: Borja Trueba
- Prioridad: media — objetivo operativo antes de 2027
- Alcance: todos los departamentos de STEF (no solo el piloto inicial)

## Repositorio

- GitHub: https://github.com/MauriL28/CPP-Calendario
- Clone local (Mac): `~/Documents/Practicas/CPP_Calendario`

## Stack decidido

- **Frontend**: Vue.js (SPA)
- **Backend**: Flask (Python) + API REST
- **Base de datos**: PostgreSQL
- **Despliegue**: Docker / Docker Compose, gestionado por el equipo de Sistemas
- Mismo stack (Flask + SQLAlchemy + PostgreSQL + Flask-JWT-Extended + Docker) ya usado con éxito en otro proyecto propio (TFG académico), así que no es territorio nuevo.

## Roles y permisos

Una sola tabla de usuario, sin herencia y sin tabla de empleados. Tres roles, gestionados y validados en el **backend**. Quien sale en el cuadrante es un usuario; si todavía no entra en la app, es un usuario sin clave. La comprobación de contraseña en el navegador, si existiera, es solo client-side y no se reutiliza.

- **admin**: crea los mandos. Departamento nulo por ahora.
- **mando**: un departamento. Crea los trabajadores de su equipo y edita el cuadrante de ese departamento (el antiguo Editor). Varios mandos en el mismo departamento. No hay un jefe único. Aplica los ajustes de horas al momento.
- **trabajador**: es la Consulta. Entra y ve **solo sus** filas (celdas, ajustes y fichajes). No ve el coste ETT.

No hay un perfil Consulta aparte. El coste ETT no se serializa para el trabajador (el filtro es de respuesta de API, no solo de UI).

## Origen de los datos

- La planificación (cuadrante) se introduce **manualmente**.
- Los **fichajes reales** de los usuarios se sincronizan desde **SAP**, con frecuencia **semanal** (confirmado: solo fichajes, no otros datos de SAP).
- En v1 los fichajes se **muestran** y se **comparan** con la celda planificada de ese usuario y esa fecha (horas plan vs. fichadas, estado de cruce, fichajes sin emparejar). El formato concreto del extracto se detalla al implementar la importación.

## Requisitos funcionales

| ID | Requisito | Descripción |
|---|---|---|
| RF-01 | Acceso por roles | Login con roles admin, mando y trabajador. El trabajador ve solo sus filas y no ve coste ETT. No hay perfil Consulta aparte. |
| RF-02 | Selección de departamento | Pantalla inicial con acceso a los departamentos; cada uno independiente, sin visibilidad cruzada |
| RF-03 | Vista semanal | Cuadrante editable por usuario y día (horario o ausencia L, D, V, B, F, P); cálculo automático de horas totales y nocturnas. La semana es la vista: agrupa celdas por fecha. |
| RF-04 | Vista mensual | Misma edición que semanal, mes completo, navegación horizontal |
| RF-05 | Copiar semana anterior | Duplicar las celdas de las fechas de la semana previa. La semana es la vista, no una entidad. |
| RF-06 | Gestión de empleados | Alta/baja/edición de las personas del cuadrante, que son usuarios (no hay tabla de empleados): nombre, grupo STEF/ETT, sección si aplica, horas de contrato, horas de convenio, días de vacaciones al año, tarifas ETT. Clave nula si aún no entran. |
| RF-07 | Ajustes manuales | Añadir/eliminar ajustes puntuales de horas por usuario, con motivo. El mando los aplica **directo** (sin aprobación ni rol extra). |
| RF-08 | Análisis | Ranking de horas, desglose por usuario, coste ETT, producción, totales por ausencia (L, D, V, B, F, P) |
| RF-09 | Producción | Registro semanal de palés/toneladas por sección |
| RF-10 | Ficha anual | Resumen anual imprimible del usuario: horas por mes, ajustes, festivos/sábados trabajados, firma |
| RF-11 | Exportación de datos | Exportar planificación/informes (Excel/PDF) |
| RF-12 | Origen de datos | Entrada manual + sincronización semanal de fichajes desde SAP. En v1: ver fichajes y **conciliarlos** con el cuadrante. |
| RF-13 | Datos de jornada | Días de vacaciones al año, horas de contrato y horas de convenio van en el usuario. No hay parámetros globales ni por departamento. La franja nocturna es una sola fila de empresa (`company_settings`), la misma para todos. |

## Requisitos no funcionales

| ID | Categoría | Descripción |
|---|---|---|
| RNF-01 | Seguridad | Auth y permisos gestionados en servidor; contraseñas cifradas; rol validado en cada operación |
| RNF-02 | Concurrencia | Varias personas editando el mismo departamento sin sobrescrituras silenciosas |
| RNF-03 | Disponibilidad | Operativa en todos los turnos, incluida noche |
| RNF-04 | Rendimiento | Carga aceptable con mes completo + todos los departamentos activos |
| RNF-05 | Compatibilidad | Escritorio + diseño responsive para móvil (deseable, uso confirmado por los mandos). Pendiente: ¿el móvil necesita también edición, o solo lectura? |
| RNF-06 | Trazabilidad | Registrar quién y cuándo hizo el **último** cambio (confirmado: no se requiere historial completo de versiones) |
| RNF-07 | Copias de seguridad | Backups periódicos de la BD, coordinados con Sistemas |
| RNF-08 | Integración | Accesible desde el portal corporativo MY STEF |
| RNF-09 | Migración | Migrar los datos ya existentes (Excels + prototipo) a la BD definitiva sin pérdida |

## Decisiones ya cerradas con el solicitante

- Sin visibilidad entre departamentos. Mando y trabajador tienen un departamento; el admin, ninguno por ahora.
- SAP: solo fichajes, sincronización semanal; en v1 se ven **y** se concilian con la celda de ese usuario y esa fecha.
- Jornada: vacaciones, horas de contrato y horas de convenio en el usuario. La franja nocturna es de la empresa (`company_settings`), una sola, y no se copia en cada usuario.
- Ajustes de horas: el mando los aplica directo; no hay cola de aprobación ni rol extra.
- Auditoría: basta con el último cambio, no historial completo.
- Acceso móvil: deseable, al menos para ver los datos propios.
- Retención: no hay borrado automático; no bloquea el diseño.
- Notificaciones: habrá avisos más adelante; el canal no forma parte del ER v1.
- El trabajador no ve coste ETT (el filtro es de respuesta de API, no solo de UI). No hay perfil Consulta aparte. No hay entidad Semana: la celda tiene fecha.

## Aún abierto / por confirmar

Cuando haya material (no bloquea el modelo de datos):

- Cómo llegará el extracto SAP (fichero, columnas, quién lo carga). La lista de departamentos del prototipo ya está en `prototipo-extraido.md`.
- Cómo se hacen los avisos (pantalla, correo, MY STEF).

## Estructura de carpetas propuesta (frontend)

```
src/
├── config/
│   └── constants.js       // semilla del prototipo: departamentos, grupos, códigos
│                           // Vacaciones, contrato y convenio van en el usuario.
│                           // La franja de noche es la fila company_settings.
├── utils/
│   ├── dates.js            // mondayOfWeek, weeksInYear, isoWeekOf, semanasDelMes
│   └── schedule.js         // franja, esNoct, calcNoche, parseRange, parseCell,
│                            // statsRango, tarifas, costeDe, prodRangoSemanas
│                            // (lógica de negocio — replicar validación en backend,
│                            //  no confiar solo en el cálculo del cliente)
├── stores/                  // Pinia
│   ├── calendario.js        // reemplaza el DATA + localStorage del prototipo
│   └── auth.js               // rol, sesión — consumiendo JWT del backend
├── composables/
│   ├── usePeriodNav.js       // navegación semana/mes/año
│   └── useDirtyState.js      // control de cambios sin guardar
├── components/
│   ├── ScheduleTable.vue     // tabla editable, reutilizada por semana y mes
│   ├── UserModal.vue         // alta y edición de la persona (es un usuario)
│   ├── Legend.vue
│   └── KpiPanel.vue
└── views/
    ├── LoginView.vue
    ├── HomeView.vue
    ├── WeekView.vue
    ├── MonthView.vue
    ├── AnalysisView.vue
    └── UserSheetView.vue       // ficha anual de ese usuario
```

## Estado actual

Requisitos funcionales/no funcionales y decisiones de producto (22 sep 2026) cerrados con el solicitante. Aún no hay código de backend ni de la app Vue definitiva — solo el prototipo HTML/JS de referencia. El modelo de datos y la API están en `data-model-and-api.md`.
