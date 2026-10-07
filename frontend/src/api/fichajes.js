import { pedir } from "./cliente.js";

function consultaAnalisis(filtros) {
  const consulta = new URLSearchParams();
  if (filtros.departamento) {
    consulta.set("departamento_id", filtros.departamento);
  }
  if (filtros.coincide) {
    consulta.set("coincide", filtros.coincide);
  }
  if (filtros.desde) {
    consulta.set("desde", filtros.desde);
  }
  if (filtros.hasta) {
    consulta.set("hasta", filtros.hasta);
  }
  return consulta.toString();
}

export function analisisFichajes(token, filtros) {
  const qs = consultaAnalisis(filtros);
  return pedir(`/fichajes/analisis${qs ? `?${qs}` : ""}`, { token });
}

export async function exportarAnalisis(token, filtros) {
  const qs = consultaAnalisis(filtros);
  const respuesta = await fetch(`/fichajes/analisis/exportar${qs ? `?${qs}` : ""}`, {
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
  const nombre = coincidencia ? coincidencia[1] : "analisis.xlsx";
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = nombre;
  enlace.click();
  URL.revokeObjectURL(url);
}

export function importarFichajes(token, archivo) {
  const formulario = new FormData();
  formulario.append("archivo", archivo);
  return pedir("/fichajes/importar", {
    method: "POST",
    token,
    formulario,
    espera: 60000,
  });
}
