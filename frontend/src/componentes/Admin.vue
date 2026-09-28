<script setup>
import { computed, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { crearMando } from "../api/usuarios.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const departamentos = ref([]);
const error = ref("");
const elegido = ref(null);
const nombre = ref("");
const login = ref("");
const clave = ref("");
const errorMando = ref("");

const actual = computed(() => {
  if (!elegido.value) {
    return null;
  }
  return (
    departamentos.value.find(
      (item) =>
        item.delegacion === elegido.value.delegacion && item.codigo === elegido.value.codigo,
    ) || null
  );
});

function departamentosDe(codigo) {
  return departamentos.value.filter((item) => item.delegacion === codigo);
}

function ciudad(codigo) {
  const visible = delegacionVisible(codigo);
  const prefijo = `${codigo} `;
  return visible.startsWith(prefijo) ? visible.slice(prefijo.length) : "";
}

function iniciales(nombre) {
  const palabras = nombre.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  return palabras
    .slice(0, 2)
    .map((parte) => parte[0].toLocaleUpperCase("es"))
    .join("");
}

function cifra(total, uno, varios) {
  return total === 1 ? `1 ${uno}` : `${total} ${varios}`;
}

function recuento(departamento) {
  return `${cifra(departamento.mandos.length, "mando", "mandos")} · ${cifra(departamento.trabajadores.length, "trabajador", "trabajadores")}`;
}

function abrir(departamento) {
  errorMando.value = "";
  elegido.value = { delegacion: departamento.delegacion, codigo: departamento.codigo };
}

function volver() {
  errorMando.value = "";
  elegido.value = null;
}

async function cargar() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

async function guardar() {
  if (!elegido.value) {
    return;
  }
  errorMando.value = "";
  try {
    await crearMando(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      delegacion: elegido.value.delegacion,
      departamento: elegido.value.codigo,
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    await cargar();
  } catch (causa) {
    errorMando.value = causa instanceof Error ? causa.message : "No se pudo crear el mando";
  }
}

onMounted(cargar);
</script>

<template>
  <p v-if="error" class="error" role="alert">{{ error }}</p>
  <div v-if="!actual" class="bloques">
    <header class="lista-intro">
      <h1>Departamentos</h1>
      <p>Selecciona un departamento para gestionar su equipo.</p>
    </header>
    <section v-for="codigo in delegaciones" :key="codigo" class="delegacion">
      <div class="delegacion-cabecera">
        <template v-if="ciudad(codigo)">
          <span class="delegacion-codigo">{{ codigo }}</span>
          <span class="delegacion-nombre">{{ ciudad(codigo) }}</span>
        </template>
        <span v-else class="delegacion-nombre">{{ delegacionVisible(codigo) }}</span>
      </div>
      <div class="rejilla-deptos">
        <button
          v-for="departamento in departamentosDe(codigo)"
          :key="departamento.codigo"
          type="button"
          class="tarjeta"
          @click="abrir(departamento)"
        >
          <span class="tarjeta-iniciales">{{ iniciales(departamento.nombre) }}</span>
          <span class="tarjeta-nombre">{{ departamento.nombre }}</span>
          <span class="tarjeta-recuento">{{ recuento(departamento) }}</span>
        </button>
      </div>
    </section>
  </div>
  <section v-else class="detalle">
    <nav class="migas">
      <button type="button" class="migas-enlace" @click="volver">Departamentos</button>
      <span>›</span>
      <span class="migas-medio">{{ delegacionVisible(actual.delegacion) }}</span>
      <span>›</span>
      <span class="migas-actual">{{ actual.nombre }}</span>
    </nav>
    <header class="detalle-cabecera">
      <span class="detalle-iniciales">{{ iniciales(actual.nombre) }}</span>
      <div>
        <h1>{{ actual.nombre }}</h1>
        <p class="detalle-chip">{{ delegacionVisible(actual.delegacion) }}</p>
      </div>
    </header>
    <div class="detalle-rejilla">
      <div class="detalle-listas">
        <section class="panel">
          <header class="panel-cabecera">
            <h2>Mandos</h2>
            <span class="panel-cuenta">{{ actual.mandos.length }}</span>
          </header>
          <p v-if="!actual.mandos.length" class="panel-vacio">Este departamento aún no tiene mandos.</p>
          <ul v-else class="panel-filas">
            <li v-for="mando in actual.mandos" :key="mando.login">
              <span class="avatar">{{ iniciales(mando.nombre) }}</span>
              <span class="persona-datos">
                <strong>{{ mando.nombre }}</strong>
                <span>{{ mando.login }}</span>
              </span>
            </li>
          </ul>
        </section>
        <section class="panel">
          <header class="panel-cabecera">
            <h2>Trabajadores</h2>
            <span class="panel-cuenta">{{ actual.trabajadores.length }}</span>
          </header>
          <p v-if="!actual.trabajadores.length" class="panel-vacio">
            Aún no hay trabajadores. Los crea el mando del departamento.
          </p>
          <ul v-else class="panel-filas">
            <li v-for="trabajador in actual.trabajadores" :key="trabajador.login">
              <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
              <span class="persona-datos">
                <strong>{{ trabajador.nombre }}</strong>
                <span>{{ trabajador.login }}</span>
              </span>
              <span class="grupo-pastilla" :class="trabajador.grupo === 'ETT' ? 'grupo-ett' : 'grupo-stef'">
                {{ trabajador.grupo }}
              </span>
            </li>
          </ul>
        </section>
      </div>
      <form class="panel alta-mando" @submit.prevent="guardar">
        <header class="panel-cabecera">
          <h2>Alta de mando</h2>
        </header>
        <div class="alta-cuerpo">
          <p class="alta-aviso">
            Se creará en {{ delegacionVisible(actual.delegacion) }} · {{ actual.nombre }}
          </p>
          <label>
            Nombre
            <input v-model="nombre" name="nombre" autocomplete="off" />
          </label>
          <label>
            Login
            <input v-model="login" name="login" autocomplete="off" />
          </label>
          <label>
            Clave
            <input v-model="clave" name="clave-mando" type="password" autocomplete="new-password" />
          </label>
          <p v-if="errorMando" class="error" role="alert">{{ errorMando }}</p>
          <button class="primario" type="submit">Guardar mando</button>
        </div>
      </form>
    </div>
  </section>
</template>
