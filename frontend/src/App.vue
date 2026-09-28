<script setup>
import { computed, ref } from "vue";
import Admin from "./componentes/Admin.vue";
import Login from "./componentes/Login.vue";
import Mando from "./componentes/Mando.vue";
import Trabajador from "./componentes/Trabajador.vue";
import { delegacionVisible, rolVisible } from "./fechas.js";

const rol = ref("");
const nombre = ref("");
const departamento = ref("");
const token = ref("");
const delegaciones = ref([]);

const lugares = computed(() => delegaciones.value.map(delegacionVisible).join(" · "));

function alEntrar(sesion) {
  rol.value = sesion.rol;
  nombre.value = sesion.nombre;
  departamento.value = sesion.departamento;
  token.value = sesion.token;
  delegaciones.value = sesion.delegaciones;
}

function salir() {
  rol.value = "";
  nombre.value = "";
  departamento.value = "";
  token.value = "";
  delegaciones.value = [];
}
</script>

<template>
  <main>
    <header class="cabecera">
      <h1>CPP-Calendario</h1>
      <div v-if="rol" class="sesion">
        <p class="quien">
          <strong>{{ nombre }}</strong>
          <span>{{ rolVisible(rol) }}</span>
        </p>
        <p v-if="rol === 'admin'" class="donde">{{ lugares }}</p>
        <p v-else class="donde">{{ lugares }} · {{ departamento }}</p>
        <button type="button" @click="salir">Salir</button>
      </div>
    </header>
    <Login v-if="!rol" @entrada="alEntrar" />
    <Admin v-else-if="rol === 'admin'" :token="token" :delegaciones="delegaciones" />
    <Mando v-else-if="rol === 'mando'" :token="token" />
    <Trabajador v-else-if="rol === 'trabajador'" :token="token" />
  </main>
</template>
