<script setup>
import { ref } from "vue";
import Admin from "./componentes/Admin.vue";
import Login from "./componentes/Login.vue";
import Mando from "./componentes/Mando.vue";
import Trabajador from "./componentes/Trabajador.vue";

const rol = ref("");
const token = ref("");
const delegaciones = ref([]);

function alEmpezar() {
  rol.value = "";
  token.value = "";
  delegaciones.value = [];
}

function alEntrar(sesion) {
  rol.value = sesion.rol;
  token.value = sesion.token;
  delegaciones.value = sesion.delegaciones;
}
</script>

<template>
  <main>
    <h1>CPP-Calendario</h1>
    <Login @inicio="alEmpezar" @entrada="alEntrar" />
    <p v-if="rol">Rol: {{ rol }}</p>
    <Admin v-if="rol === 'admin'" :token="token" :delegaciones="delegaciones" />
    <Mando v-else-if="rol === 'mando'" :token="token" :delegaciones="delegaciones" />
    <Trabajador v-else-if="rol === 'trabajador'" :token="token" />
  </main>
</template>
