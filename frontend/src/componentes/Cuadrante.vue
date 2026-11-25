<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import CeldaCuadrante from "./CeldaCuadrante.vue";
import LeyendaTurnos from "./LeyendaTurnos.vue";
import NavegacionPeriodo from "./NavegacionPeriodo.vue";
import { horasPeriodo } from "../costes.js";
import { fechaVisible, lunesDe, rangoSemana, sumarDias, textoCelda } from "../fechas.js";
import { GRUPOS } from "../personas.js";
import { anio, borrarAusenciaMando, borrarTurno, copiarSemana, exportarCuadrante, guardarAusenciasMando, guardarTurno, guardarTurnos, mes, mesMandos, semana, semanaActual, semanaMandos } from "../api/turnos.js";

const emit = defineEmits(["cambiar-horario"]);

const props = defineProps({
  token: { type: String, required: true },
  propia: { type: Boolean, default: false },
  editable: { type: Boolean, default: false },
  mandos: { type: Boolean, default: false },
  departamentoId: { type: String, default: "" },
});

const diasNombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const diasCortos = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const mesesLargos = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];
const ausencias = [
  { codigo: "L", nombre: "Libranza" },
  { codigo: "V", nombre: "Vacaciones" },
  { codigo: "B", nombre: "Baja" },
  { codigo: "F", nombre: "Festivo" },
  { codigo: "P", nombre: "Permiso" },
  { codigo: "SR", nombre: "Sábado recuperado" },
  { codigo: "FR", nombre: "Festivo recuperado" },
  { codigo: "HS", nombre: "Horas sindicales" },
  { codigo: "PEND", nombre: "Pendientes año anterior" },
  { codigo: "ST", nombre: "Sábado trabajado" },
  { codigo: "FT", nombre: "Festivo trabajado" },
];
const ausenciasPropias = [
  { codigo: "V", nombre: "Vacaciones" },
  { codigo: "B", nombre: "Baja" },
  { codigo: "P", nombre: "Permiso" },
  { codigo: "F", nombre: "Festivo" },
  { codigo: "L", nombre: "Libranza" },
];
const familias = {
  L: "libranza",
  D: "domingo",
  V: "vacaciones",
  B: "baja",
  A: "ausente",
  F: "festivo",
  P: "permiso",
  SR: "vacaciones",
  FR: "vacaciones",
  HS: "permiso",
  PEND: "permiso",
  ST: "festivo",
  FT: "festivo",
};
const franjas = [
  { id: "noche", nombre: "Total noche" },
  { id: "manana", nombre: "Total mañana" },
  { id: "tarde", nombre: "Total tarde" },
];
const modo = ref("semana");
const ampliado = ref(false);
const semanaDesde = ref("");
const anioMes = ref(0);
const numeroMes = ref(0);
const anioVista = ref(0);
const cuadrante = ref(null);
const vistaAnio = ref(null);
const tablaAnio = ref(null);
const marcoCuadrante = ref(null);
const periodoAnterior = ref(null);
let solicitudAnterior = 0;
const errorSemana = ref("");
const avisoCopia = ref("");
const celda = ref(null);
const dialogo = ref(null);
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoPausa = ref("");
const turnoAusencia = ref("L");
const conHorario = computed(
  () => turnoModo.value === "ausencia" && (turnoAusencia.value === "ST" || turnoAusencia.value === "FT"),
);
const muestraPausa = computed(() => {
  if (props.propia || props.mandos || !celda.value) {
    return false;
  }
  const minutos = Number(celda.value.pausaMinutos);
  if (!(minutos > 0)) {
    return false;
  }
  return turnoModo.value === "horario" || conHorario.value;
});
const textoPausa = computed(() => {
  const minutos = Number(celda.value?.pausaMinutos) || 0;
  const inicio = horaCorta(turnoPausa.value);
  if (inicio) {
    return `${minutos} min · ${inicio}-${finPausa(inicio, minutos)}`;
  }
  const habitual = horaCorta(celda.value?.pausaHabitual);
  if (habitual) {
    return `habitual ${habitual}-${finPausa(habitual, minutos)}`;
  }
  return `${minutos} min de pausa`;
});
const errorTurno = ref("");
const seccionElegida = ref("");
const copiasMarcadas = ref([false, false, false, false, false, false, false]);
const letrasCopia = ["L", "M", "X", "J", "V", "S", "D"];
const tituloMes = computed(() => `${mesesLargos[numeroMes.value - 1] || ""} ${anioMes.value}`.trim());
const gruposCuadrante = GRUPOS;
function claveTrabajador(trabajador) {
  return trabajador.login || trabajador.id;
}

const muestraEquipo = computed(
  () => props.propia && modo.value === "semana" && cuadrante.value?.desde === semanaActual(),
);

const secciones = computed(() => {
  const fuente = modo.value === "anio" ? vistaAnio.value : cuadrante.value;
  const nombres = new Set();
  for (const trabajador of fuente?.trabajadores || []) {
    if (trabajador.seccion) {
      nombres.add(trabajador.seccion);
    }
  }
  return [...nombres].sort((a, b) => a.localeCompare(b, "es"));
});

const muestraSecciones = computed(() => !props.propia && !props.mandos && secciones.value.length > 0);

const opcionesSeccion = computed(() => {
  const nombres = [...secciones.value];
  if (seccionElegida.value && !nombres.includes(seccionElegida.value)) {
    nombres.push(seccionElegida.value);
    nombres.sort((a, b) => a.localeCompare(b, "es"));
  }
  return nombres;
});

function trabajadoresDe(datos) {
  const lista = datos?.trabajadores || [];
  if (!muestraSecciones.value || !seccionElegida.value) {
    return lista;
  }
  return lista.filter((trabajador) => trabajador.seccion === seccionElegida.value);
}

const trabajadoresCuadrante = computed(() => trabajadoresDe(cuadrante.value));

function filasDe(lista) {
  if (props.propia && !props.mandos && modo.value !== "semana") {
    return lista.map((trabajador) => ({ tipo: "persona", trabajador }));
  }
  const filas = [];
  const vistos = new Set();
  if (props.mandos) {
    const propio = lista.find((trabajador) => esMio(trabajador));
    if (propio) {
      vistos.add(claveTrabajador(propio));
      filas.push({ tipo: "persona", trabajador: propio });
    }
  }
  for (const grupo of gruposCuadrante) {
    const personas = lista.filter(
      (trabajador) => trabajador.grupo === grupo.id && !vistos.has(claveTrabajador(trabajador)),
    );
    if (!personas.length) {
      continue;
    }
    filas.push({ tipo: "grupo", id: grupo.id, titulo: grupo.titulo });
    for (const trabajador of personas) {
      vistos.add(claveTrabajador(trabajador));
      filas.push({ tipo: "persona", trabajador });
    }
  }
  for (const trabajador of lista) {
    if (!vistos.has(claveTrabajador(trabajador))) {
      filas.push({ tipo: "persona", trabajador });
    }
  }
  return filas;
}

