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
const semanaDesde = ref("");
const cuadrante = ref(null);
const errorSemana = ref("");
const celda = ref(null);
const turnoModo = ref("horario");
const turnoInicio = ref("");
const turnoFin = ref("");
const turnoAusencia = ref("L");
const errorTurno = ref("");
const diasNombre = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];

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
  errorSemana.value = "";
  cuadrante.value = null;
  celda.value = null;
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
    if (carga.rol === "trabajador") {
      await cargarSemana(lunesDe(new Date()));
    } else {
      await cargarDepartamentos(cuerpo.access_token);
      alCambiarDelegacion();
      if (carga.rol === "mando") {
        await cargarSemana(lunesDe(new Date()));
      }
    }
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
    if (rol.value === "mando") {
      await cargarSemana(semanaDesde.value || lunesDe(new Date()));
    }
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function isoFecha(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

function lunesDe(fecha) {
  const copia = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  const dia = copia.getDay();
  const resto = dia === 0 ? -6 : 1 - dia;
  copia.setDate(copia.getDate() + resto);
  return isoFecha(copia);
}

function sumarDias(iso, dias) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(anio, mes - 1, dia);
  fecha.setDate(fecha.getDate() + dias);
  return isoFecha(fecha);
}

function textoCelda(turno) {
  if (!turno) {
    return "";
  }
  if (turno.ausencia) {
    return turno.ausencia;
  }
  return `${turno.hora_inicio}–${turno.hora_fin}`;
}

async function cargarSemana(desde) {
  errorSemana.value = "";
  celda.value = null;
  try {
    const ruta = rol.value === "trabajador" ? "/turnos/mios" : "/turnos";
    const respuesta = await fetch(`${ruta}?desde=${desde}`, {
      headers: { Authorization: `Bearer ${token.value}` },
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorSemana.value = await mensajeDeError(respuesta);
      return;
    }
    cuadrante.value = await respuesta.json();
    semanaDesde.value = cuadrante.value.desde;
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo cargar la semana";
  }
}

function abrirCelda(trabajador, dia) {
  const turno = dia.turno;
  celda.value = {
    login: trabajador.login,
    nombre: trabajador.nombre,
    fecha: dia.fecha,
  };
  errorTurno.value = "";
  if (turno && turno.ausencia) {
    turnoModo.value = "ausencia";
    turnoAusencia.value = turno.ausencia;
    turnoInicio.value = "";
    turnoFin.value = "";
  } else {
    turnoModo.value = "horario";
    turnoAusencia.value = "L";
    turnoInicio.value = turno?.hora_inicio || "";
    turnoFin.value = turno?.hora_fin || "";
  }
}

async function copiarSemana() {
  errorSemana.value = "";
  try {
    const respuesta = await fetch("/turnos/copiar-semana", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify({ desde: semanaDesde.value }),
      signal: AbortSignal.timeout(8000),
    });
    if (!respuesta.ok) {
      errorSemana.value = await mensajeDeError(respuesta);
      return;
    }
    await cargarSemana(semanaDesde.value);
  } catch (causa) {
    errorSemana.value = causa instanceof Error ? causa.message : "No se pudo copiar la semana";
  }
}

async function guardarTurno() {
  if (!celda.value) {
    return;
  }
  errorTurno.value = "";
  const cuerpo = {
    login: celda.value.login,
    fecha: celda.value.fecha,
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
    await cargarSemana(semanaDesde.value);
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
    <section v-if="(rol === 'mando' || rol === 'trabajador') && cuadrante" class="semana">
      <div class="semana-nav">
        <button type="button" @click="cargarSemana(sumarDias(semanaDesde, -7))">Semana anterior</button>
        <span>{{ cuadrante.desde }} – {{ cuadrante.dias[6] }}</span>
        <button type="button" @click="cargarSemana(sumarDias(semanaDesde, 7))">Semana siguiente</button>
        <button v-if="rol === 'mando'" type="button" @click="copiarSemana">Copiar semana anterior</button>
      </div>
      <p v-if="errorSemana" class="error">{{ errorSemana }}</p>
      <table>
        <thead>
          <tr>
            <th>Trabajador</th>
            <th v-for="(dia, indice) in cuadrante.dias" :key="dia">
              {{ diasNombre[indice] }} {{ dia.slice(8) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="trabajador in cuadrante.trabajadores" :key="trabajador.login">
            <th>{{ trabajador.nombre }}</th>
            <td v-for="dia in trabajador.dias" :key="dia.fecha">
              <button
                v-if="rol === 'mando'"
                type="button"
                class="celda"
                @click="abrirCelda(trabajador, dia)"
              >
                {{ textoCelda(dia.turno) }}
              </button>
              <span v-else class="celda">{{ textoCelda(dia.turno) }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <form v-if="celda" class="alta" @submit.prevent="guardarTurno">
        <p>{{ celda.nombre }} · {{ celda.fecha }}</p>
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
            <input v-model="turnoInicio" type="time" required />
          </label>
          <label>
            Hora fin
            <input v-model="turnoFin" type="time" required />
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
    </section>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="rol !== 'trabajador'">
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
    </template>
  </main>
</template>
