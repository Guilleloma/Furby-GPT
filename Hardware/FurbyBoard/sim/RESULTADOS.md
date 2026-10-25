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
| Puente H y motor | `drv8231a_motor.cir` | PASS (θJA del DSG, 66,5 °C/W, corregida en NOTAS en el bloque F) |
| Amplificador (MAX98357A) | `max98357_vsys.cir` | PASS con C41 (10 µF junto a los pines 7/8, bloque F): 70 mV pp en VDD (87 en el peor caso); sin C41 eran 258 mV pp (FAIL) |
| LDO de la cámara (ME6211) | `ldo_camara.cir`, `ldo_camara_psrr.cir` | PASS (RESETB sin reset por hardware al encender: el firmware usa el reset por SCCB) |
| NTC en TS | `ntc_ts.cir` | PASS frente a 0–51 °C (nominal 0,2–51,2 °C; con tolerancias −2,2–56,4 °C); frente a 0–45 °C, pendiente de la hoja de la celda |
| Señales | `senales_i2c_led_ir.cir`, `senales_sensores_adc.cir` | D4/D5 PASS con R57/R58 de 1 kΩ (bloque F); **FAIL** condicionado: ADC solo con muestreo ≤ 1 kHz (regla de firmware); I2C a 400 kHz PASS |
| Arranque y caída de batería | `arranque_brownout.cir` | Arranque PASS; **FAIL**: el pico de 10,2 W hunde VSYS bajo 2,5 V con la batería < 3,36 V (0,21 Ω) o < 4,0 V (0,37 Ω); 3V3 se mantiene. Propuesta: presupuesto de potencia en firmware y celda de baja resistencia |

### Propuestas que salen de las simulaciones

El bloque F (2026-10-25) aplicó las de pieza y documentación (C41, R57/R58 y la θJA); las de firmware están en `NOTAS.md` y en el `README.md` de la placa, sección «Reglas para el firmware».

| Prioridad | Propuesta | Por qué | Dónde |
|-----------|-----------|---------|-------|
| Alta (firmware) | Presupuesto de potencia: con USB presente (PGOOD) o con VBAT en carga < ≈ 3,7 V, no sumar motor bloqueado + audio a plena potencia + TX (PWM del motor ≤ 50–60 %, audio a −12 dBFS mientras se mueve) | VO(SC2) del BQ24073 con USB500 y caída de VSYS bajo el UVLO del elevador con la batería baja | «Power path», «Arranque» |
| Alta (firmware) | Al subir PGOOD, pausar motor y audio ≈ 5 ms | Biestabilidad del power path con cargas de potencia constante | «Power path» |
| **Aplicada** (bloque F) | C41: 10 µF 10 V 0603 (C19702) junto a los pines 7/8 de U7 | 258 → 70 mV pp de rizado en VDD del amplificador (25 mV pp si estuviera pegado al pin; no cabe) | «Amplificador» |
| Media (compra) | Celda con resistencia interna (con PCM) ≤ 100 mΩ; medirla en el bring-up | El pico de 10,2 W se sostiene hasta 3,07 V en vez de 3,36–4,0 V | «Arranque» |
| **Aplicada** (bloque F) | R57 y R58 de 1 kΩ (C21190) | Los LED verdes son de InGaN (VF ≈ 2,8 V): D4 se quedaba en 0,24 mA; ahora 0,47–0,92 mA | «Señales» |
| Baja (firmware) | ADC de VBAT_SNS y LIGHT en lecturas sueltas a ≤ 1 kHz de media; antirrebote ≥ 30 ms en la INT del TCA9535; reset de la cámara por SCCB | Impedancia de 235 kΩ, entradas sin histéresis, RESETB sin flanco al encender | «Señales», «LDO de la cámara» |
| **Aplicada** (bloque F) | θJA del DRV8231A en `NOTAS.md`: 66,5 °C/W (DSG), no 42,8 | Tj con el motor bloqueado 103 °C, no 76 °C | «Puente H» |
| v1.1 | NTC de B ≈ 3950–4100 K si la celda pide 0–45 °C; R54 en 1206; PTC de 2 A + modo ILIM | Ventana de carga, potencia de R54 con portadora continua, margen de VO(SC2) | «NTC», «Señales», «Power path» |

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
| Desenchufe del USB (4,4 → 3,0 V en 10 µs, 0,55 A) | VSYS mín. 2,69 V; 3V3 3,27–3,27 V | VSYS ≥ 2,3 V; el modelo no tiene paso de línea: la figura 10-28 da < 0,1 V con 2,2 → 4,2 V | PASS |
| Pico de L1, buck (VSYS 4,4 V, 0,7 A, L −20 %) | 1,37 A | < 3,8 A con margen ≥ 20 % | PASS |
| Pico de L1, boost (VSYS 3,0 V, 0,7 A, L −20 %) | 0,94 A | < 4,0 A (mín.) con margen ≥ 20 % | PASS |
| Rizado de 3V3 en C7/C8, buck / boost (20 MHz) | 5,8 / 2,7 mV pp | ≤ 33 mV pp (1 %) | PASS |
| Rizado de 3V3 en el módulo (C9), buck / boost | 0,6 / 0,1 mV pp | ≤ 33 mV pp | PASS |

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

