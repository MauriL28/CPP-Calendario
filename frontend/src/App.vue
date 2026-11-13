<script setup>
import { computed, onMounted, ref } from "vue";
import Admin from "./componentes/Admin.vue";
import Login from "./componentes/Login.vue";
import Mando from "./componentes/Mando.vue";
import Trabajador from "./componentes/Trabajador.vue";
import logo from "./assets/logo.png";
import { salir as salirRemoto } from "./api/auth.js";
import { delegacionVisible, rolVisible } from "./fechas.js";
import {
  alPerderSesion,
  borrarToken,
  cerrarSesion,
  guardarToken,
  leerToken,
  rearmarAvisoSesion,
  sesionDesdeToken,
} from "./sesion.js";

const rol = ref("");
const login = ref("");
const nombre = ref("");
const departamento = ref("");
const token = ref("");
const delegaciones = ref([]);
const cargando = ref(true);

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

function aplicar(sesion) {
  rol.value = sesion.rol;
  login.value = sesion.login;
  nombre.value = sesion.nombre;
  departamento.value = sesion.departamento;
  token.value = sesion.token;
  delegaciones.value = sesion.delegaciones;
  guardarToken(sesion.token);
  rearmarAvisoSesion();
}

function alEntrar(sesion) {
  aplicar(sesion);
}

function alMarca() {
  marcaPaso.value += 1;
}

function limpiarLocal() {
  borrarToken();
  rol.value = "";
  login.value = "";
  nombre.value = "";
  departamento.value = "";
  token.value = "";
  delegaciones.value = [];
}

alPerderSesion(limpiarLocal);

async function salir() {
  const actual = token.value;
  limpiarLocal();
  await cerrarSesion(actual, salirRemoto);
}

onMounted(() => {
  const guardado = leerToken();
  const sesion = sesionDesdeToken(guardado);
  if (sesion) {
    aplicar(sesion);
  } else if (guardado) {
    borrarToken();
  }
  cargando.value = false;
});
</script>

<template>
  <p v-if="cargando" class="cargando-sesion">Cargando…</p>
  <Login v-else-if="!rol" @entrada="alEntrar" />
  <template v-else>
    <header class="cabecera">
      <div class="cabecera-interior">
        <button v-if="rol !== 'trabajador'" type="button" class="marca" @click="alMarca">
          <img class="marca-logo" :src="logo" alt="STEF" />
          <span class="marca-sep"></span>
          <h1>STEF365</h1>
        </button>
        <div v-else class="marca">
          <img class="marca-logo" :src="logo" alt="STEF" />
          <span class="marca-sep"></span>
          <h1>STEF365</h1>
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
      <Admin
        v-if="rol === 'admin'"
        :key="marcaPaso"
        :token="token"
        :delegaciones="delegaciones"
        :nombre-sesion="nombre"
      />
      <Mando
        v-else-if="rol === 'mando'"
        :key="marcaPaso"
        :token="token"
        :nombre-sesion="nombre"
        :departamento="departamento"
      />
      <Trabajador
        v-else-if="rol === 'trabajador'"
        :token="token"
        :login="login"
        :nombre-sesion="nombre"
        :departamento="departamento"
      />
    </main>
    <footer class="pie">
      <div class="pie-interior">
        <p class="pie-marca">STEF365</p>
        <p class="pie-meta">STEF · {{ anio }}</p>
      </div>
    </footer>
  </template>
</template>

<style scoped>
.cargando-sesion {
  margin: 4rem auto;
  text-align: center;
  color: var(--text-2);
}
</style>
