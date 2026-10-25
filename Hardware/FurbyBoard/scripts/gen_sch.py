#!/usr/bin/env python3
"""Genera el esquemático jerárquico de la FurbyBoard a partir de design.py.

- FurbyBoard.kicad_sch: hoja raíz con un bloque por hoja.
- hojas/<hoja>.kicad_sch: una hoja por bloque (USB, alimentación, MCU, motor,
  audio, cámara, sensores, LED y TP).

Cada pin lleva un tramo de cable y una etiqueta con su red: local si la red
solo está en esa hoja y global si cruza hojas. Así el esquemático se regenera
entero desde design.py y los enlaces con el PCB (UUID deterministas) no cambian.

Uso: python3 scripts/gen_sch.py   (después: kicad-cli sch erc)
"""
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402
import params as P  # noqa: E402

ROOT_UUID = "8b4f1e2a-3c5d-4e6f-9a1b-2c3d4e5f6a7b"
NS = uuid.UUID("5a7e0c3e-9f2b-4b1d-8c6a-1f0e2d3c4b5a")
GRID = 2.54

NOTAS = {
    "usb": ["USB-C 16 pines HRO TYPE-C-31-M-13C (C2848620): D+/D− al USB nativo del ESP32-S3 (GPIO19/20).",
            "Rd de 5,1 kΩ en CC1 y CC2: cualquier fuente USB-C da 5 V. ESD USBLC6-2SC6 junto al conector.",
            "PTC de 1,5 A antes del cargador."],
    "alimentacion": ["BQ24073: ICHG = 890/1,8k = 0,494 A; ILIM 1610/1,2k = 1,34 A con EN2=1 y EN1=0.",
                     "Al arrancar EN1=1, EN2=0: USB500 (475 mA). OUT = 4,4 V con USB y VBAT − 50 mV sin USB.",
                     "Q1 SI7615ADN: protección de polaridad con la puerta a GND. Con la batería al revés no llega",
                     "tensión negativa a nada; con USB, el BQ se queda en detección de cortocircuito (4–11 mA).",
                     "TPS63802: 3,3 V = 0,5 × (1 + 510k/91k). LED CHG y PG desde VBUS: no gastan batería."],
    "mcu": ["ESP32-S3-WROOM-1-N16R8: GPIO35–37 ocupados por la PSRAM octal.",
            "Strapping: GPIO0 (BOOT, 10 kΩ a 3V3), GPIO45 y GPIO46 a 0 al arrancar (pull-downs en sus hojas),",
            "GPIO3 (JTAG) ignorado sin eFuse. EN con 10 kΩ y 1 µF. LED PROG en U0TXD (log del ROM)."],
    "motor": ["TPS61089: 5,94 V = 1,212 × (1 + 390k/100k); ILIM 3,8 A; fSW ≈ 0,96 MHz; EN desde el expansor.",
              "DRV8231A: ITRIP = VREF / (1,5k × 1500 µA/A) = 1,0 A con VREF = 2,245 V (R26 ajustable).",
              "PWM a 20 kHz en IN1/IN2 (el DRV se duerme si IN1 = IN2 = 0 más de 0,8 ms).",
              "JP1–JP3: cortar para liberar GPIO9, GPIO46 y GPIO3."],
    "audio": ["MAX98357A en VSYS, GAIN_SLOT a VDD (6 dB), altavoz de 4 Ω y 3 W: 0,9–1,9 W según VSYS.",
              "VDD: C26 (100 nF) y C41 (10 µF) junto a los pines 7/8; C24/C25 (22 µF) al otro lado del puente de VSYS.",
              "I2S full duplex a 16 kHz: BCLK y WS compartidos con el micro ICS-43434 (placa aparte, pads J5)."],
    "camara": ["FPC 24p 0,5 con el pinout de facto de los módulos OV2640/OV3660/OV5640 para ESP32 (verificar).",
               "AVDD 2,8 V (U8) y DVDD 1,2 V (U9; 1,5 V con ME6211C15 para OV3660/OV5640), EN desde el expansor.",
               "DOVDD = 3V3 siempre: el SCCB comparte el I2C del expansor. PWDN a 1 al arrancar."],
    "sensores": ["TCA9535 en 0x20, mismo I2C que el SCCB de la cámara; INT a GPIO6 (despierta del sueño).",
                 "Pull-ups: barriga, espalda y lengua 47 kΩ; inclinación 220 kΩ; leva 100 kΩ; 1 kΩ en serie.",
                 "Encoder: LED IR desde V6 por 470 Ω (luce con EN_6V) y fototransistor al Schmitt; JP4 libera GPIO8.",
                 "IR: emisor con AO3400A en GPIO45 (pull-down por el strapping); receptor alimentado por P17."],
    "led_tp": ["LED PWR (JP5 para apagarlo), LED RUN en P03 del expansor.",
               "J_EXP: 2 × 5 sin montar: 1 GND, 2 3V3, 3 VSYS, 4 VBUS, 5 P04, 6 SCL, 7 U0TX, 8 GND, 9 SDA, 10 U0RX."],
}


