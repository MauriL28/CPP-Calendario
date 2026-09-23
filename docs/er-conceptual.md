# ER conceptual (para dibujar)

Sin entidad Puesto: vacaciones, contrato y convenio son atributos del usuario.

## Entidades y atributos

Cada caja tiene un `id`. Las flechas son las relaciones.

**Departamento**
- código
- nombre
- orden (posición en la pantalla de inicio: Tráfico, SAC, Muelle… como en el prototipo)
Flechas: 1 — N Usuario (mandos y trabajadores). 0..1 Usuario **responsable** (el jefe; es relación, no un nombre escrito). 1 — N Sección.

**Usuario**
- nombre
- login
- clave (si luego cambia el acceso, se quita)
- rol: `admin` | `mando` | `trabajador`
- grupo: STEF | ETT (en trabajador)
- días de vacaciones al año
- horas de contrato (semana)
- horas de convenio (año; si no se usa, se quita)
- tarifas ETT (si es ETT; el trabajador no las ve)
- número SAP (si lo tiene)
- activo
Flechas: pertenece a Departamento; opcionalmente a Sección. Un usuario mando puede ser el responsable de su departamento.

**Turno** (un usuario, un día)
- fecha
- ausencia (`L` `D` `V` `B` `F` `P`) **o** hora_inicio + hora_fin — nunca las dos
- horas_planificadas
- horas_nocturnas (derivado, óvalo discontinuo: sale del horario y de la franja de noche de la empresa)
Flecha: de Usuario (a quién le toca ese día).

**Ajuste**
- fecha
- horas (+ o −)
- motivo
Dos flechas a Usuario:
- **a quién** (el trabajador al que se le suman o restan horas)
- **quién lo registra** (el mando que lo apunta)

**Fichaje**
- fecha
- horas_fichadas
- coincide: `ok` | `descuadre` | `sin_plan` | `sin_emparejar`
Flecha: de Usuario (a quién se le aplica). No hay flecha a Turno. Sin horas_nocturnas.

**Sección** (a un lado; en el prototipo solo Tráfico)
- nombre
Flecha: de Departamento.

**Festivo** (a un lado, suelta)
- fecha
- nombre

No se dibujan: Empleado, Semana, Código de ausencia, Parámetro, Puesto.

La franja de noche (hora inicio / hora fin) es de la empresa, dos números, **sin caja**.

## Flechas (resumen)

- Departamento 1 — N Usuario (equipo)
- Departamento 0..1 — 1 Usuario (responsable)
- Departamento 1 — N Sección
- Usuario N — 0..1 Sección
- Usuario 1 — N Turno
- Usuario 1 — N Ajuste (a quién)
- Usuario 1 — N Ajuste (quién registra)
- Usuario 1 — N Fichaje
