#!/usr/bin/env python3
"""Renders de la base modificada: planta y dos cortes acotados (matplotlib) y dos
vistas 3/4 (Blender, con render_blender.py).

Lee los STL que deja modificar_base.py en --salida y escribe en <salida>/render/.
Los renders muestran el diseño de terceros: se quedan fuera del repositorio.

Uso (desde Hardware/Base-furby, con el venv):
    python -I scripts/render_base.py --base-stl <STL original> --salida <carpeta>
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path as RutaMpl  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import verificar_base  # noqa: E402

BLENDER = Path("/Applications/Blender.app/Contents/MacOS/Blender")

COLOR_BASE = "#c9ccd6"
COLOR_PCB = "#2e8b57"
COLOR_USB = "#9a9a9a"
COLOR_FUNDA = "#3b3b3b"
COLOR_AVISO = "#d1495b"
COLOR_COTA = "#1f3b73"


def mm(v, decimales=2):
    return f"{v:.{decimales}f}".replace(".", ",")


def poligono_a_ruta(poligono):
    """Ruta de matplotlib con los huecos del polígono (regla par-impar)."""
    vertices, codigos = [], []
    for anillo in [poligono.exterior, *poligono.interiors]:
        xy = np.asarray(anillo.coords)
        vertices += list(xy)
        codigos += [RutaMpl.MOVETO] + [RutaMpl.LINETO] * (len(xy) - 2) + [RutaMpl.CLOSEPOLY]
    return RutaMpl(vertices, codigos)


def dibujar_poligonos(ax, poligonos, color, **kwargs):
    for p in poligonos:
        ax.add_patch(PathPatch(poligono_a_ruta(p), facecolor=color, edgecolor="#333", linewidth=0.6, **kwargs))


def cota(ax, p0, p1, texto, desplazamiento=(0, 0), color=COLOR_COTA, tam=7.5, rot=0):
    ax.annotate("", p0, p1, arrowprops={"arrowstyle": "<->", "linewidth": 0.7, "color": color,
                                        "shrinkA": 0, "shrinkB": 0})
    medio = ((p0[0] + p1[0]) / 2 + desplazamiento[0], (p0[1] + p1[1]) / 2 + desplazamiento[1])
    ax.text(*medio, texto, ha="center", va="center", fontsize=tam, color=color, rotation=rot,
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.6, "alpha": 0.85})


# -------------------------------------------------------------------- 1. planta

def dibujar_agujeros(ax, medidas, geo, tapados):
    """Agujeros originales del suelo: abiertos, o tapados (discontinuos y rotulados)."""
    muescas = comun.muescas_activas(geo)
    x_medio = np.mean([a["centro"][0] for a in medidas["agujeros"]])
    for a in medidas["agujeros"]:
        if tapados:
            ax.add_patch(Circle(a["centro"], a["d"] / 2, fill=False, edgecolor="#555", linewidth=0.8,
                                linestyle="--"))
            hacia_dentro = 1 if a["centro"][0] < x_medio else -1
            ax.text(a["centro"][0] + hacia_dentro * (a["d"] / 2 + 0.6), a["centro"][1], "tapado",
                    ha="left" if hacia_dentro > 0 else "right", va="center", fontsize=7, color="#555")
        else:
            ax.add_patch(Circle(a["centro"], a["d"] / 2, fill=False, edgecolor="#000", linewidth=0.8))
        if muescas:
            ax.add_patch(Circle(a["centro"], muescas["radio"], fill=False, edgecolor="#777",
                                linewidth=0.5, linestyle="--"))


def render_planta(ruta, base, geo, par, der, medidas, ver):
    seg = par["segmentos_circulo"]
    pcb = comun.contorno_pcb(geo, seg)
    tapados = par["tapar_agujeros_originales"]
    # Con los agujeros tapados se añade una sección por el suelo, donde se ve macizo.
    zs = ([par["verificacion"]["agujero_z"]] if tapados else []) + par["render"]["planta_z"]
    fig, ejes = plt.subplots(1, len(zs), figsize=(8.5 * len(zs), 9.6))
    for ax, z in zip(ejes, zs):
        dibujar_poligonos(ax, comun.seccion(base, z), COLOR_BASE)
        if z < geo["alturas"]["z_pcb_inf"]:
            ax.add_patch(PathPatch(poligono_a_ruta(pcb), facecolor="none", edgecolor=COLOR_PCB,
                                   linewidth=1.0, linestyle="--", label="PCB (por encima)"))
        else:
            ax.add_patch(PathPatch(poligono_a_ruta(pcb), facecolor=COLOR_PCB, alpha=0.18, edgecolor=COLOR_PCB,
                                   linewidth=1.0, label="PCB"))
        for i, t in enumerate(geo["taladros"], start=1):
            ax.add_patch(Circle(t, par["separador_d"] / 2, fill=False, edgecolor="#555", linewidth=0.6,
                                linestyle=":"))
            ax.add_patch(Circle(t, geo["taladro_diametro"] / 2, fill=False, edgecolor=COLOR_PCB, linewidth=0.8))
            ax.text(t[0], t[1] + par["separador_d"] / 2 + 1.0, f"H{i}", ha="center", fontsize=8)
        dibujar_agujeros(ax, medidas, geo, tapados)
        mec = geo["mecanismo"]
        ax.add_patch(Circle(mec["centro"], der["exclusion_d"] / 2, fill=False, edgecolor=COLOR_AVISO,
                            linewidth=0.8, linestyle="--"))
        ax.text(mec["centro"][0], mec["centro"][1] - der["exclusion_d"] / 2 - 1.2,
                f"exclusión Ø{mm(der['exclusion_d'], 1)} (supuesto)", ha="center", fontsize=7.5, color=COLOR_AVISO)
        x0, y0, x1, y1 = comun.caja_usb(geo, par)
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=COLOR_USB, alpha=0.6, edgecolor="#333",
                               linewidth=0.5))
        ax.set_aspect("equal")
        (bx0, by0, _), (bx1, by1, _) = base.bounds
        ax.set_xlim(bx0 - 3, bx1 + 3)
        ax.set_ylim(by0 - 6, by1 + 3)
        ax.set_title(f"Sección z = {mm(z, 1)}" + (" (suelo)" if z < der["z_suelo"] else ""), fontsize=11)
        ax.grid(True, linewidth=0.2)

    ax = ejes[-2]
    vx0, vx1 = der["ventana_x"]
    y_cota = medidas["pared_lobulo"][0]["y_ext"] - 3.5
    cota(ax, (vx0, y_cota), (vx1, y_cota), f"ventana {mm(vx1 - vx0, 1)}")
    sep = ver["F_medidas_salida"]["separadores"][2]
    t = geo["taladros"][2]
    cota(ax, (t[0] - sep["d"] / 2, t[1] + 5.5), (t[0] + sep["d"] / 2, t[1] + 5.5), f"Ø{mm(sep['d'])}", (0, 1.0))
    b = ver["B_interior_pcb"]
    ejes[-1].text(0.02, 0.02, f"Holgura PCB-pared mín. {mm(b['holgura_pcb_min'], 3)}\n"
                              f"Separador a agujero original mín. {mm(ver['G_exclusiones']['separador_a_agujero_min'], 1)}",
                  transform=ejes[-1].transAxes, fontsize=8.5, va="bottom",
                  bbox={"facecolor": "white", "edgecolor": "#999"})
    if tapados:
        e = ver["E_intocado"]
        ejes[0].text(0.02, 0.02, f"Agujeros originales tapados a ras: suelo macizo de z {mm(medidas['z_min'], 0)} "
                                 f"a {mm(der['z_suelo'], 3)}\n"
                                 f"Cara inferior: {mm(e['cara_inferior']['area_original'], 1)} → "
                                 f"{mm(e['cara_inferior']['area_salida'], 1)} mm² (plana en z 0)",
                     transform=ejes[0].transAxes, fontsize=8.5, va="bottom",
                     bbox={"facecolor": "white", "edgecolor": "#999"})
    agujeros = "agujeros originales tapados" if tapados else "agujeros originales"
    fig.suptitle(f"Base modificada: planta con PCB, separadores, {agujeros}, exclusión y ventana del USB-C",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# -------------------------------------------------------------------- 2. corte por el USB-C

def render_corte_usb(ruta, base, fantasma, geo, par, der, medidas, ver):
    a, u = geo["alturas"], geo["usb"]
    x = u["x"]
    fig, ax = plt.subplots(figsize=(13, 7.5))
    dibujar_poligonos(ax, comun.seccion_vertical(base, "x", x), COLOR_BASE)
    dibujar_poligonos(ax, comun.seccion_vertical(fantasma["pcb"], "x", x), COLOR_PCB, alpha=0.75)
    dibujar_poligonos(ax, comun.seccion_vertical(fantasma["usb"], "x", x), COLOR_USB, alpha=0.9)
    dibujar_poligonos(ax, comun.seccion_vertical(fantasma["funda"], "x", x), COLOR_FUNDA, alpha=0.3)

    pared = next(p for p in medidas["pared_lobulo"] if abs(p["x"] - x) < 1e-9)
    y_ext, y_int = pared["y_ext"], pared["y_int"]
    z_suelo, z_sup = der["ventana_z"]
    fondo = par["rebaje_usb_fondo"]
    z_cota = z_sup + 3.0
    cota(ax, (y_ext, z_cota), (y_int - fondo, z_cota), f"pared {mm(y_int - fondo - y_ext)}", (-0.4, 0.5))
    if fondo > 0:
        cota(ax, (y_int - fondo, z_cota + 1.6), (y_int, z_cota + 1.6), f"rebaje {mm(fondo)}", (1.2, 0.5))
        ax.plot([y_int, y_int], [z_sup - par["rebaje_usb_solape"], z_sup + 9], color=COLOR_AVISO,
                linewidth=0.7, linestyle="--")
        ax.text(y_int + 0.3, z_sup + 6.3, "cara interior\noriginal", fontsize=7, color=COLOR_AVISO, va="center")
    cota(ax, (y_ext - 0.8, z_suelo), (y_ext - 0.8, z_sup), f"ventana {mm(z_sup - z_suelo)}", (-0.7, 0), rot=90)
    f0, f1 = der["funda_z"]
    yf = u["y_boca"] - 4
    cota(ax, (yf, z_suelo), (yf, f0), f"{mm(f0 - z_suelo)}", (-0.9, 0), tam=7)
    cota(ax, (yf, f1), (yf, z_sup), f"{mm(z_sup - f1)}", (-0.9, 0), tam=7)
    cota(ax, (u["y_boca"], a["carcasa_sup"] + 0.6), (y_int, a["carcasa_sup"] + 0.6),
         f"boca a pared {mm(u['y_boca'] - y_int)}", (0, 0.5), tam=7)
    chaflan = ver["F_medidas_salida"]["chaflan_real"]
    h = ver["H_cable"]
    ax.text(0.01, 0.98,
            f"Corte por x = {mm(x, 1)}\n"
            f"Funda {mm(der['funda_ancho'], 0)} × {mm(der['funda_alto'], 1)} (supuesto): z {mm(f0, 3)} … {mm(f1, 3)}\n"
            f"Funda a la base mín. {mm(h['funda_distancia_min'], 3)} · USB-C montado a la base mín. {mm(h['usb_distancia_min'], 2)}\n"
            f"USB-C a la pared al bajar la PCB: {mm(ver['B_interior_pcb']['holgura_usb_min'], 2)} con el rebaje "
            f"({mm(ver['B_interior_pcb']['holgura_usb_min_sin_rebaje'], 2)} sin él)\n"
            f"Chaflán exterior real (x −80 / −73,5 / −67): "
            + " / ".join(mm(c, 2) for c in chaflan.values()),
            transform=ax.transAxes, va="top", fontsize=8.5, bbox={"facecolor": "white", "edgecolor": "#999"})
    ax.text(u["y_boca"] + 3.4, a["z_centro_usb"], "USB-C", ha="center", va="center", fontsize=8)
    ax.text(yf - 4, (f0 + f1) / 2, "funda del cable", ha="center", va="center", fontsize=8)
    ax.text(u["y_fondo"] + 3, a["z_pcb_sup"] + 0.4, "PCB", ha="center", fontsize=8, color=COLOR_PCB)
    ax.set_aspect("equal")
    ax.set_xlim(u["y_boca"] - 13, u["y_boca"] + 14)
    ax.set_ylim(-1.0, z_sup + 9)
    ax.set_xlabel("y (mm)  ← detrás · delante →")
    ax.set_ylabel("z (mm)")
    ax.grid(True, linewidth=0.2)
    fig.tight_layout()
    fig.savefig(ruta, dpi=160, bbox_inches="tight")
    plt.close(fig)


# -------------------------------------------------------------------- 3. corte por los separadores H3 y H4

def render_corte_separadores(ruta, base, fantasma, geo, par, der, medidas, ver):
    a = geo["alturas"]
    traseros = [t for t in geo["taladros"] if abs(t[1] - geo["taladros"][2][1]) < 1e-9]
    y = traseros[0][1]
    fig, ax = plt.subplots(figsize=(14, 4.6))
    dibujar_poligonos(ax, comun.seccion_vertical(base, "y", y), COLOR_BASE)
    dibujar_poligonos(ax, comun.seccion_vertical(fantasma["pcb"], "y", y), COLOR_PCB, alpha=0.75)

    r = par["render"]
    for t in traseros:
        # Tornillo fantasma M2 × largo: cabeza sobre la PCB, caña hacia abajo.
        z_cabeza = a["z_pcb_sup"]
        ax.add_patch(Rectangle((t[0] - r["tornillo_cabeza_d"] / 2, z_cabeza), r["tornillo_cabeza_d"],
                               r["tornillo_cabeza_alto"], facecolor="#b08d57", edgecolor="#333", linewidth=0.5))
        z_punta = z_cabeza - par["tornillo_largo"]
        ax.add_patch(Rectangle((t[0] - r["tornillo_d"] / 2, z_punta), r["tornillo_d"], par["tornillo_largo"],
                               facecolor="#b08d57", edgecolor="#333", linewidth=0.5, alpha=0.8))
        xd = t[0] + par["separador_d"] / 2 + 1.2
        cota(ax, (xd, medidas["z_min"]), (xd, der["z_piloto_fondo"]),
             f"suelo restante {mm(der['suelo_restante'], 3)}", (2.4, 0), tam=7)
        cota(ax, (xd + 4.6, der["z_piloto_fondo"]), (xd + 4.6, a["z_pcb_inf"]),
             f"piloto {mm(der['piloto_prof'], 1)}", (1.9, 0), tam=7)
        cota(ax, (t[0] - 4.2, der["z_suelo"]), (t[0] - 4.2, a["z_pcb_inf"]),
             f"separador {mm(der['separador_alto'], 2)}", (-2.4, 0), tam=7)
        ax.text(t[0], z_cabeza + r["tornillo_cabeza_alto"] + 0.5, f"M2 × {mm(par['tornillo_largo'], 0)}",
                ha="center", fontsize=8)
    ax.text(0.01, 0.98,
            f"Corte por y = {mm(y, 1)} (H3 y H4)\n"
            f"Piloto Ø{mm(par['piloto_d'], 1)} con chaflán {mm(par['piloto_chaflan'], 1)}; "
            f"aire bajo la punta {mm(par['tornillo_margen_punta'], 1)}",
            transform=ax.transAxes, va="top", fontsize=8.5, bbox={"facecolor": "white", "edgecolor": "#999"})
    xs = [t[0] for t in traseros]
    ax.set_aspect("equal")
    ax.set_xlim(min(xs) - 9, max(xs) + 12)
    ax.set_ylim(-1.0, a["z_pcb_sup"] + 3.5)
    ax.set_xlabel("x (mm)")
    ax.set_ylabel("z (mm)")
    ax.grid(True, linewidth=0.2)
    fig.tight_layout()
    fig.savefig(ruta, dpi=160, bbox_inches="tight")
    plt.close(fig)


# -------------------------------------------------------------------- 4 y 5. Blender

def render_blender(carpeta_render, base, fantasma, geo, blender):
    with tempfile.TemporaryDirectory() as tmp:
        base.export(str(Path(tmp) / "base.stl"))
        for nombre, solido in fantasma.items():
            comun.escribir_stl(solido, Path(tmp) / f"{nombre}.stl")
        script = Path(__file__).resolve().parent / "render_blender.py"
        subprocess.run([str(blender), "-b", "--factory-startup", "--python", str(script), "--",
                        "--mallas", tmp, "--salida", str(carpeta_render),
                        "--lobulo", str(geo["usb"]["x"]), str(geo["usb"]["y_boca"])],
                       check=True, stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-stl", type=Path, required=True, help="STL original de la base")
    parser.add_argument("--salida", type=Path, required=True, help="carpeta con los STL de modificar_base.py")
    parser.add_argument("--geometria", type=Path, default=comun.GEOMETRIA)
    parser.add_argument("--parametros", type=Path, default=comun.PARAMETROS)
    parser.add_argument("--blender", type=Path, default=BLENDER)
    args = parser.parse_args()

    salida_dir = comun.comprobar_salida_fuera_del_repo(args.salida)
    par, geo, _, medidas, der, _ = verificar_base.preparar(args.base_stl, args.geometria, args.parametros)
    ver = json.loads((salida_dir / comun.NOMBRE_VERIFICACION).read_text(encoding="utf-8"))["comprobaciones"]
    base = comun.leer_malla(salida_dir / comun.NOMBRE_BASE)
    fantasma = comun.pcb_fantasma(geo, par, der, partes=True)
    fantasma_mallas = {n: comun.a_trimesh(s) for n, s in fantasma.items()}

    render = salida_dir / "render"
    render.mkdir(exist_ok=True)
    render_planta(render / "planta.png", base, geo, par, der, medidas, ver)
    render_corte_usb(render / "corte-usb.png", base, fantasma_mallas, geo, par, der, medidas, ver)
    render_corte_separadores(render / "corte-separadores.png", base, fantasma_mallas, geo, par, der, medidas, ver)
    render_blender(render, base, fantasma, geo, args.blender)
    print("Renders escritos en render/")


if __name__ == "__main__":
    main()
