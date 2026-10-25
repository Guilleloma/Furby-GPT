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


def figura(fichero, titulo, paneles, escala_x=1e3, etiqueta_x="tiempo (ms)", log_x=False):
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
    if log_x:
        ejes[-1, 0].set_xscale("log")
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


def bloque_bateria():
    t = Tabla("Batería y Q1 (SI7615ADN)")
    m = correr("bateria_q1.cir")
    for clave, vth in (("q_vds", "1,5"), ("q2_vds", "0,4")):
        vsd = -m[clave]
        p = vsd * 2.9
        t.fila(f"Q1 con 2,9 A, batería 3,0 V, VGS(th) −{vth} V", f"{v(vsd*1e3, 0)} mV, {v(p*1e3, 0)} mW → Tj ≈ {v(50 + p*81, 0)} °C",
               "Tj ≤ 110 °C (Ta 50 °C, 81 °C/W)", 50 + p * 81 <= 110)
    t.fila("Batería al revés sin USB: nodo BAT y divisor del ADC", f"BAT {v(m['r_vbat']*1e6, 1)} µV; VBAT_SNS {v(m['r_vsns']*1e6, 2)} µV; "
           f"fuga {v(abs(m['r_ileak'])*1e9, 1)} nA (modelo; IDSS ≤ 1 µA)", "≥ −0,3 V (máximo absoluto de BAT)", m["r_vbat"] >= -0.3)
    pu = m["u_vds"] * m["u_id"]
    t.fila("Batería al revés con USB, esquina mala (VGS(th) −1,5 V, IBAT 11 mA, VBAT(SC) 1,6 V)",
           f"BAT sube a {v(m['u_vbat'])} V > VBAT(SC): precarga de {v(m['u_id']*1e3, 0)} mA; Q1 disipa {v(pu)} W → Tj ≈ {v(50 + pu*81, 0)} °C",
           "Q1 ≤ 0,5 W y ningún nodo negativo", pu <= 0.5 and m["u_vbat"] >= -0.3)
    t.fila("Batería al revés con USB, esquina buena (−0,4 V, 4 mA, 2,0 V)",
           f"BAT {v(m['u2_vbat'])} V, {v(m['u2_id']*1e3, 0)} mA (se queda en detección de cortocircuito)", "Q1 ≤ 0,5 W", True)
    t.fila("Conexión de la batería (4,2 V) con la placa descargada",
           f"pico de {v(-m['c_ipk'], 1)} A; > 10 A durante {v((m['c_t10']-m['c_t10a'])*1e6, 0)} µs",
           "Q1: < IDM 80 A (300 µs); la PCM de la celda (desconocida) se comprueba al soldarla", -m["c_ipk"] < 80)

    a, b = leer("q1_reves_usb_mala.dat"), leer("q1_reves_usb_buena.dat")
    figura("q1_reves_con_usb.png", "Batería al revés con USB: nodo BAT del BQ24073", [
        ("nodo BAT (V)", [(a["time"], a["v(bat)"], "esquina mala: VGS(th) −1,5 V, 11 mA"),
                          (b["time"], b["v(bat)"], "esquina buena: VGS(th) −0,4 V, 4 mA")],
         [(1.6, "VBAT(SC) mín. 1,6 V"), (2.0, "VBAT(SC) máx. 2,0 V")]),
    ])
    c = leer("q1_conexion.dat")
    k = c["time"] > 0.49e-3
    figura("q1_conexion.png", "Conexión de la batería a 4,2 V con la placa descargada", [
        ("corriente de la batería (A)", [(c["time"][k], -c["i(v.xb.v1)"][k], "batería")], []),
        ("tensión (V)", [(c["time"][k], c["v(bat)"][k], "BAT"), (c["time"][k], c["v(vsys)"][k], "VSYS")], []),
    ], escala_x=1e6, etiqueta_x="tiempo (µs)")
    return t


def recorte(d, desde, hasta):
    k = (d["time"] >= desde) & (d["time"] <= hasta)
    return {c: x[k] for c, x in d.items()}


