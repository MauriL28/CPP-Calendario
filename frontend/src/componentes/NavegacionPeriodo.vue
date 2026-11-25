<script setup>
defineProps({
  anterior: { type: String, required: true },
  siguiente: { type: String, required: true },
});

defineEmits(["anterior", "siguiente"]);
</script>

<template>
  <button type="button" :title="anterior" :aria-label="anterior" @click="$emit('anterior')">‹</button>
  <span class="rango"><slot /></span>
  <button type="button" :title="siguiente" :aria-label="siguiente" @click="$emit('siguiente')">›</button>
</template>
