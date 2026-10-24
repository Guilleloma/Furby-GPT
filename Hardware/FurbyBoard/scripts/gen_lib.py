#!/usr/bin/env python3
"""Librería propia de la FurbyBoard: símbolos y huellas que no están en KiCad 10.

Símbolos (lib/FurbyBoard.kicad_sym):
- SI7615ADN: P-MOSFET de la protección de polaridad (PowerPAK 1212-8: S 1–3, G 4, D 5).
- TPS63802: buck-boost de 3,3 V (TI SLVSEU9D, tabla 7-1, encapsulado DLA).

Huellas (lib/FurbyBoard.pretty), dibujadas con las cotas de las hojas de datos y
comprobadas contra la huella de LCSC de cada número de pieza (la que usa JLCPCB):
- USB_C_HRO_TYPE-C-31-M-13C (C2848620): origen en la boca, boca hacia +Y. En el
  layout del fabricante la boca queda a ras del borde; aquí sale 0,70, así que
  el borde de la PCB queda en y = −0,70 y la ranura (Edge.Cuts del contorno)
  llega hasta y = −6,55.
- FPC_AFC01-S24FCA-00 (C262669): 24 pines a 0,5, contacto inferior; el flex
  entra por +Y.
- L_Changjiang_FHD4020S (C602026/C602028): 4 × 4 mm.
- Texas_DLA_VSON-10_2x3mm_P0.5mm (TPS63802, C2845237).
- Pads_RxC_P2.54mm: pads pasantes de Ø1,7 / taladro de 1,0 para soldar cables
  (el 1, cuadrado).
- BAT_POS_Square3x3_Drill1.2 y BAT_NEG_Round2.6_Drill1.0: pads de la batería,
  de forma distinta para no confundirlos.
- MountingHole_2.3mm_M2 y Logo_Furby_PixelArt: copias de Hardware/PCB-suelo.

Uso: python3 scripts/gen_lib.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import params as P  # noqa: E402


def f(v):
    return ("%.4f" % v).rstrip("0").rstrip(".") if v != 0 else "0"


# ------------------------------------------------------------------ símbolos

def _font(size=1.27):
    return "(effects (font (size %s %s)))" % (size, size)


def _prop(name, value, x=0.0, y=0.0, hide=False):
    h = " (hide yes)" if hide else ""
    return '(property "%s" "%s" (at %s %s 0)%s %s)' % (name, value, f(x), f(y), h, _font())


def _pin(kind, x, y, ang, name, num, length=2.54, hidden=False):
    h = " hide" if hidden else ""
    return ('(pin %s line (at %s %s %d) (length %s)%s (name "%s" %s) (number "%s" %s))'
            % (kind, f(x), f(y), ang, f(length), h, name, _font(), num, _font()))


def _symbol(name, ref, value, fp, ds, desc, box, pins, extra=""):
    x0, y0, x1, y1 = box
    out = ['(symbol "%s" (pin_names (offset 0.254)) (exclude_from_sim no) (in_bom yes) (on_board yes)' % name,
           _prop("Reference", ref, x0, y0 + 1.27), _prop("Value", value, x0, y1 - 1.27),
           _prop("Footprint", fp, 0, 0, True), _prop("Datasheet", ds, 0, 0, True),
           _prop("Description", desc, 0, 0, True),
           '(symbol "%s_0_1" (rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) '
           '(fill (type background))) %s)' % (name, f(x0), f(y0), f(x1), f(y1), extra),
           '(symbol "%s_1_1" %s)' % (name, " ".join(_pin(*p) for p in pins)), ")"]
    return " ".join(out)


def symbols():
    syms = []
    syms.append(_symbol(
        "SI7615ADN", "Q", "SI7615ADN", "Package_SO:Vishay_PowerPAK_1212-8_Single",
        "https://www.vishay.com/docs/65848/si7615adn.pdf",
        "P-MOSFET −20 V, 9,8 mΩ a −2,5 V, VGS(th) −0,4 a −1,5 V (PowerPAK 1212-8)",
        (-5.08, 5.08, 5.08, -5.08),
        [("passive", -7.62, 2.54, 0, "S", "1"), ("passive", -7.62, 0, 0, "S", "2", 2.54),
         ("passive", -7.62, -2.54, 0, "S", "3"), ("input", 0, -7.62, 90, "G", "4"),
         ("passive", 7.62, 0, 180, "D", "5")]))
    syms.append(_symbol(
        "TPS63802", "U", "TPS63802DLAR", "FurbyBoard:Texas_DLA_VSON-10_2x3mm_P0.5mm",
        "https://www.ti.com/lit/ds/symlink/tps63802.pdf",
        "Buck-boost 1,3–5,5 V, 2 A, VFB 0,5 V (VSON-10 2 × 3 mm)",
        (-7.62, 7.62, 7.62, -7.62),
        [("power_in", -10.16, 5.08, 0, "VIN", "10"), ("input", -10.16, 2.54, 0, "EN", "1"),
         ("input", -10.16, 0, 0, "MODE", "2"), ("passive", -10.16, -5.08, 0, "L1", "9"),
         ("power_out", 10.16, 5.08, 180, "VOUT", "6"), ("input", 10.16, 0, 180, "FB", "4"),
         ("open_collector", 10.16, 2.54, 180, "PG", "5"), ("passive", 10.16, -5.08, 180, "L2", "7"),
         ("power_in", -2.54, -10.16, 90, "AGND", "3"), ("power_in", 2.54, -10.16, 90, "GND", "8")]))
    return syms


def _close(text, i):
    depth, ins = 0, False
    for j in range(i, len(text)):
        c = text[j]
        if ins:
            if c == '"' and text[j - 1] != "\\":
                ins = False
            continue
        if c == '"':
            ins = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
    raise ValueError("paréntesis sin cerrar")


def copia_kicad(lib, name, tipos):
    """Copia un símbolo de KiCad cambiando el tipo eléctrico de algunos pines.

    DRV8231ADSG: el pin 8 (OUT2) viene como entrada de alimentación y es una salida.
    MAX98357A: el pad (17) viene sin especificar; es GND (pasivo) para que el ERC no avise.
    """
    import re
    text = open(os.path.join(P.KICAD_SYM_DIR, lib + ".kicad_sym"), encoding="utf-8").read()
    i = text.find('(symbol "%s"' % name)
    blk = text[i:_close(text, i) + 1]
    if "(extends" in blk:
        raise NotImplementedError(name)
    for num, tipo in tipos.items():
        for m in re.finditer(r"\(pin (\w+) ", blk):
            fin = _close(blk, m.start())
            if '(number "%s"' % num in blk[m.start():fin]:
                blk = blk[:m.start()] + "(pin %s " % tipo + blk[m.end():]
                break
        else:
            raise KeyError((name, num))
    return blk


def write_symbols():
    body = "\n".join(symbols() + [copia_kicad("Driver_Motor", "DRV8231ADSG", {"8": "output"}),
                                   copia_kicad("Audio", "MAX98357A", {"17": "passive"})])
    os.makedirs(P.LIB_DIR, exist_ok=True)
    with open(P.SYM_LIB, "w") as fh:
        fh.write('(kicad_symbol_lib (version 20241209) (generator "gen_lib") (generator_version "10.0")\n%s\n)\n'
                 % body)


# ------------------------------------------------------------------- huellas

class Fp:
    def __init__(self, name, descr, tags, attr="smd"):
        self.name = name
        self.lines = ['(footprint "%s"' % name, "\t(version 20260206)", '\t(generator "gen_lib")',
                      '\t(layer "F.Cu")', '\t(descr "%s")' % descr, '\t(tags "%s")' % tags,
                      '\t(property "Reference" "REF**" (at 0 0 0) (layer "F.SilkS") (hide yes) '
                      "(effects (font (size 0.8 0.8) (thickness 0.12))))",
                      '\t(property "Value" "%s" (at 0 0 0) (layer "F.Fab") (hide yes) '
                      "(effects (font (size 0.8 0.8) (thickness 0.12))))" % name]
        if attr:
            self.lines.append("\t(attr %s)" % attr)

    def rect(self, layer, x0, y0, x1, y1, w=0.1):
        self.lines.append("\t(fp_rect (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer \"%s\"))"
                          % (f(x0), f(y0), f(x1), f(y1), f(w), layer))

    def line(self, layer, x0, y0, x1, y1, w=0.12):
        self.lines.append("\t(fp_line (start %s %s) (end %s %s) (stroke (width %s) (type solid)) (layer \"%s\"))"
                          % (f(x0), f(y0), f(x1), f(y1), f(w), layer))

    def circle(self, layer, x, y, r, w=0.12):
        self.lines.append("\t(fp_circle (center %s %s) (end %s %s) (stroke (width %s) (type solid)) (fill no) (layer \"%s\"))"
                          % (f(x), f(y), f(x + r), f(y), f(w), layer))

    def smd(self, num, shape, x, y, w, h, extra=""):
        layers = '"F.Cu" "F.Paste" "F.Mask"'
        rr = " (roundrect_rratio 0.25)" if shape == "roundrect" else ""
        self.lines.append('\t(pad "%s" smd %s (at %s %s) (size %s %s) (layers %s)%s%s)'
                          % (num, shape, f(x), f(y), f(w), f(h), layers, rr, extra))

    def tht(self, num, shape, x, y, w, h, drill, extra=""):
        self.lines.append('\t(pad "%s" thru_hole %s (at %s %s) (size %s %s) (drill %s) (layers "*.Cu" "*.Mask")%s)'
                          % (num, shape, f(x), f(y), f(w), f(h), drill, extra))

    def text(self, layer, txt, x, y, size=0.6):
        self.lines.append('\t(fp_text user "%s" (at %s %s 0) (layer "%s") (effects (font (size %s %s) (thickness %s))))'
                          % (txt, f(x), f(y), layer, f(size), f(size), f(size * 0.15)))

    def save(self, d):
        with open(os.path.join(d, self.name + ".kicad_mod"), "w") as fh:
            fh.write("\n".join(self.lines + [")"]) + "\n")


USB_PADS = [("A1", -3.35), ("B12", -3.05), ("A4", -2.55), ("B9", -2.25), ("B8", -1.75), ("A5", -1.25),
            ("B7", -0.75), ("A6", -0.25), ("A7", 0.25), ("B6", 0.75), ("A8", 1.25), ("B5", 1.75),
            ("B4", 2.25), ("A9", 2.55), ("B1", 3.05), ("A12", 3.35)]
USB_SALIENTE = 0.70


def fp_usb(d):
    fp = Fp("USB_C_HRO_TYPE-C-31-M-13C",
            "USB-C 16P montaje medio para PCB de 1,6 mm, HRO TYPE-C-31-M-13C (LCSC C2848620). Origen en la "
            "boca, boca hacia +Y; la boca sale %s mm del borde de la PCB (y = -%s). Ranura de 9,24 x 6,55 "
            "desde la boca en Edge.Cuts del contorno" % (f(USB_SALIENTE), f(USB_SALIENTE)),
            "USB C Type-C receptacle USB2.0 16P mid-mount")
    for num, x in USB_PADS:
        fp.smd(num, "rect", x, -7.30, 0.30, 1.20)
    # Patas de la carcasa: ranuras metalizadas (traseras 0,8 x 1,6, delanteras 0,8 x 2,0)
    for x in (-5.62, 5.62):
        fp.lines.append('\t(pad "SH" thru_hole oval (at %s -6.1) (size 1.2 2.0) (drill oval 0.8 1.6) '
                        '(layers "*.Cu" "*.Mask"))' % f(x))
        fp.lines.append('\t(pad "SH" thru_hole oval (at %s -2.1) (size 1.2 2.4) (drill oval 0.8 2.0) '
                        '(layers "*.Cu" "*.Mask"))' % f(x))
    fp.rect("F.Fab", -4.47, -6.42, 4.47, 0, 0.1)
    fp.line("Dwgs.User", -6.5, -USB_SALIENTE, 6.5, -USB_SALIENTE, 0.05)
    fp.text("Dwgs.User", "borde PCB", 0, -USB_SALIENTE - 0.4, 0.4)
    fp.rect("F.CrtYd", -6.5, -8.15, 6.5, 0.25, 0.05)
    fp.save(d)


def fp_fpc(d):
    fp = Fp("FPC_AFC01-S24FCA-00",
            "FPC 24 pines a 0,5 mm, contacto inferior, tapa abatible, JUSHUO AFC01-S24FCA-00 (LCSC C262669). "
            "El flex entra por +Y",
            "FPC FFC 24P 0.5mm bottom contact")
    for i in range(24):
        fp.smd(str(i + 1), "rect", -5.75 + 0.5 * i, -1.325, 0.30, 1.30)
    for x in (-7.45, 7.45):
        fp.smd("MP", "rect", x, 1.325, 2.0, 1.6)
    fp.rect("F.Fab", -8.2, -1.0, 8.2, 4.4, 0.1)
    fp.line("F.SilkS", -8.35, 2.4, -8.35, 4.55)
    fp.line("F.SilkS", -8.35, 4.55, 8.35, 4.55)
    fp.line("F.SilkS", 8.35, 4.55, 8.35, 2.4)
    fp.circle("F.SilkS", -6.6, -1.9, 0.15, 0.3)
    fp.text("F.Fab", "flex por aquí", 0, 3.6, 0.6)
    fp.rect("F.CrtYd", -8.75, -2.25, 8.75, 4.9, 0.05)
    fp.save(d)


def fp_inductor(d):
    fp = Fp("L_Changjiang_FHD4020S", "Bobina Changjiang FHD4020S 4 x 4 x 2 mm (LCSC C602026, C602028)",
            "inductor 4020")
    for num, x in (("1", -1.6), ("2", 1.6)):
        fp.smd(num, "rect", x, 0, 1.6, 3.5)
    fp.rect("F.Fab", -2.0, -2.0, 2.0, 2.0, 0.1)
    fp.line("F.SilkS", -0.6, -2.1, 0.6, -2.1)
    fp.line("F.SilkS", -0.6, 2.1, 0.6, 2.1)
    fp.rect("F.CrtYd", -2.65, -2.25, 2.65, 2.25, 0.05)
    fp.save(d)


def fp_vson(d):
    fp = Fp("Texas_DLA_VSON-10_2x3mm_P0.5mm", "TI DLA (VSON-10, 2 x 3 mm), TPS63802 (LCSC C2845237)",
            "VSON-10 DLA TPS63802")
    for i in range(5):
        fp.smd(str(i + 1), "rect", -0.825, -1.0 + 0.5 * i, 0.60, 0.30)
    for num, y in (("10", -1.0), ("9", -0.5), ("7", 0.5), ("6", 1.0)):
        fp.smd(num, "rect", 0.825, y, 0.90, 0.30)
    fp.smd("8", "rect", 0.625, 0.0, 1.30, 0.30)
    fp.rect("F.Fab", -1.0, -1.5, 1.0, 1.5, 0.1)
    fp.circle("F.SilkS", -1.35, -1.45, 0.1, 0.2)
    fp.rect("F.CrtYd", -1.45, -1.75, 1.6, 1.75, 0.05)
    fp.save(d)


def fp_pads(d, filas, cols):
    n = filas * cols
    fp = Fp("Pads_%dx%02d_P2.54mm" % (filas, cols) if filas > 1 else "Pads_1x%02d_P2.54mm" % cols,
            "%d pads pasantes de Ø1,7 (taladro 1,0) a 2,54 para soldar cables; el 1 es cuadrado" % n,
            "pads cables THT", attr="through_hole")
    k = 1
    for r in range(filas):
        for c in range(cols):
            shape = "rect" if k == 1 else "circle"
            fp.tht(str(k), shape, c * 2.54, r * 2.54, 1.7, 1.7, 1.0)
            k += 1
    fp.rect("F.CrtYd", -1.1, -1.1, (cols - 1) * 2.54 + 1.1, (filas - 1) * 2.54 + 1.1, 0.05)
    fp.save(d)


def fp_bat(d):
    fp = Fp("BAT_POS_Square3x3_Drill1.2", "Pad BAT+ de la batería: cuadrado de 3 x 3, taladro de 1,2",
            "battery pad positive", attr="through_hole")
    fp.tht("1", "rect", 0, 0, 3.0, 3.0, 1.2)
    fp.rect("F.CrtYd", -1.75, -1.75, 1.75, 1.75, 0.05)
    fp.save(d)
    fp = Fp("BAT_NEG_Round2.6_Drill1.0", "Pad BAT- de la batería: redondo de Ø2,6, taladro de 1,0",
            "battery pad negative", attr="through_hole")
    fp.tht("1", "circle", 0, 0, 2.6, 2.6, 1.0)
    fp.circle("F.CrtYd", 0, 0, 1.55, 0.05)
    fp.save(d)


def write_footprints():
    d = P.FP_LIB
    os.makedirs(d, exist_ok=True)
    fp_usb(d)
    fp_fpc(d)
    fp_inductor(d)
    fp_vson(d)
    for filas, cols in ((1, 2), (1, 5), (1, 6), (1, 10), (2, 2), (2, 3), (2, 5)):
        fp_pads(d, filas, cols)
    fp_bat(d)
    shutil.copy(P.TALADRO_FP_SRC, os.path.join(d, "MountingHole_2.3mm_M2.kicad_mod"))
    shutil.copy(P.LOGO_FP_SRC, os.path.join(d, "Logo_Furby_PixelArt.kicad_mod"))


def write_tables():
    """Tablas del proyecto: la propia más las de KiCad que se usan (las globales de este Mac están vacías)."""
    import design as D
    sym_libs = sorted(({p["lib_id"].split(":")[0] for p in D.parts()} | {"power"}) - {"FurbyBoard"})
    fp_libs = sorted({p["footprint"].split(":")[0] for p in D.parts()} - {"FurbyBoard"})
    with open(os.path.join(P.ROOT, "sym-lib-table"), "w") as fh:
        fh.write('(sym_lib_table\n\t(version 7)\n'
                 '\t(lib (name "FurbyBoard") (type "KiCad") (uri "${KIPRJMOD}/lib/FurbyBoard.kicad_sym") (options "") '
                 '(descr "Símbolos propios de la FurbyBoard"))\n')
        for lib in sym_libs:
            fh.write('\t(lib (name "%s") (type "KiCad") (uri "${KICAD10_SYMBOL_DIR}/%s.kicad_sym") (options "") '
                     '(descr ""))\n' % (lib, lib))
        fh.write(")\n")
    with open(os.path.join(P.ROOT, "fp-lib-table"), "w") as fh:
        fh.write('(fp_lib_table\n\t(version 7)\n'
                 '\t(lib (name "FurbyBoard") (type "KiCad") (uri "${KIPRJMOD}/lib/FurbyBoard.pretty") (options "") '
                 '(descr "Huellas propias de la FurbyBoard"))\n')
        for lib in fp_libs:
            fh.write('\t(lib (name "%s") (type "KiCad") (uri "${KICAD10_FOOTPRINT_DIR}/%s.pretty") (options "") '
                     '(descr ""))\n' % (lib, lib))
        fh.write(")\n")


def main():
    write_symbols()
    write_footprints()
    write_tables()
    print("Librería escrita en", os.path.relpath(P.LIB_DIR, P.ROOT))


if __name__ == "__main__":
    main()
