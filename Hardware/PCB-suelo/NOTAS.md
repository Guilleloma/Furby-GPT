# PCB del FurbyGPT con la forma del suelo de la base

La PCB va dentro de la base del Furby de 1998 (impresa y modificada), sobre separadores apoyados en su suelo. Su contorno es el suelo interior menos una holgura, con el lóbulo trasero incluido. El USB-C de alimentación asoma por un corte en la pared del lóbulo.

Sustituye al planteamiento de `Hardware/PCB/`: el contorno del colaborador (`FurbyPCB-suave.dxf`) invade la pared entre 1,2 y 1,6 mm y solo sirvió para situar el agujero del mecanismo.

## Ficheros

| Fichero | Qué es |
|---------|--------|
| `contorno-pcb.dxf` | Contorno de la PCB, taladros, mecanismo, exclusión, planta del USB-C, agujeros originales de la base y radio libre de sus muescas, en coordenadas del STL |
| `interfaz-base.md` | Contrato para el diseño de la base: separadores, corte de la pared y exclusiones |
| `geometria.json` | Geometría calculada; es la entrada de `generar_kicad.py` |
| `kicad/` | Proyecto KiCad 10: esquema mínimo y placa con el USB-C colocado y rutado |
| `render/planta.png` | PCB sobre el suelo de la base, con taladros, muescas, ranura y corte |
| `render/lateral-lobulo.png` | Corte por x = −73,5: suelo, separador, PCB, USB-C, funda del cable y corte de la pared |
| `scripts/contorno_suelo.py` | Calcula el contorno y escribe el DXF, `geometria.json` y los renders |
| `scripts/generar_kicad.py` | Crea el proyecto KiCad (se ejecuta con el Python de KiCad) |

El STL y el DXF del suelo de la base son de un tercero y no están en el repositorio. Aquí solo está el contorno de la PCB derivado de ellos.

## Coordenadas

- Todo va en las coordenadas del STL de la base: mm, vista desde arriba, **delante = y máxima**, **detrás = y mínima** (lóbulo y USB-C). El agujero del mecanismo queda a la derecha (x mayor).
- En KiCad el eje Y va hacia abajo: `x_kicad = x + 220` y `y_kicad = −40 − y`. El origen auxiliar y el de la rejilla están en (220; −40), que es el origen del STL. Con el origen de usuario ahí y el eje Y invertido en la vista, KiCad muestra las coordenadas del STL.

## Contorno

1. **Encoger el suelo 0,5 mm** con esquinas en inglete (`shapely`, `buffer` negativo). Cada lado queda paralelo a su pared, y en las esquinas cóncavas el inglete queda más lejos de la pared, nunca más cerca.
2. **Quitar las facetas por dentro.** Es un Douglas-Peucker que solo acepta cuerdas con todos los vértices sustituidos del lado de la pared, a 0,12 mm como máximo. De 100 vértices quedan 64. Los 4 vértices cóncavos de los hombros del lóbulo se conservan siempre.
3. **Fillets.** Cada vértice convexo se sustituye por un arco tangente, a 0,2 mm como máximo de su vértice, con el mismo llenado progresivo de radios que `Hardware/PCB/scripts/suavizar_contorno.py`. Cada vértice cóncavo de más de 3° se sustituye por un arco de R 0,5 mm centrado en la esquina de la pared. Es el radio de la fresa de JLCPCB y mantiene la holgura exacta. Los quiebros cóncavos de menos de 3° son ruido de las facetas y quedan sin arco.
4. **Ranura del USB-C** en el borde trasero, centrada en x = −73,5: 9,24 de ancho × 6,70 de fondo, con alivios semicirculares de R 0,5 en las esquinas del fondo para que la fresa no deje material donde apoyan las esquinas del cuerpo.
5. **Muescas en los 4 agujeros originales del suelo.** Un arco cóncavo de R 3,0 (`--muesca-r`) centrado en cada agujero, y sus dos esquinas con el borde redondeadas con arcos convexos de R 0,5 (`--muesca-redondeo`), sin picos. Los centros se leen de la capa `Agujeros` del DXF del suelo.

El script comprueba que el contorno cierra, que no se corta a sí mismo, que está dentro del suelo, que ningún punto queda a menos de la holgura de la pared (muestreo cada 0,01 mm) y que no hay PCB a menos de `--muesca-r` del centro de ningún agujero original.

### Resultados

