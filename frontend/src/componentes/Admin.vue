<script setup>
import { computed, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { importarFichajes } from "../api/fichajes.js";
import { crearMando } from "../api/usuarios.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const vista = ref("departamentos");
const departamentos = ref([]);
const error = ref("");
const elegido = ref(null);
const nombre = ref("");
const login = ref("");
const clave = ref("");
const errorMando = ref("");
const archivo = ref(null);
const enviando = ref(false);
const errorFichajes = ref("");
const resumen = ref(null);

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

function alArchivo(evento) {
  const elegidoArchivo = evento.target.files?.[0] ?? null;
  archivo.value = elegidoArchivo;
  errorFichajes.value = "";
  resumen.value = null;
}

async function importar() {
  if (!archivo.value || enviando.value) {
    return;
  }
  enviando.value = true;
  errorFichajes.value = "";
  resumen.value = null;
  try {
    resumen.value = await importarFichajes(props.token, archivo.value);
  } catch (causa) {
    errorFichajes.value = causa instanceof Error ? causa.message : "No se pudo importar el archivo";
  } finally {
    enviando.value = false;
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
  <nav class="vistas">
    <button type="button" :class="{ activo: vista === 'departamentos' }" @click="vista = 'departamentos'">
      Departamentos
    </button>
    <button type="button" :class="{ activo: vista === 'fichajes' }" @click="vista = 'fichajes'">
      Fichajes
    </button>
  </nav>
  <p v-if="vista === 'departamentos' && error" class="error" role="alert">{{ error }}</p>
  <div v-if="vista === 'departamentos' && !actual" class="bloques">
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
  <section v-else-if="vista === 'departamentos'" class="detalle">
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
  <section v-else class="fichajes">
    <header class="lista-intro">
      <h1>Fichajes</h1>
      <p>Importa el extracto de SAP. El archivo tiene que ser .xlsx, con la hoja Data.</p>
    </header>
    <form class="panel fichajes-form" @submit.prevent="importar">
      <header class="panel-cabecera">
        <h2>Importar</h2>
      </header>
      <div class="alta-cuerpo">
        <label>
          Archivo
          <input type="file" accept=".xlsx" @change="alArchivo" />
        </label>
        <p v-if="errorFichajes" class="error" role="alert">{{ errorFichajes }}</p>
        <button class="primario" type="submit" :disabled="enviando || !archivo">Importar</button>
      </div>
    </form>
    <dl v-if="resumen" class="panel fichajes-resumen">
      <div>
        <dt>Filas leídas</dt>
        <dd>{{ resumen.filas_leidas }}</dd>
      </div>
      <div>
        <dt>Emparejadas</dt>
        <dd>{{ resumen.emparejadas }}</dd>
      </div>
      <div>
        <dt>Sin emparejar</dt>
        <dd>{{ resumen.sin_emparejar }}</dd>
      </div>
      <div>
        <dt>Días con incidencia</dt>
        <dd>{{ resumen.dias_con_incidencia }}</dd>
      </div>
      <div>
        <dt>Filas nuevas</dt>
        <dd>{{ resumen.filas_nuevas }}</dd>
      </div>
    </dl>
  </section>
</template>
