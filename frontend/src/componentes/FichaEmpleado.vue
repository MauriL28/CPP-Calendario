<script setup>
import { computed, onMounted, ref, watch } from "vue";
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

const DIAS_CORTOS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
const AUSENCIAS = {
  L: "libranza",
  D: "domingo",
  V: "vacaciones",
  B: "baja",
  F: "festivo",
  P: "permiso",
};
const leyenda = [
  { id: "manana", nombre: "Mañana" },
  { id: "tarde", nombre: "Tarde" },
  { id: "noche", nombre: "Noche" },
  { id: "libranza", nombre: "Libranza" },
  { id: "domingo", nombre: "Domingo" },
  { id: "vacaciones", nombre: "Vacaciones" },
  { id: "baja", nombre: "Baja" },
  { id: "festivo", nombre: "Festivo" },
  { id: "permiso", nombre: "Permiso" },
];

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
                  >
                    <template v-if="dia">
                      <span class="ficha-dia-num">{{ dia.numero }}</span>
                      <span v-if="dia.texto" class="ficha-dia-texto">{{ dia.texto }}</span>
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>
        <ul class="leyenda">
          <li v-for="item in leyenda" :key="item.id">
            <span class="muestra" :class="`turno-${item.id}`"></span>
            {{ item.nombre }}
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
