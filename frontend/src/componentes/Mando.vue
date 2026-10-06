<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import {
  borrarAjuste,
  cambiarHorario,
  cambiarNumeroSap,
  crearAjuste,
  crearTrabajador,
  darDeBaja as pedirBaja,
  listarAjustes,
} from "../api/usuarios.js";
import Analisis from "./Analisis.vue";
import Cuadrante from "./Cuadrante.vue";
import FichaEmpleado from "./FichaEmpleado.vue";

const props = defineProps({
  token: { type: String, required: true },
});

const vista = ref("cuadrante");
const fichaLogin = ref("");
const cuadrante = ref(null);
const departamentos = ref([]);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const numeroSap = ref("");
const grupo = ref("STEF");
const letras = ["L", "M", "X", "J", "V", "S", "D"];
const diasMarcados = ref([true, true, true, true, true, false, false]);
const horasDia = ref(letras.map(() => ({ inicio: "", fin: "" })));
const plantillaDia = ref(null);
const propios = ref(letras.map(() => false));
const vacaciones = ref("");
const horasContrato = ref("");
const errorTrabajador = ref("");
const dialogo = ref(null);
const dialogoHorario = ref(null);
const trabajadorHorario = ref(null);
const desdeHorario = ref("");
const diasHorario = ref([true, true, true, true, true, false, false]);
const horasHorario = ref(letras.map(() => ({ inicio: "", fin: "" })));
const plantillaHorario = ref(null);
const propiosHorario = ref(letras.map(() => false));
const errorHorario = ref("");
const dialogoSap = ref(null);
const dialogoAjustes = ref(null);
const trabajadorAjuste = ref(null);
const ajustes = ref([]);
const fechaAjuste = ref("");
const horasAjuste = ref("");
const motivoAjuste = ref("");
const errorAjuste = ref("");
const trabajadorSap = ref(null);
const numeroSapEdit = ref("");
const errorSap = ref("");
const aviso = ref(false);
const busqueda = ref("");
let avisoTemporizador = 0;

const equipo = computed(() => departamentos.value[0] || null);
const trabajadores = computed(() => equipo.value?.trabajadores ?? []);
const filtrados = computed(() => {
  const texto = busqueda.value.trim().toLocaleLowerCase("es");
  if (!texto) {
    return trabajadores.value;
  }
  return trabajadores.value.filter((trabajador) => {
    const nombreVisible = trabajador.nombre.toLocaleLowerCase("es");
    const loginVisible = trabajador.login.toLocaleLowerCase("es");
    return nombreVisible.includes(texto) || loginVisible.includes(texto);
  });
});
const gruposEquipo = computed(() => [
  {
    id: "STEF",
    titulo: "Personal STEF",
    vacio: "Sin personal STEF en este departamento.",
    personas: filtrados.value.filter((trabajador) => trabajador.grupo === "STEF"),
    hay: trabajadores.value.some((trabajador) => trabajador.grupo === "STEF"),
  },
  {
    id: "ETT",
    titulo: "ETT",
    vacio: "Sin personal ETT en este departamento.",
    personas: filtrados.value.filter((trabajador) => trabajador.grupo === "ETT"),
    hay: trabajadores.value.some((trabajador) => trabajador.grupo === "ETT"),
  },
]);

function abrirFicha(trabajador) {
  fichaLogin.value = trabajador.login;
  vista.value = "ficha";
}

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

function reiniciarHorario() {
  diasMarcados.value = [true, true, true, true, true, false, false];
  horasDia.value = letras.map(() => ({ inicio: "", fin: "" }));
  plantillaDia.value = null;
  propios.value = letras.map(() => false);
}

function vaciarAlta() {
  nombre.value = "";
  login.value = "";
  clave.value = "";
  numeroSap.value = "";
  grupo.value = "STEF";
  reiniciarHorario();
  vacaciones.value = "";
  horasContrato.value = "";
  errorTrabajador.value = "";
}

