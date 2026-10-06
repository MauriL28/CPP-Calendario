<script setup>
import { ref } from "vue";
import Cuadrante from "./Cuadrante.vue";
import FichaEmpleado from "./FichaEmpleado.vue";

defineProps({
  token: { type: String, required: true },
  login: { type: String, required: true },
});

const ficha = ref(false);
</script>

<template>
  <header v-if="!ficha" class="mi-horario">
    <h1>Mi horario</h1>
    <p>Turnos de la semana seleccionada.</p>
    <button type="button" class="enlace" @click="ficha = true">Ver ficha</button>
  </header>
  <header v-else class="mi-horario">
    <button type="button" class="enlace" @click="ficha = false">Mi horario</button>
  </header>
  <div v-show="!ficha">
    <Cuadrante :token="token" propia />
  </div>
  <FichaEmpleado v-if="ficha" :token="token" :login="login" />
</template>
