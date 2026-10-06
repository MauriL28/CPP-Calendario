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
    throw new Error(await mensaje(respuesta));
  }
  if (respuesta.status === 204) {
    return null;
  }
  return respuesta.json();
}

async function mensaje(respuesta) {
  try {
    const cuerpo = await respuesta.json();
    if (cuerpo && cuerpo.error) {
      return String(cuerpo.error);
    }
  } catch {
    // El cuerpo no es JSON.
  }
  return `Error ${respuesta.status}`;
}
