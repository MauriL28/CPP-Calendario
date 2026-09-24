import { pedir } from "./cliente.js";

export function crearMando(token, datos) {
  return pedir("/usuarios", { method: "POST", token, cuerpo: datos });
}

export function crearTrabajador(token, datos) {
  return pedir("/trabajadores", { method: "POST", token, cuerpo: datos });
}
