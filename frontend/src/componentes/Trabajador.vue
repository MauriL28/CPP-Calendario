<script setup>
import Cuadrante from "./Cuadrante.vue";

defineProps({
  token: { type: String, required: true },
});
</script>

<template>
  <header class="mi-horario">
    <h1>Mi horario</h1>
    <p>Turnos de la semana seleccionada.</p>
  </header>
  <Cuadrante :token="token" propia />
</template>
