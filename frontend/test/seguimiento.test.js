import assert from "node:assert/strict";
import test from "node:test";

import {
  aplicarDias,
  celdasDesdeDetalle,
  cuerpoGuardado,
  detalleDesdeCeldas,
  detalleSeguimiento,
  desviacionSeguimiento,
  filasDesdeDetalle,
  lecturaSeguimiento,
  numeroSuelto,
  parsearPrevision,
  pegarSeguimiento,
  ratioReal,
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

test("de uno a seis números son días, sin total", () => {
  const fila = parsearPrevision("Prévision 2026\t100\t10\t20\t30");
  assert.equal(fila.error, undefined);
  assert.equal(fila.nombre, "Prévision 2026");
  assert.equal(fila.total, undefined);
  assert.deepEqual(fila.dias, [100, 10, 20, 30]);
});

test("acepta 6 o 7 números, con nombre o sin él", () => {
  const seis = parsearPrevision(DIAS.join("\t"));
  assert.equal(seis.nombre, "Previsión");
  assert.equal(seis.total, undefined);
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

  assert.deepEqual(parsearPrevision([1, 2, 3, 4, 5].join("\t")).dias, [1, 2, 3, 4, 5]);
  assert.equal(
    parsearPrevision([1, 2, 3, 4, 5, 6, 7, 8].join("\t")).error,
    "Hay 8 valores y solo caben seis días (lunes a sábado).",
  );

  const conPunto = parsearPrevision(
    "1.126.870\t13.777\t143.718\t213.675\t166.712\t168.205\t420.783",
  );
  assert.equal(conPunto.nombre, "Previsión");
  assert.equal(conPunto.total, 1126870);
  assert.deepEqual(conPunto.dias, DIAS);
});

test("sin tabulador el espacio y el punto y coma separan valores", () => {
  const seis = parsearPrevision("1 2 3 4 5 6");
  assert.equal(seis.error, undefined);
  assert.equal(seis.total, undefined);
  assert.deepEqual(seis.dias, [1, 2, 3, 4, 5, 6]);

  const cuatro = parsearPrevision("1 2 3 4");
  assert.deepEqual(cuatro.dias, [1, 2, 3, 4]);
  assert.equal(cuatro.total, undefined);

  assert.deepEqual(parsearPrevision("1;2;3").dias, [1, 2, 3]);
  assert.deepEqual(parsearPrevision("1,5").dias, [1.5]);

  const columna = parsearPrevision(["10", "20", "30", "40"].join("\n"));
  assert.equal(columna.total, undefined);
  assert.deepEqual(columna.dias, [10, 20, 30, 40]);

  const conAnio = "Prévision 2026 1126870 13777 143718 213675 166712 168205 420783";
  const sinTab = parsearPrevision(conAnio);
  assert.equal(sinTab.nombre, "Prévision 2026");
  assert.equal(sinTab.total, 1126870);
  assert.deepEqual(sinTab.dias, DIAS);
  assert.equal(sinTab.aviso, "");

  const conTab = parsearPrevision(
    "Prévision 2026\t1126870\t13777\t143718\t213675\t166712\t168205\t420783",
  );
  assert.equal(conTab.nombre, "Prévision 2026");
  assert.equal(conTab.total, 1126870);
  assert.deepEqual(conTab.dias, DIAS);

  const miles = parsearPrevision("1 126 870\t");
  assert.equal(miles.total, undefined);
  assert.deepEqual(miles.dias, [1126870]);

  assert.equal(parsearPrevision("Prévision semana").error, "Pega de 1 a 7 números separados por tabulador o espacio");
  assert.equal(parsearPrevision("hola").error, "Pega de 1 a 7 números separados por tabulador o espacio");
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

test("en una pegada de 4 filas previsión y real eligen la suya", () => {
  const prevision = ["Prévision 2026", 70, 10, 10, 10, 10, 10, 20].join("\t");
  const tonnage2025 = ["Tonnage 2025", 30, 5, 5, 5, 5, 5, 5].join("\t");
  const tonnage2026 = ["Tonnage 2026", 90, 15, 15, 15, 15, 15, 15].join("\t");
  const texto = [prevision, "Otra fila\t7\t1\t1\t1\t1\t1\t2", tonnage2025, tonnage2026].join("\n");

  const ambas = pegarSeguimiento(texto, null, 2026);
  assert.equal(ambas.prevision.nombre, "Prévision 2026");
  assert.deepEqual(ambas.prevision.dias, [10, 10, 10, 10, 10, 20]);
  assert.equal(ambas.real.nombre, "Tonnage 2026");
  assert.deepEqual(ambas.real.dias, [15, 15, 15, 15, 15, 15]);

  const conFocoEnPrevision = pegarSeguimiento(texto, "prevision", 2026);
  assert.deepEqual(conFocoEnPrevision.prevision.dias, [10, 10, 10, 10, 10, 20]);
  assert.equal(conFocoEnPrevision.real.nombre, "Tonnage 2026");

  const delAnioAnterior = pegarSeguimiento(texto, "real", 2025);
  assert.equal(delAnioAnterior.real.nombre, "Tonnage 2025");
  assert.deepEqual(delAnioAnterior.real.dias, [5, 5, 5, 5, 5, 5]);
  assert.equal(delAnioAnterior.prevision.nombre, "Prévision 2026");

  const sinAnio = [prevision, "Tonnage A\t12\t2\t2\t2\t2\t2\t2", "Tonnage B\t18\t3\t3\t3\t3\t3\t3"].join("\n");
  assert.equal(pegarSeguimiento(sinAnio, "real", 2026).real.nombre, "Tonnage B");
  const sinFoco = pegarSeguimiento([1, 2, 3, 4, 5, 6].join("\t"), null, 2026);
  assert.equal(sinFoco.real, undefined);
  assert.equal(sinFoco.prevision.total, undefined);
  assert.deepEqual(sinFoco.prevision.dias, [1, 2, 3, 4, 5, 6]);
});

test("una fila corta se escribe desde el foco y no pisa el resto", () => {
  const previas = ["9", "8", "7", "6", "5", "4"];
  const cuatro = parsearPrevision("10\t20\t30\t40");
  assert.equal(cuatro.total, undefined);
  assert.deepEqual(cuatro.dias, [10, 20, 30, 40]);

  const desdeLunes = aplicarDias(previas, cuatro.dias, null);
  assert.equal(desdeLunes.desde, 0);
  assert.equal(desdeLunes.escritos, 4);
  assert.equal(desdeLunes.sobran, 0);
  assert.deepEqual(desdeLunes.celdas, ["10", "20", "30", "40", "5", "4"]);

  const desdeJueves = aplicarDias(previas, cuatro.dias, 3);
  assert.equal(desdeJueves.desde, 3);
  assert.equal(desdeJueves.escritos, 3);
  assert.equal(desdeJueves.aviso, "Sobran 1 valores");
  assert.deepEqual(desdeJueves.indices, [3, 4, 5]);
  assert.deepEqual(desdeJueves.celdas, ["9", "8", "7", "10", "20", "30"]);

  const seis = parsearPrevision("1\t2\t3\t4\t5\t6");
  assert.equal(seis.total, undefined);
  assert.deepEqual(aplicarDias(previas, seis.dias, 3).celdas, ["1", "2", "3", "4", "5", "6"]);

  const conTotal = parsearPrevision("Prévision 2026\t21\t1\t2\t3\t4\t5\t6");
  assert.equal(conTotal.nombre, "Prévision 2026");
  assert.equal(conTotal.total, 21);
  assert.deepEqual(conTotal.dias, [1, 2, 3, 4, 5, 6]);
  assert.equal(conTotal.aviso, "");

  const sieteCuadra = parsearPrevision("21\t1\t2\t3\t4\t5\t6");
  assert.equal(sieteCuadra.total, 21);
  assert.deepEqual(sieteCuadra.dias, [1, 2, 3, 4, 5, 6]);

  const sieteNoCuadra = parsearPrevision("99\t1\t2\t3\t4\t5\t6");
  assert.equal(sieteNoCuadra.error, "Hay 7 valores y solo seis días (lunes a sábado)");
  assert.equal(sieteNoCuadra.dias, undefined);

  assert.equal(
    parsearPrevision("1\t2\t3\t4\t5\t6\t7\t8").error,
    "Hay 8 valores y solo caben seis días (lunes a sábado).",
  );

  const uno = parsearPrevision("42");
  assert.equal(uno.total, undefined);
  assert.deepEqual(uno.dias, [42]);
  assert.deepEqual(aplicarDias(previas, uno.dias, 2).celdas, ["9", "8", "42", "6", "5", "4"]);
});

test("el nombre reconocible manda sobre el foco y un número suelto no es una fila", () => {
  const tonnage = ["Tonnage 2026", 90, 15, 15, 15, 15, 15, 15].join("\t");
  const prevision = ["Prévision 2026", 70, 10, 10, 10, 10, 10, 20].join("\t");
  const correction = ["Correction", ...DIAS].join("\t");

  const aReal = pegarSeguimiento(tonnage, "prevision", 2026);
  assert.equal(aReal.prevision, undefined);
  assert.equal(aReal.real.nombre, "Tonnage 2026");

  const aPrevision = pegarSeguimiento(prevision, "real", 2026);
  assert.equal(aPrevision.real, undefined);
  assert.equal(aPrevision.prevision.nombre, "Prévision 2026");

  const correctionEnReal = pegarSeguimiento(correction, "real", 2026);
  assert.equal(correctionEnReal.prevision, undefined);
  assert.deepEqual(correctionEnReal.real.dias, DIAS);

  const correctionSinFoco = pegarSeguimiento(correction, null, 2026);
  assert.equal(correctionSinFoco.real, undefined);
  assert.equal(correctionSinFoco.prevision.nombre, "Correction");

  assert.equal(numeroSuelto("1.234"), 1234);
  assert.equal(numeroSuelto("1 234"), null);
  assert.equal(numeroSuelto("1,5"), 1.5);
  assert.equal(numeroSuelto("42"), 42);
  assert.equal(numeroSuelto("1\t2"), null);
  assert.equal(numeroSuelto("42\n"), null);
  assert.equal(pegarSeguimiento("1.234", "real", 2026).celda, 1234);
  assert.equal(pegarSeguimiento("1.234", "real", 2026, { magnitud: "pales" }).celda, 1234);
  assert.equal(pegarSeguimiento(tonnage, "prevision", 2026, { magnitud: "pales" }).real.nombre, "Tonnage 2026");
});

test("los días reales a 0 no entran en el ratio", () => {
  const { hayDatos, ratio, toneladas, horas } = ratioReal([0, 1000, 0, 0, 0, 0], [8, 8, 8, 8, 8, 8]);
  assert.equal(hayDatos, true);
  assert.equal(toneladas, 1);
  assert.equal(horas, 8);
  assert.equal(ratio, 0.13);
});

test("una semana sin real no tiene fila ni productividad real", () => {
  const detalle = { filas: [{ nombre: "Previsión", total: 6, dias: [1, 1, 1, 1, 1, 1] }] };
  const leido = filasDesdeDetalle(detalle, "Previsión");
  assert.deepEqual(leido.prevision.dias, ["1", "1", "1", "1", "1", "1"]);
  assert.deepEqual(leido.real.dias, ["", "", "", "", "", ""]);

  const guardado = detalleSeguimiento(["1", "1", "1", "1", "1", "1"], ["", "", "0", "", "", ""]);
  assert.deepEqual(guardado.detalle.filas, [{ nombre: "Previsión", total: 6, dias: [1, 1, 1, 1, 1, 1] }]);
  assert.equal(guardado.fila_base, "Previsión");
  const conReal = detalleSeguimiento(["1", "1", "1", "1", "1", "1"], ["", "2", "0", "", "", ""]);
  assert.deepEqual(conReal.detalle.filas[1], { nombre: "Real", total: 2, dias: [0, 2, 0, 0, 0, 0] });
  assert.equal(ratioReal([null, 0, null, 0, null, 0], [8, 8, 8, 8, 8, 8]).hayDatos, false);
});

test("la desviación total compara solo los días con real", () => {
  const previstos = [1000, 9000, 1000, 1000, 1000, 1000];
  const reales = [2000, 0, null, 500, 1000, 1000];
  const { dias, total } = desviacionSeguimiento(previstos, reales);
  assert.equal(dias[0].toneladas, 1);
  assert.equal(dias[0].porcentaje, 100);
  assert.equal(dias[1].toneladas, null);
  assert.equal(dias[2].toneladas, null);
  assert.equal(dias[3].toneladas, -0.5);
  assert.equal(dias[3].porcentaje, -50);
  assert.equal(total.toneladas, 0.5);
  assert.equal(total.porcentaje, 12.5);
});

test("el divisor 1000 pasa a toneladas y el 1 deja los palés", () => {
  const kilos = [0, 1000, 0, 0, 0, 0];
  const horas = [8, 8, 8, 8, 8, 8];
  const enToneladas = ratioReal(kilos, horas, 1000);
  assert.equal(enToneladas.toneladas, 1);
  assert.equal(enToneladas.horas, 8);
  assert.equal(enToneladas.ratio, 0.13);
  const enPales = ratioReal(kilos, horas, 1);
  assert.equal(enPales.toneladas, 1000);
  assert.equal(enPales.ratio, 125);

  const previstos = [1000, 9000, 0, 0, 0, 0];
  const reales = [1500, 0, 0, 0, 0, 0];
  assert.equal(desviacionSeguimiento(previstos, reales, 1000).total.toneladas, 0.5);
  assert.equal(desviacionSeguimiento(previstos, reales, 1000).dias[1].toneladas, null);
  assert.equal(desviacionSeguimiento(previstos, reales, 1).total.toneladas, 500);
  assert.equal(desviacionSeguimiento(previstos, reales, 1).dias[1].toneladas, null);
});

test("el pegado de palés usa la fila con foco si no puede distinguir el nombre", () => {
  const suelta = ["12", 2, 2, 2, 2, 2, 2].join("\t");
  const tonnage = ["Tonnage 2026", 90, 15, 15, 15, 15, 15, 15].join("\t");
  const texto = [suelta, tonnage].join("\n");
  const enFoco = pegarSeguimiento(texto, "prevision", 2026, { magnitud: "pales" });
  assert.equal(enFoco.real, undefined);
  assert.deepEqual(enFoco.prevision.dias, [2, 2, 2, 2, 2, 2]);
  assert.equal(
    pegarSeguimiento(texto, "prevision", 2026).prevision.error,
    "Hay varias líneas y ninguna empieza por Prévision.",
  );

  const prevision = ["Prévision 2026", 70, 10, 10, 10, 10, 10, 20].join("\t");
  const ambas = pegarSeguimiento([prevision, "Otra\t7\t1\t1\t1\t1\t1\t2", tonnage].join("\n"), null, 2026, {
    magnitud: "pales",
  });
  assert.deepEqual(ambas.prevision.dias, [10, 10, 10, 10, 10, 20]);
  assert.deepEqual(ambas.real.dias, [15, 15, 15, 15, 15, 15]);
});

test("guardar una magnitud no mezcla los datos de la otra", () => {
  const lectura = lecturaSeguimiento({
    detalle: { filas: [{ nombre: "Previsión", total: 6000, dias: [1000, 1000, 1000, 1000, 1000, 1000] }] },
    fila_base: "Previsión",
    detalle_pales: { filas: [{ nombre: "Previsión", total: 12, dias: [2, 2, 2, 2, 2, 2] }] },
    fila_base_pales: "Previsión",
  });
  const pales = cuerpoGuardado("pales", lectura.pales.prevision.dias, lectura.pales.real.dias);
  const toneladas = cuerpoGuardado("toneladas", lectura.toneladas.prevision.dias, lectura.toneladas.real.dias);
  assert.equal(pales.magnitud, "pales");
  assert.equal(pales.pales, 12);
  assert.equal(pales.toneladas, undefined);
  assert.deepEqual(pales.detalle.filas[0].dias, [2, 2, 2, 2, 2, 2]);
  assert.equal(toneladas.magnitud, "toneladas");
  assert.equal(toneladas.toneladas, 6);
  assert.equal(toneladas.pales, undefined);
  assert.deepEqual(toneladas.detalle.filas[0].dias, [1000, 1000, 1000, 1000, 1000, 1000]);
});

test("sin toneladas el ratio no se calcula", () => {
  for (const vacio of ["", null, undefined]) {
    const { ratio, motivo } = ratioSeguimiento(vacio, 374);
    assert.equal(ratio, null);
    assert.equal(motivo, "No hay toneladas previstas.");
  }
});
