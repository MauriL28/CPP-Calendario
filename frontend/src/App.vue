<script setup>
import { ref } from "vue";

const departamentos = ref([]);
const error = ref("");
const usuario = ref("");
const clave = ref("");
const errorLogin = ref("");
const rol = ref("");
const delegaciones = ref([]);
const token = ref("");
const nuevaDelegacion = ref("");
const nuevoDepartamento = ref("");
const nuevoNombre = ref("");
const nuevoLogin = ref("");
const nuevaClave = ref("");
const errorMando = ref("");
const trabajadorNombre = ref("");
const trabajadorLogin = ref("");
const trabajadorClave = ref("");
const trabajadorGrupo = ref("STEF");
const errorTrabajador = ref("");

async function entrar() {
  errorLogin.value = "";
  error.value = "";
  rol.value = "";
  delegaciones.value = [];
  departamentos.value = [];
  token.value = "";
  errorMando.value = "";
  errorTrabajador.value = "";
  try {
    const respuesta = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ login: usuario.value, clave: clave.value }),
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorLogin.value = await mensajeDeError(respuesta);
      return;
    }
    const cuerpo = await respuesta.json();
    const carga = cargaDelToken(cuerpo.access_token);
    rol.value = carga.rol;
    delegaciones.value = carga.delegaciones;
    token.value = cuerpo.access_token;
    nuevaDelegacion.value = carga.delegaciones[0] ?? "";
    await cargarDepartamentos(cuerpo.access_token);
    alCambiarDelegacion();
  } catch (causa) {
    errorLogin.value = causa instanceof Error ? causa.message : "No se pudo entrar";
  }
}

async function cargarDepartamentos(token) {
  try {
    const respuesta = await fetch("/departamentos", {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      error.value = await mensajeDeError(respuesta);
      return;
    }
    departamentos.value = await respuesta.json();
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

function alCambiarDelegacion() {
  const lista = departamentosDe(nuevaDelegacion.value);
  if (!lista.some((departamento) => departamento.codigo === nuevoDepartamento.value)) {
    nuevoDepartamento.value = lista[0]?.codigo ?? "";
  }
}

async function crearMando() {
  errorMando.value = "";
  try {
    const respuesta = await fetch("/usuarios", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify({
        nombre: nuevoNombre.value,
        login: nuevoLogin.value,
        clave: nuevaClave.value,
        delegacion: nuevaDelegacion.value,
        departamento: nuevoDepartamento.value,
      }),
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorMando.value = await mensajeDeError(respuesta);
      return;
    }
    nuevoNombre.value = "";
    nuevoLogin.value = "";
    nuevaClave.value = "";
    await cargarDepartamentos(token.value);
  } catch (causa) {
    errorMando.value = causa instanceof Error ? causa.message : "No se pudo crear el mando";
  }
}

async function crearTrabajador() {
  errorTrabajador.value = "";
  try {
    const respuesta = await fetch("/trabajadores", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify({
        nombre: trabajadorNombre.value,
        login: trabajadorLogin.value,
        clave: trabajadorClave.value,
        grupo: trabajadorGrupo.value,
      }),
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorTrabajador.value = await mensajeDeError(respuesta);
      return;
    }
    trabajadorNombre.value = "";
    trabajadorLogin.value = "";
    trabajadorClave.value = "";
    await cargarDepartamentos(token.value);
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function departamentosDe(codigo) {
  return departamentos.value.filter((departamento) => departamento.delegacion === codigo);
}

function cargaDelToken(token) {
  const carga = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = carga + "=".repeat((4 - (carga.length % 4)) % 4);
  return JSON.parse(atob(padded));
}

async function mensajeDeError(respuesta) {
  try {
    const cuerpo = await respuesta.json();
    if (cuerpo && cuerpo.error) {
      return String(cuerpo.error);
    }
  } catch {
    // El cuerpo no es JSON.
  }
  return `Error ${respuesta.status}`;
}
</script>

<template>
  <main>
    <h1>CPP-Calendario</h1>
    <form class="login" @submit.prevent="entrar">
      <label>
        Usuario
        <input v-model="usuario" name="usuario" autocomplete="username" />
      </label>
      <label>
        Clave
        <input v-model="clave" name="clave" type="password" autocomplete="current-password" />
      </label>
      <button type="submit">Entrar</button>
    </form>
    <p v-if="errorLogin" class="error">{{ errorLogin }}</p>
    <p v-if="rol">Rol: {{ rol }}</p>
    <form v-if="rol === 'admin'" class="alta" @submit.prevent="crearMando">
      <label>
        Delegación
        <select v-model="nuevaDelegacion" @change="alCambiarDelegacion">
          <option v-for="codigo in delegaciones" :key="codigo" :value="codigo">{{ codigo }}</option>
        </select>
      </label>
      <label>
        Departamento
        <select v-model="nuevoDepartamento">
          <option
            v-for="departamento in departamentosDe(nuevaDelegacion)"
            :key="departamento.codigo"
            :value="departamento.codigo"
          >
            {{ departamento.nombre }}
          </option>
        </select>
      </label>
      <label>
        Nombre
        <input v-model="nuevoNombre" name="nombre" />
      </label>
      <label>
        Login
        <input v-model="nuevoLogin" name="login" autocomplete="off" />
      </label>
      <label>
        Clave
        <input v-model="nuevaClave" name="clave-mando" type="password" autocomplete="new-password" />
      </label>
      <button type="submit">Guardar mando</button>
    </form>
    <p v-if="errorMando" class="error">{{ errorMando }}</p>
    <form v-if="rol === 'mando'" class="alta" @submit.prevent="crearTrabajador">
      <label>
        Nombre
        <input v-model="trabajadorNombre" name="nombre-trabajador" />
      </label>
      <label>
        Login
        <input v-model="trabajadorLogin" name="login-trabajador" autocomplete="off" />
      </label>
      <label>
        Clave
        <input v-model="trabajadorClave" name="clave-trabajador" type="password" autocomplete="new-password" />
      </label>
      <label>
        Grupo
        <select v-model="trabajadorGrupo">
          <option value="STEF">STEF</option>
          <option value="ETT">ETT</option>
        </select>
      </label>
      <button type="submit">Guardar trabajador</button>
    </form>
    <p v-if="errorTrabajador" class="error">{{ errorTrabajador }}</p>
    <p v-if="error" class="error">{{ error }}</p>
    <section v-for="codigo in delegaciones" :key="codigo">
      <h2>Delegación: {{ codigo }}</h2>
      <ul class="departamentos">
        <li v-for="departamento in departamentosDe(codigo)" :key="departamento.codigo">
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
  </main>
</template>
