"""
Descarga Sumaria (módulo 34) y Programas Sociales (módulo 37 / cap. 700) de la
ENAHO anual, usando el paquete inei-microdatos, y los descomprime en enaho-AAAA/.

Uso:
    pip install inei-microdatos
    python descargar_enaho.py               # 2020-2024 (por defecto)
    python descargar_enaho.py 2020 2025     # rango de años
"""

import copy
import sys
import zipfile
from pathlib import Path

from inei_microdatos import download_modules, load_catalog
from inei_microdatos.catalog import filter_catalog

RAIZ = Path(__file__).resolve().parent
MODULOS = {"34", "37"}  # Sumaria, Programas Sociales
FORMATO = "STATA"       # .dta: nombres y tipos de variables consistentes entre años


def catalogo(anio_min, anio_max):
    """Catálogo ENAHO anual (Ene-Dic) restringido a los módulos 34 y 37."""
    cat = copy.deepcopy(filter_catalog(load_catalog(), survey="enaho",
                                       year_min=anio_min, year_max=anio_max))
    cat = [s for s in cat if "PANEL" not in s["value"].upper()]
    for s in cat:
        for anio, periodos in s["years"].items():
            for p in [p for p in periodos if not p.startswith("Anual")]:
                del periodos[p]
            for d in periodos.values():
                d["modules"] = [m for m in d["modules"] if m["module_code"] in MODULOS]
    return cat


def main():
    anio_min, anio_max = (int(a) for a in sys.argv[1:3]) if len(sys.argv) > 2 else (2020, 2024)
    tmp = RAIZ / "_descargas"
    res = download_modules(catalogo(anio_min, anio_max), dest=tmp, fmt=FORMATO,
                           layout="by-year", workers=2)
    print(res)

    for z in sorted(tmp.rglob("*.zip")):
        anio = z.parent.name
        destino = RAIZ / f"enaho-{anio}"
        destino.mkdir(exist_ok=True)
        with zipfile.ZipFile(z) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                nombre = Path(info.filename).name  # aplana subcarpetas del zip
                (destino / nombre).write_bytes(zf.read(info))
                print(f"{anio}: {nombre}")


if __name__ == "__main__":
    main()
