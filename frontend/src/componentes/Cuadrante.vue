<script setup>
import { computed, nextTick, ref } from "vue";
import { fechaVisible, lunesDe, rangoSemana, sumarDias, textoCelda } from "../fechas.js";
import { borrarTurno, copiarSemana, guardarTurno, mes, semana } from "../api/turnos.js";

const props = defineProps({
  token: { type: String, required: true },
  propia: { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
});

const diasNombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const diasCortos = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const mesesLargos = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const ausencias = [
  { codigo: "L", nombre: "Libranza" },
  { codigo: "D", nombre: "Domingo" },
  { codigo: "V", nombre: "Vacaciones" },
  { codigo: "B", nombre: "Baja" },
  { codigo: "F", nombre: "Festivo" },
  { codigo: "P", nombre: "Permiso" },
];
const familias = {
  L: "libranza",
  D: "domingo",
  V: "vacaciones",
  B: "baja",
  F: "festivo",
  P: "permiso",
};
const franjas = [
  { id: "noche", nombre: "Total noche" },
  { id: "manana", nombre: "Total mañana" },
  { id: "tarde", nombre: "Total tarde" },
];
const leyenda = [
  { id: "manana", nombre: "Mañana" },
  { id: "tarde", nombre: "Tarde" },
  { id: "noche", nombre: "Noche" },
  { id: "libranza", nombre: "Libranza" },
  { id: "domingo", nombre: "Domingo" },
  { id: "vacaciones", nombre: "Vacaciones" },
  { id: "baja", nombre: "Baja" },
  { id: "festivo", nombre: "Festivo" },
  { id: "permiso", nombre: "Permiso" },
];
const modo = ref("semana");
const semanaDesde = ref("");
const anioMes = ref(0);
const numeroMes = ref(0);
const cuadrante = ref(null);
const errorSemana = ref("");
const celda = ref(null);
const dialogo = ref(null);
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoAusencia = ref("L");
const errorTurno = ref("");

const tituloMes = computed(() => `${mesesLargos[numeroMes.value - 1] || ""} ${anioMes.value}`.trim());
const gruposCuadrante = [
  { id: "STEF", titulo: "Personal STEF" },
  { id: "ETT", titulo: "ETT" },
];
const filasCuadrante = computed(() => {
  const lista = cuadrante.value?.trabajadores || [];
  if (props.propia) {
    return lista.map((trabajador) => ({ tipo: "persona", trabajador }));
  }
  const filas = [];
  const vistos = new Set();
  for (const grupo of gruposCuadrante) {
    const personas = lista.filter((trabajador) => trabajador.grupo === grupo.id);
    if (!personas.length) {
      continue;
    }
    filas.push({ tipo: "grupo", id: grupo.id, titulo: grupo.titulo });
    for (const trabajador of personas) {
      vistos.add(trabajador.login);
      filas.push({ tipo: "persona", trabajador });
    }
  }
  for (const trabajador of lista) {
    if (!vistos.has(trabajador.login)) {
      filas.push({ tipo: "persona", trabajador });
    }
  }
  return filas;
});

async function cargar(desde) {
  errorSemana.value = "";
  if (dialogo.value?.open) {
    dialogo.value.close();
  }
  try {
    cuadrante.value = await semana(props.token, desde, props.propia);
    semanaDesde.value = cuadrante.value.desde;
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

async function cargarMes(anio, mesNumero) {
  errorSemana.value = "";
  if (dialogo.value?.open) {
    dialogo.value.close();
  }
  try {
    cuadrante.value = await mes(props.token, anio, mesNumero, props.propia);
    anioMes.value = anio;
    numeroMes.value = mesNumero;
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar el mes";
  }
}

function partes(iso) {
  return iso.split("-").map(Number);
}

function diaSemana(iso) {
  const [anio, mesNumero, dia] = partes(iso);
  return new Date(anio, mesNumero - 1, dia).getDay();
}

function cambiarModo(nuevo) {
  if (nuevo === modo.value) {
    return;
  }
  modo.value = nuevo;
  if (nuevo === "mes") {
    const [anio, mesNumero] = partes(semanaDesde.value || lunesDe(new Date()));
    cargarMes(anio, mesNumero);
    return;
  }
  const referencia = semanaDesde.value;
  if (referencia && partes(referencia)[0] === anioMes.value && partes(referencia)[1] === numeroMes.value) {
    cargar(referencia);
    return;
  }
  cargar(lunesDe(new Date(anioMes.value, numeroMes.value - 1, 1)));
}

function moverMes(delta) {
  const fecha = new Date(anioMes.value, numeroMes.value - 1 + delta, 1);
  cargarMes(fecha.getFullYear(), fecha.getMonth() + 1);
}

function esFin(indice) {
  return indice >= 5;
}

function esFinDia(dia, indice) {
  if (modo.value !== "mes") {
    return esFin(indice);
  }
  const semanaDia = diaSemana(dia);
  return semanaDia === 0 || semanaDia === 6;
}

function nombreFestivo(indice) {
  for (const trabajador of cuadrante.value?.trabajadores || []) {
    const dia = trabajador.dias?.[indice];
    if (dia?.festivo) {
      return dia.nombre || "Festivo";
    }
  }
  return "";
}

function totalFranja(franja, indice) {
  return (cuadrante.value?.trabajadores || []).filter(
    (trabajador) => familia(trabajador.dias[indice]?.turno) === franja,
  ).length;
}

function familia(turno) {
  if (!turno) {
    return "";
  }
  if (turno.ausencia) {
    return familias[turno.ausencia] || "";
  }
  const [hora, minuto] = (turno.hora_inicio || "00:00").split(":").map(Number);
  const inicio = hora * 60 + minuto;
  if (inicio >= 22 * 60 || inicio < 6 * 60) {
    return "noche";
  }
  if (inicio < 14 * 60) {
    return "manana";
  }
  return "tarde";
}

async function abrirCelda(trabajador, dia) {
  if (!props.editable) {
    return;
  }
  const turno = dia.turno;
  celda.value = {
    login: trabajador.login,
    nombre: trabajador.nombre,
    fecha: dia.fecha,
    origen: dia.origen || "",
  };
  errorTurno.value = "";
  if (turno && turno.ausencia) {
    turnoModo.value = "ausencia";
    turnoAusencia.value = turno.ausencia;
    turnoInicio.value = "";
    turnoFin.value = "";
  } else {
    turnoModo.value = "horario";
    turnoAusencia.value = "L";
    turnoInicio.value = turno?.hora_inicio || "";
    turnoFin.value = turno?.hora_fin || "";
  }
  await nextTick();
  dialogo.value?.showModal();
  dialogo.value?.querySelector("select")?.focus();
}

function cerrarCelda() {
  dialogo.value?.close();
}

function alCerrarCelda() {
  celda.value = null;
  errorTurno.value = "";
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    cerrarCelda();
  }
}

async function copiar() {
  errorSemana.value = "";
  try {
    await copiarSemana(props.token, semanaDesde.value);
    await cargar(semanaDesde.value);
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo copiar la semana";
  }
}

async function guardar() {
  if (!celda.value) {
    return;
  }
  errorTurno.value = "";
  const cuerpo = {
    login: celda.value.login,
    fecha: celda.value.fecha,
  };
  if (turnoModo.value === "ausencia") {
    cuerpo.ausencia = turnoAusencia.value;
  } else {
    cuerpo.hora_inicio = turnoInicio.value;
    cuerpo.hora_fin = turnoFin.value;
  }
  try {
    await guardarTurno(props.token, cuerpo);
    cerrarCelda();
    await refrescar();
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo guardar el turno";
  }
}

async function quitar() {
  if (!celda.value) {
    return;
  }
  errorTurno.value = "";
  const cuerpo = { login: celda.value.login, fecha: celda.value.fecha };
  try {
    await borrarTurno(props.token, cuerpo);
    cerrarCelda();
    await refrescar();
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo quitar la excepción";
  }
}

async function refrescar() {
  if (modo.value === "mes") {
    await cargarMes(anioMes.value, numeroMes.value);
    return;
  }
  await cargar(semanaDesde.value || lunesDe(new Date()));
}

defineExpose({ recargar: refrescar });
cargar(lunesDe(new Date()));
</script>

<template>
  <section v-if="cuadrante" class="semana" :class="{ lectura: !editable }">
    <div class="semana-nav">
      <div class="vistas modo-vista">
        <button type="button" :class="{ activo: modo === 'semana' }" @click="cambiarModo('semana')">
          Semanal
        </button>
        <button type="button" :class="{ activo: modo === 'mes' }" @click="cambiarModo('mes')">
          Mensual
        </button>
      </div>
      <template v-if="modo === 'semana'">
        <button type="button" @click="cargar(sumarDias(semanaDesde, -7))">Semana anterior</button>
        <span class="rango">{{ rangoSemana(cuadrante.desde, cuadrante.dias[6]) }}</span>
        <button type="button" @click="cargar(sumarDias(semanaDesde, 7))">Semana siguiente</button>
        <button v-if="editable" type="button" @click="copiar">Copiar semana anterior</button>
      </template>
      <template v-else>
        <button type="button" @click="moverMes(-1)">Mes anterior</button>
        <span class="rango">{{ tituloMes }}</span>
        <button type="button" @click="moverMes(1)">Mes siguiente</button>
      </template>
    </div>
    <p v-if="!editable" class="aviso-lectura">Solo lectura</p>
    <p v-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
    <div class="cuadrante-scroll" :class="{ mensual: modo === 'mes' }">
    <table class="cuadrante" :class="{ mensual: modo === 'mes' }">
      <thead>
        <tr>
          <th>Trabajador</th>
          <th v-for="(dia, indice) in cuadrante.dias" :key="dia" :class="{ fin: esFinDia(dia, indice) }">
            <span class="dia-nombre">{{ modo === "mes" ? diasCortos[diaSemana(dia)] : diasNombre[indice] }}</span>
            <span class="dia-numero">{{ modo === "mes" ? Number(dia.slice(8)) : fechaVisible(dia).slice(0, 5) }}</span>
            <span
              v-if="nombreFestivo(indice)"
              class="dia-festivo"
              :title="nombreFestivo(indice)"
              :aria-label="nombreFestivo(indice)"
            ></span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="fila in filasCuadrante" :key="fila.tipo === 'grupo' ? fila.id : fila.trabajador.login">
          <tr v-if="fila.tipo === 'grupo'" class="grupo-fila">
            <th :colspan="cuadrante.dias.length + 1">{{ fila.titulo }}</th>
          </tr>
          <tr v-else>
            <th>{{ fila.trabajador.nombre }}</th>
            <td
              v-for="(dia, indice) in fila.trabajador.dias"
              :key="dia.fecha"
              :class="[esFinDia(dia.fecha, indice) ? 'fin' : '', familia(dia.turno) ? `turno-${familia(dia.turno)}` : '']"
            >
              <button
                v-if="editable"
                type="button"
                class="celda"
                @click="abrirCelda(fila.trabajador, dia)"
              >
                {{ textoCelda(dia.turno) }}
              </button>
              <span v-else class="celda lectura">{{ textoCelda(dia.turno) }}</span>
            </td>
          </tr>
        </template>
      </tbody>
      <tfoot v-if="!propia">
        <tr v-for="franja in franjas" :key="franja.id">
          <td>{{ franja.nombre }}</td>
          <td v-for="(dia, indice) in cuadrante.dias" :key="dia">{{ totalFranja(franja.id, indice) }}</td>
        </tr>
      </tfoot>
    </table>
    </div>
    <ul class="leyenda">
      <li v-for="item in leyenda" :key="item.id">
        <span class="muestra" :class="`turno-${item.id}`"></span>
        {{ item.nombre }}
      </li>
    </ul>
  </section>
  <p v-else-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
  <dialog ref="dialogo" class="editor-dia" @close="alCerrarCelda" @click="alFondo">
    <form v-if="celda" @submit.prevent="guardar">
      <header class="editor-dia-cabecera">
        <h2>Editar día</h2>
        <p class="editor-dia-quien">
          {{ celda.nombre }}<br />
          {{ fechaVisible(celda.fecha) }}
        </p>
      </header>
      <div class="editor-dia-cuerpo">
        <label class="ancho">
          Tipo
          <select v-model="turnoModo">
            <option value="horario">Horario</option>
            <option value="ausencia">Ausencia</option>
          </select>
        </label>
        <template v-if="turnoModo === 'horario'">
          <label>
            Hora de inicio
            <input v-model="turnoInicio" type="time" required />
          </label>
          <label>
            Hora de fin
            <input v-model="turnoFin" type="time" required />
          </label>
        </template>
        <label v-else class="ancho">
          Ausencia
          <select v-model="turnoAusencia">
            <option v-for="item in ausencias" :key="item.codigo" :value="item.codigo">
              {{ item.nombre }}
            </option>
          </select>
        </label>
      </div>
      <p v-if="errorTurno" class="error" role="alert">{{ errorTurno }}</p>
      <footer class="editor-dia-pie">
        <button v-if="celda.origen === 'guardado'" type="button" @click="quitar">
          Quitar excepción y volver al horario habitual
        </button>
        <span class="editor-dia-acciones">
          <button type="button" @click="cerrarCelda">Cancelar</button>
          <button class="primario" type="submit">Guardar</button>
        </span>
      </footer>
    </form>
  </dialog>
</template>
