"""Modelos 3D simplificados (STEP) de las huellas propias que no tienen modelo en KiCad.

Se ejecuta con el Python de FreeCAD:
    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd scripts/gen_modelos3d.py

Solo la envolvente de cada pieza, con las medidas del dibujo del fabricante, para
los renders y para el STEP de la placa que usa la carcasa. Coordenadas del modelo
de KiCad: x a la derecha, y hacia arriba (la y de la huella cambiada de signo),
z = 0 en la cara superior de la PCB.

- USB-C HRO TYPE-C-31-M-13C: cuerpo de 8,94 x 6,42 x 3,16 desde la boca (origen de
  la huella) hacia dentro de la placa, eje 0,02 por encima de la cara superior
  (montaje medio para PCB de 1,6: la mitad del cuerpo queda en la ranura). Boca de
  8,34 x 2,56 con la lengüeta, y las cuatro patas de la carcasa.
- FPC JUSHUO AFC01-S24FCA-00: 16,4 x 5,4 x 2,0 (contorno de F.Fab de la huella).
- Bobina Changjiang FHD4020S: 4,0 x 4,0 x 2,0.

Encapsulados de huellas estándar de KiCad cuyo modelo no viene instalado en KiCad 10
(se llaman como el modelo que pide la huella). Altura máxima del dibujo, para que la
carcasa tenga margen; terminales 0,03 mm fuera del cuerpo para que se vean en el render
y hoyuelo de pin 1 en la cara superior:
- U2 BQ24073, VQFN-16 RGT0016C (https://www.ti.com/lit/ds/symlink/bq24073.pdf, «Package
  outline»): 3,0 x 3,0 x 1,0 máx., 16 terminales de 0,25 x 0,4 a paso 0,5, EP 1,68.
- U5 TPS61089, VQFN-HR RNR0011A (https://www.ti.com/lit/ds/symlink/tps61089.pdf, «Package
  outline»): 2,5 x 2,0 x 1,0 máx.; pines 1-4 y 7-10 de 0,25 x 0,35 a paso 0,5 en los lados
  largos, 5 y 6 de 0,35 x 0,8 en x = ±0,35 en el borde de abajo y 11 de 1,0 x 0,8 en el de arriba.
- Q1 SI7615ADN, PowerPAK 1212-8 single (https://www.vishay.com/docs/71656/ppak12128.pdf):
  cuerpo moldeado de 3,05 x 3,05 x 1,12 máx., patas de 0,30 x 0,43 x 0,28 a paso 0,65 que
  llegan a 3,30 de punta a punta (1-4 a la izquierda; 5-8, el drenador, a la derecha).
"""
import os

import FreeCAD as App
import Part

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "FurbyBoard.3dshapes")


def caja(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, App.Vector(x0, y0, z0))


def estadio(ancho, alto, largo, y0, zc):
    """Prisma de sección de estadio (rectángulo con extremos semicirculares) a lo largo de +y."""
    r = alto / 2
    centro = caja(-ancho / 2 + r, ancho / 2 - r, y0, y0 + largo, zc - r, zc + r)
    izq = Part.makeCylinder(r, largo, App.Vector(-ancho / 2 + r, y0, zc), App.Vector(0, 1, 0))
    der = Part.makeCylinder(r, largo, App.Vector(ancho / 2 - r, y0, zc), App.Vector(0, 1, 0))
    return centro.fuse(izq).fuse(der).removeSplitter()


def usb_c():
    zc = 0.02
    cuerpo = estadio(8.94, 3.16, 6.42, 0.0, zc)
    boca = estadio(8.34, 2.56, 6.0, -0.01, zc)
    lengua = caja(-3.35, 3.35, 0.4, 6.0, zc - 0.35, zc + 0.35)
    forma = cuerpo.cut(boca).fuse(lengua)
    for x in (-5.62, 5.62):
        for y, largo in ((2.1, 2.0), (6.1, 1.6)):
            pata = caja(x - 0.3, x + 0.3, y - largo / 2, y + largo / 2, -2.4, zc)
            # ala de chapa que une la pata con el lateral del cuerpo
            ala = caja(min(x, -4.3 if x < 0 else 4.3), max(x, -4.3 if x < 0 else 4.3),
                       y - largo / 2, y + largo / 2, zc - 0.2, zc)
            forma = forma.fuse(pata).fuse(ala)
    return forma.removeSplitter()