| Medida | Valor |
|--------|-------|
| Holgura PCB-pared | **0,500 mín.**, 0,697 máx. (fuera de la ranura y de las muescas) |
| Caja | 69,85 × 75,39 mm (las muescas no la cambian) |
| Área | 4165 mm² (4248 sin muescas; el suelo tiene 4437) |
| Primitivas | 66 arcos y 30 rectas; radios de 0,5 a 60,5 mm |
| Perímetro | 272,15 mm |
| PCB al centro de cada agujero original | 3,000 mm, en los 4 |

### Muescas de los agujeros originales: R 3,0

Los 4 agujeros originales del suelo (Ø2,13) pasan tornillos hacia el cuerpo del Furby, y una torreta del cuerpo baja hasta el suelo a recibirlos. La PCB los tapaba, así que lleva una muesca en cada uno.

- **Torreta supuesta de Ø5,0.** Por el agujero de Ø2,13 pasa un tornillo de unos 2 mm. La regla habitual para torretas de tornillo autorroscante en plástico es un diámetro exterior de 2 a 2,5 veces el del tornillo: de 4,0 a 5,0 mm. Se toma el extremo alto.
- **Holgura de 0,5 por lado**, la misma que entre PCB y pared: ±0,2 del fresado de JLCPCB, unos 0,2 de la impresión y 0,1 de margen.
- **R = 5,0 / 2 + 0,5 = 3,0 mm.** Si la torreta real mide otra cosa: `--muesca-r` = radio de la torreta + 0,5, y el mismo valor en `test_contorno.py --muesca-r`.
- Los centros quedan a 1,61-1,68 mm de la pared interior y a 1,1 mm por dentro del borde de la PCB, así que cada muesca se come un sector de unos 200° de un círculo de R 3,0. Quita 83 mm² en total.
- El arco de la muesca es cóncavo de R 3,0, por encima del radio de la fresa de JLCPCB (0,5). Las esquinas donde la muesca corta el borde serían picos de unos 70°: se redondean con R 0,5.
- Distancias que salen: H1 y H2 quedan a 8,8 mm del borde de su muesca más cercana, H3 y H4 a 20,4. Ningún taladro se mueve y su distancia al borde de la PCB no cambia (mínimo 2,55, en H3). El agujero del mecanismo queda a 14,1 mm de la muesca más cercana, que ahora es su borde de PCB más próximo.

### Por qué 0,5 mm de holgura

- JLCPCB fresa el contorno con ±0,2 mm de tolerancia (CNC normal), así que la placa puede salir 0,2 mm más grande por lado.
- En FDM los contornos interiores salen más pequeños, unos 0,1-0,2 mm por lado, según la impresora y el ancho de línea.
- Peor caso: 0,2 + 0,2 = 0,4 mm, y aún sobran 0,1 mm. Con 0,3 mm de holgura la placa podría no entrar, y con 1,0 mm bailaría y perdería área sin necesidad.

## USB-C de alimentación

**Elegido: HRO TYPE-C-31-M-28A, LCSC C2848622.** USB-C hembra de 6 pines (solo alimentación), de montaje medio en ranura para PCB de 1,6 mm. Admite 5 A y 20 V, y 3000 ciclos. A 23-10-2026 tenía 15 510 unidades en stock en JLCPCB (pieza extendida, 0,13 USD por unidad).

Según el dibujo del fabricante, con PCB de 1,6 mm el eje de la boca queda **a ras de la cara superior** y la carcasa queda a ras de la cara inferior: no asoma nada por debajo. La boca sobresale 0,2 mm del borde de la PCB. Esa cota no está en el dibujo: sale de comparar el alzado (patas delanteras a 2,8 mm de la boca) con el layout (a 2,6 mm del borde).

### Montaje medio frente a montaje en superficie

Altura del eje sobre el suelo = separador + grosor de la PCB + altura del eje sobre la cara superior.

| Opción | Pieza | Eje sobre la cara superior | Eje sobre el suelo (separador de 2,0) | z del eje (STL) | Bajo la PCB |
|--------|-------|----------------------------|---------------------------------------|-----------------|-------------|
| **Montaje medio** | HRO TYPE-C-31-M-28A (C2848622) | 0 | **3,60** | 5,505 | Nada |
| Superficie | HRO TYPE-C-31-M-17 (C283540) | 1,63 (0,05 de apoyo + 3,16 / 2) | 5,23 | 7,135 | Patas THT de 0,8 mm, no atraviesan la PCB |

El montaje medio deja el conector **1,63 mm más bajo** con los mismos separadores. A cambio, la PCB necesita la ranura y JLCPCB no se responsabiliza si la ranura no coincide con la pieza.

Alternativa con stock, sin verificar: SHOU HAN TYPE-C 6P CB1.6(073), C2858274 (26 694 en stock), también de montaje medio para 1,6 mm. Su huella es distinta: habría que hacerla desde su hoja de datos.

