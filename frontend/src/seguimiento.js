function sinAcento(texto) {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function separar(linea, conTabulador) {
  const limpia = String(linea ?? "").replace(/\u00a0/g, " ");
  const trozos = (conTabulador ? limpia.split("\t") : limpia.split(/[; ]+/)).map((campo) => campo.trim());
  return trozos.filter((campo) => campo !== "");
}

function esAnio(token) {
  if (!/^\d{4}$/.test(token)) {
    return false;
  }
  const anio = Number(token);
  return anio >= 1900 && anio <= 2099;
}

function partirLinea(linea, conTabulador = String(linea ?? "").includes("\t")) {
  const campos = separar(linea, conTabulador);
  const nombrePartes = [];
  let indice = 0;
  while (indice < campos.length && leerKg(campos[indice]) === null) {
    nombrePartes.push(campos[indice]);
    indice += 1;
  }
  const numeros = campos.length - indice;
  if (!conTabulador && nombrePartes.length > 0 && numeros > 6 && esAnio(campos[indice])) {
    nombrePartes.push(campos[indice]);
    indice += 1;
  }
  return {
    nombre: nombrePartes.join(" "),
    teniaNombre: nombrePartes.length > 0,
    tokens: campos.slice(indice),
  };
}

function esPrevision(linea) {
  return sinAcento(linea).startsWith("prevision");
}

function esTonnage(linea) {
  return sinAcento(linea).startsWith("tonnage");
}

function lineasDe(texto) {
  return String(texto ?? "")
    .split(/\r?\n/)
    .map((linea) => linea.trim())
    .filter(Boolean);
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

const SIN_NUMEROS = "Pega de 1 a 7 números separados por tabulador o espacio";

function parsearLinea(linea, conTabulador = String(linea ?? "").includes("\t")) {
  const partido = partirLinea(linea, conTabulador);
  if (partido.tokens.length === 0 && !partido.teniaNombre) {
    return { error: "Pega la fila de previsión." };
  }
  const nombre = partido.teniaNombre ? partido.nombre : "Previsión";
  const teniaNombre = partido.teniaNombre;
  const valores = [];
  for (const token of partido.tokens) {
    const numero = leerKg(token);
    if (numero === null) {
      return { error: `No se entiende el valor «${token}».` };
    }
    valores.push(numero);
  }
  if (valores.length === 0) {
    return { error: SIN_NUMEROS };
  }
  if (valores.length > 7) {
    return { error: `Hay ${valores.length} valores y solo caben seis días (lunes a sábado).` };
  }
  if (valores.length === 7) {
    const [total, ...dias] = valores;
    const suma = dias.reduce((acumulado, dia) => acumulado + dia, 0);
    const cuadra = Math.abs(suma - total) <= 0.001;
    if (!teniaNombre && !cuadra) {
      return { error: "Hay 7 valores y solo seis días (lunes a sábado)" };
    }
    return {
      nombre,
      total,
      dias,
      aviso: cuadra ? "" : "El total no coincide con la suma de los días.",
    };
  }
  return { nombre, dias: valores, aviso: "" };
}

export function aplicarDias(celdas, dias, inicio) {
  const base = Array.from({ length: 6 }, (_, indice) => {
    const valor = Array.isArray(celdas) ? celdas[indice] : "";
    return valor == null ? "" : String(valor);
  });
  const lista = Array.isArray(dias) ? dias : [];
  const desde = lista.length === 6
    ? 0
    : Number.isInteger(inicio) && inicio >= 0 && inicio < 6
      ? inicio
      : 0;
  const escritos = lista.slice(0, 6 - desde);
  const sobran = lista.length - escritos.length;
  const siguientes = [...base];
  const indices = escritos.map((dia, desplazamiento) => {
    const indice = desde + desplazamiento;
    siguientes[indice] = String(dia);
    return indice;
  });
  return {
    celdas: siguientes,
    desde,
    escritos: escritos.length,
    indices,
    sobran,
    aviso: sobran > 0 ? `Sobran ${sobran} valores` : "",
  };
}

function nombreDeLinea(linea) {
  return partirLinea(linea).nombre;
}

function serieDeColumna(texto) {
  if (String(texto ?? "").includes("\t")) {
    return null;
  }
  const lineas = lineasDe(texto);
  if (lineas.length < 2) {
    return null;
  }
  const numeros = [];
  for (const linea of lineas) {
    const campos = separar(linea, false);
    if (campos.length !== 1) {
      return null;
    }
    const numero = leerKg(campos[0]);
    if (numero === null) {
      return null;
    }
    numeros.push(String(numero));
  }
  return parsearLinea(numeros.join(" "), false);
}

export function parsearPrevision(texto, flexible = false) {
  const serie = serieDeColumna(texto);
  if (serie) {
    return serie;
  }
  const lineas = lineasDe(texto);
  if (lineas.length === 0) {
    return { error: "Pega la fila de previsión." };
  }
  const conTabulador = String(texto ?? "").includes("\t");
  let linea = lineas[0];
  if (lineas.length > 1) {
    const marcada = lineas.find((item) => esPrevision(item));
    if (!marcada) {
      return flexible ? parsearLinea(lineas[0], conTabulador) : { error: "Hay varias líneas y ninguna empieza por Prévision." };
    }
    linea = marcada;
  }
  return parsearLinea(linea, conTabulador);
}

export function parsearReal(texto, anio, flexible = false) {
  const serie = serieDeColumna(texto);
  if (serie) {
    return serie;
  }
  const lineas = lineasDe(texto);
  if (lineas.length === 0) {
    return { error: "Pega la fila de real." };
  }
  const conTabulador = String(texto ?? "").includes("\t");
  let linea = lineas[0];
  if (lineas.length > 1) {
    const tonnages = lineas.filter((item) => esTonnage(item));
    if (tonnages.length === 0) {
      return flexible ? parsearLinea(lineas[0], conTabulador) : { error: "Hay varias líneas y ninguna empieza por Tonnage." };
    }
    const conAnio = anio
      ? tonnages.filter((item) => sinAcento(nombreDeLinea(item)).includes(String(anio)))
      : [];
    linea = (conAnio.length > 0 ? conAnio : tonnages).at(-1);
  }
  return parsearLinea(linea, conTabulador);
}

export function numeroSuelto(texto) {
  const crudo = String(texto ?? "").replace(/\u00a0/g, " ");
  if (/[\t\r\n]/.test(crudo)) {
    return null;
  }
  const limpio = crudo.trim();
  if (/[ ;]/.test(limpio)) {
    return null;
  }
  const numero = leerKg(limpio);
  return numero === null ? null : numero;
}

function destinoPorNombre(linea) {
  if (esTonnage(linea)) {
    return "real";
  }
  if (esPrevision(linea)) {
    return "prevision";
  }
  return "";
}

function resultadoDeLinea(linea, fila, conTabulador) {
  const parseo = parsearLinea(linea, conTabulador);
  return fila === "real" ? { real: parseo } : { prevision: parseo };
}

export function pegarSeguimiento(texto, destino, anio, opciones = {}) {
  const flexible = opciones.magnitud === "pales";
  const lineas = lineasDe(texto);
  if (lineas.length > 1 && lineas.some(esPrevision) && lineas.some(esTonnage)) {
    return { prevision: parsearPrevision(texto), real: parsearReal(texto, anio) };
  }
  const suelto = numeroSuelto(texto);
  if (suelto !== null) {
    return { celda: suelto };
  }
  if (lineas.length === 0) {
    return { error: "Pega la fila de previsión." };
  }
  if (lineas.length === 1) {
    const fila = destinoPorNombre(lineas[0]) || destino || "prevision";
    return resultadoDeLinea(lineas[0], fila, String(texto ?? "").includes("\t"));
  }
  const fila = destino || "prevision";
  if (fila === "real") {
    return { real: parsearReal(texto, anio, flexible) };
  }
  return { prevision: parsearPrevision(texto, flexible) };
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

function leerFilaGuardada(fila) {
  const dias = Array.isArray(fila?.dias) ? fila.dias.slice(0, 6) : [];
  const total = Number(fila?.total);
  if (
    dias.length !== 6
    || dias.some((dia) => !Number.isFinite(Number(dia)))
    || !Number.isFinite(total)
  ) {
    return { nombre: "", dias: [...CELDAS_VACIAS], total: null };
  }
  return {
    nombre: String(fila?.nombre ?? "").trim(),
    dias: dias.map((dia) => String(Number(dia))),
    total,
  };
}

export function filasDesdeDetalle(detalle, filaBase) {
  const filas = Array.isArray(detalle?.filas) ? detalle.filas : [];
  const prevision =
    filas.find((fila) => fila?.nombre === "Previsión")
    || filas.find((fila) => filaBase && fila?.nombre === filaBase)
    || filas.find((fila) => fila?.nombre !== "Real");
  const real = filas.find((fila) => fila?.nombre === "Real");
  return {
    prevision: leerFilaGuardada(prevision),
    real: leerFilaGuardada(real),
  };
}

function kilosReales(celdas) {
  const lista = Array.isArray(celdas) ? celdas : [];
  if (lista.length !== 6) {
    return { error: "El real tiene que tener 6 días, de lunes a sábado." };
  }
  const dias = [];
  for (const celda of lista) {
    const texto = String(celda ?? "").trim().replace(",", ".");
    if (!texto) {
      dias.push(0);
      continue;
    }
    const numero = Number(texto);
    if (!Number.isFinite(numero) || numero < 0 || !Number.isInteger(numero)) {
      return { error: "Los kilos tienen que ser números enteros mayores o iguales que cero." };
    }
    dias.push(numero);
  }
  return { dias, total: dias.reduce((acumulado, dia) => acumulado + dia, 0) };
}

export function detalleSeguimiento(prevision, real) {
  const base = detalleDesdeCeldas(prevision, "Previsión");
  if (base.error) {
    return base;
  }
  const reales = kilosReales(real);
  if (reales.error) {
    return reales;
  }
  const filas = [{ nombre: "Previsión", total: base.total, dias: base.dias }];
  if (reales.dias.some((dia) => dia > 0)) {
    filas.push({ nombre: "Real", total: reales.total, dias: reales.dias });
  }
  return {
    total: base.total,
    detalle: { filas },
    fila_base: "Previsión",
  };
}

function indicesConDatos(kilos) {
  return kilos.flatMap((kg, indice) => (Number(kg) > 0 ? [indice] : []));
}

export function ratioReal(kilos, horas, divisor = 1000) {
  const indices = indicesConDatos(kilos);
  if (indices.length === 0) {
    return { hayDatos: false, ratio: null, toneladas: 0, horas: 0, motivo: "" };
  }
  const kg = indices.reduce((suma, indice) => suma + Number(kilos[indice]), 0);
  const horasDatos = indices.reduce((suma, indice) => suma + (Number(horas?.[indice]) || 0), 0);
  const cantidad = kg / divisor;
  const calculo = ratioSeguimiento(cantidad, horasDatos);
  return {
    hayDatos: true,
    ratio: calculo.ratio,
    toneladas: cantidad,
    horas: horasDatos,
    motivo: calculo.motivo,
  };
}

export function desviacionSeguimiento(previstos, reales, divisor = 1000) {
  const dias = reales.map((real, indice) => {
    if (!(Number(real) > 0)) {
      return { toneladas: null, porcentaje: null };
    }
    const previsto = Number(previstos?.[indice]) || 0;
    return {
      toneladas: (Number(real) - previsto) / divisor,
      porcentaje: previsto > 0 ? ((Number(real) - previsto) / previsto) * 100 : null,
    };
  });
  const indices = indicesConDatos(reales);
  if (indices.length === 0) {
    return { dias, total: { toneladas: null, porcentaje: null } };
  }
  const real = indices.reduce((suma, indice) => suma + Number(reales[indice]), 0);
  const previsto = indices.reduce((suma, indice) => suma + (Number(previstos?.[indice]) || 0), 0);
  return {
    dias,
    total: {
      toneladas: (real - previsto) / divisor,
      porcentaje: previsto > 0 ? ((real - previsto) / previsto) * 100 : null,
    },
  };
}

export function lecturaSeguimiento(seguimiento) {
  return {
    toneladas: filasDesdeDetalle(seguimiento?.detalle, seguimiento?.fila_base),
    pales: filasDesdeDetalle(seguimiento?.detalle_pales, seguimiento?.fila_base_pales),
  };
}

export function cuerpoGuardado(magnitud, prevision, real) {
  const construido = detalleSeguimiento(prevision, real);
  if (construido.error) {
    return construido;
  }
  const cuerpo = {
    magnitud,
    detalle: construido.detalle,
    fila_base: construido.fila_base,
  };
  if (magnitud === "pales") {
    cuerpo.pales = Number(construido.total.toFixed(2));
  } else {
    cuerpo.toneladas = Number((construido.total / 1000).toFixed(2));
  }
  return cuerpo;
}
