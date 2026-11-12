<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { listar } from "../api/departamentos.js";
import Analisis from "./Analisis.vue";
import Cobertura from "./Cobertura.vue";
import Cuadrante from "./Cuadrante.vue";
import EditarUsuario from "./EditarUsuario.vue";
import FichaEmpleado from "./FichaEmpleado.vue";
import Fichajes from "./Fichajes.vue";
import HorarioHabitual from "./HorarioHabitual.vue";
import Festivos from "./Festivos.vue";
import {
  asignarDepartamentoMando,
  cambiarActivoMando,
  cambiarHorarioMando,
  crearMando,
  crearTrabajador,
  quitarDepartamentoMando,
} from "../api/usuarios.js";
import { delegacionVisible, hoyIso, lunesQueViene } from "../fechas.js";
import { agruparPersonas, iniciales, numeroFormulario as numeroTrabajador } from "../personas.js";

const COLORES_DEPARTAMENTO = {
  trafico: { fondo: "#e5f0fb", texto: "#2e78c9" },
  sac: { fondo: "#fbe9e2", texto: "#c9542e" },
  muelle: { fondo: "#d8f3f0", texto: "#0f766e" },
  choferes: { fondo: "#fdf1c9", texto: "#8a6a08" },
  mandos: { fondo: "#eae7fb", texto: "#5b4fc9" },
  mandos_funcionales: { fondo: "#eae7fb", texto: "#5b4fc9" },
  mantenimiento: { fondo: "#dcf0dc", texto: "#2a6b2a" },
  defecto: { fondo: "#f0f2f5", texto: "#5c6570" },
};

const props = defineProps({
  token: { type: String, required: true },
  delegaciones: { type: Array, required: true },
  nombreSesion: { type: String, required: true },
});

const vista = ref("departamentos");
const departamentos = ref([]);
const error = ref("");
const elegido = ref(null);
const sedeVisible = ref("");
const seccionSede = ref("cuadrante");
const altaAbierta = ref(false);
const modoAlta = ref("crear");
const loginAsignar = ref("");
const errorAccion = ref("");
const altaTrabajadorAbierta = ref(false);
const nombreTrabajador = ref("");
const loginTrabajador = ref("");
const claveTrabajador = ref("");
const grupoTrabajador = ref("STEF");
const costeTrabajador = ref("");
const vacacionesTrabajador = ref("");
const horasContratoTrabajador = ref("");
const pausaTrabajador = ref(0);
const numeroSapTrabajador = ref("");
const seccionTrabajador = ref("");
const errorTrabajador = ref("");
const horarioTrabajador = ref(null);
const nombre = ref("");
const login = ref("");
const clave = ref("");
const numeroSap = ref("");
const errorMando = ref("");
const personaEditar = ref(null);
const fichaLogin = ref("");
const dialogoHorario = ref(null);
const horarioMando = ref(null);
const horarioMandoForm = ref(null);
const desdeHorario = ref("");
const errorHorario = ref("");
const seccionesEditar = ref([]);

