<script setup>
import { computed, ref, watch } from "vue";
import { fechaVisible, lunesDe, rangoSemana, sumarDias } from "../fechas.js";
import { GRUPOS } from "../personas.js";
import { semana, semanaActual } from "../api/turnos.js";

const props = defineProps({
  token: { type: String, required: true },
  departamentoId: { type: String, default: "" },
});

const letras = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
const diasNombre = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const horasDia = Array.from({ length: 24 }, (_, hora) => hora);
const grupos = GRUPOS;

const cuadrante = ref(null);
const semanaPrevia = ref(null);
const avisoPrevia = ref(false);
const error = ref("");
const diaIndice = ref(indiceDeHoy());
let previaPedida = "";

function indiceDeHoy() {
  const texto = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const [anio, mes, dia] = texto.split("-").map(Number);
  const ordinal = new Date(Date.UTC(anio, mes - 1, dia)).getUTCDay() || 7;
  return ordinal - 1;
}

function minutosReloj(hora) {
  const [horas, minutos = "0"] = hora.split(":");
  return Number(horas) * 60 + Number(minutos);
}

function textoNumero(valor) {
  return Number(valor.toFixed(1)).toLocaleString("es-ES");
}

function solape(desde, hasta, hora) {
  const bloque = hora * 60;
  return Math.max(0, Math.min(hasta, bloque + 60) - Math.max(desde, bloque));
}

function celdasDe(tramos) {
  return horasDia.map((hora) => {
    const minutos = tramos.reduce((total, [desde, hasta]) => total + solape(desde, hasta, hora), 0);
    if (minutos >= 60) {
      return "completa";
    }
    if (minutos > 0) {
      return "parcial";
    }
    return "";
  });
}

function cubreHoras(turno) {
  if (!turno?.hora_inicio || !turno?.hora_fin) {
    return false;
  }
  return turno.ausencia == null || turno.ausencia === "ST" || turno.ausencia === "FT";
}

function tramosDelDia(turno, turnoAnterior) {
  const tramos = [];
  if (cubreHoras(turnoAnterior)) {
    const desde = minutosReloj(turnoAnterior.hora_inicio);
    const hasta = minutosReloj(turnoAnterior.hora_fin);
    if (hasta <= desde) {
      tramos.push([0, hasta]);
    }
  }
  if (cubreHoras(turno)) {
    const desde = minutosReloj(turno.hora_inicio);
    let hasta = minutosReloj(turno.hora_fin);
    if (hasta <= desde) {
      hasta = 24 * 60;
    }
    tramos.push([desde, hasta]);
  }
  return tramos;
}

function horasDeCeldas(celdas) {
  return celdas.reduce((total, celda) => {
    if (celda === "completa") {
      return total + 1;
    }
    if (celda === "parcial") {
      return total + 0.5;
    }
    return total;
  }, 0);
}

function turnoEnFecha(trabajador, fecha) {
  const dia = trabajador?.dias?.find((item) => item.fecha === fecha);
  return dia?.turno || null;
}

function turnoAnterior(trabajador, fecha) {
  const ayer = sumarDias(fecha, -1);
  const enSemana = turnoEnFecha(trabajador, ayer);
  if (trabajador?.dias?.some((item) => item.fecha === ayer)) {
    return enSemana;
  }
  const clave = trabajador.login || trabajador.id;
  const previo = (semanaPrevia.value?.trabajadores || []).find(
    (item) => (item.login || item.id) === clave,
  );
  return turnoEnFecha(previo, ayer);
}

function filaPersona(trabajador) {
  const fecha = cuadrante.value?.dias?.[diaIndice.value] || "";
  const turno = fecha ? turnoEnFecha(trabajador, fecha) : null;
  const celdas = celdasDe(tramosDelDia(turno, fecha ? turnoAnterior(trabajador, fecha) : null));
  const cubiertas = horasDeCeldas(celdas);
  const base = {
    tipo: "persona",
    clave: trabajador.login || trabajador.id,
    nombre: trabajador.nombre,
    inicio: "",
    fin: "",
    horas: cubiertas ? textoNumero(cubiertas) : "",
    celdas,
  };
  if (turno?.hora_inicio && turno?.hora_fin) {
    return {
      ...base,
      inicio: turno.hora_inicio,
      fin: turno.hora_fin,
    };
  }
  if (turno?.ausencia) {
    return { ...base, inicio: turno.ausencia };
  }
  return base;
}

const filas = computed(() => {
  const lista = cuadrante.value?.trabajadores || [];
  const resultado = [];
  const vistos = new Set();
  for (const grupo of grupos) {
    const personas = lista.filter((trabajador) => trabajador.grupo === grupo.id);
    if (!personas.length) {
      continue;
    }
    resultado.push({ tipo: "grupo", id: grupo.id, titulo: grupo.titulo });
    for (const trabajador of personas) {
      vistos.add(trabajador.login || trabajador.id);
      resultado.push(filaPersona(trabajador));
    }
  }
  for (const trabajador of lista) {
    const clave = trabajador.login || trabajador.id;
    if (!vistos.has(clave)) {
      resultado.push(filaPersona(trabajador));
    }
  }
  return resultado;
});

const personas = computed(() => filas.value.filter((fila) => fila.tipo === "persona"));

const totales = computed(() =>
  horasDia.map((hora) =>
    personas.value.reduce((total, fila) => {
      const celda = fila.celdas[hora];
      if (celda === "completa") {
        return total + 1;
      }
      if (celda === "parcial") {
        return total + 0.5;
      }
      return total;
    }, 0),
  ),
);

