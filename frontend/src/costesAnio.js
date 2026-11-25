import { horasDiurnas, horasNocturnas, importeTrabajador } from "./costes.js";

const cacheMeses = new Map();

export function claveMesCache(departamentoId, anio, mes) {
  return `${departamentoId}|${anio}|${mes}`;
}

export function leerMesCache(clave) {
  return cacheMeses.get(clave);
}

export function guardarMesCache(clave, datos) {
  cacheMeses.set(clave, datos);
}

export function agregarMeses(meses) {
  const porLogin = new Map();
  meses.forEach((datos, indice) => {
    for (const trabajador of datos?.trabajadores || []) {
      if (trabajador.grupo !== "ETT") {
        continue;
      }
      let fila = porLogin.get(trabajador.login);
      if (!fila) {
        fila = {
          login: trabajador.login,
          nombre: trabajador.nombre,
          seccion: trabajador.seccion || "",
          grupo: "ETT",
          coste: trabajador.coste,
          tarifa_nocturna: trabajador.tarifa_nocturna,
          meses: Array.from({ length: 12 }, () => null),
        };
        porLogin.set(trabajador.login, fila);
      }
      fila.nombre = trabajador.nombre;
      fila.seccion = trabajador.seccion || fila.seccion;
      fila.coste = trabajador.coste;
      fila.tarifa_nocturna = trabajador.tarifa_nocturna;
      const { importe, sinTarifaNocturna } = importeTrabajador(trabajador);
      fila.meses[indice] = {
        diurnas: horasDiurnas(trabajador),
        nocturnas: horasNocturnas(trabajador),
        importe,
        sinTarifaNocturna,
      };
    }
  });
  const filas = [...porLogin.values()]
    .map((fila) => ({
      ...fila,
      total: fila.meses.reduce((suma, mes) => suma + (mes?.importe || 0), 0),
      sinTarifaNocturna: fila.meses.some((mes) => mes?.sinTarifaNocturna),
    }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
  const totales = totalesDe(filas);
  return { filas, ...totales };
}

export function totalesDe(filas) {
  const totalesMes = Array.from({ length: 12 }, (_, indice) =>
    filas.reduce((suma, fila) => suma + (fila.meses[indice]?.importe || 0), 0),
  );
  return {
    totalesMes,
    total: totalesMes.reduce((suma, valor) => suma + valor, 0),
  };
}

export function horasDeFila(fila) {
  return fila.meses.reduce(
    (suma, mes) => {
      suma.diurnas += mes?.diurnas || 0;
      suma.nocturnas += mes?.nocturnas || 0;
      return suma;
    },
    { diurnas: 0, nocturnas: 0 },
  );
}
