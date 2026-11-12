<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import LeyendaTurnos from "./LeyendaTurnos.vue";
import { fechaVisible, lunesDe, rangoSemana, sumarDias, textoCelda } from "../fechas.js";
import { GRUPOS } from "../personas.js";
import { borrarAusenciaMando, borrarTurno, copiarSemana, exportarCuadrante, guardarAusenciasMando, guardarTurno, guardarTurnos, mes, mesMandos, semana, semanaActual, semanaMandos } from "../api/turnos.js";

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
const semanaDesde = ref("");
const anioMes = ref(0);
const numeroMes = ref(0);
const cuadrante = ref(null);
const periodoAnterior = ref(null);
let solicitudAnterior = 0;
const errorSemana = ref("");
const avisoCopia = ref("");
const celda = ref(null);
const dialogo = ref(null);
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoAusencia = ref("L");
const conHorario = computed(
  () => turnoModo.value === "ausencia" && (turnoAusencia.value === "ST" || turnoAusencia.value === "FT"),
);
const errorTurno = ref("");
const seccionElegida = ref("");
const copiasMarcadas = ref([false, false, false, false, false, false, false]);
const letrasCopia = ["L", "M", "X", "J", "V", "S", "D"];
const ausenciasConCoste = new Set([null, "ST", "FT"]);
const euros = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

const tituloMes = computed(() => `${mesesLargos[numeroMes.value - 1] || ""} ${anioMes.value}`.trim());
const gruposCuadrante = GRUPOS;
function claveTrabajador(trabajador) {
  return trabajador.login || trabajador.id;
}

const muestraEquipo = computed(
  () => props.propia && modo.value === "semana" && cuadrante.value?.desde === semanaActual(),
);

const secciones = computed(() => {
  const nombres = new Set();
  for (const trabajador of cuadrante.value?.trabajadores || []) {
    if (trabajador.seccion) {
      nombres.add(trabajador.seccion);
    }
  }
  return [...nombres].sort((a, b) => a.localeCompare(b, "es"));
});

const muestraSecciones = computed(() => !props.propia && !props.mandos && secciones.value.length > 0);
const muestraCoste = computed(() => !props.propia && !props.mandos);

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

