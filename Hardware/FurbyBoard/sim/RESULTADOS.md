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
| Batería y Q1 | `bateria_q1.cir` | PASS (con USB y batería al revés, en la esquina mala el BQ entra en precarga: 0,32 W en Q1) |
| Power path (BQ24073) | `bq24073_powerpath.cir` | **2 FAIL** (pico de 2,9 A con USB en USB500 en el peor caso; enchufe con ≥ 4,3 W en modo ILIM): propuestas de firmware |

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

## Power path (BQ24073, Q1 y batería) — `bq24073_powerpath.cir`

Supuestos:

- **Modelo `BQ24073_PP`** con lo que da la tabla 8.5 del datasheet (SLUS810N): OUT regulado a 4,4 V con límite de entrada (USB500 0,475 A; ILIM 1,25–1,43 A con RILIM 1,2 kΩ), VIN-DPM 4,5 V, DPPM a VO(REG) − 100 mV, supplement a VBAT − 40 mV, BAT-FET de 50 mΩ típ. y 100 mΩ máx. (VDO(BAT-OUT) 50/100 mV a 1 A), validación de la entrada a los 1,2 ms y consumo de IN de 1,5 mA. **El retardo de entrada en supplement no está en la hoja**: se usan 5 µs y 50 µs (la figura 10-6 lo muestra por debajo de la resolución de 1 ms/div).
- **Cargas de VSYS como potencia constante** (convertidores): elevador + motor bloqueado 6,6 W, amplificador 1,6 W (limitador a −6 dBFS), 3V3 con 0,55 A a través del modelo del TPS63802: **2,9–3,3 A a 3,1–2,9 V**, el pico simultáneo de `ARQUITECTURA.md` §11.
- Batería 3,7 V (media) o 3,4 V (baja) con 0,15 Ω; Q1 con el modelo EKV (`SI7615`); cable USB de 1 m (0,15 Ω, 1 µH); PTC en frío 0,08 Ω; capacidades efectivas tras DC bias.
- `VO(SC2)` (cortocircuito en supplement: VBAT − VOUT > 200–300 mV durante 250 µs apaga OUT 60 ms) no se modela como apagado: `analiza.py` mide el tramo continuo más largo por encima de 200 mV.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Pico de 2,9 A con USB (USB500, BAT-FET típ. (50 mΩ)): VBAT − VSYS en régimen | 142 mV (> 200 mV durante 0 µs seguidos) | < 200 mV (VO(SC2) mín.) o > 200 mV menos de 250 µs | PASS |
| Pico de 2,9 A con USB (USB500, BAT-FET máx. (100 mΩ)): VBAT − VSYS en régimen | 308 mV (> 200 mV durante 19968 µs seguidos) | < 200 mV (VO(SC2) mín.) o > 200 mV menos de 250 µs | **FAIL** |
| Pico de 2,9 A con USB (modo ILIM, BAT-FET máx. (100 mΩ)): VBAT − VSYS en régimen | 198 mV (> 200 mV durante 0 µs seguidos) | < 200 mV (VO(SC2) mín.) o > 200 mV menos de 250 µs | PASS |
| VSYS mín. en supplement (USB500, BAT-FET máx.) | 2,88 V | ≥ 2,5 V | PASS |
| 3V3 mín. durante el pico | 3,26 V | ≥ 3,0 V | PASS |
| Desenchufe con 1,15 A (batería 3,4 V), retardo de supplement 5 µs | VSYS 4,24 → mín. 2,95 V; VBAT − VSYS máx. 170 mV durante 0 µs | VSYS ≥ 2,5 V; sin VO(SC2) (≥ 250 µs) | PASS |
| Desenchufe con 1,15 A (batería 3,4 V), retardo de supplement 50 µs | VSYS 4,24 → mín. 2,81 V; VBAT − VSYS máx. 309 mV durante 104 µs | VSYS ≥ 2,5 V; sin VO(SC2) (≥ 250 µs) | PASS |
| Enchufe en caliente (cable 1 m, 1 µH): pico de VBUS | 6,06 V | < 6,4 V (OVP mín.) y < 28 V (máx. absoluto) | PASS |
| Enchufe con 5 W de carga (modo ILIM): VSYS final y disipación de U2 | VSYS se queda en 3,30 V (supplement); U2 disipa 1,76 W → Tj ≈ 128 °C | Tj ≤ 110 °C con Ta 50 °C (θJA 44,5 °C/W) | **FAIL** |
| Disipación de U2 durante el pico en USB500 (LDO + BAT-FET, 20 ms) | 1,89 W (en régimen daría Tj ≈ 134 °C) | Informativo: es un pulso; el firmware no debe sostenerlo (bloqueo ≤ 150 ms) | — |

