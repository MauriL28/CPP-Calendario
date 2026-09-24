<script setup>
import { ref } from "vue";
import { entrar } from "../api/auth.js";

const emit = defineEmits(["inicio", "entrada"]);

const usuario = ref("");
const clave = ref("");
const error = ref("");

async function enviar() {
  error.value = "";
  emit("inicio");
  try {
    const sesion = await entrar(usuario.value, clave.value);
    emit("entrada", sesion);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo entrar";
  }
}
</script>

<template>
  <form class="formulario" @submit.prevent="enviar">
    <label>
      Usuario
      <input v-model="usuario" name="usuario" autocomplete="username" />
    </label>
    <label>
      Clave
      <input v-model="clave" name="clave" type="password" autocomplete="current-password" />
    </label>
    <button type="submit">Entrar</button>
  </form>
  <p v-if="error" class="error">{{ error }}</p>
</template>
