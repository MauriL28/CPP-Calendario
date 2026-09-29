<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { listar } from "../api/departamentos.js";
import { cambiarHorario, crearTrabajador, darDeBaja as pedirBaja } from "../api/usuarios.js";
import Cuadrante from "./Cuadrante.vue";

const props = defineProps({
  token: { type: String, required: true },
});

const vista = ref("cuadrante");
const cuadrante = ref(null);
const departamentos = ref([]);
const error = ref("");
const nombre = ref("");
const login = ref("");
const clave = ref("");
const grupo = ref("STEF");
const letras = ["L", "M", "X", "J", "V", "S", "D"];
const diasMarcados = ref([true, true, true, true, true, false, false]);
const horasDia = ref(letras.map(() => ({ inicio: "", fin: "" })));
const plantillaDia = ref(null);
const propios = ref(letras.map(() => false));
const vacaciones = ref("");
const horasContrato = ref("");
const errorTrabajador = ref("");
const dialogo = ref(null);
const dialogoHorario = ref(null);
const trabajadorHorario = ref(null);
const desdeHorario = ref("");
const diasHorario = ref([true, true, true, true, true, false, false]);
const horasHorario = ref(letras.map(() => ({ inicio: "", fin: "" })));
const plantillaHorario = ref(null);
const propiosHorario = ref(letras.map(() => false));
const errorHorario = ref("");
const aviso = ref(false);
const busqueda = ref("");
const filtroGrupo = ref("");
let avisoTemporizador = 0;

const equipo = computed(() => departamentos.value[0] || null);
const trabajadores = computed(() => equipo.value?.trabajadores ?? []);
const filtrados = computed(() => {
  const texto = busqueda.value.trim().toLocaleLowerCase("es");
  return trabajadores.value.filter((trabajador) => {
    if (filtroGrupo.value && trabajador.grupo !== filtroGrupo.value) {
      return false;
    }
    if (!texto) {
      return true;
    }
    const nombreVisible = trabajador.nombre.toLocaleLowerCase("es");
    const loginVisible = trabajador.login.toLocaleLowerCase("es");
    return nombreVisible.includes(texto) || loginVisible.includes(texto);
  });
});

function iniciales(texto) {
  const palabras = texto.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  return palabras
    .slice(0, 2)
    .map((parte) => parte[0].toLocaleUpperCase("es"))
    .join("");
}

async function cargarDepartamentos() {
  error.value = "";
  try {
    departamentos.value = await listar(props.token);
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudieron cargar los departamentos";
  }
}

function reiniciarHorario() {
  diasMarcados.value = [true, true, true, true, true, false, false];
  horasDia.value = letras.map(() => ({ inicio: "", fin: "" }));
  plantillaDia.value = null;
  propios.value = letras.map(() => false);
}

function vaciarAlta() {
  nombre.value = "";
  login.value = "";
  clave.value = "";
  grupo.value = "STEF";
  reiniciarHorario();
  vacaciones.value = "";
  horasContrato.value = "";
  errorTrabajador.value = "";
}

function alMarcar(dia, evento) {
  const marcado = evento.target.checked;
  diasMarcados.value[dia] = marcado;
  if (!marcado || plantillaDia.value === null || propios.value[dia]) {
    return;
  }
  const origen = horasDia.value[plantillaDia.value];
  horasDia.value[dia] = { inicio: origen.inicio, fin: origen.fin };
}

function alHora(dia, campo, valor) {
  const actual = horasDia.value[dia];
  horasDia.value[dia] = { ...actual, [campo]: valor };
  if (plantillaDia.value === null) {
    plantillaDia.value = dia;
  } else if (dia !== plantillaDia.value) {
    propios.value[dia] = true;
    return;
  }
  const origen = horasDia.value[dia];
  horasDia.value = horasDia.value.map((item, indice) => {
    if (indice === dia) {
      return origen;
    }
    if (!diasMarcados.value[indice] || propios.value[indice]) {
      return item;
    }
    return { inicio: origen.inicio, fin: origen.fin };
  });
}

