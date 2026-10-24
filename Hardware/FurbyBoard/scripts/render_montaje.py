#!/usr/bin/env python3
"""Render de la FurbyBoard montada sobre la base, con la batería encima.

Se ejecuta con el Python de KiCad:
    $KICAD_PY scripts/render_montaje.py

1. kicad-cli exporta la placa a GLB (componentes, pistas, serigrafía y máscara)
   con el origen en el (0,0) del STL de la base.
2. La base se dibuja simplificada a partir del contorno de la PCB: suelo y pared
   a la holgura de geometria.json (el STL de la base es de un tercero y no está
   en el repositorio). Las alturas salen de geometria.json.
3. La batería es una caja de 33 × 50 mm en su posición (layout.BATERIA), apoyada
   en los calzos de 4,1 mm. Su grosor (6,0 mm) es estimado.
4. Blender (sin interfaz) monta la escena y renderiza dos vistas.
"""
import json
import os
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LAY  # noqa: E402
import params as P  # noqa: E402

KICAD_CLI = os.environ.get("KICAD_CLI", "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
BLENDER = os.environ.get("BLENDER", "/Applications/Blender.app/Contents/MacOS/Blender")
SALIDA = os.path.join(P.ROOT, "render")
GROSOR_BATERIA = 6.0
HUECO_BATERIA = 4.1
PARED = 1.7
SEPARADOR = 2.0      # separadores de la base bajo los taladros (interfaz-base.md)

ESCENA = r'''
import bpy, json, math, sys
d = json.load(open(sys.argv[sys.argv.index("--") + 1]))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
try:
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 64
except TypeError:
    pass
sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
sc.render.film_transparent = False

def material(nombre, rgba, alpha=1.0):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = rgba
    if alpha < 1:
        bsdf.inputs["Alpha"].default_value = alpha
    return m

def prisma(nombre, anillos, z0, z1, mat):
    """Extruye un polígono (primer anillo) con agujeros (resto) entre z0 y z1."""
    import bmesh
    bm = bmesh.new()
    caras = []
    for anillo in anillos:
        vs = [bm.verts.new((x, y, z0)) for x, y in anillo]
        caras.append(vs)
    bm.verts.ensure_lookup_table()
    edges = []
    for vs in caras:
        for i in range(len(vs)):
            edges.append(bm.edges.new((vs[i], vs[(i + 1) % len(vs)])))
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    for f in bm.faces:
        f.normal_update()
    geom = bm.faces[:] + bm.edges[:] + bm.verts[:]
    ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z = z1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(nombre, me)
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob

base = material("base", (0.85, 0.82, 0.76, 1))
prisma("suelo", [d["pared_ext"]], 0.0, d["suelo_z"], base)
prisma("pared", [d["pared_ext"], d["pared_int"]], d["suelo_z"], d["pared_z"], base)
for x, y in d["separadores"]:
    bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=d["pcb_z"] - d["suelo_z"],
                                        location=(x, y, (d["pcb_z"] + d["suelo_z"]) / 2))
    bpy.context.active_object.data.materials.append(base)
bpy.ops.import_scene.gltf(filepath=d["glb"])
# El GLB de KiCad va en metros: a mm, y sobre los separadores
for ob in bpy.context.selected_objects:
    if ob.parent is None:
        ob.scale = (1000 * ob.scale[0], 1000 * ob.scale[1], 1000 * ob.scale[2])
        ob.location = (1000 * ob.location[0], 1000 * ob.location[1], 1000 * ob.location[2] + d["pcb_z"])
bat = material("bateria", (0.15, 0.32, 0.65, 1))
bpy.ops.mesh.primitive_cube_add(size=1, location=(d["bat"][0], d["bat"][1], d["bat_z"] + d["bat_h"] / 2))
c = bpy.context.active_object
c.scale = (d["bat_w"], d["bat_l"], d["bat_h"])
c.rotation_euler.z = math.radians(d["bat_giro"])
c.data.materials.append(bat)
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
for loc, e in (((-40, -60, 120), 900), ((-140, -150, 80), 500)):
    l = bpy.data.lights.new("l", "AREA"); l.energy = e * 40; l.size = 80
    o = bpy.data.objects.new("l", l); o.location = loc; bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(30), 0, 0)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); bpy.context.collection.objects.link(cam)
sc.camera = cam
cx, cy = d["centro"]
for nombre, pos in d["vistas"].items():
    cam.location = (cx + pos[0], cy + pos[1], pos[2])
    direc = (cx - cam.location.x, cy - cam.location.y, 6 - cam.location.z)
    import mathutils
    cam.rotation_euler = mathutils.Vector(direc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 50
    sc.render.filepath = d["salida"] + "/" + nombre
    bpy.ops.render.render(write_still=True)
'''


def contorno(board, crece):
    """Contorno de la PCB (sin la ranura del USB-C, que la pared no tiene) crecido `crece` mm."""
    ps = pcbnew.SHAPE_POLY_SET()
    board.GetBoardPolygonOutlines(ps, True)
    usb = json.load(open(P.GEOMETRIA, encoding="utf-8"))["usb"]
    ranura = pcbnew.SHAPE_POLY_SET()
    ranura.NewOutline()
    x0, x1 = [pcbnew.FromMM(v + P.STL_OX) for v in usb["x_paredes"]]
    y0, y1 = [pcbnew.FromMM(P.STL_OY - v) for v in (usb["y_fondo"] + 0.1, usb["y_borde"] - 0.05)]
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ranura.Append(x, y)
    ps.BooleanAdd(ranura)
    ps.Inflate(pcbnew.FromMM(crece), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.05))
    o = ps.Outline(0)
    return [(pcbnew.ToMM(o.CPoint(k).x) - P.STL_OX, P.STL_OY - pcbnew.ToMM(o.CPoint(k).y)) for k in range(o.PointCount())]


