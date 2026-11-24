<script setup>
defineProps({
  pulsable: { type: Boolean, default: false },
  lectura: { type: Boolean, default: false },
  titulo: { type: String, default: undefined },
  ajuste: { type: Boolean, default: false },
  partido: { type: Boolean, default: false },
  texto: { type: String, default: "" },
});

defineEmits(["abrir"]);
</script>

<template>
  <button
    v-if="pulsable"
    type="button"
    class="celda"
    :title="titulo"
    @click="$emit('abrir')"
  >
    <span v-if="ajuste" class="ajuste-marca">
      <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path d="M2.2 13.8 5 13.1 13.2 4.9 11.1 2.8 2.9 11Z" />
        <path d="M9.4 4.5 11.5 6.6" />
        <path d="M3.2 11.4 4.6 12.8" />
      </svg>
    </span>
    <span :class="{ 'celda-partida': partido }">{{ texto }}</span>
  </button>
  <span v-else class="celda" :class="{ lectura }" :title="titulo">
    <span v-if="ajuste" class="ajuste-marca">
      <svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path d="M2.2 13.8 5 13.1 13.2 4.9 11.1 2.8 2.9 11Z" />
        <path d="M9.4 4.5 11.5 6.6" />
        <path d="M3.2 11.4 4.6 12.8" />
      </svg>
    </span>
    <span :class="{ 'celda-partida': partido }">{{ texto }}</span>
  </span>
</template>

<style scoped>
.celda-partida {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
  font-size: 11.5px;
  white-space: nowrap;
}

.celda {
  position: relative;
}

.ajuste-marca {
  position: absolute;
  top: -5px;
  right: -5px;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: 1.5px solid #fff;
  border-radius: 50%;
  background: var(--accent-darker);
  color: #fff;
  pointer-events: none;
  cursor: default;
}

.ajuste-marca svg {
  display: block;
  width: 10px;
  height: 10px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
