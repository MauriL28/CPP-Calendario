<script setup>
import { onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { crearMando } from "../api/usuarios.js";
import ListadoDepartamentos from "./ListadoDepartamentos.vue";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const departamentos = ref([]);
const error = ref("");
const delegacion = ref(props.delegaciones[0] ?? "");
const departamento = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const errorMando = ref("");

function departamentosDe(codigo) {
  return departamentos.value.filter((item) => item.delegacion === codigo);
}

function alCambiarDelegacion() {
  const lista = departamentosDe(delegacion.value);
  if (!lista.some((item) => item.codigo === departamento.value)) {
    departamento.value = lista[0]?.codigo ?? "";
  }
}

async function cargar() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
    alCambiarDelegacion();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

async function guardar() {
  errorMando.value = "";
  try {
    await crearMando(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      delegacion: delegacion.value,
      departamento: departamento.value,
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    await cargar();
  } catch (causa) {
    errorMando.value = causa instanceof Error ? causa.message : "No se pudo crear el mando";
  }
}

onMounted(cargar);
</script>

<template>
  <form class="formulario" @submit.prevent="guardar">
    <label>
      Delegación
      <select v-model="delegacion" @change="alCambiarDelegacion">
        <option v-for="codigo in delegaciones" :key="codigo" :value="codigo">{{ codigo }}</option>
      </select>
    </label>
    <label>
      Departamento
      <select v-model="departamento">
        <option v-for="item in departamentosDe(delegacion)" :key="item.codigo" :value="item.codigo">
          {{ item.nombre }}
        </option>
      </select>
    </label>
    <label>
      Nombre
      <input v-model="nombre" name="nombre" />
    </label>
    <label>
      Login
      <input v-model="login" name="login" autocomplete="off" />
    </label>
    <label>
      Clave
      <input v-model="clave" name="clave-mando" type="password" autocomplete="new-password" />
    </label>
    <button type="submit">Guardar mando</button>
  </form>
  <p v-if="errorMando" class="error">{{ errorMando }}</p>
  <p v-if="error" class="error">{{ error }}</p>
  <ListadoDepartamentos :delegaciones="delegaciones" :departamentos="departamentos" />
</template>
