<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { borrar as borrarSeguimiento, obtener, guardar as guardarSeguimiento } from "../api/seguimiento.js";
import { semana } from "../api/turnos.js";
import { horasPeriodo } from "../costes.js";
import { lunesDe, rangoSemana, sumarDias } from "../fechas.js";
import Aviso from "./Aviso.vue";
import NavegacionPeriodo from "./NavegacionPeriodo.vue";
import { celdasDesdeDetalle, detalleDesdeCeldas, parsearPrevision, ratioSeguimiento } from "../seguimiento.js";

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const DIAS_LARGOS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const CELDAS_VACIAS = ["", "", "", "", "", ""];

const props = defineProps({
  token: { type: String, required: true },
  departamentoId: { type: String, default: "" },
});

const tabla = ref(null);
const periodo = ref(null);
const semanaDesde = ref("");
const celdas = ref([...CELDAS_VACIAS]);
const nombre = ref("");
const totalDeclarado = ref(null);
const error = ref("");
const falloPegado = ref("");
const aviso = ref("");
const avisoOculto = ref("");
let generacion = 0;
let avisoTimer = 0;

const etiqueta = computed(() => {
  if (periodo.value?.desde && periodo.value?.dias?.[6]) {
    return rangoSemana(periodo.value.desde, periodo.value.dias[6]);
  }
  if (!semanaDesde.value) {
    return "";
  }
  return rangoSemana(semanaDesde.value, sumarDias(semanaDesde.value, 6));
});

