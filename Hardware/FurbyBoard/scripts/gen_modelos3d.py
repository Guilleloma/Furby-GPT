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


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for nombre, forma in (("USB_C_HRO_TYPE-C-31-M-13C", usb_c()), ("FPC_AFC01-S24FCA-00", fpc()),
                          ("L_Changjiang_FHD4020S", bobina())):
        ruta = os.path.join(SALIDA, nombre + ".step")
        forma.exportStep(ruta)
        print("Modelo:", os.path.relpath(ruta, os.path.join(SALIDA, "..", "..")))


main()