Observaciones y propuestas:

- **FAIL 1 — pico de 2,9 A con el USB enchufado en USB500 y el BAT-FET en su máximo.** La batería aporta ≈ 3 A por el BAT-FET y VBAT − VSYS queda en 308 mV, por encima de VO(SC2) (200–300 mV) mientras dure el pico: **OUT se apagaría 60 ms y la placa se reiniciaría.** Con el BAT-FET típico (50 mΩ) quedan 142 mV y pasa; el máximo de 100 mΩ es para todo el rango de Tj (0–125 °C), así que el fallo es probable con la placa caliente. El firmware arranca y se queda en USB500 por la restricción B8 (PTC de 1,5 A). Propuestas, sin cambiar el esquema de la v1.0:
  1. **Firmware (recomendada):** con USB presente (PGOOD a 0 en el TCA9535), limitar la carga simultánea de VSYS a ≈ 2,0 A, de modo que la batería aporte ≤ 1,6 A (≤ 160 mV con 100 mΩ, 20 % de margen): motor con PWM ≤ 50 % en decaimiento lento (con el motor bloqueado, la corriente de V6 solo circula en el tiempo encendido: ≈ 1,1 A en VSYS) y el audio a −12 dBFS mientras se mueve el motor. La detección de bloqueo por el encoder (150 ms) llega tarde frente a los 250 µs de VO(SC2): el límite tiene que estar puesto antes.
  2. Modo ILIM (1,34 A) con USB: deja 198 mV en el peor caso, **sin margen**, y exige el PTC de 2 A de la v1.1 (B8). No se recomienda como única medida.
  3. v1.1, si la medida lo confirma: ITRIP más bajo (R26 de 4,7 kΩ a 6,8 kΩ → 0,87 A; resta ≈ 0,3 A al pico) o un cargador conmutado con power path.
  - **Medida en el bring-up (propuesta de paso para TEST-PLAN §8.3):** USB enchufado en USB500, motor bloqueado + TX + audio al máximo durante 1 s; medir VBAT (TP4) − VSYS (TP5) con el osciloscopio en modo diferencial (dos canales) y comprobar que no hay reinicio. PASS: < 150 mV y sin reinicio.
- **FAIL 2 — enchufar el USB con ≥ ≈ 4,3 W de carga en modo ILIM.** Con cargas de potencia constante el power path lineal es biestable: al enchufar con la batería a 3,4 V y 5 W de carga, VSYS no sube a 4,4 V (a 3,3 V el BQ solo entrega 1,25 A × 3,3 V = 4,1 W) y se queda en supplement: la batería sigue descargándose y U2 disipa 1,76 W (Tj ≈ 128 °C con Ta 50 °C): entra en regulación térmica y, si sigue subiendo, en el «hiccup» de TJ(OFF) (sección 9.3.5.8). No rompe nada, pero no carga. En USB500 el umbral es ≈ 1,6 W (0,475 A × VBAT): con el WiFi activo la placa enchufada tampoco carga hasta que baje el consumo, aunque ahí U2 no pasa de ≈ 0,75 W. **Propuesta (firmware):** al detectar el flanco de PGOOD, pausar motor y audio ≈ 5 ms para que VSYS suba a 4,4 V; una vez arriba, el punto de 4,4 V es estable mientras la carga sea < ILIM × 4,4 V (2,1 W en USB500; 5,9 W en ILIM).
- El desenchufe es limpio incluso con 50 µs de retardo de supplement (VSYS mín. 2,81 V, 104 µs por encima de 200 mV, menos de los 250 µs de VO(SC2)) y 3V3 no se entera (el modelo promediado del TPS63802 no tiene paso de línea; la figura 10-28 del datasheet da < 0,1 V).
- El pico de VBUS al enchufar en caliente con un cable de 1 m (6,06 V) queda por debajo del OVP mínimo; con cables más largos o C1 con menos DC bias puede acercarse a 6,4 V: el OVP tiene 50 µs de filtro y el pico dura < 10 µs. No se modela el diodo de U1 (USBLC6-2SC6) entre VBUS y GND, que lo recortaría. Se mide en TEST-PLAN §4 con el osciloscopio en VBUS.

Figuras: `png/bq24073_supplement.png`, `png/bq24073_desenchufe.png`, `png/bq24073_enchufe.png`.

## Batería y Q1 (SI7615ADN) — `bateria_q1.cir`

