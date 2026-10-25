"""Piezas y redes de la FurbyBoard v1.0: la fuente de verdad del esquemático y del PCB.

Cada pieza lleva su hoja (bloque del esquemático), símbolo, huella, número LCSC
y la red de cada pin. Los valores salen de Hardware/PCB-suelo/ARQUITECTURA.md
(revisión v2, iteración 3). Números LCSC comprobados en la API de piezas de
JLCPCB el 2026-10-24.

Hojas: usb, alimentacion, mcu, motor, audio, camara, sensores, led_tp.
"""

SHEETS = [
    ("usb", "USB-C y protección"),
    ("alimentacion", "Carga, batería y 3,3 V"),
    ("mcu", "ESP32-S3-WROOM-1"),
    ("motor", "Elevador 6 V y puente H"),
    ("audio", "Amplificador y micro"),
    ("camara", "Cámara DVP"),
    ("sensores", "Expansor y sensores del Furby"),
    ("led_tp", "LED, puntos de test y J_EXP"),
]

FP_R0603 = "Resistor_SMD:R_0603_1608Metric"
FP_R0805 = "Resistor_SMD:R_0805_2012Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_TP = "TestPoint:TestPoint_Pad_D1.5mm"
FP_JP = "Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm"

# Resistencias 0603 UNI-ROYAL 1 %: valor -> (LCSC, clase)
RES = {
    "33": ("C23140", "base"), "100": ("C22775", "base"), "220": ("C22962", "base"), "470": ("C23179", "base"),
    "1k": ("C21190", "base"), "1.2k": ("C22765", "base"), "1.5k": ("C22843", "base"),
    "1.8k": ("C4177", "base"), "2.2k": ("C4190", "base"), "4.7k": ("C23162", "base"),
    "5.1k": ("C23186", "base"), "10k": ("C25804", "base"), "30k": ("C22984", "base"),
    "47k": ("C25819", "base"), "91k": ("C23265", "pref"), "100k": ("C25803", "base"),
    "150k": ("C22807", "base"), "220k": ("C22961", "base"), "270k": ("C22965", "pref"),
    "390k": ("C23150", "pref"), "470k": ("C23178", "base"), "510k": ("C23192", "base"),
}
# Condensadores: valor -> (LCSC, clase, huella, descripción)
CAP = {
    "10p": ("C1634", "base", FP_C0603, "10 pF 50 V C0G"),
    "4.7n": ("C53987", "base", FP_C0603, "4,7 nF 50 V X7R"),
    "10n": ("C57112", "base", FP_C0603, "10 nF 50 V X7R"),
    "100n": ("C14663", "base", FP_C0603, "100 nF 50 V X7R"),
    "1u": ("C15849", "base", FP_C0603, "1 µF 50 V X5R"),
    "2.2u": ("C23630", "base", FP_C0603, "2,2 µF 16 V X5R"),
    "10u": ("C19702", "base", FP_C0603, "10 µF 10 V X5R"),
    "22u": ("C45783", "base", FP_C0805, "22 µF 25 V X5R"),
}

_parts = []


def part(ref, sheet, lib_id, value, footprint, pins, lcsc="", jlc="", mpn="", desc="",
         in_bom=True, in_pos=True, dnp=False):
    _parts.append(dict(ref=ref, sheet=sheet, lib_id=lib_id, value=value, footprint=footprint,
                       pins=pins, lcsc=lcsc, jlc=jlc, mpn=mpn, desc=desc, in_bom=in_bom,
                       in_pos=in_pos, dnp=dnp))


def R(ref, sheet, value, a, b, desc=""):
    lcsc, jlc = RES[value]
    part(ref, sheet, "Device:R", value, FP_R0603, {"1": a, "2": b}, lcsc, jlc,
         "UNI-ROYAL 0603 1%", desc)


def C(ref, sheet, value, a, b, desc=""):
    lcsc, jlc, fp, d = CAP[value]
    part(ref, sheet, "Device:C", value, fp, {"1": a, "2": b}, lcsc, jlc, d, desc)


def TP(ref, sheet, net, desc=""):
    part(ref, sheet, "Connector:TestPoint", net, FP_TP, {"1": net}, desc=desc,
         in_bom=False, in_pos=False)