const filasCuadrante = computed(() => filasDe(trabajadoresCuadrante.value));
const filasAnio = computed(() => filasDe(trabajadoresDe(vistaAnio.value)));

const mesesAnio = computed(() => {
  const grupos = [];
  let cursor = 0;
  for (const iso of vistaAnio.value?.dias || []) {
    const mes = Number(iso.slice(5, 7));
    const ultimo = grupos[grupos.length - 1];
    if (!ultimo || ultimo.mes !== mes) {
      grupos.push({
        mes,
        dias: 1,
        indice: cursor,
        nombre: mesesLargos[mes - 1],
        corto: mesesLargos[mes - 1].slice(0, 3).toUpperCase(),
      });
    } else {
      ultimo.dias += 1;
    }
    cursor += 1;
  }
  return grupos;
});

async function cargar(desde) {
  errorSemana.value = "";
  avisoCopia.value = "";
  if (dialogo.value?.open) {
    dialogo.value.close();
  }
  try {
    cuadrante.value = props.mandos
      ? await semanaMandos(props.token, desde)
      : await semana(props.token, desde, props.propia, props.departamentoId);
    semanaDesde.value = cuadrante.value.desde;
    await cargarPeriodoAnterior();
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

async function cargarMes(anio, mesNumero) {
  errorSemana.value = "";
  avisoCopia.value = "";
  if (dialogo.value?.open) {
    dialogo.value.close();
  }
  try {
    cuadrante.value = props.mandos
      ? await mesMandos(props.token, anio, mesNumero)
      : await mes(props.token, anio, mesNumero, props.propia, props.departamentoId);
    anioMes.value = anio;
    numeroMes.value = mesNumero;
    await cargarPeriodoAnterior();
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar el mes";
  }
}

function mesPrevio(anio, mesNumero) {
  if (mesNumero <= 1) {
    return { anio: anio - 1, mes: 12 };
  }
  return { anio, mes: mesNumero - 1 };
}

async function cargarPeriodoAnterior() {
  const solicitud = ++solicitudAnterior;
  periodoAnterior.value = null;
  if (props.propia || props.mandos) {
    return;
  }
  try {
    let datos;
    if (modo.value === "mes") {
      const previo = mesPrevio(anioMes.value, numeroMes.value);
      datos = await mes(props.token, previo.anio, previo.mes, false, props.departamentoId);
    } else {
      datos = await semana(props.token, sumarDias(semanaDesde.value, -7), false, props.departamentoId);
    }
    if (solicitud !== solicitudAnterior) {
      return;
    }
    periodoAnterior.value = datos;
  } catch {
    if (solicitud === solicitudAnterior) {
      periodoAnterior.value = null;
    }
  }
}

function partes(iso) {
  return iso.split("-").map(Number);
}

function hoyMadrid() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function diaSemana(iso) {
  const [anio, mesNumero, dia] = partes(iso);
  return new Date(anio, mesNumero - 1, dia).getDay();
}

function turnoDeValor(valor) {
  if (!valor) {
    return null;
  }
  const espacio = valor.indexOf(" ");
  if (espacio > 0) {
    const [inicio, fin] = valor.slice(espacio + 1).split("-");
    return { ausencia: valor.slice(0, espacio), hora_inicio: inicio, hora_fin: fin };
  }
  if (valor.includes(":")) {
    const [inicio, fin] = valor.split("-");
    return { hora_inicio: inicio, hora_fin: fin };
  }
  return { ausencia: valor };
}

function prepararAnio(datos) {
  const festivos = datos.festivos || {};
  for (const trabajador of datos.trabajadores || []) {
    trabajador.dias = (datos.dias || []).map((fecha, indice) => {
      const dia = {
        fecha,
        turno: turnoDeValor(trabajador.dias?.[indice] || ""),
        festivo: Boolean(festivos[fecha]),
      };
      if (festivos[fecha]) {
        dia.nombre = festivos[fecha];
      }
      return dia;
    });
  }
  return datos;
}

function indiceAnioVisible() {
  const dias = vistaAnio.value?.dias || [];
  const hoy = hoyMadrid();
  if (vistaAnio.value?.anio === Number(hoy.slice(0, 4))) {
    const indice = dias.indexOf(hoy);
    return indice >= 0 ? indice : 0;
  }
  return 0;
}

function irADia(indice) {
  const marco = marcoCuadrante.value;
  const tabla = tablaAnio.value;
  if (!marco || !tabla) {
    return;
  }
  const celda = tabla.querySelector(`thead tr.anio-dias th[data-dia="${indice}"]`);
  if (!celda) {
    return;
  }
  const nombre = tabla.querySelector("thead th");
  const ancho = nombre?.getBoundingClientRect().width || 0;
  const destino = celda.getBoundingClientRect().left - marco.getBoundingClientRect().left + marco.scrollLeft - ancho;
  marco.scrollLeft = Math.max(0, destino);
}

async function cargarAnio(anioNumero) {
  errorSemana.value = "";
  avisoCopia.value = "";
  if (dialogo.value?.open) {
    dialogo.value.close();
  }
  try {
    const datos = prepararAnio(await anio(props.token, anioNumero, props.departamentoId));
    vistaAnio.value = datos;
    anioVista.value = datos.anio;
    await nextTick();
    requestAnimationFrame(() => irADia(indiceAnioVisible()));
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar el año";
  }
}

function moverAnio(delta) {
  cargarAnio(anioVista.value + delta);
}

function irAHoy() {
  irADia(indiceAnioVisible());
}

function cambiarModo(nuevo) {
  if (nuevo === modo.value) {
    return;
  }
  const anterior = modo.value;
  modo.value = nuevo;
  if (nuevo === "anio") {
    const anioVisible = anterior === "mes"
      ? anioMes.value
      : partes(semanaDesde.value || lunesDe(new Date()))[0];
    cargarAnio(anioVisible);
    return;
  }
  if (anterior === "anio") {
    if (nuevo === "mes") {
      if (anioMes.value) {
        cargarMes(anioMes.value, numeroMes.value);
        return;
      }
      const [anioNumero, mesNumero] = partes(semanaDesde.value || lunesDe(new Date()));
      cargarMes(anioNumero, mesNumero);
      return;
    }
    cargar(semanaDesde.value || lunesDe(new Date()));
    return;
  }
  if (nuevo === "mes") {
    const [anio, mesNumero] = partes(semanaDesde.value || lunesDe(new Date()));
    cargarMes(anio, mesNumero);
    return;
  }
  const referencia = semanaDesde.value;
  if (referencia && partes(referencia)[0] === anioMes.value && partes(referencia)[1] === numeroMes.value) {
    cargar(referencia);
    return;
  }
  cargar(lunesDe(new Date(anioMes.value, numeroMes.value - 1, 1)));
}

function moverMes(delta) {
  const fecha = new Date(anioMes.value, numeroMes.value - 1 + delta, 1);
  cargarMes(fecha.getFullYear(), fecha.getMonth() + 1);
}

function esFin(indice) {
  return indice >= 5;
}

function esFinDia(dia, indice) {
  if (modo.value === "semana") {
    return esFin(indice);
  }
  const semanaDia = diaSemana(dia);
  return semanaDia === 0 || semanaDia === 6;
}

function nombreFestivo(indice) {
  for (const trabajador of cuadrante.value?.trabajadores || []) {
    const dia = trabajador.dias?.[indice];
    if (dia?.festivo) {
      return dia.nombre || "Festivo";
    }
  }
  return "";
}

function totalFranja(franja, indice) {
  return trabajadoresCuadrante.value.filter(
    (trabajador) => familia(trabajador.dias[indice]?.turno) === franja,
  ).length;
}

function horasNocturnas(indice) {
  const suma = trabajadoresCuadrante.value.reduce(
    (total, trabajador) => total + (Number(trabajador.dias[indice]?.turno?.horas_nocturnas) || 0),
    0,
  );
  return Number(suma.toFixed(2)).toLocaleString("es-ES");
}

function muestraAjuste(dia) {
  return !props.propia && !props.mandos && Array.isArray(dia?.ajustes) && dia.ajustes.length > 0;
}

function textoHorasAjuste(valor) {
  const cantidad = Number(Number(valor).toFixed(2));
  const signo = cantidad < 0 ? "-" : "+";
  const absoluto = Math.abs(cantidad).toLocaleString("es-ES", { maximumFractionDigits: 2 });
  return `${signo}${absoluto} h`;
}

function textoAjustes(dia) {
  if (!muestraAjuste(dia)) {
    return undefined;
  }
  const lineas = dia.ajustes.map((ajuste) => {
    const horas = textoHorasAjuste(ajuste.horas);
    const motivo = String(ajuste.motivo || "").trim();
    return motivo ? `Ajuste: ${horas} · ${motivo}` : `Ajuste: ${horas}`;
  });
  if (dia.ajustes.length > 1) {
    const total = dia.ajustes.reduce((suma, ajuste) => suma + Number(ajuste.horas), 0);
    lineas.push(`Total: ${textoHorasAjuste(total)}`);
  }
  return lineas.join("\n");
}

function horaCorta(valor) {
  const texto = String(valor || "").trim();
  return texto.length >= 5 ? texto.slice(0, 5) : "";
}

function finPausa(inicio, minutos) {
  const [hora, minuto] = inicio.split(":").map(Number);
  const total = (hora * 60 + minuto + minutos) % (24 * 60);
  const horas = String(Math.floor(total / 60)).padStart(2, "0");
  const resto = String(total % 60).padStart(2, "0");
  return `${horas}:${resto}`;
}

function pausaCabe(turno, inicio, minutos) {
  if (!turno?.hora_inicio || !turno?.hora_fin || !inicio || !(minutos > 0)) {
    return false;
  }
  if (turno.ausencia && turno.ausencia !== "ST" && turno.ausencia !== "FT") {
    return false;
  }
  const enMinutos = (hora) => {
    const [horas, minuto] = horaCorta(hora).split(":").map(Number);
    return horas * 60 + minuto;
  };
  const desde = enMinutos(turno.hora_inicio);
  let hasta = enMinutos(turno.hora_fin);
  const cruza = hasta <= desde;
  if (cruza) {
    hasta += 24 * 60;
  }
  let marca = enMinutos(inicio);
  if (cruza && marca < desde) {
    marca += 24 * 60;
  }
  return desde <= marca && marca + minutos <= hasta;
}

function pausaEfectiva(trabajador, turno) {
  const minutos = Number(trabajador?.pausa_minutos);
  if (!(minutos > 0) || !turno) {
    return null;
  }
  const puntual = horaCorta(turno.pausa_inicio);
  if (puntual) {
    return { inicio: puntual, fin: finPausa(puntual, minutos), habitual: false };
  }
  const habitual = horaCorta(trabajador.pausa_habitual);
  if (habitual && pausaCabe(turno, habitual, minutos)) {
    return { inicio: habitual, fin: finPausa(habitual, minutos), habitual: true };
  }
  return null;
}

function tituloCelda(trabajador, dia) {
  const lineas = [];
  const ajustes = textoAjustes(dia);
  if (ajustes) {
    lineas.push(ajustes);
  }
  const pausa = pausaEfectiva(trabajador, dia.turno);
  if (pausa) {
    const sufijo = pausa.habitual ? " (habitual)" : "";
    lineas.push(`Pausa: ${pausa.inicio}-${pausa.fin}${sufijo}`);
  }
  return lineas.length ? lineas.join("\n") : undefined;
}

function horaVisible(hora) {
  const texto = textoCelda({ hora_inicio: hora, hora_fin: "00:00" });
  return texto.slice(0, texto.lastIndexOf("-"));
}

function pausaEnMadrugada(turno, inicio) {
  const desde = horaCorta(turno?.hora_inicio).split(":").map(Number);
  const hasta = horaCorta(turno?.hora_fin).split(":").map(Number);
  const inicioTurno = desde[0] * 60 + desde[1];
  const finTurno = hasta[0] * 60 + hasta[1];
  if (finTurno > inicioTurno) {
    return false;
  }
  const [hora, minuto] = horaCorta(inicio).split(":").map(Number);
  return hora * 60 + minuto < inicioTurno;
}

function textoPartido(trabajador, dia) {
  if (modo.value !== "semana" || props.propia || props.mandos || dia.turno?.ausencia) {
    return "";
  }
  const pausa = pausaEfectiva(trabajador, dia.turno);
  if (!pausa || pausaEnMadrugada(dia.turno, pausa.inicio)) {
    return "";
  }
  const inicio = horaVisible(dia.turno.hora_inicio);
  const fin = horaVisible(dia.turno.hora_fin);
  return `${inicio}-${horaVisible(pausa.inicio)} ${horaVisible(pausa.fin)}-${fin}`;
}

function textoVisible(trabajador, dia) {
  return textoPartido(trabajador, dia) || textoCelda(dia.turno);
}

function horasVisibles(valor) {
  return `${Number(valor.toFixed(2)).toLocaleString("es-ES")} h`;
}

function totalesHoras(lista) {
  const stef = lista
    .filter((trabajador) => trabajador.grupo === "STEF")
    .reduce((total, trabajador) => total + horasPeriodo(trabajador, "horas_planificadas"), 0);
  const ett = lista
    .filter((trabajador) => trabajador.grupo === "ETT")
    .reduce((total, trabajador) => total + horasPeriodo(trabajador, "horas_planificadas"), 0);
  const nocturnas = lista.reduce(
    (total, trabajador) => total + horasPeriodo(trabajador, "horas_nocturnas"),
    0,
  );
  return { stef, ett, noche: nocturnas, total: stef + ett };
}

function textoDelta(valor) {
  const cantidad = Number(valor.toFixed(2));
  if (cantidad === 0) {
    return "(±0 h)";
  }
  const signo = cantidad > 0 ? "+" : "-";
  const absoluto = Math.abs(cantidad).toLocaleString("es-ES", { maximumFractionDigits: 2 });
  return `(${signo}${absoluto} h)`;
}

const tituloComparacion = computed(() => {
  if (modo.value === "mes") {
    const previo = mesPrevio(anioMes.value, numeroMes.value);
    return `Frente a ${mesesLargos[previo.mes - 1].toLowerCase()} de ${previo.anio}`;
  }
  if (!semanaDesde.value) {
    return "";
  }
  const desde = sumarDias(semanaDesde.value, -7);
  const hasta = sumarDias(desde, 6);
  return `Frente a la semana del ${fechaVisible(desde).slice(0, 5)} al ${fechaVisible(hasta).slice(0, 5)}`;
});

const resumenHoras = computed(() => {
  const actual = totalesHoras(trabajadoresCuadrante.value);
  const previo = periodoAnterior.value ? totalesHoras(trabajadoresDe(periodoAnterior.value)) : null;
  return [
    { id: "stef", nombre: "Horas STEF", horas: actual.stef },
    { id: "ett", nombre: "Horas ETT", horas: actual.ett },
    { id: "noche", nombre: "Horas nocturnas", horas: actual.noche },
    { id: "total", nombre: "Total horas", horas: actual.total },
  ].map((tarjeta) => ({
    id: tarjeta.id,
    nombre: tarjeta.nombre,
    valor: horasVisibles(tarjeta.horas),
    delta: previo ? textoDelta(tarjeta.horas - previo[tarjeta.id]) : null,
  }));
});

function idDeSesion() {
  try {
    const parte = props.token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = JSON.parse(atob(parte + "=".repeat((4 - (parte.length % 4)) % 4)));
    return String(json.sub || "");
  } catch {
    return "";
  }
}

function esMio(trabajador) {
  return trabajador.id === idDeSesion();
}

function familia(turno) {
  if (!turno) {
    return "";
  }
  if (turno.ausencia) {
    return familias[turno.ausencia] || "";
  }
  const [hora, minuto] = (turno.hora_inicio || "00:00").split(":").map(Number);
  const inicio = hora * 60 + minuto;
  if (inicio >= 22 * 60 || inicio < 6 * 60) {
    return "noche";
  }
  if (inicio < 14 * 60) {
    return "manana";
  }
  return "tarde";
}

async function abrirCelda(trabajador, dia) {
  if (!props.editable && !props.mandos) {
    return;
  }
  const turno = dia.turno;
  celda.value = {
    login: trabajador.login,
    id: trabajador.id,
    nombre: trabajador.nombre,
    fecha: dia.fecha,
    origen: dia.origen || "",
    pausaMinutos: Number(trabajador.pausa_minutos) || 0,
    pausaHabitual: horaCorta(trabajador.pausa_habitual),
  };
  turnoPausa.value = horaCorta(turno?.pausa_inicio);
  errorTurno.value = "";
  copiasMarcadas.value = marcasIniciales(dia.fecha);
  if (turno && turno.ausencia) {
    turnoModo.value = "ausencia";
    const lista = props.mandos ? ausenciasPropias : ausencias;
    const permitida = lista.some((item) => item.codigo === turno.ausencia);
    turnoAusencia.value = permitida ? turno.ausencia : "L";
    if (turno.ausencia === "ST" || turno.ausencia === "FT") {
      turnoInicio.value = turno.hora_inicio || "";
      turnoFin.value = turno.hora_fin || "";
    } else {
      turnoInicio.value = "";
      turnoFin.value = "";
    }
  } else {
    turnoModo.value = "horario";
    turnoAusencia.value = "L";
    turnoInicio.value = turno?.hora_inicio || "";
    turnoFin.value = turno?.hora_fin || "";
  }
  await nextTick();
  dialogo.value?.showModal();
  dialogo.value?.querySelector("select")?.focus();
}

function indiceSemana(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const ordinal = new Date(anio, mes - 1, dia).getDay();
  return ordinal === 0 ? 6 : ordinal - 1;
}

function marcasIniciales(fecha) {
  const marcas = [false, false, false, false, false, false, false];
  marcas[indiceSemana(fecha)] = true;
  return marcas;
}

const diasCopia = computed(() => {
  if (!celda.value?.fecha) {
    return [];
  }
  const [anio, mes, dia] = celda.value.fecha.split("-").map(Number);
  const lunes = lunesDe(new Date(anio, mes - 1, dia));
  const trabajador = (cuadrante.value?.trabajadores || []).find((item) =>
    celda.value.login ? item.login === celda.value.login : item.id === celda.value.id,
  );
  return letrasCopia.map((letra, indice) => {
    const fecha = sumarDias(lunes, indice);
    const dato = trabajador?.dias?.find((item) => item.fecha === fecha);
    return {
      letra,
      fecha,
      indice,
      marcado: copiasMarcadas.value[indice],
      propio: fecha === celda.value.fecha,
      guardado: dato?.origen === "guardado",
    };
  });
});

const avisaSustitucion = computed(() => diasCopia.value.some((dia) => dia.guardado));

function alternarCopia(indice, marcado) {
  if (diasCopia.value[indice]?.propio) {
    return;
  }
  const marcas = [...copiasMarcadas.value];
  marcas[indice] = marcado;
  copiasMarcadas.value = marcas;
}

function marcarLaborables() {
  const propio = indiceSemana(celda.value.fecha);
  copiasMarcadas.value = letrasCopia.map((_, indice) => indice < 5 || indice === propio);
}

function marcarTodos() {
  copiasMarcadas.value = letrasCopia.map(() => true);
}

function cerrarCelda() {
  dialogo.value?.close();
}

function alCerrarCelda() {
  celda.value = null;
  errorTurno.value = "";
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    cerrarCelda();
  }
}

function tieneTurnosGuardados() {
  return (cuadrante.value?.trabajadores || []).some((trabajador) =>
    (trabajador.dias || []).some((dia) => dia.origen === "guardado"),
  );
}

function diasCopiados(resultado) {
  if (!resultado || typeof resultado !== "object") {
    return null;
  }
  const valor = resultado.dias_copiados ?? resultado.copiados;
  if (typeof valor === "number" && Number.isFinite(valor)) {
    return valor;
  }
  return null;
}

async function copiar() {
  errorSemana.value = "";
  avisoCopia.value = "";
  if (
    tieneTurnosGuardados()
    && !window.confirm("Esta semana ya tiene turnos. Copiar la anterior los sustituirá. ¿Continuar?")
  ) {
    return;
  }
  try {
    const resultado = await copiarSemana(props.token, semanaDesde.value, props.departamentoId);
    await cargar(semanaDesde.value);
    const copiados = diasCopiados(resultado);
    if (copiados !== null) {
      const dias = copiados === 1 ? "día" : "días";
      avisoCopia.value = `Se han copiado ${copiados} ${dias}.`;
    }
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo copiar la semana";
  }
}

async function guardar() {
  if (!celda.value) {
    return;
  }
  errorTurno.value = "";
  const fechasMarcadas = diasCopia.value.filter((dia) => dia.marcado).map((dia) => dia.fecha);
  if (props.mandos) {
    try {
      const datos = { fechas: fechasMarcadas };
      if (turnoModo.value === "ausencia") {
        datos.ausencia = turnoAusencia.value;
      } else {
        datos.hora_inicio = turnoInicio.value;
        datos.hora_fin = turnoFin.value;
      }
      await guardarAusenciasMando(props.token, datos);
      cerrarCelda();
      await refrescar();
    } catch (causa) {
      errorTurno.value = causa instanceof Error ? causa.message : "No se pudo guardar el turno";
    }
    return;
  }
  const cuerpo = {
    login: celda.value.login,
    fecha: celda.value.fecha,
  };
  if (turnoModo.value === "ausencia") {
    cuerpo.ausencia = turnoAusencia.value;
    if (conHorario.value) {
      cuerpo.hora_inicio = turnoInicio.value;
      cuerpo.hora_fin = turnoFin.value;
    }
  } else {
    cuerpo.hora_inicio = turnoInicio.value;
    cuerpo.hora_fin = turnoFin.value;
  }
  const pausaEscrita = horaCorta(turnoPausa.value);
  if (muestraPausa.value && pausaEscrita) {
    cuerpo.pausa_inicio = pausaEscrita;
  }
  try {
    const fechas = fechasMarcadas;
    if (fechas.length > 1) {
      const datos = {
        login: celda.value.login,
        fechas,
      };
      if (turnoModo.value === "ausencia") {
        datos.ausencia = turnoAusencia.value;
        if (conHorario.value) {
          datos.hora_inicio = turnoInicio.value;
          datos.hora_fin = turnoFin.value;
        }
      } else {
        datos.hora_inicio = turnoInicio.value;
        datos.hora_fin = turnoFin.value;
      }
      if (muestraPausa.value && pausaEscrita) {
        datos.pausa_inicio = pausaEscrita;
      }
      await guardarTurnos(props.token, datos);
    } else {
      await guardarTurno(props.token, cuerpo);
    }
    cerrarCelda();
    await refrescar();
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo guardar el turno";
  }
}

async function quitar() {
  if (!celda.value) {
    return;
  }
  errorTurno.value = "";
  try {
    if (props.mandos) {
      await borrarAusenciaMando(props.token, celda.value.fecha);
    } else {
      await borrarTurno(props.token, { login: celda.value.login, fecha: celda.value.fecha });
    }
    cerrarCelda();
    await refrescar();
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo quitar la excepción";
  }
}

async function refrescar() {
  if (modo.value === "mes") {
    await cargarMes(anioMes.value, numeroMes.value);
    return;
  }
  await cargar(semanaDesde.value || lunesDe(new Date()));
}

defineExpose({ recargar: refrescar });

const raiz = ref(null);
const cuadro = ref(null);
const lupa = ref(null);
const cuadroAbierto = computed(() => ampliado.value && !props.propia && !props.mandos);

function scrollDetras(oculto) {
  const valor = oculto ? "hidden" : "";
  document.documentElement.style.overflow = valor;
  document.body.style.overflow = valor;
}

function enlazarCuadro(elemento) {
  cuadro.value = elemento;
  raiz.value = elemento;
}

function alAntesDeImprimir() {
  document.documentElement.style.overflow = "";
  document.body.style.overflow = "";
  const visible = raiz.value instanceof HTMLElement && raiz.value.offsetParent !== null;
  document.body.classList.toggle("imprimir-cuadrante", visible);
}

function alDespuesDeImprimir() {
  document.body.classList.remove("imprimir-cuadrante");
  scrollDetras(cuadroAbierto.value);
}

function cerrarAmpliar() {
  if (!cuadroAbierto.value) {
    return;
  }
  ampliado.value = false;
  nextTick(() => lupa.value?.focus());
}

function alTecla(evento) {
  if (!cuadroAbierto.value || dialogo.value?.open) {
    return;
  }
  if (evento.key === "Escape") {
    evento.preventDefault();
    cerrarAmpliar();
    return;
  }
  if (evento.key !== "Tab" || !cuadro.value) {
    return;
  }
  const lista = [...cuadro.value.querySelectorAll("button, a[href], input, select, textarea")].filter(
    (elemento) => !elemento.disabled && elemento.tabIndex !== -1,
  );
  if (!lista.length) {
    return;
  }
  const primero = lista[0];
  const ultimo = lista[lista.length - 1];
  const activo = document.activeElement;
  if (!cuadro.value.contains(activo) || (evento.shiftKey && activo === primero) || activo === cuadro.value) {
    evento.preventDefault();
    (evento.shiftKey ? ultimo : primero).focus();
  } else if (!evento.shiftKey && activo === ultimo) {
    evento.preventDefault();
    primero.focus();
  }
}

function imprimir() {
  window.print();
}

async function exportar() {
  errorSemana.value = "";
  const parametros =
    modo.value === "mes"
      ? { anio: String(anioMes.value), mes: String(numeroMes.value) }
      : { desde: semanaDesde.value };
  if (props.departamentoId && !props.propia && !props.mandos) {
    parametros.departamento_id = props.departamentoId;
  }
  try {
    await exportarCuadrante(props.token, parametros);
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo exportar el cuadrante";
  }
}

watch(cuadroAbierto, (activo) => {
  scrollDetras(activo);
  if (activo) {
    nextTick(() => cuadro.value?.focus());
  }
});

onMounted(() => {
  window.addEventListener("beforeprint", alAntesDeImprimir);
  window.addEventListener("afterprint", alDespuesDeImprimir);
  window.addEventListener("keydown", alTecla);
});

onUnmounted(() => {
  window.removeEventListener("beforeprint", alAntesDeImprimir);
  window.removeEventListener("afterprint", alDespuesDeImprimir);
  window.removeEventListener("keydown", alTecla);
  ampliado.value = false;
  scrollDetras(false);
  alDespuesDeImprimir();
});

cargar(lunesDe(new Date()));
</script>

<template>
  <Teleport to="body" :disabled="!ampliado">
  <section
    v-if="cuadrante"
    :ref="enlazarCuadro"
    class="semana"
    :class="{
      lectura: !editable && !mandos,
      'pagina-horizontal': modo === 'mes',
      'cuadrante-modal': cuadroAbierto,
    }"
    :role="cuadroAbierto ? 'dialog' : undefined"
    :aria-modal="cuadroAbierto ? 'true' : undefined"
    aria-label="Cuadrante"
    :tabindex="cuadroAbierto ? -1 : undefined"
  >
    <div class="cuadrante-panel">
    <button
      v-if="cuadroAbierto"
      type="button"
      class="cuadrante-cerrar"
      aria-label="Cerrar"
      @click="cerrarAmpliar"
    >
      ×
    </button>
    <div class="semana-nav">
      <div class="vistas modo-vista">
        <button type="button" :class="{ activo: modo === 'semana' }" @click="cambiarModo('semana')">
          Semanal
        </button>
        <button type="button" :class="{ activo: modo === 'mes' }" @click="cambiarModo('mes')">
          Mensual
        </button>
        <button
          v-if="!propia && !mandos"
          type="button"
          :class="{ activo: modo === 'anio' }"
          @click="cambiarModo('anio')"
        >
          Anual
        </button>
      </div>
      <template v-if="modo === 'semana'">
        <NavegacionPeriodo
          anterior="Semana anterior"
          siguiente="Semana siguiente"
          @anterior="cargar(sumarDias(semanaDesde, -7))"
          @siguiente="cargar(sumarDias(semanaDesde, 7))"
        >
          {{ rangoSemana(cuadrante.desde, cuadrante.dias[6]) }}
        </NavegacionPeriodo>
        <button v-if="editable" type="button" @click="copiar">Copiar semana anterior</button>
      </template>
      <template v-else-if="modo === 'mes'">
        <NavegacionPeriodo
          anterior="Mes anterior"
          siguiente="Mes siguiente"
          @anterior="moverMes(-1)"
          @siguiente="moverMes(1)"
        >
          {{ tituloMes }}
        </NavegacionPeriodo>
      </template>
      <template v-else>
        <NavegacionPeriodo
          anterior="Año anterior"
          siguiente="Año siguiente"
          @anterior="moverAnio(-1)"
          @siguiente="moverAnio(1)"
        >
          {{ anioVista }}
        </NavegacionPeriodo>
        <button type="button" @click="irAHoy">Hoy</button>
      </template>
      <button v-if="mandos" type="button" @click="emit('cambiar-horario')">Cambiar mi horario</button>
      <button v-if="modo !== 'anio'" type="button" class="cuadrante-imprimir" @click="imprimir">Imprimir</button>
      <button v-if="editable && modo !== 'anio'" type="button" class="cuadrante-exportar" @click="exportar">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="4" y="3" width="16" height="18" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8" />
          <path d="M4 8.5 H20 M9.5 8.5 V21 M14.5 8.5 V21 M4 13.5 H20 M4 17.5 H20" fill="none" stroke="currentColor" stroke-width="1.4" />
        </svg>
        Exportar a Excel
      </button>
    </div>
    <p v-if="!editable && !mandos" class="aviso-lectura">Solo lectura</p>
    <p v-if="muestraEquipo" class="equipo-semana">Equipo de esta semana</p>
    <p v-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
    <p v-if="avisoCopia" class="aviso-ok" role="status">{{ avisoCopia }}</p>
    <div v-if="!propia && !mandos" class="cuadrante-seccion">
      <template v-if="muestraSecciones">
        <button type="button" :class="{ activo: seccionElegida === '' }" @click="seccionElegida = ''">
          Todas
        </button>
        <button
          v-for="nombre in opcionesSeccion"
          :key="nombre"
          type="button"
          :class="{ activo: seccionElegida === nombre }"
          @click="seccionElegida = nombre"
        >
          {{ nombre }}
        </button>
      </template>
      <button
        v-if="!propia && !mandos"
        ref="lupa"
        type="button"
        class="boton-icono"
        :title="cuadroAbierto ? 'Reducir' : 'Ampliar'"
        :aria-label="cuadroAbierto ? 'Reducir' : 'Ampliar'"
        @click="cuadroAbierto ? cerrarAmpliar() : (ampliado = true)"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="10" cy="10" r="6.25" fill="none" stroke="currentColor" stroke-width="2" />
          <path d="M14.8 14.8 L20 20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          <path
            :d="cuadroAbierto ? 'M7.5 10 H12.5' : 'M10 7.5 V12.5 M7.5 10 H12.5'"
            fill="none"
            stroke="currentColor"
            stroke-width="1.8"
            stroke-linecap="round"
          />
        </svg>
      </button>
    </div>
    <div v-if="!propia && !mandos && modo !== 'anio'" class="cuadrante-horas">
      <article v-for="tarjeta in resumenHoras" :key="tarjeta.id" :class="tarjeta.id">
        <p class="lb">{{ tarjeta.nombre }}</p>
        <p class="vl">
          {{ tarjeta.valor }}<span v-if="tarjeta.delta" class="delta" :title="tituloComparacion">{{ ` ${tarjeta.delta}` }}</span>
        </p>
      </article>
    </div>
    <div v-if="modo === 'anio' && vistaAnio" class="anio-chips">
      <button
        v-for="mes in mesesAnio"
        :key="mes.mes"
        type="button"
        class="anio-chip"
        @click="irADia(mes.indice)"
      >
        {{ mes.corto }}
      </button>
    </div>
    <div ref="marcoCuadrante" class="cuadrante-scroll" :class="{ mensual: modo === 'mes' || modo === 'anio', anual: modo === 'anio' }">
    <table
      v-if="modo === 'anio' && vistaAnio"
      ref="tablaAnio"
      class="cuadrante mensual anual"
    >
      <thead>
        <tr class="anio-meses">
          <th rowspan="2">Trabajador</th>
          <th v-for="mes in mesesAnio" :key="mes.mes" :colspan="mes.dias" :class="{ 'mes-inicio': mes.indice > 0 }">
            <button type="button" class="anio-mes" @click="irADia(mes.indice)">{{ mes.nombre }}</button>
          </th>
        </tr>
        <tr class="anio-dias">
          <th
            v-for="(dia, indice) in vistaAnio.dias"
            :key="dia"
            :data-dia="indice"
            :class="{
              fin: esFinDia(dia, indice),
              'col-festivo': vistaAnio.festivos[dia],
              'mes-inicio': indice > 0 && dia.endsWith('-01'),
            }"
            :title="vistaAnio.festivos[dia] || undefined"
          >
            <span class="dia-nombre">{{ diasCortos[diaSemana(dia)] }}</span>
            <span class="dia-numero">{{ Number(dia.slice(8)) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="fila in filasAnio" :key="fila.tipo === 'grupo' ? fila.id : claveTrabajador(fila.trabajador)">
          <tr v-if="fila.tipo === 'grupo'" class="grupo-fila">
            <th class="grupo-anio-nombre">{{ fila.titulo }}</th>
            <td class="grupo-anio-resto" :colspan="vistaAnio.dias.length"></td>
          </tr>
          <tr v-else>
            <th>{{ fila.trabajador.nombre }}</th>
            <td
              v-for="(dia, indice) in fila.trabajador.dias"
              :key="dia.fecha"
              :class="[
                esFinDia(dia.fecha, indice) ? 'fin' : '',
                familia(dia.turno) ? `turno-${familia(dia.turno)}` : '',
                indice > 0 && dia.fecha.endsWith('-01') ? 'mes-inicio' : '',
              ]"
            >
              <CeldaCuadrante
                :lectura="!mandos"
                :titulo="tituloCelda(fila.trabajador, dia)"
                :ajuste="muestraAjuste(dia)"
                :partido="Boolean(textoPartido(fila.trabajador, dia))"
                :texto="textoVisible(fila.trabajador, dia)"
              />
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <table v-else-if="modo !== 'anio'" class="cuadrante" :class="{ mensual: modo === 'mes' }">
      <thead>
        <tr>
          <th>Trabajador</th>
          <th
            v-for="(dia, indice) in cuadrante.dias"
            :key="dia"
            :class="{ fin: esFinDia(dia, indice), 'col-festivo': nombreFestivo(indice) }"
            :title="nombreFestivo(indice) || undefined"
          >
            <span class="dia-nombre">{{ modo === "mes" ? diasCortos[diaSemana(dia)] : diasNombre[indice] }}</span>
            <span class="dia-numero">{{ modo === "mes" ? Number(dia.slice(8)) : fechaVisible(dia).slice(0, 5) }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="fila in filasCuadrante" :key="fila.tipo === 'grupo' ? fila.id : claveTrabajador(fila.trabajador)">
          <tr v-if="fila.tipo === 'grupo'" class="grupo-fila">
            <th :colspan="cuadrante.dias.length + 1">{{ fila.titulo }}</th>
          </tr>
          <tr v-else>
            <th>{{ fila.trabajador.nombre }}</th>
            <td
              v-for="(dia, indice) in fila.trabajador.dias"
              :key="dia.fecha"
              :class="[esFinDia(dia.fecha, indice) ? 'fin' : '', familia(dia.turno) ? `turno-${familia(dia.turno)}` : '']"
            >
              <CeldaCuadrante
                :pulsable="editable || (mandos && esMio(fila.trabajador))"
                :lectura="!mandos"
                :titulo="tituloCelda(fila.trabajador, dia)"
                :ajuste="muestraAjuste(dia)"
                :partido="Boolean(textoPartido(fila.trabajador, dia))"
                :texto="textoVisible(fila.trabajador, dia)"
                @abrir="abrirCelda(fila.trabajador, dia)"
              />
            </td>
          </tr>
        </template>
      </tbody>
      <tfoot v-if="!propia && !mandos">
        <tr v-for="franja in franjas" :key="franja.id">
          <td>{{ franja.nombre }}</td>
          <td v-for="(dia, indice) in cuadrante.dias" :key="dia">{{ totalFranja(franja.id, indice) }}</td>
        </tr>
        <tr>
          <td>Horas nocturnas</td>
          <td v-for="(dia, indice) in cuadrante.dias" :key="`noche-${dia}`">{{ horasNocturnas(indice) }}</td>
        </tr>
      </tfoot>
    </table>
    </div>
    <LeyendaTurnos />
    </div>
  </section>
  </Teleport>
  <p v-if="!cuadrante && errorSemana" class="error" role="alert">{{ errorSemana }}</p>
  <dialog ref="dialogo" class="editor-dia" @close="alCerrarCelda" @click="alFondo">
    <form v-if="celda" @submit.prevent="guardar">
      <header class="editor-dia-cabecera">
        <h2>Editar día</h2>
        <p class="editor-dia-quien">
          {{ celda.nombre }}<br />
          {{ fechaVisible(celda.fecha) }}
        </p>
      </header>
      <div class="editor-dia-cuerpo">
        <label class="ancho">
          Tipo
          <select v-model="turnoModo">
            <option value="horario">Horario</option>
            <option value="ausencia">Ausencia</option>
          </select>
        </label>
        <template v-if="turnoModo === 'ausencia'">
          <label class="ancho">
            Ausencia
            <select v-model="turnoAusencia">
              <option v-for="item in mandos ? ausenciasPropias : ausencias" :key="item.codigo" :value="item.codigo">
                {{ item.nombre }}
              </option>
            </select>
          </label>
        </template>
        <template v-if="turnoModo === 'horario' || conHorario">
          <label>
            Hora de inicio
            <input v-model="turnoInicio" type="time" required />
          </label>
          <label>
            Hora de fin
            <input v-model="turnoFin" type="time" required />
          </label>
        </template>
        <label v-if="muestraPausa" class="ancho pausa-inicio">
          Pausa (inicio)
          <span class="pausa-inicio-fila">
            <input v-model="turnoPausa" type="time" :placeholder="celda.pausaHabitual || undefined" />
            <span class="pausa-inicio-nota">{{ textoPausa }}</span>
          </span>
        </label>
        <div class="ancho copiar-dias">
          <p class="copiar-dias-titulo">Copiar también a:</p>
          <div class="copiar-dias-marcas">
            <label v-for="dia in diasCopia" :key="dia.fecha" class="copiar-dia">
              <input
                type="checkbox"
                :checked="dia.marcado"
                :disabled="dia.propio"
                @change="alternarCopia(dia.indice, $event.target.checked)"
              />
              <span>{{ dia.letra }}</span>
              <span v-if="dia.guardado" class="copiar-dia-punto" aria-hidden="true"></span>
            </label>
          </div>
          <p v-if="avisaSustitucion" class="copiar-dias-aviso">ya tiene turno, se sustituirá</p>
          <div class="copiar-dias-atajos">
            <button type="button" class="copiar-dias-atajo" @click="marcarLaborables">Lunes a viernes</button>
            <button type="button" class="copiar-dias-atajo" @click="marcarTodos">Todos</button>
          </div>
        </div>
      </div>
      <p v-if="errorTurno" class="error" role="alert">{{ errorTurno }}</p>
      <footer class="editor-dia-pie">
        <button v-if="celda.origen === 'guardado'" type="button" @click="quitar">
          {{ mandos ? "Quitar" : "Quitar excepción y volver al horario habitual" }}
        </button>
        <span class="editor-dia-acciones">
          <button type="button" @click="cerrarCelda">Cancelar</button>
          <button class="primario" type="submit">Guardar</button>
        </span>
      </footer>
    </form>
  </dialog>
</template>

<style scoped>
.copiar-dias-titulo {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-2);
}

.copiar-dias-marcas {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.copiar-dia {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
}

.copiar-dia input {
  width: auto;
  height: auto;
  margin: 0;
  padding: 0;
}

.copiar-dia-punto {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--alerta);
}

.copiar-dias-aviso {
  margin: 8px 0 0;
  font-size: 12px;
  font-weight: 400;
  color: var(--text-3);
}

.copiar-dias-atajos {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

button.copiar-dias-atajo {
  padding: 4px 8px;
  font-size: 12px;
}

.delta {
  margin-left: 0.35rem;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
}

.pausa-inicio-fila {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.pausa-inicio-fila input {
  width: 9rem;
  margin-top: 0;
  flex: 0 0 auto;
}

.pausa-inicio-nota {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-3);
}

:deep(table.cuadrante thead th.col-festivo),
:deep(table.cuadrante thead th.fin.col-festivo) {
  background: color-mix(in srgb, var(--festivo-bg) 42%, var(--libranza-bg));
}

.cuadrante-panel {
  display: contents;
}

.semana.lectura .cuadrante-panel > :not(.semana-nav):not(.aviso-lectura) {
  grid-column: 1 / -1;
}

.semana.cuadrante-modal {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  background: rgba(32, 36, 44, 0.45);
  outline: none;
}

.cuadrante-modal .cuadrante-panel {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 96vw;
  height: 94vh;
  box-sizing: border-box;
  padding: 16px 48px 12px 16px;
  border-radius: 12px;
  background: var(--bg);
  overflow: hidden;
}

.cuadrante-modal .cuadrante-panel > :not(.cuadrante-scroll) {
  flex-shrink: 0;
}

.cuadrante-modal .cuadrante-scroll {
  flex: 1 1 auto;
  min-height: 0;
  max-width: none;
  overflow: auto;
}

.cuadrante-modal .cuadrante-scroll thead th {
  position: sticky;
  top: 0;
  z-index: 3;
  background: var(--libranza-bg);
}

.cuadrante-modal .cuadrante-scroll table.anual thead tr.anio-dias th {
  top: 37px;
}

.cuadrante-modal .cuadrante-scroll tbody th,
.cuadrante-modal .cuadrante-scroll tfoot td:first-child,
.cuadrante-modal .cuadrante-scroll thead th:first-child {
  position: sticky;
  left: 0;
}

.cuadrante-modal .cuadrante-scroll thead th:first-child {
  z-index: 4;
  background: var(--libranza-bg);
}

.cuadrante-modal .cuadrante-scroll tbody th {
  z-index: 1;
  background: var(--panel);
}

.cuadrante-modal .cuadrante-scroll tfoot td:first-child {
  z-index: 1;
  background: #fafbfc;
}

.cuadrante-modal .cuadrante-scroll tbody tr.grupo-fila > th {
  position: static;
  left: auto;
  z-index: auto;
}

.cuadrante-modal .cuadrante-scroll table.anual thead tr.anio-dias th:first-child {
  left: auto;
  z-index: 3;
}

.cuadrante-modal .cuadrante-scroll table.anual tbody tr.grupo-fila th.grupo-anio-nombre {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--bg);
}

button.cuadrante-cerrar:not(.tarjeta):not(.celda) {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 5;
  margin: 0;
  padding: 0 4px;
  border: 0;
  background: transparent;
  color: var(--text-2);
  font-size: 22px;
  font-weight: 600;
  line-height: 1;
}

button.cuadrante-cerrar:not(.tarjeta):not(.celda):hover {
  border-color: transparent;
  color: var(--text);
}

@media print {
  .cuadrante-modal {
    position: static;
    display: block;
    background: none;
  }

  .cuadrante-modal .cuadrante-panel {
    display: contents;
  }
}

.anio-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 8px;
}

