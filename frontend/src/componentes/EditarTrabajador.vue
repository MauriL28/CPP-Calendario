<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { editarTrabajador } from "../api/usuarios.js";
import DuracionPausa from "./DuracionPausa.vue";
import EditarUsuario from "./EditarUsuario.vue";
import HorarioHabitual from "./HorarioHabitual.vue";

const props = defineProps({
  token: { type: String, required: true },
  persona: { type: Object, required: true },
  secciones: { type: Array, default: () => [] },
  conHorario: { type: Boolean, default: false },
});

const emit = defineEmits(["guardado", "cerrar"]);

const dialogo = ref(null);
const datosRef = ref(null);
const horarioRef = ref(null);
const pestana = ref("datos");
const pausa = ref(0);
const horaPausa = ref("");
const errorPausa = ref("");
const avisoDatos = ref(false);
const avisoPausa = ref(false);
const avisoHorario = ref(false);
const horarioSucio = ref(false);

const pausaDistinta = computed(() => cambiosPausa().pausa_minutos !== undefined
  || cambiosPausa().pausa_habitual !== undefined);

function horaCorta(valor) {
  const texto = String(valor || "").trim();
  return texto.length >= 5 ? texto.slice(0, 5) : "";
}

function pausaDe(valor) {
  const cantidad = Number(valor);
  if (Number.isInteger(cantidad) && cantidad >= 0 && cantidad <= 180 && cantidad % 5 === 0) {
    return cantidad;
  }
  return 0;
}

function rellenarPausa() {
  pausa.value = pausaDe(props.persona.pausa_minutos);
  horaPausa.value = horaCorta(props.persona.pausa_habitual);
  errorPausa.value = "";
}

function cambiosPausa() {
  const cambios = {};
  const pausaNueva = pausaDe(pausa.value);
  if (pausaNueva !== pausaDe(props.persona.pausa_minutos)) {
    cambios.pausa_minutos = pausaNueva;
  }
  if (pausaNueva > 0) {
    const horaNueva = horaCorta(horaPausa.value);
    if (horaNueva !== horaCorta(props.persona.pausa_habitual)) {
      cambios.pausa_habitual = horaNueva || null;
    }
  }
  return cambios;
}

function hayPendientes() {
  return Boolean(datosRef.value?.cambiosPendientes())
    || pausaDistinta.value
    || (props.conHorario && horarioSucio.value);
}

function pedirCierre() {
  if (hayPendientes() && !window.confirm("Hay cambios sin guardar. ¿Cerrar?")) {
    return;
  }
  dialogo.value?.close();
}

function alCancelar(evento) {
  if (!hayPendientes()) {
    return;
  }
  evento.preventDefault();
  if (window.confirm("Hay cambios sin guardar. ¿Cerrar?")) {
    dialogo.value?.close();
  }
}

function alCerrar() {
  emit("cerrar");
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    pedirCierre();
  }
}

function alCambioHorario(sucio) {
  horarioSucio.value = sucio;
  if (sucio) {
    avisoHorario.value = false;
  }
}

async function guardarPausa() {
  const cambios = cambiosPausa();
  if (!Object.keys(cambios).length) {
    return;
  }
  errorPausa.value = "";
  avisoPausa.value = false;
  try {
    await editarTrabajador(props.token, props.persona.login, cambios);
    emit("guardado", "pausa");
  } catch (causa) {
    errorPausa.value = causa instanceof Error ? causa.message : "No se pudo guardar";
  }
}

function alGuardarDatos() {
  avisoDatos.value = false;
  emit("guardado", "datos");
}

function alGuardarHorario() {
  avisoHorario.value = false;
  emit("guardado", "horario");
}

function aplicar(bloque, fresco) {
  if (bloque === "datos") {
    avisoDatos.value = true;
    if (fresco) {
      datosRef.value?.rellenar();
    }
    return;
  }
  if (bloque === "pausa") {
    avisoPausa.value = true;
    if (fresco) {
      rellenarPausa();
    }
    return;
  }
  if (bloque === "horario") {
    avisoHorario.value = true;
    if (fresco) {
      horarioRef.value?.iniciar();
    }
  }
}