## Puente H y motor (DRV8231A + TPS61089) — `drv8231a_motor.cir`

Supuestos:

- **DRV8231A de comportamiento** con la lógica IN/IN y la regulación de corriente de la sección 7.4.2.2: comparador IPROPI frente a VREF con tBLK 1,4 µs y tDEG 0,7 µs, freno de tOFF 25 µs que termina antes si cambia una entrada, IPROPI = 1500 µA/A sobre R28 (1,5 kΩ) y VREF del divisor R26/R27 con C23. RDS(on) por lado 0,33 Ω (27 °C) o 0,45 Ω (en caliente, figuras 6-5 y 6-6). No se modelan el reposo (tSLEEP) ni tWAKE: con PWM a 20 kHz no se duerme.
- **Elevador** con el modelo promediado `TPS61089_AVG` (control de pico de corriente, GEA 190 µS, Rsense 0,08 Ω, compensación real R24/C14/C15) y ≈ 53 µF efectivos en V6.
- **Motor estimado** (el bobinado no está medido, `ARQUITECTURA.md` §6): 5 Ω (1,2 A bloqueado, por encima de ITRIP: el caso que regula), 0,5 mH, KE = KT = 5 mV·s/rad; 0,2 A y 1000 rad/s en vacío; constante mecánica ≈ 30 ms.
- Batería a media carga (3,7 V) con 0,21 Ω hasta VSYS. Con la batería baja, ver «Arranque y caída de batería».

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| ITRIP con las tolerancias (cálculo) | 0,91–1,10 A (nominal 1,00 A) | Informativo: AERR (±6 %) solo está garantizado con VM ≥ 6,5 V y V6 es 5,94 V; se mide | — |
| Arranque al 100 % desde parado: pico del motor | 1,00 A | ≤ ITRIP + 10 % y < 3,7 A (OCP) | PASS |
| Arranque: V6 y VSYS mínimos (batería 3,7 V) | V6 5,87 V; VSYS 3,31 V | V6 > 4,45 V (UVLO del DRV8231A); VSYS > 2,7 V (UVLO del TPS61089) | PASS |
| Bloqueado al 100 %: corriente regulada (media / pico / valle) | 0,94 / 1,00 / 0,74 A | pico ≤ ITRIP + 10 % | PASS |
| Bloqueado: IPROPI en el pico frente a VREF | 2,246 V frente a 2,246 V | ≤ 3,0 V (rango de AERR) y ≤ 3,1 V (ADC del ESP32-S3 a 12 dB) | PASS |
| Bloqueado: disipación del DRV8231A (RDS(on) 0,45 Ω por lado en caliente) | 0,79 W → Tj ≈ 103 °C (θJA 66,5 °C/W del DSG) | Tj ≤ 110 °C con Ta 50 °C | PASS |
| Bloqueado: rizado y mínimo de V6 | 130 mV pp; mín. 5,92 V | V6 > 4,45 V | PASS |
| PWM 20 kHz al 70 % (decaimiento lento) a 700 rad/s: corriente y rizado | 0,12 A medios, 125 mA pp; V6 19 mV pp | Informativo (motor estimado) | — |
| Inversión a toda velocidad sin freno: pico | 1,01 A; V6 5,85–5,97 V | < 3,7 A (OCP) y V6 < 6,5 V | PASS |

Observaciones:

