<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { delegacionVisible } from "../fechas.js";
import { agruparPersonas, iniciales, numeroFormulario as numero } from "../personas.js";
import {
  borrarAjuste,
  crearAjuste,
  editarAjuste,
  crearTrabajador,
  darDeBaja as pedirBaja,
  listarAjustes,
} from "../api/usuarios.js";
import Analisis from "./Analisis.vue";
import Cobertura from "./Cobertura.vue";
import HorarioHabitual from "./HorarioHabitual.vue";
import Cuadrante from "./Cuadrante.vue";
import DuracionPausa from "./DuracionPausa.vue";
import EditarTrabajador from "./EditarTrabajador.vue";
import FichaEmpleado from "./FichaEmpleado.vue";
import TrabajadoresInactivos from "./TrabajadoresInactivos.vue";

const props = defineProps({
  token: { type: String, required: true },
  nombreSesion: { type: String, required: true },
  departamento: { type: String, default: "" },
});

const vista = ref("cuadrante");
const ambito = ref("departamento");
const fichaLogin = ref("");
const cuadrante = ref(null);
const inactivos = ref(null);
const departamentos = ref([]);
const departamentoId = ref("");
const departamentosCargados = ref(false);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const numeroSap = ref("");
const grupo = ref("STEF");
const coste = ref("");
const letras = ["L", "M", "X", "J", "V", "S", "D"];
const horarioAlta = ref(null);
const vacaciones = ref("");
const horasContrato = ref("");
const pausa = ref(0);
const horaPausa = ref("");
const seccionId = ref("");
const errorTrabajador = ref("");
const dialogo = ref(null);
const dialogoHorario = ref(null);
const horarioPropio = ref(false);
const horarioForm = ref(null);
const cuadranteMandos = ref(null);
const trabajadorHorario = ref(null);
const dialogoAjustes = ref(null);
const trabajadorAjuste = ref(null);
const ajustes = ref([]);
const fechaAjuste = ref("");
const operacionAjuste = ref("sumar");
const horasAjuste = ref(0);
const minutosAjuste = ref(0);
const motivoAjuste = ref("");
const errorAjuste = ref("");
const formularioAjusteAbierto = ref(false);
const ajusteEnEdicion = ref(null);
const fechaAjusteInput = ref(null);
const personaEditar = ref(null);
const editorTrabajador = ref(null);
let recargaEdicion = Promise.resolve();
const aviso = ref(false);
const busqueda = ref("");
const filtroSeccion = ref("");
const menuAbierto = ref("");
let avisoTemporizador = 0;

const equipo = computed(
  () => departamentos.value.find((item) => item.id === departamentoId.value) || null,
);
const variosDepartamentos = computed(() => departamentos.value.length > 1);
const muestraHorario = computed(() => equipo.value?.usa_horario_habitual !== false);
const seccionesEquipo = computed(() => equipo.value?.secciones ?? []);
const trabajadores = computed(() => equipo.value?.trabajadores ?? []);
const chipsSeccion = computed(() => {
  if (!seccionesEquipo.value.length) {
    return [];
  }
  const lista = trabajadores.value;
  const chips = [
    { id: "", nombre: "Todas", total: lista.length },
  ];
  for (const seccion of seccionesEquipo.value) {
    chips.push({
      id: seccion.id,
      nombre: seccion.nombre,
      total: lista.filter((trabajador) => trabajador.seccion_id === seccion.id).length,
    });
  }
  chips.push({
    id: "sin",
    nombre: "Sin sección",
    total: lista.filter((trabajador) => !trabajador.seccion_id).length,
  });
  return chips;
});
const filtrados = computed(() => {
  let lista = trabajadores.value;
  if (seccionesEquipo.value.length && filtroSeccion.value) {
    if (filtroSeccion.value === "sin") {
      lista = lista.filter((trabajador) => !trabajador.seccion_id);
    } else {
      lista = lista.filter((trabajador) => trabajador.seccion_id === filtroSeccion.value);
    }
  }
  const texto = busqueda.value.trim().toLocaleLowerCase("es");
  if (!texto) {
    return lista;
  }
  return lista.filter((trabajador) => {
    const nombreVisible = trabajador.nombre.toLocaleLowerCase("es");
    const loginVisible = trabajador.login.toLocaleLowerCase("es");
    return nombreVisible.includes(texto) || loginVisible.includes(texto);
  });
});
const gruposEquipo = computed(() => agruparPersonas(filtrados.value));

