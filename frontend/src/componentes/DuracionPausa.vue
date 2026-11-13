<script setup>
import { computed } from "vue";

const PASO = 5;
const MINIMO = 0;
const MAXIMO = 180;

const minutos = defineModel({ type: Number, default: 0 });

const valor = computed(() => encajar(minutos.value));
const texto = computed(() => textoDe(valor.value));

function encajar(cantidad) {
  const numero = Number(cantidad);
  if (!Number.isInteger(numero)) {
    return MINIMO;
  }
  const pasos = Math.round(numero / PASO) * PASO;
  return Math.min(MAXIMO, Math.max(MINIMO, pasos));
}

function textoDe(cantidad) {
  if (cantidad <= 0) {
    return "Sin pausa";
  }
  if (cantidad < 60) {
    return `${cantidad} min`;
  }
  const horas = Math.floor(cantidad / 60);
  const resto = cantidad % 60;
  if (resto === 0) {
    return `${horas} h`;
  }
  return `${horas} h ${resto} min`;
}

function cambiar(delta) {
  const siguiente = encajar(valor.value + delta);
  if (siguiente !== valor.value) {
    minutos.value = siguiente;
  }
}

function alTecla(evento) {
  if (evento.key === "ArrowUp") {
    evento.preventDefault();
    cambiar(PASO);
  } else if (evento.key === "ArrowDown") {
    evento.preventDefault();
    cambiar(-PASO);
  }
}
</script>

<template>
  <div class="duracion-pausa" @keydown="alTecla">
    <button
      type="button"
      class="duracion-paso"
      aria-label="Reducir la pausa"
      :disabled="valor <= MINIMO"
      @click="cambiar(-PASO)"
    >
      −
    </button>
    <span class="duracion-valor">{{ texto }}</span>
    <button
      type="button"
      class="duracion-paso"
      aria-label="Aumentar la pausa"
      :disabled="valor >= MAXIMO"
      @click="cambiar(PASO)"
    >
      +
    </button>
  </div>
</template>

<style scoped>
.duracion-pausa {
  display: flex;
  align-items: center;
  height: 40px;
  margin-top: 6px;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--panel);
  overflow: hidden;
}

.duracion-pausa:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--ring);
}

.duracion-valor {
  flex: 1;
  min-width: 0;
  text-align: center;
  font-size: 14px;
  font-weight: 400;
  color: var(--text);
}

button.duracion-paso:not(.tarjeta):not(.celda) {
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
  margin: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--text);
  font-size: 18px;
  line-height: 1;
}

button.duracion-paso:not(.tarjeta):not(.celda):hover:not(:disabled) {
  background: var(--libranza-bg);
  border-color: transparent;
}

button.duracion-paso:not(.tarjeta):not(.celda):disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
</style>
