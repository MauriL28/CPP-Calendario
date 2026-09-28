<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { crearTrabajador } from "../api/usuarios.js";
import Cuadrante from "./Cuadrante.vue";

const props = defineProps({
  token: { type: String, required: true },
});

const vista = ref("cuadrante");
const cuadrante = ref(null);
const departamentos = ref([]);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const grupo = ref("STEF");
const horaInicio = ref("");
const horaFin = ref("");
const vacaciones = ref("");
const horasContrato = ref("");
const errorTrabajador = ref("");
const dialogo = ref(null);
const aviso = ref(false);
const busqueda = ref("");
const filtroGrupo = ref("");
let avisoTemporizador = 0;

const equipo = computed(() => departamentos.value[0] || null);
const trabajadores = computed(() => equipo.value?.trabajadores ?? []);
const filtrados = computed(() => {
  const texto = busqueda.value.trim().toLocaleLowerCase("es");
  return trabajadores.value.filter((trabajador) => {
    if (filtroGrupo.value && trabajador.grupo !== filtroGrupo.value) {
      return false;
    }
    if (!texto) {
      return true;
    }
    const nombreVisible = trabajador.nombre.toLocaleLowerCase("es");
    const loginVisible = trabajador.login.toLocaleLowerCase("es");
    return nombreVisible.includes(texto) || loginVisible.includes(texto);
  });
});

function iniciales(texto) {
  const palabras = texto.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  return palabras
    .slice(0, 2)
    .map((parte) => parte[0].toLocaleUpperCase("es"))
    .join("");
}

async function cargarDepartamentos() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

function vaciarAlta() {
  nombre.value = "";
  login.value = "";
  clave.value = "";
  grupo.value = "STEF";
  horaInicio.value = "";
  horaFin.value = "";
  vacaciones.value = "";
  horasContrato.value = "";
  errorTrabajador.value = "";
}

function abrirAlta() {
  vaciarAlta();
  dialogo.value?.showModal();
  dialogo.value?.querySelector("[name='nombre-trabajador']")?.focus();
}

function cerrarAlta() {
  dialogo.value?.close();
}

function alCerrarAlta() {
  vaciarAlta();
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    cerrarAlta();
  }
}

function mostrarAviso() {
  aviso.value = true;
  window.clearTimeout(avisoTemporizador);
  avisoTemporizador = window.setTimeout(() => {
    aviso.value = false;
  }, 3000);
}

function horario(trabajador) {
  if (!trabajador.horario_inicio || !trabajador.horario_fin) {
    return "—";
  }
  return `${trabajador.horario_inicio}–${trabajador.horario_fin}`;
}

function cantidad(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  return Number(valor).toLocaleString("es-ES");
}

function cuenta(total) {
  return total === 1 ? "1 trabajador" : `${total} trabajadores`;
}

