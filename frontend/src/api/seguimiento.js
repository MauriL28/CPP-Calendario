import { pedir } from "./cliente.js";

export function obtener(token, semana, departamentoId) {
  const consulta = new URLSearchParams({ semana });
  if (departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  return pedir(`/seguimiento?${consulta}`, { token });
}

export function borrar(token, semana, departamentoId, magnitud) {
  const consulta = new URLSearchParams({ semana });
  if (departamentoId) {
    consulta.set("departamento_id", departamentoId);
  }
  if (magnitud) {
    consulta.set("magnitud", magnitud);
  }
  return pedir(`/seguimiento?${consulta}`, { method: "DELETE", token });
}

export function guardar(token, semana, departamentoId, cuerpo) {
  const datos = { semana, ...cuerpo };
  if (departamentoId) {
    datos.departamento_id = departamentoId;
  }
  return pedir("/seguimiento", { method: "PUT", token, cuerpo: datos });
}
