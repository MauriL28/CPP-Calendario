<script setup>
import { ref } from "vue";
import { entrar } from "../api/auth.js";
import logo from "../assets/logo.png";

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
  <div class="login">
    <aside class="login-marca">
      <div class="login-logo">
        <img :src="logo" alt="STEF" />
      </div>
      <h1>CPP-Calendario</h1>
      <p>Calendario de turnos de delegación</p>
    </aside>
    <section class="login-panel">
      <form class="login-form" @submit.prevent="enviar">
        <h2>Iniciar sesión</h2>
        <p class="login-sub">Accede con tu usuario y clave</p>
        <label>
          Usuario
          <input v-model="usuario" name="usuario" autocomplete="username" autofocus required />
        </label>
        <label>
          Clave
          <input v-model="clave" name="clave" type="password" autocomplete="current-password" required />
        </label>
        <p v-if="error" class="error" role="alert">{{ error }}</p>
        <button class="primario" type="submit">Entrar</button>
      </form>
    </section>
  </div>
</template>
