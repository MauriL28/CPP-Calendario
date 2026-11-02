<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { analisisFichajes, exportarAnalisis } from "../api/fichajes.js";
import { delegacionVisible } from "../fechas.js";

const props = defineProps({
  token: { type: String, required: true },
  mando: { type: Boolean, default: false },
  departamentoId: { type: String, default: "" },
});

const departamentos = ref([]);
const delegacion = ref("");
const codigo = ref("");
const estado = ref("");
const desde = ref("");
const hasta = ref("");
const datos = ref(null);
const error = ref("");

const estados = [
  { valor: "", texto: "Todos los estados" },
  { valor: "ok", texto: "Correctos" },
  { valor: "descuadre", texto: "Descuadres" },
  { valor: "sin_plan", texto: "Sin plan" },
  { valor: "sin_emparejar", texto: "Sin emparejar" },
];

const etiquetas = {
  ok: "Correcto",
  descuadre: "Descuadre",
  sin_plan: "Sin plan",
  sin_emparejar: "Sin emparejar",
};

const kpis = [
  { clave: "total", texto: "Total" },
  { clave: "ok", texto: "Correctos" },
  { clave: "descuadre", texto: "Descuadres" },
  { clave: "sin_plan", texto: "Sin plan" },
  { clave: "sin_emparejar", texto: "Sin emparejar" },
];

const delegaciones = computed(() => {
  const vistas = [];
  const codigos = new Set();
  for (const item of departamentos.value) {
    if (!codigos.has(item.delegacion)) {
      codigos.add(item.delegacion);
      vistas.push(item.delegacion);
    }
  }
  return vistas;
});

const departamentosUnicos = computed(() => {
  const vistos = new Map();
  for (const item of departamentos.value) {
    if (!vistos.has(item.codigo)) {
      vistos.set(item.codigo, { codigo: item.codigo, nombre: item.nombre });
    }
  }
  return [...vistos.values()];
});

function fechaVisible(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function textoMinutos(valor, conSigno) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  const numero = Number(valor);
  const signo = conSigno && numero > 0 ? "+" : numero < 0 ? "-" : "";
  const absoluto = Math.abs(numero);
  const horas = Math.floor(absoluto / 60);
  const minutos = absoluto % 60;
  if (!horas) {
    return `${signo}${minutos} min`;
  }
  return `${signo}${horas} h ${String(minutos).padStart(2, "0")} min`;
}

function minutosReloj(hora) {
  const [horas, minutos] = hora.split(":").map(Number);
  return horas * 60 + minutos;
}

function diaSiguiente(valor) {
  return Number(valor) === 1;
}

function minutosEnEscala(hora, dia) {
  return minutosReloj(hora) + (diaSiguiente(dia) ? 24 * 60 : 0);
}

function cruzaMedianoche(entrada, salida) {
  if (!entrada || !salida) {
    return 0;
  }
  return minutosReloj(salida) < minutosReloj(entrada) ? 1 : 0;
}

function rango(inicio, fin, diaFin) {
  if (!inicio || !fin) {
    return "—";
  }
  const salida = diaSiguiente(diaFin) ? `${fin} (+1)` : fin;
  return `${inicio}–${salida}`;
}

function desvio(previsto, fichado) {
  if (!previsto || !fichado) {
    return null;
  }
  return minutosReloj(fichado) - minutosReloj(previsto);
}

function desvioSalida(fila) {
  if (!fila.salida_prevista || !fila.salida_fichada) {
    return null;
  }
  const previsto = minutosEnEscala(
    fila.salida_prevista,
    cruzaMedianoche(fila.entrada_prevista, fila.salida_prevista),
  );
  const fichado = minutosEnEscala(fila.salida_fichada, fila.salida_dia_offset);
  return fichado - previsto;
}

function textoDesvio(minutos, llegada) {
  if (minutos === null) {
    return "—";
  }
  const verbo = llegada ? "entró" : "salió";
  if (minutos === 0) {
    return `${verbo} a la hora`;
  }
  const cuanto = textoMinutos(Math.abs(minutos), false);
  if (llegada) {
    return `${verbo} ${cuanto} ${minutos > 0 ? "tarde" : "antes"}`;
  }
  return `${verbo} ${cuanto} ${minutos > 0 ? "después" : "antes"}`;
}

function hayPrevisto(fila) {
  return Boolean(fila.entrada_prevista && fila.salida_prevista);
}

function desvioGrande(fila) {
  const entrada = desvio(fila.entrada_prevista, fila.entrada_fichada);
  const salida = desvioSalida(fila);
  return (entrada !== null && Math.abs(entrada) > 20) || (salida !== null && Math.abs(salida) > 20);
}

function claseEstado(coincide) {
  if (coincide === "ok") {
    return "estado-ok";
  }
  if (coincide === "descuadre") {
    return "estado-descuadre";
  }
  return "estado-aviso";
}

async function cargarDepartamentos() {
  departamentos.value = await listar(props.token);
}

function filtrosActuales() {
  const filtros = {
    coincide: estado.value,
    desde: desde.value,
    hasta: hasta.value,
  };
  if (props.mando) {
    filtros.departamento = props.departamentoId;
    return filtros;
  }
  filtros.delegacion = delegacion.value;
  filtros.codigo = codigo.value;
  return filtros;
}

