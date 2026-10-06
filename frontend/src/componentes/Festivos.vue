<script setup>
import { onMounted, ref } from "vue";
import { borrarFestivo, crearFestivo, listarFestivos } from "../api/festivos.js";

const props = defineProps({
  token: { type: String, required: true },
});

const festivos = ref([]);
const fecha = ref("");
const nombre = ref("");
const error = ref("");

function fechaVisible(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

async function cargar() {
  error.value = "";
  try {
    festivos.value = await listarFestivos(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los festivos";
  }
}

async function anadir() {
  error.value = "";
  try {
    await crearFestivo(props.token, { fecha: fecha.value, nombre: nombre.value });
    fecha.value = "";
    nombre.value = "";
    await cargar();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo guardar el festivo";
  }
}

async function eliminar(festivo) {
  if (!window.confirm(`¿Eliminar el festivo ${festivo.nombre}?`)) {
    return;
  }
  error.value = "";
  try {
    await borrarFestivo(props.token, festivo.fecha);
    festivos.value = festivos.value.filter((item) => item.fecha !== festivo.fecha);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo eliminar el festivo";
  }
}

onMounted(cargar);
</script>

<template>
  <section class="festivos">
    <header class="equipo-intro">
      <h1>Festivos</h1>
      <p>Días festivos de la empresa. Valen para todas las sedes.</p>
    </header>
    <form class="equipo-barra" @submit.prevent="anadir">
      <label class="analisis-filtro">
        Fecha
        <input v-model="fecha" class="equipo-buscar" type="date" required />
      </label>
      <label class="analisis-filtro">
        Nombre
        <input v-model="nombre" class="equipo-buscar" required />
      </label>
      <button class="primario" type="submit">Añadir</button>
    </form>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section class="panel">
      <p v-if="!festivos.length" class="panel-vacio">Sin festivos registrados.</p>
      <table v-else class="equipo">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Nombre</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="festivo in festivos" :key="festivo.fecha">
            <td>{{ fechaVisible(festivo.fecha) }}</td>
            <td>{{ festivo.nombre }}</td>
            <td>
              <button type="button" @click="eliminar(festivo)">Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </section>
</template>