def suuid(*key):
    return str(uuid.uuid5(NS, "/".join(key)))


def sheet_uuid(name):
    return suuid("sheet", name)


def fnum(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


def _close(s, i):
    depth, ins = 0, False
    for j in range(i, len(s)):
        c = s[j]
        if ins:
            if c == "\\":
                continue
            if c == '"' and s[j - 1] != "\\":
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


def _block(text, name):
    i = text.find('(symbol "%s"' % name)
    if i < 0:
        raise KeyError(name)
    return text[i:_close(text, i) + 1]


_cache = {}


def lib_symbol(lib_id):
    """Bloque lib_symbols del símbolo (con «extends» resuelto) y posición de sus pines."""
    if lib_id in _cache:
        return _cache[lib_id]
    lib, name = lib_id.split(":")
    path = P.SYM_LIB if lib == "FurbyBoard" else os.path.join(P.KICAD_SYM_DIR, lib + ".kicad_sym")
    text = open(path, encoding="utf-8").read()
    blk = _block(text, name)
    m = re.search(r'\(extends "([^"]+)"\)', blk)
    if m:
        parent = _block(text, m.group(1))
        props = re.findall(r'\(property "[^"]+".*?\)\s*\)\s*\)', blk, re.S)
        body = parent.replace('(symbol "%s"' % m.group(1), '(symbol "%s"' % name, 1)
        body = re.sub(r'\(symbol "%s_' % re.escape(m.group(1)), '(symbol "%s_' % name, body)
        for pr in re.findall(r'\(property "([^"]+)" "([^"]*)"', blk):
            body = re.sub(r'(\(property "%s" )"[^"]*"' % re.escape(pr[0]), lambda mm: mm.group(1) + '"%s"' % pr[1], body, count=1)
        blk = body
        del props
    blk = blk.replace('(symbol "%s"' % name, '(symbol "%s"' % lib_id, 1)
    pins = {}
    for mm in re.finditer(r'\(pin (\w+) (\w+)\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)', blk):
        tail = blk[mm.end():_close(blk, mm.start()) + 1]
        num = re.search(r'\(number "([^"]*)"', tail).group(1)
        pins.setdefault(num, []).append((float(mm.group(3)), float(mm.group(4)), int(mm.group(5))))
    _cache[lib_id] = (blk, pins)
    return _cache[lib_id]


def pin_names(lib_id):
    """Nombre de cada pin (para las redes «unconnected-(...)» que KiCad crea en los pines sin conectar)."""
    blk, _ = lib_symbol(lib_id)
    out = {}
    for mm in re.finditer(r'\(pin (\w+) (\w+)', blk):
        tail = blk[mm.start():_close(blk, mm.start()) + 1]
        name = re.search(r'\(name "([^"]*)"', tail).group(1)
        num = re.search(r'\(number "([^"]*)"', tail).group(1)
        out[num] = name
    return out


def bbox(pins):
    xs = [x for v in pins.values() for x, _, _ in v] or [0]
    ys = [y for v in pins.values() for _, y, _ in v] or [0]
    return min(xs), max(xs), min(ys), max(ys)


class Sheet:
    def __init__(self, name, title, path_uuid, file_uuid):
        self.name, self.title = name, title
        self.path = path_uuid
        self.file_uuid = file_uuid
        self.items, self.libs = [], {}
        self.n = 0

    def _uid(self, kind):
        self.n += 1
        return suuid(self.name, kind, str(self.n))

    def wire(self, x1, y1, x2, y2):
        self.items.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid "%s"))'
                          % (fnum(x1), fnum(y1), fnum(x2), fnum(y2), self._uid("w")))

    def label(self, net, x, y, ang, glob):
        just = "right" if ang in (180, 270) else "left"
        if glob:
            self.items.append('(global_label "%s" (shape passive) (at %s %s %d) (fields_autoplaced yes) '
                              '(effects (font (size 1.27 1.27)) (justify %s)) (uuid "%s") '
                              '(property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) '
                              '(effects (font (size 1.27 1.27)) (hide yes))))'
                              % (net, fnum(x), fnum(y), ang, just, self._uid("g"), fnum(x), fnum(y)))
        else:
            self.items.append('(label "%s" (at %s %s %d) (effects (font (size 1.27 1.27)) (justify %s bottom)) '
                              '(uuid "%s"))' % (net, fnum(x), fnum(y), ang, just, self._uid("l")))

    def noconn(self, x, y):
        self.items.append('(no_connect (at %s %s) (uuid "%s"))' % (fnum(x), fnum(y), self._uid("nc")))

    def text(self, txt, x, y, size=1.5):
        txt = txt.replace('"', "'")
        self.items.append('(text "%s" (exclude_from_sim no) (at %s %s 0) (effects (font (size %s %s)) '
                          '(justify left top)) (uuid "%s"))' % (txt, fnum(x), fnum(y), size, size, self._uid("t")))

    def symbol(self, part, x, y, globales, stub=2.54):
        blk, pins = lib_symbol(part["lib_id"])
        self.libs[part["lib_id"]] = blk
        ref = part["ref"]
        x0, x1, y0, y1 = bbox(pins)
        props = [("Reference", ref, x + x1 + 1.5, y - y1 - 1.0, False),
                 ("Value", part["value"], x + x1 + 1.5, y - y1 + 1.0, False),
                 ("Footprint", part["footprint"], x, y, True),
                 ("Datasheet", "~", x, y, True),
                 ("Description", part.get("desc", ""), x, y, True),
                 ("LCSC", part.get("lcsc", ""), x, y, True),
                 ("JLC_Class", part.get("jlc", ""), x, y, True),
                 ("MPN", part.get("mpn", ""), x, y, True)]
        ptxt = " ".join('(property "%s" "%s" (at %s %s 0)%s (effects (font (size 1.27 1.27)) (justify left)))'
                        % (n, v.replace('"', "'"), fnum(px), fnum(py), " (hide yes)" if h else "")
                        for n, v, px, py, h in props)
        pin_txt = " ".join('(pin "%s" (uuid "%s"))' % (n, suuid("pin", ref, n)) for n in sorted(pins))
        self.items.append(
            '(symbol (lib_id "%s") (at %s %s 0) (unit 1) (exclude_from_sim no) (in_bom %s) (on_board yes) '
            '(dnp %s) (uuid "%s") %s %s (instances (project "%s" (path "/%s/%s" (reference "%s") (unit 1)))))'
            % (part["lib_id"], fnum(x), fnum(y), "yes" if part["in_bom"] else "no",
               "yes" if part.get("dnp") else "no", suuid("sym", ref), ptxt, pin_txt,
               P.PROJECT_NAME, ROOT_UUID, self.path, ref))
        for num, locs in pins.items():
            net = part["pins"].get(num, "")
            for px, py, ang in locs:
                cx, cy = x + px, y - py
                if not net:
                    self.noconn(cx, cy)
                    continue
                dx, dy = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[ang]
                ex, ey = cx + dx * stub, cy + dy * stub
                self.wire(cx, cy, ex, ey)
                lang = {(-1, 0): 180, (1, 0): 0, (0, 1): 270, (0, -1): 90}[(dx, dy)]
                self.label(net, ex, ey, lang, net in globales)

    def pwr_flag(self, net, x, y, globales):
        self.symbol(dict(ref="#FLG_%s" % net, lib_id="power:PWR_FLAG", value="PWR_FLAG", footprint="",
                         pins={"1": net}, in_bom=False, desc=""), x, y, globales)

    def render(self, root=False, extra=""):
        libs = "\n".join(self.libs.values())
        tb = ('(title_block (title "FurbyBoard %s · %s") (date "2026-10-24") (rev "%s") '
              '(company "FurbyGPT") (comment 1 "Generado por scripts/gen_sch.py desde scripts/design.py: '
              'no editar a mano"))' % (P.BOARD_REV, self.title, P.BOARD_REV))
        tail = '(sheet_instances (path "/" (page "1")))' if root else ""
        return ('(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") '
                '(uuid "%s") (paper "A3") %s\n(lib_symbols\n%s\n)\n%s\n%s\n%s (embedded_fonts no))\n'
                % (self.file_uuid, tb, libs, "\n".join(self.items), extra, tail))


