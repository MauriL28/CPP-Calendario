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
const turnoLogin = ref("");
const turnoFecha = ref("");
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoAusencia = ref("L");
const errorTurno = ref("");

async function entrar() {
  errorLogin.value = "";
  error.value = "";
  rol.value = "";
  delegaciones.value = [];
  departamentos.value = [];
  token.value = "";
  errorMando.value = "";
  errorTrabajador.value = "";
  errorTurno.value = "";
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
    elegirTrabajadorSiFalta();
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

function trabajadoresDelMando() {
  return departamentos.value.flatMap((departamento) => departamento.trabajadores);
}

function elegirTrabajadorSiFalta() {
  const lista = trabajadoresDelMando();
  if (!lista.some((trabajador) => trabajador.login === turnoLogin.value)) {
    turnoLogin.value = lista[0]?.login ?? "";
  }
}

function textoTurno(turno) {
  const horas = `${turno.horas_planificadas} h, ${turno.horas_nocturnas} h noche`;
  if (turno.ausencia) {
    return `${turno.fecha} ausencia ${turno.ausencia} (${horas})`;
  }
  return `${turno.fecha} ${turno.hora_inicio}–${turno.hora_fin} (${horas})`;
}

async function guardarTurno() {
  errorTurno.value = "";
  const cuerpo = {
    login: turnoLogin.value,
    fecha: turnoFecha.value,
  };
  if (turnoModo.value === "ausencia") {
    cuerpo.ausencia = turnoAusencia.value;
  } else {
    cuerpo.hora_inicio = turnoInicio.value;
    cuerpo.hora_fin = turnoFin.value;
  }
  try {
    const respuesta = await fetch("/turnos", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify(cuerpo),
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorTurno.value = await mensajeDeError(respuesta);
      return;
    }
    await cargarDepartamentos(token.value);
  } catch (causa) {
    errorTurno.value = causa instanceof Error ? causa.message : "No se pudo guardar el turno";
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
    <form v-if="rol === 'mando'" class="alta" @submit.prevent="guardarTurno">
      <label>
        Trabajador
        <select v-model="turnoLogin">
          <option v-for="trabajador in trabajadoresDelMando()" :key="trabajador.login" :value="trabajador.login">
            {{ trabajador.nombre }}
          </option>
        </select>
      </label>
      <label>
        Día
        <input v-model="turnoFecha" name="fecha" type="date" required />
      </label>
      <label>
        Tipo
        <select v-model="turnoModo">
          <option value="horario">Horario</option>
          <option value="ausencia">Ausencia</option>
        </select>
      </label>
      <template v-if="turnoModo === 'horario'">
        <label>
          Hora inicio
          <input v-model="turnoInicio" name="hora-inicio" type="time" required />
        </label>
        <label>
          Hora fin
          <input v-model="turnoFin" name="hora-fin" type="time" required />
        </label>
      </template>
      <label v-else>
        Ausencia
        <select v-model="turnoAusencia">
          <option v-for="codigo in ['L', 'D', 'V', 'B', 'F', 'P']" :key="codigo" :value="codigo">
            {{ codigo }}
          </option>
        </select>
      </label>
      <button type="submit">Guardar turno</button>
    </form>
    <p v-if="errorTurno" class="error">{{ errorTurno }}</p>
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
              <ul v-if="trabajador.turnos.length">
                <li v-for="turno in trabajador.turnos" :key="turno.fecha">{{ textoTurno(turno) }}</li>
              </ul>
            </li>
          </ul>
        </li>
      </ul>
    </section>
  </main>
</template>
