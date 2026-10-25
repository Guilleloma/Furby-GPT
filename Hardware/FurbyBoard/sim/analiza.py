"""Ejecuta las simulaciones de sim/, comprueba cada criterio (PASS/FAIL) y dibuja las formas de onda.

Uso, desde sim/:  python3 -I analiza.py [bloque ...]   (sin argumentos, todos los bloques)
Necesita ngspice en el PATH y numpy + matplotlib. Los datos van a datos/ (fuera de git) y las
figuras a png/. La tabla que imprime es la que se copia en RESULTADOS.md.
"""
import pathlib
import re
import subprocess
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

AQUI = pathlib.Path(__file__).resolve().parent
DATOS = AQUI / "datos"
PNG = AQUI / "png"

# Paleta categórica en orden fijo (skill dataviz, palette.md) y tintas neutras para límites y texto
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
SUPERFICIE = "#fcfcfb"
TINTA = "#2b2a27"
TINTA_SUAVE = "#6b6a65"


def correr(cir):
    """Ejecuta un .cir y devuelve sus medidas (líneas «nombre = valor») como diccionario."""
    DATOS.mkdir(exist_ok=True)
    salida = subprocess.run(["ngspice", "-b", cir], cwd=AQUI, capture_output=True, text=True).stdout
    medidas = {}
    for linea in salida.splitlines():
        m = re.match(r"^\s*([a-z][a-z0-9_]*)\s*=\s*([-+0-9.eE]+)", linea)
        if m:
            medidas[m.group(1)] = float(m.group(2))
    return medidas


def leer(nombre):
    """Lee un fichero de wrdata (wr_singlescale + wr_vecnames) como diccionario de columnas."""
    ruta = DATOS / nombre
    with open(ruta) as f:
        cabecera = f.readline().split()
    valores = np.loadtxt(ruta, skiprows=1, ndmin=2)
    return {c: valores[:, i] for i, c in enumerate(cabecera)}