const tarjetas = computed(() => {
  const porCodigo = new Map();
  for (const item of departamentos.value) {
    const grupo = porCodigo.get(item.codigo);
    if (!grupo) {
      porCodigo.set(item.codigo, {
        codigo: item.codigo,
        nombre: item.nombre,
        orden: item.orden,
        sedes: [item],
      });
      continue;
    }
    grupo.sedes.push(item);
    if (item.orden < grupo.orden) {
      grupo.orden = item.orden;
      grupo.nombre = item.nombre;
    }
  }
  return [...porCodigo.values()]
    .map((grupo) => ({
      codigo: grupo.codigo,
      nombre: grupo.nombre,
      orden: grupo.orden,
      personas: personasDistintas(grupo.sedes),
    }))
    .sort((a, b) => a.orden - b.orden);
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

function colorDepartamento(codigo) {
  return COLORES_DEPARTAMENTO[codigo] || COLORES_DEPARTAMENTO.defecto;
}

function cifra(total, uno, varios) {
  return total === 1 ? `1 ${uno}` : `${total} ${varios}`;
}

function mandosActivos(sede) {
  return (sede?.mandos ?? []).filter((mando) => mando.activo === true);
}

function personasSede(sede) {
  return mandosActivos(sede).length + (sede?.trabajadores?.length ?? 0);
}

function cuentaTrabajadores(total) {
  return total === 1 ? "1 trabajador" : `${total} trabajadores`;
}

function personasDistintas(sedes) {
  const logins = new Set();
  for (const sede of sedes) {
    for (const mando of mandosActivos(sede)) {
      logins.add(mando.login);
    }
    for (const trabajador of sede.trabajadores ?? []) {
      logins.add(trabajador.login);
    }
  }
  return logins.size;
}

const candidatos = computed(() => {
  if (!grupo.value) {
    return [];
  }
  const actual = grupo.value.sedes.find((sede) => sede.delegacion === sedeVisible.value);
  const ya = new Set((actual?.mandos ?? []).map((mando) => mando.login));
  const vistos = new Map();
  for (const sede of grupo.value.sedes) {
    if (sede.delegacion === sedeVisible.value) {
      continue;
    }
    for (const mando of mandosActivos(sede)) {
      if (!ya.has(mando.login) && !vistos.has(mando.login)) {
        vistos.set(mando.login, mando);
      }
    }
  }
  return [...vistos.values()];
});

function abrirAlta() {
  modoAlta.value = "crear";
  loginAsignar.value = "";
  errorMando.value = "";
  altaAbierta.value = true;
}

function elegirModoAlta(modo) {
  modoAlta.value = modo;
  errorMando.value = "";
}

function abrir(tarjeta) {
  errorMando.value = "";
  errorAccion.value = "";
  altaTrabajadorAbierta.value = false;
  errorTrabajador.value = "";
  modoAlta.value = "crear";
  loginAsignar.value = "";
  const sede = props.delegaciones[0] ?? "";
  const encontrada = departamentos.value.find(
    (item) => item.codigo === tarjeta.codigo && item.delegacion === sede,
  );
  sedeVisible.value = sede;
  seccionSede.value = "cuadrante";
  altaAbierta.value = mandosActivos(encontrada).length === 0;
  elegido.value = tarjeta.codigo;
}

function verSede(codigo) {
  if (codigo === sedeVisible.value) {
    return;
  }
  sedeVisible.value = codigo;
  altaAbierta.value = false;
  modoAlta.value = "crear";
  loginAsignar.value = "";
  errorMando.value = "";
  errorAccion.value = "";
  altaTrabajadorAbierta.value = false;
  errorTrabajador.value = "";
}

function abrirEdicion(persona, rol, sede) {
  personaEditar.value = { ...persona, rol };
  seccionesEditar.value = sede.secciones ?? [];
}

function abrirFicha(trabajador) {
  fichaLogin.value = trabajador.login;
  vista.value = "ficha";
}

function cerrarFicha() {
  fichaLogin.value = "";
  vista.value = "departamentos";
}

function cerrarEdicion() {
  personaEditar.value = null;
}

async function alGuardarUsuario() {
  await cargar();
}

function abrirHorario(mando) {
  horarioMando.value = mando;
  desdeHorario.value = lunesQueViene();
  errorHorario.value = "";
  dialogoHorario.value?.showModal();
  nextTick(() => dialogoHorario.value?.querySelector("[name='desde-horario']")?.focus());
}

function cerrarHorario() {
  dialogoHorario.value?.close();
}

function alCerrarHorario() {
  horarioMando.value = null;
  errorHorario.value = "";
}

function alFondoHorario(evento) {
  if (evento.target === dialogoHorario.value) {
    cerrarHorario();
  }
}

async function guardarHorario() {
  errorHorario.value = "";
  const mando = horarioMando.value;
  if (!mando) {
    return;
  }
  if (!desdeHorario.value) {
    errorHorario.value = "Indica desde qué fecha aplica.";
    return;
  }
  if (desdeHorario.value < hoyIso()) {
    errorHorario.value = "La fecha no puede ser anterior a hoy.";
    return;
  }
  const horario = horarioMandoForm.value?.horarioDias();
  if (!horario?.horario_dias) {
    errorHorario.value = horario?.error || "Marca al menos un día.";
    return;
  }
  const sede = sedeVisible.value;
  try {
    await cambiarHorarioMando(props.token, mando.login, {
      desde: desdeHorario.value,
      horario_dias: horario.horario_dias,
    });
    cerrarHorario();
    await cargar();
    sedeVisible.value = sede;
  } catch (causa) {
    errorHorario.value = causa instanceof Error ? causa.message : "No se pudo cambiar el horario";
  }
}

function volver() {
  errorMando.value = "";
  errorAccion.value = "";
  altaTrabajadorAbierta.value = false;
  errorTrabajador.value = "";
  sedeVisible.value = props.delegaciones[0] ?? "";
  elegido.value = null;
}

function abrirAltaTrabajador() {
  errorTrabajador.value = "";
  altaTrabajadorAbierta.value = true;
}

function vaciarAltaTrabajador() {
  nombreTrabajador.value = "";
  loginTrabajador.value = "";
  claveTrabajador.value = "";
  grupoTrabajador.value = "STEF";
  costeTrabajador.value = "";
  vacacionesTrabajador.value = "";
  horasContratoTrabajador.value = "";
  pausaTrabajador.value = 0;
  numeroSapTrabajador.value = "";
  seccionTrabajador.value = "";
  errorTrabajador.value = "";
  altaTrabajadorAbierta.value = false;
}

function horarioSeleccionado() {
  const origen = horarioTrabajador.value;
  const horario = Array.isArray(origen) ? origen.find(Boolean) : origen;
  return horario?.horarioDias?.() ?? null;
}

async function guardarTrabajador() {
  const sede = grupo.value?.sedes.find((item) => item.delegacion === sedeVisible.value);
  if (!sede?.id) {
    errorTrabajador.value = "No se ha encontrado el departamento";
    return;
  }
  errorTrabajador.value = "";
  const datos = {
    nombre: nombreTrabajador.value,
    login: loginTrabajador.value,
    clave: claveTrabajador.value,
    grupo: grupoTrabajador.value,
    vacaciones: numeroTrabajador(vacacionesTrabajador.value),
    horas_contrato: numeroTrabajador(horasContratoTrabajador.value),
    pausa_minutos: pausaTrabajador.value,
    numero_sap: numeroSapTrabajador.value,
    departamento_id: sede.id,
  };
  if (
    grupoTrabajador.value === "ETT"
    && costeTrabajador.value !== ""
    && costeTrabajador.value !== null
  ) {
    datos.coste = numeroTrabajador(costeTrabajador.value);
  }
  if (sede.usa_horario_habitual !== false) {
    const horario = horarioSeleccionado();
    if (!horario?.horario_dias) {
      errorTrabajador.value = horario?.error || "Marca al menos un día.";
      return;
    }
    datos.horario_dias = horario.horario_dias;
  }
  if (sede.secciones?.length) {
    datos.seccion_id = seccionTrabajador.value || null;
  }
  try {
    await crearTrabajador(props.token, datos);
    vaciarAltaTrabajador();
    await cargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

async function cambiarActivo(mando) {
  errorAccion.value = "";
  try {
    await cambiarActivoMando(props.token, mando.login, mando.activo !== true);
    await cargar();
  } catch (causa) {
    errorAccion.value = causa instanceof Error ? causa.message : "No se pudo cambiar el estado";
  }
}

async function quitarDeSede(mando, sede) {
  if (!window.confirm(`¿Quitar a ${mando.nombre} de esta sede?`)) {
    return;
  }
  errorAccion.value = "";
  try {
    await quitarDepartamentoMando(props.token, mando.login, sede.id);
    await cargar();
  } catch (causa) {
    errorAccion.value = causa instanceof Error ? causa.message : "No se pudo quitar de esta sede";
  }
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
  if (!grupo.value || !sedeVisible.value) {
    return;
  }
  errorMando.value = "";
  try {
    await crearMando(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      delegacion: sedeVisible.value,
      departamento: grupo.value.codigo,
      numero_sap: numeroSap.value,
    });
    nombre.value = "";
    login.value = "";
    clave.value = "";
    numeroSap.value = "";
    altaAbierta.value = false;
    await cargar();
  } catch (causa) {
    errorMando.value = causa instanceof Error ? causa.message : "No se pudo crear el mando";
  }
}

async function asignar() {
  if (!grupo.value || !sedeVisible.value || !loginAsignar.value) {
    return;
  }
  errorMando.value = "";
  try {
    await asignarDepartamentoMando(
      props.token,
      loginAsignar.value,
      sedeVisible.value,
      grupo.value.codigo,
    );
    loginAsignar.value = "";
    altaAbierta.value = false;
    await cargar();
  } catch (causa) {
    errorMando.value = causa instanceof Error ? causa.message : "No se pudo asignar el mando";
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
    <button type="button" :class="{ activo: vista === 'festivos' }" @click="vista = 'festivos'">
      Festivos
    </button>
  </nav>
  <p v-if="vista === 'departamentos' && error" class="error" role="alert">{{ error }}</p>
  <div v-if="vista === 'departamentos' && !grupo" class="bloques">
    <section class="bienvenida">
      <p class="bienvenida-titulo">Bienvenido, {{ nombreSesion }}</p>
      <p class="bienvenida-detalle">Gestiona los equipos de 60I San Sebastián y 05I Irún.</p>
    </section>
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
        :class="{ 'tarjeta-vacia': tarjeta.personas === 0 }"
        @click="abrir(tarjeta)"
      >
        <span
          class="tarjeta-iniciales"
          :style="{
            background: colorDepartamento(tarjeta.codigo).fondo,
            color: colorDepartamento(tarjeta.codigo).texto,
          }"
        >{{ iniciales(tarjeta.nombre) }}</span>
        <span class="tarjeta-datos">
          <span class="tarjeta-nombre">{{ tarjeta.nombre }}</span>
          <span class="tarjeta-recuento">{{
            tarjeta.personas === 0 ? "Sin equipo todavía" : cifra(tarjeta.personas, "persona", "personas")
          }}</span>
        </span>
        <span class="tarjeta-flecha" aria-hidden="true">›</span>
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
        <nav v-if="grupo.sedes.length > 1" class="vistas">
          <button
            v-for="sede in grupo.sedes"
            :key="sede.delegacion"
            type="button"
            :class="{ activo: sedeVisible === sede.delegacion }"
            @click="verSede(sede.delegacion)"
          >
            {{ delegacionVisible(sede.delegacion) }} · {{ personasSede(sede) }}
          </button>
        </nav>
        <template v-for="sede in grupo.sedes" :key="sede.delegacion">
        <div v-if="sede.delegacion === sedeVisible" class="detalle-listas">
          <nav class="vistas">
            <button type="button" :class="{ activo: seccionSede === 'cuadrante' }" @click="seccionSede = 'cuadrante'">
              Cuadrante
            </button>
            <button type="button" :class="{ activo: seccionSede === 'cobertura' }" @click="seccionSede = 'cobertura'">
              Cobertura
            </button>
            <button type="button" :class="{ activo: seccionSede === 'equipo' }" @click="seccionSede = 'equipo'">
              Equipo
            </button>
          </nav>
          <Cuadrante
            v-if="seccionSede === 'cuadrante' && sede.id"
            :key="sede.id"
            :token="token"
            :departamento-id="sede.id"
          />
          <p v-else-if="seccionSede === 'cuadrante'" class="panel-vacio">
            Este departamento no está en esta sede.
          </p>
          <Cobertura
            v-if="seccionSede === 'cobertura' && sede.id"
            :key="sede.id"
            :token="token"
            :departamento-id="sede.id"
          />
          <p v-else-if="seccionSede === 'cobertura'" class="panel-vacio">
            Este departamento no está en esta sede.
          </p>
          <section v-if="seccionSede === 'equipo'" class="panel">
            <header class="panel-cabecera">
              <h2>Mandos</h2>
              <span class="panel-cuenta">{{ sede.mandos.length }}</span>
              <button
                v-if="!mandosActivos(sede).length"
                type="button"
                class="anadir-mando"
                @click="abrirAlta"
              >+ Añadir mando</button>
            </header>
            <p v-if="errorAccion" class="error mando-error" role="alert">{{ errorAccion }}</p>
            <p v-if="!sede.mandos.length" class="panel-vacio">Este departamento aún no tiene mandos.</p>
            <ul v-else class="panel-filas">
              <li v-for="mando in sede.mandos" :key="mando.login">
                <span class="avatar">{{ iniciales(mando.nombre) }}</span>
                <span class="persona-datos">
                  <strong>{{ mando.nombre }}</strong>
                  <span>{{ mando.login }}</span>
                  <span v-if="mando.numero_sap">{{ mando.numero_sap }}</span>
                </span>
                <span v-if="mando.activo === false || mando.propio === false" class="mando-marcas">
                  <span v-if="mando.activo === false" class="mando-pastilla mando-pastilla-inactivo">Inactivo</span>
                  <span v-if="mando.propio === false" class="mando-pastilla mando-pastilla-otra">Otra sede</span>
                </span>
                <span class="mando-acciones">
                  <button type="button" @click="cambiarActivo(mando)">
                    {{ mando.activo === true ? "Desactivar" : "Reactivar" }}
                  </button>
                  <button v-if="mando.propio === false" type="button" @click="quitarDeSede(mando, sede)">
                    Quitar de esta sede
                  </button>
                  <button type="button" @click="abrirHorario(mando)">Horario</button>
                  <button type="button" @click="abrirEdicion(mando, 'mando', sede)">Editar</button>
                </span>
              </li>
            </ul>
          </section>
          <section v-if="seccionSede === 'equipo'" class="panel">
            <header class="panel-cabecera">
              <h2>Trabajadores</h2>
              <span class="panel-cuenta">{{ sede.trabajadores.length }}</span>
              <button type="button" class="anadir-mando" @click="abrirAltaTrabajador">+ Añadir trabajador</button>
            </header>
            <form v-if="altaTrabajadorAbierta" class="alta-cuerpo" @submit.prevent="guardarTrabajador">
              <label>
                Nombre
                <input v-model="nombreTrabajador" name="nombre-trabajador" autocomplete="off" />
              </label>
              <label>
                Login
                <input v-model="loginTrabajador" name="login-trabajador" autocomplete="off" />
              </label>
              <label>
                Clave
                <input v-model="claveTrabajador" name="clave-trabajador" type="password" autocomplete="new-password" />
              </label>
              <label>
                Grupo
                <select v-model="grupoTrabajador" name="grupo-trabajador">
                  <option value="STEF">STEF</option>
                  <option value="ETT">ETT</option>
                </select>
              </label>
              <label v-if="grupoTrabajador === 'ETT'">
                Coste (€/hora)
                <input v-model="costeTrabajador" name="coste-trabajador" type="number" min="0" step="0.0001" />
              </label>
              <label>
                Vacaciones
                <input v-model="vacacionesTrabajador" name="vacaciones-trabajador" type="number" min="0" step="0.5" />
              </label>
              <label>
                Horas de contrato
                <input v-model="horasContratoTrabajador" name="horas-contrato-trabajador" type="number" min="0" step="0.5" />
              </label>
              <label>
                Pausa
                <select v-model="pausaTrabajador" name="pausa-trabajador">
                  <option :value="0">Sin pausa</option>
                  <option :value="30">30 minutos</option>
                  <option :value="60">1 hora</option>
                </select>
              </label>
              <p class="campo-pista">Descanso diario no pagado. Se resta de las horas planificadas.</p>
              <label>
                Número de personal (SAP)
                <input v-model="numeroSapTrabajador" name="numero-sap-trabajador" autocomplete="off" />
              </label>
              <p class="campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
              <label v-if="sede.secciones?.length">
                Sección
                <select v-model="seccionTrabajador" name="seccion-trabajador">
                  <option value="">Sin sección</option>
                  <option v-for="seccion in sede.secciones" :key="seccion.id" :value="seccion.id">
                    {{ seccion.nombre }}
                  </option>
                </select>
              </label>
              <HorarioHabitual v-if="sede.usa_horario_habitual !== false" ref="horarioTrabajador" />
              <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
              <button class="primario" type="submit">Guardar trabajador</button>
            </form>
            <p v-if="!sede.trabajadores.length" class="panel-vacio">
              Aún no hay trabajadores. Los crea el mando del departamento.
            </p>
            <div v-else class="equipo-grupos">
              <section v-for="grupoEquipo in agruparPersonas(sede?.trabajadores)" :key="grupoEquipo.id" class="panel">
                <header class="panel-cabecera">
                  <h2>{{ grupoEquipo.titulo }}</h2>
                  <span class="panel-cuenta">{{ cuentaTrabajadores(grupoEquipo.personas.length) }}</span>
                </header>
                <ul class="panel-filas">
                  <li v-for="trabajador in grupoEquipo.personas" :key="trabajador.login">
                    <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
                    <span class="persona-datos">
                      <strong>{{ trabajador.nombre }}</strong>
                      <span>{{ trabajador.login }}</span>
                    </span>
                    <span class="mando-acciones">
                      <button type="button" @click="abrirFicha(trabajador)">Ficha</button>
                      <button type="button" @click="abrirEdicion(trabajador, 'trabajador', sede)">Editar</button>
                    </span>
                  </li>
                </ul>
              </section>
            </div>
          </section>
        </div>
        </template>
      </div>
      <form v-if="altaAbierta" class="panel alta-mando" @submit.prevent="modoAlta === 'crear' ? guardar() : asignar()">
        <header class="panel-cabecera">
          <h2>Alta de mando</h2>
        </header>
        <div class="alta-cuerpo">
          <nav class="vistas alta-modos">
            <button type="button" :class="{ activo: modoAlta === 'crear' }" @click="elegirModoAlta('crear')">
              Crear nuevo
            </button>
            <button type="button" :class="{ activo: modoAlta === 'asignar' }" @click="elegirModoAlta('asignar')">
              Asignar existente
            </button>
          </nav>
          <template v-if="modoAlta === 'crear'">
            <p class="alta-aviso">Se creará en {{ grupo.nombre }}</p>
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
          </template>
          <template v-else>
            <label>
              Mando
              <select v-model="loginAsignar" name="mando-existente">
                <option value="" disabled>Elige un mando</option>
                <option v-for="mando in candidatos" :key="mando.login" :value="mando.login">
                  {{ mando.nombre }} ({{ mando.login }})
                </option>
              </select>
            </label>
            <p v-if="!candidatos.length" class="campo-pista">No hay mandos activos en otras sedes.</p>
            <p v-if="errorMando" class="error" role="alert">{{ errorMando }}</p>
            <button class="primario" type="submit" :disabled="!loginAsignar">Asignar</button>
          </template>
        </div>
      </form>
    </div>
  </section>
  <KeepAlive>
    <Fichajes
      v-if="vista === 'fichajes'"
      :token="token"
      @ver-analisis="vista = 'analisis'"
    />
  </KeepAlive>
  <FichaEmpleado
    v-if="vista === 'ficha'"
    :token="token"
    :login="fichaLogin"
    volver
    texto-volver="← Departamento"
    @volver="cerrarFicha"
  />
  <Analisis v-else-if="vista === 'analisis'" :token="token" />
  <Festivos v-else-if="vista === 'festivos'" :token="token" />
  <dialog ref="dialogoHorario" class="alta-dialogo" @close="alCerrarHorario" @click="alFondoHorario">
    <form v-if="horarioMando" @submit.prevent="guardarHorario">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>Cambiar horario</h2>
          <p class="alta-dialogo-persona">{{ horarioMando.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarHorario">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Desde
          <input
            v-model="desdeHorario"
            name="desde-horario"
            type="date"
            required
            :min="hoyIso()"
          />
        </label>
        <HorarioHabitual ref="horarioMandoForm" />
      </div>
      <p v-if="errorHorario" class="error" role="alert">{{ errorHorario }}</p>
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarHorario">Cancelar</button>
        <button class="primario" type="submit">Guardar horario</button>
      </footer>
    </form>
  </dialog>
  <EditarUsuario
    v-if="personaEditar"
    :token="token"
    :persona="personaEditar"
    :secciones="seccionesEditar"
    @guardado="alGuardarUsuario"
    @cerrar="cerrarEdicion"
  />
</template>

<style scoped>
.rejilla-deptos {
  max-width: 1100px;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.tarjeta {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px 24px;
}

.tarjeta-iniciales {
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  margin-bottom: 0;
}

.tarjeta-datos {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.tarjeta-flecha {
  flex-shrink: 0;
  color: #c5cad3;
  font-size: 22px;
  line-height: 1;
}

@media (max-width: 900px) {
  .rejilla-deptos {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 600px) {
  .rejilla-deptos {
    grid-template-columns: 1fr;
  }
}

.tarjeta-vacia {
  background: #f3f4f6;
  border-color: #e5e7eb;
}

.tarjeta-vacia .tarjeta-nombre,
.tarjeta-vacia .tarjeta-recuento {
  color: #8b939e;
}

.detalle .anadir-mando {
  margin-left: auto;
}

.mando-error {
  margin: 0;
  padding: 0 18px 12px;
}

.mando-marcas {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.mando-pastilla {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.mando-pastilla-inactivo {
  background: #f3f4f6;
  color: #6b7280;
}

.mando-pastilla-otra {
  background: #e5f0fb;
  color: #2e78c9;
}

.mando-acciones {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
  margin-left: auto;
}

.alta-mando .alta-modos {
  margin-bottom: 0;
}

.alta-mando .alta-modos button {
  padding: 5px 10px;
  font-size: 12px;
}

.detalle-listas > .vistas {
  justify-self: start;
}

.detalle-rejilla:not(:has(> .alta-mando)) {
  grid-template-columns: minmax(0, 1fr);
}

</style>
