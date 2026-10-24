"""Parámetros comunes de la FurbyBoard (rutas, reglas de JLCPCB y capas).

La geometría mecánica (contorno, taladros, mecanismo, USB-C) no está aquí: se
lee de Hardware/PCB-suelo/geometria.json, que es el contrato con la base.
"""
import os

PROJECT_NAME = "FurbyBoard"
BOARD_REV = "v1.0"
BOARD_DATE = "2026-10"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIB_DIR = os.path.join(ROOT, "lib")
SYM_LIB = os.path.join(LIB_DIR, "FurbyBoard.kicad_sym")
FP_LIB = os.path.join(LIB_DIR, "FurbyBoard.pretty")
SHEETS_DIR = os.path.join(ROOT, "hojas")
SCH = os.path.join(ROOT, PROJECT_NAME + ".kicad_sch")
PCB = os.path.join(ROOT, PROJECT_NAME + ".kicad_pcb")
PRO = os.path.join(ROOT, PROJECT_NAME + ".kicad_pro")

PCB_SUELO = os.path.abspath(os.path.join(ROOT, "..", "PCB-suelo"))
GEOMETRIA = os.path.join(PCB_SUELO, "geometria.json")
LOGO_FP_SRC = os.path.join(PCB_SUELO, "kicad", "Furby.pretty", "Logo_Furby_PixelArt.kicad_mod")
TALADRO_FP_SRC = os.path.join(PCB_SUELO, "kicad", "Furby.pretty", "MountingHole_2.3mm_M2.kicad_mod")

KICAD_SYM_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
KICAD_FP_DIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

# Coordenadas: el STL usa y hacia delante; KiCad, y hacia abajo.
# x_kicad = x + STL_OX, y_kicad = STL_OY - y (igual que FurbyGPT-suelo).
STL_OX = 220.0
STL_OY = -40.0

# Placa: 4 capas, 1,6 mm, apilado JLC04161H-7628 de JLCPCB
# (L1 señal, L2 plano de GND, L3 plano de VSYS, L4 señal + GND).
COPPER_LAYERS = 4
BOARD_THICKNESS = 1.6

# Reglas (JLCPCB, 4 capas): pista/espacio mínimos 0,09/0,09; se usa margen.
RULE_CLEARANCE = 0.15
RULE_TRACK_MIN = 0.15
RULE_VIA_DIAM = 0.6
RULE_VIA_DRILL = 0.3
# Vía fina (0,45/0,2, anillo 0,125): dentro del estándar de JLCPCB para 4 capas
# (taladro >= 0,15, diámetro >= taladro + 0,1; 0,2 de taladro preferido, sin sobrecoste según
# fabricante-jlcpcb.md). Solo la clase USB la usa (cruce del par en J1); regla en el .kicad_dru.
VIA_FINA_DIAM = 0.45
VIA_FINA_DRILL = 0.2
VIA_FINA_ANILLO = 0.12
RULE_EDGE_CLEARANCE = 0.3
TRACK_SIGNAL = 0.2
# VSYS va por el plano de In2 (L3) y GND por el de In1 (L2): por pistas solo quedan tramos
# cortos de potencia. Se autorrutan a 0,4, el máximo que entra en los pads de 0,5 de paso de
# los QFN sin invadir el margen del pad vecino, y luego ensanchar_potencia.py los lleva a
# TRACK_POWER_MAX donde cabe. 0,4 en cara exterior de 1 oz aguanta ≈ 1,3 A con 10 °C de
# subida (IPC-2152), por encima del ITRIP de 1,0 A del motor.
TRACK_POWER = 0.4
TRACK_MOTOR = 0.4
TRACK_3V3 = 0.4
TRACK_POWER_MAX = 0.8

# Ancho mínimo por red de potencia (mm), de la tabla de raíles de NOTAS.md (IPC-2221, 1 oz
# exterior, dT 10 °C: 0,3 -> 1,0 A; 0,5 -> 1,45 A; 0,8 -> 2,0 A). Por encima de 1,5 A manda el
# polígono: VSYS y BAT llevan además el relleno de In2 y cobre ancho junto al cargador.
ANCHOS_MINIMOS = {
    "VBUS_IN": 0.5, "VBUS": 0.5,          # PTC de 1,5 A
    "VSYS": 0.6, "BAT": 0.8, "BAT_PAD": 0.8,  # picos de 2,9 A (motor + radio + audio): polígonos
    "3V3": 0.4,                           # 0,6 A de pico (radio + cámara)
    "V6": 0.5, "MOT_OUT1": 0.5, "MOT_OUT2": 0.5,  # ITRIP 1,0 A
    "BST_SW": 0.8, "BB_SW1": 0.6, "BB_SW2": 0.6,  # nodos SW: cortos y anchos
    "SPK_P": 0.4, "SPK_N": 0.4,           # picos de 0,9 A
    "IR_LED_A": 0.3, "IR_LED_K": 0.3,     # 100 mA en pulsos
}

# Par USB de ≈ 90 Ω diferenciales en L1 sobre GND en L2 (prepreg 7628 de 0,2104 mm,
# εr 4,4). Microstrip acoplado (IPC-2141): con 0,28 de ancho Z0 ≈ 59 Ω y, con
# 0,15 de separación, Zdiff ≈ 89 Ω. A 12 Mbit/s (USB FS) no hace falta pedir
# impedancia controlada; si se pide, ajustar con la calculadora de JLCPCB.
USB_DIFF_W = 0.28
USB_DIFF_GAP = 0.15
