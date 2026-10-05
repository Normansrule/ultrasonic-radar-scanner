#!/usr/bin/env python3
"""
Photo-style renders of the CadQuery model with Blender's Cycles engine (headless).

  hardware/diagrams/hero.png        three-quarter view from the screen side
  hardware/diagrams/hero_back.png   the scan side: the two "eyes"
  hardware/diagrams/exploded.png    how the four printed parts go together

The parts come straight from cad/build_radar.py; the display shows a frame from
scripts/sim_display.py (synthetic targets). These are renders, not photos.

Needs: pip install bpy==4.2.0 (Python 3.11) plus requirements.txt.
Usage: python scripts/render_beauty.py [--samples 96] [--scale 1.0]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cad"))

import bpy  # noqa: E402
import build_radar as M  # noqa: E402

OUT = ROOT / "hardware" / "diagrams"
MM = 0.001  # build in metres so light falloff looks natural

COLORS = {  # base colour (linear-ish sRGB), roughness
    "shell": ((0.62, 0.57, 0.48), 0.55),      # warm ivory PLA
    "bezel": ((0.025, 0.028, 0.03), 0.45),    # charcoal PLA
    "base": ((0.025, 0.028, 0.03), 0.6),
    "head": ((0.16, 0.62, 0.42), 0.45),       # mint green PLA
    "servo": ((0.05, 0.12, 0.45), 0.25),
    "horn": ((0.9, 0.9, 0.88), 0.4),
    "pcb": ((0.04, 0.18, 0.55), 0.35),
    "can": ((0.42, 0.42, 0.44), 0.3),
    "cyd": ((0.03, 0.03, 0.03), 0.4),
}


def material(name, rgb, rough, metal=0.0, layer_lines=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if layer_lines:  # faint 0.2 mm layer lines along world Z
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        mathn = nt.nodes.new("ShaderNodeMath")
        mathn.operation = "SINE"
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        mul.inputs[1].default_value = 2 * math.pi / (0.2 * MM)
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.06
        bump.inputs["Distance"].default_value = 0.00005
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], mul.inputs[0])
        nt.links.new(mul.outputs[0], mathn.inputs[0])
        nt.links.new(mathn.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def screen_material():
    m = bpy.data.materials.new("screen")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    img = bpy.data.images.load(str(OUT / "screen_texture.png"))
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
    nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Emission Strength"].default_value = 2.2
    b.inputs["Roughness"].default_value = 0.08
    return m


def add_mesh(name, wp, mat, offset=(0, 0, 0), tol=0.05):
    shp = wp.val() if hasattr(wp, "val") else wp
    verts, tris = shp.tessellate(tol, 0.2)
    me = bpy.data.meshes.new(name)
    me.from_pydata([((v.x + offset[0]) * MM, (v.y + offset[1]) * MM, (v.z + offset[2]) * MM) for v in verts], [], tris)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(35))
    return ob


def screen_plane(mat, offset=(0, 0, 0)):
    """Rectangle carrying the screen texture, just behind the bezel window."""
    import cadquery as cq
    z = M.cyd_local_to_screen(0, 0, M.CYD_GLASS_TOP)[2] + 0.02
    vc = M.cyd_center_v()
    pts = [(M.CYD_VIEW_DX - 57.6 / 2, vc - 43.2 / 2), (M.CYD_VIEW_DX + 57.6 / 2, vc - 43.2 / 2),
           (M.CYD_VIEW_DX + 57.6 / 2, vc + 43.2 / 2), (M.CYD_VIEW_DX - 57.6 / 2, vc + 43.2 / 2)]
    verts = []
    for (x, v) in pts:
        p = cq.Workplane("XY").add(cq.Vertex.makeVertex(x, v, z))
        pv = M.to_screen_frame(p, M.RECESS).val()
        verts.append(((pv.X + offset[0]) * MM, (pv.Y + offset[1]) * MM, (pv.Z + offset[2]) * MM))
    me = bpy.data.meshes.new("screen")
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for i, (u, v) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)]):
        uv.data[i].uv = (u, v)
    ob = bpy.data.objects.new("screen", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def setup_scene(samples, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = int(1600 * scale)
    sc.render.resolution_y = int(1050 * scale)
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.7
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.93, 0.95, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.07
    # floor
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.active_object
    fm = material("floor", (0.55, 0.56, 0.57), 0.7)
    floor.data.materials.append(fm)
    # lights: big soft key, fill, rim
    for name, loc, size, energy, color in (
        ("key", (-0.35, -0.45, 0.55), 0.6, 14, (1.0, 0.96, 0.9)),
        ("fill", (0.5, -0.25, 0.25), 0.5, 3, (0.88, 0.93, 1.0)),
        ("rim", (0.15, 0.55, 0.45), 0.4, 9, (1.0, 1.0, 1.0)),
    ):
        ld = bpy.data.lights.new(name, "AREA")
        ld.size = size
        ld.energy = energy
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(lo)
        lo.location = loc
        direction = -lo.location
        lo.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return sc


def camera(sc, loc, target, lens=70, dof=True):
    cd = bpy.data.cameras.new("cam")
    cd.lens = lens
    cd.dof.use_dof = dof
    cd.dof.aperture_fstop = 5.6
    co = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(co)
    co.location = loc
    from mathutils import Vector
    d = Vector(target) - Vector(loc)
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cd.dof.focus_distance = d.length
    sc.camera = co
    return co


def build(sc, exploded=False):
    mats = {k: material(k, *v, layer_lines=k in ("shell", "head", "bezel", "base")) for k, v in COLORS.items()}
    mats["can"].node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    parts = M.build_all()
    off = {
        "01_shell": (0, 0, 0), "02_bezel": (0, -55, -6), "03_base": (0, 0, -38), "04_head": (0, 0, 42),
    } if exploded else {}
    o = lambda n: off.get(n, (0, 0, 0))  # noqa: E731
    add_mesh("shell", parts["01_shell"], mats["shell"], o("01_shell"))
    add_mesh("bezel", parts["02_bezel"], mats["bezel"], o("02_bezel"))
    add_mesh("base", parts["03_base"], mats["base"], o("03_base"))
    add_mesh("head", parts["04_head"], mats["head"], o("04_head"))
    refs = {n: f() for n, f in M.REFERENCE_BUILDERS.items()}
    add_mesh("servo", refs["ref_servo_sg90"], mats["servo"], o("servo"))
    add_mesh("horn", refs["ref_servo_horn"], mats["horn"], o("04_head"))
    add_mesh("cyd", refs["ref_cyd"], mats["cyd"], o("02_bezel"))
    sp = M.ref_sensor_parts()
    add_mesh("sensor_pcb", sp["pcb"], mats["pcb"], o("04_head"))
    add_mesh("sensor_cans", sp["cans"], mats["can"], o("04_head"))
    add_mesh("sensor_header", sp["header"], mats["cyd"], o("04_head"))
    screen_plane(screen_material(), o("02_bezel"))
    if exploded:  # lift the floor out of the way
        bpy.data.objects["Plane"].location.z = -0.06


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("wrote", path.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--only", default="", help="hero | back | exploded")
    a = ap.parse_args()
    cz = 0.05
    sc = setup_scene(a.samples, a.scale)
    build(sc)
    if a.only in ("", "hero"):
        camera(sc, (-0.23, -0.33, 0.21), (0.0, 0.0, cz))
        render(OUT / "hero.png")
    if a.only in ("", "back"):
        camera(sc, (0.26, 0.33, 0.19), (0.0, 0.01, cz + 0.01))
        render(OUT / "hero_back.png")
    if a.only not in ("", "exploded"):
        return
    sc = setup_scene(a.samples, a.scale)
    build(sc, exploded=True)
    camera(sc, (-0.40, -0.52, 0.36), (0.0, -0.02, 0.045), lens=58, dof=False)
    render(OUT / "exploded.png")


if __name__ == "__main__":
    main()
