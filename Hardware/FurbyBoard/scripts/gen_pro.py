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


def netclass(name, track, clearance=P.RULE_CLEARANCE, diff_w=0.2, diff_gap=0.25, prio=0):
    return {"name": name, "clearance": clearance, "track_width": track,
            "via_diameter": P.RULE_VIA_DIAM, "via_drill": P.RULE_VIA_DRILL,
            "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "diff_pair_width": diff_w, "diff_pair_gap": diff_gap, "diff_pair_via_gap": 0.25,
            "bus_width": 12, "wire_width": 6, "line_style": 0, "priority": prio,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}


POWER_NETS = ["VBUS_IN", "VBUS", "VSYS", "BAT", "BAT_PAD", "V6", "BST_SW", "BB_L1", "BB_L2",
              "SPK_P", "SPK_N", "IR_LED_A", "IR_LED_K"]
MOTOR_NETS = ["MOT_OUT1", "MOT_OUT2"]


def project():
    rules = {
        "min_clearance": P.RULE_CLEARANCE, "min_connection": 0.0,
        "min_copper_edge_clearance": P.RULE_EDGE_CLEARANCE, "min_hole_clearance": 0.2,
        "min_hole_to_hole": 0.25, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
        "min_resolved_spokes": 1, "min_silk_clearance": 0.1, "min_text_height": 0.8,
        "min_text_thickness": 0.15, "min_through_hole_diameter": P.RULE_VIA_DRILL,
        "min_track_width": P.RULE_TRACK_MIN, "min_via_annular_width": 0.13, "min_via_diameter": 0.5,
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
               netclass("USB", P.USB_DIFF_W, diff_w=P.USB_DIFF_W, diff_gap=P.USB_DIFF_GAP, prio=2),
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
DRU = """(version 1)

(rule "USB-C de montaje medio: pads junto a la ranura"
\t(condition "A.memberOfFootprint('J1')")
\t(constraint edge_clearance (min 0.12mm)))
"""


def main():
    with open(P.PRO, "w") as fh:
        json.dump(project(), fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.splitext(P.PRO)[0] + ".kicad_dru", "w") as fh:
        fh.write(DRU)
    print("Proyecto escrito:", os.path.basename(P.PRO))


if __name__ == "__main__":
    main()
