<script setup>
import { ref } from "vue";
import Cuadrante from "./Cuadrante.vue";
import FichaEmpleado from "./FichaEmpleado.vue";

defineProps({
  token: { type: String, required: true },
  login: { type: String, required: true },
  nombreSesion: { type: String, required: true },
  departamento: { type: String, default: "" },
});

const ficha = ref(false);
</script>

<template>
  <section v-if="!ficha" class="bienvenida">
    <p class="bienvenida-titulo">Bienvenido, {{ nombreSesion }}</p>
    <p class="bienvenida-detalle">
      Consulta tu horario y tu ficha<span v-if="departamento"> en {{ departamento }}</span>.
    </p>
  </section>
  <header v-if="!ficha" class="mi-horario">
    <div class="mi-horario-fila">
      <h1>Mi horario</h1>
      <button type="button" class="primario" @click="ficha = true">Ver mi ficha</button>
    </div>
    <p>Turnos de la semana seleccionada.</p>
  </header>
  <div v-show="!ficha">
    <Cuadrante :token="token" propia />
  </div>
  <FichaEmpleado v-if="ficha" :token="token" :login="login" volver @volver="ficha = false" />
</template>

<style scoped>
div :deep(.aviso-lectura) {
  display: none;
}

.mi-horario-fila {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.mi-horario-fila button.primario {
  padding: 10px 22px;
  font-size: 16px;
  font-weight: 700;
  min-height: 44px;
}

@media (max-width: 599px) {
  .mi-horario-fila {
    flex-direction: column;
    align-items: stretch;
  }

  .mi-horario-fila button.primario {
    width: 100%;
  }
}
</style>
