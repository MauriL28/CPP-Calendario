<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { editarTrabajador, editarUsuario } from "../api/usuarios.js";
import { numeroFormulario as numeroDe } from "../personas.js";
import DuracionPausa from "./DuracionPausa.vue";

const props = defineProps({
  token: { type: String, required: true },
  persona: { type: Object, required: true },
  secciones: { type: Array, default: () => [] },
  modo: {
    type: String,
    default: "admin",
    validator: (valor) => valor === "admin" || valor === "mando",
  },
  conHorario: { type: Boolean, default: false },
  conPausa: { type: Boolean, default: true },
  embebido: { type: Boolean, default: false },
  aviso: { type: Boolean, default: false },
});

const emit = defineEmits(["guardado", "cerrar", "horario"]);

const dialogo = ref(null);
const nombre = ref("");
const numeroSap = ref("");
const clave = ref("");
const grupo = ref("STEF");
const coste = ref("");
const vacaciones = ref("");
const horasContrato = ref("");
const horasConvenio = ref("");
const pausa = ref(0);
const horaPausa = ref("");
const seccionId = ref("");
const error = ref("");

const esTrabajador = computed(() => props.persona.rol === "trabajador");

function rellenar() {
  nombre.value = props.persona.nombre || "";
  numeroSap.value = props.persona.numero_sap || "";
  clave.value = "";
  grupo.value = props.persona.grupo || "STEF";
  coste.value = props.persona.coste ?? "";
  vacaciones.value = props.persona.vacaciones ?? "";
  horasContrato.value = props.persona.horas_contrato ?? "";
  horasConvenio.value = props.persona.horas_convenio ?? "";
  pausa.value = pausaDe(props.persona.pausa_minutos);
  horaPausa.value = horaCorta(props.persona.pausa_habitual);
  seccionId.value = props.persona.seccion_id || "";
  error.value = "";
}

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

function cambiosHechos() {
  const cambios = {};
  const nombreNuevo = nombre.value.trim();
  if (nombreNuevo !== (props.persona.nombre || "").trim()) {
    cambios.nombre = nombreNuevo;
  }
  if (numeroSap.value !== (props.persona.numero_sap || "")) {
    cambios.numero_sap = numeroSap.value;
  }
  if (clave.value.trim()) {
    cambios.clave = clave.value;
  }
  if (!esTrabajador.value) {
    return cambios;
  }
  if (grupo.value !== props.persona.grupo) {
    cambios.grupo = grupo.value;
  }
  if (grupo.value === "ETT") {
    const costeNuevo = numeroDe(coste.value);
    const costeActual = numeroDe(props.persona.coste);
    if (costeNuevo !== costeActual) {
      cambios.coste = costeNuevo;
    }
  }
  const vacacionesNuevas = numeroDe(vacaciones.value);
  const vacacionesActuales = numeroDe(props.persona.vacaciones);
  if (vacacionesNuevas !== vacacionesActuales) {
    cambios.vacaciones = vacacionesNuevas;
  }
  const horasNuevas = numeroDe(horasContrato.value);
  const horasActuales = numeroDe(props.persona.horas_contrato);
  if (horasNuevas !== horasActuales) {
    cambios.horas_contrato = horasNuevas;
  }
  const convenioNuevo = numeroDe(horasConvenio.value);
  const convenioActual = numeroDe(props.persona.horas_convenio);
  if (convenioNuevo !== convenioActual) {
    cambios.horas_convenio = convenioNuevo;
  }
  if (props.conPausa) {
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
  }
  if (props.secciones.length) {
    const seccionNueva = seccionId.value || null;
    const seccionActual = props.persona.seccion_id || null;
    if (seccionNueva !== seccionActual) {
      cambios.seccion_id = seccionNueva;
    }
  }
  return cambios;
}

function cerrar() {
  if (props.embebido) {
    return;
  }
  dialogo.value?.close();
}

function irAHorario() {
  if (
    Object.keys(cambiosHechos()).length
    && !window.confirm("Hay cambios sin guardar en el perfil. ¿Seguir?")
  ) {
    return;
  }
  emit("horario");
  cerrar();
}