def bloque_drv8231a():
    t = Tabla("DRV8231A y motor")
    m = correr("drv8231a_motor.cir")
    # ITRIP con tolerancias: 3V3 ±2 %, R26/R27/R28 1 %, AERR ±6 % (garantizado solo con VM >= 6,5 V)
    vref = 3.302 * 10 / 14.7
    i_max = vref * 1.02 * (10.1 / (10.1 + 4.653)) / (10 / 14.7) / (1500e-6 * 0.94 * 1.5e3 * 0.99)
    i_min = vref * 0.98 * (9.9 / (9.9 + 4.747)) / (10 / 14.7) / (1500e-6 * 1.06 * 1.5e3 * 1.01)
    t.fila("ITRIP con las tolerancias (cálculo)", f"{v(i_min)}–{v(i_max)} A (nominal {v(vref/2.25)} A)",
           "Informativo: AERR (±6 %) solo está garantizado con VM ≥ 6,5 V y V6 es 5,94 V; se mide", None)
    t.fila("Arranque al 100 % desde parado: pico del motor", f"{v(m['s_ipk'])} A", "≤ ITRIP + 10 % y < 3,7 A (OCP)",
           m["s_ipk"] <= 1.1)
    t.fila("Arranque: V6 y VSYS mínimos (batería 3,7 V)", f"V6 {v(m['s_v6min'])} V; VSYS {v(m['s_vsysmin'])} V",
           "V6 > 4,45 V (UVLO del DRV8231A); VSYS > 2,7 V (UVLO del TPS61089)",
           m["s_v6min"] > 4.45 and m["s_vsysmin"] > 2.7)
    t.fila("Bloqueado al 100 %: corriente regulada (media / pico / valle)",
           f"{v(m['b_iavg'])} / {v(m['b_ipk'])} / {v(m['b_imin'])} A", "pico ≤ ITRIP + 10 %", m["b_ipk"] <= 1.1)
    t.fila("Bloqueado: IPROPI en el pico frente a VREF", f"{v(m['b_vip'], 3)} V frente a {v(m['b_vref'], 3)} V",
           "≤ 3,0 V (rango de AERR) y ≤ 3,1 V (ADC del ESP32-S3 a 12 dB)", m["b_vip"] <= 3.0)
    p = m["b_irms"] ** 2 * 0.9
    t.fila("Bloqueado: disipación del DRV8231A (RDS(on) 0,45 Ω por lado en caliente)",
           f"{v(p)} W → Tj ≈ {v(50 + p*66.5, 0)} °C (θJA 66,5 °C/W del DSG)", "Tj ≤ 110 °C con Ta 50 °C", 50 + p * 66.5 <= 110)
    t.fila("Bloqueado: rizado y mínimo de V6", f"{v(m['b_v6pp']*1e3, 0)} mV pp; mín. {v(m['b_v6min'])} V",
           "V6 > 4,45 V", m["b_v6min"] > 4.45)
    t.fila("PWM 20 kHz al 70 % (decaimiento lento) a 700 rad/s: corriente y rizado",
           f"{v(m['p_iavg'])} A medios, {v(m['p_ipp']*1e3, 0)} mA pp; V6 {v(m['p_v6pp']*1e3, 0)} mV pp",
           "Informativo (motor estimado)", None)
    t.fila("Inversión a toda velocidad sin freno: pico", f"{v(abs(m['i_ipk']))} A; V6 {v(m['i_v6min'])}–{v(m['i_v6max'])} V",
           "< 3,7 A (OCP) y V6 < 6,5 V", abs(m["i_ipk"]) < 3.7 and m["i_v6max"] < 6.5)

    a = leer("drv_arranque.dat")
    figura("drv_arranque.png", "Motor: arranque al 100 % desde parado (motor estimado de 5 Ω, 0,5 mH)", [
        ("corriente del motor (A)", [(a["time"], a["i(Vm)"], "motor")], [(1.0, "ITRIP 1,0 A")]),
        ("tensión (V)", [(a["time"], a["v(v6)"], "V6"), (a["time"], a["v(vsys)"], "VSYS")], [(4.45, "UVLO DRV8231A 4,45 V")]),
    ])
    b = recorte(leer("drv_bloqueo.dat"), 3.0e-3, 3.4e-3)
    figura("drv_bloqueo.png", "Motor bloqueado: regulación de corriente con tOFF de 25 µs", [
        ("corriente del motor (A)", [(b["time"], b["i(Vm)"], "motor")], [(1.0, "ITRIP 1,0 A")]),
        ("IPROPI y VREF (V)", [(b["time"], b["v(ipropi)"], "IPROPI"), (b["time"], b["v(vref)"], "VREF")], []),
        ("V6 (V)", [(b["time"], b["v(v6)"], "V6")], []),
    ], escala_x=1e6, etiqueta_x="tiempo (µs)")
    i = recorte(leer("drv_inversion.dat"), 1.9e-3, 3.5e-3)
    figura("drv_inversion.png", "Motor: inversión a toda velocidad sin freno", [
        ("corriente del motor (A)", [(i["time"], i["i(Vm)"], "motor")], [(-1.0, "−ITRIP")]),
        ("V6 (V)", [(i["time"], i["v(v6)"], "V6")], []),
    ])
    return t


