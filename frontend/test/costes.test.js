import assert from "node:assert/strict";
import test from "node:test";

import {
  horasDiurnas,
  horasNocturnas,
  horasQueCuentan,
  importeTrabajador,
  totalGrupo,
} from "../src/costes.js";

function dia(ausencia, planificadas, nocturnas) {
  return {
    turno: {
      ausencia,
      horas_planificadas: planificadas,
      horas_nocturnas: nocturnas,
    },
  };
}

function trabajador(dias, extra = {}) {
  return {
    grupo: "ETT",
    coste: 10,
    tarifa_nocturna: null,
    dias,
    ...extra,
  };
}

test("un turno de 14 a 22 se cobra entero a tarifa diurna", () => {
  const persona = trabajador([dia(null, 8, 0)]);
  const { importe, sinTarifaNocturna } = importeTrabajador(persona);
  assert.equal(horasNocturnas(persona), 0);
  assert.equal(horasDiurnas(persona), 8);
  assert.equal(importe, 80);
  assert.equal(sinTarifaNocturna, false);
});

test("un 22-6 con pausa no deja las diurnas en negativo", () => {
  const persona = trabajador([dia(null, 7, 8)]);
  assert.equal(horasNocturnas(persona), 7);
  assert.equal(horasDiurnas(persona), 0);
});

test("un 18-02 reparte 3 diurnas y 4 nocturnas", () => {
  const persona = trabajador([dia(null, 7, 4)]);
  assert.equal(horasDiurnas(persona), 3);
  assert.equal(horasNocturnas(persona), 4);
});

test("la tarifa diurna y la nocturna se aplican cada una a sus horas", () => {
  const persona = trabajador([dia(null, 7, 4)], { tarifa_nocturna: 15 });
  assert.equal(importeTrabajador(persona).importe, 3 * 10 + 4 * 15);
});

test("sin tarifa nocturna las horas nocturnas se calculan a diurna", () => {
  const persona = trabajador([dia(null, 7, 4)]);
  const { importe, sinTarifaNocturna } = importeTrabajador(persona);
  assert.equal(importe, 7 * 10);
  assert.equal(sinTarifaNocturna, true);
});

test("sin horas nocturnas no marca la tarifa nocturna como ausente", () => {
  const persona = trabajador([dia(null, 8, 0)]);
  assert.equal(importeTrabajador(persona).sinTarifaNocturna, false);
});

test("sin coste el importe es null", () => {
  const persona = trabajador([dia(null, 8, 0)], { coste: null });
  assert.equal(importeTrabajador(persona).importe, null);
});

test("la vacación y el día sin turno no suman; ST y FT sí", () => {
  const persona = trabajador([
    dia("V", 7.5, 0),
    { turno: null },
    dia("ST", 7.5, 0),
    dia("FT", 7.5, 0),
  ]);
  assert.equal(horasQueCuentan(persona), 15);
  assert.equal(horasNocturnas(persona), 0);
  assert.equal(horasDiurnas(persona), 15);
});

test("totalGrupo cuenta el que no tiene coste y el que no tiene tarifa nocturna", () => {
  const conAmbas = trabajador([dia(null, 7, 4)], { tarifa_nocturna: 15 });
  const sinCoste = trabajador([dia(null, 8, 0)], { coste: null });
  const sinNocturna = trabajador([dia(null, 7, 4)]);
  assert.deepEqual(totalGrupo([conAmbas, sinCoste, sinNocturna]), {
    total: 3 * 10 + 4 * 15 + 7 * 10,
    sinCoste: 1,
    sinTarifaNocturna: 1,
  });
});
