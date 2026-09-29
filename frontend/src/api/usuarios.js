import { pedir } from "./cliente.js";

export function crearMando(token, datos) {
  return pedir("/usuarios", { method: "POST", token, cuerpo: datos });
}

export function crearTrabajador(token, datos) {
  return pedir("/trabajadores", { method: "POST", token, cuerpo: datos });
}

export function cambiarHorario(token, login, datos) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/horario`, {
    method: "PUT",
    token,
    cuerpo: datos,
  });
}

export function darDeBaja(token, login) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/baja`, {
    method: "PUT",
    token,
    cuerpo: {},
  });
}