function abrirFicha(trabajador) {
  fichaLogin.value = trabajador.login;
  vista.value = "ficha";
}

function etiquetaDepartamento(item) {
  return `${item.nombre} · ${delegacionVisible(item.delegacion)}`;
}

async function cargarDepartamentos() {
  error.value = "";
  try {
    const lista = await listar(props.token);
    departamentos.value = lista;
    if (!lista.some((item) => item.id === departamentoId.value)) {
      departamentoId.value = lista[0]?.id || "";
    }
  } catch (causa) {
    departamentos.value = [];
    departamentoId.value = "";
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
  departamentosCargados.value = true;
}

function reiniciarHorario() {
  horarioAlta.value?.reiniciar();
}

function vaciarAlta() {
  nombre.value = "";
  login.value = "";
  clave.value = "";
  numeroSap.value = "";
  grupo.value = "STEF";
  coste.value = "";
  pausa.value = 0;
  horaPausa.value = "";
  reiniciarHorario();
  vacaciones.value = "";
  horasContrato.value = "";
  seccionId.value = "";
  errorTrabajador.value = "";
}

function datosPersona(trabajador) {
  const partes = [trabajador.login];
  if (trabajador.numero_sap) {
    partes.push(`SAP ${trabajador.numero_sap}`);
  }
  if (seccionesEquipo.value.length && trabajador.seccion_id) {
    const seccion = seccionesEquipo.value.find((item) => item.id === trabajador.seccion_id);
    if (seccion) {
      partes.push(seccion.nombre);
    }
  }
  return partes.join(" · ");
}

function abrirMenu(loginNombre) {
  menuAbierto.value = menuAbierto.value === loginNombre ? "" : loginNombre;
}

function cerrarMenu() {
  menuAbierto.value = "";
}

function alClicFueraMenu(evento) {
  if (!(evento.target instanceof Node)) {
    return;
  }
  if (!evento.target.closest(".equipo-mas")) {
    cerrarMenu();
  }
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
  const dias = [...(trabajador.horario || [])].sort((a, b) => a.dia_semana - b.dia_semana);
  if (!dias.length) {
    return "—";
  }
  const grupos = [];
  for (const dia of dias) {
    const ultimo = grupos[grupos.length - 1];
    const sigue = ultimo
      && dia.inicio === ultimo.inicio
      && dia.fin === ultimo.fin
      && dia.dia_semana === ultimo.hasta + 1;
    if (sigue) {
      ultimo.hasta = dia.dia_semana;
    } else {
      grupos.push({
        desde: dia.dia_semana,
        hasta: dia.dia_semana,
        inicio: dia.inicio,
        fin: dia.fin,
      });
    }
  }
  return grupos
    .map((grupoDia) => {
      const rango = grupoDia.desde === grupoDia.hasta
        ? letras[grupoDia.desde]
        : `${letras[grupoDia.desde]}-${letras[grupoDia.hasta]}`;
      return `${rango} ${grupoDia.inicio}–${grupoDia.fin}`;
    })
    .join(", ");
}

function cantidad(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  return Number(valor).toLocaleString("es-ES");
}

function abrirPerfil(trabajador) {
  personaEditar.value = { ...trabajador, rol: "trabajador" };
}

function trabajadorActual(login) {
  return (equipo.value?.trabajadores || []).find((item) => item.login === login) || null;
}

function alGuardarTrabajador(bloque) {
  recargaEdicion = recargaEdicion.then(() => recargarEdicion(bloque));
}

async function recargarEdicion(bloque) {
  try {
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch {
    // La recarga fallida no debe impedir el aviso del bloque guardado.
  }
  const actual = personaEditar.value;
  if (!actual) {
    return;
  }
  const fresco = trabajadorActual(actual.login);
  if (fresco) {
    Object.assign(actual, fresco, { rol: "trabajador" });
  }
  editorTrabajador.value?.aplicar(bloque, Boolean(fresco));
}

function cuenta(total) {
  return total === 1 ? "1 trabajador" : `${total} trabajadores`;
}

function abrirHorarioPropio() {
  horarioPropio.value = true;
  trabajadorHorario.value = null;
  dialogoHorario.value?.showModal();
  dialogoHorario.value?.querySelector("[name='desde-horario']")?.focus();
}

function cerrarHorario() {
  dialogoHorario.value?.close();
}

function alCerrarHorario() {
  trabajadorHorario.value = null;
  horarioPropio.value = false;
}

function alFondoHorario(evento) {
  if (evento.target === dialogoHorario.value) {
    cerrarHorario();
  }
}

async function alGuardarHorario() {
  const propio = horarioPropio.value;
  cerrarHorario();
  if (propio) {
    await cuadranteMandos.value?.recargar();
    return;
  }
  await cargarDepartamentos();
  await cuadrante.value?.recargar();
}

async function darDeBaja(trabajador) {
  if (!window.confirm(`¿Dar de baja a ${trabajador.nombre}?`)) {
    return;
  }
  error.value = "";
  try {
    await pedirBaja(props.token, trabajador.login);
    const lista = equipo.value?.trabajadores;
    if (lista) {
      const indice = lista.findIndex((item) => item.login === trabajador.login);
      if (indice >= 0) {
        lista.splice(indice, 1);
      }
    }
    await inactivos.value?.recargar();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo dar de baja";
  }
}

async function guardar() {
  errorTrabajador.value = "";
  try {
    const alta = {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      grupo: grupo.value,
      numero_sap: numeroSap.value,
      vacaciones: numero(vacaciones.value),
      horas_contrato: numero(horasContrato.value),
      pausa_minutos: pausa.value,
      seccion_id: seccionId.value || null,
    };
    if (Number(pausa.value) > 0 && horaPausa.value) {
      alta.pausa_habitual = horaPausa.value.slice(0, 5);
    }
    if (grupo.value === "ETT" && coste.value !== "" && coste.value !== null) {
      alta.coste = numero(coste.value);
    }
    if (muestraHorario.value) {
      const horario = horarioAlta.value?.horarioDias();
      if (!horario?.horario_dias) {
        errorTrabajador.value = horario?.error || "Marca al menos un día.";
        return;
      }
      alta.horario_dias = horario.horario_dias;
    }
    if (departamentoId.value) {
      alta.departamento_id = departamentoId.value;
    }
    await crearTrabajador(props.token, alta);
    cerrarAlta();
    mostrarAviso();
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function fechaVisible(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function horasConSigno(valor) {
  const numeroHoras = Number(valor);
  const texto = Math.abs(numeroHoras).toLocaleString("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  if (numeroHoras > 0) {
    return `+${texto}`;
  }
  if (numeroHoras < 0) {
    return `-${texto}`;
  }
  return texto;
}

async function abrirAjustes(trabajador) {
  trabajadorAjuste.value = trabajador;
  fechaAjuste.value = "";
  operacionAjuste.value = "sumar";
  horasAjuste.value = 0;
  minutosAjuste.value = 0;
  motivoAjuste.value = "";
  errorAjuste.value = "";
  formularioAjusteAbierto.value = false;
  ajusteEnEdicion.value = null;
  ajustes.value = [];
  dialogoAjustes.value?.showModal();
  try {
    ajustes.value = await listarAjustes(props.token, trabajador.login);
  } catch (causa) {
    errorAjuste.value = causa instanceof Error ? causa.message : "No se pudieron cargar los ajustes";
  }
}

function cerrarAjustes() {
  dialogoAjustes.value?.close();
}

function alCerrarAjustes() {
  trabajadorAjuste.value = null;
  ajustes.value = [];
  errorAjuste.value = "";
  formularioAjusteAbierto.value = false;
  ajusteEnEdicion.value = null;
}

function alFondoAjustes(evento) {
  if (evento.target === dialogoAjustes.value) {
    cerrarAjustes();
  }
}

function vaciarFormularioAjuste() {
  fechaAjuste.value = "";
  operacionAjuste.value = "sumar";
  horasAjuste.value = 0;
  minutosAjuste.value = 0;
  motivoAjuste.value = "";
}

function rellenarFormularioAjuste(ajuste) {
  const totalMinutos = Math.round(Math.abs(Number(ajuste.horas)) * 60);
  fechaAjuste.value = ajuste.fecha;
  operacionAjuste.value = Number(ajuste.horas) < 0 ? "restar" : "sumar";
  horasAjuste.value = Math.floor(totalMinutos / 60);
  minutosAjuste.value = totalMinutos % 60;
  motivoAjuste.value = ajuste.motivo;
}

async function abrirFormularioAjuste() {
  ajusteEnEdicion.value = null;
  vaciarFormularioAjuste();
  errorAjuste.value = "";
  formularioAjusteAbierto.value = true;
  await nextTick();
  fechaAjusteInput.value?.focus();
}

async function editarFormularioAjuste(ajuste) {
  ajusteEnEdicion.value = ajuste.id;
  rellenarFormularioAjuste(ajuste);
  errorAjuste.value = "";
  formularioAjusteAbierto.value = true;
  await nextTick();
  fechaAjusteInput.value?.focus();
}

function cancelarFormularioAjuste() {
  vaciarFormularioAjuste();
  errorAjuste.value = "";
  formularioAjusteAbierto.value = false;
  ajusteEnEdicion.value = null;
}

async function guardarAjuste() {
  const persona = trabajadorAjuste.value;
  if (!persona) {
    return;
  }
  const horasEnteras = Number(horasAjuste.value);
  const minutos = Number(minutosAjuste.value);
  if (
    !Number.isInteger(horasEnteras)
    || horasEnteras < 0
    || ![0, 15, 30, 45].includes(minutos)
    || !fechaAjuste.value
    || !motivoAjuste.value.trim()
  ) {
    errorAjuste.value = "Faltan datos";
    return;
  }
  if (horasEnteras === 0 && minutos === 0) {
    errorAjuste.value = "Indica al menos 15 minutos";
    return;
  }
  const valorHoras = horasEnteras + minutos / 60;
  const numeroHoras = operacionAjuste.value === "restar" ? -valorHoras : valorHoras;
  errorAjuste.value = "";
  const datos = {
    fecha: fechaAjuste.value,
    horas: numeroHoras,
    motivo: motivoAjuste.value.trim(),
  };
  try {
    if (ajusteEnEdicion.value) {
      const actualizado = await editarAjuste(props.token, ajusteEnEdicion.value, datos);
      ajustes.value = ajustes.value
        .map((item) => (item.id === actualizado.id ? actualizado : item))
        .sort((a, b) => a.fecha.localeCompare(b.fecha) || a.id.localeCompare(b.id));
    } else {
      const creado = await crearAjuste(props.token, {
        usuario_afectado: persona.login,
        ...datos,
      });
      ajustes.value = [...ajustes.value, creado].sort((a, b) => a.fecha.localeCompare(b.fecha) || a.id.localeCompare(b.id));
    }
    vaciarFormularioAjuste();
    formularioAjusteAbierto.value = false;
    ajusteEnEdicion.value = null;
  } catch (causa) {
    errorAjuste.value = causa instanceof Error ? causa.message : "No se pudo guardar el ajuste";
  }
}

async function eliminarAjuste(ajuste) {
  const persona = trabajadorAjuste.value;
  if (!persona || !window.confirm("¿Eliminar este ajuste?")) {
    return;
  }
  errorAjuste.value = "";
  try {
    await borrarAjuste(props.token, ajuste.id);
    ajustes.value = ajustes.value.filter((item) => item.id !== ajuste.id);
    if (ajusteEnEdicion.value === ajuste.id) {
      cancelarFormularioAjuste();
    }
  } catch (causa) {
    errorAjuste.value = causa instanceof Error ? causa.message : "No se pudo eliminar el ajuste";
  }
}

watch(departamentoId, () => {
  busqueda.value = "";
  filtroSeccion.value = "";
  menuAbierto.value = "";
  if (vista.value === "ficha") {
    fichaLogin.value = "";
    vista.value = "equipo";
  }
  if (dialogo.value?.open) {
    cerrarAlta();
  }
  if (dialogoHorario.value?.open) {
    cerrarHorario();
  }
  if (personaEditar.value) {
    personaEditar.value = null;
  }
  if (dialogoAjustes.value?.open) {
    cerrarAjustes();
  }
});

watch(vista, (nueva) => {
  if (nueva !== "equipo") {
    cerrarMenu();
  }
  if (nueva !== "equipo" && dialogo.value?.open) {
    cerrarAlta();
  }
  if (nueva !== "equipo" && dialogoHorario.value?.open) {
    cerrarHorario();
  }
  if (nueva !== "equipo" && personaEditar.value) {
    personaEditar.value = null;
  }
  if (nueva !== "equipo" && dialogoAjustes.value?.open) {
    cerrarAjustes();
  }
});

onMounted(() => {
  cargarDepartamentos();
  document.addEventListener("click", alClicFueraMenu);
});

onUnmounted(() => {
  document.removeEventListener("click", alClicFueraMenu);
});
</script>

<template>
  <nav class="vistas">
    <button type="button" :class="{ activo: vista === 'cuadrante' }" @click="vista = 'cuadrante'">
      Cuadrante
    </button>
    <button type="button" :class="{ activo: vista === 'cobertura' }" @click="vista = 'cobertura'">
      Cobertura
    </button>
    <button type="button" :class="{ activo: vista === 'equipo' }" @click="vista = 'equipo'">
      Equipo
    </button>
    <button type="button" :class="{ activo: vista === 'analisis' }" @click="vista = 'analisis'">
      Análisis
    </button>
  </nav>
  <section v-if="vista === 'cuadrante'" class="bienvenida">
    <p class="bienvenida-titulo">Bienvenido, {{ nombreSesion }}</p>
    <p class="bienvenida-detalle">
      Gestiona el cuadrante y el equipo de {{ departamento || "tu departamento" }}.
    </p>
  </section>
  <label v-if="variosDepartamentos" class="analisis-filtro departamento-mando">
    Departamento
    <select v-model="departamentoId" class="equipo-grupo">
      <option v-for="item in departamentos" :key="item.id" :value="item.id">
        {{ etiquetaDepartamento(item) }}
      </option>
    </select>
  </label>
  <div v-show="vista === 'cuadrante'">
    <div class="vistas cuadrante-ambito">
      <button type="button" :class="{ activo: ambito === 'departamento' }" @click="ambito = 'departamento'">
        Mi departamento
      </button>
      <button type="button" :class="{ activo: ambito === 'mandos' }" @click="ambito = 'mandos'">
        Mandos + Funcionales
      </button>
    </div>
    <Cuadrante
      v-if="ambito === 'departamento' && departamentosCargados"
      :key="departamentoId || 'propio'"
      ref="cuadrante"
      :token="token"
      :departamento-id="departamentoId"
      editable
    />
    <Cuadrante
      v-else-if="ambito === 'mandos'"
      ref="cuadranteMandos"
      :token="token"
      mandos
      @cambiar-horario="abrirHorarioPropio"
    />
  </div>
  <Cobertura
    v-if="vista === 'cobertura' && departamentosCargados"
    :key="departamentoId || 'propio'"
    :token="token"
    :departamento-id="departamentoId"
  />
  <Analisis
    v-if="vista === 'analisis'"
    :key="departamentoId || 'propio'"
    :token="token"
    :departamento-id="departamentoId"
    mando
  />
  <FichaEmpleado v-if="vista === 'ficha'" :token="token" :login="fichaLogin" />
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
        <div v-if="chipsSeccion.length" class="equipo-chips">
          <button
            v-for="chip in chipsSeccion"
            :key="chip.id || 'todas'"
            type="button"
            :class="{ activo: filtroSeccion === chip.id }"
            @click="filtroSeccion = chip.id"
          >
            {{ chip.nombre }} ({{ chip.total }})
          </button>
        </div>
        <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
      </div>
      <div v-if="!gruposEquipo.length" class="panel">
        <p class="panel-vacio">Ningún trabajador coincide con el filtro.</p>
      </div>
      <div class="equipo-grupos">
        <section v-for="grupoEquipo in gruposEquipo" :key="grupoEquipo.id" class="panel">
          <header class="panel-cabecera">
            <h2>{{ grupoEquipo.titulo }}</h2>
            <span class="panel-cuenta">{{ cuenta(grupoEquipo.personas.length) }}</span>
          </header>
          <table class="equipo">
            <thead>
              <tr>
                <th>Trabajador</th>
                <th v-if="muestraHorario">Horario</th>
                <th class="col-extra">Horas/semana</th>
                <th class="col-extra">Vacaciones/año</th>
                <th class="equipo-acciones">Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trabajador in grupoEquipo.personas" :key="trabajador.login">
                <td>
                  <span class="equipo-persona">
                    <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
                    <span class="persona-datos">
                      <strong>{{ trabajador.nombre }}</strong>
                      <span>{{ datosPersona(trabajador) }}</span>
                    </span>
                  </span>
                </td>
                <td v-if="muestraHorario">{{ horario(trabajador) }}</td>
                <td class="col-extra">{{ cantidad(trabajador.horas_contrato) }}</td>
                <td class="col-extra">{{ cantidad(trabajador.vacaciones) }}</td>
                <td class="equipo-acciones">
                  <div class="equipo-acciones-botones">
                  <button type="button" @click="abrirFicha(trabajador)">Ver ficha</button>
                  <button type="button" @click="abrirAjustes(trabajador)">Ajustes</button>
                  <div class="equipo-mas">
                    <button type="button" aria-haspopup="true" :aria-expanded="menuAbierto === trabajador.login" @click.stop="abrirMenu(trabajador.login)">⋯</button>
                    <div v-if="menuAbierto === trabajador.login" class="equipo-mas-menu" role="menu">
                      <button type="button" role="menuitem" @click="cerrarMenu(); abrirPerfil(trabajador)">Editar</button>
                      <button type="button" class="peligro" role="menuitem" @click="cerrarMenu(); darDeBaja(trabajador)">Dar de baja</button>
                    </div>
                  </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </template>
    <TrabajadoresInactivos
      v-if="departamentoId"
      ref="inactivos"
      :token="token"
      :departamento-id="departamentoId"
      @ver-ficha="(login) => abrirFicha({ login })"
      @reactivado="cargarDepartamentos"
    />
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
          <label class="ancho">
            Número de personal (SAP)
            <input v-model="numeroSap" name="numero-sap" autocomplete="off" />
          </label>
          <p class="ancho campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
          <h3>Contrato</h3>
          <label v-if="seccionesEquipo.length" class="ancho">
            Sección
            <select v-model="seccionId">
              <option value="">Sin sección</option>
              <option v-for="seccion in seccionesEquipo" :key="seccion.id" :value="seccion.id">
                {{ seccion.nombre }}
              </option>
            </select>
          </label>
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
          <label v-if="grupo === 'ETT'" class="ancho">
            Coste (€/hora)
            <input v-model="coste" name="coste" type="number" min="0" step="0.0001" />
          </label>
          <label class="ancho">
            Pausa
            <DuracionPausa v-model="pausa" />
          </label>
          <p class="ancho campo-pista">Descanso diario no pagado. Se resta de las horas planificadas.</p>
          <label v-if="Number(pausa) > 0" class="ancho">
            Hora de pausa
            <input v-model="horaPausa" name="hora-pausa-trabajador" type="time" />
          </label>
          <p v-if="Number(pausa) > 0" class="ancho campo-pista">Si la indicas, Cobertura la tiene en cuenta.</p>
          <HorarioHabitual v-if="muestraHorario" ref="horarioAlta" />
        </div>
        <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
        <footer class="alta-dialogo-pie">
          <button type="button" @click="cerrarAlta">Cancelar</button>
          <button class="primario" type="submit">Guardar trabajador</button>
        </footer>
      </form>
  </dialog>
  <dialog ref="dialogoHorario" class="alta-dialogo" @close="alCerrarHorario" @click="alFondoHorario">
    <form @submit.prevent="horarioForm?.guardar()">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>{{ horarioPropio ? "Cambiar mi horario" : "Cambiar horario" }}</h2>
          <p v-if="trabajadorHorario" class="alta-dialogo-persona">{{ trabajadorHorario.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarHorario">✕</button>
      </header>
      <HorarioHabitual
        ref="horarioForm"
        :token="token"
        :persona="trabajadorHorario"
        :modo="horarioPropio ? 'propio' : 'trabajador'"
        @guardado="alGuardarHorario"
      />
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarHorario">Cancelar</button>
        <button class="primario" type="submit">Guardar horario</button>
      </footer>
    </form>
  </dialog>
  <EditarTrabajador
    v-if="personaEditar"
    ref="editorTrabajador"
    :token="token"
    :persona="personaEditar"
    :secciones="seccionesEquipo"
    :con-horario="muestraHorario"
    @guardado="alGuardarTrabajador"
    @cerrar="personaEditar = null"
  />
  <dialog
    ref="dialogoAjustes"
    class="alta-dialogo ajustes-dialogo"
    :class="{ 'con-formulario': formularioAjusteAbierto }"
    @close="alCerrarAjustes"
    @click="alFondoAjustes"
  >
    <header class="alta-dialogo-cabecera">
      <div>
        <h2>Ajustes</h2>
        <p v-if="trabajadorAjuste" class="alta-dialogo-persona">{{ trabajadorAjuste.nombre }}</p>
      </div>
      <button type="button" class="dialogo-cerrar" @click="cerrarAjustes">✕</button>
    </header>
    <div class="ajustes-disposicion">
      <div class="ajustes-listado">
        <div class="ajustes-contenido">
          <p v-if="!ajustes.length" class="panel-vacio">Sin ajustes registrados.</p>
          <div v-else class="ajustes-tabla-scroll">
            <table class="ajustes-tabla">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Horas</th>
                  <th>Motivo</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ajuste in ajustes" :key="ajuste.id">
                  <td>{{ fechaVisible(ajuste.fecha) }}</td>
                  <td class="ajustes-horas">{{ horasConSigno(ajuste.horas) }}</td>
                  <td>
                    {{ ajuste.motivo }}
                    <small>{{ ajuste.registra }}</small>
                  </td>
                  <td class="ajustes-acciones">
                    <button type="button" @click="editarFormularioAjuste(ajuste)">Editar</button>
                    <button type="button" @click="eliminarAjuste(ajuste)">Eliminar</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <p v-if="errorAjuste && !formularioAjusteAbierto" class="error" role="alert">{{ errorAjuste }}</p>
        <div v-if="!formularioAjusteAbierto" class="ajustes-anadir">
          <button type="button" @click="abrirFormularioAjuste">+ Añadir ajuste</button>
        </div>
      </div>
      <form v-if="formularioAjusteAbierto" novalidate class="ajustes-formulario" @submit.prevent="guardarAjuste">
        <div class="alta-dialogo-cuerpo">
          <label class="ancho">
            Fecha
            <input ref="fechaAjusteInput" v-model="fechaAjuste" name="fecha-ajuste" type="date" />
          </label>
          <fieldset class="ajustes-operacion ancho">
            <legend>Operación</legend>
            <label>
              <input v-model="operacionAjuste" type="radio" name="operacion-ajuste" value="sumar" />
              <span>Sumar</span>
            </label>
            <label>
              <input v-model="operacionAjuste" type="radio" name="operacion-ajuste" value="restar" />
              <span>Restar</span>
            </label>
          </fieldset>
          <label>
            Horas
            <input v-model="horasAjuste" name="horas-ajuste" type="number" min="0" step="1" />
          </label>
          <label>
            Minutos
            <select v-model.number="minutosAjuste" name="minutos-ajuste">
              <option :value="0">0</option>
              <option :value="15">15</option>
              <option :value="30">30</option>
              <option :value="45">45</option>
            </select>
          </label>
          <label class="ancho">
            Motivo
            <input v-model="motivoAjuste" name="motivo-ajuste" />
          </label>
        </div>
        <p v-if="errorAjuste" class="error" role="alert">{{ errorAjuste }}</p>
        <footer class="alta-dialogo-pie">
          <button type="button" @click="cancelarFormularioAjuste">Cancelar</button>
          <button class="primario" type="submit">
            {{ ajusteEnEdicion ? "Guardar cambios" : "Añadir ajuste" }}
          </button>
        </footer>
      </form>
    </div>
  </dialog>
  <p v-if="aviso" class="aviso-ok" role="status">Trabajador creado</p>
</template>

<style scoped>
.ajustes-dialogo {
  max-width: 680px;
}

.ajustes-dialogo.con-formulario {
  max-width: 1040px;
}

.ajustes-dialogo.con-formulario .ajustes-disposicion {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(340px, 0.85fr);
  align-items: start;
}

.ajustes-contenido {
  padding: 16px 20px 0;
}

.ajustes-contenido .panel-vacio {
  padding: 12px 0;
}

.ajustes-tabla-scroll {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: 10px;
}

.ajustes-tabla {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ajustes-tabla th,
.ajustes-tabla td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: middle;
}

.ajustes-tabla th {
  background: var(--bg);
  color: var(--text-3);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.ajustes-tabla tr:last-child td {
  border-bottom: 0;
}

.ajustes-tabla small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 11px;
}

.ajustes-horas {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.ajustes-acciones {
  width: 1%;
  white-space: nowrap;
  text-align: right !important;
}

.ajustes-acciones button + button {
  margin-left: 6px;
}

.ajustes-anadir {
  padding: 14px 20px 20px;
}

.ajustes-formulario {
  min-width: 0;
  border-left: 1px solid var(--border);
}

.ajustes-operacion {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.ajustes-operacion legend {
  margin-bottom: 6px;
  color: var(--text-2);
  font-size: 12px;
  font-weight: 600;
}

.ajustes-operacion label {
  position: relative;
}

.ajustes-operacion input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.ajustes-operacion span {
  display: block;
  padding: 9px 12px;
  border: 1px solid var(--border-strong);
  text-align: center;
  color: var(--text-2);
  background: var(--panel);
}

.ajustes-operacion label:first-of-type span {
  border-radius: 8px 0 0 8px;
}

.ajustes-operacion label:last-of-type span {
  margin-left: -1px;
  border-radius: 0 8px 8px 0;
}

.ajustes-operacion input:checked + span {
  position: relative;
  z-index: 1;
  border-color: var(--accent);
  color: var(--accent);
  background: var(--manana-bg);
}

.ajustes-operacion input:focus-visible + span {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

@media (max-width: 699px) {
  .ajustes-dialogo.con-formulario .ajustes-disposicion {
    display: block;
  }

  .ajustes-formulario {
    margin-top: 14px;
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}
</style>