- La regulación funciona como dice la hoja: el pico se queda en ITRIP en el arranque, bloqueado y al invertir sin freno, lejos del OCP (3,7 A). Con el motor bloqueado la corriente oscila entre 0,74 y 1,0 A (0,93 A de media) con un periodo de ≈ 230 µs (≈ 4 kHz): **se oirá un pitido** mientras regula. Si molesta al micro, el firmware evita sostener la regulación (rampa de PWM y detección de bloqueo).
- **θJA del DRV8231A**: `NOTAS.md` («Tabla de raíles», «Cálculos») y `ARQUITECTURA.md` §6 usan 42,8 °C/W, que es la del encapsulado DDA (HSOP). U6 es el **DSG (WSON 2 × 2)**: 66,5 °C/W (tabla 6.4). Con el motor bloqueado de forma continua y RDS(on) en caliente, Tj ≈ 103 °C (PASS justo); con 0,6 W, 90 °C en vez de 76 °C. El firmware limita el bloqueo a ≤ 150 ms (encoder), así que en uso real no se llega al régimen. Corregido en `NOTAS.md` (bloque F).
- **ITRIP**: el ±6 % de AERR solo está garantizado con VM ≥ 6,5 V y V6 es 5,94 V. Con el resto de tolerancias, 0,91–1,10 A. Se mide en el bring-up (TEST-PLAN §11, IPROPI en TP8 con el motor bloqueado: 2,25 V ± 10 %).
- V6 no baja de 5,85 V en ningún caso (UVLO del DRV8231A 4,05–4,35 V). El rizado de V6 con el motor bloqueado (130 mV pp) viene de la carga a golpes de la regulación; el lazo del elevador (fc ≈ 20 kHz) lo sigue sin problemas.

Figuras: `png/drv_arranque.png`, `png/drv_bloqueo.png`, `png/drv_inversion.png`.

## Amplificador MAX98357A sobre VSYS — `max98357_vsys.cir`

Repetida el 2026-10-25 con C41 (bloque F); la primera pasada, sin C41, daba 257 mV pp en VDD (FAIL).

Supuestos:

- **Clase D conmutado**: modulación BD de 3 niveles a 300 kHz, 0,25 Ω por interruptor (estimado del 92 % de rendimiento de la hoja), flancos de 15 ns con tiempo muerto, altavoz de 4 Ω + 33 µH (la carga de prueba de la hoja) y tono de 1 kHz con m = 0,9 (≈ 1 W con VSYS a 3,6 V). El ensanchado de espectro (± 20 kHz) no se modela.
- **Puente de VSYS** (rutado del bloque C, `NOTAS.md`): los pines 7/8, C26 (100 nF) y C41 (10 µF) cuelgan del relleno de In2 a través de 2 vías, 6,5 mm de B.Cu de 0,6 mm y otras 2 vías; C24 y C25 (22 µF) están del lado del relleno. Estimado: 10 mΩ y 3 nH (peor caso 5 nH).
- **C41** (bloque F): 10 µF 10 V X5R 0603 (C19702), ≈ 5 µF a 3,6 V, a 1,3 mm de los pines 7/8 por el oeste de C26. Conexión medida en el PCB: 1,5 mm de F.Cu de 0,6 mm hasta el tronco de los pines, 1,1 mm de tronco y 1 mm de 0,25 mm, más el ESL del 0603: **1,25 nH** estimados (peor caso 2 nH).
- Batería a media carga (3,7 V) con 0,21 Ω; ≈ 58 µF en el resto de VSYS.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Potencia en el altavoz (tono de 1 kHz, m = 0,9, VSYS ≈ 3,6 V) | 1,01 W; 0,71 A de pico en 4 Ω | Informativo | — |
| Corriente por el puente de B.Cu (media / pico) | 0,32 / 0,84 A | ≤ 0,7 A por vía en continua (2 vías por extremo: 1,4 A) | PASS |
| VDD en los pines 7/8 (puente de 3 nH, C41 a 1,25 nH): mínimo | 3,53 V | ≥ 2,5 V | PASS |
| Rizado de conmutación en los pines 7/8 con C41: nominal (3 nH, 1,25 nH) / peor caso (5 nH, 2 nH) | 70 / 87 mV pp | ≤ 200 mV pp (rizado de la prueba de PSRR) | PASS |
| Diseño anterior al bloque F (sin C41, solo C26 junto a los pines) | 258 mV pp; mín. 3,42 V | ≤ 200 mV pp (informativo: ya no aplica) | — |
| Rizado en los pines con los 22 µF pegados (referencia sin puente) | 39 mV pp | ≤ 200 mV pp | PASS |
| VSYS en el relleno de In2 (lo que ve U3) | mín. 3,55 V | ≥ 2,3 V (VIN;LOAD del TPS63802) | PASS |

Observaciones:

- **Sin C41 (primera pasada): 257 mV pp en los pines.** Con solo 100 nF junto a los pines 7/8 y el bulk al otro lado del puente, cada flanco de la salida excitaba la resonancia de C26 con la inductancia del puente (≈ 9 MHz). VDD no bajaba de 3,42 V, pero el rizado quedaba por encima del que caracteriza el PSRR de la hoja, que pide 0,1 µF **y 10 µF** junto a VDD («Power-Supply Input»).
- **Con C41 (bloque F): 70 mV pp** (87 mV pp con el puente de 5 nH y 2 nH hasta C41). Queda por encima de los 25 mV pp de un 10 µF pegado al pin (0,4 nH) porque junto a los pines 7/8 no cabe un 0603: al norte está C26, al oeste SPK_P y al este los pines sin conexión; C41 va al oeste de C26 y entra en el tronco de VSYS de los pines. Un barrido de esa conexión con el puente de 3 nH (0,4 / 1 / 1,5 / 2 / 3 nH → 25 / 59 / 71 / 75 / 96 mV pp) muestra que el margen frente a 200 mV pp es amplio aunque la estimación de 1,25 nH se quede corta.
- El puente aguanta la corriente (0,32 A medios; el pico baja de 1,5 a 0,84 A porque C41 da los flancos) y VSYS en el relleno apenas se mueve (mín. 3,55 V): **3V3 no se entera** (U3 regula con VIN ≥ 2,3 V; la figura 10-29 del TPS63802 da < 0,1 V para escalones de entrada de 0,6 V en 1 µs).
- Se mide en el bring-up (TEST-PLAN §13, «Rizado de VDD»): osciloscopio en el pad de VSYS de C41 con masa corta y 20 MHz de ancho de banda, tono de 1 kHz a −6 dBFS.

Figuras: `png/max98357_vdd.png` (VDD en los pines: puente actual, propuesta y referencia), `png/max98357_vsys.png`.

## LDO de la cámara (ME6211C28 y ME6211C12) — `ldo_camara.cir`, `ldo_camara_psrr.cir`

Supuestos:

- **Modelo `LDO_ME6211`** con la hoja ME6211 V24: caída de 110 mV (C28) y 280 mV (C12) a 100 mA, IOUTMAX 450/300 mA con repliegue a 65 mA en cortocircuito, PSRR ajustada a sus dos puntos (70 dB a 1 kHz y 62 dB a 10 kHz) y aplanada en −38 dB por encima de ≈ 170 kHz (supuesto), regulación de carga de 67 mΩ. La hoja no da el tiempo de arranque: rampa de 50 µs supuesta.
- Cámara OV2640: AVDD 20 mA y DVDD 80 mA (tabla de raíles), 1 µF más en cada raíl dentro del módulo; 3V3 con el modelo del TPS63802 y la pista de 58 mΩ.
- Rizado de 3V3 para el caso de PSRR: 6 mV pp a 1,6 MHz (PWM, de `tps63802_rizado.cir`) más 40 mV pp a 20 kHz (PFM: **supuesto**, se mide).

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Arranque con CAM_EN: subida de AVDD (10 → 90 %) | 36 µs; sobreimpulso 0,9 mV | Monótona, sin sobreimpulso > 5 % | PASS |
| Orden de arranque: DVDD frente a AVDD | DVDD − AVDD máx. 0 mV (U9 cuelga de AVDD) | DVDD nunca por encima de AVDD | PASS |
| Pico de corriente de 3V3 al encender la cámara y caída de 3V3 | 284 mA; 3V3 mín. 3,27 V | 3V3 ≥ 3,0 V | PASS |
| AVDD y DVDD en régimen (20 y 80 mA) | 2,794 V y 1,195 V | 2,8 V ± 5 % y 1,2 V ± 5 % | PASS |
| PSRR de U8 a 1 kHz / 10 kHz / 20 kHz / 1,6 MHz | 70 / 62 / 57 / 42 dB | Ajuste a la hoja: 70 dB a 1 kHz y 62 dB a 10 kHz | PASS |
| Rizado de AVDD / DVDD con 46 mV pp en 3V3 (PWM 1,6 MHz + PFM 20 kHz) | 0,16 / 0,06 mV pp | AVDD ≤ 10 mV pp | PASS |
| Disipación de U8 / U9 (SOT-23-5, 250 °C/W) | 50 / 128 mW → Tj ≈ 62 / 82 °C | Tj ≤ 110 °C con Ta 50 °C | PASS |

Observaciones:

- U8 trabaja con 0,47 V de margen (3,27 → 2,8 V) y la PSRR de la hoja está medida con 1 V: la real será algo peor, pero hay más de 30 dB de sobra frente al criterio de 10 mV pp. Se mide en TEST-PLAN §14 (TP10 y TP11 con el osciloscopio en AC y 20 MHz).
- **CAM_RST (RESETB) no da un reset por hardware al encender la cámara**: R35/C31 cuelgan de 3V3, que ya está arriba cuando CAM_EN enciende AVDD y DVDD, así que RESETB está a 3,3 V desde antes de alimentar el sensor. No es un fallo si el firmware usa el reset por SCCB (en `esp32-camera`, `pin_reset = -1`) y PWDN (R34 lo deja en reposo al arrancar). Se anota para el firmware.

