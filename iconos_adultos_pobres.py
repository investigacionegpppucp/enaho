"""
Gráfico de íconos "La pobreza en adultos en el Perú" (2025): si los adultos pobres
fueran 50, cuántos viven en zona rural o en Lima Metropolitana, tienen lengua
materna nativa y no terminaron la secundaria (y sus combinaciones).

Cifras: adultos de 25+ años en hogares pobres, ponderados con FACTOR07 (= FACPOB07),
calculadas con pobreza_adultos_2025.py.
Uso:    python iconos_adultos_pobres.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

import pobreza_adultos_2025 as base

SALIDA = Path(__file__).resolve().parent / "resultados"
PESO = "factor07"

TEAL, AMARILLO, AZUL, ROJO, GRIS = "#14A7A7", "#F2B705", "#3F51A3", "#E2294F", "#D3D3CF"
TINTA = "#14234B"

# Orden de los íconos: rurales, Lima, otras ciudades y al final los grises.
# Cada clave: (rural, lima, nativa, sin_secundaria)
ORDEN = [
    (True, False, True, True), (True, False, False, True), (True, False, True, False),
    (True, False, False, False),
    (False, True, True, True), (False, True, False, True), (False, True, True, False),
    (False, True, False, False),
    (False, False, True, True), (False, False, False, True), (False, False, True, False),
    (False, False, False, False),
]


def colores(clave):
    rural, lima, nativa, sin_sec = clave
    c = [col for activo, col in [(rural, TEAL), (lima, AMARILLO), (nativa, AZUL), (sin_sec, ROJO)]
         if activo]
    return c or [GRIS]


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


def calcular():
    d = base.cargar()
    x = d[(d.pobreza < 3) & (d.p208a >= 25)].copy()
    x["lima"] = x.dominio == 8
    claves = ["rural", "lima", "nativa", "sin_secundaria"]
    w = x.groupby(claves)[PESO].sum().reindex(ORDEN, fill_value=0)
    pct = 100 * w / w.sum()
    cuenta = base.de_50(pct.reset_index(drop=True))
    combos = dict(zip(ORDEN, cuenta))
    totales = {}
    for i, c in enumerate(claves):
        totales[c] = (sum(n for k, n in combos.items() if k[i]),
                      100 * np.average(x[c], weights=x[PESO]))
    totales["ninguna"] = (combos[(False, False, False, False)], pct[(False, False, False, False)])
    return combos, totales


def main():
    SALIDA.mkdir(exist_ok=True)
    combos, tot = calcular()

    fig = plt.figure(figsize=(14, 7.6), facecolor="white")
    ax = fig.add_axes([0.03, 0.1, 0.58, 0.82])
    ax.set_xlim(-0.2, 15.6)
    ax.set_ylim(-0.3, 10.4)
    ax.set_aspect("equal")
    ax.axis("off")

    k = 0
    for clave in ORDEN:
        for _ in range(combos[clave]):
            fila, col = divmod(k, 10)
            icono(ax, col * 1.6, 8.4 - fila * 2.1, colores(clave))
            k += 1

    # Leyenda
    lg = fig.add_axes([0.64, 0.1, 0.34, 0.82])
    lg.set_xlim(0, 10)
    lg.set_ylim(0, 10)
    lg.axis("off")
    lg.add_patch(Rectangle((0, 8.35), 10, 1.5, color=TINTA, lw=0))
    lg.text(5, 9.1, "Si los adultos en condición de pobreza\nen el Perú fueran solo 50:",
            ha="center", va="center", fontsize=13, color="white", weight="bold")
    items = [
        (TEAL, "Vive en zona rural", tot["rural"]),
        (AMARILLO, "Vive en Lima Metropolitana", tot["lima"]),
        (AZUL, "Lengua materna quechua, aimara\nu otra nativa", tot["nativa"]),
        (ROJO, "No terminó la secundaria", tot["sin_secundaria"]),
        (GRIS, "Ninguna de las anteriores", tot["ninguna"]),
    ]
    y = 7.3
    for color, texto, (n, pct) in items:
        lg.add_patch(Rectangle((0.1, y - 0.28), 0.55, 0.55, color=color, lw=0))
        lg.text(0.95, y, texto, va="center", fontsize=11.5, color=TINTA)
        lg.text(9.9, y, f"{n} de 50", va="center", ha="right", fontsize=12.5, color=TINTA,
                weight="bold")
        lg.text(9.9, y - 0.5, f"({pct:.0f} %)", va="center", ha="right", fontsize=9.5,
                color="#777")
        y -= 1.45
    lg.text(0.1, y + 0.35,
            "Un ícono con varios colores reúne varias\ncaracterísticas. Ninguna de las anteriores: "
            "vive en\notra ciudad, su lengua materna es el castellano\ny terminó la secundaria.",
            va="top", fontsize=9.5, color="#555", style="italic")

    fig.text(0.03, 0.03, "Nota: adultos de 25 años o más en hogares en situación de pobreza "
             "monetaria. Ponderado con el factor de población (FACPOB07).\n"
             "Fuente: INEI, Encuesta Nacional de Hogares (ENAHO) 2025.",
             fontsize=9, color="#444")
    fig.savefig(SALIDA / "iconos_adultos_pobres_2025.png", dpi=170, facecolor="white")

    for clave in ORDEN:
        print(clave, combos[clave])
    print({k: (n, round(p, 1)) for k, (n, p) in tot.items()})


if __name__ == "__main__":
    main()
