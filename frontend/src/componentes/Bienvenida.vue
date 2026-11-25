<script setup>
import { ref } from "vue";
import { datosDelToken } from "../sesion.js";

const props = defineProps({
  token: { type: String, required: true },
  titulo: { type: String, required: true },
  detalle: { type: String, required: true },
});

function clave() {
  try {
    const id = datosDelToken(props.token)?.sub;
    return id ? `stef365.bienvenida.${id}` : "";
  } catch {
    return "";
  }
}

function estabaCerrada() {
  const id = clave();
  if (!id) {
    return false;
  }
  try {
    return localStorage.getItem(id) === "1";
  } catch {
    return false;
  }
}

const visible = ref(estabaCerrada() === false);

function cerrar() {
  visible.value = false;
  const id = clave();
  if (!id) {
    return;
  }
  try {
    localStorage.setItem(id, "1");
  } catch {
    // Esta visita queda cerrada aunque el navegador no guarde la preferencia.
  }
}
</script>

<template>
  <section v-if="visible" class="bienvenida">
    <div>
      <p class="bienvenida-titulo">{{ titulo }}</p>
      <p class="bienvenida-detalle">{{ detalle }}</p>
    </div>
    <button type="button" class="bienvenida-cerrar" aria-label="Cerrar bienvenida" @click="cerrar">×</button>
  </section>
</template>
