<script setup>
import { computed, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { crearTrabajador } from "../api/usuarios.js";
import Cuadrante from "./Cuadrante.vue";

const props = defineProps({
  token: { type: String, required: true },
});

const vista = ref("cuadrante");
const cuadrante = ref(null);
const departamentos = ref([]);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const grupo = ref("STEF");
const horaInicio = ref("");
const horaFin = ref("");
const vacaciones = ref("");
const horasContrato = ref("");
const errorTrabajador = ref("");

const equipo = computed(() => departamentos.value[0] || null);

async function cargarDepartamentos() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

async function guardar() {
  errorTrabajador.value = "";
  try {
    await crearTrabajador(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      grupo: grupo.value,
      hora_inicio: horaInicio.value,
      hora_fin: horaFin.value,
      vacaciones: numero(vacaciones.value),
      horas_contrato: numero(horasContrato.value),
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    grupo.value = "STEF";
    horaInicio.value = "";
    horaFin.value = "";
    vacaciones.value = "";
    horasContrato.value = "";
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function numero(valor) {
  if (valor === "" || valor === null) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
}

onMounted(cargarDepartamentos);
</script>

<template>
  <nav class="vistas">
    <button type="button" :class="{ activo: vista === 'cuadrante' }" @click="vista = 'cuadrante'">
      Cuadrante
    </button>
    <button type="button" :class="{ activo: vista === 'equipo' }" @click="vista = 'equipo'">
      Equipo
    </button>
  </nav>
  <Cuadrante v-show="vista === 'cuadrante'" ref="cuadrante" :token="token" editable />
  <section v-if="vista === 'equipo'" class="detalle">
    <h2>Equipo</h2>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <ul v-if="equipo" class="personas">
      <li v-if="!equipo.trabajadores.length" class="vacio">Sin trabajadores</li>
      <li v-for="trabajador in equipo.trabajadores" :key="trabajador.login">
        <strong>{{ trabajador.nombre }}</strong>
        <span>{{ trabajador.login }}</span>
        <span>{{ trabajador.grupo }}</span>
      </li>
    </ul>
    <form class="formulario alta-aparte" @submit.prevent="guardar">
      <h2>Alta de trabajador</h2>
      <label>
        Nombre
        <input v-model="nombre" name="nombre-trabajador" />
      </label>
      <label>
        Login
        <input v-model="login" name="login-trabajador" autocomplete="off" />
      </label>
      <label>
        Clave
        <input v-model="clave" name="clave-trabajador" type="password" autocomplete="new-password" />
      </label>
      <label>
        Grupo
        <select v-model="grupo">
          <option value="STEF">STEF</option>
          <option value="ETT">ETT</option>
        </select>
      </label>
      <label>
        Hora de inicio
        <input v-model="horaInicio" name="hora-inicio" type="time" />
      </label>
      <label>
        Hora de fin
        <input v-model="horaFin" name="hora-fin" type="time" />
      </label>
      <label>
        Días de vacaciones al año
        <input v-model="vacaciones" name="vacaciones" type="number" min="0" step="0.5" />
      </label>
      <label>
        Horas de contrato a la semana
        <input v-model="horasContrato" name="horas-contrato" type="number" min="0" step="0.5" />
      </label>
      <button type="submit">Guardar trabajador</button>
      <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
    </form>
  </section>
</template>
