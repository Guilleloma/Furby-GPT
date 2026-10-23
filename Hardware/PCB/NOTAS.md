# PCB del FurbyGPT: contorno y taladros

## Ficheros

| Fichero | Qué es |
|---------|--------|
| `FurbyPCB.dxf` | Contorno original del colaborador (fuente). Capa `Final`, mm. Sin el nombre del autor en la cabecera (`$LASTSAVEDBY`) |
| `FurbyPCB-suave.dxf` | Contorno suavizado (capa `Contorno`) y los 4 agujeros (capa `Taladros`) |
| `kicad/` | Proyecto KiCad 10 con el borde en `Edge.Cuts` y los taladros, sin componentes |
| `render/comparacion.png` | Original en gris frente al suavizado en azul, con cotas |
| `scripts/suavizar_contorno.py` | Genera todo lo anterior a partir de `FurbyPCB.dxf` |

## Cómo se suaviza

- Cada vértice convexo del polígono se cambia por un arco tangente a sus dos segmentos. El borde queda continuo en tangente, siempre por dentro del original, y solo usa líneas y arcos, que KiCad, el DXF y el Gerber representan de forma nativa.
- Los radios crecen todos a la vez hasta que cada arco toca su límite: la desviación máxima respecto al vértice original (`--desviacion`, 0,5 mm) o la longitud del segmento que comparte con el vecino. Así el radio más pequeño es el mayor posible.
- Los segmentos de menos de 2 mm entre dos vértices convexos (`--fusion`) se absorben en un solo arco. Pasa en el lateral izquierdo, en y ≈ 43 mm: el radio sube de 10,6 a 39 mm.
- El escalón de 0,137 mm de la esquina superior derecha (x = 67,42) era un vértice cóncavo. Se quita prolongando el lateral derecho hasta el borde superior, que corta un triángulo de 0,035 × 0,137 mm hacia dentro.
- El borde superior sigue recto entre x = 5,97 y x = 65,99 mm. Sus dos esquinas quedan con R 2,0 y R 1,8 mm.

## Resultados (desviación 0,5 mm)

- Desviación máxima medida, del original al nuevo: **0,500 mm**. Del nuevo al original: 0,484 mm. Ningún punto sale del contorno original.
- Caja: 71,29 × 58,98 mm (antes 71,34 × 58,98).
- Radios de 1,8 mm (esquinas superiores) a 144 mm.
- 19 arcos y 10 rectas, cerrado, sin autointersecciones (giro total de 360°).
- DRC de `kicad-cli`: 0 errores y 0 avisos.

| Agujero | Centro (mm) | Ø original | Ø nuevo | Borde del agujero a borde de placa |
|---------|-------------|-----------|---------|------------------------------------|
| H1 (M2) | 49,93; 56,38 | 2,35 | 2,3 | 1,45 mm |
| H2 (M2) | 17,28; 56,36 | 2,33 | 2,3 | 1,46 mm |
| H3 (M2) | 35,74; 16,07 | 2,32 | 2,3 | 14,92 mm |
| Recorte | 48,58; 31,02 | 11,28 | 11,3 | 17,11 mm |

## Decisiones

- **Taladros Ø2,3 sin cobre (NPTH)**, con el footprint propio `Furby:MountingHole_2.3mm_M2`. El de la librería de KiCad es de Ø2,2. Se mantiene Ø2,3 porque los centros vienen de un calco y 0,1 mm más de holgura absorbe su error. Sin anillo de cobre porque, con una pad de Ø4,4, el cobre de H1 y H2 quedaría a 0,4 mm del borde superior, por debajo de los 0,5 mm que usa KiCad por defecto. Para tornillos a postes de plástico no hace falta.
- **Recorte de Ø11,3 dibujado en `Edge.Cuts`**, no como taladro. JLCPCB fresa los agujeros de Ø6,3 mm o más, así que se trata como contorno interior.
- Los taladros llevan el atributo «no está en el esquema» (`board_only`), así que «Actualizar PCB desde el esquema» no los borra.
- Origen auxiliar y de rejilla en la esquina inferior izquierda del DXF, (100; 160) en la hoja. Con el origen de usuario ahí, las coordenadas de KiCad coinciden con las del DXF, con el eje Y invertido.

`FurbyPCB2.dxf` (la misma geometría más una capa `Componentes`) y `furby_pcb.dwg` no están en el repositorio: el repositorio es público y los dos llevan el nombre del colaborador en los metadatos.

## Fabricación (JLCPCB, de su página de capacidades)

- Tolerancia del contorno fresado: ±0,2 mm. En el peor caso, el borde puede quedar 0,2 mm por fuera del original.
- Cobre a borde fresado: ≥ 0,2 mm (KiCad usa 0,5 mm por defecto; se puede dejar así).
- Su página no da una distancia mínima de taladro a borde para agujeros normales; 1,45 mm sobra.

## Regenerar

```bash
cd Hardware/PCB
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -I scripts/suavizar_contorno.py --desviacion 0.5
```

- El script reescribe `FurbyPCB-suave.dxf` y `render/comparacion.png`. **No toca `kicad/FurbyGPT.kicad_pcb` ni el esquema si ya existen**, porque pueden tener componentes.
- Si cambias el contorno con la placa ya empezada: borra las líneas y arcos de `Edge.Cuts` e importa `FurbyPCB-suave.dxf` en KiCad (Archivo → Importar → Gráficos), en la capa `Edge.Cuts`, escala 1 y con el origen en (100; 160).
- `--forzar-kicad` regenera la placa desde cero y borra lo que tuviera.

## Pendiente de confirmar con el colaborador

- Para qué es el agujero de Ø11,28 (paso de un eje, de cables o de un altavoz) y si su diámetro es crítico.
- Si los taladros son para tornillos M2 o autorroscantes, y si algún tornillo necesita masa (entonces haría falta cobre y alejarlo del borde superior).
- Si el borde superior y sus esquinas apoyan en algo de la carcasa. Las esquinas pasan a R 2 mm.
- Si las medidas salen de la placa original o de un calco. La desviación de 0,5 mm se suma a la precisión del calco.
