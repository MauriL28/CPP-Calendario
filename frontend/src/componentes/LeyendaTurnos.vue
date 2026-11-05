<script setup>
const items = [
  { id: "manana", nombre: "Mañana" },
  { id: "tarde", nombre: "Tarde" },
  { id: "noche", nombre: "Noche" },
  { id: "libranza", nombre: "Libranza" },
  { id: "domingo", nombre: "Domingo" },
  { id: "vacaciones", nombre: "Vacaciones" },
  { id: "baja", nombre: "Baja" },
  { id: "festivo", nombre: "Festivo" },
  { id: "permiso", nombre: "Permiso" },
  { id: "vacaciones", codigo: "SR", nombre: "Sábado recuperado" },
  { id: "vacaciones", codigo: "FR", nombre: "Festivo recuperado" },
  { id: "permiso", codigo: "HS", nombre: "Horas sindicales" },
  { id: "permiso", codigo: "PEND", nombre: "Pendientes año anterior" },
  { id: "festivo", codigo: "ST", nombre: "Sábado trabajado" },
  { id: "festivo", codigo: "FT", nombre: "Festivo trabajado" },
];
</script>

<template>
  <ul class="leyenda">
    <li v-for="item in items" :key="item.codigo || item.id">
      <span class="muestra" :class="[`turno-${item.id}`, { 'muestra-largo': item.codigo && item.codigo.length > 2 }]">{{ item.codigo }}</span>
      {{ item.nombre }}
    </li>
  </ul>
</template>

<style scoped>
.leyenda {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 8px 16px;
  min-width: 0;
  max-width: 100%;
  padding: 0;
  list-style: none;
}

.leyenda li {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  font-size: 13px;
  line-height: 1.2;
  break-inside: avoid;
}

.leyenda .muestra {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 5px;
  font-size: 9px;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.leyenda .muestra-largo {
  letter-spacing: -1.3px;
}

@media print {
  .leyenda li {
    break-inside: avoid;
  }

  .leyenda .muestra {
    border-color: #333;
    print-color-adjust: exact;
    -webkit-print-color-adjust: exact;
  }
}
</style>
