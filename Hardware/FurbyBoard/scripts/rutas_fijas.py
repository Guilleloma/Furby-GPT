"""Rutas que se trazan a mano antes del autorrutado (coordenadas del STL, mm).

El par USB va de J1 al ESD (U1) y de ahí al módulo como par acoplado de 0,28 / 0,15
(≈ 90 Ω sobre el plano de GND de In1, ver params.py) por F.Cu, sin vías. Solo
entre los pads de J1 y U1 se estrecha a 0,20 durante 4 mm: a 12 Mbit/s esa
discontinuidad no se ve.

La cara A del conector (A6/A7) entra por el centro de U1; la cara B se une en
el propio U1, que tiene dos pines por línea unidos por dentro (1-6 para D+ y
3-4 para D−): B7 sube directa al pin 3 y B6 baja a B.Cu y vuelve a subir junto
al pin 6. El par sale de U1 por la izquierda (pines 1 y 3), con la vía de GND
del pin 2 entre las dos líneas, y sube por el canal de x −83,1 hasta los pads
13 (D−) y 14 (D+) del módulo.

Freerouting recibe estas pistas bloqueadas y no las toca.
"""

USB_W = 0.28
NECK_W = 0.20
VIA = (0.6, 0.3)

# Carriles del par: D+ por dentro (derecha en la subida, arriba en el tramo horizontal)
_DP_X, _DN_X = -82.90, -83.33
_DP_Y, _DN_Y = -116.785, -117.215

TRACKS = [
    # J1 cara A -> centro de U1 (cuello de 0,20)
    ("F.Cu", NECK_W, "USB_DP", [(-73.75, -121.194), (-73.75, -120.50), (-73.68, -120.43), (-73.68, -116.05),
                                (-74.637, -116.05)]),
    ("F.Cu", NECK_W, "USB_DN", [(-73.25, -121.194), (-73.25, -120.50), (-73.32, -120.43), (-73.32, -117.95),
                                (-72.363, -117.95)]),
    # J1 cara B
    ("F.Cu", NECK_W, "USB_DN", [(-74.25, -121.194), (-74.25, -117.95)]),
    ("F.Cu", NECK_W, "USB_DP", [(-72.75, -121.194), (-72.75, -120.45), (-72.60, -119.75)]),
    ("B.Cu", NECK_W, "USB_DP", [(-72.60, -119.75), (-72.60, -116.60), (-72.05, -116.05), (-71.10, -116.05)]),
    ("F.Cu", NECK_W, "USB_DP", [(-71.10, -116.05), (-72.363, -116.05)]),
    # GND del pin 2 de U1
    ("F.Cu", 0.30, "GND", [(-74.637, -117.0), (-76.0, -117.0)]),
    # Par acoplado U1 -> módulo
    ("F.Cu", USB_W, "USB_DP", [(-74.637, -116.05), (-76.70, -116.05), (-77.435, _DP_Y), (_DP_X + 0.5, _DP_Y),
                               (_DP_X, _DP_Y + 0.5), (_DP_X, -79.90), (-82.50, -79.50), (-81.75, -79.50)]),
    ("F.Cu", USB_W, "USB_DN", [(-74.637, -117.95), (-76.90, -117.95), (-77.635, _DN_Y), (_DN_X + 0.752, _DN_Y),
                               (_DN_X, _DN_Y + 0.752), (_DN_X, -78.63), (-82.93, -78.23), (-81.75, -78.23)]),
]

VIAS = [
    ("USB_DP", (-72.60, -119.75)),
    ("USB_DP", (-71.10, -116.05)),
    ("GND", (-76.0, -117.0)),
]