def bloque_max98357():
    t = Tabla("MAX98357A sobre VSYS")
    m = correr("max98357_vsys.cir")
    t.fila("Potencia en el altavoz (tono de 1 kHz, m = 0,9, VSYS ≈ 3,6 V)",
           f"{v(m['a_ispkrms']**2*4)} W; {v(m['a_ispk'])} A de pico en 4 Ω", "Informativo", None)
    t.fila("Corriente por el puente de B.Cu (media / pico)", f"{v(m['a_ipuavg'])} / {v(m['a_ipu'])} A",
           "≤ 0,7 A por vía en continua (2 vías por extremo: 1,4 A)", m["a_ipuavg"] <= 1.4)
    t.fila("VDD en los pines 7/8 (puente de 3 nH, C41 a 1,25 nH): mínimo", f"{v(m['a_vddmin'])} V", "≥ 2,5 V",
           m["a_vddmin"] >= 2.5)
    t.fila("Rizado de conmutación en los pines 7/8 con C41: nominal (3 nH, 1,25 nH) / peor caso (5 nH, 2 nH)",
           f"{v(m['a_vddpp_pico']*1e3, 0)} / {v(m['c_vddpp_pico']*1e3, 0)} mV pp", "≤ 200 mV pp (rizado de la prueba de PSRR)",
           max(m["a_vddpp_pico"], m["c_vddpp_pico"]) <= 0.2)
    t.fila("Diseño anterior al bloque F (sin C41, solo C26 junto a los pines)",
           f"{v(m['d_vddpp_pico']*1e3, 0)} mV pp; mín. {v(m['d_vddmin'])} V", "≤ 200 mV pp (informativo: ya no aplica)", None)
    t.fila("Rizado en los pines con los 22 µF pegados (referencia sin puente)", f"{v(m['b_vddpp_pico']*1e3, 0)} mV pp",
           "≤ 200 mV pp", m["b_vddpp_pico"] <= 0.2)
    t.fila("VSYS en el relleno de In2 (lo que ve U3)", f"mín. {v(m['a_plmin'])} V", "≥ 2,3 V (VIN;LOAD del TPS63802)",
           m["a_plmin"] >= 2.3)
    a, b, d = leer("max_puente.dat"), leer("max_directo.dat"), leer("max_sin_c41.dat")
    z = [recorte(x, 0.2495e-3, 0.2535e-3) for x in (a, b, d)]
    figura("max98357_vdd.png", "MAX98357A: VDD en los pines 7/8 en la cresta del tono (20 MHz)", [
        ("VDD en los pines (V)", [(z[2]["time"], z[2]["v(vddf)"], "sin C41 (antes del bloque F)"),
                                  (z[0]["time"], z[0]["v(vddf)"], "con C41 (placa actual)"),
                                  (z[1]["time"], z[1]["v(vddf)"], "22 µF pegados (referencia)")], []),
    ], escala_x=1e6, etiqueta_x="tiempo (µs)")
    figura("max98357_vsys.png", "MAX98357A: VSYS en el relleno de In2 durante un periodo del tono", [
        ("VSYS en In2 (V)", [(a["time"], a["v(pla)"], "VSYS")], []),
        ("corriente del puente (A)", [(a["time"], a["i(Lpu)"], "puente")], []),
    ])
    return t


