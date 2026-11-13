const CLAVE = "stef365.token";

let alPerder = () => {};
let avisado = false;

export function alPerderSesion(accion) {
  alPerder = accion;
}

export function avisarSesionInvalida() {
  if (avisado) {
    return;
  }
  avisado = true;
  alPerder();
}

export function rearmarAvisoSesion() {
  avisado = false;
}

export function guardarToken(token, storage = localStorage) {
  storage.setItem(CLAVE, token);
}

export function leerToken(storage = localStorage) {
  return storage.getItem(CLAVE);
}

export function borrarToken(storage = localStorage) {
  storage.removeItem(CLAVE);
}

export function datosDelToken(token) {
  const carga = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  const padded = carga + "=".repeat((4 - (carga.length % 4)) % 4);
  const binario = atob(padded);
  const bytes = Uint8Array.from(binario, (caracter) => caracter.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes));
}

export function sesionDesdeToken(token) {
  if (!token) {
    return null;
  }
  let carga;
  try {
    carga = datosDelToken(token);
  } catch {
    return null;
  }
  if (typeof carga.exp !== "number" || carga.exp * 1000 <= Date.now()) {
    return null;
  }
  if (!carga.rol) {
    return null;
  }
  return {
    token,
    login: carga.login || "",
    rol: carga.rol,
    nombre: carga.nombre || "",
    departamento: carga.departamento || "",
    delegaciones: Array.isArray(carga.delegaciones) ? carga.delegaciones : [],
  };
}

export async function cerrarSesion(token, pedirSalir, storage = localStorage) {
  borrarToken(storage);
  if (!token) {
    return;
  }
  try {
    await pedirSalir(token);
  } catch {
    // El token local ya no está, aunque el servidor no haya respondido.
  }
}
