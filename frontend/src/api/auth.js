import { pedir } from "./cliente.js";
import { datosDelToken } from "../sesion.js";

export async function entrar(login, clave) {
  const cuerpo = await pedir("/login", {
    method: "POST",
    cuerpo: { login, clave },
  });
  const carga = datosDelToken(cuerpo.access_token);
  return {
    token: cuerpo.access_token,
    login: carga.login || login,
    rol: carga.rol,
    nombre: carga.nombre,
    departamento: carga.departamento || "",
    delegaciones: carga.delegaciones,
  };
}

export function salir(token) {
  return pedir("/logout", { method: "POST", token });
}
