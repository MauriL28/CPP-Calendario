<script setup>
import { onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { crearTrabajador } from "../api/usuarios.js";
import Cuadrante from "./Cuadrante.vue";
import ListadoDepartamentos from "./ListadoDepartamentos.vue";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const cuadrante = ref(null);
const departamentos = ref([]);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const grupo = ref("STEF");
const errorTrabajador = ref("");

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
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

onMounted(cargarDepartamentos);
</script>

<template>
  <form class="formulario" @submit.prevent="guardar">
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
    <button type="submit">Guardar trabajador</button>
  </form>
  <p v-if="errorTrabajador" class="error">{{ errorTrabajador }}</p>
  <Cuadrante ref="cuadrante" :token="token" editable />
  <p v-if="error" class="error">{{ error }}</p>
  <ListadoDepartamentos :delegaciones="delegaciones" :departamentos="departamentos" />
</template>
