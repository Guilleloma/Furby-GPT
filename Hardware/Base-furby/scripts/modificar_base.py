#!/usr/bin/env python3
"""Base del Furby de 1998 modificada para alojar la PCB de FurbyGPT.

Sobre el STL original añade 4 separadores con piloto para tornillo M2 × 4, tapa los
4 agujeros originales del suelo, abre la ventana del USB-C en la pared del lóbulo y
rebaja la cara interior encima. Todo lo demás queda igual.
Booleanas de malla con manifold3d; cotas en parametros-base.json y en
Hardware/PCB-suelo/geometria.json.

Verifica antes de escribir (verificar_base.py, comprobaciones A a I). Si algo
falla, sale con código 1 y no escribe los STL, salvo con --forzar.

Uso (desde Hardware/Base-furby, con el venv):
    python -I scripts/modificar_base.py --base-stl <STL original> --salida <carpeta fuera del repo>
Salidas: FurbyGPT-base-modificada.stl, prueba-lobulo.stl, cupon-pilotos.stl,
pcb-fantasma.stl (solo para renders) y verificacion.json.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import verificar_base  # noqa: E402


def comprobar_original(original, original_m):
    """Paso 0: la malla de partida tiene que ser un sólido cerrado de un cuerpo."""
    cuerpos = len(original.split(only_watertight=False))
    if not (original.is_watertight and original.is_winding_consistent and cuerpos == 1):
        raise SystemExit("El STL original no es un sólido cerrado de un cuerpo: hay que repararlo antes "
                         f"(watertight={original.is_watertight}, normales={original.is_winding_consistent}, "
                         f"cuerpos={cuerpos})")
    return {"watertight": True, "normales_coherentes": True, "cuerpos": cuerpos,
            "genero": original_m.genus(), "volumen": original_m.volume(), "triangulos": len(original.faces)}


def construir(original_m, geo, par, der, medidas):
    """Aplica las operaciones. Si la malla no sale limpia (género, un cuerpo, cerrada y sin
    triángulos degenerados), repite bajando la ventana eps_coplanar. Los tapones no se
    desplazan: tienen que quedar a ras de las dos caras del suelo."""
    area_min = par["verificacion"]["triangulo_degenerado_area"]
    for desfase in (0.0, par["eps_coplanar"]):
        ops = comun.operaciones(geo, par, der, medidas["cavidad"], medidas["agujeros"], desfase)
        resultado = comun.aplicar(original_m, ops, par["tolerancia_malla"])
        malla = comun.a_trimesh(resultado)
        genero = comun.genero_esperado(original_m.genus(), ops)
        if (resultado.genus() == genero and len(resultado.decompose()) == 1
                and malla.is_watertight and not (malla.area_faces < area_min).any()):
            return resultado, ops, desfase
        print(f"Malla no limpia con desfase {desfase} (género {resultado.genus()}); se reintenta")
    raise SystemExit("La booleana no sale limpia ni desplazando el corte eps_coplanar")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--base-stl", type=Path, required=True, help="STL original de la base")
    parser.add_argument("--salida", type=Path, required=True, help="carpeta de salida, fuera del repositorio")
    parser.add_argument("--geometria", type=Path, default=comun.GEOMETRIA)
    parser.add_argument("--parametros", type=Path, default=comun.PARAMETROS)
    parser.add_argument("--forzar", action="store_true",
                        help="escribe los STL aunque falle alguna comprobación (para inspeccionar)")
    args = parser.parse_args()

    salida_dir = comun.comprobar_salida_fuera_del_repo(args.salida)
    par, geo, original, medidas, der, huella = verificar_base.preparar(args.base_stl, args.geometria,
                                                                       args.parametros)
    original_m = comun.a_manifold(original)
    estado_original = comprobar_original(original, original_m)

    base_m, ops, desfase = construir(original_m, geo, par, der, medidas)
    base = comun.a_trimesh(base_m)
    base_m = comun.a_manifold(base)   # la misma malla que se escribe, para que la verificación mida eso
    fantasma_m = comun.pcb_fantasma(geo, par, der)

    comprobaciones = verificar_base.verificar(original, original_m, base, base_m, fantasma_m,
                                              geo, par, medidas, der, ops)
    prueba = comun.prueba_lobulo(base_m, par)
    cupon, diametros = comun.cupon_pilotos(geo, par, der)
    extra = {
        "sha256_original": huella,
        "original": estado_original,
        "desfase_ventana": desfase,
        "features": list(ops),
        "caja_salida": [list(base.bounds[0]), list(base.bounds[1])],
        "prueba_lobulo": {"volumen": prueba.volume(), "cuerpos": len(prueba.decompose()),
                          "caja": list(prueba.bounding_box())},
        "cupon_pilotos": {"diametros": diametros, "volumen": cupon.volume(), "cuerpos": len(cupon.decompose()),
                          "caja": list(cupon.bounding_box()), "marca": "esquina recortada junto al Ø más estrecho"},
    }
    datos = verificar_base.informe(comprobaciones, der, medidas, extra)
    verificar_base.resumen(comprobaciones)

    salida_dir.mkdir(parents=True, exist_ok=True)
    (salida_dir / comun.NOMBRE_VERIFICACION).write_text(verificar_base.a_json(datos), encoding="utf-8")
    if not datos["aprobado"] and not args.forzar:
        print("Hay comprobaciones en rojo: no se escriben los STL (ver verificacion.json)")
        sys.exit(1)
    comun.escribir_stl(base_m, salida_dir / comun.NOMBRE_BASE)
    comun.escribir_stl(prueba, salida_dir / comun.NOMBRE_PRUEBA)
    comun.escribir_stl(cupon, salida_dir / comun.NOMBRE_CUPON)
    comun.escribir_stl(fantasma_m, salida_dir / comun.NOMBRE_FANTASMA)
    print(f"STL escritos en {salida_dir}")
    sys.exit(0 if datos["aprobado"] else 1)


if __name__ == "__main__":
    main()
