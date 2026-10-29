import { pedir } from "./cliente.js";

export function semanaActual() {
  const texto = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Madrid",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
  const [anio, mes, dia] = texto.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  const ordinal = fecha.getUTCDay() || 7;
  fecha.setUTCDate(fecha.getUTCDate() - (ordinal - 1));
  const mesLunes = String(fecha.getUTCMonth() + 1).padStart(2, "0");
  const diaLunes = String(fecha.getUTCDate()).padStart(2, "0");
  return `${fecha.getUTCFullYear()}-${mesLunes}-${diaLunes}`;
}

export function semana(token, desde, propia, departamentoId) {
  let ruta = "/turnos";
  if (propia) {
    ruta = desde === semanaActual() ? "/turnos/departamento" : "/turnos/mios";
  }
  const consulta = new URLSearchParams({ desde });
  if (!propia && departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  return pedir(`${ruta}?${consulta}`, { token });
}

export function mes(token, anio, mesNumero, propia, departamentoId) {
  const ruta = propia ? "/turnos/mios/mes" : "/turnos/mes";
  const consulta = new URLSearchParams({ anio: String(anio), mes: String(mesNumero) });
  if (!propia && departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  return pedir(`${ruta}?${consulta}`, { token });
}

export async function exportarCuadrante(token, parametros) {
  const consulta = new URLSearchParams(parametros);
  const respuesta = await fetch(`/turnos/exportar?${consulta}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(20000),
  });
  if (!respuesta.ok) {
    let texto = `Error ${respuesta.status}`;
    try {
      const cuerpo = await respuesta.json();
      if (cuerpo && cuerpo.error) {
        texto = String(cuerpo.error);
      }
    } catch {
      // El cuerpo no es JSON.
    }
    throw new Error(texto);
  }
  const blob = await respuesta.blob();
  const disposicion = respuesta.headers.get("Content-Disposition") || "";
  const coincidencia = /filename="?([^";]+)"?/.exec(disposicion);
  const nombre = coincidencia ? coincidencia[1] : "cuadrante.xlsx";
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}

export function copiarSemana(token, desde, departamentoId) {
  const cuerpo = { desde };
  if (departamentoId) {
    cuerpo.departamento_id = departamentoId;
  }
  return pedir("/turnos/copiar-semana", {
    method: "POST",
    token,
    cuerpo,
  });
}

export function guardarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "PUT", token, cuerpo });
}

export function borrarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "DELETE", token, cuerpo });
}

export function semanaMandos(token, desde) {
  return pedir(`/turnos/mandos?desde=${desde}`, { token });
}

export function mesMandos(token, anio, mesNumero) {
  return pedir(`/turnos/mandos/mes?anio=${anio}&mes=${mesNumero}`, { token });
}

export function vacacionesMando(token, cuerpo) {
  return pedir("/turnos/mandos/vacaciones", { method: "PUT", token, cuerpo });
}
