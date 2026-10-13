"""
Gráfico de íconos "La pobreza en adultos en el Perú" (2025): si los adultos pobres
fueran 50, cuántos viven en zona rural, tienen lengua materna nativa, no terminaron
la secundaria y tienen otras características (y sus combinaciones). Se genera una
versión por cada entrada de VARIANTES.

Cifras: adultos de 25+ años en hogares pobres, ponderados con FACTOR07 (= FACPOB07),
calculadas con pobreza_adultos_2025.py.
Uso:    python iconos_adultos_pobres.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

import pobreza_adultos_2025 as base

SALIDA = Path(__file__).resolve().parent / "resultados"
PESO = "factor07"

TEAL, AMARILLO, AZUL, ROJO, GRIS = "#14A7A7", "#F2B705", "#3F51A3", "#E2294F", "#D3D3CF"
CARBON, TINTA = "#3A3A3A", "#14234B"

# característica: (etiqueta, color)
CARACTERISTICAS = {
    "rural": ("Vive en zona rural", TEAL),
    "lima": ("Vive en Lima Metropolitana", AMARILLO),
    "nativa": ("Lengua materna quechua, aimara\nu otra nativa", AZUL),
    "sin_secundaria": ("No terminó la secundaria", ROJO),
    "sin_programa": ("Su hogar no recibe ningún\nprograma social", AMARILLO),
    "pobreza_extrema": ("Está en pobreza extrema", CARBON),
}
NOTA_PROGRAMAS = ("Programas: Pensión 65, Juntos, Vaso de Leche y Qali Warma / Wasi Mikuna. "
                  "Para los hogares sin respuesta a ese módulo (14 %) se usa la tasa de hogares con el "
                  "mismo perfil.\n")

# versión: características que se agregan a rural, nativa y sin secundaria
VARIANTES = {
    "lima": ["lima"],
    "sin_programa_pobreza_extrema": ["sin_programa", "pobreza_extrema"],
}
BASE = ["rural", "nativa", "sin_secundaria"]


def icono(ax, x, y, cols, s=1.0):
    """Persona de ancho s, con una franja vertical por color."""
    n = len(cols)
    for i, c in enumerate(cols):
        clip = Rectangle((x + i * s / n, y - 0.1), s / n, 2 * s, transform=ax.transData)
        for forma in (Circle((x + s / 2, y + 1.18 * s), 0.34 * s),
                      FancyBboxPatch((x, y), s, 0.78 * s,
                                     boxstyle=f"round,pad=0,rounding_size={0.32 * s}"),
                      Rectangle((x, y), s, 0.4 * s)):
            forma.set(color=c, lw=0)
            ax.add_patch(forma)
            forma.set_clip_path(clip)


def sin_programa():
    """Hogares que no reciben ninguno de los cuatro programas (NaN si no respondió el 700)."""
    m = pd.read_csv(base.DATOS / "Enaho01-2025-700.csv", sep=";", encoding="latin1", dtype=str)
    m.columns = [c.lower().replace("$", "_") for c in m.columns]
    vars700 = ["p701_01", "p701_03", "p701_04", "p710_04", "p710_05"]
    for c in vars700:
        m[c] = pd.to_numeric(m[c].str.strip(), errors="coerce")
    m["sin_programa"] = (~(m[vars700] == 1).any(axis=1)).astype(float)
    m.loc[m[vars700].isna().any(axis=1), "sin_programa"] = np.nan
    return m[base.LLAVE + ["sin_programa"]]


def ajustar(combos, pct, objetivo):
    """Mueve íconos entre combinaciones que difieren en una sola característica hasta que
    el total de cada característica coincida con su porcentaje redondeado (de 50)."""
    for _ in range(50):
        malos = [(i, objetivo[i] - sum(n for k, n in combos.items() if k[i])) for i in objetivo]
        malos = [(i, dif) for i, dif in malos if dif]
        if not malos:
            break
        i, dif = malos[0]
        candidatos = []
        for origen, n in combos.items():
            if n == 0 or origen[i] == (dif > 0):
                continue
            destino = tuple(not v if j == i else v for j, v in enumerate(origen))
            if destino in combos:
                # error de redondeo que se acepta al mover un ícono
                costo = (combos[destino] + 1 - pct[destino] / 2) + (pct[origen] / 2 - (n - 1))
                candidatos.append((costo, origen, destino))
        if not candidatos:
            break
        _, origen, destino = min(candidatos)
        combos[origen] -= 1
        combos[destino] += 1
    return combos


def imputar_sin_programa(x):
    """Mantiene en la base a quienes no respondieron el módulo 700: a cada uno se le asigna
    la tasa de 'no recibe programas' de los que sí respondieron y tienen su mismo perfil
    (rural, Lima, lengua nativa, secundaria y pobreza extrema). Cada no respondiente se
    divide en dos filas (recibe / no recibe) con su peso repartido según esa tasa."""
    celdas = ["rural", "lima", "nativa", "sin_secundaria", "pobreza_extrema"]
    resp = x[x.sin_programa.notna()]
    tasa = (resp.assign(wp=resp[PESO] * resp.sin_programa).groupby(celdas)
            .agg(wp=("wp", "sum"), w=(PESO, "sum")))
    tasa = (tasa.wp / tasa.w).rename("tasa")
    nr = x[x.sin_programa.isna()].join(tasa, on=celdas)
    nr["tasa"] = nr.tasa.fillna(np.average(resp.sin_programa, weights=resp[PESO]))
    si = nr.assign(sin_programa=1.0, **{PESO: nr[PESO] * nr.tasa})
    no = nr.assign(sin_programa=0.0, **{PESO: nr[PESO] * (1 - nr.tasa)})
    x = pd.concat([resp, si.drop(columns="tasa"), no.drop(columns="tasa")], ignore_index=True)
    x["sin_programa"] = x.sin_programa == 1
    return x


def calcular(extras):
    claves = BASE + extras
    d = base.cargar()
    x = d[(d.pobreza < 3) & (d.p208a >= 25)].copy()
    x["lima"] = x.dominio == 8
    x["pobreza_extrema"] = x.pobreza == 1
    if "sin_programa" in extras:
        x = imputar_sin_programa(x.merge(sin_programa(), on=base.LLAVE, how="left"))

    w = x.groupby(claves)[PESO].sum()
    w = w[w > 0]
    # rurales primero, luego por las características agregadas; grises al final
    prioridad = [0] + list(range(3, len(claves))) + [1, 2]
    orden = sorted(w.index, key=lambda k: tuple(not k[i] for i in prioridad))
    pct = 100 * w.reindex(orden) / w.sum()
    combos = ajustar(dict(zip(orden, base.de_50(pct.reset_index(drop=True)))), pct,
                     {i: round(np.average(x[c], weights=x[PESO]) * 50) for i, c in enumerate(claves)})
    totales = {c: (sum(n for k, n in combos.items() if k[i]),
                   100 * np.average(x[c], weights=x[PESO])) for i, c in enumerate(claves)}
    ninguna = (False,) * len(claves)
    totales["ninguna"] = (combos.get(ninguna, 0), pct.get(ninguna, 0))
    return claves, combos, totales


def main():
    SALIDA.mkdir(exist_ok=True)
    for variante in VARIANTES:
        dibujar(variante)


def dibujar(variante):
    claves, combos, tot = calcular(VARIANTES[variante])
    nota_extra = NOTA_PROGRAMAS if "sin_programa" in claves else ""

    fig = plt.figure(figsize=(14, 7.6), facecolor="white")
    ax = fig.add_axes([0.03, 0.1, 0.58, 0.82])
    ax.set_xlim(-0.2, 15.6)
    ax.set_ylim(-0.3, 10.4)
    ax.set_aspect("equal")
    ax.axis("off")

    k = 0
    for clave, n in combos.items():
        for _ in range(n):
            fila, col = divmod(k, 10)
            cols = [CARACTERISTICAS[c][1] for c, activo in zip(claves, clave) if activo]
            icono(ax, col * 1.6, 8.4 - fila * 2.1, cols or [GRIS])
            k += 1

    # Leyenda
    lg = fig.add_axes([0.64, 0.1, 0.34, 0.82])
    lg.set_xlim(0, 10)
    lg.set_ylim(0, 10)
    lg.axis("off")
    lg.add_patch(Rectangle((0, 8.35), 10, 1.5, color=TINTA, lw=0))
    lg.text(5, 9.1, "Si los adultos en condición de pobreza\nen el Perú fueran solo 50:",
            ha="center", va="center", fontsize=13, color="white", weight="bold")
    items = [(CARACTERISTICAS[c][1], CARACTERISTICAS[c][0], tot[c]) for c in claves]
    items.append((GRIS, "Ninguna de las anteriores", tot["ninguna"]))
    paso = 7.0 / len(items)
    y = 7.4
    for color, texto, (n, pct) in items:
        lg.add_patch(Rectangle((0.1, y - 0.28), 0.55, 0.55, color=color, lw=0))
        lg.text(0.95, y, texto, va="center", fontsize=11.5, color=TINTA)
        lg.text(9.9, y, f"{n} de 50", va="center", ha="right", fontsize=12.5, color=TINTA,
                weight="bold")
        lg.text(9.9, y - 0.5, f"({pct:.0f} %)", va="center", ha="right", fontsize=9.5,
                color="#777")
        y -= paso
    lg.text(0.1, y + 0.35,
            "Un ícono con varios colores reúne varias\ncaracterísticas.",
            va="top", fontsize=9.5, color="#555", style="italic")

    fig.text(0.03, 0.03, nota_extra + "Nota: adultos de 25 años o más en hogares en situación de pobreza "
             "monetaria. Ponderado con el factor de población (FACPOB07).\n"
             "Fuente: INEI, Encuesta Nacional de Hogares (ENAHO) 2025.",
             fontsize=9, color="#444")
    fig.savefig(SALIDA / f"iconos_adultos_pobres_2025_{variante}.png", dpi=170,
                facecolor="white")
    plt.close(fig)
    print(variante, {k: (n, round(p, 1)) for k, (n, p) in tot.items()})


if __name__ == "__main__":
    main()
