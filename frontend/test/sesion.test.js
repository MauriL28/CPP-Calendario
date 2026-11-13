import assert from "node:assert/strict";
import test from "node:test";

import { esFalloDeSesion } from "../src/api/cliente.js";
import {
  alPerderSesion,
  avisarSesionInvalida,
  borrarToken,
  cerrarSesion,
  guardarToken,
  leerToken,
  rearmarAvisoSesion,
  sesionDesdeToken,
} from "../src/sesion.js";

function memoria() {
  const datos = new Map();
  return {
    getItem(clave) {
      return datos.has(clave) ? datos.get(clave) : null;
    },
    setItem(clave, valor) {
      datos.set(clave, valor);
    },
    removeItem(clave) {
      datos.delete(clave);
    },
    claves() {
      return [...datos.keys()];
    },
  };
}

function token(carga) {
  const json = Buffer.from(JSON.stringify(carga)).toString("base64url");
  return `cabecera.${json}.firma`;
}

function trabajador() {
  return {
    rol: "trabajador",
    login: "nerea.lago",
    nombre: "Nerea Lago",
    departamento: "Tráfico",
    delegaciones: ["60I"],
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
}

test("al recargar se recupera la sesión del trabajador desde el token", () => {
  const storage = memoria();
  const acceso = token(trabajador());
  guardarToken(acceso, storage);

  const sesion = sesionDesdeToken(leerToken(storage));

  assert.equal(sesion.login, "nerea.lago");
  assert.equal(sesion.rol, "trabajador");
  assert.equal(sesion.nombre, "Nerea Lago");
  assert.equal(sesion.departamento, "Tráfico");
  assert.deepEqual(sesion.delegaciones, ["60I"]);
  assert.equal(sesion.token, acceso);
  assert.deepEqual(storage.claves(), ["stef365.token"]);
});

test("un token caducado no restaura la sesión", () => {
  const acceso = token({ ...trabajador(), exp: Math.floor(Date.now() / 1000) - 10 });
  assert.equal(sesionDesdeToken(acceso), null);
});

test("si el logout remoto falla, el token local se borra", async () => {
  const storage = memoria();
  guardarToken(token(trabajador()), storage);
  await cerrarSesion("token-vivo", async () => {
    throw new Error("red");
  }, storage);
  assert.equal(leerToken(storage), null);
});

test("varias respuestas de sesión inválida solo cierran una vez", () => {
  let cierres = 0;
  alPerderSesion(() => {
    cierres += 1;
  });
  rearmarAvisoSesion();
  avisarSesionInvalida();
  avisarSesionInvalida();
  assert.equal(cierres, 1);
  borrarToken(memoria());
});

test("solo un 401 de token caducado o revocado cierra la sesión", () => {
  assert.equal(esFalloDeSesion(401, { msg: "Token has expired" }, true), true);
  assert.equal(esFalloDeSesion(401, { msg: "Token has been revoked" }, true), true);
  assert.equal(esFalloDeSesion(401, { error: "Credenciales incorrectas" }, false), false);
  assert.equal(esFalloDeSesion(401, { error: "Delegación no presente" }, true), false);
});
