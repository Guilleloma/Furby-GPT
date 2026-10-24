# FurbyBoard: notas de diseño (fase 2)

Decisiones y cálculos del esquema y el PCB. La arquitectura (componentes, presupuesto de potencia, GPIO) está en `../PCB-suelo/ARQUITECTURA.md`; aquí va lo que se decidió al hacer el layout.

## 4 capas y no 2

| Criterio | 2 capas | 4 capas (elegida) |
|----------|---------|-------------------|
| Redes | ≈ 150 redes y 340 conexiones en 4 100 mm², con media placa bajo la batería y la cara superior llena | Las señales tienen F.Cu y B.Cu enteras; GND y VSYS no gastan pistas |
| Retorno de corriente | El plano de GND de B.Cu queda troceado por las pistas: lazos grandes en los convertidores y en el par USB | Plano de GND continuo en L2, a 0,21 mm de las pistas de L1 |
| Par USB | ≈ 90 Ω pide pistas de ≈ 0,9 mm sobre 1,5 mm de FR-4 (no caben en los pads del ESD ni del conector) | 0,28 / 0,15 mm sobre L2 da ≈ 87–89 Ω |
| Convertidores (3, a ≈ 1 MHz) y clase D | Rizado y EMI peores; el lazo de entrada del elevador cruza señales | Lazos cortos sobre GND; L3 como capa de señal con relleno de VSYS |
| Antena | Igual (zona sin cobre en todas las capas) | Igual |
| Coste en JLCPCB, 5 placas de 69 × 75 mm | Base | Del orden de 5–15 USD más en total (estimado; mandan las tarifas del día). Frente a ≈ 170–235 USD del pedido montado, es menos de un 10 % |

Con 2 capas la placa probablemente se podría rutar, pero a costa del plano de masa, que es lo que protege el WiFi, la cámara (XCLK a 20 MHz, PCLK) y el USB del ruido de tres convertidores conmutados y del puente H. Para un prototipo de pocas unidades no compensa.

Apilado JLC04161H-7628: L1–L2 con prepreg 7628 de 0,2104 mm (εr ≈ 4,4), núcleo de ≈ 1,065 mm entre L2 y L3, cobre exterior de 1 oz.

## Par USB

Microstrip acoplado sobre L2 (IPC-2141): h = 0,2104, w = 0,28, t = 0,035, εr = 4,4.

- Z0 = 87 / √(εr + 1,41) · ln(5,98 h / (0,8 w + t)) = 36,1 · ln(1,258 / 0,259) = 36,1 · 1,580 ≈ 57 Ω
- Zdiff = 2 Z0 (1 − 0,48 e^(−0,96 s/h)) = 114,2 · (1 − 0,48 · e^(−0,684)) ≈ 87 Ω con s = 0,15

Dentro del ±10 % de 90 Ω (estimado; la calculadora de JLCPCB da el valor del apilado real). A 12 Mbit/s (USB FS) el margen es enorme: el tramo de 4 mm a 0,20 entre los pads del conector y el ESD no se nota. Trazado a mano en `scripts/rutas_fijas.py`, por F.Cu y sin vías, con la cara B del conector unida dentro del USBLC6 (pines 1-6 y 3-4).

## Potencia

- **VSYS:** L3 empezó como plano de VSYS; desde 44bb6cc es capa de señal con relleno de VSYS en lo libre, y VSYS va además por pistas de 0,6 mm pre-rutadas (≈ 2,3 A de pico en la entrada del elevador: el relleno de L3 aporta la sección que falta).
- **Pistas de potencia:** se autorrutan a 0,4 mm, lo más ancho que entra en los pads de 0,5 de paso de los QFN sin invadir el margen del pad vecino (0,5 − 0,2 − 0,14 = 0,16 ≥ 0,15). Luego `scripts/ensanchar_potencia.py` las lleva a 0,8, 0,6 o 0,5 donde el DRC lo permite. 0,4 mm en 1 oz exterior aguanta ≈ 1,3 A con 10 °C de subida; el motor está limitado a 1,0 A (ITRIP).
- **Vías a los planos:** una vía de 0,3 mm aguanta del orden de 1 A. En los pads de los convertidores, el cargador y el amplificador `scripts/vias_extra.py` añade hasta 2 vías más por pad, donde pasan el DRC.

