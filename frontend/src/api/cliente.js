export async function pedir(ruta, { method = "GET", token, cuerpo } = {}) {
  const headers = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (cuerpo !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const respuesta = await fetch(ruta, {
    method,
    headers,
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    signal: AbortSignal.timeout(8000),
  });
  if (!respuesta.ok) {
    throw new Error(await mensaje(respuesta));
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
