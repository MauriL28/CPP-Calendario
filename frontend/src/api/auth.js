import { pedir } from "./cliente.js";

export async function entrar(login, clave) {
  const cuerpo = await pedir("/login", {
    method: "POST",
    cuerpo: { login, clave },
  });
  const carga = datosDelToken(cuerpo.access_token);
  return {
    token: cuerpo.access_token,
    login,
    rol: carga.rol,
    nombre: carga.nombre,
    departamento: carga.departamento || "",
    delegaciones: carga.delegaciones,
  };
}

function datosDelToken(token) {
  const carga = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = carga + "=".repeat((4 - (carga.length % 4)) % 4);
  return JSON.parse(atob(padded));
}