## Rutado

Freerouting **v1.9.0** (release oficial de github.com/freerouting/freerouting, 2023-10-30), con el temurin-21 de este Mac. Se probó antes la v2.1.0 (2025-04-12, la última que corre con Java 21; las 2.2 y siguientes piden Java 25), pero en modo sin interfaz no respeta el límite de pasadas (`-mp`) ni el tiempo máximo, y no escribe el SES hasta rutarlo todo: con conexiones pendientes no acaba nunca. La 1.9.0 respeta `-mp` y escribe el SES; abre su ventana mientras ruta. Ninguna de las dos releases publica checksum: se comprobó el tamaño de cada `.jar` contra la API de GitHub (1.9.0: 5 044 336 bytes). Se ejecutó desde el scratchpad, sin instalar nada y con la red cortada al proceso (proxy a 127.0.0.1:9 y `-da`) para que no envíe telemetría. El `.jar` no va al repositorio.

Freerouting no conoce el margen a borde de KiCad (0,3 mm) y usa el margen general (0,15): `exportar_dsn.py` le añade una franja prohibida de 0,32 mm a lo largo del contorno y del agujero del mecanismo, solo en el DSN.

Orden:

1. `gen_pcb.py --sin-rutado` y `exportar_dsn.py`: DSN con el par USB bloqueado, L2 y L3 como planos y las zonas prohibidas (antena en todas las capas, vías bajo el logo).
2. Freerouting sobre `scripts/rutado.dsn` → `scripts/rutado.ses`.
3. `gen_pcb.py` (importa el SES), `vias_extra.py`, `ensanchar_potencia.py` (rellena los planos al acabar).
4. DRC sin `--refill-zones`, con paridad: 0 errores y 0 avisos.

## Serigrafía

- Los rótulos los coloca `scripts/serigrafia.py` sin pisar pads, cuerpos ni otra serigrafía. Si un rótulo no cabe, no se pone (manda el diseño): pasa con el de JP1 arriba, que sí está abajo.
- Para que cupieran se reordenaron los LED (fila con el rótulo encima), los botones (en vertical, rótulo debajo) y los TP (rejilla con el rótulo debajo), y se quitaron 5 TP redundantes (EN, IO0, CHG, PGOOD y un GND).

## Fabricación

- BOM y CPL: `scripts/jlc_post.py`, con el giro y el origen de cada pieza comparados pad a pad con su huella EasyEDA. Los LED van a 0°: EasyEDA numera el cátodo como pad 2, pero está en el mismo lado que el pad 1 de KiCad.
- Gerber y CPL con el mismo origen: el (0,0) del STL de la base, como origen auxiliar.

## Estado al pausar (2026-10-24)

La placa queda **pausada** por decisión de Guillermo hasta que existan las skills de electrónica (layout, KiCad, JLCPCB, pruebas y revisión) y `pcb-toolkit` (revisar-rutado y comprobar-flujo). Se retomará con el modelo frontera. **El PCB no está terminado: no se puede fabricar.**

### Hecho, por commit (rama `feature/electronica-v1`, sin push)