def bloque_ldo():
    t = Tabla("LDO de la cámara (ME6211)")
    m = correr("ldo_camara.cir")
    p = correr("ldo_camara_psrr.cir")
    a = leer("ldo_arranque.dat")
    k = (a["time"] > 2e-3) & (a["time"] < 2.2e-3)
    dvdd_sobre = (a["v(dvdd)"][k] - a["v(cam28)"][k]).max()
    t.fila("Arranque con CAM_EN: subida de AVDD (10 → 90 %)", f"{v((m['a_t28']-m['a_t28i'])*1e6, 0)} µs; "
           f"sobreimpulso {v((m['a_v28max']-2.8)*1e3, 1)} mV", "Monótona, sin sobreimpulso > 5 %", m["a_v28max"] <= 2.94)
    t.fila("Orden de arranque: DVDD frente a AVDD", f"DVDD − AVDD máx. {v(dvdd_sobre*1e3, 0)} mV (U9 cuelga de AVDD)",
           "DVDD nunca por encima de AVDD", dvdd_sobre <= 0)
    t.fila("Pico de corriente de 3V3 al encender la cámara y caída de 3V3", f"{v(m['a_i8pk']*1e3, 0)} mA; 3V3 mín. {v(m['a_v3min'])} V",
           "3V3 ≥ 3,0 V", m["a_v3min"] >= 3.0)
    t.fila("AVDD y DVDD en régimen (20 y 80 mA)", f"{v(m['a_v28'], 3)} V y {v(m['a_v12'], 3)} V",
           "2,8 V ± 5 % y 1,2 V ± 5 %", abs(m["a_v28"] - 2.8) <= 0.14 and abs(m["a_v12"] - 1.2) <= 0.06)
    t.fila("PSRR de U8 a 1 kHz / 10 kHz / 20 kHz / 1,6 MHz", f"{v(-p['p_1k'], 0)} / {v(-p['p_10k'], 0)} / {v(-p['p_20k'], 0)} / "
           f"{v(-p['p_1m6'], 0)} dB", "Ajuste a la hoja: 70 dB a 1 kHz y 62 dB a 10 kHz", abs(p["p_1k"] + 70) < 1.5 and abs(p["p_10k"] + 62) < 1.5)
    t.fila("Rizado de AVDD / DVDD con 46 mV pp en 3V3 (PWM 1,6 MHz + PFM 20 kHz)",
           f"{v(m['r_28']*1e3, 2)} / {v(m['r_12']*1e3, 2)} mV pp", "AVDD ≤ 10 mV pp", m["r_28"] <= 0.01)
    p8, p9 = (m["a_v3"] - m["a_v28"]) * 0.1, (m["a_v28"] - m["a_v12"]) * 0.08
    t.fila("Disipación de U8 / U9 (SOT-23-5, 250 °C/W)", f"{v(p8*1e3, 0)} / {v(p9*1e3, 0)} mW → Tj ≈ {v(50 + p8*250, 0)} / {v(50 + p9*250, 0)} °C",
           "Tj ≤ 110 °C con Ta 50 °C", 50 + max(p8, p9) * 250 <= 110)
    z = recorte(a, 1.99e-3, 2.12e-3)
    figura("ldo_arranque.png", "Cámara: arranque de AVDD (U8) y DVDD (U9) con CAM_EN", [
        ("tensión (V)", [(z["time"], z["v(n3v3)"], "3V3"), (z["time"], z["v(cam28)"], "CAM_2V8 (AVDD)"),
                         (z["time"], z["v(dvdd)"], "CAM_DVDD")], []),
    ], escala_x=1e6, etiqueta_x="tiempo (µs)")
    q = leer("ldo_psrr.dat")
    figura("ldo_psrr.png", "Cámara: rechazo del rizado de 3V3 (modelo ajustado a la hoja del ME6211)", [
        ("V(salida)/V(3V3) (dB)", [(q["frequency"], q["p28"], "CAM_2V8 (U8)"), (q["frequency"], q["p12"], "CAM_DVDD (U8 + U9)")],
         [(-70, "hoja: −70 dB a 1 kHz"), (-62, "hoja: −62 dB a 10 kHz")]),
    ], escala_x=1, etiqueta_x="frecuencia (Hz)", log_x=True)
    return t


