<script setup>
import { computed, onActivated, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { borrar as borrarSeguimiento, obtener, guardar as guardarSeguimiento } from "../api/seguimiento.js";
import { semana } from "../api/turnos.js";
import { horasPeriodo } from "../costes.js";
import { lunesDe, rangoSemana, sumarDias } from "../fechas.js";
import Aviso from "./Aviso.vue";
import NavegacionPeriodo from "./NavegacionPeriodo.vue";
import {
  cuerpoGuardado,
  detalleDesdeCeldas,
  aplicarDias,
  desviacionSeguimiento,
  lecturaSeguimiento,
  numeroSuelto,
  pegarSeguimiento,
  ratioReal,
  ratioSeguimiento,
} from "../seguimiento.js";

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const CELDAS_VACIAS = ["", "", "", "", "", ""];

const props = defineProps({
  token: { type: String, required: true },
  departamentoId: { type: String, default: "" },
});

const emit = defineEmits(["cambios"]);

const tabla = ref(null);
const periodo = ref(null);
const semanaDesde = ref("");
const magnitud = ref("toneladas");
const magnitudes = reactive({
  toneladas: crearMagnitud(),
  pales: crearMagnitud(),
});
const error = ref("");
const falloPegado = ref("");
const aviso = ref("");
const avisoOculto = ref("");
const notaPegado = ref("");
const filasDestello = ref({ prevision: false, real: false });
const celdasDestello = ref({ prevision: [], real: [] });
let generacion = 0;
let avisoTimer = 0;
let notaTimer = 0;
let destelloTimer = 0;
let ultimaFila = "";

function crearMagnitud() {
  return {
    celdas: [...CELDAS_VACIAS],
    celdasReal: [...CELDAS_VACIAS],
    totalDeclarado: null,
    totalRealDeclarado: null,
    firmaGuardada: firmaDe(CELDAS_VACIAS, CELDAS_VACIAS),
  };
}

function firmaDe(celdas, celdasReal) {
  return JSON.stringify([celdas, celdasReal]);
}

const etiqueta = computed(() => {
  if (periodo.value?.desde && periodo.value?.dias?.[6]) {
    return rangoSemana(periodo.value.desde, periodo.value.dias[6]);
  }
  if (!semanaDesde.value) {
    return "";
  }
  return rangoSemana(semanaDesde.value, sumarDias(semanaDesde.value, 6));
});

const actual = computed(() => magnitudes[magnitud.value]);
const divisor = computed(() => (magnitud.value === "pales" ? 1 : 1000));
const unidad = computed(() => (magnitud.value === "pales" ? "pal/h" : "t/h"));
const diasKg = computed(() => actual.value.celdas.map(kilosDeCelda));
const diasReales = computed(() => actual.value.celdasReal.map(kilosDeCelda));
const totalKg = computed(() => sumaCeldas(diasKg.value));
const totalRealKg = computed(() => sumaCeldas(diasReales.value));
const horasDias = computed(() => DIAS.map((_, indice) => horasDe(indice)));
const horasSemana = computed(() => horasDe(null));
const horasDomingo = computed(() => horasDe(6));
const resultado = computed(() => {
  if (totalKg.value === null) {
    return { ratio: null, motivo: "" };
  }
  return ratioSeguimiento(totalKg.value / divisor.value, horasSemana.value);
});
const realInfo = computed(() => ratioReal(diasReales.value, horasDias.value, divisor.value));
const desviacion = computed(() => desviacionSeguimiento(diasKg.value, diasReales.value, divisor.value));
const previsionLista = computed(() => !detalleDesdeCeldas(actual.value.celdas, "Previsión").error);
const deltaReal = computed(() => {
  if (resultado.value.ratio === null || realInfo.value.ratio === null) {
    return "";
  }
  const diferencia = Number((realInfo.value.ratio - resultado.value.ratio).toFixed(2));
  if (diferencia === 0) {
    return `±0,00 ${unidad.value} respecto a la prevista`;
  }
  const signo = diferencia > 0 ? "+" : "−";
  return `${signo}${numeroVisible(Math.abs(diferencia), 2)} ${unidad.value} respecto a la prevista`;
});
const avisoTotal = computed(() => avisoDeTotal(actual.value.totalDeclarado, totalKg.value));
const avisoTotalReal = computed(() => {
  const texto = avisoDeTotal(actual.value.totalRealDeclarado, totalRealKg.value);
  return texto ? "El total real no coincide con la suma de los días." : "";
});
const avisos = computed(() => {
  const lista = diasKg.value.flatMap((kg, indice) => {
    if (!(kg > 0) || horasDias.value[indice] > 0) {
      return [];
    }
    const cantidad = magnitud.value === "pales" ? `${kilosVisibles(kg)} pal` : `${toneladasVisibles(kg)} t`;
    return [`${DIAS_LARGOS[indice]}: ${cantidad} sin horas planificadas`];
  });
  if (avisoTotal.value) {
    lista.push(avisoTotal.value);
  }
  if (avisoTotalReal.value) {
    lista.push(avisoTotalReal.value);
  }
  if (falloPegado.value) {
    lista.unshift(falloPegado.value);
  }
  return lista;
});
const claveAvisos = computed(() => `${semanaDesde.value}\n${avisos.value.join("\n")}`);
const mostrarAvisos = computed(() => avisos.value.length > 0 && claveAvisos.value !== avisoOculto.value);

function kilosDeCelda(celda) {
  const texto = String(celda ?? "").trim().replace(",", ".");
  if (!texto) {
    return null;
  }
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

function sumaCeldas(dias) {
  if (dias.every((dia) => dia === null)) {
    return null;
  }
  return dias.reduce((suma, dia) => suma + (dia ?? 0), 0);
}

function avisoDeTotal(declarado, suma) {
  if (declarado === null || suma === null) {
    return "";
  }
  if (Math.abs(declarado - suma) > 0.001) {
    return "El total no coincide con la suma de los días.";
  }
  return "";
}

function horasDe(indice) {
  return (periodo.value?.trabajadores || [])
    .filter((trabajador) => trabajador.grupo === "STEF" || trabajador.grupo === "ETT")
    .reduce((total, trabajador) => {
      const dias = indice === null ? trabajador.dias : [trabajador.dias?.[indice]];
      return total + horasPeriodo({ dias }, "horas_planificadas");
    }, 0);
}

function numeroVisible(valor, decimales) {
  const redondeado = Number(Number(valor).toFixed(decimales));
  const [entero, fraccion = ""] = Math.abs(redondeado).toFixed(decimales).split(".");
  const grupos = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const texto = decimales > 0 ? `${grupos},${fraccion}` : grupos;
  return redondeado < 0 ? `-${texto}` : texto;
}

function kilosVisibles(valor) {
  if (valor === null) {
    return "—";
  }
  return numeroVisible(valor, Number.isInteger(valor) ? 0 : 2);
}

function toneladasVisibles(kg) {
  return numeroVisible(kg / divisor.value, divisor.value === 1 && Number.isInteger(kg) ? 0 : 2);
}

function cantidadVisible(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  if (divisor.value === 1) {
    return kilosVisibles(valor);
  }
  return numeroVisible(valor, 2);
}

function horasVisibles(valor) {
  return numeroVisible(valor, 2).replace(/,00$/, "").replace(/(\,\d)0$/, "$1");
}

function ratioCelda(kg, horas) {
  if (kg === null || !(horas > 0)) {
    return "—";
  }
  return numeroVisible(kg / divisor.value / horas, 2);
}

function ratioRealCelda(kg, horas) {
  if (!(Number(kg) > 0) || !(horas > 0)) {
    return "—";
  }
  return numeroVisible(kg / divisor.value / horas, 2);
}

function textoDesviacion(dato) {
  if (!dato || dato.toneladas === null) {
    return "—";
  }
  const decimales = divisor.value === 1 && Number.isInteger(dato.toneladas) ? 0 : 2;
  const cantidad = conSigno(dato.toneladas, decimales, divisor.value === 1 ? "" : " t");
  if (dato.porcentaje === null) {
    return cantidad;
  }
  return `${cantidad} · ${conSigno(dato.porcentaje, 1, " %")}`;
}

function conSigno(valor, decimales, sufijo) {
  const texto = numeroVisible(valor, decimales);
  return `${valor > 0 ? "+" : ""}${texto}${sufijo}`;
}

function ratioVisible(valor) {
  return `${numeroVisible(valor, 2)} ${unidad.value}`;
}

function sucia(nombre) {
  const estado = magnitudes[nombre];
  return firmaDe(estado.celdas, estado.celdasReal) !== estado.firmaGuardada;
}

const hayCambios = computed(() => sucia("toneladas") || sucia("pales"));

function alCerrar(evento) {
  evento.preventDefault();
  evento.returnValue = "";
}

function irASemana(desde) {
  if (hayCambios.value && desde !== semanaDesde.value) {
    const seguir = window.confirm("Hay cambios sin guardar. ¿Cambiar de semana y perderlos?");
    if (!seguir) {
      return;
    }
  }
  cargar(desde);
}

function cerrarAvisos() {
  avisoOculto.value = claveAvisos.value;
}

function ocultarAviso() {
  window.clearTimeout(avisoTimer);
  avisoTimer = 0;
  aviso.value = "";
}

function mostrarGuardado() {
  aviso.value = "Guardado";
  window.clearTimeout(avisoTimer);
  avisoTimer = window.setTimeout(() => {
    aviso.value = "";
    avisoTimer = 0;
  }, 2500);
}

function vaciarMagnitud(estado) {
  estado.celdas = [...CELDAS_VACIAS];
  estado.celdasReal = [...CELDAS_VACIAS];
  estado.totalDeclarado = null;
  estado.totalRealDeclarado = null;
  estado.firmaGuardada = firmaDe(estado.celdas, estado.celdasReal);
}

function totalQueNoCuadra(leido) {
  const suma = leido.dias.reduce((total, dia) => total + (dia === "" ? 0 : Number(dia)), 0);
  return leido.total !== null && Math.abs(leido.total - suma) > 0.001 ? leido.total : null;
}

function aplicarLeido(estado, leido) {
  estado.celdas = leido.prevision.dias;
  estado.celdasReal = leido.real.dias;
  estado.totalDeclarado = totalQueNoCuadra(leido.prevision);
  estado.totalRealDeclarado = totalQueNoCuadra(leido.real);
  estado.firmaGuardada = firmaDe(estado.celdas, estado.celdasReal);
}

function alEditar(fila) {
  ocultarAviso();
  falloPegado.value = "";
  const estado = actual.value;
  const vacia = (celda) => String(celda).trim() === "";
  if (fila === "real") {
    if (estado.celdasReal.every(vacia)) {
      estado.totalRealDeclarado = null;
    }
    return;
  }
  if (estado.celdas.every(vacia)) {
    estado.totalDeclarado = null;
  }
}

function anioVisible() {
  const anio = Number(String(semanaDesde.value).slice(0, 4));
  return Number.isInteger(anio) ? anio : null;
}

function filaEnFoco() {
  return celdaEnFoco()?.fila ?? null;
}

function celdaEnFoco() {
  const activo = document.activeElement;
  if (!tabla.value?.contains(activo)) {
    return null;
  }
  const fila = activo?.dataset?.fila;
  const indice = Number(activo?.dataset?.indice);
  if ((fila !== "real" && fila !== "prevision") || !Number.isInteger(indice) || indice < 0 || indice > 5) {
    return null;
  }
  return { fila, indice };
}

function destinoPegado() {
  return filaEnFoco() || ultimaFila || "prevision";
}

function recordarFila(fila) {
  if (fila === "prevision" || fila === "real") {
    ultimaFila = fila;
  }
}

function textoPegado(aplicados) {
  const tienePrevision = aplicados.some((item) => item.fila === "prevision");
  const tieneReal = aplicados.some((item) => item.fila === "real");
  if (tienePrevision && tieneReal) {
    return "Pegados en Previsión y Real";
  }
  const uno = aplicados[0];
  const nombre = uno.fila === "real" ? "Real" : "Previsión";
  return `Pegados ${uno.escritos} valores en ${nombre} desde ${DIAS[uno.desde]}`;
}

function anunciarPegado(aplicados) {
  const filas = { prevision: false, real: false };
  const celdas = { prevision: [], real: [] };
  for (const item of aplicados) {
    if (item.escritos >= 6) {
      filas[item.fila] = true;
    } else {
      celdas[item.fila] = item.indices;
    }
  }
  filasDestello.value = filas;
  celdasDestello.value = celdas;
  window.clearTimeout(destelloTimer);
  destelloTimer = window.setTimeout(() => {
    filasDestello.value = { prevision: false, real: false };
    celdasDestello.value = { prevision: [], real: [] };
    destelloTimer = 0;
  }, 1200);
  notaPegado.value = textoPegado(aplicados);
  window.clearTimeout(notaTimer);
  notaTimer = window.setTimeout(() => {
    notaPegado.value = "";
    notaTimer = 0;
  }, 3000);
}

function aplicarCelda(fila, indice, numero) {
  const estado = actual.value;
  const texto = String(numero);
  if (fila === "real") {
    const celdas = [...estado.celdasReal];
    celdas[indice] = texto;
    estado.celdasReal = celdas;
    estado.totalRealDeclarado = null;
  } else {
    const celdas = [...estado.celdas];
    celdas[indice] = texto;
    estado.celdas = celdas;
    estado.totalDeclarado = null;
  }
  alEditar(fila);
}

function aplicarFila(fila, parseo) {
  const estado = actual.value;
  const actuales = fila === "real" ? estado.celdasReal : estado.celdas;
  const foco = celdaEnFoco();
  const inicio = foco?.fila === fila ? foco.indice : null;
  const aplicado = aplicarDias(actuales, parseo.dias, inicio);
  const declarado = parseo.total == null ? null : parseo.total;
  if (fila === "real") {
    estado.celdasReal = aplicado.celdas;
    estado.totalRealDeclarado = declarado;
  } else {
    estado.celdas = aplicado.celdas;
    estado.totalDeclarado = declarado;
  }
  return aplicado;
}

function campoExterno(elemento) {
  if (!elemento) {
    return false;
  }
  const etiquetaCampo = elemento.tagName;
  const esCampo = etiquetaCampo === "INPUT" || etiquetaCampo === "TEXTAREA" || elemento.isContentEditable;
  return esCampo && !(tabla.value && tabla.value.contains(elemento));
}

function alPegar(evento) {
  if (campoExterno(document.activeElement)) {
    return;
  }
  const texto = evento.clipboardData?.getData("text") ?? "";
  const suelto = numeroSuelto(texto);
  const celda = celdaEnFoco();
  if (suelto !== null && !celda) {
    return;
  }
  evento.preventDefault();
  if (suelto !== null && celda) {
    aplicarCelda(celda.fila, celda.indice, suelto);
    recordarFila(celda.fila);
    falloPegado.value = "";
    error.value = "";
    anunciarPegado([{
      fila: celda.fila,
      escritos: 1,
      desde: celda.indice,
      indices: [celda.indice],
    }]);
    return;
  }
  const pegado = pegarSeguimiento(texto, destinoPegado(), anioVisible(), {
    magnitud: magnitud.value,
  });
  if (pegado.error || pegado.prevision?.error || pegado.real?.error) {
    falloPegado.value = pegado.error || pegado.prevision?.error || pegado.real?.error;
    notaPegado.value = "";
    window.clearTimeout(notaTimer);
    notaTimer = 0;
    return;
  }
  const aplicados = [];
  if (pegado.prevision) {
    aplicados.push({ fila: "prevision", ...aplicarFila("prevision", pegado.prevision) });
  }
  if (pegado.real) {
    aplicados.push({ fila: "real", ...aplicarFila("real", pegado.real) });
  }
  if (aplicados.length === 1) {
    recordarFila(aplicados[0].fila);
  }
  const sobras = [...new Set(aplicados.map((item) => item.aviso).filter(Boolean))];
  falloPegado.value = sobras.join(" ");
  error.value = "";
  ocultarAviso();
  anunciarPegado(aplicados);
}

async function cargar(desde) {
  const solicitud = ++generacion;
  error.value = "";
  falloPegado.value = "";
  ocultarAviso();
  vaciarMagnitud(magnitudes.toneladas);
  vaciarMagnitud(magnitudes.pales);
  try {
    const [turnos, seguimiento] = await Promise.all([
      semana(props.token, desde, false, props.departamentoId),
      obtener(props.token, desde, props.departamentoId),
    ]);
    if (solicitud !== generacion) {
      return;
    }
    periodo.value = turnos;
    semanaDesde.value = turnos.desde || seguimiento.semana_inicio;
    const leido = lecturaSeguimiento(seguimiento);
    aplicarLeido(magnitudes.toneladas, leido.toneladas);
    aplicarLeido(magnitudes.pales, leido.pales);
  } catch (causa) {
    if (solicitud !== generacion) {
      return;
    }
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar el seguimiento";
  }
}

async function guardar() {
  error.value = "";
  ocultarAviso();
  const estado = actual.value;
  const construido = cuerpoGuardado(magnitud.value, estado.celdas, estado.celdasReal);
  if (construido.error) {
    error.value = construido.error;
    return;
  }
  try {
    await guardarSeguimiento(props.token, semanaDesde.value, props.departamentoId, construido);
    estado.totalDeclarado = null;
    estado.totalRealDeclarado = null;
    estado.firmaGuardada = firmaDe(estado.celdas, estado.celdasReal);
    mostrarGuardado();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo guardar el seguimiento";
  }
}

async function borrar() {
  error.value = "";
  falloPegado.value = "";
  ocultarAviso();
  if (!semanaDesde.value) {
    vaciarMagnitud(actual.value);
    return;
  }
  try {
    await borrarSeguimiento(props.token, semanaDesde.value, props.departamentoId, magnitud.value);
    vaciarMagnitud(actual.value);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo borrar el seguimiento";
  }
}

watch(hayCambios, (sucio) => {
  emit("cambios", sucio);
  if (sucio) {
    window.addEventListener("beforeunload", alCerrar);
    return;
  }
  window.removeEventListener("beforeunload", alCerrar);
}, { immediate: true });

onActivated(() => {
  emit("cambios", hayCambios.value);
});

onMounted(() => {
  window.addEventListener("paste", alPegar);
  cargar(lunesDe(new Date()));
});

onUnmounted(() => {
  window.removeEventListener("paste", alPegar);
  window.removeEventListener("beforeunload", alCerrar);
  window.clearTimeout(avisoTimer);
  window.clearTimeout(notaTimer);
  window.clearTimeout(destelloTimer);
  emit("cambios", false);
});
</script>

<template>
  <section class="semana">
    <div class="semana-nav">
      <NavegacionPeriodo
        anterior="Semana anterior"
        siguiente="Semana siguiente"
        @anterior="irASemana(sumarDias(semanaDesde || lunesDe(new Date()), -7))"
        @siguiente="irASemana(sumarDias(semanaDesde || lunesDe(new Date()), 7))"
      >
        {{ etiqueta }}
      </NavegacionPeriodo>
    </div>
    <div class="vistas seguimiento-magnitud">
      <button
        type="button"
        :class="{ activo: magnitud === 'toneladas' }"
        :aria-label="sucia('toneladas') ? 'Toneladas, cambios sin guardar' : 'Toneladas'"
        @click="magnitud = 'toneladas'"
      >
        Toneladas
        <span v-if="magnitud !== 'toneladas' && sucia('toneladas')" class="seguimiento-puntito" aria-hidden="true"></span>
      </button>
      <button
        type="button"
        :class="{ activo: magnitud === 'pales' }"
        :aria-label="sucia('pales') ? 'Palés, cambios sin guardar' : 'Palés'"
        @click="magnitud = 'pales'"
      >
        Palés
        <span v-if="magnitud !== 'pales' && sucia('pales')" class="seguimiento-puntito" aria-hidden="true"></span>
      </button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-if="totalKg !== null || realInfo.hayDatos" class="productividad-par">
      <article class="panel productividad">
        <p class="productividad-titulo">Productividad prevista</p>
        <p class="productividad-valor">{{ totalKg === null || resultado.ratio === null ? "—" : ratioVisible(resultado.ratio) }}</p>
        <p v-if="totalKg !== null" class="productividad-cuenta">
          {{ toneladasVisibles(totalKg) }}{{ magnitud === "pales" ? "" : " t" }} ÷ {{ horasVisibles(horasSemana) }} h
          <span v-if="etiqueta"> · {{ etiqueta }}</span>
        </p>
        <p v-if="resultado.motivo" class="productividad-cuenta">{{ resultado.motivo }}</p>
      </article>
      <article class="panel productividad" :class="{ 'sin-datos': !realInfo.hayDatos }">
        <p class="productividad-titulo">Productividad real</p>
        <p v-if="!realInfo.hayDatos" class="productividad-valor sin-datos">Sin datos reales</p>
        <template v-else>
          <p class="productividad-valor">{{ realInfo.ratio === null ? "—" : ratioVisible(realInfo.ratio) }}</p>
          <p class="productividad-cuenta">
            {{ cantidadVisible(realInfo.toneladas) }}{{ magnitud === "pales" ? "" : " t" }} ÷ {{ horasVisibles(realInfo.horas) }} h
            <span v-if="etiqueta"> · {{ etiqueta }}</span>
          </p>
          <p v-if="realInfo.motivo" class="productividad-cuenta">{{ realInfo.motivo }}</p>
          <p v-if="deltaReal" class="productividad-delta">{{ deltaReal }}</p>
        </template>
      </article>
    </div>
    <Aviso v-if="mostrarAvisos" :mensajes="avisos" @cerrar="cerrarAvisos" />
    <section class="seguimiento-entrada-marco">
      <h2>Datos de la semana ({{ magnitud === "pales" ? "palés" : "kg" }}) · pega o escribe aquí</h2>
      <p v-if="totalKg === null && totalRealKg === null" class="cobertura-nota seguimiento-pista">
        Pega en la fila de Previsión o de Real con Ctrl+V
      </p>
      <div class="cuadrante-scroll costes-scroll">
        <table ref="tabla" class="cuadrante seguimiento-tabla seguimiento-entrada">
          <colgroup>
            <col class="col-nombre" />
            <col v-for="dia in DIAS" :key="dia" class="col-dia" />
            <col class="col-total" />
          </colgroup>
          <thead>
            <tr>
              <th></th>
              <th v-for="dia in DIAS" :key="dia">{{ dia }}</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            <tr class="fila-prevision" :class="{ 'fila-pegada': filasDestello.prevision }">
              <th>{{ magnitud === "pales" ? "Previsión (palés)" : "Previsión (kg)" }}</th>
              <td
                v-for="(dia, indice) in DIAS"
                :key="dia"
                :class="{ 'celda-pegada': celdasDestello.prevision.includes(indice) }"
              >
                <input
                  v-model="actual.celdas[indice]"
                  data-fila="prevision"
                  :data-indice="indice"
                  type="number"
                  min="0"
                  step="1"
                  inputmode="numeric"
                  :placeholder="magnitud === 'pales' ? 'palés' : 'kg'"
                  :aria-label="`Previsión ${DIAS_LARGOS[indice]}`"
                  @input="alEditar('prevision')"
                />
              </td>
              <td>{{ kilosVisibles(totalKg) }}</td>
            </tr>
            <tr class="fila-real" :class="{ 'fila-pegada': filasDestello.real }">
              <th>{{ magnitud === "pales" ? "Real (palés)" : "Real (kg)" }}</th>
              <td
                v-for="(dia, indice) in DIAS"
                :key="dia"
                :class="{ 'celda-pegada': celdasDestello.real.includes(indice) }"
              >
                <input
                  v-model="actual.celdasReal[indice]"
                  data-fila="real"
                  :data-indice="indice"
                  type="number"
                  min="0"
                  step="1"
                  inputmode="numeric"
                  :placeholder="magnitud === 'pales' ? 'palés' : 'kg'"
                  :aria-label="`Real ${DIAS_LARGOS[indice]}`"
                  @input="alEditar('real')"
                />
              </td>
              <td>{{ kilosVisibles(totalRealKg) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <p v-if="notaPegado" class="seguimiento-pegado" role="status">{{ notaPegado }}</p>
    <h2 class="seguimiento-resultado-titulo">Resultado</h2>
    <div class="cuadrante-scroll costes-scroll">
      <table class="cuadrante seguimiento-tabla">
        <colgroup>
          <col class="col-nombre" />
          <col v-for="dia in DIAS" :key="dia" class="col-dia" />
          <col class="col-total" />
        </colgroup>
        <thead>
          <tr>
            <th></th>
            <th v-for="dia in DIAS" :key="dia">{{ dia }}</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th>{{ magnitud === "pales" ? "Palés previstos" : "Toneladas previstas" }}</th>
            <td v-for="(kg, indice) in diasKg" :key="DIAS[indice]">
              {{ kg === null ? "—" : toneladasVisibles(kg) }}
            </td>
            <td>{{ totalKg === null ? "—" : toneladasVisibles(totalKg) }}</td>
          </tr>
          <tr>
            <th>{{ magnitud === "pales" ? "Palés reales" : "Toneladas reales" }}</th>
            <td v-for="(kg, indice) in diasReales" :key="DIAS[indice]">
              {{ Number(kg) > 0 ? toneladasVisibles(kg) : "—" }}
            </td>
            <td>{{ realInfo.hayDatos ? cantidadVisible(realInfo.toneladas) : "—" }}</td>
          </tr>
          <tr>
            <th>Horas</th>
            <td
              v-for="(horas, indice) in horasDias"
              :key="DIAS[indice]"
              :class="{ 'hora-vacia': !(horas > 0) }"
            >
              {{ horasVisibles(horas) }}
            </td>
            <td>{{ horasVisibles(horasSemana) }}</td>
          </tr>
          <tr class="fila-ratio">
            <th>{{ unidad }} previsto</th>
            <td
              v-for="(kg, indice) in diasKg"
              :key="DIAS[indice]"
              :class="{ 'hora-vacia': !(horasDias[indice] > 0) }"
            >
              {{ ratioCelda(kg, horasDias[indice]) }}
            </td>
            <td>{{ ratioCelda(totalKg, horasSemana) }}</td>
          </tr>
          <tr class="fila-ratio">
            <th>{{ unidad }} real</th>
            <td
              v-for="(kg, indice) in diasReales"
              :key="DIAS[indice]"
              :class="{ 'hora-vacia': !(Number(kg) > 0) || !(horasDias[indice] > 0) }"
            >
              {{ ratioRealCelda(kg, horasDias[indice]) }}
            </td>
            <td>{{ realInfo.ratio === null ? "—" : numeroVisible(realInfo.ratio, 2) }}</td>
          </tr>
          <tr>
            <th>Desviación</th>
            <td v-for="(dato, indice) in desviacion.dias" :key="DIAS[indice]">
              {{ textoDesviacion(dato) }}
            </td>
            <td>{{ textoDesviacion(desviacion.total) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="horasDomingo > 0" class="cobertura-nota">
      El domingo tiene horas (ST/FT) y entran en el total de la semana.
    </p>
    <div class="seguimiento-acciones">
      <button class="primario seguimiento-guardar" type="button" :disabled="!previsionLista" @click="guardar">
        Guardar
      </button>
      <button type="button" @click="borrar">Borrar</button>
      <span v-if="!previsionLista" class="seguimiento-falta">Falta la previsión.</span>
      <span v-if="aviso" class="seguimiento-guardado" role="status">{{ aviso }}</span>
    </div>
  </section>
</template>

<style scoped>
.productividad-par {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 1rem;
}

.productividad {
  margin: 0;
  padding: 16px 18px;
}

.productividad-delta {
  margin: 4px 0 0;
  color: var(--text-2);
  font-size: 12px;
}

.productividad-valor.sin-datos {
  color: var(--text-3);
  font-size: 22px;
  font-weight: 600;
}

.seguimiento-magnitud {
  margin: 0 0 12px;
}

.seguimiento-puntito {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-left: 6px;
  border-radius: 50%;
  background: var(--accent);
  vertical-align: 1px;
}

.seguimiento-falta {
  color: var(--text-2);
  font-size: 13px;
}

button.seguimiento-guardar:disabled {
  opacity: 0.45;
  cursor: default;
}

.productividad-titulo {
  margin: 0;
  color: var(--text-3);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.productividad-valor {
  margin: 2px 0 0;
  color: var(--text);
  font-size: 40px;
  font-weight: 700;
  line-height: 1.1;
}

.productividad-cuenta {
  margin: 6px 0 0;
  color: var(--text-2);
  font-size: 13px;
}

.seguimiento-pista {
  margin-bottom: 0.6rem;
}

.seguimiento-acciones {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 0.9rem;
}

.seguimiento-guardado {
  color: var(--ok);
  font-size: 12px;
  font-weight: 600;
}

.costes-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.seguimiento-pegado {
  margin: -0.65rem 0 1.25rem;
  color: var(--text-2);
  font-size: 13px;
}

.seguimiento-entrada tr.fila-pegada :is(th, td),
.seguimiento-entrada td.celda-pegada {
  animation: fila-pegada 1.2s ease;
}

@keyframes fila-pegada {
  0% {
    box-shadow: inset 0 0 0 999px color-mix(in srgb, var(--accent) 22%, transparent);
  }
  100% {
    box-shadow: inset 0 0 0 999px transparent;
  }
}

.seguimiento-entrada-marco {
  margin: 0 0 1.25rem;
  padding: 14px 16px 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--manana-bg);
}

.seguimiento-entrada-marco h2,
.seguimiento-resultado-titulo {
  margin: 0 0 0.7rem;
  color: var(--text);
  font-size: 15px;
  font-weight: 700;
}

.seguimiento-resultado-titulo {
  margin-top: 0.2rem;
}

.seguimiento-tabla {
  width: 100%;
  table-layout: fixed;
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.col-nombre {
  width: 22%;
}

.col-dia {
  width: 11%;
}

.col-total {
  width: 12%;
}

.seguimiento-tabla th,
.seguimiento-tabla td {
  padding: 0.85rem 0.7rem;
  font-size: 18px;
  text-align: right;
  white-space: nowrap;
}

.seguimiento-tabla thead th {
  font-size: 14px;
}

.seguimiento-tabla thead th:first-child,
.seguimiento-tabla tbody th {
  text-align: left;
  white-space: normal;
}

.seguimiento-entrada .fila-prevision :is(th, td) {
  background: var(--manana-bg);
}

.seguimiento-entrada .fila-real :is(th, td) {
  background: var(--ok-bg);
}

.seguimiento-tabla :is(th, td):last-child {
  background: var(--manana-bg);
  font-weight: 700;
}

.seguimiento-tabla input {
  width: 100%;
  margin: 0;
  padding: 8px 10px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--panel);
  color: var(--text);
  font: inherit;
  font-size: 18px;
  font-weight: 600;
  text-align: right;
  appearance: textfield;
}

.seguimiento-tabla input::placeholder {
  color: var(--text-3);
  font-weight: 500;
}

.seguimiento-tabla input::-webkit-outer-spin-button,
.seguimiento-tabla input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.seguimiento-tabla input:focus {
  outline: 2px solid var(--accent);
  border-color: var(--accent);
}

.fila-ratio th,
.fila-ratio td {
  font-weight: 700;
}

.hora-vacia {
  color: var(--text-3);
  font-weight: 400;
}

@media (max-width: 720px) {
  .productividad-par {
    grid-template-columns: 1fr;
  }
}
</style>