| Commit | Qué |
|--------|-----|
| 7ccbb60, 700514f, 1c848e4 | Contorno con holgura de 1,0, H3/H4 nuevos, USB-C de 16 pines con saliente de 0,70 y orejetas para sus patas delanteras (`../PCB-suelo/geometria.json`, `interfaz-base.md`) |
| b6c2e31, 841edd3, 86cc50f | Piezas, redes y LCSC (`scripts/design.py`), librería propia y esquema jerárquico de 8 hojas. ERC 0/0 |
| 44bb6cc | GPIO reasignados: cámara en los pines del lado del FPC (fila inferior derecha y columna derecha del módulo), I2S y sensores a la izquierda, MOT_IN1 en GPIO9. Sin tocar strapping ni USB. L3 pasa a capa de señal con relleno de VSYS |
| 6fa3d1f, 5460fd5, 5e1d428 | Colocación: elevador de 6 V fuera del pasillo módulo–FPC (abajo a la derecha, entre cargador y puente H), cargador reordenado, amplificador junto al I2S y a J8, pasillos de vías en las columnas del expansor, TP junto a su fuente en la cara inferior. PNG en `render/colocacion-arriba.png` y `render/colocacion-abajo.png` |
| b54457e | Par USB trazado a mano (`scripts/rutas_fijas.py`) y serigrafía con rótulos automáticos (`scripts/serigrafia.py`) |
| 97b63e5 | BOM y CPL de JLCPCB con giros comprobados (`scripts/jlc_post.py`, `scripts/make_fab.sh`) |
| 489be3e | `TEST-PLAN.md`, `README.md`, `fabricacion/README.md`. **El TEST-PLAN está desfasado**: TP renumerados (14), TP en la cara inferior y GPIO reasignados después |
| 9d867eb | Modelos 3D simplificados (USB-C, FPC, bobinas) |
| cba8892 | Logo con expresión neutra |
| 335b384 | Lo crítico pre-rutado y fijado: lazos del TPS61089, del TPS63802 y del puente H, potencia, bajadas de GND y vías térmicas bajo los pads expuestos |
| d28aea4 | Una ejecución de Freerouting 1.9.0 (-mp 20) importada y limpiada |
| 249bbbf, 9d42d8b (y el commit de este traspaso) | Remate por rejilla de lo pendiente: de 30 a 15 pads sin unir. **Último estado del PCB**. Detalle en «Remate R5» |

### Remate R5 (2026-10-24, límite de 60 min alcanzado sin llegar a 0)

**Resultado** (DRC sin `--refill-zones`, con paridad, en `FurbyBoard.kicad_pcb`):

| | d28aea4 | Tras R5 |
|---|---|---|
| Pads sin unir | 30 | **15** |
| Pistas de In2 a < 0,3 mm del borde | 7 | 0 |
| Puntas colgando | 23 | 0 |
| Vías colgando | 2 | 2 (IR_RX: medio camino de una conexión pendiente) |
| Ángulos agudos / fuera de 0-45-90° (`limpiar.py`) | 10 / 1 | 0 / 0 |
| Paridad con el esquema | 0 | 0 |
| `pcb-toolkit revisar-rutado` | FAIL, 583 errores, 591 avisos | FAIL, **318 errores**, 607 avisos |

**Faltan 15 pads**, mapa en `render/rutado-pendiente.png`:

- **Elevador U5**: BST_VCC (U5.2–C12), BST_COMP (U5.4), VSYS (U5.9 y un tramo B–F junto a C17).
- **USB-C J1**: CC1 (R1–A5), CC2 (B5–R2) y **USB_DN**. Lo de USB_DN viene de antes: el cuello de B7 y el de A7 nunca se unen, porque el pad A6 de DP queda entre ellos. Hace falta cruzar por B.Cu con dos vías, y con vías de 0,6 no caben entre el cuello de DP en F y su tramo en B. Requiere la opción A (vías de 0,45/0,2) o rehacer el cruce del par. Es **crítico**: sin esto no hay USB por una de las dos orientaciones del conector.
- **Amplificador U7**: AMP_SD (U7.4–U10.16), I2S_BCLK (U7.16).
- **Puente H U6**: MOT_IN1 (U6.3), MOT_OUT2 (U6.8).
- **Cámara J6**: CAM_Y7 (U4.23–J6.16), CAM_Y8 (J6.14).
- **Otros**: IR_RX (R56–U4), GND (vía–U4.40).

**Qué se hizo**:

1. El cuello de DP en J1 pasa de oblicuo a 45° + vertical (`rutas_fijas.py`), sin mover la vía, así que el tramo acoplado del par queda igual.
2. Las pistas de In2 junto al borde, los tramos de los ángulos agudos y las puntas colgando se quitan (`router/rematar_prep.py`), y lo que queda suelto pasa a la lista de pendientes.
3. El rutador por rejilla une **solo los pares que da el DRC de KiCad** (`rutar.py --remate`): todo lo demás es obstáculo fijo y el post-proceso es el mismo (0/45/90°, entradas centradas). Además, las vías se mantienen a 0,6 mm o más de los pads que aún tienen que salir, y si un par no sale se levanta lo rutado en el remate junto a sus pads y se reruta (dos intentos).
4. Con eso los pines de U5, U2, U7 y U6 seguían encerrados, así que **se limpió el cobre alrededor** de esos cuatro integrados (1,2 mm) y se volvió a rutar. Se excluyeron de la limpieza BST_SW, el par USB y las vías de GND bloqueadas. Después se hicieron vueltas de levantar el cobre no fijo que encerraba los pads que fallaban (`router/rematar_levantar.py`, sin tocar redes de potencia).
5. **TP13 (GND) se movió** de (−53,6; −109,7) a (−53,4; −105,7) junto con su vía, porque tapaba la salida de U5.2-U5.4. También se quitó una vía de GND que estaba bloqueada en (−53,6; −110,7).