const huecos = computed(() => {
  const marcas = horasDia.map(() => false);
  const cubiertas = totales.value.flatMap((total, hora) => (total > 0 ? [hora] : []));
  if (cubiertas.length < 2) {
    return marcas;
  }
  const primera = cubiertas[0];
  const ultima = cubiertas[cubiertas.length - 1];
  for (let hora = primera; hora <= ultima; hora += 1) {
    marcas[hora] = totales.value[hora] === 0;
  }
  return marcas;
});

const tituloDia = computed(() => {
  const iso = cuadrante.value?.dias?.[diaIndice.value];
  if (!iso) {
    return "";
  }
  return `${diasNombre[diaIndice.value]} ${fechaVisible(iso)}`;
});

const tituloSemana = computed(() => {
  if (!cuadrante.value?.dias?.[6]) {
    return "";
  }
  return rangoSemana(cuadrante.value.desde, cuadrante.value.dias[6]);
});

const lunesPrevio = computed(() => {
  if (diaIndice.value !== 0 || !cuadrante.value?.desde) {
    return "";
  }
  return sumarDias(cuadrante.value.desde, -7);
});

function numeroDia(indice) {
  const iso = cuadrante.value?.dias?.[indice];
  return iso ? Number(iso.slice(8)) : "";
}

async function cargar(desde) {
  error.value = "";
  try {
    cuadrante.value = await semana(props.token, desde, false, props.departamentoId);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

async function cargarPrevia(desde) {
  previaPedida = desde;
  try {
    const datos = await semana(props.token, desde, false, props.departamentoId);
    if (previaPedida !== desde || lunesPrevio.value !== desde) {
      return;
    }
    semanaPrevia.value = datos;
    avisoPrevia.value = false;
  } catch {
    if (previaPedida === desde && lunesPrevio.value === desde) {
      semanaPrevia.value = null;
      avisoPrevia.value = true;
    }
  }
}

watch(lunesPrevio, (desde) => {
  if (!desde) {
    avisoPrevia.value = false;
    return;
  }
  if (semanaPrevia.value?.desde !== desde) {
    semanaPrevia.value = null;
  }
  if (semanaPrevia.value?.desde === desde) {
    return;
  }
  cargarPrevia(desde);
});

function moverSemana(delta) {
  const desde = cuadrante.value?.desde || semanaActual();
  cargar(sumarDias(desde, delta * 7));
}

function moverDia(delta) {
  const destino = diaIndice.value + delta;
  if (destino >= 0 && destino <= 6) {
    diaIndice.value = destino;
    return;
  }
  const desde = cuadrante.value?.desde || semanaActual();
  const fecha = sumarDias(desde, destino);
  const [anio, mes, dia] = fecha.split("-").map(Number);
  diaIndice.value = destino < 0 ? 6 : 0;
  cargar(lunesDe(new Date(anio, mes - 1, dia)));
}

cargar(semanaActual());
</script>

<template>
  <section v-if="cuadrante" class="cobertura">
    <div class="semana-nav">
      <button type="button" @click="moverSemana(-1)">Semana anterior</button>
      <span class="rango">{{ tituloSemana }}</span>
      <button type="button" @click="moverSemana(1)">Semana siguiente</button>
      <button type="button" @click="moverDia(-1)">Día anterior</button>
      <span class="rango">{{ tituloDia }}</span>
      <button type="button" @click="moverDia(1)">Día siguiente</button>
    </div>
    <div class="cuadrante-seccion">
      <button
        v-for="(letra, indice) in letras"
        :key="letra"
        type="button"
        :class="{ activo: diaIndice === indice }"
        @click="diaIndice = indice"
      >
        {{ letra }}<span v-if="numeroDia(indice)"> {{ numeroDia(indice) }}</span>
      </button>
    </div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-if="diaIndice === 0 && avisoPrevia" class="cobertura-nota" role="status">
      No se pudo cargar la semana anterior: la madrugada del lunes puede estar incompleta.
    </p>
    <div class="cobertura-scroll">
      <table class="cuadrante cobertura">
        <thead>
          <tr>
            <th>Trabajador</th>
            <th>Inicio</th>
            <th>Fin</th>
            <th>Horas</th>
            <th v-for="hora in horasDia" :key="hora" class="hora">{{ hora }}</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="fila in filas" :key="fila.tipo === 'grupo' ? fila.id : fila.clave">
            <tr v-if="fila.tipo === 'grupo'" class="grupo-fila">
              <th :colspan="horasDia.length + 4">{{ fila.titulo }}</th>
            </tr>
            <tr v-else>
              <th>{{ fila.nombre }}</th>
              <td :class="{ 'cobertura-ausencia': fila.inicio && !fila.fin }">{{ fila.inicio }}</td>
              <td>{{ fila.fin }}</td>
              <td>{{ fila.horas }}</td>
              <td
                v-for="(celda, hora) in fila.celdas"
                :key="hora"
                class="hora"
                :class="celda ? `cubre-${celda}` : ''"
                :title="celda === 'parcial' ? 'Tramo parcial' : celda === 'completa' ? 'En turno' : ''"
              ></td>
            </tr>
          </template>
        </tbody>
        <tfoot>
          <tr>
            <td>Personas por hora</td>
            <td></td>
            <td></td>
            <td></td>
            <td
              v-for="(total, hora) in totales"
              :key="hora"
              class="hora"
              :class="{ hueco: huecos[hora] }"
            >
              {{ textoNumero(total) }}
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
    <p class="cobertura-nota">La pausa no se descuenta por hora.</p>
  </section>
  <p v-else-if="error" class="error" role="alert">{{ error }}</p>
</template>