const filasCuadrante = computed(() => {
  const lista = trabajadoresCuadrante.value;
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

function diaSemana(iso) {
  const [anio, mesNumero, dia] = partes(iso);
  return new Date(anio, mesNumero - 1, dia).getDay();
}

function cambiarModo(nuevo) {
  if (nuevo === modo.value) {
    return;
  }
  modo.value = nuevo;
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
  if (modo.value !== "mes") {
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

function horasPeriodo(trabajador, campo, ausencias) {
  return (trabajador.dias || []).reduce((total, dia) => {
    if (ausencias && !ausencias.has(dia.turno?.ausencia ?? null)) {
      return total;
    }
    return total + (Number(dia.turno?.[campo]) || 0);
  }, 0);
}

function tieneCoste(trabajador) {
  if (trabajador.coste === null || trabajador.coste === undefined || trabajador.coste === "") {
    return false;
  }
  return Number.isFinite(Number(trabajador.coste));
}

function importeEtt(trabajador) {
  if (trabajador.grupo !== "ETT" || !tieneCoste(trabajador)) {
    return null;
  }
  return horasPeriodo(trabajador, "horas_planificadas", ausenciasConCoste) * Number(trabajador.coste);
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

function textoCostePersona(trabajador) {
  if (trabajador.grupo !== "ETT") {
    return "";
  }
  const importe = importeEtt(trabajador);
  return importe === null ? "—" : euros.format(importe);
}

function costeGrupo(id) {
  if (id !== "ETT") {
    return null;
  }
  const personas = trabajadoresCuadrante.value.filter((trabajador) => trabajador.grupo === "ETT");
  return {
    total: personas.reduce((suma, trabajador) => suma + (importeEtt(trabajador) || 0), 0),
    sinCoste: personas.filter((trabajador) => !tieneCoste(trabajador)).length,
  };
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
  };
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

function alAntesDeImprimir() {
  const visible = raiz.value instanceof HTMLElement && raiz.value.offsetParent !== null;
  document.body.classList.toggle("imprimir-cuadrante", visible);
}

function alDespuesDeImprimir() {
  document.body.classList.remove("imprimir-cuadrante");
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

onMounted(() => {
  window.addEventListener("beforeprint", alAntesDeImprimir);
  window.addEventListener("afterprint", alDespuesDeImprimir);
});

onUnmounted(() => {
  window.removeEventListener("beforeprint", alAntesDeImprimir);
  window.removeEventListener("afterprint", alDespuesDeImprimir);
  alDespuesDeImprimir();
});

cargar(lunesDe(new Date()));
</script>

<template>
  <section
    v-if="cuadrante"
    ref="raiz"
    class="semana"
    :class="{ lectura: !editable && !mandos, 'pagina-horizontal': modo === 'mes' }"
  >
    <div class="semana-nav">
      <div class="vistas modo-vista">
        <button type="button" :class="{ activo: modo === 'semana' }" @click="cambiarModo('semana')">
          Semanal
        </button>
        <button type="button" :class="{ activo: modo === 'mes' }" @click="cambiarModo('mes')">
          Mensual
        </button>
      </div>
      <template v-if="modo === 'semana'">
        <button type="button" @click="cargar(sumarDias(semanaDesde, -7))">Semana anterior</button>
        <span class="rango">{{ rangoSemana(cuadrante.desde, cuadrante.dias[6]) }}</span>
        <button type="button" @click="cargar(sumarDias(semanaDesde, 7))">Semana siguiente</button>
        <button v-if="editable" type="button" @click="copiar">Copiar semana anterior</button>
      </template>
      <template v-else>
        <button type="button" @click="moverMes(-1)">Mes anterior</button>
        <span class="rango">{{ tituloMes }}</span>
        <button type="button" @click="moverMes(1)">Mes siguiente</button>
      </template>
      <button v-if="mandos" type="button" @click="emit('cambiar-horario')">Cambiar mi horario</button>
      <button type="button" class="cuadrante-imprimir" @click="imprimir">Imprimir</button>
      <button v-if="editable" type="button" class="cuadrante-exportar" @click="exportar">Exportar</button>
    </div>
    <p v-if="!editable && !mandos" class="aviso-lectura">Solo lectura</p>
    <p v-if="muestraEquipo" class="equipo-semana">Equipo de esta semana</p>
    <p v-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
    <p v-if="avisoCopia" class="aviso-ok" role="status">{{ avisoCopia }}</p>
    <div v-if="muestraSecciones" class="cuadrante-seccion">
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
    </div>
    <div v-if="!propia && !mandos" class="cuadrante-horas">
      <article v-for="tarjeta in resumenHoras" :key="tarjeta.id" :class="tarjeta.id">
        <p class="lb">{{ tarjeta.nombre }}</p>
        <p class="vl">
          {{ tarjeta.valor }}<span v-if="tarjeta.delta" class="delta" :title="tituloComparacion">{{ ` ${tarjeta.delta}` }}</span>
        </p>
      </article>
    </div>
    <div class="cuadrante-scroll" :class="{ mensual: modo === 'mes' }">
    <table class="cuadrante" :class="{ mensual: modo === 'mes' }">
      <thead>
        <tr>
          <th>Trabajador</th>
          <th v-for="(dia, indice) in cuadrante.dias" :key="dia" :class="{ fin: esFinDia(dia, indice) }">
            <span class="dia-nombre">{{ modo === "mes" ? diasCortos[diaSemana(dia)] : diasNombre[indice] }}</span>
            <span class="dia-numero">{{ modo === "mes" ? Number(dia.slice(8)) : fechaVisible(dia).slice(0, 5) }}</span>
            <span
              v-if="nombreFestivo(indice)"
              class="dia-festivo"
              :title="nombreFestivo(indice)"
              :aria-label="nombreFestivo(indice)"
            ></span>
          </th>
          <th v-if="muestraCoste" class="coste-col">
            <span class="dia-nombre">Coste</span>
            <span class="dia-numero">{{ modo === "mes" ? "mes" : "semana" }}</span>
          </th>
        </tr>
      </thead>
      <tbody>
        <template v-for="fila in filasCuadrante" :key="fila.tipo === 'grupo' ? fila.id : claveTrabajador(fila.trabajador)">
          <tr v-if="fila.tipo === 'grupo'" class="grupo-fila">
            <th :colspan="cuadrante.dias.length + 1">{{ fila.titulo }}</th>
            <td v-if="muestraCoste" class="coste-col">
              <template v-if="costeGrupo(fila.id)">
                <span class="coste-total">{{ euros.format(costeGrupo(fila.id).total) }}</span>
                <span
                  v-if="costeGrupo(fila.id).sinCoste"
                  class="coste-nota"
                  title="Trabajadores ETT sin coste asignado: no suman en el total"
                >
                  ({{ costeGrupo(fila.id).sinCoste }} sin coste)
                </span>
              </template>
            </td>
          </tr>
          <tr v-else>
            <th>{{ fila.trabajador.nombre }}</th>
            <td
              v-for="(dia, indice) in fila.trabajador.dias"
              :key="dia.fecha"
              :class="[esFinDia(dia.fecha, indice) ? 'fin' : '', familia(dia.turno) ? `turno-${familia(dia.turno)}` : '']"
            >
              <button
                v-if="editable || (mandos && esMio(fila.trabajador))"
                type="button"
                class="celda"
                :title="textoAjustes(dia)"
                @click="abrirCelda(fila.trabajador, dia)"
              >
                <span v-if="muestraAjuste(dia)" class="ajuste-marca">
                  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                    <path d="M2.2 13.8 5 13.1 13.2 4.9 11.1 2.8 2.9 11Z" />
                    <path d="M9.4 4.5 11.5 6.6" />
                    <path d="M3.2 11.4 4.6 12.8" />
                  </svg>
                </span>
                {{ textoCelda(dia.turno) }}
              </button>
              <span v-else class="celda" :class="{ lectura: !mandos }" :title="textoAjustes(dia)">
                <span v-if="muestraAjuste(dia)" class="ajuste-marca">
                  <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
                    <path d="M2.2 13.8 5 13.1 13.2 4.9 11.1 2.8 2.9 11Z" />
                    <path d="M9.4 4.5 11.5 6.6" />
                    <path d="M3.2 11.4 4.6 12.8" />
                  </svg>
                </span>
                {{ textoCelda(dia.turno) }}
              </span>
            </td>
            <td
              v-if="muestraCoste"
              class="coste-col"
              :class="fila.trabajador.grupo === 'ETT' ? (tieneCoste(fila.trabajador) ? 'coste-importe' : 'coste-vacio') : ''"
            >{{ textoCostePersona(fila.trabajador) }}</td>
          </tr>
        </template>
      </tbody>
      <tfoot v-if="!propia && !mandos">
        <tr v-for="franja in franjas" :key="franja.id">
          <td>{{ franja.nombre }}</td>
          <td v-for="(dia, indice) in cuadrante.dias" :key="dia">{{ totalFranja(franja.id, indice) }}</td>
          <td v-if="muestraCoste" class="coste-col"></td>
        </tr>
        <tr>
          <td>Horas nocturnas</td>
          <td v-for="(dia, indice) in cuadrante.dias" :key="`noche-${dia}`">{{ horasNocturnas(indice) }}</td>
          <td v-if="muestraCoste" class="coste-col"></td>
        </tr>
      </tfoot>
    </table>
    </div>
    <LeyendaTurnos />
  </section>
  <p v-else-if="errorSemana" class="error" role="alert">{{ errorSemana }}</p>
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

table.cuadrante th.coste-col,
table.cuadrante td.coste-col {
  width: 7.5rem;
  min-width: 7.5rem;
  max-width: 8rem;
  text-align: center;
  white-space: nowrap;
}

table.cuadrante thead th.coste-col .dia-numero {
  text-transform: none;
}

table.cuadrante tbody tr.grupo-fila td.coste-col {
  background: var(--bg);
}

.coste-total,
.coste-importe {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.coste-total {
  display: block;
  font-weight: 700;
}

.coste-nota {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  font-weight: 400;
  line-height: 1.2;
  color: var(--text-3);
}

.coste-vacio {
  font-weight: 400;
  color: var(--text-3);
}

.delta {
  margin-left: 0.35rem;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
}

.celda {
  position: relative;
}

.ajuste-marca {
  position: absolute;
  top: -5px;
  right: -5px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1.5px solid #fff;
  border-radius: 50%;
  background: var(--accent-darker);
  color: #fff;
  pointer-events: none;
  cursor: default;
}

.ajuste-marca svg {
  display: block;
  width: 10px;
  height: 10px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
