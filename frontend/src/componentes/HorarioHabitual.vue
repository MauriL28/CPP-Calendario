<script setup>
import { useHorarioHabitual } from "../horarioHabitual.js";

const { letras, diasMarcados, horasDia, reiniciar, alMarcar, alHora, horarioDias } = useHorarioHabitual();

defineExpose({ reiniciar, horarioDias });
</script>

<template>
  <div class="ancho horario-habitual">
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

h3 {
  margin: 6px 0 -2px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-3);
}

label.alta-casilla {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
}

label.alta-casilla input {
  width: auto;
  height: auto;
  margin: 0;
  padding: 0;
  box-shadow: none;
}
</style>