function abrirAlta() {
  vaciarAlta();
  dialogo.value?.showModal();
  dialogo.value?.querySelector("[name='nombre-trabajador']")?.focus();
}

function cerrarAlta() {
  dialogo.value?.close();
}

function alCerrarAlta() {
  vaciarAlta();
}

function alFondo(evento) {
  if (evento.target === dialogo.value) {
    cerrarAlta();
  }
}

function mostrarAviso() {
  aviso.value = true;
  window.clearTimeout(avisoTemporizador);
  avisoTemporizador = window.setTimeout(() => {
    aviso.value = false;
  }, 3000);
}

function horario(trabajador) {
  const dias = [...(trabajador.horario || [])].sort((a, b) => a.dia_semana - b.dia_semana);
  if (!dias.length) {
    return "—";
  }
  const grupos = [];
  for (const dia of dias) {
    const ultimo = grupos[grupos.length - 1];
    const sigue = ultimo
      && dia.inicio === ultimo.inicio
      && dia.fin === ultimo.fin
      && dia.dia_semana === ultimo.hasta + 1;
    if (sigue) {
      ultimo.hasta = dia.dia_semana;
    } else {
      grupos.push({
        desde: dia.dia_semana,
        hasta: dia.dia_semana,
        inicio: dia.inicio,
        fin: dia.fin,
      });
    }
  }
  return grupos
    .map((grupoDia) => {
      const rango = grupoDia.desde === grupoDia.hasta
        ? letras[grupoDia.desde]
        : `${letras[grupoDia.desde]}-${letras[grupoDia.hasta]}`;
      return `${rango} ${grupoDia.inicio}–${grupoDia.fin}`;
    })
    .join(", ");
}

function cantidad(valor) {
  if (valor === null || valor === undefined) {
    return "—";
  }
  return Number(valor).toLocaleString("es-ES");
}

function cuenta(total) {
  return total === 1 ? "1 trabajador" : `${total} trabajadores`;
}

function fechaLocal(dia) {
  const mes = String(dia.getMonth() + 1).padStart(2, "0");
  const numero = String(dia.getDate()).padStart(2, "0");
  return `${dia.getFullYear()}-${mes}-${numero}`;
}

function hoyIso() {
  return fechaLocal(new Date());
}

function lunesQueViene() {
  const hoy = new Date();
  hoy.setHours(12, 0, 0, 0);
  const salto = hoy.getDay() === 1 ? 0 : (8 - hoy.getDay()) % 7;
  hoy.setDate(hoy.getDate() + salto);
  return fechaLocal(hoy);
}

function abrirHorario(trabajador) {
  trabajadorHorario.value = trabajador;
  desdeHorario.value = lunesQueViene();
  errorHorario.value = "";
  const marcados = letras.map(() => false);
  const horas = letras.map(() => ({ inicio: "", fin: "" }));
  const propio = letras.map(() => false);
  let plantilla = null;
  for (const dia of trabajador.horario || []) {
    if (dia.dia_semana < 0 || dia.dia_semana > 6) {
      continue;
    }
    marcados[dia.dia_semana] = true;
    horas[dia.dia_semana] = { inicio: dia.inicio || "", fin: dia.fin || "" };
    propio[dia.dia_semana] = true;
    if (plantilla === null) {
      plantilla = dia.dia_semana;
    }
  }
  diasHorario.value = marcados;
  horasHorario.value = horas;
  propiosHorario.value = propio;
  plantillaHorario.value = plantilla;
  dialogoHorario.value?.showModal();
  dialogoHorario.value?.querySelector("[name='desde-horario']")?.focus();
}

function cerrarHorario() {
  dialogoHorario.value?.close();
}

function alCerrarHorario() {
  trabajadorHorario.value = null;
  errorHorario.value = "";
}

function alFondoHorario(evento) {
  if (evento.target === dialogoHorario.value) {
    cerrarHorario();
  }
}

