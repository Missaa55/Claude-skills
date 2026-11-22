"""Run only inside Blender: original procedural object scene, no external blend/add-ons."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from asset_studio import safe


def main():
    import bpy
    from mathutils import Vector
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=640)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    path = safe(args.output)
    if path.exists() or path.suffix.lower() != ".png" or not 256 <= args.width <= 2048 or not 256 <= args.height <= 2048:
        raise ValueError("Choose a new PNG path and dimensions from 256 to 2048")
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def material(name, color, metallic=0):
        mat = bpy.data.materials.new(name)
        mat.diffuse_color = (*color, 1)
        mat.use_nodes = True
        shader = mat.node_tree.nodes.get("Principled BSDF")
        shader.inputs["Base Color"].default_value = (*color, 1)
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = 0.35
        return mat
    ivory = material("Ceramic", (0.82, 0.86, 0.88))
    navy = material("Navy", (0.025, 0.07, 0.11))
    copper = material("Copper", (0.68, 0.30, 0.12), 0.7)
    amber = material("Amber", (0.96, 0.56, 0.10))
    def box(name, location, scale, mat, bevel=0.06):
        bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        obj = bpy.context.object
        obj.name, obj.scale = name, scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        obj.data.materials.append(mat)
        mod = obj.modifiers.new("Soft manufactured edges", "BEVEL")
        mod.width, mod.segments = bevel, 3
        obj.modifiers.new("Weighted normals", "WEIGHTED_NORMAL")
        return obj
    box("Display platform", (0, 0, -0.2), (5.5, 4, 0.3), navy)
    box("Cabinet body", (0.65, 0.25, 0.4), (2.7, 2.5, 0.9), ivory)
    box("Cabinet inset", (0.65, 0.25, 0.88), (2.38, 2.15, 0.08), navy, 0.02)
    for row in range(2):
        for col in range(5):
            x, y = -0.22 + col*0.44, -0.32 + row*1.04
            box("Breaker housing", (x, y, 1.04), (0.36, 0.8, 0.30), ivory, 0.025)
            box("Breaker switch", (x, y, 1.23), (0.18, 0.34, 0.10), amber, 0.015)
    for i in range(3):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.47-i*0.08, minor_radius=0.027, location=(-1.55, -0.35, 0.06+i*0.06))
        bpy.context.object.data.materials.append(copper)
    box("Illustrative tester", (-1.35, 0.95, 0.22), (0.65, 1.0, 0.35), amber)
    box("Tester screen", (-1.35, 1.12, 0.42), (0.42, 0.32, 0.04), navy, 0.01)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.render.threads_mode, scene.render.threads = "FIXED", 2
    scene.render.resolution_x, scene.render.resolution_y = args.width, args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(path)
    scene.world = bpy.data.worlds.new("Studio world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.16, 0.19, 0.23, 1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    bpy.ops.object.light_add(type="AREA", location=(-3, -4, 7))
    bpy.context.object.data.energy, bpy.context.object.data.size = 900, 5
    bpy.ops.object.light_add(type="AREA", location=(4, 2, 5))
    bpy.context.object.data.energy, bpy.context.object.data.size = 650, 4
    bpy.ops.object.camera_add(location=(5.5, -6.5, 7.0))
    camera = bpy.context.object
    camera.rotation_euler = (Vector((0, 0, 0.35))-camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.type, camera.data.ortho_scale = "ORTHO", 6.8
    scene.camera = camera
    bpy.ops.render.render(write_still=True)
    if not path.is_file() or path.stat().st_size < 1000:
        raise RuntimeError("Render did not produce an image")
    print("ASSET_STUDIO_RENDERED", path.name, args.width, args.height)


if __name__ == "__main__":
    main()
