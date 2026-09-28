<script setup>
import { computed, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { crearMando } from "../api/usuarios.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const departamentos = ref([]);
const error = ref("");
const elegido = ref(null);
const nombre = ref("");
const login = ref("");
const clave = ref("");
const errorMando = ref("");

const actual = computed(() => {
  if (!elegido.value) {
    return null;
  }
  return (
    departamentos.value.find(
      (item) =>
        item.delegacion === elegido.value.delegacion && item.codigo === elegido.value.codigo,
    ) || null
  );
});

function departamentosDe(codigo) {
  return departamentos.value.filter((item) => item.delegacion === codigo);
}

function personas(departamento) {
  const total = departamento.mandos.length + departamento.trabajadores.length;
  return total === 1 ? "1 persona" : `${total} personas`;
}

function abrir(departamento) {
  errorMando.value = "";
  elegido.value = { delegacion: departamento.delegacion, codigo: departamento.codigo };
}

function volver() {
  errorMando.value = "";
  elegido.value = null;
}

async function cargar() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

async function guardar() {
  if (!elegido.value) {
    return;
  }
  errorMando.value = "";
  try {
    await crearMando(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      delegacion: elegido.value.delegacion,
      departamento: elegido.value.codigo,
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
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <div v-if="!actual" class="bloques">
    <section v-for="codigo in delegaciones" :key="codigo" class="delegacion">
      <h2>{{ delegacionVisible(codigo) }}</h2>
      <div class="rejilla-deptos">
        <button
          v-for="departamento in departamentosDe(codigo)"
          :key="departamento.codigo"
          type="button"
          class="tarjeta"
          @click="abrir(departamento)"
        >
          <strong>{{ departamento.nombre }}</strong>
          <span>{{ personas(departamento) }}</span>
        </button>
      </div>
    </section>
  </div>
  <section v-else class="detalle">
    <button type="button" class="volver" @click="volver">Volver a las delegaciones</button>
    <h2>{{ delegacionVisible(actual.delegacion) }} · {{ actual.nombre }}</h2>
    <div class="zona-mandos">
      <div>
        <h3>Mandos</h3>
        <ul class="personas">
          <li v-if="!actual.mandos.length" class="vacio">Sin mandos</li>
          <li v-for="mando in actual.mandos" :key="mando.login">
            <strong>{{ mando.nombre }}</strong>
            <span>{{ mando.login }}</span>
          </li>
        </ul>
      </div>
      <form class="formulario junto" @submit.prevent="guardar">
        <h2>Alta de mando</h2>
        <p class="dato-fijo">Delegación <strong>{{ delegacionVisible(actual.delegacion) }}</strong></p>
        <p class="dato-fijo">Departamento <strong>{{ actual.nombre }}</strong></p>
        <label>
          Nombre
          <input v-model="nombre" name="nombre" autocomplete="off" />
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
        <p v-if="errorMando" class="error" role="alert">{{ errorMando }}</p>
      </form>
    </div>
    <h3>Trabajadores</h3>
    <ul class="personas">
      <li v-if="!actual.trabajadores.length" class="vacio">Sin trabajadores</li>
      <li v-for="trabajador in actual.trabajadores" :key="trabajador.login">
        <strong>{{ trabajador.nombre }}</strong>
        <span>{{ trabajador.login }}</span>
        <span>{{ trabajador.grupo }}</span>
      </li>
    </ul>
  </section>
</template>
