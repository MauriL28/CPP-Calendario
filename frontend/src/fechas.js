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

const DELEGACIONES = {
  "60I": "San Sebastián",
  "05I": "Irún",
};

const ROLES = {
  admin: "Administrador",
  mando: "Mando",
  trabajador: "Trabajador",
};

export function delegacionVisible(codigo) {
  const nombre = DELEGACIONES[codigo];
  return nombre ? `${codigo} ${nombre}` : codigo;
}

export function rolVisible(rol) {
  return ROLES[rol] || rol;
}

const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export function numeroSemanaIso(iso) {
  const [anio, mes, dia] = iso.split("-").map(Number);
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  const diaSemana = fecha.getUTCDay() || 7;
  fecha.setUTCDate(fecha.getUTCDate() + 4 - diaSemana);
  const inicio = new Date(Date.UTC(fecha.getUTCFullYear(), 0, 1));
  return Math.ceil((fecha - inicio) / 86400000 / 7 + 1 / 7);
}

export function rangoSemana(desde, hasta) {
  return `Semana ${numeroSemanaIso(desde)} · ${diaMes(desde)} – ${diaMes(hasta)}`;
}

function diaMes(iso) {
  const [, mes, dia] = iso.split("-").map(Number);
  return `${dia} ${MESES[mes - 1]}`;
}

export function fechaVisible(iso) {
  const [anio, mes, dia] = iso.split("-");
  return `${dia}/${mes}/${anio}`;
}

function horaCompacta(hora) {
  const [horas, minutos] = hora.split(":");
  const texto = String(Number(horas));
  if (Number(minutos) === 0) {
    return texto;
  }
  return `${texto}:${minutos}`;
}

export function textoCelda(turno) {
  if (!turno) {
    return "";
  }
  if (turno.ausencia) {
    return turno.ausencia;
  }
  return `${horaCompacta(turno.hora_inicio)}-${horaCompacta(turno.hora_fin)}`;
}
