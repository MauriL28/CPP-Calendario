import { pedir } from "./cliente.js";

export function analisisFichajes(token, filtros) {
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
  const qs = consulta.toString();
  return pedir(`/fichajes/analisis${qs ? `?${qs}` : ""}`, { token });
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
