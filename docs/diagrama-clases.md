# Diagrama de clases (para dibujar)

Mismas cajas que el ER. UML: clase = entidad, asociación = relación. `horasNocturnas` en Turno va con `/` (derivado).

## Enums (aparte, o tipos de atributo)

- `Rol`: admin, mando, trabajador
- `Grupo`: STEF, ETT
- `Ausencia`: L, D, V, B, F, P
- `Coincide`: ok, descuadre, sin_plan, sin_emparejar

## Clases

**Departamento**
- codigo: String
- nombre: String
- orden: int

**Usuario**
- nombre: String
- login: String
- clave: String
- rol: Rol
- grupo: Grupo
- vacaciones: Number
- horasContrato: Number
- horasConvenio: Number
- tarifasETT: Number
- numeroSAP: String
- activo: boolean

**Seccion**
- nombre: String

**Turno**
- fecha: Date
- ausencia: Ausencia
- horaInicio: Time
- horaFin: Time
- horasPlanificadas: Number
- / horasNocturnas: Number

**Ajuste**
- fecha: Date
- horas: Number
- motivo: String

**Fichaje**
- fecha: Date
- horasFichadas: Number
- coincide: Coincide

**Festivo**
- fecha: Date
- nombre: String

## Asociaciones (multiplicidades)

- Departamento 1 — * Usuario  (`pertenece`)
- Departamento 0..1 — 0..1 Usuario  (`responsable`)
- Departamento 1 — * Seccion  (`tiene`)
- Usuario * — 0..1 Seccion  (`asignado`)  // muchos en una sección; un usuario, como mucho una
- Usuario 1 — * Turno  (`tiene`)
- Usuario 1 — * Ajuste  (`registra`)
- Usuario 1 — * Ajuste  (`afecta`)
- Usuario 1 — * Fichaje  (`ficha`)

Festivo sin asociaciones.

Turno: o `ausencia` o `horaInicio`+`horaFin`. Sin asociación Turno–Fichaje.