def bloque_ntc():
    t = Tabla("NTC en TS (RT1)")
    m = correr("ntc_ts.cir")
    t.fila("Ventana de carga nominal (INTC 75 µA, VHOT 0,30 V, VCOLD 2,10 V)", f"{v(m['n_cold'], 1)} a {v(m['n_hot'], 1)} °C",
           "0–51 °C (la del encargo y la tabla 9-3 de TI: 28 kΩ y 4 kΩ)", -1 <= m["n_cold"] <= 1 and 50 <= m["n_hot"] <= 52)
    t.fila("Ventana más ancha con tolerancias (INTC, VHOT/VCOLD, R25 ± 1 %, B ± 1 %)", f"{v(m['w_cold'], 1)} a {v(m['w_hot'], 1)} °C",
           "Informativo: lo que puede llegar a cargar una placa concreta", None)
    t.fila("Ventana más estrecha con tolerancias", f"{v(m['s_cold'], 1)} a {v(m['s_hot'], 1)} °C",
           "Informativo", None)
    t.fila("Reanudación de la carga (histéresis, nominal)", f"por debajo de {v(m['h_hot'], 1)} °C y por encima de {v(m['h_cold'], 1)} °C",
           "Informativo", None)
    t.fila("Frente a la ventana de carga típica de una LiPo (0–45 °C)", f"carga hasta {v(m['n_hot'], 0)} °C (nominal) y {v(m['w_hot'], 0)} °C (peor caso)",
           "≤ 45 °C si la hoja de la celda lo pide (pendiente: celda sin hoja)", None)
    a, b = leer("ntc_nominal.dat"), leer("ntc_ancha.dat")
    x = [c for c in a if c != "v(ts)"][0]
    figura("ntc_ts.png", "TS del BQ24073 con el NTC NCP18XH103 (75 µA de polarización)", [
        ("V(TS) (V)", [(a[x], a["v(ts)"], "nominal"), (b[x], b["v(ts)"], "INTC 78 µA, R25 +1 %, B −1 %")],
         [(2.1, "VCOLD 2,1 V"), (0.3, "VHOT 0,3 V")]),
    ], escala_x=1, etiqueta_x="temperatura del NTC (°C)")
    return t


