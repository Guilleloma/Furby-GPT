# Simulaciones (ngspice)

Modelos de comportamiento declarados: no hay modelos SPICE de los convertidores de TI que acepte ngspice, así que se simula la etapa de potencia idealizada en lazo abierto (ciclo de trabajo fijo) para el peor caso. Las cifras se contrastan con los máximos del datasheet y se vuelven a medir en el bring-up (`TEST-PLAN.md`).

## Elevador de 6 V (TPS61089 + FHD4020S-1R0MT) — `elevador_6v.cir`

Peor caso: Vin 3,0 V (batería agotada), carga 1,0 A (ITRIP del motor), L −20 % (0,8 µH), Cout 4 × 22 µF con DC bias a 6 V (≈ 53 µF), fSW 0,96 MHz.

| Magnitud | Resultado | Criterio | PASS/FAIL |
|----------|-----------|----------|-----------|
| Corriente de pico en la bobina | **2,82 A** | < ILIM 3,8 A (RILIM 270 kΩ) con margen ≥ 20 % | PASS (margen 26 %) |
| Corriente media de entrada | 1,86 A | Coherente con el presupuesto (2,0 A a 3,3 V en `ARQUITECTURA.md` §11) | PASS |
| Rizado de la bobina (pico a pico) | 1,94 A | Informativo: fija el Isat necesario ≥ 2,82 A · 1,2 ≈ 3,4 A | **Isat de la FHD4020S-1R0MT por verificar en su hoja de datos antes del pedido** |
| Rizado de salida | 19 mV pico a pico | < 1 % de 5,94 V (59 mV) | PASS |
| Tensión media (lazo abierto, D fijo) | 5,54 V | Solo informativo: sin el lazo cerrado la salida cae con las pérdidas; el regulador la mantiene en 5,94 V | — |

Ejecutar: `ngspice -b sim/elevador_6v.cir`.

## Lo que no se simula y por qué

- **TPS63802 (3,3 V):** control propietario (PFM/PWM con 4 interruptores); el pico de 0,7 A frente a 2 A de capacidad se comprueba por cálculo y por medida.
- **Polaridad inversa con USB (P-MOSFET + BQ24073):** depende de la detección de cortocircuito del cargador (4–11 mA, datasheet SLUS810); análisis en `ARQUITECTURA.md` §7.1 y prueba obligatoria en el bring-up con fuente limitada, sin y con USB.
- **Compensación del TPS61089:** valores de la nota de aplicación del datasheet (R24 30 kΩ, C14 4,7 nF, C15 10 pF); se mide el escalón de carga en el bring-up.
