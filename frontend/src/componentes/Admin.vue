<script setup>
import { computed, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import { importarFichajes } from "../api/fichajes.js";
import Analisis from "./Analisis.vue";
import { cambiarNumeroSapMando, crearMando } from "../api/usuarios.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
});

const vista = ref("departamentos");
const departamentos = ref([]);
const error = ref("");
const elegido = ref(null);
const sedeAlta = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const numeroSap = ref("");
const errorMando = ref("");
const dialogoSap = ref(null);
const mandoSap = ref(null);
const numeroSapEdit = ref("");
const errorSap = ref("");
const archivo = ref(null);
const enviando = ref(false);
const errorFichajes = ref("");
const resumen = ref(null);

const tarjetas = computed(() => {
  const porCodigo = new Map();
  for (const item of departamentos.value) {
    const personas = item.mandos.length + item.trabajadores.length;
    const grupo = porCodigo.get(item.codigo);
    if (!grupo) {
      porCodigo.set(item.codigo, {
        codigo: item.codigo,
        nombre: item.nombre,
        orden: item.orden,
        personas,
      });
      continue;
    }
    grupo.personas += personas;
    if (item.orden < grupo.orden) {
      grupo.orden = item.orden;
      grupo.nombre = item.nombre;
    }
  }
  return [...porCodigo.values()].sort((a, b) => a.orden - b.orden);
});

const grupo = computed(() => {
  if (!elegido.value) {
    return null;
  }
  const sedes = departamentos.value.filter((item) => item.codigo === elegido.value);
  if (!sedes.length) {
    return null;
  }
  const base = sedes.reduce((menor, item) => (item.orden < menor.orden ? item : menor));
  return {
    codigo: base.codigo,
    nombre: base.nombre,
    sedes: props.delegaciones.map((codigo) => {
      return (
        sedes.find((item) => item.delegacion === codigo) || {
          delegacion: codigo,
          mandos: [],
          trabajadores: [],
        }
      );
    }),
  };
});

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

function abrir(tarjeta) {
  errorMando.value = "";
  sedeAlta.value = "";
  elegido.value = tarjeta.codigo;
}

function abrirSap(mando) {
  mandoSap.value = mando;
  numeroSapEdit.value = mando.numero_sap || "";
  errorSap.value = "";
  dialogoSap.value?.showModal();
  dialogoSap.value?.querySelector("[name='numero-sap-mando']")?.focus();
}

function cerrarSap() {
  dialogoSap.value?.close();
}

function alCerrarSap() {
  mandoSap.value = null;
  errorSap.value = "";
}

function alFondoSap(evento) {
  if (evento.target === dialogoSap.value) {
    cerrarSap();
  }
}

async function guardarSap() {
  const persona = mandoSap.value;
  if (!persona) {
    return;
  }
  errorSap.value = "";
  try {
    const respuesta = await cambiarNumeroSapMando(props.token, persona.login, numeroSapEdit.value);
    persona.numero_sap = respuesta.numero_sap;
    cerrarSap();
  } catch (causa) {
    errorSap.value = causa instanceof Error ? causa.message : "No se pudo guardar el número";
  }
}