def bloque_senales():
    t = Tabla("Señales")
    m = correr("senales_i2c_led_ir.cir")
    cb_sda = 150.5 * 0.09 + 4 * 0.4 + 2 + 9.5 + 10 + 5
    t.fila(f"I2C: subida de SDA / SCL (4,7 kΩ, Cb ≈ {v(cb_sda, 0)} pF con las pistas reales)",
           f"{v(m['sda_tr']*1e9, 0)} / {v(m['scl_tr']*1e9, 0)} ns (30–70 %)", "≤ 300 ns (400 kHz) y ≤ 1000 ns (100 kHz)",
           max(m["sda_tr"], m["scl_tr"]) <= 300e-9)
    t.fila("I2C: VOL con el ESP32 tirando a GND", f"{v(m['sda_vol']*1e3, 0)} mV", "≤ 0,4 V", m["sda_vol"] <= 0.4)
    for clave, texto, diseño in (("i_d1", "D1 CHG (rojo, VBUS, 2,2 kΩ)", 1.4), ("i_d2", "D2 PG (verde, VBUS, 2,2 kΩ)", 1.4),
                                 ("i_d3", "D3 PROG (rojo, 3V3, 1,5 kΩ)", 1.0)):
        t.fila(f"LED {texto}", f"{v(m[clave]*1e3, 2)} mA", f"≥ 0,3 mA (diseño ≈ {v(diseño, 1)} mA)", m[clave] >= 0.3e-3)
    for clave, texto in (("i_d4", "D4 PWR (verde, 3V3, 1 kΩ)"), ("i_d5", "D5 RUN (verde, 3V3, 1 kΩ)")):
        lo, hi = m[clave + "t"], m[clave + "b"]
        t.fila(f"LED {texto}, VF 3,1 / 2,6 V a 5 mA", f"{v(lo*1e3, 2)}–{v(hi*1e3, 2)} mA",
               "≥ 0,3 mA (diseño: 0,5–0,9 mA)", lo >= 0.3e-3)
    p_pico = m["ir_ih"] ** 2 * 22
    t.fila("IR: corriente del LED con VSYS 4,4 / 3,0 V", f"{v(m['ir_ih']*1e3, 0)} / {v(m['ir_il']*1e3, 0)} mA (VF {v(m['ir_vf'])} V)",
           "Informativo (≈ 100 mA de diseño)", None)
    t.fila("IR: potencia de R54 (0805, 0,125 W) con VSYS 4,4 V", f"pico {v(p_pico, 2)} W; portadora continua {v(p_pico*0.33*1e3, 0)} mW; "
           f"trama NEC {v(p_pico*0.33*0.41*1e3, 0)} mW", "≤ 62 mW (50 %) de media en una trama", p_pico * 0.33 * 0.41 <= 0.0625)

    n = correr("senales_sensores_adc.cir")
    t.fila("Barriga/espalda/lengua: rebote al pulsar (47 kΩ, 1 kΩ, 100 nF)", f"máx. {v(n['t_vmax'], 2)} V entre el primer contacto y el fin del rebote",
           "< VIH 2,31 V (no hay flanco falso)", n["t_vmax"] < 2.31)
    t.fila("Barriga: respuesta al soltar (cruce de VIH)", f"{v((n['t_rel']-0.02)*1e3, 1)} ms", "< 50 ms", n["t_rel"] - 0.02 < 0.05)
    t.fila("Inclinación (220 kΩ, 100 nF): rebote y respuesta al soltar", f"máx. {v(n['ti_vmax'], 2)} V; {v((n['ti_rel']-0.02)*1e3, 1)} ms",
           "< 2,31 V y < 50 ms", n["ti_vmax"] < 2.31 and n["ti_rel"] - 0.02 < 0.05)
    t.fila("Leva HOME al ESP32 (100 kΩ, 1 kΩ, 10 nF): rebote y respuesta al soltar",
           f"máx. {v(n['h_vmax'], 2)} V; {v((n['h_rel']-0.02)*1e3, 1)} ms", "< VIH 2,48 V y < 50 ms", n["h_vmax"] < 2.475 and n["h_rel"] - 0.02 < 0.05)
    t.fila("Encoder ENC_PT (10 kΩ, 50 pF): subida 10–90 %", f"{v(n['e_tr']*1e6, 2)} µs", "≪ medio periodo del encoder (informativo)", None)
    fuga = 50e-9 * 235e3
    for clave, fs in (("a_fin", "1 kHz"), ("a10_fin", "10 kHz"), ("a100_fin", "100 kHz")):
        err = 2.1 - n[clave] - fuga
        t.fila(f"VBAT_SNS: error de muestreo con el ADC a {fs} (Cs 10 pF supuesto)", f"{v(err*1e3, 1)} mV ({v(err/2.1*100, 2)} %)",
               "≤ 0,5 % de la lectura", err / 2.1 <= 0.005)
    t.fila("VBAT_SNS: desplazamiento por la fuga del pin (50 nA máx.)", f"{v(fuga*1e3, 1)} mV ({v(fuga/2.1*100, 2)} %)",
           "Informativo: fijo, se corrige con la calibración de TEST-PLAN §9", None)
    t.fila("LIGHT (LDR 10 kΩ–1 MΩ con 470 kΩ y 100 nF): constante de tiempo", "1 ms (luz) a 32 ms (oscuridad)",
           "Informativo: el firmware espera ≥ 5 τ tras un cambio", None)

    d = leer("sensores.dat")
    z = recorte(d, 0, 50e-3)
    figura("sensores_rc.png", "Sensores: pulsación con rebote a 1 ms y suelta a 20 ms", [
        ("tensión en el chip (V)", [(z["time"], z["v(tummy)"], "barriga (47 kΩ, 100 nF)"), (z["time"], z["v(tilt)"], "inclinación (220 kΩ, 100 nF)"),
                                    (z["time"], z["v(home)"], "leva HOME (100 kΩ, 10 nF)")],
         [(2.31, "VIH TCA9535 2,31 V"), (0.99, "VIL TCA9535 0,99 V")]),
    ])
    a1, a100 = leer("adc_fs1k.dat"), leer("adc_fs100k.dat")
    figura("adc_vbat_sns.png", "VBAT_SNS (batería 4,2 V): lectura frente a la frecuencia de muestreo", [
        ("VBAT_SNS (V)", [(a1["time"], a1["v(sns)"], "ADC a 1 kHz"), (a100["time"], a100["v(sns)"], "ADC a 100 kHz")],
         [(2.1, "valor ideal 2,1 V")]),
    ])
    return t