def main():
    geo = json.load(open(P.GEOMETRIA, encoding="utf-8"))
    alt = geo["alturas"]
    holgura = geo["resultado"]["holgura_min"]
    board = pcbnew.LoadBoard(P.PCB)
    os.makedirs(SALIDA, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        glb = os.path.join(tmp, "placa.glb")
        subprocess.run([KICAD_CLI, "pcb", "export", "glb", "--force", "--subst-models", "--drill-origin",
                        "--include-tracks", "--include-pads", "--include-zones", "--include-silkscreen",
                        "--include-soldermask", "-o", glb, P.PCB], check=True, capture_output=True)
        bt = LAY.BATERIA
        datos = {
            "glb": glb, "salida": SALIDA,
            "pared_int": contorno(board, holgura), "pared_ext": contorno(board, holgura + PARED),
            "suelo_z": alt["z_pcb_inf"] - SEPARADOR, "separadores": geo["taladros"],
            "pared_z": alt["z_pcb_sup"] + 3.0,
            "pcb_z": alt["z_pcb_inf"],
            "bat": bt["centro"], "bat_w": bt["ancho"], "bat_l": bt["largo"], "bat_giro": bt["giro"],
            "bat_z": alt["z_pcb_sup"] + HUECO_BATERIA, "bat_h": GROSOR_BATERIA,
            "centro": [-73.5, -90.0],
            "vistas": {"montaje-iso.png": [55, -85, 95], "montaje-usb.png": [-20, -95, 45]},
        }
        js = os.path.join(tmp, "escena.json")
        json.dump(datos, open(js, "w"))
        py = os.path.join(tmp, "escena.py")
        open(py, "w").write(ESCENA)
        subprocess.run([BLENDER, "-b", "--factory-startup", "-P", py, "--", js], check=True,
                       stdout=subprocess.DEVNULL)
    print("Renders en", os.path.relpath(SALIDA, P.ROOT))


if __name__ == "__main__":
    main()
