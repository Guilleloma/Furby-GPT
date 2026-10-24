# Contrato PCB ↔ base impresa (para el 3d-architect)

Todas las cotas en mm y en el **sistema de coordenadas del STL de la base del Furby de 1998**: vista desde arriba (+Z), delante = y máxima, detrás (lóbulo) = y mínima. La cara superior del suelo está en **z = 1,905**.

Fichero de referencia: `contorno-pcb.dxf` (mismas coordenadas, sin transformar).

| Capa del DXF | Qué es |
|--------------|--------|
| `Contorno` | Borde de la PCB, con la ranura del USB-C, sus dos orejetas y sin muescas. 54 arcos y 36 rectas, cerrado |
| `Taladros` | 4 taladros M2 Ø2,3 |
| `Mecanismo` | Agujero de Ø11,3 del mecanismo |
| `ExclusionMecanismo` | Zona de exclusión de Ø15,3 alrededor del mecanismo |
| `UsbC` | Planta del cuerpo del USB-C de 16 pines (8,94 × 6,42), desde la boca |
| `AgujerosBase` | Los 4 agujeros originales del suelo (Ø2,13), que la base tapa: solo de referencia |

La capa `Muescas` ya no existe: solo sale si se regenera con `--muescas` (sección 5).

## 1. PCB

| Dato | Valor |
|------|-------|
| Grosor | **1,6** (FR-4, tolerancia de fábrica ±10 %) |
| Cara inferior | z **3,905** |
| Cara superior | z **5,505** |
| Caja | x −107,92 … −39,08 (68,85) · y −127,79 … −53,21 (74,59) |
| Holgura a la pared interior | **1,00 mín.** y 1,20 máx. por lado (fuera de la ranura del USB-C). En las orejetas del USB-C, **0,47 mín.** La posición la fijan los 4 tornillos, no el borde |

El contorno es el suelo interior encogido 1,0 mm (antes 0,5: con 0,5 había riesgo de tener que forzarla). La pared interior **no puede moverse más de 0,5 hacia dentro** en la base modificada sin volver a ajustar la holgura. Si se engrosa la pared, que sea hacia fuera.

**Orejetas del USB-C (FurbyBoard):** las patas delanteras de la carcasa del conector (pads de 1,2 × 2,4 en x −79,12 y −67,88) empiezan 0,20 dentro del borde de la PCB. Como el fondo del lóbulo es curvo, el borde con holgura de 1,0 pasaba por encima de esos pads. El borde sigue recto a la cota del eje (y −127,794) entre x −80,25 y −66,75, dos orejetas de 2,1 mm a cada lado de la ranura que salen 0,2-0,45 mm hacia la pared. Ahí la pared queda a **0,47 mm**: entre x −81 y −66 la pared del lóbulo no puede moverse hacia dentro.

## 2. Separadores

| Dato | Valor |
|------|-------|
| Altura sobre el suelo | **2,0** (de z 1,905 a z 3,905) |
| Diámetro recomendado | 5,0 (la cabeza del M2 mide Ø4,0 y la PCB deja libre Ø5,0 alrededor de cada taladro) |
| Tornillo | **M2 × 4** autorroscante para plástico (rosca PA o PB), **4,2 de largo como máximo** bajo cabeza |
| Plástico bajo la PCB | 3,905 (separador de 2,0 más suelo de 1,905) |
| Rosca en el plástico | 2,4 nominal (4,0 − 1,6 de PCB), 2,6 con el largo máximo |
| Suelo bajo la punta | 1,5 nominal, 1,3 con el largo máximo: no asoma por debajo |

Descartados:

- **M2 × 5:** con el largo máximo de unos 5,3 entraría 3,7 en el plástico y dejaría solo 0,2 de suelo bajo la punta. La punta marcaría o rompería la cara inferior de la base.
- **Insertos roscados:** no caben con separadores de Ø5 y 2 de alto. Un inserto M2 de 3,0 necesita un alojamiento de unos 3,5 de profundidad, que con 3,9 de plástico deja el suelo casi pasante, y pared alrededor que un Ø5 no da.

