<script setup>
import { onMounted, ref, watch } from "vue";
import { listarInactivos, reactivarTrabajador } from "../api/usuarios.js";

const props = defineProps({
  token: { type: String, required: true },
  departamentoId: { type: String, default: "" },
});

const emit = defineEmits(["ver-ficha", "reactivado"]);

const personas = ref([]);
const error = ref("");

async function cargar() {
  if (!props.departamentoId) {
    personas.value = [];
    error.value = "";
    return;
  }
  error.value = "";
  try {
    personas.value = await listarInactivos(props.token, props.departamentoId);
  } catch (causa) {
    personas.value = [];
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los inactivos";
  }
}

async function reactivar(persona) {
  error.value = "";
  try {
    await reactivarTrabajador(props.token, persona.login);
    personas.value = personas.value.filter((item) => item.login !== persona.login);
    emit("reactivado");
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo reactivar";
  }
}

onMounted(cargar);
watch(() => props.departamentoId, cargar);

defineExpose({ recargar: cargar });
</script>

<template>
  <section v-if="personas.length || error" class="panel inactivos">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <details v-if="personas.length">
      <summary>Inactivos ({{ personas.length }})</summary>
      <ul class="panel-filas">
        <li v-for="persona in personas" :key="persona.login">
          <span class="persona-datos">
            <strong>{{ persona.nombre }}</strong>
            <span>{{ persona.grupo }} · {{ persona.seccion || "Sin sección" }}</span>
          </span>
          <span class="equipo-acciones-botones">
            <button type="button" @click="emit('ver-ficha', persona.login)">Ficha</button>
            <button type="button" @click="reactivar(persona)">Reactivar</button>
          </span>
        </li>
      </ul>
    </details>
  </section>
</template>

<style scoped>
.inactivos {
  overflow: hidden;
}

.inactivos .error {
  padding: 14px 18px 0;
}

.inactivos summary {
  padding: 14px 18px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.inactivos details[open] summary {
  border-bottom: 1px solid var(--border);
}

.inactivos .persona-datos strong,
.inactivos .persona-datos span {
  color: var(--text-3);
  font-weight: 500;
}
</style>