Figuras: `png/ldo_arranque.png`, `png/ldo_psrr.png`.

## NTC en TS (RT1, NCP18XH103F03RB) — `ntc_ts.cir`

Supuestos: el pin TS del BQ24073 con su fuente de 72–78 µA y los umbrales VHOT 270–330 mV y VCOLD 2,0–2,2 V (tabla 8.5); el NTC de Murata con R25 10 kΩ ± 1 % y B25/50 3380 K ± 1 % (modelo B, exacto a 25 y 50 °C; ≈ 0,5 °C de error estimado a 0 °C). Se barre la temperatura del NTC y se toman los cruces en las esquinas que más ensanchan y más estrechan la ventana.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Ventana de carga nominal (INTC 75 µA, VHOT 0,30 V, VCOLD 2,10 V) | 0,2 a 51,2 °C | 0–51 °C (la del encargo y la tabla 9-3 de TI: 28 kΩ y 4 kΩ) | PASS |
| Ventana más ancha con tolerancias (INTC, VHOT/VCOLD, R25 ± 1 %, B ± 1 %) | -2,2 a 56,4 °C | Informativo: lo que puede llegar a cargar una placa concreta | — |
| Ventana más estrecha con tolerancias | 2,6 a 46,5 °C | Informativo | — |
| Reanudación de la carga (histéresis, nominal) | por debajo de 48,3 °C y por encima de 3,6 °C | Informativo | — |
| Frente a la ventana de carga típica de una LiPo (0–45 °C) | carga hasta 51 °C (nominal) y 56 °C (peor caso) | ≤ 45 °C si la hoja de la celda lo pide (pendiente: celda sin hoja) | — |

Observaciones:

- La ventana nominal es la que se decidió (0–51 °C, la de la nota de la tabla 8.5 de TI). Con las tolerancias del cargador, una placa concreta puede cargar hasta 56 °C o cortar ya a 46,5 °C.
- **Si la celda pide 0–45 °C** (lo habitual en LiPo), el corte en caliente queda 6–11 °C por encima. No es un fallo del circuito, sino del criterio: depende de la hoja de la celda, que no tenemos. Si la celda lo exige, la solución en la v1.1 es un NTC de 10 kΩ con B ≈ 3950–4100 K (ventana nominal ≈ 3–47 °C con los mismos umbrales); con la red Rs/Rp de la figura 9-9 no se puede bajar el corte en caliente sin bajar también el de frío por debajo de 0 °C. Recordatorio de `NOTAS.md`: el NTC mide la PCB bajo la celda, no la celda.

Figura: `png/ntc_ts.png`.

## Señales: I2C, LED, IR, sensores y ADC — `senales_i2c_led_ir.cir`, `senales_sensores_adc.cir`

Supuestos (detalle en la cabecera de cada `.cir`):