**Avisos para la revisión independiente**:

- **Rehechos por rejilla en R5**: el lazo de entrada y control del TPS61089, el cargador y el VSYS de U7 (tramos de 0,6 cortos con «bolas», en `render/remate-zona-amplificador.png`). **Revisar a mano** los lazos contra el datasheet.
- `revisar-rutado` marca:
  - 45 vías en pad. Unas 30 están previstas: 14 TP sobre vía y 16 vías térmicas. **El resto son nuevas** y hay que sacarlas.
  - 150 segmentos cortos, 61 solapes y 30 escaleras. Bajan respecto a d28aea4 (149, 86 y 11), salvo las escaleras, que **suben**: son de la rejilla.
  - 26 ángulos agudos de 45° en uniones en T. `limpiar.py` no los ve: solo mide ángulos entre tramos consecutivos.
  - Informe completo: `pcb-toolkit revisar-rutado FurbyBoard.kicad_pcb --json -`.
- `TEST-PLAN.md` sigue desfasado: TP renumerados y en la cara inferior, GPIO reasignados y TP13 movido.
- `exportar_dsn.py` sigue sin la franja de borde en In2. No afecta mientras no se use Freerouting.

### Diagnóstico

- (Antes de R5) Faltaban **30 pads (≈ 25 conexiones)**, repartidas: USB-C (CC2) y cargador (PGOOD, CHG, VBUS); puente H (MOT_IN1/2, MOT_OUT1) y J9 (TUMMY, HOME); amplificador (SPK_P, I2S_DOUT, I2S_BCLK); expansor (LED_RUN_K, TILT_B); IR_RX; y 3 GND (J6 y módulo). Mapa: `render/rutado-pendiente.png`.
- DRC de d28aea4, sin contar lo no rutado: 7 pistas de In2 a menos de 0,3 mm del borde (la franja prohibida del DSN solo cubría F.Cu y B.Cu) y 23 puntas colgando. 10 ángulos agudos y un tramo fuera de 45° (el estrechamiento del par USB en J1, `rutas_fijas.py`).
- **Puntos calientes:** el agujero del mecanismo parte la mitad derecha; media placa queda bajo la batería (piezas de ≤ 2,1 mm); el expansor y su acondicionamiento quedan lejos del módulo y de los pads de cable a los que van (J8, J9), así que hay muchos cruces largos; la zona del USB-C y el cargador está densa.
- **Causas:** colocación de la mitad izquierda (expansor y sensores) y recursos de rutado: con vías de 0,6/0,3 y señal a 0,2/0,15 las tres capas de señal se llenan.

### Opciones

- **A (recomendada)**: reglas más finas dentro de lo estándar de JLCPCB para 4 capas: vías de 0,45/0,2 (sin sobrecoste según su web) y señal a 0,15 con margen de 0,127. La potencia no cambia.
- **B (recomendada, con A)**: reorganizar la mitad izquierda: girar el TCA9535 hacia el módulo, reasignar sus pines al orden de los pads de cable y poner cada red RC junto a su pad (J8/J9).
- **C**: simplificar un bloque (LDO y control de la cámara al propio módulo de cámara; quitar IR y LDR). Lo decide Guillermo.
- **D**: 6 capas, solo si A + B no bastan (≈ 30–60 USD más en 5 placas, estimado).
- **E**: negociación de congestión en el rutador propio. **Descartada** por las reglas nuevas.

### Scripts (en `scripts/`)

