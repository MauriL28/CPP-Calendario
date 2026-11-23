<script setup>
import { computed, onMounted, ref } from "vue";
import { mes, semana } from "../api/turnos.js";
import {
  formatoEuros,
  horasDiurnas,
  horasNocturnas,
  importeTrabajador,
  tieneCoste,
  tieneTarifaNocturna,
  totalGrupo,
} from "../costes.js";
import { fechaVisible, lunesDe, rangoSemana, sumarDias } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  departamentoId: { type: String, default: "" },
});

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

const modo = ref("semana");
const periodo = ref(null);
const anterior = ref(null);
const semanaDesde = ref("");
const anioMes = ref(0);
const numeroMes = ref(0);
const error = ref("");
let generacion = 0;

const tituloMes = computed(() => `${mesesLargos[numeroMes.value - 1] || ""} ${anioMes.value}`.trim());
const ett = computed(() => ettDe(periodo.value));
const resumen = computed(() => totalGrupo(ett.value));
const comparacion = computed(() => {
  if (!anterior.value || !periodo.value) {
    return null;
  }
  const ahora = totalGrupo(ettDe(periodo.value));
  const antes = totalGrupo(ettDe(anterior.value));
  return textoDelta(ahora.total - antes.total);
});
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

function ettDe(datos) {
  return (datos?.trabajadores || [])
    .filter((trabajador) => trabajador.grupo === "ETT")
    .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
}

function mesPrevio(anio, mesNumero) {
  if (mesNumero <= 1) {
    return { anio: anio - 1, mes: 12 };
  }
  return { anio, mes: mesNumero - 1 };
}

function partes(iso) {
  return iso.split("-").map(Number);
}

function horasVisibles(valor) {
  return `${Number(valor.toFixed(2)).toLocaleString("es-ES")} h`;
}

function textoDelta(valor) {
  const cantidad = Number(valor.toFixed(2));
  if (cantidad === 0) {
    return `(±${formatoEuros(0)})`;
  }
  const signo = cantidad > 0 ? "+" : "-";
  return `(${signo}${formatoEuros(Math.abs(cantidad))})`;
}

function textoCosteHora(trabajador) {
  if (!tieneCoste(trabajador)) {
    return "—";
  }
  return formatoEuros(trabajador.coste);
}

function textoTarifa(valor, presente) {
  if (!presente) {
    return "—";
  }
  return formatoEuros(valor);
}

function textoImporte(trabajador) {
  const { importe } = importeTrabajador(trabajador);
  return importe === null ? "—" : formatoEuros(importe);
}

function vigente(solicitud) {
  return solicitud === generacion;
}

async function pedirAnterior(solicitud) {
  try {
    let datos;
    if (modo.value === "mes") {
      const previo = mesPrevio(anioMes.value, numeroMes.value);
      datos = await mes(props.token, previo.anio, previo.mes, false, props.departamentoId);
    } else {
      datos = await semana(props.token, sumarDias(semanaDesde.value, -7), false, props.departamentoId);
    }
    if (!vigente(solicitud)) {
      return;
    }
    anterior.value = datos;
  } catch {
    if (vigente(solicitud)) {
      anterior.value = null;
    }
  }
}

async function cargar(desde) {
  const solicitud = ++generacion;
  error.value = "";
  anterior.value = null;
  try {
    const datos = await semana(props.token, desde, false, props.departamentoId);
    if (!vigente(solicitud)) {
      return;
    }
    periodo.value = datos;
    semanaDesde.value = datos.desde;
    await pedirAnterior(solicitud);
  } catch (causa) {
    if (!vigente(solicitud)) {
      return;
    }
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

async function cargarMes(anio, mesNumero) {
  const solicitud = ++generacion;
  error.value = "";
  anterior.value = null;
  try {
    const datos = await mes(props.token, anio, mesNumero, false, props.departamentoId);
    if (!vigente(solicitud)) {
      return;
    }
    periodo.value = datos;
    anioMes.value = anio;
    numeroMes.value = mesNumero;
    await pedirAnterior(solicitud);
  } catch (causa) {
    if (!vigente(solicitud)) {
      return;
    }
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar el mes";
  }
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

onMounted(() => {
  cargar(lunesDe(new Date()));
});
</script>

<template>
  <section v-if="periodo" class="semana lectura">
    <div class="semana-nav">
      <div class="vistas modo-vista">
        <button type="button" :class="{ activo: modo === 'semana' }" @click="cambiarModo('semana')">
          Semana
        </button>
        <button type="button" :class="{ activo: modo === 'mes' }" @click="cambiarModo('mes')">
          Mes
        </button>
      </div>
      <template v-if="modo === 'semana'">
        <button type="button" @click="cargar(sumarDias(semanaDesde, -7))">Semana anterior</button>
        <span class="rango">{{ rangoSemana(periodo.desde, periodo.dias[6]) }}</span>
        <button type="button" @click="cargar(sumarDias(semanaDesde, 7))">Semana siguiente</button>
      </template>
      <template v-else>
        <button type="button" @click="moverMes(-1)">Mes anterior</button>
        <span class="rango">{{ tituloMes }}</span>
        <button type="button" @click="moverMes(1)">Mes siguiente</button>
      </template>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="!ett.length" class="panel-vacio">No hay trabajadores ETT en este departamento.</p>
    <template v-else>
      <div class="cuadrante-scroll costes-scroll">
        <table class="cuadrante">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Sección</th>
              <th>Horas diurnas</th>
              <th>Horas nocturnas</th>
              <th>Tarifa diurna</th>
              <th>Tarifa nocturna</th>
              <th>Importe</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trabajador in ett" :key="trabajador.login">
              <th>{{ trabajador.nombre }}</th>
              <td>{{ trabajador.seccion || "—" }}</td>
              <td>{{ horasVisibles(horasDiurnas(trabajador)) }}</td>
              <td>{{ horasVisibles(horasNocturnas(trabajador)) }}</td>
              <td :class="{ 'coste-vacio': !tieneCoste(trabajador) }">{{ textoCosteHora(trabajador) }}</td>
              <td :class="{ 'coste-vacio': !tieneTarifaNocturna(trabajador) }">
                {{ textoTarifa(trabajador.tarifa_nocturna, tieneTarifaNocturna(trabajador)) }}
              </td>
              <td :class="{ 'coste-vacio': importeTrabajador(trabajador).importe === null }">
                {{ textoImporte(trabajador) }}<span
                  v-if="importeTrabajador(trabajador).sinTarifaNocturna"
                  title="Sin tarifa nocturna: las horas nocturnas se calculan a tarifa diurna"
                >*</span>
              </td>
            </tr>
          </tbody>
          <tfoot>
            <tr>
              <td>Total del periodo</td>
              <td></td>
              <td></td>
              <td></td>
              <td></td>
              <td></td>
              <td>
                <span>{{ formatoEuros(resumen.total) }}</span>
                <span v-if="comparacion" class="delta" :title="tituloComparacion">{{ comparacion }}</span>
                <span class="coste-nota">({{ resumen.sinCoste }} sin coste)</span>
                <span v-if="resumen.sinTarifaNocturna" class="coste-nota">
                  ({{ resumen.sinTarifaNocturna }} sin tarifa nocturna)
                </span>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p class="cobertura-nota">
        Cuentan los turnos con horario y los ST/FT. Las horas nocturnas son las del turno completo, sin superar las planificadas; la pausa no se descuenta de la franja nocturna.
      </p>
    </template>
  </section>
</template>

<style scoped>
.costes-scroll {
  overflow-x: auto;
  max-width: 100%;
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
</style>
