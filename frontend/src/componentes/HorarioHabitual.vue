<script setup>
import { computed, ref, watch } from "vue";
import { hoyIso, lunesQueViene } from "../fechas.js";
import { useHorarioHabitual } from "../horarioHabitual.js";
import { cambiarHorario, cambiarHorarioPropio } from "../api/usuarios.js";

const props = defineProps({
  token: { type: String, default: "" },
  persona: { type: Object, default: null },
  modo: { type: String, default: "" },
});

const emit = defineEmits(["guardado", "cambio"]);

const { letras, diasMarcados, horasDia, reiniciar, alMarcar, alHora, horarioDias } = useHorarioHabitual();

const editor = computed(() => props.modo === "trabajador" || props.modo === "propio");
const desde = ref("");
const diasHorario = ref(letras.map(() => false));
const horasHorario = ref(letras.map(() => ({ inicio: "", fin: "" })));
const plantillaHorario = ref(null);
const propiosHorario = ref(letras.map(() => false));
const errorHorario = ref("");
let origen = "";
let silencioso = false;

function foto() {
  if (props.modo === "propio") {
    return JSON.stringify({
      desde: desde.value,
      dias: diasMarcados.value,
      horas: horasDia.value,
    });
  }
  return JSON.stringify({
    desde: desde.value,
    dias: diasHorario.value,
    horas: horasHorario.value,
  });
}

function iniciar() {
  if (!editor.value) {
    return;
  }
  silencioso = true;
  errorHorario.value = "";
  desde.value = lunesQueViene();
  if (props.modo === "propio") {
    reiniciar();
  } else {
    const marcados = letras.map(() => false);
    const horas = letras.map(() => ({ inicio: "", fin: "" }));
    const propio = letras.map(() => false);
    let plantilla = null;
    for (const dia of props.persona?.horario || []) {
      if (dia.dia_semana < 0 || dia.dia_semana > 6) {
        continue;
      }
      marcados[dia.dia_semana] = true;
      horas[dia.dia_semana] = { inicio: dia.inicio || "", fin: dia.fin || "" };
      propio[dia.dia_semana] = true;
      if (plantilla === null) {
        plantilla = dia.dia_semana;
      }
    }
    diasHorario.value = marcados;
    horasHorario.value = horas;
    propiosHorario.value = propio;
    plantillaHorario.value = plantilla;
  }
  origen = foto();
  silencioso = false;
  emit("cambio", false);
}

function alMarcarHorario(dia, evento) {
  const marcado = evento.target.checked;
  diasHorario.value[dia] = marcado;
  if (!marcado || plantillaHorario.value === null || propiosHorario.value[dia]) {
    return;
  }
  const base = horasHorario.value[plantillaHorario.value];
  horasHorario.value[dia] = { inicio: base.inicio, fin: base.fin };
}

function alHoraHorario(dia, campo, valor) {
  const actual = horasHorario.value[dia];
  horasHorario.value[dia] = { ...actual, [campo]: valor };
  if (plantillaHorario.value === null) {
    plantillaHorario.value = dia;
  } else if (dia !== plantillaHorario.value) {
    propiosHorario.value[dia] = true;
    return;
  }
  const base = horasHorario.value[dia];
  horasHorario.value = horasHorario.value.map((item, indice) => {
    if (indice === dia) {
      return base;
    }
    if (!diasHorario.value[indice] || propiosHorario.value[indice]) {
      return item;
    }
    return { inicio: base.inicio, fin: base.fin };
  });
}

async function guardar() {
  errorHorario.value = "";
  if (!desde.value) {
    errorHorario.value = "Indica desde qué fecha aplica.";
    return;
  }
  if (desde.value < hoyIso()) {
    errorHorario.value = "La fecha no puede ser anterior a hoy.";
    return;
  }
  if (props.modo === "propio") {
    const horario = horarioDias();
    if (!horario?.horario_dias) {
      errorHorario.value = horario?.error || "Marca al menos un día.";
      return;
    }
    try {
      await cambiarHorarioPropio(props.token, {
        desde: desde.value,
        horario_dias: horario.horario_dias,
      });
      emit("guardado");
    } catch (causa) {
      errorHorario.value = causa instanceof Error ? causa.message : "No se pudo cambiar el horario";
    }
    return;
  }
  const persona = props.persona;
  if (!persona) {
    return;
  }
  const horarioPedido = [];
  for (let dia = 0; dia < letras.length; dia += 1) {
    if (!diasHorario.value[dia]) {
      continue;
    }
    const horas = horasHorario.value[dia];
    if (!horas.inicio || !horas.fin) {
      errorHorario.value = "Indica la hora de inicio y de fin de cada día marcado.";
      return;
    }
    horarioPedido.push({
      dia_semana: dia,
      hora_inicio: horas.inicio,
      hora_fin: horas.fin,
    });
  }
  if (!horarioPedido.length) {
    errorHorario.value = "Marca al menos un día.";
    return;
  }
  try {
    await cambiarHorario(props.token, persona.login, {
      desde: desde.value,
      horario_dias: horarioPedido,
    });
    emit("guardado", persona);
  } catch (causa) {
    errorHorario.value = causa instanceof Error ? causa.message : "No se pudo cambiar el horario";
  }
}