| Script | Qué hace | Python |
|--------|----------|--------|
| `design.py`, `params.py` | Piezas, redes, LCSC, GPIO; reglas y apilado | — |
| `gen_lib.py`, `gen_sch.py`, `gen_pro.py` | Librería propia, esquema jerárquico y proyecto (clases de red, regla de J1) | sistema |
| `gen_modelos3d.py` | Modelos STEP simplificados | FreeCAD |
| `layout.py` | Colocación en coordenadas del STL | — |
| `gen_pcb.py` | PCB: contorno, colocación, rutas fijas del USB, zonas, serigrafía | KiCad |
| `serigrafia.py` | Rótulos y su colocación automática | — |
| `rutas_fijas.py` | Par USB trazado a mano | — |
| `comprobar_colocacion.py` | TP y LED fuera de la batería, calzos libres, alturas bajo la batería | KiCad |
| `exportar_dsn.py` | DSN para Freerouting (sin el relleno de L3, con franja de borde en F/B; **falta añadir In2 a la franja**) | KiCad |
| `router/preparar.sh` | Encadena gen_pcb, TP, vías térmicas, pre-rutado fijado y DSN | KiCad + numpy |
| `router/extraer.py` | Geometría del PCB para el rutador por rejilla | KiCad |
| `router/rutar.py`, `router/astar.c` | Rutador por rejilla con post-proceso (0/45/90, entradas a pad centradas), TP junto a su fuente (`--solo-tp`) y levantar y rerutar | numpy |
| `router/aplicar.py` | Añade al PCB lo calculado (`--fijar` lo bloquea, `--rellenos` añade GND en F/B), rótulos de TP | KiCad |
| `router/prerrutado.json` | Redes y anchos del pre-rutado de potencia | — |
| `router/vias_termicas.py` | Vías bajo los pads expuestos de U2, U7, U6 y U4 | KiCad |
| `router/limpiar.py` | Limpieza tras importar el SES: une colineales, quita repetidos y puntas, informa de ángulos | KiCad |
| `router/rematar_prep.py` | Remate: cuello de DP, quita In2 junto al borde, agudos y puntas; lista de pares pendientes del DRC | KiCad |
| `router/rematar_levantar.py` | Remate: levanta el cobre que encierra los pads que fallan, o todo el de una caja (`--caja`) | KiCad |
| `ensanchar_potencia.py`, `vias_extra.py` | Ensanchar pistas de potencia y añadir vías a los planos donde el DRC lo permita. **Escritos, no probados** | KiCad |
| `render_montaje.py` | Render de la placa sobre la base simplificada con la batería (Blender) | KiCad + Blender |
| `jlc_post.py`, `make_fab.sh` | BOM y CPL de JLCPCB y ficheros de fabricación | sistema |

### Qué descartar del rutador propio

Las reglas nuevas prohíben un autorrutador propio sin autorización y solo admiten el rutado por rejilla como remate con post-proceso. Por tanto:

- **Descartar como autorrutador** `router/rutar.py` en modo completo (todas las redes, `--vueltas`, `levantar_y_rerutar`): fue lo que dio el rutado que no gustó.
- **Se puede conservar como herramienta de remate**, siempre con su post-proceso: el pre-rutado de redes concretas con `--orden` y `--anchos`, y `--solo-tp`. También `limpiar.py`, `vias_termicas.py`, `extraer.py` y `aplicar.py`.
- El pre-rutado de potencia de 335b384 lo generó ese rutador: **revisarlo a mano** (lazos según el datasheet) antes de darlo por bueno.

### Posible fallo de las líneas naranjas de `congestion.png`

Comprobado: **no hay ninguna huella fuera del contorno ni en (0,0)**. Las líneas naranjas son conexiones de GND que el DRC informa contra la «Zona [GND] en F.Cu», y KiCad da como posición de una zona su primer vértice: la esquina del rectángulo de los rellenos, que está 1 mm fuera de la caja de la placa (x 111,08, y 88,79 en KiCad; (−108,9; −128,8) en el STL). El dibujo del PNG unía el pad con ese vértice. Lo real es que esos pads de GND (C25, C24, C26, R53, C40, U8, J6…) no tenían todavía vía al plano ni unión con el relleno de F.Cu.
