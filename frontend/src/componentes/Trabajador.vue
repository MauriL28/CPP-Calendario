<script setup>
import Cuadrante from "./Cuadrante.vue";

defineProps({
  token: { type: String, required: true },
});
</script>

<template>
  <Cuadrante :token="token" propia />
</template>
