<script setup>
import { ref } from "vue";
import { entrar } from "../api/auth.js";

const emit = defineEmits(["entrada"]);

const usuario = ref("");
const clave = ref("");
const error = ref("");

async function enviar() {
  error.value = "";
  try {
    emit("entrada", await entrar(usuario.value, clave.value));
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo entrar";
  }
}
</script>

<template>
  <form class="login-caja" @submit.prevent="enviar">
    <label>
      Usuario
      <input v-model="usuario" name="usuario" autocomplete="username" required />
    </label>
    <label>
      Clave
      <input v-model="clave" name="clave" type="password" autocomplete="current-password" required />
    </label>
    <button type="submit">Entrar</button>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
  </form>
</template>
