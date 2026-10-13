"""
Perfil de los adultos pobres - ENAHO 2025.

Verifica el gráfico "La pobreza en adultos en el Perú": entre las personas
pobres de 25 años o más, % que vive en zona rural, que tiene lengua materna
nativa, que no terminó la secundaria y que no cumple ninguna de las tres; más la
distribución de las 8 combinaciones, llevada a "si fueran 50 personas".

Definiciones:
  Pobre               POBREZA = 1 o 2 (Sumaria, a nivel de hogar)
  Residente habitual  (P204 = 1 y P205 = 2) o (P204 = 2 y P206 = 1)
  Rural               ESTRATO 6-8
  Lengua nativa       P300A = 1 quechua, 2 aimara, 3 otra nativa, 10-15 lenguas amazónicas
  No terminó secund.  P301A = 1-5 (sin nivel a secundaria incompleta) o 12 (básica especial)

Ponderación por persona:
  FACTOR07   igual a FACPOB07 (factor de población del módulo 200) en 2025; es el
             que usa el INEI para la pobreza (25.7 %) y reproduce el gráfico original
  FACTORA07  factor del módulo 300 ajustado por grupos de edad (sensibilidad)

Datos: enaho-2025/ (Sumaria, módulo 300 reducido).
Uso:   python pobreza_adultos_2025.py
Salidas en ./resultados/
"""

from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "enaho-2025"
SALIDA = RAIZ / "resultados"
LLAVE = ["conglome", "vivienda", "hogar"]

NATIVAS = [1, 2, 3, 10, 11, 12, 13, 14, 15]
SIN_SECUNDARIA = [1, 2, 3, 4, 5, 12]
CONDICIONES = {
    "rural": "Vive en zona rural",
    "nativa": "Lengua materna quechua, aimara u otra nativa",
    "sin_secundaria": "No terminó la secundaria",
}
ORIGINAL = {"rural": 27, "nativa": 27, "sin_secundaria": 55, "ninguna": 34}


def cargar():
    sumaria = pd.read_csv(DATOS / "Sumaria-2025.csv", sep=";", encoding="latin1", decimal=",",
                          dtype={c.upper(): str for c in LLAVE},
                          usecols=[c.upper() for c in LLAVE] + ["POBREZA"])
    sumaria.columns = sumaria.columns.str.lower()

    personas = pd.read_stata(DATOS / "enaho01a-2025-300.dta", convert_categoricals=False)
    residente = (((personas.p204 == 1) & (personas.p205 == 2))
                 | ((personas.p204 == 2) & (personas.p206 == 1)))
    df = personas[residente].merge(sumaria, on=LLAVE, how="left", validate="m:1")

    df["rural"] = df.estrato >= 6
    df["nativa"] = df.p300a.isin(NATIVAS)
    df["sin_secundaria"] = df.p301a.isin(SIN_SECUNDARIA)
    df["ninguna"] = ~(df.rural | df.nativa | df.sin_secundaria)
    return df


def perfil(df, edad_min, peso):
    x = df[(df.pobreza < 3) & (df.p208a >= edad_min)]
    w = x[peso]
    pct = {c: 100 * np.average(x[c], weights=w) for c in list(CONDICIONES) + ["ninguna"]}

    combos = []
    for r, n, s in product([True, False], repeat=3):
        m = (x.rural == r) & (x.nativa == n) & (x.sin_secundaria == s)
        combos.append({"rural": r, "nativa": n, "sin_secundaria": s,
                       "porcentaje": 100 * w[m].sum() / w.sum(), "n_muestral": int(m.sum())})
    combos = pd.DataFrame(combos)
    combos["de_50"] = de_50(combos.porcentaje)
    return pct, combos, len(x)


def de_50(porcentajes, total=50):
    """Reparte `total` íconos por mayor resto, para que sumen exactamente 50."""
    bruto = porcentajes / 100 * total
    base = np.floor(bruto).astype(int)
    faltan = total - base.sum()
    base[np.argsort(-(bruto - base).to_numpy())[:faltan]] += 1
    return base


def main():
    SALIDA.mkdir(exist_ok=True)
    df = cargar()

    filas = []
    for edad in [25, 18]:
        for peso in ["factora07", "factor07"]:
            pct, combos, n = perfil(df, edad, peso)
            for c, v in pct.items():
                cuenta = (combos.loc[combos[c], "de_50"].sum() if c in CONDICIONES
                          else combos.loc[~combos[list(CONDICIONES)].any(axis=1), "de_50"].sum())
                filas.append({"edad": f"{edad}+", "ponderacion": peso,
                              "indicador": CONDICIONES.get(c, "Ninguna de las tres"),
                              "porcentaje": round(v, 1), "de_50": int(cuenta),
                              "grafico_original_pct": ORIGINAL[c], "n_muestral": n})
            if edad == 25:
                combos.round(2).to_csv(SALIDA / f"adultos_pobres_combinaciones_{peso}.csv",
                                       index=False, encoding="utf-8-sig")
    tab = pd.DataFrame(filas)
    tab.to_csv(SALIDA / "adultos_pobres_2025.csv", index=False, encoding="utf-8-sig")
    with pd.option_context("display.width", 200):
        print(tab.to_string(index=False))


if __name__ == "__main__":
    main()