- **I2C**: capacidad del bus con las pistas del PCB actual (SDA 150,5 mm y 4 vías; SCL 137,6 mm y 5 vías), 0,09 pF/mm y 0,4 pF por vía (estimados para el apilado de 6 capas), pines del ESP32-S3 (2 pF), del TCA9535 (8/9,5 pF máx.) y de la cámara con su flex (15 pF, supuesto): **Cb ≈ 42 pF**, no los 100 pF que suponía `NOTAS.md`.
- **LED**: VF de las fichas de LCSC (rojo KT-0603R 1,8–2,4 V a 20 mA; verde KT-0805G **InGaN, 2,6–3,1 V a 5 mA**). Criterio de visibilidad ≥ 0,3 mA (propio).
- **IR**: LED de 940 nm supuesto (1,2 V a 20 mA, 1,5 V a 100 mA) y AO3400A con 48 mΩ; portadora de 38 kHz al 33 % y trama NEC.
- **Sensores**: rebote de 5 aperturas de 100 µs al pulsar; umbrales del TCA9535 (0,3/0,7 VCC) y del ESP32-S3 (0,25/0,75 VDD).
- **ADC**: el ESP32-S3 no publica su condensador de muestreo: 10 pF que se vacía en cada muestra (peor caso) y fuga máxima de pin de 50 nA (tabla 5-4).

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| I2C: subida de SDA / SCL (4,7 kΩ, Cb ≈ 42 pF con las pistas reales) | 166 / 157 ns (30–70 %) | ≤ 300 ns (400 kHz) y ≤ 1000 ns (100 kHz) | PASS |
| I2C: VOL con el ESP32 tirando a GND | 13 mV | ≤ 0,4 V | PASS |
| LED D1 CHG (rojo, VBUS, 2,2 kΩ) | 1,42 mA | ≥ 0,3 mA (diseño ≈ 1,4 mA) | PASS |
| LED D2 PG (verde, VBUS, 2,2 kΩ) | 0,96 mA | ≥ 0,3 mA (diseño ≈ 1,4 mA) | PASS |
| LED D3 PROG (rojo, 3V3, 1,5 kΩ) | 0,97 mA | ≥ 0,3 mA (diseño ≈ 1,0 mA) | PASS |
| LED D4 PWR (verde, 3V3, 1 kΩ), VF 3,1 / 2,6 V a 5 mA | 0,47–0,92 mA | ≥ 0,3 mA (diseño: 0,5–0,9 mA) | PASS |
| LED D5 RUN (verde, 3V3, 1 kΩ), VF 3,1 / 2,6 V a 5 mA | 0,47–0,92 mA | ≥ 0,3 mA (diseño: 0,5–0,9 mA) | PASS |
| IR: corriente del LED con VSYS 4,4 / 3,0 V | 131 / 73 mA (VF 1,59 V) | Informativo (≈ 100 mA de diseño) | — |
| IR: potencia de R54 (0805, 0,125 W) con VSYS 4,4 V | pico 0,37 W; portadora continua 124 mW; trama NEC 51 mW | ≤ 62 mW (50 %) de media en una trama | PASS |
| Barriga/espalda/lengua: rebote al pulsar (47 kΩ, 1 kΩ, 100 nF) | máx. 0,76 V entre el primer contacto y el fin del rebote | < VIH 2,31 V (no hay flanco falso) | PASS |
| Barriga: respuesta al soltar (cruce de VIH) | 5,6 ms | < 50 ms | PASS |
| Inclinación (220 kΩ, 100 nF): rebote y respuesta al soltar | máx. 0,74 V; 26,4 ms | < 2,31 V y < 50 ms | PASS |
| Leva HOME al ESP32 (100 kΩ, 1 kΩ, 10 nF): rebote y respuesta al soltar | máx. 0,34 V; 1,4 ms | < VIH 2,48 V y < 50 ms | PASS |
| Encoder ENC_PT (10 kΩ, 50 pF): subida 10–90 % | 1,08 µs | ≪ medio periodo del encoder (informativo) | — |
| VBAT_SNS: error de muestreo con el ADC a 1 kHz (Cs 10 pF supuesto) | 4,9 mV (0,23 %) | ≤ 0,5 % de la lectura | PASS |
| VBAT_SNS: error de muestreo con el ADC a 10 kHz (Cs 10 pF supuesto) | 47,9 mV (2,28 %) | ≤ 0,5 % de la lectura | **FAIL** |
| VBAT_SNS: error de muestreo con el ADC a 100 kHz (Cs 10 pF supuesto) | 397,3 mV (18,92 %) | ≤ 0,5 % de la lectura | **FAIL** |
| VBAT_SNS: desplazamiento por la fuga del pin (50 nA máx.) | 11,8 mV (0,56 %) | Informativo: fijo, se corrige con la calibración de TEST-PLAN §9 | — |
| LIGHT (LDR 10 kΩ–1 MΩ con 470 kΩ y 100 nF): constante de tiempo | 1 ms (luz) a 32 ms (oscuridad) | Informativo: el firmware espera ≥ 5 τ tras un cambio | — |

Observaciones y propuestas:

- **I2C a 400 kHz es viable** con los pull-ups de 4,7 kΩ (166 ns frente a 300 ns), con la Cb estimada desde el rutado. Si se conecta algo a J_EXP con cable, se suma su capacidad: con más de ≈ 75 pF de bus, 400 kHz deja de cumplir. Se mide en TEST-PLAN (tiempo de subida con el osciloscopio).
- **LED D4 (PWR) y D5 (RUN): resuelto en el bloque F.** Los verdes KT-0805G son de InGaN (VF ≈ 2,6–3,1 V), no de 2 V como suponían los cálculos: con 2,2 kΩ y 1,5 kΩ quedaban 0,24–0,45 mA en D4 (FAIL) y 0,34–0,63 mA en D5. Con R57 y R58 de 1 kΩ (C21190, básica, ya en la BOM): 0,47–0,92 mA en los dos. Coste en reposo: hasta 0,9 mA del LED PWR, que se quita cortando JP5.
- **IR**: con USB (VSYS 4,4 V), R54 ve 0,37 W de pico y 124 mW de media con la portadora continua, justo su potencia nominal (0,125 W en 0805). Con tramas NEC (51 mW de media) cumple el 50 %; el firmware no debe emitir portadora continua más de ≈ 50 ms. Mejora para la v1.1: R54 en 1206 (0,25 W).
- **Sensores**: los RC filtran el rebote de sobra (nunca se acercan a VIH) y responden en 1,4–26 ms. El TCA9535 no tiene histéresis en sus entradas: con la subida lenta de la inclinación (26 ms) el ruido puede dar varias interrupciones en el cruce; el firmware debe hacer antirrebote por tiempo (≥ 30 ms) en la INT del expansor.
- **FAIL condicionado — ADC de VBAT_SNS con muestreo rápido.** Con un divisor de 470 kΩ + 470 kΩ, cada muestra se lleva la carga del condensador de muestreo; la media cae ≈ Cs · V · fs · 235 kΩ: 4,9 mV a 1 kHz (PASS), 48 mV a 10 kHz y 0,4 V a 100 kHz (modo continuo del ESP-IDF). **Regla de firmware: lecturas sueltas (oneshot) a ≤ 1 kHz de media** (para la batería sobra con 1 Hz). La fuga del pin (hasta 11,8 mV, 0,56 %) es un desplazamiento fijo que corrige la calibración de TEST-PLAN §9. Lo mismo vale para LIGHT.