defineExpose({ aplicar });

onMounted(async () => {
  rellenarPausa();
  dialogo.value?.showModal();
  await nextTick();
  dialogo.value?.querySelector("[name='nombre-usuario']")?.focus();
});
</script>

<template>
  <dialog
    ref="dialogo"
    class="alta-dialogo editar-dialogo"
    @cancel="alCancelar"
    @close="alCerrar"
    @click="alFondo"
  >
    <header class="alta-dialogo-cabecera">
      <div>
        <h2>Editar usuario</h2>
        <p v-if="persona" class="alta-dialogo-persona">{{ persona.nombre }}</p>
      </div>
      <button type="button" class="dialogo-cerrar" @click="pedirCierre">✕</button>
    </header>
    <nav class="vistas" role="tablist">
      <button
        type="button"
        role="tab"
        :class="{ activo: pestana === 'datos' }"
        :aria-selected="pestana === 'datos'"
        @click="pestana = 'datos'"
      >
        Datos generales
      </button>
      <button
        type="button"
        role="tab"
        :class="{ activo: pestana === 'horario' }"
        :aria-selected="pestana === 'horario'"
        @click="pestana = 'horario'"
      >
        Horario
      </button>
    </nav>
    <div class="editar-cuerpo">
      <div v-show="pestana === 'datos'" @input="avisoDatos = false" @change="avisoDatos = false">
        <EditarUsuario
          ref="datosRef"
          embebido
          modo="mando"
          :con-pausa="false"
          :token="token"
          :persona="persona"
          :secciones="secciones"
          :aviso="avisoDatos"
          @guardado="alGuardarDatos"
        />
      </div>
      <div v-show="pestana === 'horario'">
        <form @submit.prevent="guardarPausa" @input="avisoPausa = false" @change="avisoPausa = false">
          <div class="alta-dialogo-cuerpo">
            <h3>Pausa</h3>
            <label class="ancho">
              Pausa
              <DuracionPausa v-model="pausa" />
            </label>
            <p class="ancho campo-pista">Descanso diario no pagado. Se resta de las horas planificadas.</p>
            <label v-if="pausaDe(pausa) > 0" class="ancho">
              Hora de pausa
              <input v-model="horaPausa" name="hora-pausa-usuario" type="time" />
            </label>
            <p v-if="pausaDe(pausa) > 0" class="ancho campo-pista">Si la indicas, Cobertura la tiene en cuenta.</p>
          </div>
          <p v-if="errorPausa" class="error" role="alert">{{ errorPausa }}</p>
          <p v-if="avisoPausa" class="aviso-linea" role="status">Guardado</p>
          <footer class="alta-dialogo-pie">
            <button class="primario" type="submit">Guardar pausa</button>
          </footer>
        </form>
        <form v-if="conHorario" @submit.prevent="horarioRef?.guardar()">
          <HorarioHabitual
            ref="horarioRef"
            :token="token"
            :persona="persona"
            modo="trabajador"
            @guardado="alGuardarHorario"
            @cambio="alCambioHorario"
          />
          <p v-if="avisoHorario" class="aviso-linea" role="status">Guardado</p>
          <footer class="alta-dialogo-pie">
            <button class="primario" type="submit">Guardar horario</button>
          </footer>
        </form>
      </div>
    </div>
    <footer class="alta-dialogo-pie">
      <button type="button" @click="pedirCierre">Cancelar</button>
    </footer>
  </dialog>
</template>

<style scoped>
.editar-dialogo[open] {
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 48px);
}

.editar-dialogo > .vistas {
  flex: 0 0 auto;
  align-self: flex-start;
  width: fit-content;
  margin: 16px 20px 0;
}

.editar-dialogo > .vistas button:not(.tarjeta):not(.celda) {
  line-height: 1.4;
  height: auto;
  padding: 8px 16px;
}

.editar-cuerpo {
  min-height: 0;
  overflow: auto;
}

.aviso-linea {
  margin: 0 20px 12px;
  color: var(--ok);
  font-size: 13px;
}
</style>
