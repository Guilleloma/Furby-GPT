#!/usr/bin/env python3
"""Escribe FurbyBoard.kicad_pro con las reglas de JLCPCB, las clases de red y las hojas.

KiCad completa al abrir el proyecto las claves que faltan con sus valores por
defecto; aquí solo se fijan reglas, severidades, clases de red y hojas.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402
import gen_sch  # noqa: E402
import params as P  # noqa: E402


def netclass(name, track, clearance=P.RULE_CLEARANCE, diff_w=0.2, diff_gap=0.25, prio=0,
             via=(P.RULE_VIA_DIAM, P.RULE_VIA_DRILL)):
    return {"name": name, "clearance": clearance, "track_width": track,
            "via_diameter": via[0], "via_drill": via[1],
            "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "diff_pair_width": diff_w, "diff_pair_gap": diff_gap, "diff_pair_via_gap": 0.25,
            "bus_width": 12, "wire_width": 6, "line_style": 0, "priority": prio,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}


POWER_NETS = ["VBUS_IN", "VBUS", "VSYS", "BAT", "BAT_PAD", "V6", "BST_SW", "BB_SW1", "BB_SW2",
              "SPK_P", "SPK_N", "IR_LED_A", "IR_LED_K"]
MOTOR_NETS = ["MOT_OUT1", "MOT_OUT2"]

# Ancho mínimo de pista por red de potencia (tabla de raíles de NOTAS.md). Va al DRC como
# regla del .kicad_dru y a pcb-toolkit.toml como [rutado.anchos_minimos]: doble barrera.
# Dentro del patio de los CI con pines de 0,5 mm de paso (y en los pads de 0,3 del USB-C)
# se admite un cuello de ≤ 1 mm (layout-pcb.md, sección 5.1); el ancho del cuello es
# la última regla, que es la que manda en KiCad.
ANCHOS_MINIMOS = P.ANCHOS_MINIMOS
CUELLOS = {"U2": 0.25, "U3": 0.25, "U5": 0.25, "U6": 0.25, "U7": 0.25, "Q1": 0.5, "J1": 0.2}


def project():
    rules = {
        "min_clearance": P.RULE_CLEARANCE, "min_connection": 0.0,
        "min_copper_edge_clearance": P.RULE_EDGE_CLEARANCE, "min_hole_clearance": 0.2,
        "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
        "min_resolved_spokes": 1, "min_silk_clearance": 0.1, "min_text_height": 0.8,
        "min_text_thickness": 0.15, "min_through_hole_diameter": P.VIA_FINA_DRILL,
        "min_track_width": P.RULE_TRACK_MIN, "min_via_annular_width": P.VIA_FINA_ANILLO,
        "min_via_diameter": P.VIA_FINA_DIAM,
        "solder_mask_to_copper_clearance": 0.0, "use_height_for_length_calcs": True,
    }
    severities = {
        "courtyards_overlap": "error", "missing_courtyard": "error", "malformed_courtyard": "error",
        "silk_overlap": "error", "silk_over_copper": "error", "silk_edge_clearance": "error",
        "lib_footprint_mismatch": "ignore", "lib_footprint_issues": "ignore",
    }
    pads_sin_bom = [p["ref"] for p in D.parts() if not p["in_bom"]]
    del pads_sin_bom
    classes = [netclass("Default", P.TRACK_SIGNAL, prio=2147483647),
               netclass("Potencia", P.TRACK_POWER, prio=1),
               netclass("Motor", P.TRACK_MOTOR, prio=0),
               netclass("USB", P.USB_DIFF_W, diff_w=P.USB_DIFF_W, diff_gap=P.USB_DIFF_GAP, prio=2,
                        via=(P.VIA_FINA_DIAM, P.VIA_FINA_DRILL)),
               netclass("3V3", P.TRACK_3V3, prio=3)]
    patterns = ([{"netclass": "Potencia", "pattern": n} for n in POWER_NETS + ["GND"]]
                + [{"netclass": "Motor", "pattern": n} for n in MOTOR_NETS]
                + [{"netclass": "USB", "pattern": n} for n in ("USB_DP", "USB_DN")]
                + [{"netclass": "3V3", "pattern": "3V3"}])
    sheets = [[gen_sch.ROOT_UUID, "Root"]] + [[gen_sch.sheet_uuid(n), t] for n, t in D.SHEETS]
    return {
        "board": {
            "design_settings": {
                "meta": {"version": 2}, "rules": rules, "rule_severities": severities,
                "track_widths": [0.0, 0.2, 0.28, 0.3, 0.5, 0.8, 1.0],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": P.VIA_FINA_DIAM, "drill": P.VIA_FINA_DRILL},
                                   {"diameter": P.RULE_VIA_DIAM, "drill": P.RULE_VIA_DRILL},
                                   {"diameter": 0.8, "drill": 0.4}],
                "diff_pair_dimensions": [{"width": P.USB_DIFF_W, "gap": P.USB_DIFF_GAP, "via_gap": 0.25}],
                "drc_exclusions": [],
            },
        },
        "erc": {"rule_severities": {"lib_symbol_issues": "error", "lib_symbol_mismatch": "error"}},
        "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": P.PROJECT_NAME + ".kicad_pro", "version": 3},
        "net_settings": {"classes": classes, "meta": {"version": 4}, "net_colors": None,
                         "netclass_assignments": None, "netclass_patterns": patterns},
        "sheets": sheets,
        "text_variables": {"REV": P.BOARD_REV},
    }


# El layout del fabricante del USB-C de montaje medio deja los pads de señal a 0,15 del fondo
# de la ranura (y A1/B12 a 0,14 del alivio de la esquina): es la única excepción al margen de
# 0,3 a borde y se limita a los pads de J1.
DRU_CABECERA = """(version 1)

