import { pedir } from "./cliente.js";

export function semana(token, desde, propia) {
  const ruta = propia ? "/turnos/mios" : "/turnos";
  return pedir(`${ruta}?desde=${desde}`, { token });
}

export function mes(token, anio, mesNumero, propia) {
  const ruta = propia ? "/turnos/mios/mes" : "/turnos/mes";
  return pedir(`${ruta}?anio=${anio}&mes=${mesNumero}`, { token });
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

export function borrarTurno(token, cuerpo) {
  return pedir("/turnos", { method: "DELETE", token, cuerpo });
}