def layout_sheet(sh, parts, globales):
    """Coloca los símbolos en filas, de mayor a menor, con sitio para las etiquetas."""
    def size(p):
        x0, x1, y0, y1 = bbox(lib_symbol(p["lib_id"])[1])
        return x1 - x0, y1 - y0
    orden = sorted(parts, key=lambda p: -(size(p)[0] * size(p)[1]))
    x, y, fila_alto = 30.0, 60.0, 0.0
    for p in orden:
        w, h = size(p)
        ancho = w + 40.0
        if x + ancho > 400:
            x, y, fila_alto = 30.0, y + fila_alto + 22.0, 0.0
        x0, x1, y0, y1 = bbox(lib_symbol(p["lib_id"])[1])
        cx = round((x - x0 + 18.0) / GRID) * GRID
        cy = round((y + y1 + 5.0) / GRID) * GRID
        sh.symbol(p, cx, cy, globales)
        x += ancho
        fila_alto = max(fila_alto, h + 10.0)


def build():
    parts = D.parts()
    net_sheets = D.net_sheets()
    # Todas globales: así el nombre de red del esquemático coincide con el del PCB.
    globales = set(net_sheets)
    os.makedirs(P.SHEETS_DIR, exist_ok=True)
    root = Sheet("root", "Raíz", ROOT_UUID, ROOT_UUID)
    sheet_syms = []
    for page, (name, title) in enumerate(D.SHEETS, start=2):
        su = sheet_uuid(name)
        sh = Sheet(name, title, su, suuid("file", name))
        sh.text(title.upper(), 20, 20, 3.0)
        for i, linea in enumerate(NOTAS.get(name, [])):
            sh.text(linea, 20, 30 + i * 4.0, 1.8)
        layout_sheet(sh, [p for p in parts if p["sheet"] == name], globales)
        if name == "alimentacion":
            for k, net in enumerate(("VBUS", "GND")):
                sh.pwr_flag(net, 381.0 + k * 12.7, 25.4, globales)
        if name == "usb":
            sh.pwr_flag("VBUS_IN", 381.0, 25.4, globales)
        with open(os.path.join(P.SHEETS_DIR, name + ".kicad_sch"), "w", encoding="utf-8") as fh:
            fh.write(sh.render())
        col, row = (page - 2) % 4, (page - 2) // 4
        sx, sy = 25.4 + col * 95.25, 60.96 + row * 63.5
        sheet_syms.append(
            '(sheet (at %s %s) (size 76.2 38.1) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
            '(fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) '
            '(uuid "%s") (property "Sheetname" "%s" (at %s %s 0) (effects (font (size 2 2)) (justify left bottom))) '
            '(property "Sheetfile" "hojas/%s.kicad_sch" (at %s %s 0) (effects (font (size 1.27 1.27)) '
            '(justify left top))) (instances (project "%s" (path "/%s" (page "%d")))))'
            % (fnum(sx), fnum(sy), su, title, fnum(sx), fnum(sy - 0.7), name, fnum(sx), fnum(sy + 38.8),
               P.PROJECT_NAME, ROOT_UUID, page))
    root.text("FURBYBOARD %s · %s" % (P.BOARD_REV, P.BOARD_DATE), 25.4, 25.4, 4.0)
    root.text("ESP32-S3-WROOM-1-N16R8 · BQ24073 · TPS63802 · TPS61089 + DRV8231A · MAX98357A · cámara DVP · "
              "TCA9535. Arquitectura: ../PCB-suelo/ARQUITECTURA.md", 25.4, 36.0, 2.0)
    with open(P.SCH, "w", encoding="utf-8") as fh:
        fh.write(root.render(root=True, extra="\n".join(sheet_syms)))
    print("Esquemático escrito: %d hojas, %d piezas, %d redes (%d globales)"
          % (len(D.SHEETS), len(parts), len(D.nets()), len(globales)))


if __name__ == "__main__":
    build()
