import { pedir } from "./cliente.js";

export function listarFestivos(token) {
  return pedir("/festivos", { token });
}

export function crearFestivo(token, datos) {
  return pedir("/festivos", { method: "POST", token, cuerpo: datos });
}

export function borrarFestivo(token, fecha) {
  return pedir(`/festivos/${encodeURIComponent(fecha)}`, { method: "DELETE", token });
}
