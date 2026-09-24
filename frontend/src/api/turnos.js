import { pedir } from "./cliente.js";

export function semana(token, desde, propia) {
  const ruta = propia ? "/turnos/mios" : "/turnos";
  return pedir(`${ruta}?desde=${desde}`, { token });
}

export function copiarSemana(token, desde) {
  return pedir("/turnos/copiar-semana", {
    method: "POST",
    token,
    cuerpo: { desde },
  });
}

export function guardarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "PUT", token, cuerpo });
}