function alCerrar() {
  if (props.embebido) {
    return;
  }
  emit("cerrar");
}

function alFondo(evento) {
  if (props.embebido) {
    return;
  }
  if (evento.target === dialogo.value) {
    cerrar();
  }
}

async function guardar() {
  const cambios = cambiosHechos();
  if (!Object.keys(cambios).length) {
    if (!props.embebido) {
      cerrar();
    }
    return;
  }
  error.value = "";
  try {
    const guardarEdicion = props.modo === "mando" ? editarTrabajador : editarUsuario;
    const respuesta = await guardarEdicion(props.token, props.persona.login, cambios);
    emit("guardado", respuesta);
    if (!props.embebido) {
      cerrar();
    }
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo guardar";
  }
}

defineExpose({
  cambiosPendientes() {
    return Object.keys(cambiosHechos()).length > 0;
  },
  rellenar,
});

onMounted(async () => {
  rellenar();
  if (props.embebido) {
    return;
  }
  dialogo.value?.showModal();
  await nextTick();
  dialogo.value?.querySelector("[name='nombre-usuario']")?.focus();
});
</script>

<template>
  <component
    :is="embebido ? 'div' : 'dialog'"
    ref="dialogo"
    :class="{ 'alta-dialogo': !embebido }"
    @close="alCerrar"
    @click="alFondo"
  >
    <form @submit.prevent="guardar">
      <header v-if="!embebido" class="alta-dialogo-cabecera">
        <div>
          <h2>Editar usuario</h2>
          <p v-if="persona" class="alta-dialogo-persona">{{ persona.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrar">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Nombre
          <input v-model="nombre" name="nombre-usuario" autocomplete="off" />
        </label>
        <label class="ancho">
          Número de personal (SAP)
          <input v-model="numeroSap" name="numero-sap-usuario" autocomplete="off" />
        </label>
        <p class="ancho campo-pista">Lo pasa RRHH. Déjalo en blanco si aún no lo tienes.</p>
        <label class="ancho">
          Nueva clave
          <input v-model="clave" name="clave-usuario" type="password" autocomplete="new-password" />
        </label>
        <p class="ancho campo-pista">Déjala vacía para no cambiarla.</p>
        <template v-if="esTrabajador">
          <div class="alta-tres">
            <label>
              Grupo
              <select v-model="grupo" name="grupo-usuario">
                <option value="STEF">STEF</option>
                <option value="ETT">ETT</option>
              </select>
            </label>
            <label>
              Vacaciones
              <input v-model="vacaciones" name="vacaciones-usuario" type="number" min="0" step="0.5" />
            </label>
            <label>
              Horas de contrato
              <input v-model="horasContrato" name="horas-contrato-usuario" type="number" min="0" step="0.5" />
            </label>
          </div>
          <label v-if="grupo === 'ETT'" class="ancho">
            Coste (€/hora)
            <input v-model="coste" name="coste-usuario" type="number" min="0" step="0.0001" />
          </label>
          <label class="ancho">
            Horas de convenio al año
            <input v-model="horasConvenio" name="horas-convenio-usuario" type="number" min="0" step="0.5" />
          </label>
          <p class="ancho campo-pista">Vacío = automático (1770 × horas de contrato / 37,5)</p>
          <template v-if="conPausa">
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
          </template>
          <label v-if="secciones.length" class="ancho">
            Sección
            <select v-model="seccionId" name="seccion-usuario">
              <option value="">Sin sección</option>
              <option v-for="seccion in secciones" :key="seccion.id" :value="seccion.id">
                {{ seccion.nombre }}
              </option>
            </select>
          </label>
        </template>
      </div>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="aviso" class="aviso-linea" role="status">Guardado</p>
      <footer class="alta-dialogo-pie">
        <button v-if="conHorario && !embebido" type="button" @click="irAHorario">Horario habitual…</button>
        <button v-if="!embebido" type="button" @click="cerrar">Cancelar</button>
        <button class="primario" type="submit">Guardar</button>
      </footer>
    </form>
  </component>
</template>

<style scoped>
.aviso-linea {
  margin: 0 20px 12px;
  color: var(--ok);
  font-size: 13px;
}
</style>
