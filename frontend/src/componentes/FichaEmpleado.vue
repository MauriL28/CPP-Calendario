<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { fichaTrabajador } from "../api/usuarios.js";
import { fechaVisible } from "../fechas.js";
import LeyendaTurnos from "./LeyendaTurnos.vue";

const props = defineProps({
  token: { type: String, required: true },
  login: { type: String, required: true },
  volver: { type: Boolean, default: false },
  textoVolver: { type: String, default: "← Mi horario" },
});

const emit = defineEmits(["volver"]);

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
const ajustesAbiertos = ref(false);

const DIAS_CORTOS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
const AUSENCIAS = {
  L: "libranza",
  D: "domingo",
  V: "vacaciones",
  B: "baja",
  F: "festivo",
  P: "permiso",
  SR: "vacaciones",
  FR: "vacaciones",
  HS: "permiso",
  PEND: "permiso",
  ST: "festivo",
  FT: "festivo",
};
const contadores = [
  { clave: "vacaciones", texto: "Vacaciones" },
  { clave: "bajas", texto: "Bajas" },
  { clave: "permisos", texto: "Permisos" },
  { clave: "festivos", texto: "Festivos trabajados" },
  { clave: "sabados", texto: "Sábados trabajados" },
];

const AUSENCIAS_EXTRA = [
  { codigo: "SR", texto: "Sábado recuperado" },
  { codigo: "FR", texto: "Festivo recuperado" },
  { codigo: "HS", texto: "Horas sindicales" },
  { codigo: "PEND", texto: "Pendientes año anterior" },
  { codigo: "ST", texto: "Sábado trabajado" },
  { codigo: "FT", texto: "Festivo trabajado" },
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
  return serieMes().reduce((suma, horas) => suma + Number(horas), 0);
}

function serieMes() {
  const realizadas = ficha.value?.horas_realizadas_por_mes;
  if (Array.isArray(realizadas) && realizadas.length) {
    return realizadas;
  }
  return ficha.value.horas_por_mes;
}

function anchoMes(horas) {
  const maximo = Math.max(...serieMes().map(Number));
  if (maximo <= 0) {
    return "0%";
  }
  return `${(Number(horas) / maximo) * 100}%`;
}

const muestraConvenio = computed(() => ficha.value?.horas_realizadas != null);

const claseSaldo = computed(() => {
  const saldo = Number(ficha.value?.saldo);
  if (saldo > 0) {
    return "ficha-saldo-exceso";
  }
  if (saldo < 0) {
    return "ficha-saldo-pendiente";
  }
  return "";
});

const notaSaldo = computed(() => {
  const saldo = Number(ficha.value?.saldo);
  if (saldo > 0) {
    return "Exceso";
  }
  if (saldo < 0) {
    return "Pendiente";
  }
  return "";
});

const contadoresExtra = computed(() => {
  const dias = ficha.value?.dias;
  if (!dias?.length) {
    return [];
  }
  const cuentas = Object.fromEntries(AUSENCIAS_EXTRA.map((item) => [item.codigo, 0]));
  for (const dia of dias) {
    const codigo = String(dia.texto || "").trim().split(/\s+/)[0];
    if (codigo in cuentas) {
      cuentas[codigo] += 1;
    }
  }
  return AUSENCIAS_EXTRA.filter((item) => cuentas[item.codigo] > 0).map((item) => ({
    ...item,
    numero: cuentas[item.codigo],
  }));
});

function fechaImpresion() {
  return new Date().toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
}

