import { ref } from "vue";

export const LETRAS_HORARIO = ["L", "M", "X", "J", "V", "S", "D"];

export function useHorarioHabitual() {
  const diasMarcados = ref([true, true, true, true, true, false, false]);
  const horasDia = ref(LETRAS_HORARIO.map(() => ({ inicio: "", fin: "" })));
  const plantillaDia = ref(null);
  const propios = ref(LETRAS_HORARIO.map(() => false));

  function reiniciar() {
    diasMarcados.value = [true, true, true, true, true, false, false];
    horasDia.value = LETRAS_HORARIO.map(() => ({ inicio: "", fin: "" }));
    plantillaDia.value = null;
    propios.value = LETRAS_HORARIO.map(() => false);
  }

  function alMarcar(dia, evento) {
    const marcado = evento.target.checked;
    diasMarcados.value[dia] = marcado;
    if (!marcado || plantillaDia.value === null || propios.value[dia]) {
      return;
    }
    const origen = horasDia.value[plantillaDia.value];
    horasDia.value[dia] = { inicio: origen.inicio, fin: origen.fin };
  }

  function alHora(dia, campo, valor) {
    const actual = horasDia.value[dia];
    horasDia.value[dia] = { ...actual, [campo]: valor };
    if (plantillaDia.value === null) {
      plantillaDia.value = dia;
    } else if (dia !== plantillaDia.value) {
      propios.value[dia] = true;
      return;
    }
    const origen = horasDia.value[dia];
    horasDia.value = horasDia.value.map((item, indice) => {
      if (indice === dia) {
        return origen;
      }
      if (!diasMarcados.value[indice] || propios.value[indice]) {
        return item;
      }
      return { inicio: origen.inicio, fin: origen.fin };
    });
  }

  function horarioDias() {
    const horario = [];
    for (let dia = 0; dia < LETRAS_HORARIO.length; dia += 1) {
      if (!diasMarcados.value[dia]) {
        continue;
      }
      const horas = horasDia.value[dia];
      if (!horas.inicio || !horas.fin) {
        return { error: "Indica la hora de inicio y de fin de cada día marcado." };
      }
      horario.push({
        dia_semana: dia,
        hora_inicio: horas.inicio,
        hora_fin: horas.fin,
      });
    }
    if (!horario.length) {
      return { error: "Marca al menos un día." };
    }
    return { horario_dias: horario };
  }

  return {
    letras: LETRAS_HORARIO,
    diasMarcados,
    horasDia,
    reiniciar,
    alMarcar,
    alHora,
    horarioDias,
  };
}
