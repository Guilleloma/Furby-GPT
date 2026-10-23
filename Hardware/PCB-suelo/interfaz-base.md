# Contrato PCB ↔ base impresa (para el 3d-architect)

Todas las cotas en mm y en el **sistema de coordenadas del STL de la base del Furby de 1998**: vista desde arriba (+Z), delante = y máxima, detrás (lóbulo) = y mínima. La cara superior del suelo está en **z = 1,905**.

Fichero de referencia: `contorno-pcb.dxf` (mismas coordenadas, sin transformar).

| Capa del DXF | Qué es |
|--------------|--------|
| `Contorno` | Borde de la PCB, con la ranura del USB-C. 57 arcos y 32 rectas, cerrado |
| `Taladros` | 4 taladros M2 Ø2,3 |
| `Mecanismo` | Agujero de Ø11,3 del mecanismo |
| `ExclusionMecanismo` | Zona de exclusión de Ø15,3 alrededor del mecanismo |
| `UsbC` | Planta del cuerpo del USB-C (8,94 × 6,80), desde la boca |

## 1. PCB

| Dato | Valor |
|------|-------|
| Grosor | **1,6** (FR-4, tolerancia de fábrica ±10 %) |
| Cara inferior | z **3,905** |
| Cara superior | z **5,505** |
| Caja | x −108,42 … −38,58 (69,85) · y −128,10 … −52,71 (75,39) |
| Holgura a la pared interior | **0,50 mín.** y 0,70 máx. por lado (fuera de la ranura del USB-C) |

El contorno es el suelo interior encogido 0,5 mm, así que la pared interior **no puede moverse hacia dentro** en la base modificada. Si se engrosa la pared, que sea hacia fuera.

## 2. Separadores

| Dato | Valor |
|------|-------|
| Altura sobre el suelo | **2,0** (de z 1,905 a z 3,905) |
| Diámetro recomendado | 5,0 (la cabeza del M2 mide Ø4,0 y la PCB deja libre Ø5,0 alrededor de cada taladro) |
| Tornillo | M2 autorroscante para plástico, de 4 o 5 mm bajo cabeza. Con 5 mm entra 3,4 mm en el plástico, que tiene 3,9 mm (separador más suelo), así que no asoma por debajo |
| Alternativa | Inserto roscado M2 de 3,0 mm de largo. Necesita un separador de Ø5 o más y un alojamiento de 3,5 mm de profundidad, que entra en el suelo |

| Taladro | Centro (x; y) | Borde de agujero a borde de PCB | A borde del agujero del mecanismo |
|---------|---------------|---------------------------------|-----------------------------------|
| H1 | (−97,00; −68,50) | 3,52 | 38,19 |
| H2 | (−50,00; −68,50) | 3,58 | 22,14 |
| H3 | (−86,80; −122,40) | 2,55 | 30,69 |
| H4 | (−60,20; −122,40) | 2,59 | 20,29 |

H3 y H4 flanquean el USB-C (7,5 mm de la ranura cada uno) para que la placa no cabecee al enchufar el cable. Los 4 agujeros originales de la base (Ø2,13) no se usan para la PCB.

## 3. Corte en la pared del lóbulo para el USB-C

| Dato | Valor |
|------|-------|
| Centro en x | **−73,50** |
| Ancho | **13,0** (x −80,00 … −67,00): funda de 12 + 0,5 por lado |
| z inferior | **1,905**, a ras de la cara superior del suelo |
| z superior | **9,255** |
| Alto | 7,35 |
| Profundidad | Todo el grosor de la pared trasera del lóbulo (1,70) |
| Eje del conector | z **5,505**, a 3,60 sobre el suelo |
| Boca del conector | y **−128,49**, a 0,30 de la cara interior de la pared (y −128,80 en x −73,5) |

- **Por qué el corte es tan alto:** la boca del conector queda 2,0 mm por dentro de la cara exterior de la pared (0,3 de aire más 1,7 de pared). Con el cable enchufado, la funda sobremoldeada entra esos 2 mm en el corte. Si el corte fuera solo del tamaño del conector (8,94 × 3,16), la funda chocaría con la pared.
- La funda (12 × 6,5 de referencia) queda de z 2,255 a z 8,755, a 0,35 mm del suelo y a 0,5 del techo del corte. Pasa por encima de la pestaña exterior del suelo (z 0 a 1,905).
- Los bordes verticales del corte pueden llevar un radio de hasta 1 mm. El techo es un puente de 13 mm, sin problema en FDM.
- Montaje: la PCB entra en vertical desde arriba. El conector no sobresale de la pared, así que no hace falta inclinarla.

## 4. Zona de exclusión del mecanismo

- Agujero en la PCB: Ø11,3 con centro en (−60,88; −95,32). **Es un supuesto**: es la mejor estimación sin el Furby delante, a la espera de medirlo en el Furby.
- Exclusión: cilindro de **Ø15,3** con el mismo centro (2 mm alrededor del agujero), desde el suelo hasta la cara inferior de la PCB. Dentro no van separadores, nervios ni postes.
- El suelo de la base no tiene agujero ahí. Si el mecanismo tiene que atravesar el suelo, el agujero del suelo va con este mismo centro.

## 5. Lo que la base no debe tocar

- Debajo de la PCB: patillas THT recortadas a 1,5 mm como máximo y componentes SMD de hasta 1,5 mm de alto. Deja libre la franja de z 1,905 a z 3,905 salvo en los separadores.
- Encima del conector: la carcasa del USB-C llega a z 7,085.

## Pendiente de confirmar

- Posición real del agujero del mecanismo (ahora es un supuesto).
- Los 4 agujeros originales de la base (Ø2,13, centros a 1,6 mm de la pared) quedan **tapados por la PCB**. Si en la base modificada tienen que pasar tornillos desde abajo hacia el cuerpo del Furby, hay que hacer muescas en la PCB.
- Tamaño de la funda del cable USB-C que se vaya a usar. Si es más alta que 6,5 mm, el corte crece hacia arriba (el eje no se mueve).
