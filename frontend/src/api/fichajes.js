import { pedir } from "./cliente.js";

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
