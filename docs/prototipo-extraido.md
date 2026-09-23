# Extraído del prototipo (Calendario 2027)

Fuente: el HTML de referencia de una sola página. Datos de ejemplo en el propio fichero. Sirve para sembrar departamentos, secciones, grupos y códigos. No es el modelo de acceso de la app: ese está en `decisiones.md`.

## Departamentos

Orden de la rejilla (`deptOrder`):

| Orden | Código | Nombre |
|---|---|---|
| 1 | `trafico` | Tráfico |
| 2 | `sac` | SAC |
| 3 | `muelle` | Muelle |
| 4 | `choferes` | Chóferes |
| 5 | `mandos` | Mandos + Funcionales |
| 6 | `mantenimiento` | Mantenimiento |

## Secciones

Solo Tráfico tiene secciones (en el HTML, `subgroups`; el filtro dice «Todas las secciones»), en este orden:

1. Administración
2. Nacional
3. Exportación
4. Agrupaciones

El resto de departamentos no tiene secciones.

## Grupos de filas

Un grupo agrupa empleados en el cuadrante. No es lo mismo que una sección.

| Departamento | Grupos |
|---|---|
| Tráfico | Equipo tráfico |
| SAC | Atención al cliente |
| Muelle | Personal STEF, ETT |
| Chóferes | Chóferes |
| Mandos + Funcionales | Mandos y funcionales |
| Mantenimiento | Mantenimiento |

En Muelle, Personal STEF y ETT son grupos de filas. En Tráfico la sección va aparte, dentro del único grupo.

## Códigos de ausencia

Leyenda del cuadrante:

| Código | Significado |
|---|---|
| L | Libranza |
| D | Domingo |
| V | Vacaciones |
| B | Baja |
| F | Festivo |
| P | Permiso |

El mismo mapa trae códigos de turno trabajado (no son ausencias): mañana `M`, `M1`, `M2`, `M3`, `M5`, `M8`, `M11`, `M13`; tarde `T`, `T5`, `T6`; noche `N`, `N6`, `N12`.

## Campos de empleado en el prototipo

- `name`
- `hours` — horas de contrato de la semana (columna Tot.H)
- `base` — `M`, `T` o `N` (familia de turno para armar el año)
- `days` — siete celdas: familia visual (mañana, tarde, noche, libranza, domingo, vacaciones) y texto de la celda (franja u `L` / `D` / `V`)
- `sub` — sección; solo si el departamento tiene secciones
- grupo — nombre del grupo de filas al que pertenece

No hay en este fichero número SAP, horas de convenio ni tarifas ETT. ETT aparece como nombre de grupo, no como coste.

## Login y roles en este HTML

Este prototipo no tiene pantalla de acceso, ni usuarios, ni roles. Quien abre la página ve todos los departamentos, todos los empleados y el análisis. No hay un perfil tipo Consulta ni un modo solo lectura. No hay contraseñas ni hashes que copiar.

La autenticación de la app va en el servidor. Cualquier comprobación de contraseña en el navegador es client-side y no debe reutilizarse.