Supuestos:

- **Q1 con un modelo EKV** (`SI7615` en `models/furby.lib`: subumbral, lineal y saturación, más 3 mΩ de encapsulado) ajustado a la hoja de Vishay: 250 µA a |VGS| = VGS(th) (0,4 o 1,5 V, las dos esquinas) y RDS(on) 9,8 mΩ a −2,5 V con VGS(th) = −1,5 V. La pendiente subumbral (89 mV/década) es un supuesto típico: decide dónde se queda el nodo BAT con la batería al revés y el USB puesto.
- **BQ24073 visto desde BAT** con su tabla 8.5: con USB, fuente de detección de cortocircuito IBAT 4–11 mA mientras VBAT < VBAT(SC) (1,6–2,0 V) y precarga KISET/RISET/10 = 44–54 mA por encima; sin USB, BAT-FET de 100 mΩ hacia VSYS.
- Celda con 0,15 Ω y 100 nH de cable; θJA de Q1 en régimen 81 °C/W (`ARQUITECTURA.md` §7.1; la hoja da 33 °C/W máx. solo para t ≤ 10 s sobre 1 pulgada cuadrada de cobre).

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Q1 con 2,9 A, batería 3,0 V, VGS(th) −1,5 V | 27 mV, 78 mW → Tj ≈ 56 °C | Tj ≤ 110 °C (Ta 50 °C, 81 °C/W) | PASS |
| Q1 con 2,9 A, batería 3,0 V, VGS(th) −0,4 V | 16 mV, 47 mW → Tj ≈ 54 °C | Tj ≤ 110 °C (Ta 50 °C, 81 °C/W) | PASS |
| Batería al revés sin USB: nodo BAT y divisor del ADC | BAT -0,6 µV; VBAT_SNS -0,02 µV; fuga 1,0 nA (modelo; IDSS ≤ 1 µA) | ≥ −0,3 V (máximo absoluto de BAT) | PASS |
| Batería al revés con USB, esquina mala (VGS(th) −1,5 V, IBAT 11 mA, VBAT(SC) 1,6 V) | BAT sube a 1,72 V > VBAT(SC): precarga de 54 mA; Q1 disipa 0,32 W → Tj ≈ 76 °C | Q1 ≤ 0,5 W y ningún nodo negativo | PASS |
| Batería al revés con USB, esquina buena (−0,4 V, 4 mA, 2,0 V) | BAT 0,51 V, 4 mA (se queda en detección de cortocircuito) | Q1 ≤ 0,5 W | PASS |
| Conexión de la batería (4,2 V) con la placa descargada | pico de 14,6 A; > 10 A durante 9 µs | Q1: < IDM 80 A (300 µs); la PCM de la celda (desconocida) se comprueba al soldarla | PASS |

Observaciones:

- **Con la batería al revés y el USB puesto, en la esquina mala el nodo BAT sí pasa de VBAT(SC)** (1,72 V frente a 1,6 V mín.) y el BQ24073 entra en precarga (54 mA). `ARQUITECTURA.md` §7.1 decía que se quedaría por debajo «como mucho 1,5 V», pero ya preveía este caso: Q1 disipa 0,32 W (Tj ≈ 76 °C) durante el temporizador de precarga y luego el cargador marca fallo. No rompe nada y no llega tensión negativa a ningún nodo. La prueba de TEST-PLAN §8.1 (fuente limitada al revés, sin y con USB) lo confirma en la placa: anotar la tensión de BAT (TP4) y la corriente.
- Al soldar la batería, el pico de 14,6 A (≈ 9 µs por encima de 10 A) carga C4 y los ≈ 58 µF de VSYS a través de Q1 y del BAT-FET. Q1 lo aguanta de sobra (IDM 80 A). Si la PCM de la celda tiene un disparo por cortocircuito muy rápido (algunas cortan en < 10 µs por encima de ≈ 10 A), la celda se desconectaría y no volvería hasta enchufar el USB: se comprueba al soldarla (TEST-PLAN §8.2: tras soldar, TP4 debe leer la tensión de la celda).

Figuras: `png/q1_reves_con_usb.png`, `png/q1_conexion.png`.

## Lo que no se simula y por qué

- **TPS63802 (3,3 V):** el modo PFM y la zona de transición buck-boost (control propietario); se miden en el bring-up.
- **Compensación del TPS61089:** valores de la nota de aplicación del datasheet (R24 30 kΩ, C14 4,7 nF, C15 10 pF); se mide el escalón de carga en el bring-up.
