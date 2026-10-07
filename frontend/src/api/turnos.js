import { pedir } from "./cliente.js";

export function semana(token, desde, propia) {
  const ruta = propia ? "/turnos/mios" : "/turnos";
  return pedir(`${ruta}?desde=${desde}`, { token });
}

export function mes(token, anio, mesNumero, propia) {
  const ruta = propia ? "/turnos/mios/mes" : "/turnos/mes";
  return pedir(`${ruta}?anio=${anio}&mes=${mesNumero}`, { token });
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

export function copiarSemana(token, desde) {
  return pedir("/turnos/copiar-semana", {
    method: "POST",
    token,
    cuerpo: { desde },
  });
}

export function guardarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "PUT", token, cuerpo });
}

export function borrarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "DELETE", token, cuerpo });
}
