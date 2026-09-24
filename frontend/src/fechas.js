export function isoFecha(fecha) {
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

export function lunesDe(fecha) {
  const copia = new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
  const dia = copia.getDay();
  const resto = dia === 0 ? -6 : 1 - dia;
  copia.setDate(copia.getDate() + resto);
  return isoFecha(copia);
}

export function sumarDias(iso, dias) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(anio, mes - 1, dia);
  fecha.setDate(fecha.getDate() + dias);
  return isoFecha(fecha);
}

export function textoCelda(turno) {
  if (!turno) {
    return "";
  }
  if (turno.ausencia) {
    return turno.ausencia;
  }
  return `${turno.hora_inicio}–${turno.hora_fin}`;
}