.anio-chips button.anio-chip {
  padding: 3px 8px;
  font-size: 11px;
  letter-spacing: 0.04em;
}

:deep(table.cuadrante.anual thead tr.anio-dias th:first-child) {
  position: static;
  left: auto;
  z-index: auto;
  width: auto;
  min-width: 4.6rem;
  padding-left: 0.25rem;
  text-align: center;
}

.cuadrante-modal .cuadrante-scroll table.anual thead tr.anio-meses th {
  z-index: 4;
}

.cuadrante-modal .cuadrante-scroll table.anual thead tr.anio-meses th:first-child {
  z-index: 5;
}

.cuadrante-modal .cuadrante-scroll table.anual thead tr.anio-dias th:first-child {
  position: sticky;
  top: 37px;
  left: auto;
  z-index: 3;
  width: auto;
  min-width: 4.6rem;
  text-align: center;
}

:deep(table.cuadrante.anual th.mes-inicio),
:deep(table.cuadrante.anual td.mes-inicio) {
  border-left: 2px solid var(--border-strong);
}

:deep(table.cuadrante.anual tbody tr.grupo-fila th.grupo-anio-nombre) {
  position: sticky;
  left: 0;
  z-index: 1;
  width: 7rem;
  min-width: 7rem;
  max-width: 7rem;
  background: var(--bg);
}

:deep(table.cuadrante.anual tbody tr.grupo-fila td.grupo-anio-resto) {
  background: var(--bg);
}

:deep(table.cuadrante.anual .anio-meses button.anio-mes) {
  width: 100%;
  margin: 0;
  padding: 6px 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
  text-transform: none;
}

</style>
