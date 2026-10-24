# FurbyBoard v1.0

Placa del Furby: ESP32-S3-WROOM-1-N16R8, cargador BQ24073 con power path, 3,3 V con TPS63802, 6 V con TPS61089 para el puente H DRV8231A, amplificador MAX98357A, micro I2S en cable, cámara DVP por FPC de 24 pines, expansor TCA9535 para los sensores y batería LiPo soldada con protección de polaridad. Tiene la forma del suelo de la base (`../PCB-suelo/`) y va atornillada con 4 × M2.

La arquitectura y los cálculos están en [`../PCB-suelo/ARQUITECTURA.md`](../PCB-suelo/ARQUITECTURA.md); la geometría que comparte con la base, en [`../PCB-suelo/interfaz-base.md`](../PCB-suelo/interfaz-base.md) y `geometria.json`. El plan de pruebas es [`TEST-PLAN.md`](TEST-PLAN.md) y el pedido, [`fabricacion/README.md`](fabricacion/README.md).

## Estado (2026-10-24)

| Parte | Estado |
|-------|--------|
| Esquema jerárquico (8 hojas) | ERC 0 errores, 0 avisos. LCSC en todas las piezas que se montan |
| Contorno, taladros, ranura del USB-C | De `geometria.json` (holgura de 1,0 a la pared) |
| Colocación | DRC sin infracciones salvo lo que falta por rutar; `comprobar_colocacion.py` OK |
| Par USB | Trazado a mano y bloqueado (`scripts/rutas_fijas.py`) |
| **Resto del rutado** | **Pendiente**: hace falta ejecutar Freerouting (ver «Rutado») |
| Serigrafía | Nombre y versión arriba; logo, pads y GPIO del J_EXP abajo; rótulos de TP, LED, botones y puentes arriba |
| BOM y CPL | `scripts/jlc_post.py`, con giros comprobados contra las huellas EasyEDA |
| Gerber, renders | Se generan con `scripts/make_fab.sh` cuando el DRC esté limpio |

## Capas

4 capas, 1,6 mm, apilado JLC04161H-7628:

| Capa | Uso |
|------|-----|
| F.Cu (L1) | Componentes, par USB (0,28 / 0,15 sobre el GND de L2) y señales |
| In1.Cu (L2) | Plano de GND entero (salvo la zona de la antena) |
| In2.Cu (L3) | Plano de VSYS: alimenta el 3,3 V, el elevador de 6 V y el amplificador con vías, sin pistas anchas |
| B.Cu (L4) | Señales y relleno de GND; sin vías bajo el logo |

Por qué 4 y no 2: el módulo, la cámara (12 señales DVP), el expansor y la potencia ocupan casi toda la cara superior, y media placa queda bajo la batería. Con 2 capas no quedaría un plano de GND continuo bajo el par USB ni bajo los lazos de los convertidores. En JLCPCB, 4 capas en 5 placas de este tamaño cuestan del orden de 10–20 USD más que 2.

## Estructura

| Ruta | Qué es |
|------|--------|
| `FurbyBoard.kicad_pro`, `.kicad_sch`, `hojas/` | Proyecto y esquema jerárquico (raíz + usb, alimentación, mcu, motor, audio, cámara, sensores, led_tp) |
| `FurbyBoard.kicad_pcb`, `.kicad_dru` | PCB y la única regla especial (pads de J1 junto a la ranura) |
| `lib/` | Símbolos y huellas propias (USB-C M-13C, FPC AFC01, TPS63802, SI7615ADN, pads de cable y de batería, logo) |
| `scripts/` | Todo se genera desde aquí (ver abajo) |
| `fabricacion/` | Gerber, BOM, CPL, informes y opciones de pedido |
| `render/` | Renders 3D y STEP |

## Regenerar

Con el Python de KiCad 10 (`KP=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`) y el `kicad-cli` de la app:

```sh
python3 scripts/gen_lib.py          # librería propia
python3 scripts/gen_sch.py          # esquema (luego: kicad-cli sch upgrade en cada hoja)
python3 scripts/gen_pro.py          # proyecto, clases de red y regla del USB-C
$KP scripts/gen_pcb.py --sin-rutado # PCB colocado, con el par USB y la serigrafía
$KP scripts/comprobar_colocacion.py # TP accesibles, calzos libres, alturas bajo la batería
$KP scripts/exportar_dsn.py         # DSN para Freerouting
```

Las piezas, redes y LCSC están en `scripts/design.py`; la colocación, en `scripts/layout.py` (coordenadas del STL de la base); los rótulos, en `scripts/serigrafia.py`.

## Rutado

El par USB va trazado a mano. El resto se autorruta con [Freerouting](https://github.com/freerouting/freerouting) sobre `scripts/rutado.dsn`, que ya lleva las clases de red (señal 0,2; 3,3 V 0,3; potencia 0,4), los planos de L2 y L3 como «power» y las zonas prohibidas (antena, logo):

```sh
java -jar freerouting-2.1.0.jar -de scripts/rutado.dsn -do scripts/rutado.ses -mp 100
$KP scripts/gen_pcb.py --rellenar    # importa scripts/rutado.ses y rellena los planos
kicad-cli pcb drc --schematic-parity --severity-all FurbyBoard.kicad_pcb
scripts/make_fab.sh
```

La v2.1.0 es la última que corre con Java 21; las 2.2 y siguientes piden Java 25.
