<script setup>
import { ref } from "vue";
import { lunesDe, sumarDias, textoCelda } from "../fechas.js";
import { copiarSemana, guardarTurno, semana } from "../api/turnos.js";

const props = defineProps({
  token: { type: String, required: true },
  propia: { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
});

const diasNombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
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

function abrirCelda(trabajador, dia) {
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
  <section v-if="cuadrante" class="semana">
    <div class="semana-nav">
      <button type="button" @click="cargar(sumarDias(semanaDesde, -7))">Semana anterior</button>
      <span>{{ cuadrante.desde }} – {{ cuadrante.dias[6] }}</span>
      <button type="button" @click="cargar(sumarDias(semanaDesde, 7))">Semana siguiente</button>
      <button v-if="editable" type="button" @click="copiar">Copiar semana anterior</button>
    </div>
    <p v-if="errorSemana" class="error">{{ errorSemana }}</p>
    <table class="cuadrante">
      <thead>
        <tr>
          <th>Trabajador</th>
          <th v-for="(dia, indice) in cuadrante.dias" :key="dia">
            <span class="dia-nombre">{{ diasNombre[indice] }}</span>
            <span class="dia-numero">{{ dia.slice(8) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="trabajador in cuadrante.trabajadores" :key="trabajador.login">
          <th>{{ trabajador.nombre }}</th>
          <td
            v-for="dia in trabajador.dias"
            :key="dia.fecha"
            :class="{ ausencia: dia.turno?.ausencia, horario: dia.turno && !dia.turno.ausencia }"
          >
            <button v-if="editable" type="button" class="celda" @click="abrirCelda(trabajador, dia)">
              {{ textoCelda(dia.turno) }}
            </button>
            <span v-else class="celda">{{ textoCelda(dia.turno) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <form v-if="editable && celda" class="formulario" @submit.prevent="guardar">
      <p class="celda-titulo">{{ celda.nombre }} · {{ celda.fecha }}</p>
      <label>
        Tipo
        <select v-model="turnoModo">
          <option value="horario">Horario</option>
          <option value="ausencia">Ausencia</option>
        </select>
      </label>
      <template v-if="turnoModo === 'horario'">
        <label>
          Hora inicio
          <input v-model="turnoInicio" type="time" required />
        </label>
        <label>
          Hora fin
          <input v-model="turnoFin" type="time" required />
        </label>
      </template>
      <label v-else>
        Ausencia
        <select v-model="turnoAusencia">
          <option v-for="codigo in ['L', 'D', 'V', 'B', 'F', 'P']" :key="codigo" :value="codigo">
            {{ codigo }}
          </option>
        </select>
      </label>
      <button type="submit">Guardar turno</button>
    </form>
    <p v-if="errorTurno" class="error">{{ errorTurno }}</p>
  </section>
  <p v-else-if="errorSemana" class="error">{{ errorSemana }}</p>
</template>
