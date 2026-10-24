# FurbyBoard v1.0: ficheros y opciones de pedido en JLCPCB

Esta carpeta la llena `scripts/make_fab.sh`. **Nadie pide nada desde aquí:** el pedido lo hace Guillermo a mano en jlcpcb.com.

> **Estado (2026-10-24): falta el rutado.** El esquema (ERC 0/0), la colocación, la serigrafía, la BOM y el CPL están listos; el Gerber no se genera hasta que el PCB esté rutado y el DRC dé 0 errores, 0 avisos y paridad con el esquema. Ver «Rutado» en `../README.md`.

## Qué se sube

| Fichero | Dónde se sube | Qué es |
|---------|---------------|--------|
| `gerber-jlcpcb.zip` | «Add gerber file» | 4 capas de cobre, máscara, pasta, serigrafía, contorno y taladros (Excellon), con el origen en el (0,0) del STL de la base, el mismo que el CPL |
| `bom-jlcpcb.csv` | PCB Assembly → BOM | Una línea por valor, huella y LCSC (51 líneas, 124 piezas) |
| `cpl-jlcpcb.csv` | PCB Assembly → CPL | Posición y giro de cada pieza ya corregidos para las huellas EasyEDA de JLCPCB (`scripts/jlc_post.py`) |
| `erc.rpt`, `drc.rpt` | No se suben | Informes de ERC y DRC del momento en que se generaron los ficheros |
| `esquematico.pdf` | No se sube | Esquema para revisar |

## Opciones del formulario de PCB

| Opción | Valor | Por qué |
|--------|-------|---------|
| Base material | FR-4 | — |
| Layers | **4** | Plano de GND entero bajo el par USB y las señales, y plano de VSYS |
| Dimensions | Las lee del Gerber (≈ 68,9 × 74,6 mm) | — |
| PCB Qty | 5 | Mínimo de JLCPCB |
| Product type | Industrial/Consumer electronics | — |
| Different design | 1 | — |
| Delivery format | Single PCB | Sin panel: la placa tiene forma de suelo y lleva el USB-C en una ranura del borde |
| PCB thickness | **1,6 mm** | Obligatorio: el USB-C de montaje medio (HRO M-13C) es para PCB de 1,6, y la altura del eje en la base sale de ahí |
| Impedance control | **Sí, JLC04161H-7628** | Es el apilado con el que se calculó el par USB (0,28 / 0,15 mm, ≈ 87–89 Ω). A 12 Mbit/s no es crítico: si encarece mucho, «No» también vale |
| Layer sequence / stackup | JLC04161H-7628 | Ídem |
| PCB color | Verde (el más rápido) o negro (el logo blanco de la cara inferior luce más) | La placa no se ve con el Furby cerrado |
| Silkscreen | White | — |
| Surface finish | **ENIG** (1 U") | Pads planos para los QFN y WSON de 0,5 mm, el FPC de 0,5 y los pads de cable. HASL sin plomo funciona, pero es menos plano |
| Via covering | Tented | Las vías no llevan pads de prueba |
| Min via hole size/diameter | 0,3 / 0,6 mm | Sin sobrecoste |
| Board outline tolerance | ±0,2 mm (normal) | La holgura a la pared es de 1,0 mm (0,47 en las orejetas del USB-C) |
| Mark on PCB | «Remove mark» (si lo ofrece) | No hay sitio reservado para el número de pedido |
| Electrical test | Flying probe (incluido) | — |
| Gold fingers, castellated holes, edge plating | No | — |

## Opciones de montaje (PCB Assembly)

| Opción | Valor | Por qué |
|--------|-------|---------|
| PCBA type | **Economic** si el formulario lo admite con 4 capas y las piezas de la BOM; si no, **Standard** | Todo va por una cara y es SMD. Economic es más barato; Standard admite más tipos de pieza |
| Assembly side | **Top side** | La cara inferior solo lleva serigrafía y el logo |
| PCBA Qty | 2 o 5 | Con 2 se prueban y se reservan las otras 3 placas desnudas |
| Tooling holes | Added by JLCPCB | — |
| Confirm parts placement | **Yes** | Revisar en el visor el pin 1 de U1–U11, Q1–Q3 y la polaridad de D1–D5 antes de pagar (ver `scripts/jlc_post.py`) |
| Pads de cable, TP, puentes y taladros | No van en la BOM | Son cobre del PCB; los cables se sueldan a mano |

**A revisar en el visor de JLCPCB:**

- **J1 (USB-C HRO M-13C):** tiene cuatro patas pasantes en la carcasa. Si JLCPCB la marca como pieza pasante, el montaje Economic no la acepta: o se pasa a Standard, o se suelda a mano (se deja fuera de la BOM).
- **U4 (WROOM-1):** el CPL ya corrige el origen de la huella (3,6 mm hacia los pines). La antena tiene que quedar hacia el borde delantero, sobre la zona sin cobre.

## Coste estimado (5 PCB, montaje de 5)

**Estimado**, con los precios y el stock de la API de piezas de JLCPCB del 2026-10-24 (componentes) y tarifas típicas de JLCPCB (PCB y montaje). Lo que vale es lo que diga el formulario.

| Concepto | USD |
|----------|-----|
| 5 PCB de 4 capas, 1,6 mm, ENIG | ≈ 15–35 |
| Componentes (16,30 por placa × 5) | ≈ 82 |
| Carga de piezas «extended»: 20 referencias × 3 | ≈ 60 |
| Montaje: puesta en marcha, plantilla y juntas | ≈ 15–35 (Economic) o ≈ 35–60 (Standard) |
| **Total sin envío ni aranceles** | **≈ 170–235** (≈ 34–47 por placa) |

Lo que más pesa por placa: el WROOM-1-N16R8 (5,35), los 11 condensadores de 22 µF (2,10), DRV8231A, TCA9535 y MAX98357A (≈ 1,33 cada uno). Con montaje de solo 2 placas, los componentes bajan a ≈ 33 y el total a ≈ 125–190.

Piezas con poco stock en JLCPCB el 2026-10-24 (pedir pronto o tener alternativa): J1 USB-C (2 206), L1 0,47 µH (2 359), TCA9535 (7 294), DRV8231A (8 895), 74LVC1G17 (9 740).