def figura(fichero, titulo, paneles, escala_x=1e3, etiqueta_x="tiempo (ms)"):
    """Paneles apilados con eje x común y un solo eje y cada uno.

    paneles: lista de (etiqueta_y, [(x, y, nombre_serie)], [(valor, texto_del_límite)]).
    """
    PNG.mkdir(exist_ok=True)
    fig, ejes = plt.subplots(len(paneles), 1, figsize=(9, 2.6 * len(paneles)), sharex=True,
                             facecolor=SUPERFICIE, squeeze=False)
    for eje, (etiqueta_y, curvas, limites) in zip(ejes[:, 0], paneles):
        eje.set_facecolor(SUPERFICIE)
        for i, (x, y, nombre) in enumerate(curvas):
            eje.plot(x * escala_x, y, color=SERIES[i % len(SERIES)], lw=1.4, label=nombre)
        for valor, texto in limites:
            eje.axhline(valor, color=TINTA_SUAVE, lw=1, ls="--")
            eje.annotate(texto, xy=(1, valor), xycoords=("axes fraction", "data"), xytext=(-4, 3),
                         textcoords="offset points", ha="right", va="bottom", fontsize=8, color=TINTA_SUAVE)
        eje.set_ylabel(etiqueta_y, color=TINTA)
        eje.grid(True, color="#e4e3df", lw=0.6)
        for lado in ("top", "right"):
            eje.spines[lado].set_visible(False)
        eje.tick_params(colors=TINTA_SUAVE)
        if len(curvas) > 1:
            eje.legend(loc="best", fontsize=8, frameon=False)
    ejes[-1, 0].set_xlabel(etiqueta_x, color=TINTA)
    ejes[0, 0].set_title(titulo, color=TINTA, loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(PNG / fichero, dpi=110, facecolor=SUPERFICIE)
    plt.close(fig)


class Tabla:
    """Filas «Magnitud | Resultado | Criterio | PASS/FAIL» de un bloque."""

    def __init__(self, bloque):
        self.bloque = bloque
        self.filas = []

    def fila(self, magnitud, resultado, criterio, pasa=None):
        veredicto = "—" if pasa is None else ("PASS" if pasa else "**FAIL**")
        self.filas.append((magnitud, resultado, criterio, veredicto))

    def imprimir(self):
        print(f"\n### {self.bloque}\n")
        print("| Magnitud | Resultado | Criterio | PASS/FAIL |")
        print("|----------|-----------|----------|-----------|")
        for f in self.filas:
            print("| " + " | ".join(f) + " |")


def v(x, d=2):
    """Número con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


# ------------------------------------------------------------------------------------------
def bloque_tps63802():
    t = Tabla("TPS63802 (3V3)")
    m = correr("tps63802_3v3.cir")
    t.fila("Calibración: caída con 0,1 → 1 A, VI 3,3 V, 22 µF nominales", f"{v(m['cal_caida']*1e3, 0)} mV",
           "≈ 120 mV leídos en la figura 10-22", None)
    caida_nom = m["nom_vrep"] - m["nom_vmin"]
    t.fila("3V3 en el módulo con 0,1 → 0,55 A, batería 3,0 V (nominal)",
           f"mín. {v(m['nom_vmin'])} V (caída {v(caida_nom*1e3, 0)} mV)", "≥ 3,00 V", m["nom_vmin"] >= 3.0)
    t.fila("3V3 en el módulo, peor caso (C −20 %, GT/2)", f"mín. {v(m['peor_vmin'])} V", "≥ 3,00 V",
           m["peor_vmin"] >= 3.0)
    t.fila("3V3 en el módulo con 0,55 A en régimen (caída de la pista de 58 mΩ)",
           f"{v(m['nom_vcarga'], 3)} V", "3,30 V ± 3 % (3,20–3,40)", 3.20 <= m["nom_vcarga"] <= 3.40)
    t.fila("VSYS en la entrada de U3 con 0,55 A, batería 3,0 V", f"mín. {v(m['nom_vsysmin'])} V",
           "≥ 2,3 V (VIN;LOAD para 2 A)", m["nom_vsysmin"] >= 2.3)
    t.fila("Desenchufe del USB (4,4 → 3,0 V en 10 µs, 0,55 A)",
           f"VSYS mín. {v(m['lin_vsysmin'])} V; 3V3 {v(m['lin_vmin'])}–{v(m['lin_vmax'])} V",
           "VSYS ≥ 2,3 V; el modelo no tiene paso de línea: la figura 10-28 da < 0,1 V con 2,2 → 4,2 V",
           m["lin_vsysmin"] >= 2.3 and m["lin_vmin"] - 0.1 >= 3.0)
    r = correr("tps63802_rizado.cir")
    t.fila("Pico de L1, buck (VSYS 4,4 V, 0,7 A, L −20 %)", f"{v(r['b_ipk'])} A", "< 3,8 A con margen ≥ 20 %",
           r["b_ipk"] < 3.8 / 1.2)
    t.fila("Pico de L1, boost (VSYS 3,0 V, 0,7 A, L −20 %)", f"{v(r['s_ipk'])} A", "< 4,0 A (mín.) con margen ≥ 20 %",
           r["s_ipk"] < 4.0 / 1.2)
    t.fila("Rizado de 3V3 en C7/C8, buck / boost (20 MHz)", f"{v(r['b_rpp']*1e3, 1)} / {v(r['s_rpp']*1e3, 1)} mV pp",
           "≤ 33 mV pp (1 %)", max(r["b_rpp"], r["s_rpp"]) <= 0.033)
    t.fila("Rizado de 3V3 en el módulo (C9), buck / boost", f"{v(r['b_rpp_mod']*1e3, 1)} / {v(r['s_rpp_mod']*1e3, 1)} mV pp",
           "≤ 33 mV pp", max(r["b_rpp_mod"], r["s_rpp_mod"]) <= 0.033)

    nom, peor = leer("tps63802_placa_nominal.dat"), leer("tps63802_placa_peor.dat")
    ven = [(d, (d["time"] > 1.9e-3) & (d["time"] < 2.8e-3)) for d in (nom, peor)]
    (n, kn), (p, kp) = ven
    figura("tps63802_escalon.png", "3V3: escalón de 0,1 a 0,55 A en el módulo (batería a 3,0 V)", [
        ("3V3 en el módulo (V)", [(n["time"][kn], n["v(mod)"][kn], "nominal"),
                                  (p["time"][kp], p["v(mod)"][kp], "peor caso (C −20 %, GT/2)")],
         [(3.0, "mín. ESP32-S3 3,0 V")]),
        ("VSYS en U3 (V)", [(n["time"][kn], n["v(vsys)"][kn], "nominal")], [(2.3, "VIN;LOAD 2,3 V")]),
    ])
    rz = leer("tps63802_rizado.dat")
    rz = {c: x[rz["time"] > 1.195e-3] for c, x in rz.items()}
    figura("tps63802_rizado.png", "3V3: rizado en C7/C8 y corriente de L1 (L −20 %, 0,7 A)", [
        ("3V3 en C7/C8 (V)", [(rz["time"], rz["v(fob)"], "buck, VSYS 4,4 V"), (rz["time"], rz["v(fos)"], "boost, VSYS 3,0 V")], []),
        ("corriente de L1 (A)", [(rz["time"], rz["i(Lb)"], "buck, VSYS 4,4 V"), (rz["time"], rz["i(Ls)"], "boost, VSYS 3,0 V")], []),
    ], escala_x=1e6, etiqueta_x="tiempo (µs)")
    return t


BLOQUES = {
    "tps63802": bloque_tps63802,
}

if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(BLOQUES)
    for nombre in pedidos:
        BLOQUES[nombre]().imprimir()
