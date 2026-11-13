import { pedir } from "./cliente.js";

export function crearMando(token, datos) {
  return pedir("/usuarios", { method: "POST", token, cuerpo: datos });
}

export function cambiarNumeroSapMando(token, login, numeroSap) {
  return pedir(`/usuarios/${encodeURIComponent(login)}/numero-sap`, {
    method: "PUT",
    token,
    cuerpo: { numero_sap: numeroSap },
  });
}

export function cambiarActivoMando(token, login, activo) {
  return pedir(`/usuarios/${encodeURIComponent(login)}/activo`, {
    method: "PUT",
    token,
    cuerpo: { activo },
  });
}

export function asignarDepartamentoMando(token, login, delegacion, departamento) {
  return pedir(`/usuarios/${encodeURIComponent(login)}/departamentos`, {
    method: "POST",
    token,
    cuerpo: { delegacion, departamento },
  });
}

export function quitarDepartamentoMando(token, login, departamentoId) {
  return pedir(
    `/usuarios/${encodeURIComponent(login)}/departamentos/${encodeURIComponent(departamentoId)}`,
    { method: "DELETE", token },
  );
}

export function editarUsuario(token, login, cambios) {
  return pedir(`/usuarios/${encodeURIComponent(login)}`, {
    method: "PUT",
    token,
    cuerpo: cambios,
  });
}

export function editarTrabajador(token, login, cambios) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}`, {
    method: "PUT",
    token,
    cuerpo: cambios,
  });
}

export function crearTrabajador(token, datos) {
  return pedir("/trabajadores", { method: "POST", token, cuerpo: datos });
}

export function cambiarSeccion(token, login, seccionId) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/seccion`, {
    method: "PUT",
    token,
    cuerpo: { seccion_id: seccionId },
  });
}

export function cambiarHorario(token, login, datos) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/horario`, {
    method: "PUT",
    token,
    cuerpo: datos,
  });
}

export function cambiarHorarioPropio(token, datos) {
  return pedir("/mandos/propio/horario", {
    method: "PUT",
    token,
    cuerpo: datos,
  });
}

export function cambiarHorarioMando(token, login, datos) {
  return pedir(`/usuarios/${encodeURIComponent(login)}/horario`, {
    method: "PUT",
    token,
    cuerpo: datos,
  });
}

export function cambiarNumeroSap(token, login, numeroSap) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/numero-sap`, {
    method: "PUT",
    token,
    cuerpo: { numero_sap: numeroSap },
  });
}

export function listarAjustes(token, login) {
  return pedir(`/ajustes?usuario_afectado=${encodeURIComponent(login)}`, { token });
}

export function crearAjuste(token, datos) {
  return pedir("/ajustes", { method: "POST", token, cuerpo: datos });
}

export function editarAjuste(token, id, datos) {
  return pedir(`/ajustes/${encodeURIComponent(id)}`, { method: "PUT", token, cuerpo: datos });
}

export function borrarAjuste(token, id) {
  return pedir(`/ajustes/${encodeURIComponent(id)}`, { method: "DELETE", token });
}

export function fichaTrabajador(token, login, anio) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/ficha?anio=${encodeURIComponent(anio)}`, {
    token,
  });
}

export function darDeBaja(token, login) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/baja`, {
    method: "PUT",
    token,
    cuerpo: {},
  });
}

export function listarInactivos(token, departamentoId) {
  const ruta = departamentoId
    ? `/trabajadores/inactivos?departamento_id=${encodeURIComponent(departamentoId)}`
    : "/trabajadores/inactivos";
  return pedir(ruta, { token });
}

export function reactivarTrabajador(token, login) {
  return pedir(`/trabajadores/${encodeURIComponent(login)}/alta`, {
    method: "PUT",
    token,
  });
}
