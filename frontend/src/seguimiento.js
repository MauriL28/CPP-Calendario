function sinAcento(texto) {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function separar(linea) {
  const trozos = (linea.includes("\t") ? linea.split("\t") : linea.split(/ {2,}/)).map((campo) =>
    campo.trim(),
  );
  while (trozos.length > 0 && trozos[trozos.length - 1] === "") {
    trozos.pop();
  }
  return trozos;
}

function esPrevision(linea) {
  return sinAcento(linea).startsWith("prevision");
}

function leerKg(token) {
  let texto = token.trim().replace(/\u00a0/g, " ");
  if (/^\d{1,3}(?: \d{3})+(?:[.,]\d+)?$/.test(texto)) {
    texto = texto.replace(/ /g, "");
  }
  if (/^\d{1,3}(?:\.\d{3})+(?:,\d+)?$/.test(texto)) {
    texto = texto.replace(/\./g, "").replace(",", ".");
  } else if (/^\d{1,3}(?:,\d{3})+(?:\.\d+)?$/.test(texto)) {
    texto = texto.replace(/,/g, "");
  } else {
    texto = texto.replace(",", ".");
  }
  if (!/^\d+(?:\.\d+)?$/.test(texto)) {
    return null;
  }
  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

export function parsearPrevision(texto) {
  const lineas = String(texto ?? "")
    .split(/\r?\n/)
    .map((linea) => linea.trim())
    .filter(Boolean);
  if (lineas.length === 0) {
    return { error: "Pega la fila de previsión." };
  }
  let linea = lineas[0];
  if (lineas.length > 1) {
    const marcada = lineas.find((item) => esPrevision(item));
    if (!marcada) {
      return { error: "Hay varias líneas y ninguna empieza por Prévision." };
    }
    linea = marcada;
  }
  const campos = separar(linea).filter((campo) => campo !== "");
  if (campos.length === 0) {
    return { error: "Pega la fila de previsión." };
  }
  let nombre = "Previsión";
  let tokens = campos;
  if (leerKg(campos[0]) === null) {
    nombre = campos[0];
    tokens = campos.slice(1);
  }
  const valores = [];
  for (const token of tokens) {
    const numero = leerKg(token);
    if (numero === null) {
      return { error: `No se entiende el valor «${token}».` };
    }
    valores.push(numero);
  }
  if (valores.length === 6) {
    return {
      nombre,
      total: valores.reduce((acumulado, dia) => acumulado + dia, 0),
      dias: valores,
      aviso: "",
    };
  }
  if (valores.length === 7) {
    const [total, ...dias] = valores;
    const suma = dias.reduce((acumulado, dia) => acumulado + dia, 0);
    return {
      nombre,
      total,
      dias,
      aviso: Math.abs(suma - total) > 0.001 ? "El total no coincide con la suma de los días." : "",
    };
  }
  return { error: "Hacen falta 6 valores (lunes a sábado) o 7 con el total." };
}

const CELDAS_VACIAS = ["", "", "", "", "", ""];

export function celdasDesdeDetalle(detalle, filaBase) {
  const filas = detalle?.filas;
  if (!Array.isArray(filas) || filas.length === 0) {
    return { nombre: "", dias: [...CELDAS_VACIAS], total: null };
  }
  const elegida = filas.find((fila) => fila?.nombre === filaBase) || filas[0];
  const dias = Array.isArray(elegida?.dias) ? elegida.dias.slice(0, 6) : [];
  const total = Number(elegida?.total);
  if (
    dias.length !== 6
    || dias.some((dia) => !Number.isFinite(Number(dia)))
    || !Number.isFinite(total)
  ) {
    return { nombre: "", dias: [...CELDAS_VACIAS], total: null };
  }
  return {
    nombre: String(elegida?.nombre ?? "").trim(),
    dias: dias.map((dia) => String(Number(dia))),
    total,
  };
}

export function detalleDesdeCeldas(celdas, nombre) {
  const lista = Array.isArray(celdas) ? celdas : [];
  if (lista.length !== 6) {
    return { error: "La previsión tiene que tener 6 días, de lunes a sábado." };
  }
  const dias = [];
  for (const celda of lista) {
    const texto = String(celda ?? "").trim().replace(",", ".");
    if (!texto) {
      return { error: "La previsión tiene que tener 6 días, de lunes a sábado." };
    }
    const numero = Number(texto);
    if (!Number.isFinite(numero) || numero < 0 || !Number.isInteger(numero)) {
      return { error: "Los kilos tienen que ser números enteros mayores o iguales que cero." };
    }
    dias.push(numero);
  }
  const total = dias.reduce((acumulado, dia) => acumulado + dia, 0);
  const nombreFinal = String(nombre ?? "").trim() || "Previsión";
  return {
    nombre: nombreFinal,
    total,
    dias,
    detalle: { filas: [{ nombre: nombreFinal, total, dias }] },
    fila_base: nombreFinal,
  };
}

export function textoDesdeDetalle(detalle, filaBase) {
  const filas = detalle?.filas;
  if (!Array.isArray(filas) || filas.length === 0) {
    return "";
  }
  const elegida = filas.find((fila) => fila?.nombre === filaBase) || filas[0];
  const dias = Array.isArray(elegida?.dias) ? elegida.dias.slice(0, 6) : [];
  const total = Number(elegida?.total);
  const nombre = String(elegida?.nombre ?? "").trim();
  if (!nombre || dias.length !== 6 || !Number.isFinite(total) || dias.some((dia) => !Number.isFinite(Number(dia)))) {
    return "";
  }
  return [nombre, total, ...dias.map(Number)].join("\t");
}

export function ratioSeguimiento(toneladas, horas) {
  const texto = String(toneladas ?? "").trim().replace(",", ".");
  if (!texto) {
    return { ratio: null, motivo: "No hay toneladas previstas." };
  }
  const numero = Number(texto);
  if (!Number.isFinite(numero) || numero < 0) {
    return { ratio: null, motivo: "Las toneladas no son válidas." };
  }
  if (!(Number(horas) > 0)) {
    return { ratio: null, motivo: "No hay horas planificadas esta semana." };
  }
  return { ratio: Number((numero / Number(horas)).toFixed(2)), motivo: "" };
}
