import { avisarSesionInvalida } from "../sesion.js";

export async function pedir(ruta, { method = "GET", token, cuerpo, formulario, espera = 8000 } = {}) {
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  let body;
  if (formulario !== undefined) {
    body = formulario;
  } else if (cuerpo !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(cuerpo);
  }
  const respuesta = await fetch(ruta, {
    method,
    headers,
    body,
    signal: AbortSignal.timeout(espera),
  });
  if (!respuesta.ok) {
    const cuerpoRespuesta = await leerCuerpo(respuesta);
    if (esFalloDeSesion(respuesta.status, cuerpoRespuesta, Boolean(token))) {
      avisarSesionInvalida();
    }
    throw new Error(textoError(cuerpoRespuesta, respuesta));
  }
  if (respuesta.status === 204) {
    return null;
  }
  return respuesta.json();
}

export function esFalloDeSesion(status, cuerpo, habiaToken) {
  if (!habiaToken || status !== 401 || !cuerpo) {
    return false;
  }
  return cuerpo.msg === "Token has expired" || cuerpo.msg === "Token has been revoked";
}

async function leerCuerpo(respuesta) {
  try {
    return await respuesta.json();
  } catch {
    return null;
  }
}

function textoError(cuerpo, respuesta) {
  if (cuerpo && cuerpo.error) {
    return String(cuerpo.error);
  }
  if (cuerpo && cuerpo.msg) {
    return String(cuerpo.msg);
  }
  return `Error ${respuesta.status}`;
}
