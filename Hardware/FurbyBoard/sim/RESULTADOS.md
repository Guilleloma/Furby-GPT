# Simulaciones (ngspice)

Modelos de comportamiento declarados: no hay modelos SPICE de los chips de la placa (TI, Maxim, Microne) que acepte ngspice, así que cada bloque se simula con un modelo que reproduce solo lo que dice su hoja de datos y declara lo que se supone. Los modelos compartidos están en `models/furby.lib`; cada `.cir` lleva en su cabecera los supuestos, las fuentes y los criterios. Las cifras se contrastan con los máximos del datasheet y se vuelven a medir en el bring-up (`TEST-PLAN.md`): **la simulación no sustituye a la medida**.

## Cómo se ejecuta

Desde `sim/`:

```sh
python3 -I analiza.py            # todos los bloques; o p. ej. «analiza.py tps63802»
ngspice -b tps63802_3v3.cir      # un circuito suelto (medidas en la consola)
```

`analiza.py` lanza cada `.cir`, recoge las medidas, aplica los criterios, imprime las tablas de abajo y dibuja las formas de onda en `png/`. Los datos crudos quedan en `datos/` (fuera de git). Necesita ngspice y Python con numpy y matplotlib. `ruta_r.py` calcula la resistencia de pistas y vías de una red entre dos pads a partir del `.kicad_pcb` (entrada de las simulaciones de 3V3 y VSYS).

Convenciones: «peor caso» = tolerancias, DC bias de los cerámicos y tensión de entrada en su extremo desfavorable a la vez. Capacidades efectivas de los MLCC estimadas (curvas típicas de DC bias de X5R en 0603/0805): **22 µF 25 V 0805 (C45783) ≈ 13 µF a 3,3 V, ≈ 12 µF a 4,4 V, ≈ 13 µF a 6 V por pieza en el cálculo del elevador; 10 µF 10 V 0603 (C19702) ≈ 5 µF a 3–4,4 V; 1 µF 50 V 0603 ≈ 0,8 µF**; −20 % de tolerancia encima en el peor caso. Verificar con la herramienta del fabricante (Samsung o Murata) si alguna conclusión queda justa.

## Resumen

| Bloque | Fichero | Resultado |
|--------|---------|-----------|
| Elevador de 6 V (TPS61089) | `elevador_6v.cir` | PASS (Isat de L2 por verificar) |
| 3V3 (TPS63802) | `tps63802_3v3.cir`, `tps63802_rizado.cir` | PASS |

## Elevador de 6 V (TPS61089 + FHD4020S-1R0MT) — `elevador_6v.cir`

Peor caso: Vin 3,0 V (batería agotada), carga 1,0 A (ITRIP del motor), L −20 % (0,8 µH), Cout 4 × 22 µF con DC bias a 6 V (≈ 53 µF), fSW 0,96 MHz.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Corriente de pico en la bobina | **2,82 A** | < ILIM 3,8 A (RILIM 270 kΩ) con margen ≥ 20 % | PASS (margen 26 %) |
| Corriente media de entrada | 1,86 A | Coherente con el presupuesto (2,0 A a 3,3 V en `ARQUITECTURA.md` §11) | PASS |
| Rizado de la bobina (pico a pico) | 1,94 A | Informativo: fija el Isat necesario ≥ 2,82 A · 1,2 ≈ 3,4 A | **Isat de la FHD4020S-1R0MT por verificar en su hoja de datos antes del pedido** |
| Rizado de salida | 19 mV pico a pico | < 1 % de 5,94 V (59 mV) | PASS |
| Tensión media (lazo abierto, D fijo) | 5,54 V | Solo informativo: sin el lazo cerrado la salida cae con las pérdidas; el regulador la mantiene en 5,94 V | — |

## 3V3 (TPS63802) — `tps63802_3v3.cir`, `tps63802_rizado.cir`

Supuestos:

- **Lazo**: la compensación del TPS63802 es interna y no está publicada. Modelo promediado (`TPS63802_AVG`) con un PI de transconductancia (GT = 7,5 A/V, cero a 15 kHz) y un retardo del lazo de corriente de 0,8 µs, **calibrado contra la figura 10-22 del datasheet** (VI 3,3 V, escalón de 0,1 a 1 A, un 22 µF de 6,3 V en 0603 ≈ 11 µF efectivos): el modelo da 120 mV, lo que se lee en la figura. La lectura de la figura es aproximada, por eso el peor caso usa GT a la mitad.
- **Pista de 3V3** de C7/C8 a C9 (módulo): 58 mΩ (68 mΩ hasta el pin 2 de U4) medidos con `ruta_r.py` sobre el rutado actual, y 12 nH estimados. Cambia si se rehace el rutado de 3V3.
- **VSYS**: batería agotada a 3,0 V con 0,25 Ω (celda y PCM), Q1 y el BAT-FET del BQ24073 al máximo (0,1 Ω).
- **Carga**: 0,1 A de base y escalón a 0,55 A en 1 µs (TX 802.11b a 21 dBm, 340 mA de pico según la tabla 5-7 del datasheet del ESP32-S3, más cámara y lógica).
- **Rizado**: etapa de potencia idealizada en lazo abierto en los dos extremos (buck a 4,4 V y 1,6 MHz; boost a 3,0 V y 2,1 MHz; frecuencias de la tabla 8.5), con L −20 %, C −20 % tras DC bias y medida con 20 MHz de ancho de banda. La zona de transición buck-boost y el modo PFM (MODE a GND) no se modelan: se miden en el bring-up.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Calibración: caída con 0,1 → 1 A, VI 3,3 V, 22 µF nominales | 120 mV | ≈ 120 mV leídos en la figura 10-22 | — |
| 3V3 en el módulo con 0,1 → 0,55 A, batería 3,0 V (nominal) | mín. 3,23 V (caída 67 mV) | ≥ 3,00 V | PASS |
| 3V3 en el módulo, peor caso (C −20 %, GT/2) | mín. 3,20 V | ≥ 3,00 V | PASS |
| 3V3 en el módulo con 0,55 A en régimen (caída de la pista de 58 mΩ) | 3,270 V | 3,30 V ± 3 % (3,20–3,40) | PASS |
| VSYS en la entrada de U3 con 0,55 A, batería 3,0 V | mín. 2,69 V | ≥ 2,3 V (VIN;LOAD para 2 A) | PASS |
| Desenchufe del USB (4,4 → 3,0 V en 10 µs, 0,55 A) | VSYS mín. 2,69 V; 3V3 3,27 V | VSYS ≥ 2,3 V; el modelo promediado no tiene paso de línea: la figura 10-28 da < 0,1 V con 2,2 → 4,2 V en 1 µs | PASS |
| Pico de L1, buck (VSYS 4,4 V, 0,7 A, L −20 %) | 1,37 A | < 3,8 A con margen ≥ 20 % | PASS |
| Pico de L1, boost (VSYS 3,0 V, 0,7 A, L −20 %) | 1,09 A | < 4,0 A (mín.) con margen ≥ 20 % | PASS |
| Rizado de 3V3 en C7/C8, buck / boost (20 MHz) | 5,5 / 9,8 mV pp | ≤ 33 mV pp (1 %) | PASS |
| Rizado de 3V3 en el módulo (C9), buck / boost | 0,4 / 0,3 mV pp | ≤ 33 mV pp | PASS |

Observaciones:

- La caída de régimen en el módulo (≈ 30 mV con 0,55 A) es de la pista de 3V3, no del regulador. Con 3,27 V queda margen de sobra frente a los 3,0 V del ESP32-S3; si el rutado definitivo alarga o estrecha el tronco de 3V3, se repite `ruta_r.py` y esta simulación.
- C6 (10 µF 10 V 0603) da ≈ 5 µF efectivos a 4,4 V y ≈ 4 µF en el peor caso, justo el mínimo de 4 µF efectivos de la tabla 8.3. No cambia la simulación (VSYS tiene ≈ 58 µF más en la red), pero un 10 µF de 16 V o en 0805 daría margen. Mejora, no bloqueo.

Figuras: `png/tps63802_escalon.png` (escalón de carga, nominal y peor caso), `png/tps63802_rizado.png` (rizado y corriente de L1).

## Lo que no se simula y por qué

- **TPS63802 (3,3 V):** el modo PFM y la zona de transición buck-boost (control propietario); se miden en el bring-up.
- **Polaridad inversa con USB (P-MOSFET + BQ24073):** depende de la detección de cortocircuito del cargador (4–11 mA, datasheet SLUS810); análisis en `ARQUITECTURA.md` §7.1 y prueba obligatoria en el bring-up con fuente limitada, sin y con USB.
- **Compensación del TPS61089:** valores de la nota de aplicación del datasheet (R24 30 kΩ, C14 4,7 nF, C15 10 pF); se mide el escalón de carga en el bring-up.
