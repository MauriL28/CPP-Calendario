const ausenciasConCoste = new Set([null, "ST", "FT"]);
const euros = new Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" });

export function horasPeriodo(trabajador, campo, ausencias) {
  return (trabajador.dias || []).reduce((total, dia) => {
    if (ausencias && !ausencias.has(dia.turno?.ausencia ?? null)) {
      return total;
    }
    return total + (Number(dia.turno?.[campo]) || 0);
  }, 0);
}

export function horasQueCuentan(trabajador) {
  return horasPeriodo(trabajador, "horas_planificadas", ausenciasConCoste);
}

export function horasNocturnas(trabajador) {
  return (trabajador.dias || []).reduce((total, dia) => {
    const turno = dia.turno;
    if (!ausenciasConCoste.has(turno?.ausencia ?? null)) {
      return total;
    }
    const planificadas = Number(turno?.horas_planificadas) || 0;
    const nocturnas = Number(turno?.horas_nocturnas) || 0;
    return total + Math.min(nocturnas, planificadas);
  }, 0);
}

export function horasDiurnas(trabajador) {
  return horasQueCuentan(trabajador) - horasNocturnas(trabajador);
}

function tarifaPresente(valor) {
  if (valor === null || valor === undefined || valor === "") {
    return false;
  }
  return Number.isFinite(Number(valor));
}

export function tieneCoste(trabajador) {
  return tarifaPresente(trabajador.coste);
}

export function tieneTarifaNocturna(trabajador) {
  return tarifaPresente(trabajador.tarifa_nocturna);
}

export function importeTrabajador(trabajador) {
  const nocturnas = horasNocturnas(trabajador);
  const sinTarifaNocturna = nocturnas > 0 && !tieneTarifaNocturna(trabajador);
  if (trabajador.grupo !== "ETT" || !tieneCoste(trabajador)) {
    return { importe: null, sinTarifaNocturna };
  }
  const coste = Number(trabajador.coste);
  const tarifaNoche = tieneTarifaNocturna(trabajador) ? Number(trabajador.tarifa_nocturna) : coste;
  return {
    importe: horasDiurnas(trabajador) * coste + nocturnas * tarifaNoche,
    sinTarifaNocturna,
  };
}

export function totalGrupo(trabajadores) {
  return trabajadores.reduce(
    (resumen, trabajador) => {
      const { importe, sinTarifaNocturna } = importeTrabajador(trabajador);
      resumen.total += importe || 0;
      if (!tieneCoste(trabajador)) {
        resumen.sinCoste += 1;
      }
      if (sinTarifaNocturna) {
        resumen.sinTarifaNocturna += 1;
      }
      return resumen;
    },
    { total: 0, sinCoste: 0, sinTarifaNocturna: 0 },
  );
}

export function formatoEuros(valor) {
  return euros.format(valor);
}