Figuras: `png/sensores_rc.png`, `png/adc_vbat_sns.png`.

## Arranque y caída de batería — `arranque_brownout.cir`

Supuestos: batería conectada sin USB, a 3,0 V (agotada) con 0,37 Ω para el arranque; TPS63802 con su modelo (retardo de 321 µs y rampa de 224 µs); EN con R17/C11; ESP32 con 1 mA en reset, 50 mA al arrancar y 0,4 A durante 5 ms de calibración del WiFi. Para la caída de batería, cargas de potencia constante en VSYS: elevador + motor bloqueado 6,6 W (con la histéresis de UVLO del TPS61089, 2,5/2,7 V), 3V3 2,0 W y amplificador 1,6 W, y la batería bajando de 4,2 a 2,8 V; resistencia de la celda a VSYS de 0,21 Ω (nominal) o 0,37 Ω (celda vieja o fría y BAT-FET caliente).

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Arranque con batería a 3,0 V y 0,37 Ω: 3V3 llega a 3,0 V | a 0,49 ms; sobreimpulso a 3,33 V | ≤ 3,6 V (máx. del ESP32-S3) | PASS |
| VSYS mínimo durante el arranque suave de U3 | 2,43 V | > 1,25 V (UVLO de U3 bajando) | PASS |
| EN del ESP32 (10 kΩ, 1 µF) cruza 0,75 · 3V3 | a 14,3 ms: 13,8 ms después de 3V3 ≥ 3,0 V | ≥ 50 µs (tSTBL) | PASS |
| 3V3 durante la calibración del WiFi (0,4 A, 5 ms) con la batería a 3,0 V | mín. 3,24 V | ≥ 3,0 V | PASS |
| Pico de 10,2 W (motor bloqueado + TX + audio) con 0,21 Ω (nominal): batería mínima | VSYS cae por debajo de 2,5 V con la batería a 3,36 V (cálculo: 3,36 V) | ≤ 3,0 V para sostener el pico en todo el rango de la batería | **FAIL** |
| Pico de 10,2 W (motor bloqueado + TX + audio) con 0,37 Ω (peor caso): batería mínima | VSYS cae por debajo de 2,5 V con la batería a 4,01 V (cálculo: 4,01 V) | ≤ 3,0 V para sostener el pico en todo el rango de la batería | **FAIL** |
| 3V3 mientras el elevador entra y sale por UVLO | mín. 3,27 V | ≥ 3,0 V (el ESP32 no se reinicia) | PASS |

Observaciones y propuesta:

- **El arranque es limpio**: EN se libera 13,8 ms después de que 3V3 esté estable (el mínimo es 50 µs), sin sobreimpulso en 3V3, y la calibración del WiFi con la batería agotada deja 3V3 en 3,24 V. Durante el arranque suave de U3, VSYS baja un instante a 2,43 V por la resistencia de la celda; U3 sigue funcionando (UVLO 1,25 V).
- **FAIL — el pico simultáneo de 2,9 A (10,2 W) no se sostiene en todo el rango de la batería.** Con cargas de potencia constante, VSYS = (VOC + raíz(VOC² − 4·R·P)) / 2: con 10,2 W y 0,21 Ω, VSYS cae por debajo del UVLO del elevador (2,5 V) cuando la batería baja de **3,36 V**; con 0,37 Ω, ya por debajo de **4,0 V**. A partir de ahí el elevador entra y sale por UVLO (el motor da tirones y el audio se corta), aunque **3V3 se mantiene** (U3 regula hasta VIN ≈ 1,3 V) y el ESP32 no se reinicia. Es el mismo límite que el del power path (pico de 2,9 A con USB): el presupuesto de pico de `ARQUITECTURA.md` §11 supone una fuente ideal.
- **Propuestas** (sin tocar el esquema): (1) **firmware**: presupuesto de potencia según VBAT_SNS: por debajo de ≈ 3,7 V en carga, no mover el motor con el audio a plena potencia (limitador a −12 dBFS mientras se mueve) y PWM del motor ≤ 60 %; detección de bloqueo por el encoder ya prevista; (2) **batería**: elegir una celda con resistencia interna (con PCM) ≤ 100 mΩ y medirla en el bring-up (escalón de 1 A en TP4); con 0,14 Ω en total el pico se sostiene hasta 3,07 V; (3) v1.1: ITRIP de 0,87 A (R26 de 6,8 kΩ) si el motor lo permite.
- **Medida en el bring-up (propuesta para TEST-PLAN §6 «Estrés»)**: fuente en los pads de la batería con 0,2 Ω en serie, bajando de 4,2 a 3,0 V con el motor bloqueado, el WiFi transmitiendo y audio al máximo: anotar la tensión de la fuente a la que el elevador empieza a cortar (VSYS en TP5 < 2,5 V) y comprobar que el ESP32 no se reinicia.

Figuras: `png/arranque.png`, `png/caida_bateria.png`.

## Lo que no se simula y por qué

| Qué | Por qué no | Qué lo cubre |
|-----|-----------|--------------|
| Modo PFM y zona de transición buck-boost del TPS63802 | Control propietario sin modelo; el modelo promediado no tiene rizado ni paso de línea | TEST-PLAN §7: rizado de TP6 < 50 mV pp con el WiFi transmitiendo; §8.3: enchufar y desenchufar con carga |
| Lazo real del TPS61089 (polo RHP, límites de COMP, PFM a poca carga) | El modelo promediado lo aproxima con la ecuación 11 de la hoja; sin modelo del fabricante | TEST-PLAN §10: escalones con 10 Ω y 4,7 Ω en TP7 |
| Saturación de L1 y L2 (FHD4020S) | Hoja de la bobina sin Isat verificado | Comprobar Isat ≥ 3,4 A (L2) y ≥ 1,7 A (L1) en la hoja antes del pedido; TEST-PLAN §10 con 4,7 Ω |
| Retardo real de entrada en supplement y apagado por VO(SC2) del BQ24073 | La hoja no da el retardo; el apagado de 60 ms no se modela | TEST-PLAN §8.3 y el paso propuesto en «Power path» (USB500 + motor bloqueado + TX + audio, VBAT − VSYS < 150 mV) |
| Regulación térmica del BQ24073 (TJ(REG), TJ(OFF)) | Modelo eléctrico, sin térmico | TEST-PLAN §17 (U2 < 85 °C cargando) |
| PCM de la celda (disparo por cortocircuito y resistencia interna) | Celda sin hoja | TEST-PLAN §8.2 (TP4 tras soldar) y medida de la resistencia de la celda con un escalón de 1 A (propuesta en «Arranque») |
| Motor real (R, L, constante de par) | Bobinado sin medir | TEST-PLAN §11 (bobinado y bloqueo con TP8) |
| Temperaturas de unión | Solo cálculo con θJA en régimen; la placa no es la JEDEC | TEST-PLAN §17 con cámara térmica |
| Integridad de señal del bus DVP (20 MHz) y del par USB | Sin modelos IBIS de la cámara ni del ESP32-S3; las reglas de rutado y la impedancia están en `NOTAS.md` | TEST-PLAN §5 (enumeración USB) y §14 (50 fotos seguidas) |
| Calidad de audio del clase D (THD, ruido, PSRR real, espectro ensanchado) | Modelo de conmutación ideal | TEST-PLAN §13 |
| RF, antena y EMI | Fuera del alcance de SPICE | TEST-PLAN §15 (RSSI frente a una placa de referencia) |
| Condensador de muestreo y fugas reales del ADC del ESP32-S3 | Espressif no los publica | TEST-PLAN §9 (calibración de VBAT_SNS) y regla de firmware (≤ 1 kHz de media) |
| Velocidad del fototransistor del encoder | Pieza del Furby sin hoja | TEST-PLAN §12 (flancos tras U11) |
| Consumo en reposo | Depende del firmware y de las fugas reales | TEST-PLAN §16 |
| DC bias de los MLCC | Capacidades efectivas estimadas con curvas típicas | Herramienta del fabricante (Samsung o Murata) si alguna conclusión queda justa |
