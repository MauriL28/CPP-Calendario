export const GRUPOS = [
  { id: "STEF", titulo: "Personal STEF" },
  { id: "ETT", titulo: "ETT" },
];

export function iniciales(nombre) {
  const palabras = nombre.split(/\s+/).filter((parte) => /\p{L}/u.test(parte));
  return palabras
    .slice(0, 2)
    .map((parte) => parte[0].toLocaleUpperCase("es"))
    .join("");
}

export function numeroFormulario(valor) {
  if (valor === "" || valor === null) {
    return null;
  }
  const cantidad = Number(valor);
  return Number.isNaN(cantidad) ? null : cantidad;
}

export function agruparPersonas(lista) {
  const personas = lista ?? [];
  return GRUPOS
    .map((grupo) => ({
      id: grupo.id,
      titulo: grupo.titulo,
      personas: personas.filter((trabajador) => trabajador.grupo === grupo.id),
    }))
    .filter((grupo) => grupo.personas.length);
}