def fpc():
    base = caja(-8.2, 8.2, -4.4, 1.0, 0.0, 1.5)
    tapa = caja(-7.6, 7.6, -4.4, -1.6, 1.5, 2.0)
    return base.fuse(tapa).removeSplitter()


def bobina():
    return caja(-2.0, 2.0, -2.0, 2.0, 0.0, 2.0)


HOLGURA_TERMINAL = 0.03
ALTO_TERMINAL = 0.2


def terminal(lado, centro, ancho, largo, borde_x, borde_y):
    """Terminal de un encapsulado sin patas, en la cara de abajo y asomando por el lado.

    lado: "izq", "der", "arr" o "aba"; centro: coordenada a lo largo del lado; largo: hacia dentro.
    """
    h = HOLGURA_TERMINAL
    if lado == "izq":
        return caja(-borde_x - h, -borde_x + largo, centro - ancho / 2, centro + ancho / 2, 0.0, ALTO_TERMINAL)
    if lado == "der":
        return caja(borde_x - largo, borde_x + h, centro - ancho / 2, centro + ancho / 2, 0.0, ALTO_TERMINAL)
    if lado == "arr":
        return caja(centro - ancho / 2, centro + ancho / 2, borde_y - largo, borde_y + h, 0.0, ALTO_TERMINAL)
    return caja(centro - ancho / 2, centro + ancho / 2, -borde_y - h, -borde_y + largo, 0.0, ALTO_TERMINAL)


def sin_patas(largo_x, ancho_y, alto, terminales, pin1):
    """Cuerpo de QFN/SON con sus terminales y el hoyuelo de pin 1 (x, y) en la cara superior."""
    forma = caja(-largo_x / 2, largo_x / 2, -ancho_y / 2, ancho_y / 2, 0.02, alto)
    for lado, centro, ancho, largo in terminales:
        forma = forma.fuse(terminal(lado, centro, ancho, largo, largo_x / 2, ancho_y / 2))
    return marca_pin1(forma, pin1, alto)


def marca_pin1(forma, pin1, alto):
    hoyuelo = Part.makeCylinder(0.15, 0.1, App.Vector(pin1[0], pin1[1], alto - 0.05))
    return forma.cut(hoyuelo).removeSplitter()


def vqfn16_rgt():
    paso = (0.75, 0.25, -0.25, -0.75)
    terminales = []
    for lado in ("izq", "der", "arr", "aba"):
        terminales += [(lado, c, 0.25, 0.4) for c in paso]
    forma = sin_patas(3.0, 3.0, 1.0, terminales, (-1.0, 1.0))
    ep = caja(-0.84, 0.84, -0.84, 0.84, 0.0, ALTO_TERMINAL)
    return forma.fuse(ep).removeSplitter()


def vqfn_rnr():
    terminales = [(lado, c, 0.25, 0.35) for lado in ("izq", "der") for c in (0.75, 0.25, -0.25, -0.75)]
    terminales += [("aba", -0.35, 0.35, 0.8), ("aba", 0.35, 0.35, 0.8), ("arr", 0.0, 1.0, 0.8)]
    return sin_patas(2.5, 2.0, 1.0, terminales, (-0.85, 0.55))


def powerpak_1212():
    cuerpo = caja(-1.525, 1.525, -1.525, 1.525, 0.02, 1.12)
    patas = [caja(x0, x1, y - 0.15, y + 0.15, 0.0, 0.28)
             for x0, x1 in ((-1.65, -1.22), (1.22, 1.65)) for y in (0.975, 0.325, -0.325, -0.975)]
    drenador = caja(-0.2, 1.525, -1.055, 1.055, 0.0, 0.28)
    forma = cuerpo
    for pieza in patas + [drenador]:
        forma = forma.fuse(pieza)
    return marca_pin1(forma, (-1.05, 1.05), 1.12)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, forma in (("USB_C_HRO_TYPE-C-31-M-13C", usb_c()), ("FPC_AFC01-S24FCA-00", fpc()),
                          ("L_Changjiang_FHD4020S", bobina()),
                          ("VQFN-16-1EP_3x3mm_P0.5mm_EP1.6x1.6mm", vqfn16_rgt()),
                          ("Texas_VQFN-RNR0011A-11", vqfn_rnr()),
                          ("Vishay_PowerPAK_1212-8_Single", powerpak_1212())):
        ruta = os.path.join(SALIDA, nombre + ".step")
        forma.exportStep(ruta)
        print("Modelo:", os.path.relpath(ruta, os.path.join(SALIDA, "..", "..")))


main()
