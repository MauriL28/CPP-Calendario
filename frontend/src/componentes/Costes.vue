<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { mes, semana } from "../api/turnos.js";
import {
  agregarMeses,
  claveMesCache,
  guardarMesCache,
  horasDeFila,
  leerMesCache,
  totalesDe,
} from "../costesAnio.js";
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
import Aviso from "./Aviso.vue";
import NavegacionPeriodo from "./NavegacionPeriodo.vue";

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

const mesesCortos = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"];

const modo = ref("semana");
const periodo = ref(null);
const anterior = ref(null);
const semanaDesde = ref("");
const anioMes = ref(0);
const numeroMes = ref(0);
const anioVista = ref(new Date().getFullYear());
const huecos = ref([]);
const progresoAnio = ref(12);
const error = ref("");
const avisoOculto = ref("");
const seccionElegida = ref("");
const calculoAbierto = ref(false);
const calculo = ref(null);
let generacion = 0;
let generacionAnio = 0;

const tituloMes = computed(() => `${mesesLargos[numeroMes.value - 1] || ""} ${anioMes.value}`.trim());
const ett = computed(() => ettDe(periodo.value));
const agregado = computed(() =>
  agregarMeses(huecos.value.map((hueco) => (hueco?.estado === "ok" ? hueco.datos : null))),
);
const secciones = computed(() => {
  const nombres = new Set();
  const fuente = modo.value === "anio" ? agregado.value.filas : ett.value;
  for (const trabajador of fuente) {
    if (trabajador.seccion) {
      nombres.add(trabajador.seccion);
    }
  }
  return [...nombres].sort((a, b) => a.localeCompare(b, "es"));
});
const opcionesSeccion = computed(() => {
  const nombres = [...secciones.value];
  if (seccionElegida.value && !nombres.includes(seccionElegida.value)) {
    nombres.push(seccionElegida.value);
    nombres.sort((a, b) => a.localeCompare(b, "es"));
  }
  return nombres;
});
const visibles = computed(() => filtrarSeccion(ett.value));
const filasAnio = computed(() => filtrarSeccion(agregado.value.filas));
const totalesAnio = computed(() => totalesDe(filasAnio.value));
const anteriores = computed(() => filtrarSeccion(ettDe(anterior.value)));
const resumen = computed(() => totalGrupo(visibles.value));
const comparacion = computed(() => {
  if (modo.value === "anio" || !anterior.value || !periodo.value) {
    return null;
  }
  return textoDelta(totalGrupo(visibles.value).total - totalGrupo(anteriores.value).total);
});
const horasDia = computed(() =>
  modo.value === "anio"
    ? filasAnio.value.reduce((total, fila) => total + horasDeFila(fila).diurnas, 0)
    : visibles.value.reduce((total, trabajador) => total + horasDiurnas(trabajador), 0),
);
const horasNoche = computed(() =>
  modo.value === "anio"
    ? filasAnio.value.reduce((total, fila) => total + horasDeFila(fila).nocturnas, 0)
    : visibles.value.reduce((total, trabajador) => total + horasNocturnas(trabajador), 0),
);
const personasVista = computed(() => (modo.value === "anio" ? filasAnio.value : visibles.value));
const conTarifa = computed(() => personasVista.value.filter((trabajador) => tieneCoste(trabajador)).length);
const costeParcial = computed(() =>
  personasVista.value.some((trabajador) => !tieneCoste(trabajador) || !tieneTarifaNocturna(trabajador)),
);
const etiquetaCoste = computed(() => {
  if (modo.value === "anio") {
    return costeParcial.value ? "Coste parcial" : "Coste del año";
  }
  return costeParcial.value ? "Coste parcial" : "Coste del periodo";
});
const totalVista = computed(() => (modo.value === "anio" ? totalesAnio.value.total : resumen.value.total));
const importeMaximoAnio = computed(() => filasAnio.value.reduce((maximo, fila) => Math.max(maximo, fila.total), 0));
const fallosAnio = computed(() =>
  huecos.value.flatMap((hueco, indice) =>
    hueco?.estado === "error" ? [{ mes: indice + 1, mensaje: hueco.mensaje }] : [],
  ),
);
const importeMaximo = computed(() =>
  visibles.value.reduce((maximo, trabajador) => {
    const { importe } = importeTrabajador(trabajador);
    return importe === null ? maximo : Math.max(maximo, importe);
  }, 0),
);
const avisos = computed(() => {
  const sinCoste = personasVista.value.filter((trabajador) => !tieneCoste(trabajador)).map((trabajador) => trabajador.nombre);
  const sinNoche = personasVista.value
    .filter((trabajador) =>
      modo.value === "anio" ? trabajador.sinTarifaNocturna : importeTrabajador(trabajador).sinTarifaNocturna,
    )
    .map((trabajador) => trabajador.nombre);
  const resumenLinea = [];
  if (sinCoste.length) {
    resumenLinea.push(`${sinCoste.length} sin coste`);
  }
  if (sinNoche.length) {
    resumenLinea.push(`${sinNoche.length} sin tarifa nocturna`);
  }
  if (!resumenLinea.length) {
    return [];
  }
  const lineas = [resumenLinea.join(" · ")];
  if (sinCoste.length) {
    lineas.push(`Sin coste: ${sinCoste.join(", ")}`);
  }
  if (sinNoche.length) {
    lineas.push(`Sin tarifa nocturna: ${sinNoche.join(", ")}`);
  }
  return lineas;
});
const claveAvisos = computed(() => avisos.value.join("\n"));
const mostrarAvisos = computed(() => avisos.value.length > 0 && claveAvisos.value !== avisoOculto.value);
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

