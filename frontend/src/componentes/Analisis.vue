<script setup>
import { onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { analisisFichajes, exportarAnalisis } from "../api/fichajes.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  mando: { type: Boolean, default: false },
});

const departamentos = ref([]);
const departamento = ref("");
const estado = ref("");
const desde = ref("");
const hasta = ref("");
const datos = ref(null);
const error = ref("");

const estados = [
  { valor: "", texto: "Todos los estados" },
  { valor: "ok", texto: "Correctos" },
  { valor: "descuadre", texto: "Descuadres" },
  { valor: "sin_plan", texto: "Sin plan" },
  { valor: "sin_emparejar", texto: "Sin emparejar" },
];

const etiquetas = {
  ok: "Correcto",
  descuadre: "Descuadre",
  sin_plan: "Sin plan",
  sin_emparejar: "Sin emparejar",
};

const kpis = [
  { clave: "total", texto: "Total" },
  { clave: "ok", texto: "Correctos" },
  { clave: "descuadre", texto: "Descuadres" },
  { clave: "sin_plan", texto: "Sin plan" },
  { clave: "sin_emparejar", texto: "Sin emparejar" },
];

function nombreDepartamento(item) {
  return `${item.nombre} · ${delegacionVisible(item.delegacion)}`;
}

function fechaVisible(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function horasVisible(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  return Number(valor).toLocaleString("es-ES", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function diferenciaVisible(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  const numero = Number(valor);
  const texto = Math.abs(numero).toLocaleString("es-ES", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  if (numero > 0) {
    return `+${texto}`;
  }
  if (numero < 0) {
    return `-${texto}`;
  }
  return texto;
}

function claseEstado(coincide) {
  if (coincide === "ok") {
    return "estado-ok";
  }
  if (coincide === "descuadre") {
    return "estado-descuadre";
  }
  return "estado-aviso";
}

async function cargarDepartamentos() {
  departamentos.value = await listar(props.token);
  if (props.mando && departamentos.value.length) {
    departamento.value = departamentos.value[0].id;
  }
}

function filtrosActuales() {
  return {
    departamento: props.mando ? "" : departamento.value,
    coincide: estado.value,
    desde: desde.value,
    hasta: hasta.value,
  };
}

async function exportar() {
  error.value = "";
  try {
    await exportarAnalisis(props.token, filtrosActuales());
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo exportar el análisis";
  }
}

async function cargar() {
  error.value = "";
  try {
    datos.value = await analisisFichajes(props.token, filtrosActuales());
  } catch (causa) {
    datos.value = null;
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar el análisis";
  }
}

watch([departamento, estado, desde, hasta], cargar);

onMounted(async () => {
  try {
    await cargarDepartamentos();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
  if (!props.mando || !departamento.value) {
    await cargar();
  }
});
</script>

<template>
  <section class="analisis">
    <header class="equipo-intro">
      <h1>Análisis</h1>
      <p>Días ya cruzados con el turno. Una incidencia no entra, porque aún no tiene horas.</p>
    </header>
    <div class="equipo-barra">
      <label class="analisis-filtro">
        Departamento
        <select v-model="departamento" class="equipo-grupo">
          <option v-if="!mando" value="">Todos los departamentos</option>
          <option v-for="item in departamentos" :key="item.id" :value="item.id">
            {{ nombreDepartamento(item) }}
          </option>
        </select>
      </label>
      <label class="analisis-filtro">
        Estado
        <select v-model="estado" class="equipo-grupo">
          <option v-for="item in estados" :key="item.valor" :value="item.valor">{{ item.texto }}</option>
        </select>
      </label>
      <label class="analisis-filtro">
        Desde
        <input v-model="desde" class="equipo-buscar" type="date" />
      </label>
      <label class="analisis-filtro">
        Hasta
        <input v-model="hasta" class="equipo-buscar" type="date" />
      </label>
      <button type="button" class="primario" @click="exportar">Exportar</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else-if="datos">
      <div class="rejilla-deptos">
        <div v-for="kpi in kpis" :key="kpi.clave" class="tarjeta analisis-kpi">
          <span class="tarjeta-nombre">{{ datos.totales[kpi.clave] }}</span>
          <span class="tarjeta-recuento">{{ kpi.texto }}</span>
        </div>
      </div>
      <section class="panel">
        <p v-if="!datos.filas.length" class="panel-vacio">Sin resultados con ese filtro.</p>
        <table v-else class="equipo">
          <thead>
            <tr>
              <th>Trabajador</th>
              <th>Fecha</th>
              <th>Previsto</th>
              <th>Fichado</th>
              <th>Pausa</th>
              <th>Diferencia</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fila in datos.filas" :key="`${fila.nombre}-${fila.fecha}-${fila.coincide}`">
              <td>
                <span class="persona-datos">
                  <strong>{{ fila.nombre }}</strong>
                  <span v-if="fila.departamento">{{ fila.departamento }}</span>
                </span>
              </td>
              <td>{{ fechaVisible(fila.fecha) }}</td>
              <td>{{ horasVisible(fila.horas_planificadas) }}</td>
              <td>{{ horasVisible(fila.horas_trabajadas) }}</td>
              <td>{{ horasVisible(fila.horas_pausa) }}</td>
              <td>{{ diferenciaVisible(fila.diferencia) }}</td>
              <td>
                <span class="estado-pastilla" :class="claseEstado(fila.coincide)">
                  {{ etiquetas[fila.coincide] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>