### Huella

`kicad/Furby.pretty/USB_C_Receptacle_HRO_TYPE-C-31-M-28A.kicad_mod`, hecha a partir del layout recomendado del fabricante. El origen está en el borde de la PCB y la boca mira a +Y.

- Pads de señal de 0,9 (A12, B12), 0,8 (A9, B9) y 0,7 (A5, B5) de ancho, con centros en ±2,75, ±1,52 y ±0,50.
- **Cambio respecto al dibujo:** en el dibujo las pads empiezan justo en el fondo de la ranura. Aquí empiezan 0,3 mm más atrás (1,1 de largo en vez de 1,4) para respetar 0,3 mm de cobre a borde fresado. La patilla solapa 0,45 mm con la pad, más el menisco. Si se quiere la pad entera, bajar `BORDE_COBRE_MM` a 0,2 (el mínimo de JLCPCB) y alargarla.
- 4 patas de la carcasa en ranuras metalizadas: 0,5 × 1,7 delante y 0,5 × 1,3 detrás, a x ±5,575. El ancho de 0,5 es justo el mínimo de JLCPCB para ranuras metalizadas.

## Esquema

Mínimo: J1 con VBUS (A9, B9), GND (A12, B12 y la carcasa) y una **Rd de 5,1 kΩ a GND en CC1 y en CC2** (R1 y R2: 0603, UNI-ROYAL 0603WAF5101T5E, LCSC C23186, pieza básica). Con Rd, cualquier cargador USB-C entrega 5 V. El PWR_FLAG va en VBUS y GND.

Rutado: VBUS une A9 y B9 por detrás de las pads, con una pista de 0,5 mm. CC1 y CC2 pasan por debajo (B.Cu) hasta sus resistencias, y GND va a un plano en la cara inferior. Sin componentes en la cara inferior.

**ERC: 0 errores y 0 avisos. DRC de la placa tal como está guardada, sin volver a rellenar zonas: 0 errores, 0 avisos, 0 sin conectar y 0 diferencias con el esquema.** El plano de GND se rellena como último paso de `generar_kicad.py`, con la placa ya guardada y vuelta a cargar. Si se rellena antes, en memoria, no recorta los taladros ni el agujero del mecanismo.

## Separadores: 2,0 mm

- **Funda del cable.** La boca queda 2,0 mm por dentro de la cara exterior de la pared, así que la funda del cable (12 × 6,5 de referencia) entra en el corte por encima del suelo. Para que no lo toque con 0,3 mm de margen, el eje tiene que quedar a z ≥ 1,905 + 3,25 + 0,3 = 5,455. Con montaje medio, el separador mínimo es 5,455 − 1,905 − 1,6 = **1,95 mm**.
- **Patillas THT por debajo.** Recortadas a 1,5 mm como máximo, con 0,5 mm de aire hasta el suelo: también salen 2,0 mm.
- Con 2,0 mm: eje en z 5,505 (3,60 sobre el suelo), funda a 0,35 mm del suelo, corte de z 1,905 a 9,255.
- Bajar de 2,0 mm obligaría a rebajar el suelo bajo el corte y a usar solo SMD de menos de 1 mm por debajo. Gana muy poco: cada 0,5 mm de separador baja el eje 0,5 mm.

## Taladros

4 × M2 Ø2,3 sin cobre (NPTH), con la cabeza del tornillo marcada en `Cmts.User` y courtyard de Ø5 en las dos caras. Lejos del mecanismo (≥ 20,3 mm de borde a borde), del USB-C (7,5 mm de la ranura) y de las muescas (≥ 8,8 mm). Todos a ≥ 2,55 mm del borde de la PCB. Centros y distancias en `interfaz-base.md`.

H1 y H2 forman un trapecio con H3 y H4: 47 mm de ancho delante, 26,6 detrás y 53,9 de fondo. H3 y H4 están junto al USB-C, que es por donde entra la fuerza de enchufar el cable (0,5-2,0 kgf según el dibujo de HRO).

## Fabricación (JLCPCB)

- Contorno fresado con ±0,2 mm. Fresa de 0,5 mm de radio en los cortes interiores: los arcos cóncavos de R 0,5 del contorno y los alivios de la ranura ya tienen ese radio.
- Cobre a borde: 0,3 mm en las reglas del proyecto (el mínimo de JLCPCB es 0,2).
- Agujero del mecanismo dibujado en `Edge.Cuts` (Ø11,3, se fresa).
- Muescas de R 3,0 en el contorno, con las esquinas en R 0,5. Las torretas supuestas (Ø5,0) van en `Cmts.User` como referencia; no se fabrican.
- Ranuras metalizadas de 0,5 mm de ancho: el mínimo de JLCPCB.

