<script setup>
defineProps({
  delegaciones: { type: Array, required: true },
  departamentos: { type: Array, required: true },
});

function de(delegacion, departamentos) {
  return departamentos.filter((departamento) => departamento.delegacion === delegacion);
}
</script>

<template>
  <section v-for="codigo in delegaciones" :key="codigo" class="delegacion">
    <h2>Delegación: {{ codigo }}</h2>
    <ul class="departamentos">
      <li v-for="departamento in de(codigo, departamentos)" :key="departamento.codigo">
        <h3>{{ departamento.nombre }}</h3>
        <ul v-if="departamento.secciones.length" class="secciones">
          <li v-for="seccion in departamento.secciones" :key="seccion.nombre">
            {{ seccion.nombre }}
          </li>
        </ul>
        <ul v-if="departamento.mandos.length" class="mandos">
          <li v-for="mando in departamento.mandos" :key="mando.login">
            {{ mando.nombre }} ({{ mando.login }})
          </li>
        </ul>
        <ul v-if="departamento.trabajadores.length" class="mandos">
          <li v-for="trabajador in departamento.trabajadores" :key="trabajador.login">
            {{ trabajador.nombre }} ({{ trabajador.login }}, {{ trabajador.grupo }})
          </li>
        </ul>
      </li>
    </ul>
  </section>
</template>