watch(() => [props.modo, props.persona], iniciar, { immediate: true });

watch([desde, diasHorario, horasHorario, diasMarcados, horasDia], () => {
  if (!editor.value || silencioso) {
    return;
  }
  emit("cambio", foto() !== origen);
}, { deep: true });

defineExpose({ reiniciar, horarioDias, guardar, iniciar });
</script>

<template>
  <template v-if="editor">
    <div class="alta-dialogo-cuerpo">
      <label class="ancho">
        Desde
        <input
          v-model="desde"
          name="desde-horario"
          type="date"
          :required="modo === 'propio'"
          :min="hoyIso()"
        />
      </label>
      <div v-if="modo === 'trabajador'" class="ancho alta-dias-marcas">
        <label v-for="(letra, dia) in letras" :key="`cambio-${letra}`" class="alta-casilla">
          <input
            type="checkbox"
            :checked="diasHorario[dia]"
            @change="alMarcarHorario(dia, $event)"
          />
          {{ letra }}
        </label>
      </div>
      <div
        v-for="(letra, dia) in letras"
        v-show="modo === 'trabajador' && diasHorario[dia]"
        :key="`cambio-horas-${letra}`"
        class="ancho alta-dia-horas"
      >
        <span>{{ letra }}</span>
        <label>
          Hora de inicio
          <input
            :value="horasHorario[dia].inicio"
            type="time"
            @input="alHoraHorario(dia, 'inicio', $event.target.value)"
          />
        </label>
        <label>
          Hora de fin
          <input
            :value="horasHorario[dia].fin"
            type="time"
            @input="alHoraHorario(dia, 'fin', $event.target.value)"
          />
        </label>
      </div>
      <div v-if="modo === 'propio'" class="ancho horario-habitual">
        <h3>Horario habitual</h3>
        <div class="alta-dias-marcas">
          <label v-for="(letra, dia) in letras" :key="letra" class="alta-casilla">
            <input
              type="checkbox"
              :checked="diasMarcados[dia]"
              @change="alMarcar(dia, $event)"
            />
            {{ letra }}
          </label>
        </div>
        <div
          v-for="(letra, dia) in letras"
          v-show="diasMarcados[dia]"
          :key="`horas-${letra}`"
          class="alta-dia-horas"
        >
          <span>{{ letra }}</span>
          <label>
            Hora de inicio
            <input
              :value="horasDia[dia].inicio"
              type="time"
              @input="alHora(dia, 'inicio', $event.target.value)"
            />
          </label>
          <label>
            Hora de fin
            <input
              :value="horasDia[dia].fin"
              type="time"
              @input="alHora(dia, 'fin', $event.target.value)"
            />
          </label>
        </div>
      </div>
    </div>
    <p v-if="errorHorario" class="error" role="alert">{{ errorHorario }}</p>
  </template>
  <div v-else class="ancho horario-habitual">
    <h3>Horario habitual</h3>
    <div class="alta-dias-marcas">
      <label v-for="(letra, dia) in letras" :key="letra" class="alta-casilla">
        <input
          type="checkbox"
          :checked="diasMarcados[dia]"
          @change="alMarcar(dia, $event)"
        />
        {{ letra }}
      </label>
    </div>
    <div
      v-for="(letra, dia) in letras"
      v-show="diasMarcados[dia]"
      :key="`horas-${letra}`"
      class="alta-dia-horas"
    >
      <span>{{ letra }}</span>
      <label>
        Hora de inicio
        <input
          :value="horasDia[dia].inicio"
          type="time"
          @input="alHora(dia, 'inicio', $event.target.value)"
        />
      </label>
      <label>
        Hora de fin
        <input
          :value="horasDia[dia].fin"
          type="time"
          @input="alHora(dia, 'fin', $event.target.value)"
        />
      </label>
    </div>
  </div>
</template>

<style scoped>
.horario-habitual {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.horario-habitual h3 {
  margin: 6px 0 -2px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-3);
}

.horario-habitual label.alta-casilla {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}

.horario-habitual label.alta-casilla input {
  width: auto;
  height: auto;
  margin: 0;
  padding: 0;
  box-shadow: none;
}
</style>
