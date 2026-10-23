"""Vistas 3/4 de la base modificada, con y sin la PCB fantasma. Lo llama render_base.py:

    Blender -b --factory-startup --python render_blender.py -- --mallas <tmp> --salida <render> \\
        --lobulo X Y

Lee base.stl, pcb.stl, usb.stl y funda.stl de --mallas y escribe tres-cuartos-pcb.png y
tres-cuartos-sin-pcb.png en --salida.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Vector

COLOR_BASE = (0.48, 0.54, 0.68, 1.0)
COLOR_PCB = (0.05, 0.42, 0.18, 1.0)
COLOR_USB = (0.7, 0.7, 0.72, 1.0)
COLOR_FUNDA = (0.08, 0.08, 0.09, 1.0)


def argumentos():
    resto = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--mallas", required=True)
    parser.add_argument("--salida", required=True)
    parser.add_argument("--lobulo", type=float, nargs=2, required=True, help="x, y del centro de la ventana")
    return parser.parse_args(resto)


def importar(ruta, nombre):
    bpy.ops.wm.stl_import(filepath=ruta)
    objeto = bpy.context.selected_objects[0]
    objeto.name = nombre
    bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
    return objeto


def material(nombre, color, alfa=1.0, rugosidad=0.55):
    mat = bpy.data.materials.new(nombre)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = rugosidad
    if alfa < 1.0:
        bsdf.inputs["Alpha"].default_value = alfa
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
    return mat


def preparar_render(escena):
    for motor in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            escena.render.engine = motor
            break
        except TypeError:
            continue
    escena.render.resolution_x = 1600
    escena.render.resolution_y = 1200
    mundo = bpy.data.worlds.new("Mundo")
    mundo.use_nodes = True
    fondo = next(n for n in mundo.node_tree.nodes if n.type == "BACKGROUND")
    fondo.inputs["Color"].default_value = (0.93, 0.94, 0.96, 1.0)
    fondo.inputs["Strength"].default_value = 0.25
    escena.world = mundo
    for nombre, rotacion, energia in (("Sol", (40, 10, 150), 2.4), ("Relleno", (60, -20, -30), 0.8)):
        luz = bpy.data.lights.new(nombre, "SUN")
        luz.energy = energia
        luz.angle = math.radians(8)
        objeto = bpy.data.objects.new(nombre, luz)
        objeto.rotation_euler = [math.radians(a) for a in rotacion]
        escena.collection.objects.link(objeto)


def suelo(centro):
    bpy.ops.mesh.primitive_plane_add(size=2000, location=(centro.x, centro.y, -0.01))
    bpy.context.active_object.data.materials.append(material("Cama", (0.78, 0.79, 0.8, 1.0), rugosidad=0.9))


def camara(escena, centro, direccion, escala):
    datos = bpy.data.cameras.new("Camara")
    datos.type = "ORTHO"
    datos.ortho_scale = escala
    datos.clip_end = 5000
    objeto = bpy.data.objects.new("Camara", datos)
    escena.collection.objects.link(objeto)
    objeto.location = centro + direccion.normalized() * 400
    objeto.rotation_euler = (-direccion).to_track_quat("-Z", "Y").to_euler()
    escena.camera = objeto


def renderizar(ruta):
    escena = bpy.context.scene
    escena.render.filepath = ruta
    bpy.ops.render.render(write_still=True)


def main():
    args = argumentos()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    preparar_render(escena)

    base = importar(os.path.join(args.mallas, "base.stl"), "Base")
    base.data.materials.append(material("PLA", COLOR_BASE))
    fantasma = []
    for nombre, color, alfa in (("pcb", COLOR_PCB, 0.55), ("usb", COLOR_USB, 1.0), ("funda", COLOR_FUNDA, 1.0)):
        objeto = importar(os.path.join(args.mallas, f"{nombre}.stl"), nombre)
        objeto.data.materials.append(material(nombre, color, alfa=alfa, rugosidad=0.4))
        fantasma.append(objeto)

    esquinas = [base.matrix_world @ Vector(c) for c in base.bound_box]
    centro = sum(esquinas, Vector()) / 8
    suelo(centro)

    # Desde detrás a la derecha, con la PCB y la funda puestas.
    camara(escena, centro + Vector((0, 0, -4)), Vector((1.0, -1.25, 1.05)), 118)
    renderizar(os.path.join(args.salida, "tres-cuartos-pcb.png"))

    # Desde dentro: de delante y arriba hacia el lóbulo, sin la PCB.
    for objeto in fantasma:
        objeto.hide_render = True
    lobulo = Vector((args.lobulo[0], args.lobulo[1] + 9, 3.0))
    camara(escena, lobulo, Vector((0.45, 1.0, 0.95)), 66)
    renderizar(os.path.join(args.salida, "tres-cuartos-sin-pcb.png"))


main()