async function exportar() {
  error.value = "";
  try {
    await exportarAnalisis(props.token, filtrosActuales());
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo exportar el análisis";
  }
}

async function cargar() {
  error.value = "";
  try {
    datos.value = await analisisFichajes(props.token, filtrosActuales());
  } catch (causa) {
    datos.value = null;
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar el análisis";
  }
}

watch([delegacion, codigo, estado, desde, hasta], cargar);

watch(
  () => props.departamentoId,
  () => {
    if (!props.mando) {
      return;
    }
    datos.value = null;
    cargar();
  },
);

onMounted(async () => {
  if (props.mando) {
    await cargar();
    return;
  }
  try {
    await cargarDepartamentos();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
  if (!delegacion.value && !codigo.value) {
    await cargar();
  }
});
</script>

<template>
  <section class="analisis">
    <header class="equipo-intro">
      <h1>Análisis</h1>
      <p>Días ya cruzados con el turno. Una incidencia no entra, porque aún no tiene horas.</p>
    </header>
    <div class="equipo-barra">
      <label v-if="!mando" class="analisis-filtro">
        Delegación
        <select v-model="delegacion" class="equipo-grupo">
          <option value="">Todas las delegaciones</option>
          <option v-for="codigoSede in delegaciones" :key="codigoSede" :value="codigoSede">
            {{ delegacionVisible(codigoSede) }}
          </option>
        </select>
      </label>
      <label v-if="!mando" class="analisis-filtro">
        Departamento
        <select v-model="codigo" class="equipo-grupo">
          <option value="">Todos los departamentos</option>
          <option v-for="item in departamentosUnicos" :key="item.codigo" :value="item.codigo">
            {{ item.nombre }}
          </option>
        </select>
      </label>
      <label class="analisis-filtro">
        Estado
        <select v-model="estado" class="equipo-grupo">
          <option v-for="item in estados" :key="item.valor" :value="item.valor">{{ item.texto }}</option>
        </select>
      </label>
      <label class="analisis-filtro">
        Desde
        <input v-model="desde" class="equipo-buscar" type="date" />
      </label>
      <label class="analisis-filtro">
        Hasta
        <input v-model="hasta" class="equipo-buscar" type="date" />
      </label>
      <button type="button" class="primario" @click="exportar">Exportar</button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-else-if="datos">
      <div class="rejilla-deptos" :class="{ 'analisis-admin': !mando }">
        <div v-for="kpi in kpis" :key="kpi.clave" class="tarjeta analisis-kpi">
          <span class="tarjeta-nombre">{{ datos.totales[kpi.clave] }}</span>
          <span class="tarjeta-recuento">{{ kpi.texto }}</span>
        </div>
      </div>
      <section class="panel">
        <p v-if="!datos.filas.length" class="panel-vacio">Sin resultados con ese filtro.</p>
        <table v-else class="equipo">
          <thead>
            <tr>
              <th>Trabajador</th>
              <th>Fecha</th>
              <th>Previsto</th>
              <th>Fichado</th>
              <th>Pausa</th>
              <th>Diferencia</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fila in datos.filas" :key="`${fila.nombre}-${fila.fecha}-${fila.coincide}`">
              <td>
                <span class="persona-datos">
                  <strong>{{ fila.nombre }}</strong>
                  <span v-if="fila.departamento">{{ fila.departamento }}</span>
                </span>
              </td>
              <td>{{ fechaVisible(fila.fecha) }}</td>
              <td>
                <span class="persona-datos">
                  <strong>{{ textoMinutos(fila.previsto_min, false) }}</strong>
                  <span v-if="hayPrevisto(fila)">{{ rango(fila.entrada_prevista, fila.salida_prevista, cruzaMedianoche(fila.entrada_prevista, fila.salida_prevista)) }}</span>
                </span>
              </td>
              <td>
                <span class="persona-datos">
                  <strong>{{ textoMinutos(fila.fichado_min, false) }}</strong>
                  <span>{{ rango(fila.entrada_fichada, fila.salida_fichada, fila.salida_dia_offset) }}</span>
                  <span v-if="hayPrevisto(fila)" :class="{ 'analisis-tarde': desvioGrande(fila) }">
                    {{ textoDesvio(desvio(fila.entrada_prevista, fila.entrada_fichada), true) }} · {{ textoDesvio(desvioSalida(fila), false) }}
                  </span>
                </span>
              </td>
              <td>{{ textoMinutos(fila.pausa_min, false) }}</td>
              <td>{{ textoMinutos(fila.diferencia_min, true) }}</td>
              <td>
                <span class="estado-pastilla" :class="claseEstado(fila.coincide)">
                  {{ etiquetas[fila.coincide] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
</template>

<style scoped>
.analisis-admin {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.analisis-admin .analisis-kpi {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 12px;
}

.analisis-admin .tarjeta-nombre {
  font-size: 18px;
  font-weight: 700;
}

.analisis-admin .tarjeta-recuento {
  margin-top: 0;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .analisis-admin {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 600px) {
  .analisis-admin {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
