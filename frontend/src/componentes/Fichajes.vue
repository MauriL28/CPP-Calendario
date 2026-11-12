<script setup>
import { computed, onActivated, ref } from "vue";
import { importarFichajes, listarImportaciones } from "../api/fichajes.js";

const props = defineProps({
  token: { type: String, required: true },
});

const emit = defineEmits(["ver-analisis"]);

const archivo = ref(null);
const entradaArchivo = ref(null);
const arrastrando = ref(false);
const enviando = ref(false);
const errorFichajes = ref("");
const resumen = ref(null);
const importaciones = ref(null);
const errorImportaciones = ref("");
const historialAbierto = ref(false);

const tamanoArchivo = computed(() => {
  if (!archivo.value) {
    return "";
  }
  const bytes = archivo.value.size;
  const mega = 1024 * 1024;
  const cantidad = bytes >= mega ? bytes / mega : bytes / 1024;
  const unidad = bytes >= mega ? "MB" : "KB";
  return `${cantidad.toLocaleString("es-ES", { maximumFractionDigits: 1 })} ${unidad}`;
});

function fechaCorta(iso) {
  if (!iso) {
    return "—";
  }
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

const textoPeriodo = computed(() => {
  if (!resumen.value) {
    return "";
  }
  const desde = resumen.value.fecha_desde;
  const hasta = resumen.value.fecha_hasta;
  if (!desde && !hasta) {
    return "Sin fechas en el archivo";
  }
  return `Periodo cargado: ${fechaCorta(desde)} → ${fechaCorta(hasta)}`;
});

function verAnalisis() {
  emit("ver-analisis");
}

function esXlsx(fichero) {
  return fichero.name.toLowerCase().endsWith(".xlsx");
}

function tomarArchivo(fichero) {
  if (!fichero) {
    return;
  }
  if (!esXlsx(fichero)) {
    archivo.value = null;
    errorFichajes.value = "El archivo tiene que ser .xlsx";
    return;
  }
  archivo.value = fichero;
  errorFichajes.value = "";
  resumen.value = null;
}

function alArchivo(evento) {
  tomarArchivo(evento.target.files?.[0] ?? null);
  evento.target.value = "";
}

function abrirArchivo() {
  entradaArchivo.value?.click();
}

function alSoltar(evento) {
  arrastrando.value = false;
  tomarArchivo(evento.dataTransfer?.files?.[0] ?? null);
}

function alSalirZona(evento) {
  if (evento.currentTarget.contains(evento.relatedTarget)) {
    return;
  }
  arrastrando.value = false;
}

function quitarArchivo() {
  archivo.value = null;
  errorFichajes.value = "";
  if (entradaArchivo.value) {
    entradaArchivo.value.value = "";
  }
}

async function importar() {
  if (!archivo.value || enviando.value) {
    return;
  }
  enviando.value = true;
  errorFichajes.value = "";
  resumen.value = null;
  try {
    resumen.value = await importarFichajes(props.token, archivo.value);
    await cargarImportaciones();
  } catch (causa) {
    errorFichajes.value = causa instanceof Error ? causa.message : "No se pudo importar el archivo";
  } finally {
    enviando.value = false;
  }
}

function fechaHora(iso) {
  const fecha = new Date(iso);
  const dos = (numero) => String(numero).padStart(2, "0");
  return `${dos(fecha.getDate())}/${dos(fecha.getMonth() + 1)}/${fecha.getFullYear()} ${dos(fecha.getHours())}:${dos(fecha.getMinutes())}`;
}

function textoPeriodoImportacion(fila) {
  if (!fila.fecha_desde || !fila.fecha_hasta) {
    return "—";
  }
  const [, mesDesde, diaDesde] = fila.fecha_desde.split("-");
  const [anioHasta, mesHasta, diaHasta] = fila.fecha_hasta.split("-");
  return `${diaDesde}/${mesDesde} → ${diaHasta}/${mesHasta}/${anioHasta}`;
}

async function cargarImportaciones() {
  errorImportaciones.value = "";
  try {
    importaciones.value = await listarImportaciones(props.token);
  } catch (causa) {
    importaciones.value = [];
    errorImportaciones.value = causa instanceof Error ? causa.message : "No se pudieron cargar las importaciones";
  }
}

onActivated(cargarImportaciones);
</script>

<template>
  <section class="fichajes">
    <header class="lista-intro">
      <h1>Fichajes</h1>
      <p>Importa el extracto de SAP. El archivo tiene que ser .xlsx, con la hoja Data.</p>
    </header>
    <div class="fichajes-columnas">
    <form class="panel fichajes-form" @submit.prevent="importar">
      <header class="panel-cabecera">
        <h2>Importar</h2>
      </header>
      <div class="alta-cuerpo">
        <div class="fichajes-archivo">
          <input
            ref="entradaArchivo"
            class="fichajes-entrada"
            type="file"
            accept=".xlsx"
            @change="alArchivo"
          />
          <div
            class="fichajes-zona"
            role="button"
            tabindex="0"
            :class="{ 'fichajes-zona-activa': arrastrando }"
            @click="abrirArchivo"
            @keydown.enter.prevent="abrirArchivo"
            @keydown.space.prevent="abrirArchivo"
            @dragenter.prevent="arrastrando = true"
            @dragover.prevent="arrastrando = true"
            @dragleave.prevent="alSalirZona"
            @drop.prevent="alSoltar"
          >
            <template v-if="archivo">
              <span class="fichajes-nombre">{{ archivo.name }}</span>
              <span class="fichajes-tamano">{{ tamanoArchivo }}</span>
              <a href="#" class="fichajes-quitar" @click.stop.prevent="quitarArchivo">Quitar</a>
            </template>
            <template v-else>
              Arrastra aquí el extracto de SAP (.xlsx) o haz clic para elegirlo
            </template>
          </div>
        </div>
        <p v-if="errorFichajes" class="error" role="alert">{{ errorFichajes }}</p>
        <button class="primario" type="submit" :disabled="enviando || !archivo">Importar</button>
      </div>
    </form>
    <section v-if="resumen" class="panel fichajes-resumen">
      <p class="fichajes-periodo">{{ textoPeriodo }}</p>
      <dl class="fichajes-cifras">
        <div class="fichajes-cifra">
          <dt>Filas leídas</dt>
          <dd>{{ resumen.filas_leidas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Emparejadas</dt>
          <dd>{{ resumen.emparejadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Sin emparejar</dt>
          <dd>{{ resumen.sin_emparejar }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Filas nuevas</dt>
          <dd>{{ resumen.filas_nuevas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Filas sustituidas</dt>
          <dd>{{ resumen.filas_actualizadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Jornadas</dt>
          <dd>{{ resumen.jornadas }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Días con incidencia</dt>
          <dd>{{ resumen.dias_con_incidencia }}</dd>
        </div>
        <div class="fichajes-cifra">
          <dt>Personas emparejadas</dt>
          <dd>{{ resumen.personas_emparejadas }} de {{ resumen.personas_excel }}</dd>
        </div>
      </dl>
      <a
        v-if="resumen.dias_con_incidencia > 0"
        href="#"
        class="fichajes-ver-analisis"
        @click.prevent="verAnalisis"
      >Ver análisis</a>
    </section>
    </div>
    <section class="panel fichajes-historial">
      <button
        type="button"
        class="panel-cabecera fichajes-historial-cabecera"
        :aria-expanded="historialAbierto"
        @click="historialAbierto = !historialAbierto"
      >
        <h2>Importaciones anteriores ({{ importaciones ? importaciones.length : 0 }})</h2>
        <span class="fichajes-historial-flecha" :class="{ abierta: historialAbierto }" aria-hidden="true">›</span>
      </button>
      <template v-if="historialAbierto">
      <p v-if="errorImportaciones" class="error" role="alert">{{ errorImportaciones }}</p>
      <p v-else-if="importaciones && !importaciones.length" class="panel-vacio">Todavía no se ha importado ningún extracto</p>
      <div v-else-if="importaciones" class="fichajes-historial-scroll">
        <table class="equipo">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Archivo</th>
              <th>Importado por</th>
              <th>Periodo</th>
              <th>Filas leídas</th>
              <th>Sin emparejar</th>
              <th>Días con incidencia</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fila in importaciones" :key="`${fila.momento}-${fila.nombre_archivo}`">
              <td>{{ fechaHora(fila.momento) }}</td>
              <td>{{ fila.nombre_archivo }}</td>
              <td>{{ fila.nombre }}</td>
              <td>{{ textoPeriodoImportacion(fila) }}</td>
              <td>{{ fila.filas_leidas }}</td>
              <td>{{ fila.filas_sin_emparejar }}</td>
              <td>{{ fila.dias_incidencia }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      </template>
    </section>
  </section>
</template>

<style scoped>
.fichajes-archivo {
  position: relative;
}

.fichajes-form .fichajes-zona {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  width: 100%;
  margin-bottom: 16px;
  padding: 22px 18px;
  border: 1.5px dashed var(--border-strong);
  border-radius: 12px;
  background: #fff;
  color: var(--text-2);
  font-size: 14px;
  line-height: 1.4;
  text-align: left;
  cursor: pointer;
}

.fichajes-form .fichajes-zona:hover,
.fichajes-form .fichajes-zona.fichajes-zona-activa {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, #fff);
}

.fichajes-form .alta-cuerpo input.fichajes-entrada {
  position: absolute;
  display: block;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
  box-shadow: none;
}

.fichajes-nombre {
  color: var(--text);
  font-weight: 600;
}

.fichajes-tamano {
  font-size: 13px;
  color: var(--text-2);
}

.fichajes-form a.fichajes-quitar {
  margin-top: 2px;
  color: var(--accent);
  font-size: 13px;
  line-height: 1.2;
}

.fichajes-form a.fichajes-quitar:hover {
  color: var(--accent-dark);
}

.fichajes-columnas {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.fichajes-form {
  flex: 0 0 460px;
  width: 460px;
  max-width: 100%;
}

.fichajes-resumen {
  flex: 1;
  min-width: 0;
  max-width: none;
  margin-top: 0;
  padding: 16px 18px 18px;
}

@media (max-width: 900px) {
  .fichajes-columnas {
    flex-direction: column;
  }

  .fichajes-form {
    flex-basis: auto;
    width: 100%;
  }

  .fichajes-resumen {
    width: 100%;
    margin-top: 16px;
  }
}

.fichajes-periodo {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--accent) 12%, #fff);
  font-size: 14px;
  font-weight: 700;
}

.fichajes-cifras {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.fichajes-resumen div.fichajes-cifra {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
}

.fichajes-cifra dt {
  margin: 0;
  color: var(--text-2);
  font-size: 12px;
  font-weight: 500;
}

.fichajes-cifra dd {
  margin: 0;
  color: var(--text);
  font-size: 18px;
  font-weight: 700;
}

.fichajes-ver-analisis {
  display: inline-block;
  margin-top: 14px;
  color: var(--accent);
  font-size: 13px;
}

.fichajes-historial {
  width: 100%;
  margin-top: 20px;
}

button.fichajes-historial-cabecera {
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

button.fichajes-historial-cabecera[aria-expanded="true"] {
  border-bottom: 1px solid var(--border);
}

button.fichajes-historial-cabecera:hover {
  border-bottom-color: var(--border);
  background: transparent;
}

.fichajes-historial-flecha {
  margin-left: auto;
  color: var(--text-3);
  font-size: 18px;
  line-height: 1;
  transition: transform 0.15s;
}

.fichajes-historial-flecha.abierta {
  transform: rotate(90deg);
}

.fichajes-historial .error {
  margin: 0;
  padding: 16px 18px;
}

.fichajes-historial-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.fichajes-historial table.equipo {
  min-width: 860px;
}
</style>
