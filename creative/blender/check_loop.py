"""Headless QA: blender -b --python-exit-code 1 --python check_loop.py"""
import bpy
import runpy
from pathlib import Path
from mathutils import Vector

folder = Path(__file__).resolve().parent
runpy.run_path(str(folder / "build_drum.py"))

def counts():
    return tuple(len(items) for items in (bpy.data.objects, bpy.data.meshes,
                 bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                 bpy.data.collections, bpy.data.scenes, bpy.data.worlds))

for iteration in range(2):
    runpy.run_path(str(folder / "build_loop.py"))
    if iteration == 0:
        first_counts = counts()
    else:
        assert counts() == first_counts, (first_counts, counts())

scene = bpy.context.scene

def geometry(frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in sorted(scene.objects, key=lambda item: item.name):
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        points.extend(evaluated.matrix_world @ vertex.co for vertex in mesh.vertices)
        evaluated.to_mesh_clear()
    return points

first = geometry(1)
quarter = geometry(49)
closed = geometry(193)
assert len(first) == len(closed)
seam_error = max((a-b).length for a, b in zip(first, closed))
movement = max((a-b).length for a, b in zip(first, quarter))
assert seam_error < 0.000002, seam_error
assert movement > 0.01, movement
assert bpy.data.objects.get("Cube") is not None
assert bpy.data.scenes.get("BT_Preview") is not None
assert scene.render.ffmpeg.codec == "H264"
assert scene.frame_end == 192 and scene.render.fps == 24
print(f"PASS: periodic geometry, seam error={seam_error:.9f}m, motion={movement:.4f}m, repeat build, preserved source scenes")
