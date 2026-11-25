<script setup>
defineProps({
  mensajes: { type: Array, required: true },
});
defineEmits(["cerrar"]);
</script>

<template>
  <div class="aviso" role="status">
    <div>
      <p v-for="texto in mensajes" :key="texto">{{ texto }}</p>
    </div>
    <button type="button" class="aviso-cerrar" aria-label="Cerrar aviso" @click="$emit('cerrar')">×</button>
  </div>
</template>

<style scoped>
.aviso {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 8px;
  padding: 8px 12px;
  border: 1px solid #ead88a;
  border-radius: 8px;
  background: var(--warn-bg);
  color: var(--warn);
  font-size: 13px;
}

.aviso p {
  margin: 0;
}

.aviso p + p {
  margin-top: 4px;
}

button.aviso-cerrar:not(.tarjeta):not(.celda) {
  flex: none;
  margin: 0;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--warn);
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
}

button.aviso-cerrar:not(.tarjeta):not(.celda):hover {
  border-color: transparent;
  background: transparent;
  color: var(--warn);
}
</style>