function alMarcar(dia, evento) {
  const marcado = evento.target.checked;
  diasMarcados.value[dia] = marcado;
  if (!marcado || plantillaDia.value === null || propios.value[dia]) {
    return;
  }
  const origen = horasDia.value[plantillaDia.value];
  horasDia.value[dia] = { inicio: origen.inicio, fin: origen.fin };
}

function alHora(dia, campo, valor) {
  const actual = horasDia.value[dia];
  horasDia.value[dia] = { ...actual, [campo]: valor };
  if (plantillaDia.value === null) {
    plantillaDia.value = dia;
  } else if (dia !== plantillaDia.value) {
    propios.value[dia] = true;
    return;
  }
  const origen = horasDia.value[dia];
  horasDia.value = horasDia.value.map((item, indice) => {
    if (indice === dia) {
      return origen;
    }
    if (!diasMarcados.value[indice] || propios.value[indice]) {
      return item;
    }
    return { inicio: origen.inicio, fin: origen.fin };
  });
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

function abrirSap(trabajador) {
  trabajadorSap.value = trabajador;
  numeroSapEdit.value = trabajador.numero_sap || "";
  errorSap.value = "";
  dialogoSap.value?.showModal();
  dialogoSap.value?.querySelector("[name='numero-sap-edit']")?.focus();
}

function cerrarSap() {
  dialogoSap.value?.close();
}

function alCerrarSap() {
  trabajadorSap.value = null;
  errorSap.value = "";
}

function alFondoSap(evento) {
  if (evento.target === dialogoSap.value) {
    cerrarSap();
  }
}

async function guardarSap() {
  const persona = trabajadorSap.value;
  if (!persona) {
    return;
  }
  errorSap.value = "";
  try {
    const respuesta = await cambiarNumeroSap(props.token, persona.login, numeroSapEdit.value);
    persona.numero_sap = respuesta.numero_sap;
    cerrarSap();
  } catch (causa) {
    errorSap.value = causa instanceof Error ? causa.message : "No se pudo guardar el número";
  }
}

function cuenta(total) {
  return total === 1 ? "1 trabajador" : `${total} trabajadores`;
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

function abrirHorario(trabajador) {
  trabajadorHorario.value = trabajador;
  desdeHorario.value = lunesQueViene();
  errorHorario.value = "";
  const marcados = letras.map(() => false);
  const horas = letras.map(() => ({ inicio: "", fin: "" }));
  const propio = letras.map(() => false);
  let plantilla = null;
  for (const dia of trabajador.horario || []) {
    if (dia.dia_semana < 0 || dia.dia_semana > 6) {
      continue;
    }
    marcados[dia.dia_semana] = true;
    horas[dia.dia_semana] = { inicio: dia.inicio || "", fin: dia.fin || "" };
    propio[dia.dia_semana] = true;
    if (plantilla === null) {
      plantilla = dia.dia_semana;
    }
  }
  diasHorario.value = marcados;
  horasHorario.value = horas;
  propiosHorario.value = propio;
  plantillaHorario.value = plantilla;
  dialogoHorario.value?.showModal();
  dialogoHorario.value?.querySelector("[name='desde-horario']")?.focus();
}

function cerrarHorario() {
  dialogoHorario.value?.close();
}

function alCerrarHorario() {
  trabajadorHorario.value = null;
  errorHorario.value = "";
}

function alFondoHorario(evento) {
  if (evento.target === dialogoHorario.value) {
    cerrarHorario();
  }
}

function alMarcarHorario(dia, evento) {
  const marcado = evento.target.checked;
  diasHorario.value[dia] = marcado;
  if (!marcado || plantillaHorario.value === null || propiosHorario.value[dia]) {
    return;
  }
  const origen = horasHorario.value[plantillaHorario.value];
  horasHorario.value[dia] = { inicio: origen.inicio, fin: origen.fin };
}

function alHoraHorario(dia, campo, valor) {
  const actual = horasHorario.value[dia];
  horasHorario.value[dia] = { ...actual, [campo]: valor };
  if (plantillaHorario.value === null) {
    plantillaHorario.value = dia;
  } else if (dia !== plantillaHorario.value) {
    propiosHorario.value[dia] = true;
    return;
  }
  const origen = horasHorario.value[dia];
  horasHorario.value = horasHorario.value.map((item, indice) => {
    if (indice === dia) {
      return origen;
    }
    if (!diasHorario.value[indice] || propiosHorario.value[indice]) {
      return item;
    }
    return { inicio: origen.inicio, fin: origen.fin };
  });
}

async function guardarHorario() {
  errorHorario.value = "";
  const persona = trabajadorHorario.value;
  if (!persona) {
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
  const horarioDias = [];
  for (let dia = 0; dia < letras.length; dia += 1) {
    if (!diasHorario.value[dia]) {
      continue;
    }
    const horas = horasHorario.value[dia];
    if (!horas.inicio || !horas.fin) {
      errorHorario.value = "Indica la hora de inicio y de fin de cada día marcado.";
      return;
    }
    horarioDias.push({
      dia_semana: dia,
      hora_inicio: horas.inicio,
      hora_fin: horas.fin,
    });
  }
  if (!horarioDias.length) {
    errorHorario.value = "Marca al menos un día.";
    return;
  }
  try {
    await cambiarHorario(props.token, persona.login, {
      desde: desdeHorario.value,
      horario_dias: horarioDias,
    });
    cerrarHorario();
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorHorario.value = causa instanceof Error ? causa.message : "No se pudo cambiar el horario";
  }
}

async function darDeBaja(trabajador) {
  if (!window.confirm(`¿Dar de baja a ${trabajador.nombre}?`)) {
    return;
  }
  error.value = "";
  try {
    await pedirBaja(props.token, trabajador.login);
    const lista = equipo.value?.trabajadores;
    if (!lista) {
      return;
    }
    const indice = lista.findIndex((item) => item.login === trabajador.login);
    if (indice >= 0) {
      lista.splice(indice, 1);
    }
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo dar de baja";
  }
}

async function guardar() {
  errorTrabajador.value = "";
  const horarioDias = [];
  for (let dia = 0; dia < letras.length; dia += 1) {
    if (!diasMarcados.value[dia]) {
      continue;
    }
    const horas = horasDia.value[dia];
    if (!horas.inicio || !horas.fin) {
      errorTrabajador.value = "Indica la hora de inicio y de fin de cada día marcado.";
      return;
    }
    horarioDias.push({
      dia_semana: dia,
      hora_inicio: horas.inicio,
      hora_fin: horas.fin,
    });
  }
  if (!horarioDias.length) {
    errorTrabajador.value = "Marca al menos un día.";
    return;
  }
  try {
    await crearTrabajador(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      grupo: grupo.value,
      numero_sap: numeroSap.value,
      horario_dias: horarioDias,
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
  horasAjuste.value = "";
  motivoAjuste.value = "";
  errorAjuste.value = "";
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
}

function alFondoAjustes(evento) {
  if (evento.target === dialogoAjustes.value) {
    cerrarAjustes();
  }
}

async function guardarAjuste() {
  const persona = trabajadorAjuste.value;
  if (!persona) {
    return;
  }
  const textoHoras = String(horasAjuste.value ?? "").trim();
  const numeroHoras = Number(textoHoras);
  if (textoHoras === "" || Number.isNaN(numeroHoras) || !fechaAjuste.value || !motivoAjuste.value.trim()) {
    errorAjuste.value = "Faltan datos";
    return;
  }
  if (numeroHoras === 0) {
    errorAjuste.value = "Las horas no pueden ser 0";
    return;
  }
  errorAjuste.value = "";
  try {
    const creado = await crearAjuste(props.token, {
      usuario_afectado: persona.login,
      fecha: fechaAjuste.value,
      horas: numeroHoras,
      motivo: motivoAjuste.value.trim(),
    });
    ajustes.value = [...ajustes.value, creado].sort((a, b) => a.fecha.localeCompare(b.fecha) || a.id.localeCompare(b.id));
    fechaAjuste.value = "";
    horasAjuste.value = "";
    motivoAjuste.value = "";
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
  } catch (causa) {
    errorAjuste.value = causa instanceof Error ? causa.message : "No se pudo eliminar el ajuste";
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
  if (nueva !== "equipo" && dialogoHorario.value?.open) {
    cerrarHorario();
  }
  if (nueva !== "equipo" && dialogoSap.value?.open) {
    cerrarSap();
  }
  if (nueva !== "equipo" && dialogoAjustes.value?.open) {
    cerrarAjustes();
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
    <button type="button" :class="{ activo: vista === 'analisis' }" @click="vista = 'analisis'">
      Análisis
    </button>
  </nav>
  <div v-show="vista === 'cuadrante'">
    <Cuadrante ref="cuadrante" :token="token" editable />
  </div>
  <Analisis v-if="vista === 'analisis'" :token="token" mando />
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
        <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
      </div>
      <div class="equipo-grupos">
        <section v-for="grupoEquipo in gruposEquipo" :key="grupoEquipo.id" class="panel">
          <header class="panel-cabecera">
            <h2>{{ grupoEquipo.titulo }}</h2>
            <span class="panel-cuenta">{{ cuenta(grupoEquipo.personas.length) }}</span>
          </header>
          <p v-if="!grupoEquipo.hay" class="panel-vacio">{{ grupoEquipo.vacio }}</p>
          <p v-else-if="!grupoEquipo.personas.length" class="panel-vacio">
            Ningún trabajador coincide con la búsqueda.
          </p>
          <table v-else class="equipo">
            <thead>
              <tr>
                <th>Trabajador</th>
                <th>Horario</th>
                <th class="col-extra">Horas/semana</th>
                <th class="col-extra">Vacaciones/año</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trabajador in grupoEquipo.personas" :key="trabajador.login">
                <td>
                  <span class="equipo-persona">
                    <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
                    <span class="persona-datos">
                      <strong>{{ trabajador.nombre }}</strong>
                      <span>{{ trabajador.login }}</span>
                      <span v-if="trabajador.numero_sap">{{ trabajador.numero_sap }}</span>
                    </span>
                  </span>
                </td>
                <td>{{ horario(trabajador) }}</td>
                <td class="col-extra">{{ cantidad(trabajador.horas_contrato) }}</td>
                <td class="col-extra">{{ cantidad(trabajador.vacaciones) }}</td>
                <td class="equipo-acciones">
                  <button type="button" @click="abrirHorario(trabajador)">Cambiar horario</button>
                  <button type="button" @click="abrirAjustes(trabajador)">Ajustes</button>
                  <button type="button" @click="abrirSap(trabajador)">Editar número SAP</button>
                  <button type="button" @click="darDeBaja(trabajador)">Dar de baja</button>
                  <button type="button" @click="abrirFicha(trabajador)">Ver ficha</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
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
          <label class="ancho">
            Número de personal (SAP)
            <input v-model="numeroSap" name="numero-sap" autocomplete="off" />
          </label>
          <p class="ancho campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
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
          <div class="ancho alta-dias-marcas">
            <label v-for="(letra, dia) in letras" :key="letra" class="alta-casilla">
              <input
                type="checkbox"
                :checked="diasMarcados[dia]"
                @change="alMarcar(dia, $event)"
              />
              {{ letra }}
            </label>
          </div>
          <div
            v-for="(letra, dia) in letras"
            v-show="diasMarcados[dia]"
            :key="`horas-${letra}`"
            class="ancho alta-dia-horas"
          >
            <span>{{ letra }}</span>
            <label>
              Hora de inicio
              <input
                :value="horasDia[dia].inicio"
                type="time"
                @input="alHora(dia, 'inicio', $event.target.value)"
              />
            </label>
            <label>
              Hora de fin
              <input
                :value="horasDia[dia].fin"
                type="time"
                @input="alHora(dia, 'fin', $event.target.value)"
              />
            </label>
          </div>
        </div>
        <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
        <footer class="alta-dialogo-pie">
          <button type="button" @click="cerrarAlta">Cancelar</button>
          <button class="primario" type="submit">Guardar trabajador</button>
        </footer>
      </form>
  </dialog>
  <dialog ref="dialogoHorario" class="alta-dialogo" @close="alCerrarHorario" @click="alFondoHorario">
    <form @submit.prevent="guardarHorario">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>Cambiar horario</h2>
          <p v-if="trabajadorHorario" class="alta-dialogo-persona">{{ trabajadorHorario.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarHorario">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Desde
          <input v-model="desdeHorario" name="desde-horario" type="date" :min="hoyIso()" />
        </label>
        <div class="ancho alta-dias-marcas">
          <label v-for="(letra, dia) in letras" :key="`cambio-${letra}`" class="alta-casilla">
            <input
              type="checkbox"
              :checked="diasHorario[dia]"
              @change="alMarcarHorario(dia, $event)"
            />
            {{ letra }}
          </label>
        </div>
        <div
          v-for="(letra, dia) in letras"
          v-show="diasHorario[dia]"
          :key="`cambio-horas-${letra}`"
          class="ancho alta-dia-horas"
        >
          <span>{{ letra }}</span>
          <label>
            Hora de inicio
            <input
              :value="horasHorario[dia].inicio"
              type="time"
              @input="alHoraHorario(dia, 'inicio', $event.target.value)"
            />
          </label>
          <label>
            Hora de fin
            <input
              :value="horasHorario[dia].fin"
              type="time"
              @input="alHoraHorario(dia, 'fin', $event.target.value)"
            />
          </label>
        </div>
      </div>
      <p v-if="errorHorario" class="error" role="alert">{{ errorHorario }}</p>
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarHorario">Cancelar</button>
        <button class="primario" type="submit">Guardar horario</button>
      </footer>
    </form>
  </dialog>
  <dialog ref="dialogoSap" class="alta-dialogo" @close="alCerrarSap" @click="alFondoSap">
    <form @submit.prevent="guardarSap">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>Número de personal (SAP)</h2>
          <p v-if="trabajadorSap" class="alta-dialogo-persona">{{ trabajadorSap.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarSap">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Número de personal (SAP)
          <input v-model="numeroSapEdit" name="numero-sap-edit" autocomplete="off" />
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
  <dialog ref="dialogoAjustes" class="alta-dialogo" @close="alCerrarAjustes" @click="alFondoAjustes">
    <header class="alta-dialogo-cabecera">
      <div>
        <h2>Ajustes</h2>
        <p v-if="trabajadorAjuste" class="alta-dialogo-persona">{{ trabajadorAjuste.nombre }}</p>
      </div>
      <button type="button" class="dialogo-cerrar" @click="cerrarAjustes">✕</button>
    </header>
    <div class="alta-dialogo-cuerpo">
      <p v-if="!ajustes.length" class="panel-vacio ancho">Sin ajustes registrados.</p>
      <ul v-else class="panel-filas ancho">
        <li v-for="ajuste in ajustes" :key="ajuste.id">
          <span class="persona-datos">
            <strong>{{ fechaVisible(ajuste.fecha) }} · {{ horasConSigno(ajuste.horas) }}</strong>
            <span>{{ ajuste.motivo }}</span>
            <span>{{ ajuste.registra }}</span>
          </span>
          <button type="button" @click="eliminarAjuste(ajuste)">Eliminar</button>
        </li>
      </ul>
    </div>
    <form @submit.prevent="guardarAjuste">
      <div class="alta-dialogo-cuerpo">
        <label>
          Fecha
          <input v-model="fechaAjuste" name="fecha-ajuste" type="date" />
        </label>
        <label>
          Horas
          <input v-model="horasAjuste" name="horas-ajuste" type="number" step="0.01" />
        </label>
        <label class="ancho">
          Motivo
          <input v-model="motivoAjuste" name="motivo-ajuste" />
        </label>
      </div>
      <p v-if="errorAjuste" class="error" role="alert">{{ errorAjuste }}</p>
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarAjustes">Cerrar</button>
        <button class="primario" type="submit">Añadir ajuste</button>
      </footer>
    </form>
  </dialog>
  <p v-if="aviso" class="aviso-ok" role="status">Trabajador creado</p>
</template>
