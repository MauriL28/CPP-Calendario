<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { importarFichajes, listarImportaciones } from "../api/fichajes.js";
import Analisis from "./Analisis.vue";
import Cobertura from "./Cobertura.vue";
import Cuadrante from "./Cuadrante.vue";
import EditarUsuario from "./EditarUsuario.vue";
import FichaEmpleado from "./FichaEmpleado.vue";
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
import { delegacionVisible } from "../fechas.js";

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
const archivo = ref(null);
const entradaArchivo = ref(null);
const arrastrando = ref(false);
const enviando = ref(false);
const errorFichajes = ref("");
const resumen = ref(null);
const importaciones = ref(null);
const errorImportaciones = ref("");
const historialAbierto = ref(false);

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

function mandosActivos(sede) {
  return (sede?.mandos ?? []).filter((mando) => mando.activo === true);
}

function personasSede(sede) {
  return mandosActivos(sede).length + (sede?.trabajadores?.length ?? 0);
}

function gruposTrabajadores(sede) {
  const lista = sede?.trabajadores ?? [];
  return [
    {
      id: "STEF",
      titulo: "Personal STEF",
      personas: lista.filter((trabajador) => trabajador.grupo === "STEF"),
    },
    {
      id: "ETT",
      titulo: "ETT",
      personas: lista.filter((trabajador) => trabajador.grupo === "ETT"),
    },
  ].filter((grupo) => grupo.personas.length);
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

function fechaLocal(dia) {
  const mes = String(dia.getMonth() + 1).padStart(2, "0");
  const numero = String(dia.getDate()).padStart(2, "0");
  return `${dia.getFullYear()}-${mes}-${numero}`;
}

function hoyIso() {
  return fechaLocal(new Date());
}

function lunesQueViene() {
  const hoy = new Date();
  hoy.setHours(12, 0, 0, 0);
  const salto = hoy.getDay() === 1 ? 0 : (8 - hoy.getDay()) % 7;
  hoy.setDate(hoy.getDate() + salto);
  return fechaLocal(hoy);
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

function numeroTrabajador(valor) {
  if (valor === "" || valor === null) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
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

const tamanoArchivo = computed(() => {
  if (!archivo.value) {
    return "";
  }
  const bytes = archivo.value.size;
  const mega = 1024 * 1024;
  const cantidad = bytes >= mega ? bytes / mega : bytes / 1024;
  const unidad = bytes >= mega ? "MB" : "KB";
  return `${cantidad.toLocaleString("es-ES", { maximumFractionDigits: 1 })} ${unidad}`;
});

function fechaCorta(iso) {
  if (!iso) {
    return "—";
  }
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

const textoPeriodo = computed(() => {
  if (!resumen.value) {
    return "";
  }
  const desde = resumen.value.fecha_desde;
  const hasta = resumen.value.fecha_hasta;
  if (!desde && !hasta) {
    return "Sin fechas en el archivo";
  }
  return `Periodo cargado: ${fechaCorta(desde)} → ${fechaCorta(hasta)}`;
});

function verAnalisis() {
  vista.value = "analisis";
}

function esXlsx(fichero) {
  return fichero.name.toLowerCase().endsWith(".xlsx");
}

function tomarArchivo(fichero) {
  if (!fichero) {
    return;
  }
  if (!esXlsx(fichero)) {
    archivo.value = null;
    errorFichajes.value = "El archivo tiene que ser .xlsx";
    return;
  }
  archivo.value = fichero;
  errorFichajes.value = "";
  resumen.value = null;
}

function alArchivo(evento) {
  tomarArchivo(evento.target.files?.[0] ?? null);
  evento.target.value = "";
}

function abrirArchivo() {
  entradaArchivo.value?.click();
}

function alSoltar(evento) {
  arrastrando.value = false;
  tomarArchivo(evento.dataTransfer?.files?.[0] ?? null);
}

function alSalirZona(evento) {
  if (evento.currentTarget.contains(evento.relatedTarget)) {
    return;
  }
  arrastrando.value = false;
}

function quitarArchivo() {
  archivo.value = null;
  errorFichajes.value = "";
  if (entradaArchivo.value) {
    entradaArchivo.value.value = "";
  }
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
    await cargarImportaciones();
  } catch (causa) {
    errorFichajes.value = causa instanceof Error ? causa.message : "No se pudo importar el archivo";
  } finally {
    enviando.value = false;
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

function fechaHora(iso) {
  const fecha = new Date(iso);
  const dos = (numero) => String(numero).padStart(2, "0");
  return `${dos(fecha.getDate())}/${dos(fecha.getMonth() + 1)}/${fecha.getFullYear()} ${dos(fecha.getHours())}:${dos(fecha.getMinutes())}`;
}

function textoPeriodoImportacion(fila) {
  if (!fila.fecha_desde || !fila.fecha_hasta) {
    return "—";
  }
  const [, mesDesde, diaDesde] = fila.fecha_desde.split("-");
  const [anioHasta, mesHasta, diaHasta] = fila.fecha_hasta.split("-");
  return `${diaDesde}/${mesDesde} → ${diaHasta}/${mesHasta}/${anioHasta}`;
}

async function cargarImportaciones() {
  errorImportaciones.value = "";
  try {
    importaciones.value = await listarImportaciones(props.token);
  } catch (causa) {
    importaciones.value = [];
    errorImportaciones.value = causa instanceof Error ? causa.message : "No se pudieron cargar las importaciones";
  }
}

watch(vista, (valor) => {
  if (valor === "fichajes") {
    cargarImportaciones();
  }
});

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
              <section v-for="grupoEquipo in gruposTrabajadores(sede)" :key="grupoEquipo.id" class="panel">
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
  <section v-else-if="vista === 'fichajes'" class="fichajes">
    <header class="lista-intro">
      <h1>Fichajes</h1>
      <p>Importa el extracto de SAP. El archivo tiene que ser .xlsx, con la hoja Data.</p>
    </header>
    <div class="fichajes-columnas">
    <form class="panel fichajes-form" @submit.prevent="importar">
      <header class="panel-cabecera">
        <h2>Importar</h2>
      </header>
      <div class="alta-cuerpo">
        <div class="fichajes-archivo">
          <input
            ref="entradaArchivo"
            class="fichajes-entrada"
            type="file"
            accept=".xlsx"
            @change="alArchivo"
          />
          <div
            class="fichajes-zona"
            role="button"
            tabindex="0"
            :class="{ 'fichajes-zona-activa': arrastrando }"
            @click="abrirArchivo"
            @keydown.enter.prevent="abrirArchivo"
            @keydown.space.prevent="abrirArchivo"
            @dragenter.prevent="arrastrando = true"
            @dragover.prevent="arrastrando = true"
            @dragleave.prevent="alSalirZona"
            @drop.prevent="alSoltar"
          >
            <template v-if="archivo">
              <span class="fichajes-nombre">{{ archivo.name }}</span>
              <span class="fichajes-tamano">{{ tamanoArchivo }}</span>
              <a href="#" class="fichajes-quitar" @click.stop.prevent="quitarArchivo">Quitar</a>
            </template>
            <template v-else>
              Arrastra aquí el extracto de SAP (.xlsx) o haz clic para elegirlo
            </template>
          </div>
        </div>
        <p v-if="errorFichajes" class="error" role="alert">{{ errorFichajes }}</p>
        <button class="primario" type="submit" :disabled="enviando || !archivo">Importar</button>
      </div>
    </form>
    <section v-if="resumen" class="panel fichajes-resumen">
      <p class="fichajes-periodo">{{ textoPeriodo }}</p>
      <dl class="fichajes-cifras">
        <div class="fichajes-cifra">
          <dt>Filas leídas</dt>
          <dd>{{ resumen.filas_leidas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Emparejadas</dt>
          <dd>{{ resumen.emparejadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Sin emparejar</dt>
          <dd>{{ resumen.sin_emparejar }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Filas nuevas</dt>
          <dd>{{ resumen.filas_nuevas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Filas sustituidas</dt>
          <dd>{{ resumen.filas_actualizadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Jornadas</dt>
          <dd>{{ resumen.jornadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Días con incidencia</dt>
          <dd>{{ resumen.dias_con_incidencia }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Personas emparejadas</dt>
          <dd>{{ resumen.personas_emparejadas }} de {{ resumen.personas_excel }}</dd>
        </div>
      </dl>
      <a
        v-if="resumen.dias_con_incidencia > 0"
        href="#"
        class="fichajes-ver-analisis"
        @click.prevent="verAnalisis"
      >Ver análisis</a>
    </section>
    </div>
    <section class="panel fichajes-historial">
      <button
        type="button"
        class="panel-cabecera fichajes-historial-cabecera"
        :aria-expanded="historialAbierto"
        @click="historialAbierto = !historialAbierto"
      >
        <h2>Importaciones anteriores ({{ importaciones ? importaciones.length : 0 }})</h2>
        <span class="fichajes-historial-flecha" :class="{ abierta: historialAbierto }" aria-hidden="true">›</span>
      </button>
      <template v-if="historialAbierto">
      <p v-if="errorImportaciones" class="error" role="alert">{{ errorImportaciones }}</p>
      <p v-else-if="importaciones && !importaciones.length" class="panel-vacio">Todavía no se ha importado ningún extracto</p>
      <div v-else-if="importaciones" class="fichajes-historial-scroll">
        <table class="equipo">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Archivo</th>
              <th>Importado por</th>
              <th>Periodo</th>
              <th>Filas leídas</th>
              <th>Sin emparejar</th>
              <th>Días con incidencia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fila in importaciones" :key="`${fila.momento}-${fila.nombre_archivo}`">
              <td>{{ fechaHora(fila.momento) }}</td>
              <td>{{ fila.nombre_archivo }}</td>
              <td>{{ fila.nombre }}</td>
              <td>{{ textoPeriodoImportacion(fila) }}</td>
              <td>{{ fila.filas_leidas }}</td>
              <td>{{ fila.filas_sin_emparejar }}</td>
              <td>{{ fila.dias_incidencia }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      </template>
    </section>
  </section>
  <FichaEmpleado
    v-else-if="vista === 'ficha'"
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

.fichajes-archivo {
  position: relative;
}

.fichajes-form .fichajes-zona {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  margin-bottom: 16px;
  padding: 22px 18px;
  border: 1.5px dashed var(--border-strong);
  border-radius: 12px;
  background: #fff;
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.4;
  text-align: left;
  cursor: pointer;
}

.fichajes-form .fichajes-zona:hover,
.fichajes-form .fichajes-zona.fichajes-zona-activa {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, #fff);
}

.fichajes-form .alta-cuerpo input.fichajes-entrada {
  position: absolute;
  display: block;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
  box-shadow: none;
}

.fichajes-nombre {
  color: var(--text);
  font-weight: 600;
}

.fichajes-tamano {
  font-size: 13px;
  color: var(--text-2);
}

.fichajes-form a.fichajes-quitar {
  margin-top: 2px;
  color: var(--accent);
  font-size: 13px;
  line-height: 1.2;
}

.fichajes-form a.fichajes-quitar:hover {
  color: var(--accent-dark);
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

.fichajes-columnas {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.fichajes-form {
  flex: 0 0 460px;
  width: 460px;
  max-width: 100%;
}

.fichajes-resumen {
  flex: 1;
  min-width: 0;
  max-width: none;
  margin-top: 0;
  padding: 16px 18px 18px;
}

@media (max-width: 900px) {
  .fichajes-columnas {
    flex-direction: column;
  }

  .fichajes-form {
    flex-basis: auto;
    width: 100%;
  }

  .fichajes-resumen {
    width: 100%;
    margin-top: 16px;
  }
}

.fichajes-periodo {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--accent) 12%, #fff);
  font-size: 14px;
  font-weight: 700;
}

.fichajes-cifras {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.fichajes-resumen div.fichajes-cifra {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
}

.fichajes-cifra dt {
  margin: 0;
  color: var(--text-2);
  font-size: 12px;
  font-weight: 500;
}

.fichajes-cifra dd {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
}

.fichajes-ver-analisis {
  display: inline-block;
  margin-top: 14px;
  color: var(--accent);
  font-size: 13px;
}

.fichajes-historial {
  width: 100%;
  margin-top: 20px;
}

button.fichajes-historial-cabecera {
  width: 100%;
  padding: 14px 18px;
  border: 0;
  border-radius: 0;
  background: transparent;
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

button.fichajes-historial-cabecera[aria-expanded="true"] {
  border-bottom: 1px solid var(--border);
}

button.fichajes-historial-cabecera:hover {
  border-bottom-color: var(--border);
  background: transparent;
}

.fichajes-historial-flecha {
  margin-left: auto;
  color: var(--text-3);
  font-size: 18px;
  line-height: 1;
  transition: transform 0.15s;
}

.fichajes-historial-flecha.abierta {
  transform: rotate(90deg);
}

.fichajes-historial .error {
  margin: 0;
  padding: 16px 18px;
}

.fichajes-historial-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.fichajes-historial table.equipo {
  min-width: 860px;
}
</style>