const diasKg = computed(() => celdas.value.map(kilosDeCelda));
const totalKg = computed(() => {
  if (diasKg.value.every((dia) => dia === null)) {
    return null;
  }
  return diasKg.value.reduce((suma, dia) => suma + (dia ?? 0), 0);
});
const horasDias = computed(() => DIAS.map((_, indice) => horasDe(indice)));
const horasSemana = computed(() => horasDe(null));
const horasDomingo = computed(() => horasDe(6));
const resultado = computed(() => {
  if (totalKg.value === null) {
    return { ratio: null, motivo: "" };
  }
  return ratioSeguimiento(totalKg.value / 1000, horasSemana.value);
});
const avisoTotal = computed(() => {
  if (totalDeclarado.value === null || totalKg.value === null) {
    return "";
  }
  if (Math.abs(totalDeclarado.value - totalKg.value) > 0.001) {
    return "El total no coincide con la suma de los días.";
  }
  return "";
});
const avisos = computed(() => {
  const lista = diasKg.value.flatMap((kg, indice) => {
    if (!(kg > 0) || horasDias.value[indice] > 0) {
      return [];
    }
    return [`${DIAS_LARGOS[indice]}: ${toneladasVisibles(kg)} t sin horas planificadas`];
  });
  if (avisoTotal.value) {
    lista.push(avisoTotal.value);
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
  return numeroVisible(kg / 1000, 2);
}

function horasVisibles(valor) {
  return numeroVisible(valor, 2).replace(/,00$/, "").replace(/(\,\d)0$/, "$1");
}

function ratioCelda(kg, horas) {
  if (kg === null || !(horas > 0)) {
    return "—";
  }
  return numeroVisible(kg / 1000 / horas, 2);
}

function ratioVisible(valor) {
  return `${numeroVisible(valor, 2)} t/h`;
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

function vaciar() {
  celdas.value = [...CELDAS_VACIAS];
  nombre.value = "";
  totalDeclarado.value = null;
  falloPegado.value = "";
}

function aplicarDetalle(seguimiento) {
  const leido = celdasDesdeDetalle(seguimiento?.detalle, seguimiento?.fila_base);
  celdas.value = leido.dias;
  nombre.value = leido.nombre;
  const suma = leido.dias.reduce((total, dia) => total + (dia === "" ? 0 : Number(dia)), 0);
  totalDeclarado.value =
    leido.total !== null && Math.abs(leido.total - suma) > 0.001 ? leido.total : null;
}

function alEditar() {
  ocultarAviso();
  falloPegado.value = "";
  if (celdas.value.every((celda) => String(celda).trim() === "")) {
    nombre.value = "";
    totalDeclarado.value = null;
  }
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
  evento.preventDefault();
  const resultadoParseo = parsearPrevision(evento.clipboardData?.getData("text") ?? "");
  if (resultadoParseo.error) {
    falloPegado.value = resultadoParseo.error;
    return;
  }
  celdas.value = resultadoParseo.dias.map((dia) => String(dia));
  nombre.value = resultadoParseo.nombre;
  totalDeclarado.value = resultadoParseo.total;
  falloPegado.value = "";
  error.value = "";
  ocultarAviso();
}

async function cargar(desde) {
  const solicitud = ++generacion;
  error.value = "";
  falloPegado.value = "";
  ocultarAviso();
  vaciar();
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
    aplicarDetalle(seguimiento);
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
  const construido = detalleDesdeCeldas(celdas.value, nombre.value);
  if (construido.error) {
    error.value = construido.error;
    return;
  }
  const toneladas = Number((construido.total / 1000).toFixed(2));
  try {
    await guardarSeguimiento(props.token, semanaDesde.value, toneladas, props.departamentoId, {
      detalle: construido.detalle,
      fila_base: construido.fila_base,
    });
    nombre.value = construido.nombre;
    totalDeclarado.value = null;
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
    vaciar();
    return;
  }
  try {
    await borrarSeguimiento(props.token, semanaDesde.value, props.departamentoId);
    vaciar();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo borrar el seguimiento";
  }
}

onMounted(() => {
  window.addEventListener("paste", alPegar);
  cargar(lunesDe(new Date()));
});

onUnmounted(() => {
  window.removeEventListener("paste", alPegar);
  window.clearTimeout(avisoTimer);
});
</script>

<template>
  <section class="semana">
    <div class="semana-nav">
      <NavegacionPeriodo
        anterior="Semana anterior"
        siguiente="Semana siguiente"
        @anterior="cargar(sumarDias(semanaDesde || lunesDe(new Date()), -7))"
        @siguiente="cargar(sumarDias(semanaDesde || lunesDe(new Date()), 7))"
      >
        {{ etiqueta }}
      </NavegacionPeriodo>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <article v-if="totalKg !== null" class="panel productividad">
      <p class="productividad-titulo">Productividad prevista</p>
      <p class="productividad-valor">{{ resultado.ratio === null ? "—" : ratioVisible(resultado.ratio) }}</p>
      <p class="productividad-cuenta">
        {{ toneladasVisibles(totalKg) }} t ÷ {{ horasVisibles(horasSemana) }} h
        <span v-if="etiqueta"> · {{ etiqueta }}</span>
      </p>
      <p v-if="resultado.motivo" class="productividad-cuenta">{{ resultado.motivo }}</p>
    </article>
    <Aviso v-if="mostrarAvisos" :mensajes="avisos" @cerrar="cerrarAvisos" />
    <section class="seguimiento-entrada-marco">
      <h2>Datos de la semana (kg) · pega o escribe aquí</h2>
      <p v-if="totalKg === null" class="cobertura-nota seguimiento-pista">
        Copia la fila de previsión y pégala aquí con Ctrl+V
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
            <tr>
              <th>Kg</th>
              <td v-for="(dia, indice) in DIAS" :key="dia">
                <input
                  v-model="celdas[indice]"
                  type="number"
                  min="0"
                  step="1"
                  inputmode="numeric"
                  placeholder="kg"
                  :aria-label="`Previsión ${DIAS_LARGOS[indice]}`"
                  @input="alEditar"
                />
              </td>
              <td>{{ kilosVisibles(totalKg) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
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
            <th>Toneladas</th>
            <td v-for="(kg, indice) in diasKg" :key="DIAS[indice]">
              {{ kg === null ? "—" : toneladasVisibles(kg) }}
            </td>
            <td>{{ totalKg === null ? "—" : toneladasVisibles(totalKg) }}</td>
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
            <th>t/h</th>
            <td
              v-for="(kg, indice) in diasKg"
              :key="DIAS[indice]"
              :class="{ 'hora-vacia': !(horasDias[indice] > 0) }"
            >
              {{ ratioCelda(kg, horasDias[indice]) }}
            </td>
            <td>{{ ratioCelda(totalKg, horasSemana) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="horasDomingo > 0" class="cobertura-nota">
      El domingo tiene horas (ST/FT) y entran en el total de la semana.
    </p>
    <div class="seguimiento-acciones">
      <button class="primario" type="button" @click="guardar">Guardar</button>
      <button type="button" @click="borrar">Borrar</button>
      <span v-if="aviso" class="seguimiento-guardado" role="status">{{ aviso }}</span>
    </div>
  </section>
</template>

<style scoped>
.productividad {
  margin: 0 0 1rem;
  padding: 16px 18px;
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
  width: 16%;
}

.col-dia {
  width: 12%;
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
</style>
