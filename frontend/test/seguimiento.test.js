import assert from "node:assert/strict";
import test from "node:test";

import {
  celdasDesdeDetalle,
  detalleDesdeCeldas,
  parsearPrevision,
  ratioSeguimiento,
  textoDesdeDetalle,
} from "../src/seguimiento.js";

const EJEMPLO =
  "Prévision 2026\t1126870\t13777\t143718\t213675\t166712\t168205\t420783";
const DIAS = [13777, 143718, 213675, 166712, 168205, 420783];

test("la fila de ejemplo trae nombre, total y los seis días", () => {
  const fila = parsearPrevision(`  ${EJEMPLO}  `);
  assert.equal(fila.error, undefined);
  assert.equal(fila.nombre, "Prévision 2026");
  assert.equal(fila.total, 1126870);
  assert.deepEqual(fila.dias, DIAS);
  assert.equal(fila.aviso, "");
});

test("acepta miles con punto y con espacio", () => {
  const conPunto =
    "Prévision 2026\t1.126.870\t13.777\t143.718\t213.675\t166.712\t168.205\t420.783";
  const conEspacio =
    "Prevision 2026\t1 126 870\t13 777\t143 718\t213 675\t166 712\t168 205\t420 783";
  for (const texto of [conPunto, conEspacio]) {
    const fila = parsearPrevision(texto);
    assert.equal(fila.total, 1126870);
    assert.deepEqual(fila.dias, DIAS);
    assert.equal(fila.aviso, "");
  }
});

test("con varias líneas usa la que empieza por Prévision", () => {
  const texto = ["Otra fila\t10\t1\t1\t1\t1\t1\t1", EJEMPLO, "Total de la semana"].join("\n");
  const fila = parsearPrevision(texto);
  assert.equal(fila.nombre, "Prévision 2026");
  assert.equal(fila.total, 1126870);
  assert.deepEqual(fila.dias, DIAS);
});

test("un total que no suma devuelve aviso y la fila", () => {
  const fila = parsearPrevision("Prévision 2026\t100\t1\t1\t1\t1\t1\t1");
  assert.equal(fila.error, undefined);
  assert.equal(fila.total, 100);
  assert.deepEqual(fila.dias, [1, 1, 1, 1, 1, 1]);
  assert.equal(fila.aviso, "El total no coincide con la suma de los días.");
});

test("menos de seis días es un error", () => {
  const fila = parsearPrevision("Prévision 2026\t100\t10\t20\t30");
  assert.equal(fila.error, "Hacen falta 6 valores (lunes a sábado) o 7 con el total.");
  assert.equal(fila.total, undefined);
});

test("acepta 6 o 7 números, con nombre o sin él", () => {
  const seis = parsearPrevision(DIAS.join("\t"));
  assert.equal(seis.nombre, "Previsión");
  assert.equal(seis.total, DIAS.reduce((suma, dia) => suma + dia, 0));
  assert.deepEqual(seis.dias, DIAS);
  assert.equal(seis.aviso, "");

  const siete = parsearPrevision(["1126870", ...DIAS].join("\t"));
  assert.equal(siete.nombre, "Previsión");
  assert.equal(siete.total, 1126870);
  assert.deepEqual(siete.dias, DIAS);
  assert.equal(siete.aviso, "");

  const correction = parsearPrevision(["Correction", ...DIAS].join("\t"));
  assert.equal(correction.nombre, "Correction");
  assert.deepEqual(correction.dias, DIAS);
  assert.equal(correction.aviso, "");

  assert.equal(
    parsearPrevision([1, 2, 3, 4, 5].join("\t")).error,
    "Hacen falta 6 valores (lunes a sábado) o 7 con el total.",
  );
  assert.equal(
    parsearPrevision([1, 2, 3, 4, 5, 6, 7, 8].join("\t")).error,
    "Hacen falta 6 valores (lunes a sábado) o 7 con el total.",
  );

  const conPunto = parsearPrevision(
    "1.126.870\t13.777\t143.718\t213.675\t166.712\t168.205\t420.783",
  );
  assert.equal(conPunto.nombre, "Previsión");
  assert.equal(conPunto.total, 1126870);
  assert.deepEqual(conPunto.dias, DIAS);
});

test("el texto vacío es un error", () => {
  assert.equal(parsearPrevision("").error, "Pega la fila de previsión.");
  assert.equal(parsearPrevision("  \n  ").error, "Pega la fila de previsión.");
});


test("reconstruye el texto pegado desde el detalle", () => {
  const detalle = {
    filas: [
      { nombre: "Otra", total: 6, dias: [1, 1, 1, 1, 1, 1] },
      { nombre: "Prévision 2026", total: 1126870, dias: DIAS },
    ],
  };
  const texto = textoDesdeDetalle(detalle, "Prévision 2026");
  assert.equal(texto, EJEMPLO);
  assert.deepEqual(parsearPrevision(texto).dias, DIAS);
  assert.equal(textoDesdeDetalle(null, null), "");
  assert.equal(textoDesdeDetalle({ filas: [] }, "Prévision 2026"), "");
});

test("las celdas y el detalle se convierten en los dos sentidos", () => {
  const celdas = DIAS.map(String);
  const construido = detalleDesdeCeldas(celdas, "Prévision 2026");
  assert.equal(construido.error, undefined);
  assert.equal(construido.nombre, "Prévision 2026");
  assert.equal(construido.total, DIAS.reduce((suma, dia) => suma + dia, 0));
  assert.deepEqual(construido.detalle, {
    filas: [{ nombre: "Prévision 2026", total: construido.total, dias: DIAS }],
  });
  assert.equal(construido.fila_base, "Prévision 2026");

  const sinNombre = detalleDesdeCeldas(celdas, "");
  assert.equal(sinNombre.nombre, "Previsión");
  assert.equal(sinNombre.fila_base, "Previsión");

  const vuelta = celdasDesdeDetalle(construido.detalle, construido.fila_base);
  assert.equal(vuelta.nombre, "Prévision 2026");
  assert.deepEqual(vuelta.dias, celdas);
  assert.equal(vuelta.total, construido.total);
  assert.deepEqual(celdasDesdeDetalle(null, null).dias, ["", "", "", "", "", ""]);
});

test("950 toneladas entre 374 horas dan 2,54 t/h", () => {
  const { ratio, motivo } = ratioSeguimiento(950, 374);
  assert.equal(ratio, 2.54);
  assert.equal(motivo, "");
});

test("sin horas el ratio no se calcula", () => {
  const { ratio, motivo } = ratioSeguimiento(950, 0);
  assert.equal(ratio, null);
  assert.equal(motivo, "No hay horas planificadas esta semana.");
});

test("sin toneladas el ratio no se calcula", () => {
  for (const vacio of ["", null, undefined]) {
    const { ratio, motivo } = ratioSeguimiento(vacio, 374);
    assert.equal(ratio, null);
    assert.equal(motivo, "No hay toneladas previstas.");
  }
});
