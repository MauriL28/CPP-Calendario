<script setup>
import { ref } from "vue";
import { fechaVisible, lunesDe, sumarDias, textoCelda } from "../fechas.js";
import { aplicarHorarios, copiarSemana, guardarTurno, semana } from "../api/turnos.js";

const props = defineProps({
  token: { type: String, required: true },
  propia: { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
});

const diasNombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const ausencias = ["L", "D", "V", "B", "F", "P"];
const familias = {
  L: "libranza",
  D: "domingo",
  V: "vacaciones",
  B: "baja",
  F: "festivo",
  P: "permiso",
};
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
const semanaDesde = ref("");
const cuadrante = ref(null);
const errorSemana = ref("");
const celda = ref(null);
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoAusencia = ref("L");
const errorTurno = ref("");

async function cargar(desde) {
  errorSemana.value = "";
  celda.value = null;
  try {
    cuadrante.value = await semana(props.token, desde, props.propia);
    semanaDesde.value = cuadrante.value.desde;
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

function esFin(indice) {
  return indice >= 5;
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

function editando(trabajador, dia) {
  return celda.value && celda.value.login === trabajador.login && celda.value.fecha === dia.fecha;
}

function abrirCelda(trabajador, dia) {
  if (!props.editable) {
    return;
  }
  const turno = dia.turno;
  celda.value = {
    login: trabajador.login,
    nombre: trabajador.nombre,
    fecha: dia.fecha,
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
}

function cerrarCelda() {
  celda.value = null;
  errorTurno.value = "";
}

async function aplicar() {
  errorSemana.value = "";
  try {
    await aplicarHorarios(props.token, semanaDesde.value);
    await cargar(semanaDesde.value);
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudieron aplicar los horarios";
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
    await cargar(semanaDesde.value);
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo guardar el turno";
  }
}

defineExpose({ recargar: () => cargar(semanaDesde.value || lunesDe(new Date())) });
cargar(lunesDe(new Date()));
</script>

<template>
  <section v-if="cuadrante" class="semana" :class="{ lectura: !editable }">
    <div class="semana-nav">
      <button type="button" @click="cargar(sumarDias(semanaDesde, -7))">Semana anterior</button>
      <span class="rango">{{ fechaVisible(cuadrante.desde) }} – {{ fechaVisible(cuadrante.dias[6]) }}</span>
      <button type="button" @click="cargar(sumarDias(semanaDesde, 7))">Semana siguiente</button>
      <button v-if="editable" type="button" @click="aplicar">Aplicar horarios</button>
      <button v-if="editable" type="button" @click="copiar">Copiar semana anterior</button>
    </div>
    <p v-if="!editable" class="aviso-lectura">Solo lectura</p>
    <p v-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
    <table class="cuadrante">
      <thead>
        <tr>
          <th>Trabajador</th>
          <th v-for="(dia, indice) in cuadrante.dias" :key="dia" :class="{ fin: esFin(indice) }">
            <span class="dia-nombre">{{ diasNombre[indice] }}</span>
            <span class="dia-numero">{{ fechaVisible(dia).slice(0, 5) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="trabajador in cuadrante.trabajadores" :key="trabajador.login">
          <th>{{ trabajador.nombre }}</th>
          <td
            v-for="(dia, indice) in trabajador.dias"
            :key="dia.fecha"
            :class="[
              esFin(indice) ? 'fin' : '',
              editando(trabajador, dia) ? 'editando' : familia(dia.turno) ? `turno-${familia(dia.turno)}` : '',
            ]"
          >
            <form v-if="editando(trabajador, dia)" class="editor-celda" @submit.prevent="guardar">
              <label>
                Tipo
                <select v-model="turnoModo">
                  <option value="horario">Horario</option>
                  <option value="ausencia">Ausencia</option>
                </select>
              </label>
              <template v-if="turnoModo === 'horario'">
                <label>
                  Inicio
                  <input v-model="turnoInicio" type="time" required />
                </label>
                <label>
                  Fin
                  <input v-model="turnoFin" type="time" required />
                </label>
              </template>
              <label v-else>
                Ausencia
                <select v-model="turnoAusencia">
                  <option v-for="codigo in ausencias" :key="codigo" :value="codigo">{{ codigo }}</option>
                </select>
              </label>
              <span class="editor-acciones">
                <button type="submit">Guardar</button>
                <button type="button" @click="cerrarCelda">Cancelar</button>
              </span>
              <p v-if="errorTurno" class="error" role="alert">{{ errorTurno }}</p>
            </form>
            <button
              v-else-if="editable"
              type="button"
              class="celda"
              @click="abrirCelda(trabajador, dia)"
            >
              {{ textoCelda(dia.turno) }}
            </button>
            <span v-else class="celda lectura">{{ textoCelda(dia.turno) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <ul class="leyenda">
      <li v-for="item in leyenda" :key="item.id">
        <span class="muestra" :class="`turno-${item.id}`"></span>
        {{ item.nombre }}
      </li>
    </ul>
  </section>
  <p v-else-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
</template>
