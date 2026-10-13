"""
Cobertura de programas sociales en la población pobre - ENAHO 2020-2025.

Población: hogares en situación de pobreza (POBREZA = 1 o 2 en Sumaria),
no solo los hogares pobres que reciben algún programa.

Programas (módulo 700; mismos códigos 2020-2025):
  Pensión 65                    P710_05  (últimos 3 años)
  Juntos                        P710_04  (últimos 3 años)
  Vaso de Leche                 P701_01  (últimos 3 meses)
  Qali Warma / Wasi Mikuna      P701_03 o P701_04  (desayuno o almuerzo escolar, últimos 3 meses)
  No recibe ninguno             ninguno de los cuatro

Ponderación:
  por hogar   -> FACTOR07
  por persona -> FACTOR07 * MIEPERHO

Por defecto se excluyen los hogares sin respuesta al módulo 700 (variables en
blanco). El gráfico original los contaba como "no recibe"; esa versión se
guarda aparte en *_replica.csv.

Datos: carpetas enaho-AAAA/ con Sumaria y el módulo 700 (.dta o .csv).
Uso:   python programas_sociales_pobres.py
Salidas en ./resultados/
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
SALIDA = RAIZ / "resultados"
ANIOS = range(2020, 2026)
LLAVE = ["conglome", "vivienda", "hogar"]

PROGRAMAS = {
    "Pensión 65": ["p710_05"],
    "Juntos": ["p710_04"],
    "Vaso de Leche": ["p701_01"],
    "Qali Warma / Wasi Mikuna": ["p701_03", "p701_04"],
}
NINGUNO = "No recibe ninguno"
N_PROGRAMAS = ["0 programas", "1 programa", "2 programas", "3 o más programas"]

# Colores del gráfico original; gris para "ninguno"
COLORES = {
    "Pensión 65": "#D13C55",
    "Juntos": "#E8A945",
    "Vaso de Leche": "#4EA3A7",
    "Qali Warma / Wasi Mikuna": "#42509E",
    NINGUNO: "#8C8C8C",
}
COLORES_N = ["#8C8C8C", "#C6D3EA", "#7E8FC8", "#42509E"]

GRUPOS = {
    "Pobres (total)": [1, 2],
    "Pobres extremos": [1],
    "Pobres no extremos": [2],
    "No pobres": [3],
    "Total hogares": [1, 2, 3],
}
NOMBRE = {"Pobres (total)": "pobre", "Pobres extremos": "en pobreza extrema"}
UNIDADES = {"hogar": "peso_hogar", "persona": "peso_persona"}
FUENTE = ("Fuente: INEI, ENAHO {a}, Sumaria y módulo 700 (Programas Sociales). "
          "Ponderado con FACTOR07 (hogares) y FACTOR07 × MIEPERHO (personas).")


def leer(carpeta, patron, columnas):
    """Lee el primer .dta o .csv de la carpeta que calce con el patrón."""
    archivos = sorted(carpeta.glob(patron + ".dta")) + sorted(carpeta.glob(patron + ".csv"))
    if not archivos:
        raise FileNotFoundError(f"No hay {patron}.dta/.csv en {carpeta}")
    f = archivos[0]
    if f.suffix == ".dta":
        df = pd.read_stata(f, convert_categoricals=False)
    else:
        df = pd.read_csv(f, sep=";", encoding="latin1", decimal=",", dtype=str)
    df.columns = [c.lower().replace("$", "_") for c in df.columns]
    df = df[columnas].copy()
    for c in columnas:
        if c in LLAVE:
            df[c] = df[c].astype(str).str.strip()
        else:
            df[c] = pd.to_numeric(df[c].astype(str).str.strip().str.replace(",", "."),
                                  errors="coerce")
    return df


def cargar(anio, excluir_no_respuesta=True):
    carpeta = RAIZ / f"enaho-{anio}"
    sumaria = leer(carpeta, f"[Ss]umaria[-_]{anio}", LLAVE + ["mieperho", "pobreza", "factor07"])
    vars700 = sorted({v for vs in PROGRAMAS.values() for v in vs})
    m700 = leer(carpeta, f"[Ee]naho01-{anio}-700", LLAVE + vars700)

    df = sumaria.merge(m700, on=LLAVE, how="left", validate="1:1")
    completo = df[vars700].notna().all(axis=1)
    if excluir_no_respuesta:
        print(f"{anio}: {len(df):,} hogares; {(~completo).sum():,} sin respuesta al 700 (excluidos)")
        df = df[completo].copy()

    for prog, vs in PROGRAMAS.items():
        df[prog] = (df[vs] == 1).any(axis=1).astype(int)
    df["n_programas"] = df[list(PROGRAMAS)].sum(axis=1)
    df[NINGUNO] = (df["n_programas"] == 0).astype(int)
    for etiqueta, cond in zip(N_PROGRAMAS, [df.n_programas == 0, df.n_programas == 1,
                                             df.n_programas == 2, df.n_programas >= 3]):
        df[etiqueta] = cond.astype(int)

    df["peso_hogar"] = df["factor07"]
    df["peso_persona"] = df["factor07"] * df["mieperho"]
    return df


def tabular(df, anio):
    filas = []
    for grupo, codigos in GRUPOS.items():
        sub = df[df["pobreza"].isin(codigos)]
        for unidad, peso in UNIDADES.items():
            for ind in list(PROGRAMAS) + [NINGUNO] + N_PROGRAMAS:
                filas.append({
                    "anio": anio, "poblacion": grupo, "ponderacion": unidad,
                    "indicador": ind,
                    "porcentaje": round(100 * np.average(sub[ind], weights=sub[peso]), 2),
                    "n_muestral_hogares": len(sub),
                    "n_muestral_con_indicador": int(sub[ind].sum()),
                })
    return pd.DataFrame(filas)


def estilo(ax):
    ax.yaxis.grid(True, color="#e5e5e5")
    ax.set_axisbelow(True)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")


def separar(valores, minimo=3.2):
    """Posiciones verticales para etiquetas, separadas al menos `minimo` puntos."""
    pos, ultimo = {}, None
    for k in sorted(valores, key=valores.get):
        y = valores[k] if ultimo is None else max(valores[k], ultimo + minimo)
        pos[k], ultimo = y, y
    return pos


def grafico_lineas(tab, poblacion="Pobres (total)", sufijo="pobres"):
    """Líneas 2020-2025: % de la población que recibe cada programa y que no recibe ninguno."""
    t = tab[tab.poblacion == poblacion]
    anios = sorted(t.anio.unique())
    series = list(PROGRAMAS) + [NINGUNO]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)

    for ax, (unidad, titulo) in zip(axes, [("hogar", "Hogares"), ("persona", "Personas")]):
        tu = t[t.ponderacion == unidad].set_index(["indicador", "anio"])["porcentaje"]
        ini = separar({s: tu[(s, anios[0])] for s in series})
        fin = separar({s: tu[(s, anios[-1])] for s in series})
        for s in series:
            v = [tu[(s, a)] for a in anios]
            ax.plot(anios, v, color=COLORES[s], lw=2.2, marker="o", ms=6,
                    mec="white", mew=1.2, ls="--" if s == NINGUNO else "-")
            ax.text(anios[0] - 0.15, ini[s], f"{v[0]:.1f}%", ha="right", va="center",
                    fontsize=8.5, color="#333")
            ax.text(anios[-1] + 0.15, fin[s], f"{v[-1]:.1f}%  {s}", va="center",
                    fontsize=9, color=COLORES[s], weight="bold")
        ax.set_title(titulo, loc="left", fontsize=12, weight="bold")
        ax.set_xticks(anios)
        ax.set_xlim(anios[0] - 0.9, anios[-1] + 2.6)
        for s in ["bottom"]:
            ax.spines[s].set_bounds(anios[0], anios[-1])
        estilo(ax)

    axes[0].set_ylim(0, max(60, t.porcentaje[t.indicador.isin(series)].max() + 5))
    axes[0].set_ylabel(f"% de la población ({poblacion.lower()})")
    fig.suptitle(f"¿Los programas sociales llegan a la población {NOMBRE[poblacion]}? ({anios[0]}–{anios[-1]})",
                 x=0.01, ha="left", fontsize=14, weight="bold")
    fig.text(0.01, 0.01,
             "Nota: un hogar puede recibir más de un programa, por lo que las líneas no suman 100 %. "
             "Vaso de Leche y Qali Warma / Wasi Mikuna: últimos 3 meses; Juntos y Pensión 65: últimos 3 años.\n"
             "Se excluyen los hogares sin respuesta al módulo 700. "
             + FUENTE.format(a=f"{anios[0]}–{anios[-1]}"),
             fontsize=8, color="#444", va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(SALIDA / f"lineas_programas_{sufijo}.png", dpi=200)
    plt.close(fig)


def grafico_apilado(tab, poblacion="Pobres (total)", sufijo="pobres"):
    """Barras apiladas al 100 % por año: cuántos de los cuatro programas recibe la población."""
    t = tab[tab.poblacion == poblacion]
    anios = sorted(t.anio.unique())
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2), sharey=True)

    for ax, (unidad, titulo) in zip(axes, [("hogar", "Hogares"), ("persona", "Personas")]):
        tu = t[t.ponderacion == unidad].set_index(["indicador", "anio"])["porcentaje"]
        base = np.zeros(len(anios))
        for c, col in zip(N_PROGRAMAS, COLORES_N):
            vals = np.array([tu[(c, a)] for a in anios])
            ax.bar(anios, vals, 0.68, bottom=base, color=col, edgecolor="white",
                   linewidth=2, label=c)
            for x, b, v in zip(anios, base, vals):
                if v >= 4:
                    ax.text(x, b + v / 2, f"{v:.1f}%", ha="center", va="center", fontsize=8.5,
                            weight="bold", color="#222" if col == "#C6D3EA" else "white")
            base += vals
        ax.set_title(titulo, loc="left", fontsize=12, weight="bold")
        ax.set_xticks(anios)
        ax.set_ylim(0, 100)
        estilo(ax)
        ax.yaxis.grid(False)

    axes[0].set_ylabel(f"% de la población ({poblacion.lower()})")
    axes[0].legend(frameon=False, ncol=4, loc="upper left", bbox_to_anchor=(0, -0.07))
    fig.suptitle(f"¿Cuántos de los cuatro programas recibe la población {NOMBRE[poblacion]}? ({anios[0]}–{anios[-1]})",
                 x=0.01, ha="left", fontsize=14, weight="bold")
    fig.text(0.01, 0.01,
             "Programas: Pensión 65, Juntos, Vaso de Leche, Qali Warma / Wasi Mikuna. "
             "Se excluyen los hogares sin respuesta al módulo 700.\n"
             + FUENTE.format(a=f"{anios[0]}–{anios[-1]}"),
             fontsize=8, color="#444", va="bottom")
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(SALIDA / f"apilado_n_programas_{sufijo}.png", dpi=200)
    plt.close(fig)


def main():
    SALIDA.mkdir(exist_ok=True)
    anios = [a for a in ANIOS if (RAIZ / f"enaho-{a}").is_dir()]

    tab = pd.concat([tabular(cargar(a), a) for a in anios], ignore_index=True)
    replica = pd.concat([tabular(cargar(a, excluir_no_respuesta=False), a) for a in anios],
                        ignore_index=True)

    tab.to_csv(SALIDA / "programas_sociales_pobres.csv", index=False, encoding="utf-8-sig")
    replica.to_csv(SALIDA / "programas_sociales_pobres_replica.csv", index=False,
                   encoding="utf-8-sig")
    for unidad in UNIDADES:
        ancha = (tab[(tab.ponderacion == unidad) & (tab.poblacion == "Pobres (total)")]
                 .pivot(index="indicador", columns="anio", values="porcentaje")
                 .reindex(list(PROGRAMAS) + [NINGUNO] + N_PROGRAMAS))
        ancha.to_csv(SALIDA / f"pobres_por_{unidad}_ancha.csv", encoding="utf-8-sig")
        print(f"\nPobres, ponderado por {unidad}:\n{ancha.round(1)}")

    grafico_lineas(tab)
    grafico_apilado(tab)
    grafico_lineas(tab, "Pobres extremos", "pobres_extremos")
    grafico_apilado(tab, "Pobres extremos", "pobres_extremos")


if __name__ == "__main__":
    main()