function alMarcarHorario(dia, evento) {
  const marcado = evento.target.checked;
  diasHorario.value[dia] = marcado;
  if (!marcado || plantillaHorario.value === null || propiosHorario.value[dia]) {
    return;
  }
  const origen = horasHorario.value[plantillaHorario.value];
  horasHorario.value[dia] = { inicio: origen.inicio, fin: origen.fin };
}

function alHoraHorario(dia, campo, valor) {
  const actual = horasHorario.value[dia];
  horasHorario.value[dia] = { ...actual, [campo]: valor };
  if (plantillaHorario.value === null) {
    plantillaHorario.value = dia;
  } else if (dia !== plantillaHorario.value) {
    propiosHorario.value[dia] = true;
    return;
  }
  const origen = horasHorario.value[dia];
  horasHorario.value = horasHorario.value.map((item, indice) => {
    if (indice === dia) {
      return origen;
    }
    if (!diasHorario.value[indice] || propiosHorario.value[indice]) {
      return item;
    }
    return { inicio: origen.inicio, fin: origen.fin };
  });
}

async function guardarHorario() {
  errorHorario.value = "";
  const persona = trabajadorHorario.value;
  if (!persona) {
    return;
  }
  if (!desdeHorario.value) {
    errorHorario.value = "Indica desde qué fecha aplica.";
    return;
  }
  if (desdeHorario.value < hoyIso()) {
    errorHorario.value = "La fecha no puede ser anterior a hoy.";
    return;
  }
  const horarioDias = [];
  for (let dia = 0; dia < letras.length; dia += 1) {
    if (!diasHorario.value[dia]) {
      continue;
    }
    const horas = horasHorario.value[dia];
    if (!horas.inicio || !horas.fin) {
      errorHorario.value = "Indica la hora de inicio y de fin de cada día marcado.";
      return;
    }
    horarioDias.push({
      dia_semana: dia,
      hora_inicio: horas.inicio,
      hora_fin: horas.fin,
    });
  }
  if (!horarioDias.length) {
    errorHorario.value = "Marca al menos un día.";
    return;
  }
  try {
    await cambiarHorario(props.token, persona.login, {
      desde: desdeHorario.value,
      horario_dias: horarioDias,
    });
    cerrarHorario();
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorHorario.value = causa instanceof Error ? causa.message : "No se pudo cambiar el horario";
  }
}

async function darDeBaja(trabajador) {
  if (!window.confirm(`¿Dar de baja a ${trabajador.nombre}?`)) {
    return;
  }
  error.value = "";
  try {
    await pedirBaja(props.token, trabajador.login);
    const lista = equipo.value?.trabajadores;
    if (!lista) {
      return;
    }
    const indice = lista.findIndex((item) => item.login === trabajador.login);
    if (indice >= 0) {
      lista.splice(indice, 1);
    }
  } catch (causa) {
    error.value = causa instanceof Error ? causa.message : "No se pudo dar de baja";
  }
}

async function guardar() {
  errorTrabajador.value = "";
  const horarioDias = [];
  for (let dia = 0; dia < letras.length; dia += 1) {
    if (!diasMarcados.value[dia]) {
      continue;
    }
    const horas = horasDia.value[dia];
    if (!horas.inicio || !horas.fin) {
      errorTrabajador.value = "Indica la hora de inicio y de fin de cada día marcado.";
      return;
    }
    horarioDias.push({
      dia_semana: dia,
      hora_inicio: horas.inicio,
      hora_fin: horas.fin,
    });
  }
  if (!horarioDias.length) {
    errorTrabajador.value = "Marca al menos un día.";
    return;
  }
  try {
    await crearTrabajador(props.token, {
      nombre: nombre.value,
      login: login.value,
      clave: clave.value,
      grupo: grupo.value,
      horario_dias: horarioDias,
      vacaciones: numero(vacaciones.value),
      horas_contrato: numero(horasContrato.value),
    });
    cerrarAlta();
    mostrarAviso();
    await cargarDepartamentos();
    await cuadrante.value?.recargar();
  } catch (causa) {
    errorTrabajador.value = causa instanceof Error ? causa.message : "No se pudo crear el trabajador";
  }
}