function filtrarSeccion(lista) {
  if (!seccionElegida.value) {
    return lista;
  }
  return lista.filter((trabajador) => trabajador.seccion === seccionElegida.value);
}

function alTecla(evento) {
  if (evento.key === "Escape") {
    calculoAbierto.value = false;
  }
}

function alPulsarFuera(evento) {
  if (!calculoAbierto.value || calculo.value?.contains(evento.target)) {
    return;
  }
  calculoAbierto.value = false;
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

function numeroVisible(valor, decimales) {
  const redondeado = Number(Number(valor).toFixed(decimales));
  const [entero, fraccion = ""] = Math.abs(redondeado).toFixed(decimales).split(".");
  const grupos = entero.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const texto = decimales > 0 ? `${grupos},${fraccion}` : grupos;
  return redondeado < 0 ? `-${texto}` : texto;
}

function horasVisibles(valor) {
  return `${numeroVisible(valor, 2).replace(/,00$/, "").replace(/(\,\d)0$/, "$1")} h`;
}

function eurosVisibles(valor) {
  return `${numeroVisible(valor, 2)} €`;
}

function anchoBarra(trabajador) {
  const { importe } = importeTrabajador(trabajador);
  if (importe === null || importeMaximo.value <= 0) {
    return 0;
  }
  return Math.max(0, (importe / importeMaximo.value) * 100);
}

function anchoAnio(fila) {
  if (importeMaximoAnio.value <= 0) {
    return 0;
  }
  return Math.max(0, (fila.total / importeMaximoAnio.value) * 100);
}

function textoMes(importe) {
  if (!importe) {
    return "—";
  }
  return numeroVisible(importe, 2);
}

function importeConEuro(importe) {
  if (importe === null || importe === undefined) {
    return "—";
  }
  return eurosVisibles(importe);
}

function tituloMesCelda(celda) {
  if (!celda) {
    return undefined;
  }
  return `${horasVisibles(celda.diurnas)} diurnas · ${horasVisibles(celda.nocturnas)} nocturnas · ${importeConEuro(celda.importe)}`;
}

function tituloAnio(fila) {
  const horas = horasDeFila(fila);
  const alguno = fila.meses.some((mes) => mes?.importe !== null && mes?.importe !== undefined);
  return `${horasVisibles(horas.diurnas)} diurnas · ${horasVisibles(horas.nocturnas)} nocturnas · ${alguno ? eurosVisibles(fila.total) : "—"}`;
}

function tituloImporte(trabajador) {
  const { importe } = importeTrabajador(trabajador);
  return `${horasVisibles(horasDiurnas(trabajador))} diurnas · ${horasVisibles(horasNocturnas(trabajador))} nocturnas · ${importeConEuro(importe)}`;
}

function cerrarAvisos() {
  avisoOculto.value = claveAvisos.value;
}

function textoDelta(valor) {
  const cantidad = Number(valor.toFixed(2));
  if (cantidad === 0) {
    return `(±${formatoEuros(0)})`;
  }
  const signo = cantidad > 0 ? "+" : "-";
  return `(${signo}${formatoEuros(Math.abs(cantidad))})`;
}

function textoImporte(trabajador) {
  const { importe } = importeTrabajador(trabajador);
  return importe === null ? "" : numeroVisible(importe, 2);
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
  const previo = modo.value;
  if (previo === "anio") {
    generacionAnio += 1;
  }
  modo.value = nuevo;
  if (nuevo === "anio") {
    const anio = anioMes.value || partes(semanaDesde.value || lunesDe(new Date()))[0];
    cargarAnio(anio);
    return;
  }
  if (nuevo === "mes") {
    if (previo === "anio") {
      cargarMes(anioVista.value, numeroMes.value || 1);
      return;
    }
    const [anio, mesNumero] = partes(semanaDesde.value || lunesDe(new Date()));
    cargarMes(anio, mesNumero);
    return;
  }
  if (previo === "anio" && semanaDesde.value) {
    cargar(semanaDesde.value);
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

function ponerHueco(indice, hueco) {
  const copia = huecos.value.slice();
  copia[indice] = hueco;
  huecos.value = copia;
}

async function enParalelo(items, limite, trabajo) {
  let cursor = 0;
  async function worker() {
    while (cursor < items.length) {
      const item = items[cursor];
      cursor += 1;
      await trabajo(item);
    }
  }
  const puestos = Math.min(limite, items.length);
  if (!puestos) {
    return;
  }
  await Promise.all(Array.from({ length: puestos }, () => worker()));
}

async function pedirMesAnio(anio, mesNumero, solicitud) {
  if (solicitud !== generacionAnio) {
    return;
  }
  try {
    const datos = await mes(props.token, anio, mesNumero, false, props.departamentoId);
    if (solicitud !== generacionAnio) {
      return;
    }
    guardarMesCache(claveMesCache(props.departamentoId, anio, mesNumero), datos);
    ponerHueco(mesNumero - 1, { estado: "ok", datos });
  } catch (causa) {
    if (solicitud !== generacionAnio) {
      return;
    }
    ponerHueco(mesNumero - 1, {
      estado: "error",
      mensaje: causa instanceof Error ? causa.message : "No se pudo cargar el mes",
    });
  } finally {
    if (solicitud === generacionAnio) {
      progresoAnio.value += 1;
    }
  }
}

function cargarAnio(anio) {
  const solicitud = ++generacionAnio;
  anioVista.value = anio;
  const pendientes = [];
  const inicial = [];
  let listos = 0;
  for (let mesNumero = 1; mesNumero <= 12; mesNumero += 1) {
    const guardado = leerMesCache(claveMesCache(props.departamentoId, anio, mesNumero));
    if (guardado) {
      inicial.push({ estado: "ok", datos: guardado });
      listos += 1;
    } else {
      inicial.push({ estado: "pendiente" });
      pendientes.push(mesNumero);
    }
  }
  huecos.value = inicial;
  progresoAnio.value = listos;
  return enParalelo(pendientes, 4, (mesNumero) => pedirMesAnio(anio, mesNumero, solicitud));
}

function reintentarMes(mesNumero) {
  ponerHueco(mesNumero - 1, { estado: "pendiente" });
  progresoAnio.value = Math.max(0, progresoAnio.value - 1);
  return pedirMesAnio(anioVista.value, mesNumero, generacionAnio);
}

function moverAnio(delta) {
  cargarAnio(anioVista.value + delta);
}

function irAMes(mesNumero) {
  generacionAnio += 1;
  modo.value = "mes";
  cargarMes(anioVista.value, mesNumero);
}

onMounted(() => {
  window.addEventListener("keydown", alTecla);
  window.addEventListener("pointerdown", alPulsarFuera);
  cargar(lunesDe(new Date()));
});

onUnmounted(() => {
  window.removeEventListener("keydown", alTecla);
  window.removeEventListener("pointerdown", alPulsarFuera);
});
</script>

<template>
  <section v-if="periodo || modo === 'anio'" class="semana lectura">
    <div class="semana-nav">
      <div class="vistas modo-vista">
        <button type="button" :class="{ activo: modo === 'semana' }" @click="cambiarModo('semana')">
          Semana
        </button>
        <button type="button" :class="{ activo: modo === 'mes' }" @click="cambiarModo('mes')">
          Mes
        </button>
        <button type="button" :class="{ activo: modo === 'anio' }" @click="cambiarModo('anio')">
          Anual
        </button>
      </div>
      <NavegacionPeriodo
        v-if="modo === 'semana' && periodo"
        anterior="Semana anterior"
        siguiente="Semana siguiente"
        @anterior="cargar(sumarDias(semanaDesde, -7))"
        @siguiente="cargar(sumarDias(semanaDesde, 7))"
      >
        {{ rangoSemana(periodo.desde, periodo.dias[6]) }}
      </NavegacionPeriodo>
      <NavegacionPeriodo
        v-else-if="modo === 'mes'"
        anterior="Mes anterior"
        siguiente="Mes siguiente"
        @anterior="moverMes(-1)"
        @siguiente="moverMes(1)"
      >
        {{ tituloMes }}
      </NavegacionPeriodo>
      <NavegacionPeriodo
        v-else
        anterior="Año anterior"
        siguiente="Año siguiente"
        @anterior="moverAnio(-1)"
        @siguiente="moverAnio(1)"
      >
        {{ anioVista }}
      </NavegacionPeriodo>
      <div ref="calculo" class="costes-calculo">
        <button
          type="button"
          class="boton-icono"
          title="Cómo se calcula"
          aria-label="Cómo se calcula"
          :aria-expanded="calculoAbierto ? 'true' : 'false'"
          @click="calculoAbierto = !calculoAbierto"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2" />
            <circle cx="12" cy="8.2" r="1" fill="currentColor" />
            <path d="M12 11.2V16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
          </svg>
        </button>
        <div v-if="calculoAbierto" class="costes-calculo-panel" role="dialog" aria-label="Cómo se calcula">
          <p class="costes-calculo-titulo">Cómo se calcula</p>
          <p><strong>Qué horas cuentan</strong></p>
          <ul>
            <li>Los días con horario y los de sábado trabajado (ST) y festivo trabajado (FT).</li>
            <li>Vacaciones, bajas, permisos, festivos, libranzas y domingos no suman horas.</li>
            <li>Las horas de cada turno ya van sin la pausa.</li>
          </ul>
          <p><strong>Horas de día y de noche</strong></p>
          <ul>
            <li>Horas nocturnas: las del turno que caen en la franja nocturna. La pausa no se descuenta de esa franja, pero las nocturnas nunca pasan de las horas del turno.</li>
            <li>Horas diurnas: el resto.</li>
          </ul>
          <p><strong>Importe</strong></p>
          <ul>
            <li>Horas diurnas × tarifa día + horas nocturnas × tarifa noche.</li>
            <li>Si el ETT no tiene tarifa de noche, sus horas nocturnas se pagan con la tarifa de día.</li>
            <li>Si falta la tarifa de día, no se calcula su importe y aparece en el aviso amarillo.</li>
          </ul>
        </div>
      </div>
    </div>
    <p v-if="error && modo !== 'anio'" class="error" role="alert">{{ error }}</p>
    <p v-if="modo === 'anio' && progresoAnio < 12" class="costes-progreso" role="status">
      Cargando {{ progresoAnio }}/12
      <span class="costes-progreso-barra"><span :style="{ width: `${(progresoAnio / 12) * 100}%` }"></span></span>
    </p>
    <p v-for="fallo in fallosAnio" :key="fallo.mes" class="error" role="alert">
      {{ mesesLargos[fallo.mes - 1] }}: {{ fallo.mensaje }}
      <button type="button" @click="reintentarMes(fallo.mes)">Reintentar</button>
    </p>
    <div class="cuadrante-horas">
      <article class="total">
        <p class="lb">{{ etiquetaCoste }}</p>
        <p class="vl">
          {{ eurosVisibles(totalVista) }}<span v-if="comparacion" class="delta" :title="tituloComparacion">{{ ` ${comparacion}` }}</span>
        </p>
      </article>
      <article>
        <p class="lb">Horas diurnas</p>
        <p class="vl">{{ horasVisibles(horasDia) }}</p>
      </article>
      <article class="noche">
        <p class="lb">Horas nocturnas</p>
        <p class="vl">{{ horasVisibles(horasNoche) }}</p>
      </article>
      <article>
        <p class="lb">ETT con tarifa</p>
        <p class="vl">{{ conTarifa }} de {{ personasVista.length }}</p>
      </article>
    </div>
    <Aviso v-if="mostrarAvisos" :mensajes="avisos" @cerrar="cerrarAvisos" />
    <div v-if="opcionesSeccion.length" class="cuadrante-seccion">
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
    <p v-if="modo !== 'anio' && !ett.length" class="panel-vacio">No hay trabajadores ETT en este departamento.</p>
    <p v-else-if="modo !== 'anio' && !visibles.length" class="panel-vacio">No hay ETT en esta sección.</p>
    <p v-else-if="modo === 'anio' && progresoAnio === 12 && !agregado.filas.length" class="panel-vacio">
      No hay trabajadores ETT en este departamento.
    </p>
    <p v-else-if="modo === 'anio' && progresoAnio === 12 && !filasAnio.length" class="panel-vacio">
      No hay ETT en esta sección.
    </p>
    <template v-else-if="modo === 'anio' && filasAnio.length">
    <p class="costes-unidad">Importe por mes (€)</p>
    <div class="cuadrante-scroll costes-scroll">
      <table class="cuadrante costes-tabla costes-anio">
        <thead>
          <tr>
            <th>Nombre</th>
            <th v-for="(corto, indice) in mesesCortos" :key="corto">
              <button type="button" class="costes-mes" @click="irAMes(indice + 1)">{{ corto }}</button>
            </th>
            <th>Total año</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fila in filasAnio" :key="fila.login">
            <th>{{ fila.nombre }}</th>
            <td v-for="(celda, indice) in fila.meses" :key="indice" :title="tituloMesCelda(celda)">
              {{ textoMes(celda?.importe) }}
            </td>
            <td class="coste-importe" :title="tituloAnio(fila)">
              <span v-if="fila.total" class="coste-importe-linea">
                <strong>{{ numeroVisible(fila.total, 2) }}</strong>
              </span>
              <span v-else>—</span>
              <span v-if="fila.total" class="coste-barra" :style="{ width: `${anchoAnio(fila)}%` }"></span>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td>Total del año</td>
            <td v-for="(importe, indice) in totalesAnio.totalesMes" :key="indice">{{ textoMes(importe) }}</td>
            <td><strong>{{ numeroVisible(totalesAnio.total, 2) }}</strong></td>
          </tr>
        </tfoot>
      </table>
    </div>
    </template>
    <div v-else-if="modo !== 'anio'" class="cuadrante-scroll costes-scroll">
      <table class="cuadrante costes-tabla">
        <thead>
          <tr>
            <th>Nombre</th>
            <th>H. diurnas</th>
            <th>H. nocturnas</th>
            <th>Tarifa día (€/h)</th>
            <th>Tarifa noche (€/h)</th>
            <th>Importe (€)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="trabajador in visibles" :key="trabajador.login">
            <th>{{ trabajador.nombre }}</th>
            <td>{{ horasVisibles(horasDiurnas(trabajador)) }}</td>
            <td>{{ horasVisibles(horasNocturnas(trabajador)) }}</td>
            <td>
              <span v-if="tieneCoste(trabajador)">{{ numeroVisible(trabajador.coste, 2) }}</span>
              <span v-else class="sin-tarifa">Sin tarifa</span>
            </td>
            <td>
              <span v-if="tieneTarifaNocturna(trabajador)">{{ numeroVisible(trabajador.tarifa_nocturna, 2) }}</span>
              <span v-else class="sin-tarifa">Sin tarifa</span>
            </td>
            <td class="coste-importe" :title="tituloImporte(trabajador)">
              <span class="coste-importe-linea">
                <strong v-if="textoImporte(trabajador)">{{ textoImporte(trabajador) }}</strong>
                <span
                  v-if="importeTrabajador(trabajador).sinTarifaNocturna"
                  class="sin-tarifa"
                  title="Faltan horas nocturnas sin tarifa"
                >Sin tarifa</span>
                <span v-else-if="!textoImporte(trabajador)" class="sin-tarifa">Sin tarifa</span>
              </span>
              <span v-if="textoImporte(trabajador)" class="coste-barra" :style="{ width: `${anchoBarra(trabajador)}%` }"></span>
            </td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td colspan="5">Total del periodo</td>
            <td>
              <strong>{{ eurosVisibles(resumen.total) }}</strong><span v-if="comparacion" class="delta" :title="tituloComparacion">{{ ` ${comparacion}` }}</span>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  </section>
</template>

<style scoped>
.costes-unidad {
  margin: 0 0 6px;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 600;
}

.costes-scroll {
  overflow-x: auto;
  max-width: 100%;
}

.costes-tabla {
  width: 100%;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.costes-tabla th,
.costes-tabla td {
  padding: 0.85rem 0.7rem;
  font-size: 16px;
  text-align: right;
}

.costes-tabla thead th {
  font-size: 14px;
  white-space: nowrap;
}

.costes-tabla thead th:first-child,
.costes-tabla tbody th,
.costes-tabla tfoot td:first-child {
  text-align: left;
}

.costes-tabla tfoot td {
  background: var(--manana-bg);
  font-weight: 700;
}

.sin-tarifa {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--warn-bg);
  color: var(--warn);
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
}

.coste-importe {
  min-width: 8.5rem;
}

.coste-importe-linea {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.coste-barra {
  display: block;
  height: 3px;
  margin-top: 4px;
  margin-left: auto;
  border-radius: 2px;
  background: var(--accent);
}

.costes-calculo {
  position: relative;
  margin-left: auto;
}

.costes-calculo-panel {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 5;
  width: 320px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  box-shadow: 0 8px 20px rgba(32, 36, 44, 0.08);
  text-align: left;
}

.costes-calculo-titulo {
  margin: 0 0 8px;
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.costes-calculo-panel p {
  margin: 8px 0 2px;
  color: var(--text);
  font-size: 13px;
  line-height: 1.4;
}

.costes-calculo-panel ul {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--text-2);
  font-size: 13px;
  font-weight: 400;
  line-height: 1.4;
}

.costes-calculo-panel li + li {
  margin-top: 3px;
}

.costes-anio {
  width: max-content;
  min-width: 100%;
}

.costes-anio th:first-child,
.costes-anio tfoot td:first-child {
  position: sticky;
  left: 0;
  z-index: 1;
}

.costes-anio tbody th {
  position: sticky;
  left: 0;
  z-index: 1;
  background: var(--bg);
}

.costes-anio thead th:first-child {
  z-index: 2;
  background: var(--libranza-bg);
}

.costes-anio tfoot td:first-child {
  background: var(--manana-bg);
}

button.costes-mes:not(.tarjeta):not(.celda) {
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

button.costes-mes:not(.tarjeta):not(.celda):hover {
  border-color: transparent;
  color: var(--accent);
}

.costes-progreso {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 8px;
  color: var(--text-2);
  font-size: 13px;
}

.costes-progreso-barra {
  flex: 1;
  max-width: 180px;
  height: 4px;
  border-radius: 999px;
  background: var(--border);
  overflow: hidden;
}

.costes-progreso-barra span {
  display: block;
  height: 100%;
  background: var(--accent);
}

.delta {
  margin-left: 0.35rem;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
}
</style>
