import { pedir } from "./cliente.js";

export function listar(token) {
  return pedir("/departamentos", { token });
}