async function guardar() {
  errorTrabajador.value = "";
  try {
    await crearTrabajador(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      grupo: grupo.value,
      hora_inicio: horaInicio.value,
      hora_fin: horaFin.value,
      vacaciones: numero(vacaciones.value),
      horas_contrato: numero(horasContrato.value),
    });
    cerrarAlta();
    mostrarAviso();
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function numero(valor) {
  if (valor === "" || valor === null) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
}

watch(vista, (nueva) => {
  if (nueva !== "equipo" && dialogo.value?.open) {
    cerrarAlta();
  }
});

onMounted(cargarDepartamentos);
</script>

<template>
  <nav class="vistas">
    <button type="button" :class="{ activo: vista === 'cuadrante' }" @click="vista = 'cuadrante'">
      Cuadrante
    </button>
    <button type="button" :class="{ activo: vista === 'equipo' }" @click="vista = 'equipo'">
      Equipo
    </button>
  </nav>
  <Cuadrante v-show="vista === 'cuadrante'" ref="cuadrante" :token="token" editable />
  <section v-if="vista === 'equipo'" class="equipo">
    <header class="equipo-intro">
      <h1>Equipo</h1>
      <p>Personas de tu departamento. Son las filas de tu cuadrante.</p>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-else-if="equipo && !trabajadores.length" class="panel equipo-vacio">
      <strong>Aún no hay trabajadores en tu departamento</strong>
      <p>Añade el primero para empezar a montar el cuadrante.</p>
      <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
    </div>
    <template v-else-if="equipo">
      <div class="equipo-barra">
        <input v-model="busqueda" class="equipo-buscar" type="search" placeholder="Buscar trabajador..." />
        <select v-model="filtroGrupo" class="equipo-grupo">
          <option value="">Todos los grupos</option>
          <option value="STEF">STEF</option>
          <option value="ETT">ETT</option>
        </select>
        <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
      </div>
      <section class="panel">
        <header class="panel-cabecera">
          <h2>{{ cuenta(filtrados.length) }}</h2>
        </header>
        <p v-if="!filtrados.length" class="panel-vacio">Ningún trabajador coincide con la búsqueda.</p>
        <table v-else class="equipo">
          <thead>
            <tr>
              <th>Trabajador</th>
              <th>Grupo</th>
              <th>Horario</th>
              <th class="col-extra">Horas/semana</th>
              <th class="col-extra">Vacaciones/año</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trabajador in filtrados" :key="trabajador.login">
              <td>
                <span class="equipo-persona">
                  <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
                  <span class="persona-datos">
                    <strong>{{ trabajador.nombre }}</strong>
                    <span>{{ trabajador.login }}</span>
                  </span>
                </span>
              </td>
              <td>
                <span class="grupo-pastilla" :class="trabajador.grupo === 'ETT' ? 'grupo-ett' : 'grupo-stef'">
                  {{ trabajador.grupo }}
                </span>
              </td>
              <td>{{ horario(trabajador) }}</td>
              <td class="col-extra">{{ cantidad(trabajador.horas_contrato) }}</td>
              <td class="col-extra">{{ cantidad(trabajador.vacaciones) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
  <dialog ref="dialogo" class="alta-dialogo" @close="alCerrarAlta" @click="alFondo">
      <form @submit.prevent="guardar">
        <header class="alta-dialogo-cabecera">
          <h2>Alta de trabajador</h2>
          <button type="button" class="dialogo-cerrar" @click="cerrarAlta">✕</button>
        </header>
        <div class="alta-dialogo-cuerpo">
          <h3>Acceso</h3>
          <label>
            Nombre
            <input v-model="nombre" name="nombre-trabajador" />
          </label>
          <label>
            Login
            <input v-model="login" name="login-trabajador" autocomplete="off" />
          </label>
          <label class="ancho">
            Clave
            <input v-model="clave" name="clave-trabajador" type="password" autocomplete="new-password" />
          </label>
          <h3>Contrato</h3>
          <div class="alta-tres">
            <label>
              Grupo
              <select v-model="grupo">
                <option value="STEF">STEF</option>
                <option value="ETT">ETT</option>
              </select>
            </label>
            <label>
              Horas/semana
              <input v-model="horasContrato" name="horas-contrato" type="number" min="0" step="0.5" />
            </label>
            <label>
              Vacaciones (días/año)
              <input v-model="vacaciones" name="vacaciones" type="number" min="0" step="0.5" />
            </label>
          </div>
          <h3>Horario habitual</h3>
          <label>
            Hora de inicio
            <input v-model="horaInicio" name="hora-inicio" type="time" />
          </label>
          <label>
            Hora de fin
            <input v-model="horaFin" name="hora-fin" type="time" />
          </label>
        </div>
        <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
        <footer class="alta-dialogo-pie">
          <button type="button" @click="cerrarAlta">Cancelar</button>
          <button class="primario" type="submit">Guardar trabajador</button>
        </footer>
      </form>
  </dialog>
  <p v-if="aviso" class="aviso-ok" role="status">Trabajador creado</p>
</template>
