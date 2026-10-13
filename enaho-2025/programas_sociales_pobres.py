"""
Cobertura de programas sociales en hogares pobres - ENAHO 2025.

Población: hogares en situación de pobreza (POBREZA = 1 o 2 en Sumaria),
no solo los hogares pobres que reciben algún programa.

Programas (módulo 700):
  Pensión 65                    P710$05  (últimos 3 años)
  Juntos                        P710$04  (últimos 3 años)
  Vaso de Leche                 P701$01  (últimos 3 meses)
  Qali Warma / Wasi Mikuna      P701$03 o P701$04  (desayuno o almuerzo escolar, últimos 3 meses)
  Ninguno de los cuatro         ninguno de los anteriores

Ponderación:
  por hogar   -> FACTOR07
  por persona -> FACTOR07 * MIEPERHO

Por defecto se excluyen los hogares sin respuesta al módulo 700 (P701 o P710
en blanco; ~12 % de los hogares pobres, ponderado). El gráfico original los
contaba como "no recibe"; esa versión se guarda aparte como *_replica.csv.

Uso:  python programas_sociales_pobres.py
Salidas en ./resultados/
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "resultados"
ANIO = 2025
LLAVE = ["CONGLOME", "VIVIENDA", "HOGAR"]

PROGRAMAS = {
    "Pensión 65": ["P710$05"],
    "Juntos": ["P710$04"],
    "Vaso de Leche": ["P701$01"],
    "Qali Warma / Wasi Mikuna": ["P701$03", "P701$04"],
}
NINGUNO = "No recibe ninguno"

# Colores del gráfico original; gris para "ninguno"
COLORES = {
    "Pensión 65": "#D13C55",
    "Juntos": "#E8A945",
    "Vaso de Leche": "#4EA3A7",
    "Qali Warma / Wasi Mikuna": "#42509E",
    NINGUNO: "#8C8C8C",
}

GRUPOS = {
    "Pobres (total)": [1, 2],
    "Pobres extremos": [1],
    "Pobres no extremos": [2],
    "No pobres": [3],
    "Total hogares": [1, 2, 3],
}


def leer(nombre, **kw):
    return pd.read_csv(AQUI / nombre, sep=";", encoding="latin1", decimal=",",
                       dtype={c: str for c in LLAVE}, **kw)


def cargar(excluir_no_respuesta=True):
    sumaria = leer(f"Sumaria-{ANIO}.csv",
                   usecols=LLAVE + ["MIEPERHO", "POBREZA", "FACTOR07"])
    vars700 = sorted({v for vs in PROGRAMAS.values() for v in vs})
    m700 = leer(f"Enaho01-{ANIO}-700.csv", usecols=LLAVE + vars700)

    df = sumaria.merge(m700, on=LLAVE, how="left", validate="1:1")

    for v in vars700:
        df[v] = pd.to_numeric(df[v].astype(str).str.strip(), errors="coerce")
    completo = df[vars700].notna().all(axis=1)
    print(f"Hogares en Sumaria: {len(df):,}")
    print(f"Sin respuesta en módulo 700: {(~completo).sum():,} "
          f"({'excluidos' if excluir_no_respuesta else 'contados como no recibe'})")
    if excluir_no_respuesta:
        df = df[completo].copy()

    for prog, vs in PROGRAMAS.items():
        df[prog] = (df[vs] == 1).any(axis=1).astype(int)
    df["n_programas"] = df[list(PROGRAMAS)].sum(axis=1)
    df[NINGUNO] = (df["n_programas"] == 0).astype(int)

    df["peso_hogar"] = df["FACTOR07"]
    df["peso_persona"] = df["FACTOR07"] * df["MIEPERHO"]
    return df


def pct(x, w):
    return 100 * np.average(x, weights=w)


def tabular(df):
    filas = []
    nprog = {"0 programas": df["n_programas"] == 0,
             "1 programa": df["n_programas"] == 1,
             "2 programas": df["n_programas"] == 2,
             "3 o más programas": df["n_programas"] >= 3}
    for grupo, codigos in GRUPOS.items():
        sub = df[df["POBREZA"].isin(codigos)]
        nprog_sub = {k: v[sub.index] for k, v in nprog.items()}
        for unidad, peso in [("hogar", "peso_hogar"), ("persona", "peso_persona")]:
            w = sub[peso]
            indicadores = {c: sub[c] for c in list(PROGRAMAS) + [NINGUNO]}
            indicadores.update({k: v.astype(int) for k, v in nprog_sub.items()})
            for ind, x in indicadores.items():
                filas.append({
                    "anio": ANIO, "poblacion": grupo, "ponderacion": unidad,
                    "indicador": ind, "porcentaje": round(pct(x, w), 2),
                    "n_muestral_hogares": len(sub),
                    "n_muestral_con_indicador": int(x.sum()),
                })
    return pd.DataFrame(filas)


def grafico_programas(tab):
    """Barras agrupadas: % de pobres que recibe cada programa, por hogar y por persona."""
    cats = list(PROGRAMAS) + [NINGUNO]
    t = tab[tab.poblacion == "Pobres (total)"].set_index(["ponderacion", "indicador"])["porcentaje"]

    fig, ax = plt.subplots(figsize=(10, 5.6))
    x = np.arange(len(cats))
    ancho = 0.38
    for i, (unidad, etiqueta, alpha) in enumerate(
            [("hogar", "Hogares pobres", 1.0), ("persona", "Personas pobres", 0.55)]):
        vals = [t[(unidad, c)] for c in cats]
        barras = ax.bar(x + (i - 0.5) * ancho, vals, ancho - 0.03,
                        color=[COLORES[c] for c in cats], alpha=alpha,
                        edgecolor="white", linewidth=1.5, label=etiqueta)
        for b, v in zip(barras, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}%",
                    ha="center", va="bottom", fontsize=9, color="#222")

    ax.set_xticks(x, [c.replace(" / ", " /\n") for c in cats], fontsize=10)
    ax.set_ylabel("% de la población pobre")
    ax.set_ylim(0, max(tab.porcentaje[tab.poblacion == "Pobres (total)"].max() + 8, 10))
    ax.yaxis.grid(True, color="#e5e5e5")
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)

    # Leyenda neutra (opaco = hogares, claro = personas)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#555", label="Hogares pobres"),
                       Patch(color="#555", alpha=0.55, label="Personas pobres")],
              frameon=False, loc="upper left")

    ext = tab.set_index(["poblacion", "ponderacion", "indicador"])["porcentaje"]
    ax.set_title(f"Hogares y personas pobres que reciben cada programa social ({ANIO})",
                 fontsize=13, weight="bold", loc="left")
    fig.text(0.01, 0.01,
             "Nota: un hogar puede recibir más de un programa, por lo que las barras no suman 100 %. "
             "Vaso de Leche y Qali Warma: últimos 3 meses;\nJuntos y Pensión 65: últimos 3 años. "
             f"{ext[('Pobres extremos', 'hogar', NINGUNO)]:.1f} % de los hogares en pobreza extrema "
             "no recibe ninguno de los cuatro.\n"
             f"Fuente: INEI, ENAHO {ANIO}, Sumaria y módulo 700 (Programas Sociales). "
             "Ponderado con FACTOR07 (hogares) y FACTOR07 × MIEPERHO (personas).",
             fontsize=8, color="#444", va="bottom")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.savefig(SALIDA / f"programas_pobres_{ANIO}.png", dpi=200)
    plt.close(fig)


def grafico_n_programas(tab):
    """Barras apiladas al 100 %: número de programas que recibe la población pobre."""
    cats = ["0 programas", "1 programa", "2 programas", "3 o más programas"]
    colores = ["#8C8C8C", "#C6D3EA", "#7E8FC8", "#42509E"]
    barras = [("Pobres (total)", "hogar"), ("Pobres (total)", "persona"),
              ("Pobres extremos", "hogar"), ("Pobres extremos", "persona")]
    t = tab.set_index(["poblacion", "ponderacion", "indicador"])["porcentaje"]

    fig, ax = plt.subplots(figsize=(9, 5.6))
    x = np.arange(len(barras))
    base = np.zeros(len(barras))
    for c, col in zip(cats, colores):
        vals = np.array([t[(p, u, c)] for p, u in barras])
        ax.bar(x, vals, 0.6, bottom=base, color=col, edgecolor="white",
               linewidth=2, label=c)
        for xi, b, v in zip(x, base, vals):
            if v >= 3:
                ax.text(xi, b + v / 2, f"{v:.1f}%", ha="center", va="center",
                        fontsize=9, color="white" if col in ("#8C8C8C", "#42509E", "#7E8FC8") else "#222",
                        weight="bold")
        base += vals

    ax.set_xticks(x, [f"{p}\n({'hogares' if u == 'hogar' else 'personas'})" for p, u in barras])
    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    ax.set_title(f"¿Cuántos de los cuatro programas recibe la población pobre? ({ANIO})",
                 fontsize=13, weight="bold", loc="left")
    fig.text(0.01, 0.01,
             "Programas: Pensión 65, Juntos, Vaso de Leche, Qali Warma / Wasi Mikuna.\n"
             f"Fuente: INEI, ENAHO {ANIO}, Sumaria y módulo 700. Ponderado con FACTOR07 (hogares) "
             "y FACTOR07 × MIEPERHO (personas).",
             fontsize=8, color="#444", va="bottom")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(SALIDA / f"n_programas_pobres_{ANIO}.png", dpi=200)
    plt.close(fig)


def main():
    SALIDA.mkdir(exist_ok=True)
    df = cargar()
    tab = tabular(df)
    tab.to_csv(SALIDA / f"programas_sociales_pobres_{ANIO}.csv", index=False,
               encoding="utf-8-sig")

    ancha = tab.pivot_table(index="indicador", columns=["poblacion", "ponderacion"],
                            values="porcentaje", sort=False)
    ancha.to_csv(SALIDA / f"programas_sociales_pobres_{ANIO}_ancha.csv",
                 encoding="utf-8-sig")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(ancha.round(1))

    grafico_programas(tab)
    grafico_n_programas(tab)

    # Réplica del gráfico original: sin respuesta al 700 = no recibe
    tabular(cargar(excluir_no_respuesta=False)).to_csv(
        SALIDA / f"programas_sociales_pobres_{ANIO}_replica.csv", index=False,
        encoding="utf-8-sig")


if __name__ == "__main__":
    main()