La rosca de 2,4 es corta, de 1,2 veces el diámetro del tornillo. Para una PCB que solo recibe la fuerza de enchufar el cable (0,5–2,0 kgf, repartida entre H3 y H4) basta, pero conviene no apretar de más. El taladro piloto del separador sale del plan de la base.

| Taladro | Centro (x; y) | Borde de agujero a borde de PCB | A borde del agujero del mecanismo |
|---------|---------------|---------------------------------|-----------------------------------|
| H1 | (−97,00; −68,50) | 3,02 | 38,19 |
| H2 | (−50,00; −68,50) | 3,08 | 22,14 |
| **H3** | **(−86,70; −121,90)** (antes −86,80; −122,40) | 2,56 | 30,26 |
| **H4** | **(−60,30; −121,90)** (antes −60,20; −122,40) | 2,60 | 19,79 |

**Cambio de la FurbyBoard:** H3 y H4 se mueven 0,5 mm hacia delante (y 0,1 mm hacia el centro en x) para seguir a ≥ 2,5 mm del borde con la holgura de 1,0. Sus separadores y pilotos se mueven con ellos; el script de la base los lee de `geometria.json`.

H3 y H4 flanquean el USB-C (≈ 7,5 mm de la ranura cada uno) para que la placa no cabecee al enchufar el cable. Los 4 agujeros originales de la base (Ø2,13) no sujetan la PCB: se tapan (sección 5).

## 3. Corte en la pared del lóbulo para el USB-C

| Dato | Valor |
|------|-------|
| Centro en x | **−73,50** |
| Ancho | **13,0** (x −80,00 … −67,00): funda de 12 + 0,5 por lado |
| z inferior | **1,905**, a ras de la cara superior del suelo |
| z superior | **9,275** (antes 9,255: el eje del conector nuevo está 0,02 más alto) |
| Alto | 7,37 |
| Profundidad | Todo el grosor de la pared trasera del lóbulo (1,70) |
| Eje del conector | z **5,525**, a 3,62 sobre el suelo (HRO TYPE-C-31-M-13C: 1,60 de cuerpo por encima de la cara superior) |
| Boca del conector | y **−128,49**, a 0,30 de la cara interior de la pared (y −128,80 en x −73,5). **Sin cambios**: la boca sale 0,70 del borde de la PCB, que ahora está en y −127,79 |

- **Por qué el corte es tan alto:** la boca del conector queda 2,0 mm por dentro de la cara exterior de la pared (0,3 de aire más 1,7 de pared). Con el cable enchufado, la funda sobremoldeada entra esos 2 mm en el corte. Si el corte fuera solo del tamaño del conector (8,94 × 3,16), la funda chocaría con la pared.
- La funda (12 × 6,5 de referencia) queda de z 2,275 a z 8,775, a 0,37 mm del suelo y a 0,5 del techo del corte. Pasa por encima de la pestaña exterior del suelo (z 0 a 1,905).
- Los bordes verticales del corte pueden llevar un radio de hasta 1 mm. El techo es un puente de 13 mm, sin problema en FDM.
- Montaje: la PCB entra en vertical desde arriba. El conector no sobresale de la pared, así que no hace falta inclinarla.

## 4. Zona de exclusión del mecanismo

- Agujero en la PCB: Ø11,3 con centro en (−60,88; −95,32). **Es un supuesto**: es la mejor estimación sin el Furby delante, a la espera de medirlo en el Furby.
- Exclusión: cilindro de **Ø15,3** con el mismo centro (2 mm alrededor del agujero), desde el suelo hasta la cara inferior de la PCB. Dentro no van separadores, nervios ni postes.
- El suelo de la base no tiene agujero ahí. Si el mecanismo tiene que atravesar el suelo, el agujero del suelo va con este mismo centro.

