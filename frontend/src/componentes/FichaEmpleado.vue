<script setup>
import { onMounted, ref, watch } from "vue";
import { fichaTrabajador } from "../api/usuarios.js";
import { fechaVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  login: { type: String, required: true },
});

const MESES = [
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

const anio = ref(new Date().getFullYear());
const ficha = ref(null);
const error = ref("");

const contadores = [
  { clave: "vacaciones", texto: "Vacaciones" },
  { clave: "bajas", texto: "Bajas" },
  { clave: "permisos", texto: "Permisos" },
  { clave: "festivos", texto: "Festivos trabajados" },
  { clave: "sabados", texto: "Sábados trabajados" },
];

function horasVisibles(valor) {
  return Number(valor).toLocaleString("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
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

function totalAnual() {
  if (!ficha.value) {
    return 0;
  }
  return ficha.value.horas_por_mes.reduce((suma, horas) => suma + Number(horas), 0);
}

function anchoMes(horas) {
  const maximo = Math.max(...ficha.value.horas_por_mes.map(Number));
  if (maximo <= 0) {
    return "0%";
  }
  return `${(Number(horas) / maximo) * 100}%`;
}

function numeroDe(clave) {
  const datos = ficha.value;
  if (!datos) {
    return 0;
  }
  if (clave === "vacaciones") {
    return datos.ausencias.V;
  }
  if (clave === "bajas") {
    return datos.ausencias.B;
  }
  if (clave === "permisos") {
    return datos.ausencias.P;
  }
  if (clave === "festivos") {
    return datos.festivos_trabajados;
  }
  return datos.sabados_trabajados;
}

async function cargar() {
  const pedido = Number(anio.value);
  if (!Number.isInteger(pedido) || pedido < 1) {
    return;
  }
  error.value = "";
  try {
    const datos = await fichaTrabajador(props.token, props.login, pedido);
    if (Number(anio.value) === pedido) {
      ficha.value = datos;
    }
  } catch (causa) {
    ficha.value = null;
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar la ficha";
  }
}

watch(anio, cargar);
watch(() => props.login, cargar);
onMounted(cargar);
</script>

<template>
  <section class="ficha">
    <header class="ficha-cabecera">
      <div>
        <h1>{{ ficha?.nombre || "Ficha" }}</h1>
        <p v-if="ficha">{{ ficha.departamento }} · {{ ficha.grupo }}</p>
      </div>
      <label class="analisis-filtro">
        Año
        <input v-model="anio" class="equipo-grupo" type="number" min="1" max="9999" />
      </label>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else-if="ficha">
      <p class="ficha-anual">
        Total anual
        <strong>{{ horasVisibles(totalAnual()) }}</strong>
      </p>
      <div class="ficha-meses">
        <article v-for="(mes, indice) in MESES" :key="mes" class="tarjeta analisis-kpi ficha-mes">
          <span class="ficha-mes-nombre">{{ mes }}</span>
          <strong class="ficha-mes-horas">{{ horasVisibles(ficha.horas_por_mes[indice]) }}</strong>
          <span class="ficha-mes-pista">
            <span
              v-if="Number(ficha.horas_por_mes[indice]) > 0"
              class="ficha-mes-barra"
              :style="{ width: anchoMes(ficha.horas_por_mes[indice]) }"
            ></span>
          </span>
        </article>
      </div>
      <div class="ficha-contadores">
        <div v-for="item in contadores" :key="item.clave" class="tarjeta analisis-kpi">
          <span class="tarjeta-nombre">{{ numeroDe(item.clave) }}</span>
          <span class="tarjeta-recuento">{{ item.texto }}</span>
        </div>
      </div>
      <section class="panel">
        <header class="panel-cabecera">
          <h2>Ajustes</h2>
        </header>
        <p v-if="!ficha.ajustes.length" class="panel-vacio">Sin ajustes registrados.</p>
        <ul v-else class="panel-filas">
          <li v-for="(ajuste, indice) in ficha.ajustes" :key="`${ajuste.fecha}-${indice}`">
            <span class="persona-datos">
              <strong>{{ fechaVisible(ajuste.fecha) }} · {{ horasConSigno(ajuste.horas) }}</strong>
              <span>{{ ajuste.motivo }}</span>
            </span>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>