## Regenerar

```bash
cd Hardware/PCB-suelo
python3 -m venv .venv && .venv/bin/pip install -r scripts/requirements.txt
.venv/bin/python -I scripts/contorno_suelo.py --suelo <ruta a suelo-interior.dxf>
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \
    scripts/generar_kicad.py --forzar
```

- Parámetros del primer script: `--holgura`, `--simplificacion`, `--desviacion`, `--mecanismo X Y`, `--usb-x`, `--taladro X Y` (repetible), `--muesca-r` y `--muesca-redondeo`.
- `generar_kicad.py` **sobrescribe la placa y el esquema**. Cuando la placa tenga componentes a mano, no lo vuelvas a ejecutar. Para cambiar el contorno, borra `Edge.Cuts` e importa `contorno-pcb.dxf` (capa `Contorno`) en `Edge.Cuts`, con escala 1 y el origen en (220; −40) con el eje Y invertido.
- Las tablas de librerías del proyecto apuntan a las librerías de KiCad (`${KICAD10_SYMBOL_DIR}` y `${KICAD10_FOOTPRINT_DIR}`), porque las tablas globales de este Mac están vacías.

## Comprobar

```bash
cd Hardware/PCB-suelo
# Contorno: cerrado y sin autointersecciones, 4 taladros M2 en su sitio a ≥ 2,5 mm del borde,
# mecanismo y exclusión dentro de la PCB, y sin PCB a menos de 3,0 mm (--muesca-r) de los
# 4 agujeros originales del suelo. Sale con código 1 si algo falla.
.venv/bin/python -I scripts/test_contorno.py
# Lo mismo, más la holgura de ≥ 0,5 mm contra el suelo (el DXF del suelo no está en el repo)
.venv/bin/python -I scripts/test_contorno.py --suelo <ruta a suelo-interior.dxf>

cd kicad
KICAD_CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
$KICAD_CLI sch erc --exit-code-violations FurbyGPT-suelo.kicad_sch
# Sin --refill-zones: comprueba la placa tal como está commiteada
$KICAD_CLI pcb drc --schematic-parity --exit-code-violations FurbyGPT-suelo.kicad_pcb
```

- Si cambias los taladros con `--taladro`, actualiza `TALADROS_ESPERADOS` en `scripts/test_contorno.py`.
- Si cambias `--muesca-r`, pásale el mismo valor al test con `--muesca-r`.
- `contorno_suelo.py` reescribe el DXF con fecha y GUID nuevos en la cabecera aunque la geometría no cambie. Si solo cambia eso, no hace falta commitearlo.

## Verificado y supuesto

| Dato | Estado |
|------|--------|
| Suelo interior, pared y alturas de la base | Medido en el STL (3d-modeler) |
| Holgura de 0,500 mm mínimo | Verificado por el script en todo el contorno |
| Cotas del USB-C (pads, ranuras, ranura de la PCB, eje a ras de la cara superior) | Hoja de datos de HRO |
| Boca 0,2 mm fuera del borde de la PCB | Deducido del dibujo; no viene acotado |
| Agujero del mecanismo en (−60,88; −95,32), Ø11,3 | **Supuesto**: colocación del contorno del colaborador sin girar |
| Funda del cable de 12 × 6,5 | **Supuesto**: medida típica; falta medir el cable real |
| Centros de los 4 agujeros originales del suelo | Medido en el STL (capa `Agujeros` del DXF del suelo) |
| Torreta del cuerpo de Ø5,0 | **Supuesto**: proporción típica para un tornillo de unos 2 mm; falta medirla en el cuerpo |
| Tolerancia FDM de ±0,2 mm por lado | Estimación habitual, sin medir en la impresora que se vaya a usar |

## Pendiente de confirmar

1. Medir el agujero del mecanismo en el Furby (centro y diámetro) y regenerar con `--mecanismo X Y`.
2. Medir el diámetro de las torretas del cuerpo que bajan a los 4 agujeros originales y regenerar con `--muesca-r` = radio + 0,5 si no es Ø5,0.
3. Medir la funda del cable USB-C que se vaya a usar.
4. Consumo: con solo Rd en CC, la fuente no anuncia corriente al Furby. Un cargador de 5 V suele dar 2-3 A, pero el puerto USB de un ordenador puede limitar a 0,5-0,9 A. Raspberry Pi Zero W, WM8960 y motor pueden pasar de eso en los picos. Cuando se añada el resto del circuito: fusible rearmable, TVS de 5 V y condensador de bulk junto al conector.
