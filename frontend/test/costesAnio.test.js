import assert from "node:assert/strict";
import test from "node:test";

import { agregarMeses } from "../src/costesAnio.js";

function dia(ausencia, planificadas, nocturnas) {
  return {
    turno: {
      ausencia,
      horas_planificadas: planificadas,
      horas_nocturnas: nocturnas,
    },
  };
}

test("agrega dos meses y deja sin importe al ETT sin tarifa", () => {
  const ana = {
    nombre: "Ana",
    login: "ana",
    grupo: "ETT",
    seccion: "Nacional",
    coste: 10,
    tarifa_nocturna: null,
  };
  const luis = {
    nombre: "Luis",
    login: "luis",
    grupo: "ETT",
    seccion: "Nacional",
    coste: null,
    tarifa_nocturna: null,
  };
  const meses = Array.from({ length: 12 }, () => null);
  meses[0] = {
    trabajadores: [
      { ...ana, dias: [dia(null, 8, 0)] },
      { ...luis, dias: [dia(null, 8, 0)] },
      { nombre: "Stef", login: "stef", grupo: "STEF", dias: [dia(null, 8, 0)] },
    ],
  };
  meses[1] = {
    trabajadores: [{ ...ana, dias: [dia(null, 7, 4)] }],
  };

  const { filas, totalesMes, total } = agregarMeses(meses);

  assert.deepEqual(
    filas.map((fila) => fila.login),
    ["ana", "luis"],
  );
  assert.equal(filas[0].meses[0].diurnas, 8);
  assert.equal(filas[0].meses[0].nocturnas, 0);
  assert.equal(filas[0].meses[0].importe, 80);
  assert.equal(filas[0].meses[1].diurnas, 3);
  assert.equal(filas[0].meses[1].nocturnas, 4);
  assert.equal(filas[0].meses[1].importe, 70);
  assert.equal(filas[0].meses[1].sinTarifaNocturna, true);
  assert.equal(filas[0].total, 150);
  assert.equal(filas[0].sinTarifaNocturna, true);
  assert.equal(filas[1].meses[0].importe, null);
  assert.equal(filas[1].total, 0);
  assert.equal(totalesMes[0], 80);
  assert.equal(totalesMes[1], 70);
  assert.equal(total, 150);
});