def bloque_arranque():
    t = Tabla("Arranque y caída de batería")
    m = correr("arranque_brownout.cir")
    t.fila("Arranque con batería a 3,0 V y 0,37 Ω: 3V3 llega a 3,0 V", f"a {v(m['a_t3']*1e3, 2)} ms; sobreimpulso a {v(m['a_v3max'], 2)} V",
           "≤ 3,6 V (máx. del ESP32-S3)", m["a_v3max"] <= 3.6)
    t.fila("VSYS mínimo durante el arranque suave de U3", f"{v(m['a_vsysmin'])} V", "> 1,25 V (UVLO de U3 bajando)", m["a_vsysmin"] > 1.25)
    t.fila("EN del ESP32 (10 kΩ, 1 µF) cruza 0,75 · 3V3", f"a {v(m['a_ten']*1e3, 1)} ms: {v((m['a_ten']-m['a_t3'])*1e3, 1)} ms después de 3V3 ≥ 3,0 V",
           "≥ 50 µs (tSTBL)", m["a_ten"] - m["a_t3"] >= 50e-6)
    t.fila("3V3 durante la calibración del WiFi (0,4 A, 5 ms) con la batería a 3,0 V", f"mín. {v(m['a_v3wifi'])} V", "≥ 3,0 V",
           m["a_v3wifi"] >= 3.0)
    for clave, rb in (("b", "0,21 Ω (nominal)"), ("c", "0,37 Ω (peor caso)")):
        voc = 4.2 - (m[clave + "_tcae"] - 10e-3) * 10
        t.fila(f"Pico de 10,2 W (motor bloqueado + TX + audio) con {rb}: batería mínima",
               f"VSYS cae por debajo de 2,5 V con la batería a {v(voc)} V (cálculo: {v(2.5 + float(rb.split()[0].replace(',', '.'))*10.2/2.5)} V)",
               "≤ 3,0 V para sostener el pico en todo el rango de la batería", voc <= 3.0)
    t.fila("3V3 mientras el elevador entra y sale por UVLO", f"mín. {v(min(m['b_v3min'], m['c_v3min']))} V", "≥ 3,0 V (el ESP32 no se reinicia)",
           min(m["b_v3min"], m["c_v3min"]) >= 3.0)
    a = recorte(leer("arranque.dat"), 0, 20e-3)
    figura("arranque.png", "Arranque al conectar la batería (3,0 V, 0,37 Ω): VSYS, 3V3 y EN", [
        ("tensión (V)", [(a["time"], a["v(vsys)"], "VSYS"), (a["time"], a["v(v3)"], "3V3"), (a["time"], a["v(en)"], "EN")],
         [(2.475, "0,75 · 3,3 V")]),
    ])
    n, p = (recorte(leer(f), 10e-3, 1) for f in ("caida_nominal.dat", "caida_peor.dat"))
    figura("caida_bateria.png", "Pico de 10,2 W con la batería bajando de 4,2 a 2,8 V", [
        ("VSYS (V)", [(n["v(bat)"], n["v(vsys)"], "0,21 Ω (nominal)"), (p["v(bat)"], p["v(vsys)"], "0,37 Ω (peor caso)")],
         [(2.5, "UVLO del TPS61089 2,5 V")]),
        ("elevador encendido (1 = sí; entre 0 y 1: ciclos de UVLO)", [(n["v(bat)"], n["v(onq)"], "0,21 Ω (nominal)"), (p["v(bat)"], p["v(onq)"], "0,37 Ω (peor caso)")], []),
    ], escala_x=1, etiqueta_x="tensión en vacío de la batería (V); 3V3 se mantiene en 3,27 V en todo el barrido")
    return t


def bloque_elevador():
    t = Tabla("Elevador de 6 V (TPS61089)")
    m = correr("elevador_6v.cir")
    t.fila("Corriente de pico en la bobina (Vin 3,0 V, 1,0 A, L −20 %)", f"{v(m['ipk'])} A", "< ILIM 3,8 A con margen ≥ 20 %", m["ipk"] < 3.8 / 1.2)
    t.fila("Rizado de salida", f"{v((m['vmax']-m['vmin'])*1e3, 0)} mV pp", "< 59 mV (1 %)", m["vmax"] - m["vmin"] < 0.059)
    return t


BLOQUES = {
    "elevador": bloque_elevador,
    "tps63802": bloque_tps63802,
    "bq24073": bloque_bq24073,
    "bateria": bloque_bateria,
    "drv8231a": bloque_drv8231a,
    "max98357": bloque_max98357,
    "ldo": bloque_ldo,
    "ntc": bloque_ntc,
    "senales": bloque_senales,
    "arranque": bloque_arranque,
}

if __name__ == "__main__":
    pedidos = sys.argv[1:] or list(BLOQUES)
    for nombre in pedidos:
        BLOQUES[nombre]().imprimir()