def JP(ref, sheet, a, b, desc=""):
    part(ref, sheet, "Jumper:SolderJumper_2_Bridged", "Puente", FP_JP, {"1": a, "2": b},
         desc=desc, in_bom=False, in_pos=False)


def pads(ref, sheet, nets, footprint, desc):
    """Pads pasantes para soldar cables (no se montan: fuera de la BOM y del CPL)."""
    n = len(nets)
    part(ref, sheet, "Connector_Generic:Conn_01x%02d" % n, desc, footprint,
         {str(i + 1): net for i, net in enumerate(nets)}, desc=desc, in_bom=False, in_pos=False)


def build():
    _parts.clear()

    # ------------------------------------------------------------------ USB
    s = "usb"
    part("J1", s, "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C 16P",
         "FurbyBoard:USB_C_HRO_TYPE-C-31-M-13C",
         {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND",
          "A4": "VBUS_IN", "B4": "VBUS_IN", "A9": "VBUS_IN", "B9": "VBUS_IN",
          "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
          "A8": "", "B8": "", "SH": "GND"},
         "C2848620", "ext", "HRO TYPE-C-31-M-13C",
         "USB-C 16 pines de montaje medio, PCB de 1,6, boca 0,70 fuera del borde")
    R("R1", s, "5.1k", "CC1", "GND", "Rd CC1")
    R("R2", s, "5.1k", "CC2", "GND", "Rd CC2")
    part("U1", s, "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
         {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "VBUS_IN"},
         "C2687116", "ext", "STMicro USBLC6-2SC6", "ESD de D+/D− y VBUS")
    part("F1", s, "Device:Polyfuse", "1.5A", "Fuse:Fuse_1206_3216Metric",
         {"1": "VBUS_IN", "2": "VBUS"}, "C883133", "ext", "BSMD1206-150-16V", "PTC 1,5 A / 16 V")
    C("C1", s, "10u", "VBUS", "GND", "VBUS tras el PTC")
    TP("TP1", s, "VBUS", "5,0 V con USB")
    TP("TP2", s, "USB_DP", "D+")
    TP("TP3", s, "USB_DN", "D−")

    # --------------------------------------------------------- alimentación
    s = "alimentacion"
    part("U2", s, "Battery_Management:BQ24073RGT", "BQ24073RGTR",
         "Package_DFN_QFN:VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm",
         {"1": "BQ_TS", "2": "BAT", "3": "BAT", "4": "GND", "5": "BQ_EN2", "6": "BQ_EN1",
          "7": "PGOOD", "8": "GND", "9": "CHG", "10": "VSYS", "11": "VSYS", "12": "BQ_ILIM",
          "13": "VBUS", "14": "", "15": "GND", "16": "BQ_ISET", "17": "GND"},
         "C15220", "ext", "TI BQ24073RGTR", "Cargador con power path, OUT 4,4 V")
    C("C2", s, "1u", "VBUS", "GND", "IN del BQ24073")
    C("C3", s, "10u", "VSYS", "GND", "OUT del BQ24073")
    C("C4", s, "10u", "BAT", "GND", "BAT del BQ24073")
    # NTC de 10 kΩ (103AT, B 3380 K) de TS a VSS, como pide el datasheet del BQ2407x (el pin lleva
    # su fuente de corriente interna; sin red de polarización). Va en la placa bajo la batería,
    # lejos del cargador: mide la PCB bajo la celda. Decisión del 2026-10-24 (crítico B7).
    part("RT1", s, "Device:Thermistor_NTC", "10k NTC", FP_R0603, {"1": "BQ_TS", "2": "GND"},
         "C13564", "ext", "Murata NCP18XH103F03RB", "NTC 10 kΩ B3380 0603 en TS (carga 0–45 °C)")
    R("R4", s, "1.8k", "BQ_ISET", "GND", "ICHG = 890/1800 = 0,494 A")
    R("R5", s, "1.2k", "BQ_ILIM", "GND", "IIN = 1610/1200 = 1,34 A con EN2=1, EN1=0")
    R("R6", s, "100k", "BQ_EN1", "VSYS", "EN1 a 1 al arrancar (USB500)")
    R("R7", s, "100k", "BQ_EN2", "GND", "EN2 a 0 al arrancar (USB500)")
    R("R8", s, "100k", "PGOOD", "3V3", "PGOOD a 3,3 V sin USB")
    R("R9", s, "100k", "CHG", "3V3", "CHG a 3,3 V sin carga")
    R("R10", s, "2.2k", "VBUS", "LED_CHG_A", "LED CHG ≈ 1,4 mA solo con USB")
    part("D1", s, "Device:LED", "Rojo", "LED_SMD:LED_0603_1608Metric", {"1": "CHG", "2": "LED_CHG_A"},
         "C2286", "base", "KT-0603R", "LED CHG: cargando")
    R("R11", s, "2.2k", "VBUS", "LED_PG_A", "LED PG ≈ 1,4 mA solo con USB")
    part("D2", s, "Device:LED", "Verde", "LED_SMD:LED_0805_2012Metric", {"1": "PGOOD", "2": "LED_PG_A"},
         "C2297", "base", "KT-0805G", "LED PG: USB válido")
    part("Q1", s, "FurbyBoard:SI7615ADN", "SI7615ADN", "Package_SO:Vishay_PowerPAK_1212-8_Single",
         {"1": "BAT", "2": "BAT", "3": "BAT", "4": "BAT_G", "5": "BAT_PAD"},
         "C553966", "ext", "Vishay SI7615ADN-T1-GE3",
         "Protección contra polaridad inversa de la batería (P-MOSFET, puerta a GND)")
    R("R12", s, "10k", "BAT_G", "GND", "Puerta del P-MOSFET a GND")
    part("J2", s, "Connector_Generic:Conn_01x01", "BAT+", "FurbyBoard:BAT_POS_Square3x3_Drill1.2",
         {"1": "BAT_PAD"}, desc="Pad BAT+ (cuadrado)", in_bom=False, in_pos=False)
    part("J3", s, "Connector_Generic:Conn_01x01", "BAT-", "FurbyBoard:BAT_NEG_Round2.6_Drill1.0",
         {"1": "GND"}, desc="Pad BAT− (redondo)", in_bom=False, in_pos=False)
    R("R13", s, "470k", "BAT", "VBAT_SNS", "Divisor de VBAT")
    R("R14", s, "470k", "VBAT_SNS", "GND", "Divisor de VBAT")
    C("C5", s, "100n", "VBAT_SNS", "GND", "Filtro del ADC")
    part("U3", s, "FurbyBoard:TPS63802", "TPS63802DLAR", "FurbyBoard:Texas_DLA_VSON-10_2x3mm_P0.5mm",
         {"1": "VSYS", "2": "GND", "3": "GND", "4": "BB_FB", "5": "", "6": "3V3", "7": "BB_SW2",
          "8": "GND", "9": "BB_SW1", "10": "VSYS"},
         "C2845237", "ext", "TI TPS63802DLAR", "Buck-boost 3,3 V, 2 A, PFM")
    part("L1", s, "Device:L", "0.47u", "FurbyBoard:L_Changjiang_FHD4020S", {"1": "BB_SW1", "2": "BB_SW2"},
         "C602026", "ext", "Changjiang FHD4020S-R47MT", "0,47 µH, 4 × 4 mm")
    R("R15", s, "510k", "3V3", "BB_FB", "VOUT = 0,5 × (1 + 510/91) = 3,30 V")
    R("R16", s, "91k", "BB_FB", "GND", "Realimentación")
    C("C6", s, "10u", "VSYS", "GND", "Entrada del TPS63802")
    C("C7", s, "22u", "3V3", "GND", "Salida del TPS63802")
    C("C8", s, "22u", "3V3", "GND", "Salida del TPS63802")
    TP("TP4", s, "BAT", "VBAT 3,0–4,2 V (tras el P-MOSFET)")
    TP("TP5", s, "VSYS", "4,4 V con USB; VBAT sin USB")
    TP("TP6", s, "3V3", "3,30 V")

    # ------------------------------------------------------------------ MCU
    s = "mcu"
    # GPIO por geometría (replanteo del 2026-10-24): la cámara en los pines del lado del FPC
    # (fila inferior derecha y columna derecha, en el orden de los pads de J6), y en la columna
    # izquierda, de arriba abajo, lo que va al expansor (I2C, INT), al amplificador y al micro
    # (I2S) y a J9 por el pasillo sur (HOME, ENC). Los pines 35-39 (IR_RX, UART0, LIGHT,
    # VBAT_SNS) salen por debajo del módulo en capas internas: no cruzan el bus de la cámara.
    # Sin tocar strapping (IO0, IO3, IO45, IO46) ni el USB (IO19/IO20).
    io = {
        "1": "GND", "2": "3V3", "3": "EN", "4": "I2C_SDA", "5": "I2C_SCL", "6": "EXP_INT",
        "7": "I2S_BCLK", "8": "I2S_WS", "9": "I2S_DOUT", "10": "I2S_DIN", "11": "HOME",
        "12": "ENC_IO", "13": "USB_DN", "14": "USB_DP", "15": "IPROPI_IO", "16": "MOT_IN2_IO",
        "17": "MOT_IN1_IO", "18": "CAM_VSYNC", "19": "CAM_HREF", "20": "CAM_Y9", "21": "CAM_XCLK",
        "22": "CAM_Y8", "23": "CAM_Y7", "24": "CAM_PCLK", "25": "CAM_Y6", "26": "IR_TX",
        "27": "BOOT", "28": "", "29": "", "30": "", "31": "CAM_Y2", "32": "CAM_Y5",
        "33": "CAM_Y3", "34": "CAM_Y4", "35": "IR_RX", "36": "U0RX", "37": "U0TX",
        "38": "LIGHT", "39": "VBAT_SNS", "40": "GND", "41": "GND",
    }
    part("U4", s, "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R8", "RF_Module:ESP32-S3-WROOM-1",
         io, "C2913202", "ext", "Espressif ESP32-S3-WROOM-1-N16R8",
         "16 MB flash, 8 MB PSRAM octal (GPIO35–37 ocupados)")
    C("C9", s, "22u", "3V3", "GND", "Desacoplo del módulo")
    C("C10", s, "100n", "3V3", "GND", "Desacoplo del módulo")
    R("R17", s, "10k", "EN", "3V3", "EN con RC")
    C("C11", s, "1u", "EN", "GND", "EN con RC (≈ 10 ms)")
    part("SW1", s, "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TS-1088-xR020",
         {"1": "EN", "2": "GND"}, "C720477", "base", "TS-1088-AR02016", "Botón RESET")
    R("R18", s, "10k", "BOOT", "3V3", "GPIO0 a 1 (arranque normal)")
    part("SW2", s, "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TS-1088-xR020",
         {"1": "BOOT", "2": "GND"}, "C720477", "base", "TS-1088-AR02016", "Botón BOOT")
    R("R19", s, "1.5k", "3V3", "LED_PROG_A", "LED PROG ≈ 1 mA")
    part("D3", s, "Device:LED", "Rojo", "LED_SMD:LED_0603_1608Metric", {"1": "U0TX", "2": "LED_PROG_A"},
         "C2286", "base", "KT-0603R", "LED PROG en U0TXD (log del ROM)")

    # ---------------------------------------------------------------- motor
    s = "motor"
    part("U5", s, "Regulator_Switching:TPS61089", "TPS61089RNRR", "Package_DFN_QFN:Texas_VQFN-RNR0011A-11",
         {"1": "BST_FSW", "2": "BST_VCC", "3": "BST_FB", "4": "BST_COMP", "5": "GND", "6": "V6",
          "7": "EN_6V", "8": "BST_ILIM", "9": "VSYS", "10": "BST_BOOT", "11": "BST_SW"},
         "C165129", "ext", "TI TPS61089RNRR", "Elevador a 5,94 V, ILIM 3,8 A")
    part("L2", s, "Device:L", "1u", "FurbyBoard:L_Changjiang_FHD4020S", {"1": "VSYS", "2": "BST_SW"},
         "C602028", "ext", "Changjiang FHD4020S-1R0MT", "1 µH, 4 × 4 mm (la del mod de la Game Boy)")
    R("R20", s, "150k", "BST_FSW", "BST_SW", "fSW ≈ 0,96 MHz")
    C("C12", s, "2.2u", "BST_VCC", "GND", "VCC del TPS61089")
    C("C13", s, "100n", "BST_BOOT", "BST_SW", "BOOT")
    R("R21", s, "390k", "V6", "BST_FB", "VOUT = 1,212 × (1 + 390/100) = 5,94 V")
    R("R22", s, "100k", "BST_FB", "GND", "Realimentación")
    R("R23", s, "270k", "BST_ILIM", "GND", "ILIM = 1 030 000/270k = 3,8 A")
    R("R24", s, "30k", "BST_COMP", "BST_RC", "Compensación (fc ≈ 20–30 kHz)")
    C("C14", s, "4.7n", "BST_RC", "GND", "Compensación")
    C("C15", s, "10p", "BST_COMP", "GND", "Compensación, polo alto")
    R("R25", s, "100k", "EN_6V", "GND", "Elevador apagado al arrancar")
    C("C16", s, "22u", "VSYS", "GND", "Entrada del elevador")
    C("C17", s, "22u", "VSYS", "GND", "Entrada del elevador")
    for i, ref in enumerate(("C18", "C19", "C20", "C21")):
        C(ref, s, "22u", "V6", "GND", "Salida del elevador")
    C("C22", s, "100n", "V6", "GND", "Desacoplo del DRV8231A")
    part("U6", s, "FurbyBoard:DRV8231ADSG", "DRV8231ADSGR",
         "Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm",
         {"1": "IPROPI", "2": "MOT_IN2", "3": "MOT_IN1", "4": "MOT_VREF", "5": "V6", "6": "MOT_OUT1",
          "7": "GND", "8": "MOT_OUT2", "9": "GND"},
         "C5139865", "ext", "TI DRV8231ADSGR", "Puente H IN/IN con regulación de corriente")
    R("R26", s, "4.7k", "3V3", "MOT_VREF", "VREF = 3,3 × 10/(4,7+10) = 2,245 V → ITRIP 1,0 A")
    R("R27", s, "10k", "MOT_VREF", "GND", "VREF")
    C("C23", s, "100n", "MOT_VREF", "GND", "VREF")
    R("R28", s, "1.5k", "IPROPI", "GND", "RIPROPI: 2,25 V por amperio")
    R("R29", s, "100k", "MOT_IN1", "GND", "Motor parado al arrancar")
    R("R30", s, "100k", "MOT_IN2", "GND", "Motor parado al arrancar")
    JP("JP1", s, "MOT_IN1_IO", "MOT_IN1", "Cortar para liberar GPIO9")
    JP("JP2", s, "MOT_IN2_IO", "MOT_IN2", "Cortar para liberar GPIO46")
    JP("JP3", s, "IPROPI_IO", "IPROPI", "Cortar para liberar GPIO3 (ADC)")
    TP("TP7", s, "V6", "5,94 V con EN_6V")
    TP("TP8", s, "IPROPI", "2,25 V/A")

    # ---------------------------------------------------------------- audio
    s = "audio"
    part("U7", s, "FurbyBoard:MAX98357A", "MAX98357AETE+T", "Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm",
         {"1": "I2S_DOUT", "2": "VSYS", "3": "GND", "4": "AMP_SD", "5": "", "6": "", "7": "VSYS",
          "8": "VSYS", "9": "SPK_P", "10": "SPK_N", "11": "GND", "12": "", "13": "", "14": "I2S_WS",
          "15": "GND", "16": "I2S_BCLK", "17": "GND"},
         "C910544", "ext", "Maxim MAX98357AETE+T", "Clase D I2S, GAIN_SLOT a VDD (6 dB)")
    C("C24", s, "22u", "VSYS", "GND", "VDD del amplificador")
    C("C25", s, "22u", "VSYS", "GND", "VDD del amplificador")
    C("C26", s, "100n", "VSYS", "GND", "VDD del amplificador")
    # 10 µF junto a los pines 7/8 (sim/RESULTADOS.md, «Amplificador»): C24/C25 quedan al otro lado del puente de VSYS
    # de B.Cu y con solo C26 el rizado en VDD era de 257 mV pp; la hoja pide 0,1 µF + 10 µF en VDD
    C("C41", s, "10u", "VSYS", "GND", "VDD del amplificador, junto a los pines 7/8")
    R("R31", s, "33", "I2S_BCLK", "I2S_SCK_MIC", "Serie hacia el micro (cable)")
    R("R32", s, "33", "I2S_WS", "I2S_WS_MIC", "Serie hacia el micro (cable)")
    pads("J5", s, ["I2S_DIN", "GND", "I2S_SCK_MIC", "I2S_WS_MIC", "3V3", "GND"], "FurbyBoard:Pads_2x03_P2.54mm",
         "Micro I2S (SD, GND, SCK, WS, 3V3, GND)")
    TP("TP9", s, "I2S_DOUT", "Datos I2S al amplificador")

    # --------------------------------------------------------------- cámara
    s = "camara"
    part("J6", s, "Connector_Generic_MountingPin:Conn_01x24_MountingPin", "FPC 24P 0.5",
         "FurbyBoard:FPC_AFC01-S24FCA-00",
         {"1": "", "2": "GND", "3": "I2C_SDA", "4": "CAM_2V8", "5": "I2C_SCL", "6": "CAM_RST",
          "7": "CAM_VSYNC", "8": "CAM_PWDN", "9": "CAM_HREF", "10": "CAM_DVDD", "11": "3V3",
          "12": "CAM_Y9", "13": "CAM_XCLK", "14": "CAM_Y8", "15": "GND", "16": "CAM_Y7",
          "17": "CAM_PCLK", "18": "CAM_Y6", "19": "CAM_Y2", "20": "CAM_Y5", "21": "CAM_Y3",
          "22": "CAM_Y4", "23": "", "24": "", "MP": "GND"},
         "C262669", "ext", "JUSHUO AFC01-S24FCA-00",
         "Cámara DVP OV2640/OV3660/OV5640 (pinout de facto, verificar con el módulo)")
    part("U8", s, "Regulator_Linear:ME6211C28M5", "ME6211C28M5G-N", "Package_TO_SOT_SMD:SOT-23-5",
         {"1": "3V3", "2": "GND", "3": "CAM_EN", "4": "", "5": "CAM_2V8"},
         "C53099", "ext", "Microne ME6211C28M5G-N", "AVDD 2,8 V de la cámara")
    part("U9", s, "Regulator_Linear:ME6211C12M5", "ME6211C12M5G-N", "Package_TO_SOT_SMD:SOT-23-5",
         {"1": "CAM_2V8", "2": "GND", "3": "CAM_EN", "4": "", "5": "CAM_DVDD"},
         "C236672", "ext", "Microne ME6211C12M5G-N",
         "DVDD 1,2 V (OV2640); para OV3660/OV5640, ME6211C15M5G-N (C53100), misma huella")
    C("C27", s, "1u", "3V3", "GND", "Entrada del LDO de 2,8 V")
    C("C28", s, "1u", "CAM_2V8", "GND", "Salida de 2,8 V")
    C("C29", s, "1u", "CAM_DVDD", "GND", "Salida de DVDD")
    C("C30", s, "100n", "3V3", "GND", "DOVDD en el FPC")
    R("R33", s, "100k", "CAM_EN", "GND", "Cámara sin alimentar al arrancar")
    R("R34", s, "10k", "CAM_PWDN", "3V3", "Cámara en reposo al arrancar")
    R("R35", s, "10k", "CAM_RST", "3V3", "RESETB con RC")
    C("C31", s, "100n", "CAM_RST", "GND", "RESETB con RC")
    TP("TP10", s, "CAM_2V8", "2,80 V con la cámara encendida")
    TP("TP11", s, "CAM_DVDD", "1,20 V (o 1,50 V) con la cámara encendida")

    # ------------------------------------------------------------- sensores
    s = "sensores"
    part("U10", s, "Interface_Expansion:TCA9535PWR", "TCA9535PWR", "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
         # Puertos por geometría (2026-10-24): P0x (cara oeste) hacia J8, J11, J7 y el
         # amplificador; P1x (cara este) hacia el cargador, el elevador, J9, la cámara y el LED.
         # Bloque U2 (2026-10-25): P03 LED_RUN_K, P04 EXP_P07 y P17 IR_PWR (ver NOTAS «Pines»).
         {"1": "EXP_INT", "2": "GND", "3": "GND", "4": "TILT_A", "5": "TILT_B", "6": "TONGUE",
          "7": "LED_RUN_K", "8": "EXP_P07", "9": "AMP_SD", "10": "PGOOD", "11": "CHG", "12": "GND",
          "13": "BQ_EN1", "14": "BQ_EN2", "15": "EN_6V", "16": "TUMMY", "17": "BACK",
          "18": "CAM_PWDN", "19": "CAM_EN", "20": "IR_PWR", "21": "GND", "22": "I2C_SCL",
          "23": "I2C_SDA", "24": "3V3"},
         "C130204", "ext", "TI TCA9535PWR", "Expansor I2C 0x20 (bus compartido con el SCCB)")
    C("C32", s, "100n", "3V3", "GND", "Desacoplo del TCA9535")
    R("R36", s, "4.7k", "I2C_SDA", "3V3", "Pull-up I2C")
    R("R37", s, "4.7k", "I2C_SCL", "3V3", "Pull-up I2C")
    R("R38", s, "10k", "EXP_INT", "3V3", "Pull-up de INT")
    # Interruptores normalmente abiertos a GND (barriga, espalda, lengua): pull-up 47k,
    # serie 1k, 100 nF. Inclinación: 220k (si la bola queda cerrada, 15 µA).
    sw = [("TUMMY", "47k", "R39", "R40", "C33"), ("BACK", "47k", "R41", "R42", "C34"),
          ("TONGUE", "47k", "R43", "R44", "C35"), ("TILT_A", "220k", "R45", "R46", "C36"),
          ("TILT_B", "220k", "R47", "R48", "C37")]
    for net, rpu, rp, rs, cc in sw:
        R(rp, s, rpu, net, "3V3", "Pull-up de " + net)
        R(rs, s, "1k", net, net + "_PAD", "Serie de " + net)
        C(cc, s, "100n", net, "GND", "Filtro de " + net)
    R("R49", s, "100k", "HOME", "3V3", "Pull-up de la leva")
    R("R50", s, "1k", "HOME", "HOME_PAD", "Serie de la leva")
    C("C38", s, "10n", "HOME", "GND", "Filtro de la leva (τ = 1 ms)")
    # Encoder: el LED IR del engranaje se alimenta del raíl de 6 V, así solo luce con el elevador
    # encendido (EN_6V) y sin transistor: (5,94 − 1,3) / 470 ≈ 9,9 mA, 46 mW en 0603 (≤ 50 %).
    # Antes iba a 3V3 con un AO3400A gobernado por EN_6V (replanteo del 2026-10-24: sin sitio).
    # C23179 (470 Ω UNI-ROYAL 0603): código por confirmar en la API de JLCPCB antes del pedido.
    R("R51", s, "470", "V6", "ENC_LED_A", "LED del encoder ≈ 10 mA con el elevador encendido")
    R("R52", s, "10k", "ENC_PT", "3V3", "Pull-up del fototransistor (4,7k–47k)")
    part("U11", s, "74xGxx:74LVC1G17", "SN74LVC1G17DBVR", "Package_TO_SOT_SMD:SOT-23-5",
         {"1": "", "2": "ENC_PT", "3": "GND", "4": "ENC", "5": "3V3"}, "C7836", "ext",
         "TI SN74LVC1G17DBVR", "Schmitt del encoder")
    C("C39", s, "100n", "3V3", "GND", "Desacoplo del Schmitt")
    JP("JP4", s, "ENC", "ENC_IO", "Cortar para liberar GPIO8")
    # Luz: LDR entre 3V3 y LIGHT, 470k a GND
    R("R53", s, "470k", "LIGHT", "GND", "LDR con luz ≈ 7 µA")
    C("C40", s, "100n", "LIGHT", "GND", "Filtro del ADC")
    # IR: emisor con AO3400A (GPIO45, strapping: pull-down) y receptor alimentado por P17
    part("R54", s, "Device:R", "22", FP_R0805, {"1": "VSYS", "2": "IR_LED_A"}, "C17561", "base",
         "UNI-ROYAL 0805W8F220JT5E", "LED IR ≈ 100 mA en pulsos (0805 por la potencia de pico)")
    part("Q3", s, "Transistor_FET:Q_NMOS_GSD", "AO3400A", "Package_TO_SOT_SMD:SOT-23",
         {"1": "IR_TX", "2": "GND", "3": "IR_LED_K"}, "C20917", "base", "AOS AO3400A", "Emisor IR")
    R("R55", s, "100k", "IR_TX", "GND", "GPIO45 a 0 al arrancar (strapping VDD_SPI)")
    R("R56", s, "1k", "IR_RX", "IR_RX_PAD", "Serie del receptor IR")
    # Pads de cables (agrupados como en la planta)
    # J7.3 y J7.8 permutados (bloque U2, 2026-10-25): IR_PWR sale por el sur de J7 hacia In2.
    pads("J7", s, ["IR_LED_A", "IR_LED_K", "GND", "IR_RX_PAD", "3V3", "LIGHT", "GND", "IR_PWR"],
         "FurbyBoard:Pads_2x04_P2.54mm", "Frente: IR (emisor ×2, receptor ×3), luz ×2, GND")
    pads("J8", s, ["TILT_A_PAD", "TILT_B_PAD", "GND", "TONGUE_PAD", "GND", "SPK_P", "SPK_N"],
         "FurbyBoard:Pads_1x07_P2.54mm", "Inclinación ×3, lengua ×2, altavoz ×2")
    # Orden por geometría: la columna exterior lleva el encoder y la leva (fototransistor arriba, lejos
    # de las salidas del motor); la interior, barriga, espalda y el motor abajo, junto al puente H.
    pads("J9", s, ["ENC_PT", "GND", "ENC_LED_A", "GND", "HOME_PAD", "GND", "TUMMY_PAD", "GND",
                   "BACK_PAD", "GND", "MOT_OUT2", "MOT_OUT1"], "FurbyBoard:Pads_2x06_P2.54mm",
         # Pads 11/12 del motor: OUT2 arriba y OUT1 abajo (rutado 2026-10-24: OUT2 sale del pin 8
         # hacia el noreste en F.Cu y OUT1 del pin 6 por In2; el sentido de giro lo fija el firmware)
         "Encoder ×3, leva ×2, barriga ×2, espalda ×2, motor ×2 (más GND)")

    # ---------------------------------------------------------------- LED y TP
    s = "led_tp"
    R("R57", s, "1k", "3V3", "LED_PWR_A", "LED PWR ≈ 0,5–0,9 mA (verde InGaN, VF 2,6–3,1 V)")
    part("D4", s, "Device:LED", "Verde", "LED_SMD:LED_0805_2012Metric", {"1": "LED_PWR_K", "2": "LED_PWR_A"},
         "C2297", "base", "KT-0805G", "LED PWR: hay 3,3 V")
    JP("JP5", s, "LED_PWR_K", "GND", "Cortar para apagar el LED PWR (hasta −0,9 mA en reposo)")
    R("R58", s, "1k", "3V3", "LED_RUN_A", "LED RUN ≈ 0,5–0,9 mA (verde InGaN, VF 2,6–3,1 V)")
    part("D5", s, "Device:LED", "Verde", "LED_SMD:LED_0805_2012Metric", {"1": "LED_RUN_K", "2": "LED_RUN_A"},
         "C2297", "base", "KT-0805G", "LED RUN: latido del firmware (P03 del expansor)")
    pads("J11", s, ["GND", "3V3", "VSYS", "VBUS", "EXP_P07", "I2C_SCL", "U0TX", "GND", "I2C_SDA", "U0RX"],
         "FurbyBoard:Pads_2x05_P2.54mm", "J_EXP: header de expansión 2 x 5 sin montar")
    for i, ref in enumerate(("TP12", "TP13", "TP14")):
        TP(ref, s, "GND", "GND")
    return list(_parts)


def parts():
    return build()


def nets():
    seen = []
    for p in parts():
        for n in p["pins"].values():
            if n and n not in seen:
                seen.append(n)
    return seen


def netname(n):
    return n


def net_sheets():
    """Hojas en las que aparece cada red (para elegir etiqueta local o global)."""
    out = {}
    for p in parts():
        for n in p["pins"].values():
            if n:
                out.setdefault(n, set()).add(p["sheet"])
    return out


if __name__ == "__main__":
    ps = parts()
    print(len(ps), "piezas,", len(nets()), "redes")
    single = [n for n, c in __import__("collections").Counter(
        n for p in ps for n in p["pins"].values() if n).items() if c == 1]
    print("redes de un solo pin:", single)