# El layout del fabricante del USB-C de montaje medio deja los pads de señal a 0,15 del fondo
# de la ranura (y A1/B12 a 0,14 del alivio de la esquina): única excepción al margen de 0,3 a
# borde, limitada a los pads de J1.
(rule "USB-C de montaje medio: pads junto a la ranura"
\t(condition "A.memberOfFootprint('J1')")
\t(constraint edge_clearance (min 0.12mm)))

# Vías de 0,45/0,2 (estándar de JLCPCB en 4 capas) solo en el par USB: el cruce de D+/D- en el
# receptáculo de 16 pines (B7 A6 A7 B6) no cabe con vías de 0,6 entre pads a 0,5 de paso.
# El resto de la placa sigue con 0,6/0,3.
(rule "vias de 0,6 salvo el par USB"
\t(condition "A.Type == 'Via' && A.NetClass != 'USB'")
\t(constraint via_diameter (min 0.6mm))
\t(constraint hole_size (min 0.3mm)))
"""


def dru():
    """Reglas a medida: borde del USB-C, tamaño de vía y ancho mínimo por red de potencia."""
    out = [DRU_CABECERA, "# Anchos mínimos por red (tabla de raíles de NOTAS.md); también en pcb-toolkit.toml.\n"]
    for net, w in ANCHOS_MINIMOS.items():
        out.append('(rule "ancho %s"\n\t(condition "A.NetName == \'%s\'")\n\t(constraint track_width (min %smm)))\n'
                   % (net, net, w))
    cond = " || ".join("A.intersectsCourtyard('%s')" % ref for ref in CUELLOS)
    out.append("# Cuellos de entrada a pads finos (<= 1 mm, layout-pcb.md 5.1): la última regla manda.\n")
    for ref, w in CUELLOS.items():
        out.append('(rule "cuello %s"\n\t(condition "A.intersectsCourtyard(\'%s\')")\n'
                   '\t(constraint track_width (min %smm)))\n' % (ref, ref, w))
    del cond
    return "\n".join(out)


def main():
    with open(P.PRO, "w") as fh:
        json.dump(project(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.splitext(P.PRO)[0] + ".kicad_dru", "w") as fh:
        fh.write(dru())
    print("Proyecto escrito:", os.path.basename(P.PRO))


if __name__ == "__main__":
    main()
