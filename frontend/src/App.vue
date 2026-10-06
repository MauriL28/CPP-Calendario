<script setup>
import { computed, ref } from "vue";
import Admin from "./componentes/Admin.vue";
import Login from "./componentes/Login.vue";
import Mando from "./componentes/Mando.vue";
import Trabajador from "./componentes/Trabajador.vue";
import logo from "./assets/logo.png";
import { delegacionVisible, rolVisible } from "./fechas.js";

const rol = ref("");
const login = ref("");
const nombre = ref("");
const departamento = ref("");
const token = ref("");
const delegaciones = ref([]);

const lugares = computed(() => delegaciones.value.map(delegacionVisible).join(" · "));
const anio = new Date().getFullYear();
const marcaPaso = ref(0);
const iniciales = computed(() => {
  const palabras = nombre.value.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  return palabras
    .slice(0, 2)
    .map((parte) => parte[0].toLocaleUpperCase("es"))
    .join("");
});

function alEntrar(sesion) {
  rol.value = sesion.rol;
  login.value = sesion.login;
  nombre.value = sesion.nombre;
  departamento.value = sesion.departamento;
  token.value = sesion.token;
  delegaciones.value = sesion.delegaciones;
}

function alMarca() {
  marcaPaso.value += 1;
}

function salir() {
  rol.value = "";
  login.value = "";
  nombre.value = "";
  departamento.value = "";
  token.value = "";
  delegaciones.value = [];
}
</script>

<template>
  <Login v-if="!rol" @entrada="alEntrar" />
  <template v-else>
    <header class="cabecera">
      <div class="cabecera-interior">
        <button v-if="rol !== 'trabajador'" type="button" class="marca" @click="alMarca">
          <img class="marca-logo" :src="logo" alt="STEF" />
          <span class="marca-sep"></span>
          <h1>CPP-Calendario</h1>
        </button>
        <div v-else class="marca">
          <img class="marca-logo" :src="logo" alt="STEF" />
          <span class="marca-sep"></span>
          <h1>CPP-Calendario</h1>
        </div>
        <div class="sesion">
          <span class="avatar">{{ iniciales }}</span>
          <p class="quien">
            <strong>{{ nombre }}</strong>
            <span>{{ rolVisible(rol) }}</span>
          </p>
          <p v-if="rol === 'admin'" class="donde">{{ lugares }}</p>
          <p v-else class="donde">{{ lugares }} · {{ departamento }}</p>
          <span class="sesion-sep"></span>
          <button type="button" @click="salir">Salir</button>
        </div>
      </div>
    </header>
    <main>
      <Admin v-if="rol === 'admin'" :key="marcaPaso" :token="token" :delegaciones="delegaciones" />
      <Mando v-else-if="rol === 'mando'" :key="marcaPaso" :token="token" />
      <Trabajador v-else-if="rol === 'trabajador'" :token="token" :login="login" />
    </main>
    <footer class="pie">
      <div class="pie-interior">
        <p class="pie-marca">CPP-Calendario</p>
        <p class="pie-meta">STEF · {{ anio }}</p>
      </div>
    </footer>
  </template>
</template>