## 5. Agujeros originales del suelo: tapados, sin muescas en la PCB

Los 4 agujeros originales del suelo **se tapan** en la base modificada y el suelo queda **macizo**. La PCB **no lleva muescas**: pasa por encima de los 4. En el Furby real no hay tornillos ni torretas del cuerpo en esos agujeros, así que no hay nada que dejar libre.

| Agujero | Centro (x; y) | Diámetro | Centro a la pared interior | Centro al borde de la PCB (por dentro) |
|---------|---------------|----------|----------------------------|----------------------------------------|
| Delante izquierda | (−105,51; −78,23) | 2,13 | 1,67 | 0,65 |
| Delante derecha | (−41,33; −78,15) | 2,13 | 1,66 | 0,61 |
| Detrás izquierda | (−105,77; −106,80) | 2,13 | 1,68 | 0,57 |
| Detrás derecha | (−41,23; −106,83) | 2,13 | 1,61 | 0,60 |

- El tapón queda a ras de la cara superior del suelo (z 1,905), sin relieve: la franja bajo la PCB tiene que quedar libre (sección 6).
- Las cotas son de referencia, para situar los tapones. Están en la capa `AgujerosBase` del DXF.
- En `geometria.json`, `"muescas": null`. El script de la base salta la comprobación de muescas si el campo es `null` o no está (sección 7).
- Si algún día hiciera falta dejar libres esos agujeros, `contorno_suelo.py --muescas` vuelve a abrir muescas de R 3,0 (torreta supuesta de Ø5,0 + 0,5 de holgura) y `geometria.json` trae sus centros y radio.

## 6. Lo que la base no debe tocar

- Debajo de la PCB: patillas THT recortadas a 1,5 mm como máximo y componentes SMD de hasta 1,5 mm de alto. Deja libre la franja de z 1,905 a z 3,905 salvo en los separadores.
- Encima del conector: la carcasa del USB-C llega a z 7,105.

## 7. `geometria.json`

La escribe `scripts/contorno_suelo.py` y la leen `generar_kicad.py` y el script de la base. Mismas coordenadas que el DXF, en mm.

| Campo | Qué es |
|-------|--------|
| `contorno` | Primitivas del borde de la PCB, en orden: `{"tipo": "linea", "inicio", "fin"}` o `{"tipo": "arco", "inicio", "medio", "fin", "centro", "radio"}` |
| `mecanismo` | `centro`, `diametro` (11,3) y `exclusion_diametro` (15,3) |
| `funda` | Funda del cable: `ancho`, `alto` y `supuesto: true` |
| `taladros`, `taladro_diametro` | Centros de H1 a H4 y su diámetro (2,3) |
| `usb` | Posición del USB-C y de la ranura: `x`, `y_borde`, `y_boca`, `y_fondo`, `x_paredes`, `x_orejetas`, `boca_a_pared`, `y_pared_int`, `ranura_ancho`, `ranura_fondo` |
| `muescas` | **`null`**: la PCB no tiene muescas. Solo con `--muescas` es un objeto `{"centros": [[x, y] × 4], "radio", "redondeo", "torreta_diametro"}` |
| `alturas` | Cotas z del montaje: PCB, eje del USB-C, carcasa, funda y corte de la pared |
| `resultado` | Lo que mide el script: holgura, área, caja, distancias de taladros y mecanismo al borde, y `agujeros_base` (centro de cada agujero original y su distancia al borde de la PCB, positiva si queda debajo). Con `--muescas`, también `muescas` |

Quien lea `muescas` tiene que tratar `null` (o el campo ausente) como «sin muescas».

## Pendiente de confirmar

- Posición real del agujero del mecanismo (ahora es un supuesto).
- Tamaño de la funda del cable USB-C que se vaya a usar. Si es más alta que 6,5 mm, el corte crece hacia arriba (el eje no se mueve).
