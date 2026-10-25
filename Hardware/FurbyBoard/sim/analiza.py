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
        for j, (valor, texto) in enumerate(limites):
            # rótulos alternados a derecha e izquierda para que no se pisen límites cercanos
            eje.axhline(valor, color=TINTA_SUAVE, lw=1, ls="--")
            eje.annotate(texto, xy=(1 - j % 2, valor), xycoords=("axes fraction", "data"),
                         xytext=(-4 if j % 2 == 0 else 4, 3), textcoords="offset points",
                         ha="right" if j % 2 == 0 else "left", va="bottom", fontsize=8, color=TINTA_SUAVE)
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


def tramo_mas_largo(t, condicion):
    """Duración del tramo continuo más largo en que se cumple la condición (s)."""
    mejor, inicio = 0.0, None
    for ti, c in zip(t, condicion):
        if c and inicio is None:
            inicio = ti
        elif not c and inicio is not None:
            mejor, inicio = max(mejor, ti - inicio), None
    if inicio is not None:
        mejor = max(mejor, t[-1] - inicio)
    return mejor


def bloque_bq24073():
    t = Tabla("BQ24073 (power path)")
    m = correr("bq24073_powerpath.cir")
    casos = {}
    rfet = {"bq_a_typ": 0.05}
    for nombre in ("bq_a_typ", "bq_a_max", "bq_b_max", "bq_c_tsup5", "bq_c_tsup50", "bq_d"):
        d = leer(nombre + ".dat")
        d["dif"] = d["v(bat)"] - d["v(vsysu)"]
        # pérdidas de U2: LDO de entrada + BAT-FET en supplement (I² · RFET)
        d["pbq"] = ((d["v(vbus)"] - d["v(vsysu)"]) * d["v(xu2.ic)"]
                    + np.clip(d["dif"], 0, None) ** 2 / rfet.get(nombre, 0.1))
        casos[nombre] = d

    def sc2(d, desde, hasta):
        k = (d["time"] > desde) & (d["time"] < hasta)
        return (d["dif"][k].max(), tramo_mas_largo(d["time"][k], d["dif"][k] > 0.2),
                d["dif"][np.argmin(abs(d["time"] - 20e-3))])

    for nombre, texto, ilim in (("bq_a_typ", "USB500, BAT-FET típ. (50 mΩ)", "0,475 A"),
                                ("bq_a_max", "USB500, BAT-FET máx. (100 mΩ)", "0,475 A"),
                                ("bq_b_max", "modo ILIM, BAT-FET máx. (100 mΩ)", "1,25 A")):
        pico, dur, regimen = sc2(casos[nombre], 4e-3, 30e-3)
        t.fila(f"Pico de 2,9 A con USB ({texto}): VBAT − VSYS en régimen", f"{v(regimen*1e3, 0)} mV "
               f"(> 200 mV durante {v(dur*1e6, 0)} µs seguidos)",
               "< 200 mV (VO(SC2) mín.) o > 200 mV menos de 250 µs", regimen < 0.2 or dur < 250e-6)
    t.fila("VSYS mín. en supplement (USB500, BAT-FET máx.)", f"{v(m['a2_vsysmin'])} V", "≥ 2,5 V", m["a2_vsysmin"] >= 2.5)
    t.fila("3V3 mín. durante el pico", f"{v(min(m['a_v3min'], m['a2_v3min']))} V", "≥ 3,0 V",
           min(m["a_v3min"], m["a2_v3min"]) >= 3.0)
    for nombre, tsup, clave in (("bq_c_tsup5", "5 µs", "c"), ("bq_c_tsup50", "50 µs", "c2")):
        d = casos[nombre]
        k = (d["time"] > 9.9e-3) & (d["time"] < 12e-3)
        t.fila(f"Desenchufe con 1,15 A (batería 3,4 V), retardo de supplement {tsup}",
               f"VSYS {v(m['c_vsyspre'])} → mín. {v(m[clave + '_vsysmin'])} V; VBAT − VSYS máx. "
               f"{v(d['dif'][k].max()*1e3, 0)} mV durante {v(tramo_mas_largo(d['time'][k], d['dif'][k] > 0.2)*1e6, 0)} µs",
               "VSYS ≥ 2,5 V; sin VO(SC2) (≥ 250 µs)",
               m[clave + "_vsysmin"] >= 2.5 and tramo_mas_largo(d["time"][k], d["dif"][k] > 0.2) < 250e-6)
    t.fila("Enchufe en caliente (cable 1 m, 1 µH): pico de VBUS", f"{v(m['d_vbusmax'])} V",
           "< 6,4 V (OVP mín.) y < 28 V (máx. absoluto)", m["d_vbusmax"] < 6.4)
    d = casos["bq_d"]
    pmax = d["pbq"][d["time"] > 15e-3].max()
    t.fila("Enchufe con 5 W de carga (modo ILIM): VSYS final y disipación de U2",
           f"VSYS se queda en {v(m['d_vsysfin'])} V (supplement); U2 disipa {v(pmax)} W → Tj ≈ {v(50 + pmax*44.5, 0)} °C",
           "Tj ≤ 110 °C con Ta 50 °C (θJA 44,5 °C/W)", 50 + pmax * 44.5 <= 110)
    pa = casos["bq_a_max"]["pbq"][casos["bq_a_max"]["time"] > 15e-3].max()
    t.fila("Disipación de U2 durante el pico en USB500 (LDO + BAT-FET, 20 ms)",
           f"{v(pa)} W (en régimen daría Tj ≈ {v(50 + pa*44.5, 0)} °C)",
           "Informativo: es un pulso; el firmware no debe sostenerlo (bloqueo ≤ 150 ms)", None)

    a, b = ({c: x[d["time"] > 2e-3] for c, x in d.items()} for d in (casos["bq_a_typ"], casos["bq_a_max"]))
    figura("bq24073_supplement.png", "BQ24073: pico de 2,9 A con USB en USB500 (supplement mode)", [
        ("VSYS (V)", [(a["time"], a["v(vsys)"], "BAT-FET típ. 50 mΩ"), (b["time"], b["v(vsys)"], "BAT-FET máx. 100 mΩ")], []),
        ("VBAT − VSYS (V)", [(a["time"], a["dif"], "BAT-FET típ. 50 mΩ"), (b["time"], b["dif"], "BAT-FET máx. 100 mΩ")],
         [(0.2, "VO(SC2) mín. 200 mV"), (0.3, "VO(SC2) máx. 300 mV")]),
    ])
    c5, c50 = casos["bq_c_tsup5"], casos["bq_c_tsup50"]
    k5, k50 = (c5["time"] > 9.8e-3) & (c5["time"] < 10.6e-3), (c50["time"] > 9.8e-3) & (c50["time"] < 10.6e-3)
    figura("bq24073_desenchufe.png", "BQ24073: desenchufe del USB con 1,15 A de carga (batería 3,4 V)", [
        ("VSYS (V)", [(c5["time"][k5], c5["v(vsys)"][k5], "supplement en 5 µs"),
                      (c50["time"][k50], c50["v(vsys)"][k50], "supplement en 50 µs")], [(2.5, "2,5 V")]),
        ("VBUS (V)", [(c5["time"][k5], c5["v(vbus)"][k5], "VBUS")], []),
    ])
    d = {c: x[d["time"] > 2e-3] for c, x in d.items()}
    figura("bq24073_enchufe.png", "BQ24073: enchufe en caliente con 5 W de carga (modo ILIM, batería 3,4 V)", [
        ("VBUS (V)", [(d["time"], d["v(vbus)"], "VBUS")], [(6.4, "OVP mín. 6,4 V")]),
        ("VSYS (V)", [(d["time"], d["v(vsys)"], "VSYS")], [(4.4, "VO(REG) 4,4 V")]),
        ("potencia en U2 (W)", [(d["time"], d["pbq"], "U2")], []),
    ])
    return t


BLOQUES = {
    "tps63802": bloque_tps63802,
    "bq24073": bloque_bq24073,
}

if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(BLOQUES)
    for nombre in pedidos:
        BLOQUES[nombre]().imprimir()
