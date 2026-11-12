<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import { editarTrabajador, editarUsuario } from "../api/usuarios.js";

const props = defineProps({
  token: { type: String, required: true },
  persona: { type: Object, required: true },
  secciones: { type: Array, default: () => [] },
  modo: {
    type: String,
    default: "admin",
    validator: (valor) => valor === "admin" || valor === "mando",
  },
});

const emit = defineEmits(["guardado", "cerrar"]);

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
  seccionId.value = props.persona.seccion_id || "";
  error.value = "";
}

function pausaDe(valor) {
  const cantidad = Number(valor);
  if (cantidad === 30 || cantidad === 60) {
    return cantidad;
  }
  return 0;
}

function numeroDe(valor) {
  if (valor === "" || valor === null || valor === undefined) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
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
  const pausaNueva = pausaDe(pausa.value);
  if (pausaNueva !== pausaDe(props.persona.pausa_minutos)) {
    cambios.pausa_minutos = pausaNueva;
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
  dialogo.value?.close();
}

function alCerrar() {
  emit("cerrar");
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    cerrar();
  }
}

async function guardar() {
  const cambios = cambiosHechos();
  if (!Object.keys(cambios).length) {
    cerrar();
    return;
  }
  error.value = "";
  try {
    const guardarEdicion = props.modo === "mando" ? editarTrabajador : editarUsuario;
    const respuesta = await guardarEdicion(props.token, props.persona.login, cambios);
    emit("guardado", respuesta);
    cerrar();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo guardar";
  }
}

onMounted(async () => {
  rellenar();
  dialogo.value?.showModal();
  await nextTick();
  dialogo.value?.querySelector("[name='nombre-usuario']")?.focus();
});
</script>

<template>
  <dialog ref="dialogo" class="alta-dialogo" @close="alCerrar" @click="alFondo">
    <form @submit.prevent="guardar">
      <header class="alta-dialogo-cabecera">
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
          <label class="ancho">
            Pausa
            <select v-model="pausa" name="pausa-usuario">
              <option :value="0">Sin pausa</option>
              <option :value="30">30 minutos</option>
              <option :value="60">1 hora</option>
            </select>
          </label>
          <p class="ancho campo-pista">Descanso diario no pagado. Se resta de las horas planificadas.</p>
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
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrar">Cancelar</button>
        <button class="primario" type="submit">Guardar</button>
      </footer>
    </form>
  </dialog>
</template>
