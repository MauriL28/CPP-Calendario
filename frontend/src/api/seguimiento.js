import { pedir } from "./cliente.js";

export function obtener(token, semana, departamentoId) {
  const consulta = new URLSearchParams({ semana });
  if (departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  return pedir(`/seguimiento?${consulta}`, { token });
}

export function borrar(token, semana, departamentoId) {
  const consulta = new URLSearchParams({ semana });
  if (departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  return pedir(`/seguimiento?${consulta}`, { method: "DELETE", token });
}

export function guardar(token, semana, toneladas, departamentoId, extra = {}) {
  const cuerpo = { semana, toneladas, ...extra };
  if (departamentoId) {
    cuerpo.departamento_id = departamentoId;
  }
  return pedir("/seguimiento", { method: "PUT", token, cuerpo });
}