function imprimir() {
  window.print();
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

function isoLocal(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function lineasHorario(texto) {
  const corte = String(texto).indexOf("-");
  if (corte < 1 || corte >= texto.length - 1) {
    return null;
  }
  return [`${texto.slice(0, corte)}-`, texto.slice(corte + 1)];
}

function familiaTexto(texto) {
  if (!texto) {
    return "";
  }
  if (AUSENCIAS[texto]) {
    return AUSENCIAS[texto];
  }
  const [horaTexto, minutoTexto = "0"] = texto.split("-")[0].split(":");
  const inicio = Number(horaTexto) * 60 + Number(minutoTexto);
  if (Number.isNaN(inicio)) {
    return "";
  }
  if (inicio >= 22 * 60 || inicio < 6 * 60) {
    return "noche";
  }
  if (inicio < 14 * 60) {
    return "manana";
  }
  return "tarde";
}

const mesesCalendario = computed(() => {
  const lista = ficha.value?.dias;
  if (!lista?.length) {
    return [];
  }
  const porFecha = new Map(lista.map((dia) => [dia.fecha, dia]));
  const anioPedido = Number(anio.value);
  return MESES.map((nombre, indice) => {
    const primero = new Date(anioPedido, indice, 1);
    const ultimo = new Date(anioPedido, indice + 1, 0);
    const cursor = new Date(primero);
    cursor.setDate(primero.getDate() - ((primero.getDay() + 6) % 7));
    const fin = new Date(ultimo);
    fin.setDate(ultimo.getDate() + ((7 - ultimo.getDay()) % 7));
    const semanas = [];
    while (cursor <= fin) {
      const dias = [];
      let semana = null;
      for (let columna = 0; columna < 7; columna += 1) {
        const fecha = isoLocal(cursor);
        const dato = porFecha.get(fecha);
        if (dato) {
          semana = dato.semana;
        }
        const enMes = cursor.getMonth() === indice;
        dias.push(
          enMes
            ? {
                fecha,
                numero: cursor.getDate(),
                texto: dato?.texto || "",
                lineas: lineasHorario(dato?.texto || ""),
              }
            : null,
        );
        cursor.setDate(cursor.getDate() + 1);
      }
      semanas.push({ numero: semana ?? "", dias });
    }
    return { nombre, semanas };
  });
});

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
    <p class="ficha-impresion">
      <span>STEF</span>
      <span>{{ fechaImpresion() }}</span>
    </p>
    <header class="ficha-cabecera">
      <button v-if="volver" type="button" class="primario ficha-volver" @click="emit('volver')">{{ textoVolver }}</button>
      <div>
        <h1>{{ ficha?.nombre || "Ficha" }}</h1>
        <p v-if="ficha">{{ ficha.departamento }} · {{ ficha.grupo }}</p>
      </div>
      <div class="ficha-acciones">
        <label class="analisis-filtro">
          Año
          <input v-model="anio" class="equipo-grupo ficha-anio-campo" type="number" min="1" max="9999" />
          <span class="ficha-anio-texto">{{ anio }}</span>
        </label>
        <button type="button" class="ficha-imprimir" @click="imprimir">Imprimir</button>
      </div>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else-if="ficha">
      <p class="ficha-anual">
        {{ muestraConvenio ? "Total anual (con ausencias computables y ajustes)" : "Total anual (solo turnos)" }}
        <strong>{{ horasVisibles(totalAnual()) }}</strong>
      </p>
      <div v-if="muestraConvenio" class="ficha-convenio">
        <article class="tarjeta analisis-kpi">
          <span class="ficha-mes-nombre">Convenio</span>
          <strong class="ficha-mes-horas">{{ horasVisibles(ficha.convenio_anual) }}</strong>
        </article>
        <article class="tarjeta analisis-kpi">
          <span class="ficha-mes-nombre">Saldo</span>
          <strong class="ficha-mes-horas" :class="claseSaldo">{{ horasConSigno(ficha.saldo) }}</strong>
          <span v-if="notaSaldo" class="ficha-saldo-nota" :class="claseSaldo">{{ notaSaldo }}</span>
        </article>
      </div>
      <div class="ficha-meses">
        <article v-for="(mes, indice) in MESES" :key="mes" class="tarjeta analisis-kpi ficha-mes">
          <span class="ficha-mes-nombre">{{ mes }}</span>
          <strong class="ficha-mes-horas">{{ horasVisibles(serieMes()[indice]) }}</strong>
          <span class="ficha-mes-pista">
            <span
              v-if="Number(serieMes()[indice]) > 0"
              class="ficha-mes-barra"
              :style="{ width: anchoMes(serieMes()[indice]) }"
            ></span>
          </span>
        </article>
      </div>
      <div class="ficha-contadores">
        <div v-for="item in contadores" :key="item.clave" class="tarjeta analisis-kpi">
          <span class="tarjeta-nombre">{{ numeroDe(item.clave) }}</span>
          <span class="tarjeta-recuento">{{ item.texto }}</span>
        </div>
        <div v-for="item in contadoresExtra" :key="item.codigo" class="tarjeta analisis-kpi">
          <span class="tarjeta-nombre">{{ item.numero }}</span>
          <span class="tarjeta-recuento">{{ item.texto }}</span>
        </div>
      </div>
      <section class="panel ficha-ajustes">
        <button
          type="button"
          class="panel-cabecera ficha-ajustes-cabecera"
          :aria-expanded="ajustesAbiertos"
          @click="ajustesAbiertos = !ajustesAbiertos"
        >
          <h2>Ajustes ({{ ficha.ajustes.length }})</h2>
          <span class="ficha-ajustes-flecha" :class="{ abierta: ajustesAbiertos }" aria-hidden="true">›</span>
        </button>
        <template v-if="ajustesAbiertos">
          <p v-if="!ficha.ajustes.length" class="panel-vacio">Sin ajustes este año</p>
          <ul v-else class="panel-filas">
            <li v-for="(ajuste, indice) in ficha.ajustes" :key="`${ajuste.fecha}-${indice}`">
              <span class="persona-datos">
                <strong>{{ fechaVisible(ajuste.fecha) }} · {{ horasConSigno(ajuste.horas) }}</strong>
                <span>{{ ajuste.motivo }}</span>
              </span>
            </li>
          </ul>
        </template>
      </section>
      <div class="ficha-calendario">
        <h2 class="ficha-calendario-titulo">Calendario anual</h2>
        <header class="ficha-calendario-cabecera">
          <div>
            <p class="ficha-calendario-fecha">{{ fechaImpresion() }}</p>
            <h1>{{ ficha.nombre }}</h1>
          </div>
          <div class="ficha-firma">
            <strong>RECIBÍ FIRMA Y FECHA:</strong>
            <span aria-hidden="true"></span>
          </div>
        </header>
        <div class="ficha-calendario-meses">
          <article v-for="mes in mesesCalendario" :key="mes.nombre">
            <h2>{{ mes.nombre }}</h2>
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th v-for="dia in DIAS_CORTOS" :key="dia">{{ dia }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(semana, indice) in mes.semanas" :key="`${mes.nombre}-${indice}`">
                  <th>{{ semana.numero }}</th>
                  <td
                    v-for="(dia, columna) in semana.dias"
                    :key="`${mes.nombre}-${indice}-${columna}`"
                    :class="dia && familiaTexto(dia.texto) ? `turno-${familiaTexto(dia.texto)}` : ''"
                    :title="dia?.texto || undefined"
                  >
                    <template v-if="dia">
                      <span class="ficha-dia-num">{{ dia.numero }}</span>
                      <span
                        v-if="dia.texto"
                        class="ficha-dia-texto"
                        :class="{ 'ficha-dia-horario': dia.lineas }"
                      >
                        <template v-if="dia.lineas">{{ dia.lineas[0] }}<br>{{ dia.lineas[1] }}</template>
                        <template v-else>{{ dia.texto }}</template>
                      </span>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>
        <LeyendaTurnos />
      </div>
    </template>
  </section>
</template>

<style scoped>
.ficha-cabecera:has(.ficha-volver) {
  justify-content: flex-start;
}

button.primario.ficha-volver {
  order: 2;
  margin-left: auto;
  padding: 10px 22px;
  font-size: 16px;
  font-weight: 700;
  min-height: 44px;
}

.ficha-cabecera:has(.ficha-volver) .ficha-acciones {
  order: 3;
}

@media (max-width: 599px) {
  .ficha-cabecera:has(.ficha-volver) {
    flex-direction: column;
    align-items: stretch;
  }

  button.primario.ficha-volver {
    order: -1;
    width: 100%;
    margin-left: 0;
  }
}

@media print {
  .ficha-volver {
    display: none !important;
  }
}

button.panel-cabecera.ficha-ajustes-cabecera {
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

button.panel-cabecera.ficha-ajustes-cabecera[aria-expanded="true"] {
  border-bottom: 1px solid var(--border);
}

button.panel-cabecera.ficha-ajustes-cabecera:hover {
  border-bottom-color: var(--border);
  background: transparent;
}

.ficha-ajustes-flecha {
  margin-left: auto;
  color: var(--text-3);
  font-size: 18px;
  line-height: 1;
  transition: transform 0.15s;
}

.ficha-ajustes-flecha.abierta {
  transform: rotate(90deg);
}
</style>