function volver() {
  errorMando.value = "";
  sedeAlta.value = "";
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
  if (!grupo.value || !sedeAlta.value) {
    return;
  }
  errorMando.value = "";
  try {
    await crearMando(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      delegacion: sedeAlta.value,
      departamento: grupo.value.codigo,
      numero_sap: numeroSap.value,
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    numeroSap.value = "";
    sedeAlta.value = "";
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
    <button type="button" :class="{ activo: vista === 'analisis' }" @click="vista = 'analisis'">
      Análisis
    </button>
  </nav>
  <p v-if="vista === 'departamentos' && error" class="error" role="alert">{{ error }}</p>
  <div v-if="vista === 'departamentos' && !grupo" class="bloques">
    <header class="lista-intro">
      <h1>Departamentos</h1>
      <p>Selecciona un departamento para gestionar su equipo.</p>
    </header>
    <div class="rejilla-deptos">
      <button
        v-for="tarjeta in tarjetas"
        :key="tarjeta.codigo"
        type="button"
        class="tarjeta"
        @click="abrir(tarjeta)"
      >
        <span class="tarjeta-iniciales">{{ iniciales(tarjeta.nombre) }}</span>
        <span class="tarjeta-nombre">{{ tarjeta.nombre }}</span>
        <span class="tarjeta-recuento">{{ cifra(tarjeta.personas, "persona", "personas") }}</span>
      </button>
    </div>
  </div>
  <section v-else-if="vista === 'departamentos'" class="detalle">
    <nav class="migas">
      <button type="button" class="migas-enlace" @click="volver">Departamentos</button>
      <span>›</span>
      <span class="migas-actual">{{ grupo.nombre }}</span>
    </nav>
    <header class="detalle-cabecera">
      <span class="detalle-iniciales">{{ iniciales(grupo.nombre) }}</span>
      <h1>{{ grupo.nombre }}</h1>
    </header>
    <div class="detalle-rejilla">
      <div>
        <section v-for="sede in grupo.sedes" :key="sede.delegacion" class="detalle-sede">
          <h2>{{ delegacionVisible(sede.delegacion) }}</h2>
          <div class="detalle-listas">
            <section class="panel">
              <header class="panel-cabecera">
                <h2>Mandos</h2>
                <span class="panel-cuenta">{{ sede.mandos.length }}</span>
              </header>
              <p v-if="!sede.mandos.length" class="panel-vacio">Este departamento aún no tiene mandos.</p>
              <ul v-else class="panel-filas">
                <li v-for="mando in sede.mandos" :key="mando.login">
                  <span class="avatar">{{ iniciales(mando.nombre) }}</span>
                  <span class="persona-datos">
                    <strong>{{ mando.nombre }}</strong>
                    <span>{{ mando.login }}</span>
                    <span v-if="mando.numero_sap">{{ mando.numero_sap }}</span>
                  </span>
                  <button type="button" @click="abrirSap(mando)">Editar número SAP</button>
                </li>
              </ul>
            </section>
            <section class="panel">
              <header class="panel-cabecera">
                <h2>Trabajadores</h2>
                <span class="panel-cuenta">{{ sede.trabajadores.length }}</span>
              </header>
              <p v-if="!sede.trabajadores.length" class="panel-vacio">
                Aún no hay trabajadores. Los crea el mando del departamento.
              </p>
              <ul v-else class="panel-filas">
                <li v-for="trabajador in sede.trabajadores" :key="trabajador.login">
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
        </section>
      </div>
      <form class="panel alta-mando" @submit.prevent="guardar">
        <header class="panel-cabecera">
          <h2>Alta de mando</h2>
        </header>
        <div class="alta-cuerpo">
          <p class="alta-aviso">Se creará en {{ grupo.nombre }}</p>
          <label>
            Sede
            <select v-model="sedeAlta">
              <option disabled value="">Elige una sede</option>
              <option v-for="codigo in delegaciones" :key="codigo" :value="codigo">
                {{ delegacionVisible(codigo) }}
              </option>
            </select>
          </label>
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
          <label>
            Número de personal (SAP)
            <input v-model="numeroSap" name="numero-sap" autocomplete="off" />
          </label>
          <p class="campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
          <p v-if="errorMando" class="error" role="alert">{{ errorMando }}</p>
          <button class="primario" type="submit">Guardar mando</button>
        </div>
      </form>
    </div>
  </section>
  <section v-else-if="vista === 'fichajes'" class="fichajes">
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
  <Analisis v-else-if="vista === 'analisis'" :token="token" />
  <dialog ref="dialogoSap" class="alta-dialogo" @close="alCerrarSap" @click="alFondoSap">
    <form @submit.prevent="guardarSap">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>Número de personal (SAP)</h2>
          <p v-if="mandoSap" class="alta-dialogo-persona">{{ mandoSap.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarSap">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Número de personal (SAP)
          <input v-model="numeroSapEdit" name="numero-sap-mando" autocomplete="off" />
        </label>
        <p class="ancho campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
      </div>
      <p v-if="errorSap" class="error" role="alert">{{ errorSap }}</p>
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarSap">Cancelar</button>
        <button class="primario" type="submit">Guardar</button>
      </footer>
    </form>
  </dialog>
</template>