function numero(valor) {
  if (valor === "" || valor === null) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
}

watch(vista, (nueva) => {
  if (nueva !== "equipo" && dialogo.value?.open) {
    cerrarAlta();
  }
  if (nueva !== "equipo" && dialogoHorario.value?.open) {
    cerrarHorario();
  }
});

onMounted(cargarDepartamentos);
</script>

<template>
  <nav class="vistas">
    <button type="button" :class="{ activo: vista === 'cuadrante' }" @click="vista = 'cuadrante'">
      Cuadrante
    </button>
    <button type="button" :class="{ activo: vista === 'equipo' }" @click="vista = 'equipo'">
      Equipo
    </button>
  </nav>
  <Cuadrante v-show="vista === 'cuadrante'" ref="cuadrante" :token="token" editable />
  <section v-if="vista === 'equipo'" class="equipo">
    <header class="equipo-intro">
      <h1>Equipo</h1>
      <p>Personas de tu departamento. Son las filas de tu cuadrante.</p>
    </header>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div v-else-if="equipo && !trabajadores.length" class="panel equipo-vacio">
      <strong>Aún no hay trabajadores en tu departamento</strong>
      <p>Añade el primero para empezar a montar el cuadrante.</p>
      <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
    </div>
    <template v-else-if="equipo">
      <div class="equipo-barra">
        <input v-model="busqueda" class="equipo-buscar" type="search" placeholder="Buscar trabajador..." />
        <select v-model="filtroGrupo" class="equipo-grupo">
          <option value="">Todos los grupos</option>
          <option value="STEF">STEF</option>
          <option value="ETT">ETT</option>
        </select>
        <button type="button" class="primario" @click="abrirAlta">+ Añadir trabajador</button>
      </div>
      <section class="panel">
        <header class="panel-cabecera">
          <h2>{{ cuenta(filtrados.length) }}</h2>
        </header>
        <p v-if="!filtrados.length" class="panel-vacio">Ningún trabajador coincide con la búsqueda.</p>
        <table v-else class="equipo">
          <thead>
            <tr>
              <th>Trabajador</th>
              <th>Grupo</th>
              <th>Horario</th>
              <th class="col-extra">Horas/semana</th>
              <th class="col-extra">Vacaciones/año</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="trabajador in filtrados" :key="trabajador.login">
              <td>
                <span class="equipo-persona">
                  <span class="avatar">{{ iniciales(trabajador.nombre) }}</span>
                  <span class="persona-datos">
                    <strong>{{ trabajador.nombre }}</strong>
                    <span>{{ trabajador.login }}</span>
                  </span>
                </span>
              </td>
              <td>
                <span class="grupo-pastilla" :class="trabajador.grupo === 'ETT' ? 'grupo-ett' : 'grupo-stef'">
                  {{ trabajador.grupo }}
                </span>
              </td>
              <td>{{ horario(trabajador) }}</td>
              <td class="col-extra">{{ cantidad(trabajador.horas_contrato) }}</td>
              <td class="col-extra">{{ cantidad(trabajador.vacaciones) }}</td>
              <td class="equipo-acciones">
                <button type="button" @click="abrirHorario(trabajador)">Cambiar horario</button>
                <button type="button" @click="darDeBaja(trabajador)">Dar de baja</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </section>
  <dialog ref="dialogo" class="alta-dialogo" @close="alCerrarAlta" @click="alFondo">
      <form @submit.prevent="guardar">
        <header class="alta-dialogo-cabecera">
          <h2>Alta de trabajador</h2>
          <button type="button" class="dialogo-cerrar" @click="cerrarAlta">✕</button>
        </header>
        <div class="alta-dialogo-cuerpo">
          <h3>Acceso</h3>
          <label>
            Nombre
            <input v-model="nombre" name="nombre-trabajador" />
          </label>
          <label>
            Login
            <input v-model="login" name="login-trabajador" autocomplete="off" />
          </label>
          <label class="ancho">
            Clave
            <input v-model="clave" name="clave-trabajador" type="password" autocomplete="new-password" />
          </label>
          <h3>Contrato</h3>
          <div class="alta-tres">
            <label>
              Grupo
              <select v-model="grupo">
                <option value="STEF">STEF</option>
                <option value="ETT">ETT</option>
              </select>
            </label>
            <label>
              Horas/semana
              <input v-model="horasContrato" name="horas-contrato" type="number" min="0" step="0.5" />
            </label>
            <label>
              Vacaciones (días/año)
              <input v-model="vacaciones" name="vacaciones" type="number" min="0" step="0.5" />
            </label>
          </div>
          <h3>Horario habitual</h3>
          <div class="ancho alta-dias-marcas">
            <label v-for="(letra, dia) in letras" :key="letra" class="alta-casilla">
              <input
                type="checkbox"
                :checked="diasMarcados[dia]"
                @change="alMarcar(dia, $event)"
              />
              {{ letra }}
            </label>
          </div>
          <div
            v-for="(letra, dia) in letras"
            v-show="diasMarcados[dia]"
            :key="`horas-${letra}`"
            class="ancho alta-dia-horas"
          >
            <span>{{ letra }}</span>
            <label>
              Hora de inicio
              <input
                :value="horasDia[dia].inicio"
                type="time"
                @input="alHora(dia, 'inicio', $event.target.value)"
              />
            </label>
            <label>
              Hora de fin
              <input
                :value="horasDia[dia].fin"
                type="time"
                @input="alHora(dia, 'fin', $event.target.value)"
              />
            </label>
          </div>
        </div>
        <p v-if="errorTrabajador" class="error" role="alert">{{ errorTrabajador }}</p>
        <footer class="alta-dialogo-pie">
          <button type="button" @click="cerrarAlta">Cancelar</button>
          <button class="primario" type="submit">Guardar trabajador</button>
        </footer>
      </form>
  </dialog>
  <dialog ref="dialogoHorario" class="alta-dialogo" @close="alCerrarHorario" @click="alFondoHorario">
    <form @submit.prevent="guardarHorario">
      <header class="alta-dialogo-cabecera">
        <div>
          <h2>Cambiar horario</h2>
          <p v-if="trabajadorHorario" class="alta-dialogo-persona">{{ trabajadorHorario.nombre }}</p>
        </div>
        <button type="button" class="dialogo-cerrar" @click="cerrarHorario">✕</button>
      </header>
      <div class="alta-dialogo-cuerpo">
        <label class="ancho">
          Desde
          <input v-model="desdeHorario" name="desde-horario" type="date" :min="hoyIso()" />
        </label>
        <div class="ancho alta-dias-marcas">
          <label v-for="(letra, dia) in letras" :key="`cambio-${letra}`" class="alta-casilla">
            <input
              type="checkbox"
              :checked="diasHorario[dia]"
              @change="alMarcarHorario(dia, $event)"
            />
            {{ letra }}
          </label>
        </div>
        <div
          v-for="(letra, dia) in letras"
          v-show="diasHorario[dia]"
          :key="`cambio-horas-${letra}`"
          class="ancho alta-dia-horas"
        >
          <span>{{ letra }}</span>
          <label>
            Hora de inicio
            <input
              :value="horasHorario[dia].inicio"
              type="time"
              @input="alHoraHorario(dia, 'inicio', $event.target.value)"
            />
          </label>
          <label>
            Hora de fin
            <input
              :value="horasHorario[dia].fin"
              type="time"
              @input="alHoraHorario(dia, 'fin', $event.target.value)"
            />
          </label>
        </div>
      </div>
      <p v-if="errorHorario" class="error" role="alert">{{ errorHorario }}</p>
      <footer class="alta-dialogo-pie">
        <button type="button" @click="cerrarHorario">Cancelar</button>
        <button class="primario" type="submit">Guardar horario</button>
      </footer>
    </form>
  </dialog>
  <p v-if="aviso" class="aviso-ok" role="status">Trabajador creado</p>
</template>
