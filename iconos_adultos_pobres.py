"""
Borrador del gráfico de íconos "La pobreza en adultos en el Perú" (2025), con los
grises ("ninguna de las tres") separados en Lima Metropolitana / resto urbano.

Cifras: pobreza_adultos_2025.py (adultos pobres de 25+ años, FACTOR07 = FACPOB07).
Uso:    python iconos_adultos_pobres.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

SALIDA = Path(__file__).resolve().parent / "resultados"

TEAL, AZUL, ROJO = "#14A7A7", "#3F51A3", "#E2294F"
GRIS, LIMA = "#D3D3CF", "#F2A93B"

# (colores de franjas, cantidad) en el orden del gráfico original
GRUPOS = [
    ([LIMA], 11),               # ninguna de las tres, Lima Metropolitana
    ([GRIS], 6),                # ninguna de las tres, resto urbano
    ([ROJO], 12),               # solo sin secundaria
    ([AZUL], 3),                # solo lengua nativa
    ([AZUL, ROJO], 5),          # nativa + sin secundaria
    ([TEAL], 1),                # solo rural
    ([TEAL, ROJO], 6),          # rural + sin secundaria
    ([TEAL, AZUL], 1),          # rural + nativa
    ([TEAL, AZUL, ROJO], 5),    # las tres
]

LEYENDA = [
    (TEAL, "Vive en zona rural: ", "13 de 50", "(27 %)"),
    (AZUL, "Lengua materna quechua,\naimara u otra nativa: ", "14 de 50", "(27 %)"),
    (ROJO, "No terminó la secundaria: ", "28 de 50", "(55 %)"),
    (LIMA, "Ninguna de las tres y vive en\nLima Metropolitana: ", "11 de 50", "(22 %)"),
    (GRIS, "Ninguna de las tres, en otra\nzona urbana: ", "6 de 50", "(12 %)"),
]


def icono(ax, x, y, colores, s=1.0):
    """Persona de ancho s, con franjas verticales de colores."""
    n = len(colores)
    for i, c in enumerate(colores):
        clip = Rectangle((x + i * s / n, y - 0.1), s / n, 2 * s, transform=ax.transData)
        for forma in (Circle((x + s / 2, y + 1.18 * s), 0.34 * s, color=c, lw=0),
                      FancyBboxPatch((x, y), s, 0.78 * s, color=c, lw=0,
                                     boxstyle=f"round,pad=0,rounding_size={0.32 * s}"),
                      Rectangle((x, y), s, 0.4 * s, color=c, lw=0)):
            ax.add_patch(forma)
            forma.set_clip_path(clip)


def main():
    SALIDA.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 21)
    ax.set_ylim(-0.6, 15.6)
    ax.set_aspect("equal")
    ax.axis("off")

    k = 0
    for colores, n in GRUPOS:
        for _ in range(n):
            fila, col = divmod(k, 8)
            icono(ax, col * 1.6, 13.6 - fila * 2.1, colores)
            k += 1

    x0, y = 13.4, 12.6
    ax.text(x0, y + 1.6, "Si los adultos en condición de pobreza\nen el Perú fueran solo 50:",
            fontsize=13, weight="bold", color="#14234B", va="center")
    for color, texto, cifra, pct in LEYENDA:
        ax.add_patch(Rectangle((x0, y - 0.25), 0.5, 0.5, color=color, lw=0))
        ax.text(x0 + 0.8, y, texto + cifra + "  " + pct, fontsize=11, color="#14234B", va="center")
        y -= 2.0
    ax.text(x0, y + 0.4,
            "2 de cada 3 adultos pobres que no son rurales,\nno tienen lengua nativa y terminaron la\n"
            "secundaria viven en Lima Metropolitana.",
            fontsize=10.5, style="italic", color="#444", va="top")

    fig.text(0.02, 0.02, "Adultos de 25 años o más en hogares pobres. Ponderado con FACPOB07.\n"
             "Fuente: INEI, Encuesta Nacional de Hogares (ENAHO) 2025.", fontsize=9, color="#444")
    fig.savefig(SALIDA / "iconos_adultos_pobres_2025.png", dpi=170, bbox_inches="tight",
                facecolor="white")


if __name__ == "__main__":
    main()
