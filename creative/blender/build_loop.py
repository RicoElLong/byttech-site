"""BytTech — authored, periodic film study, not a fluid/cloth simulation.
Run after build_drum.py. Creates a separate BT_Film scene and preserves physics tests.
F12: still. Ctrl+F12: MP4 beside the saved .blend file.
"""
import bpy
import math
import random
import json
from pathlib import Path
from mathutils import Vector, Matrix

FPS = 24
SECONDS = 8
WIDTH, HEIGHT = 1280, 720
FRAMES = FPS * SECONDS
PHASE = f"(2*pi*(frame-1)/{FRAMES})"
PREFIX = "BTL_"
WATER_LEVEL = -0.205

required = ["BT_Perforated_Shell", "BT_Pressed_Back", "BT_Centre_Cap",
            "BT_Lifter_1", "BT_Lifter_2", "BT_Lifter_3",
            "BT_Front_Rolled_Lip", "BT_Rear_Seam"]
if any(bpy.data.objects.get(name) is None for name in required):
    raise RuntimeError("Run build_drum.py first, or open your existing drum project.")

scene = bpy.data.scenes.get("BT_Film") or bpy.data.scenes.new("BT_Film")
bpy.context.window.scene = scene
old = bpy.data.collections.get("BT_Film_Objects")
if old:
    for obj in list(old.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(old)
for blocks in (bpy.data.meshes, bpy.data.materials, bpy.data.curves,
               bpy.data.lights, bpy.data.cameras):
    for item in list(blocks):
        if item.name.startswith(PREFIX) and item.users == 0:
            blocks.remove(item)
collection = bpy.data.collections.new("BT_Film_Objects")
scene.collection.children.link(collection)


def drive(obj, path, expression, index=None):
    curve = obj.driver_add(path) if index is None else obj.driver_add(path, index)
    curve.driver.type = "SCRIPTED"
    curve.driver.expression = expression


def empty(name):
    obj = bpy.data.objects.new(PREFIX + name, None)
    collection.objects.link(obj)
    return obj


def painted(name, colour, metal=False):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    mat.diffuse_color = (*colour, 1)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    diffuse = nodes.new("ShaderNodeBsdfPrincipled" if metal else "ShaderNodeBsdfDiffuse")
    if metal:
        diffuse.inputs["Base Color"].default_value = (0.25, 0.30, 0.34, 1)
        diffuse.inputs["Metallic"].default_value = 0.65
        diffuse.inputs["Roughness"].default_value = 0.32
    else:
        diffuse.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1)
    rgb = nodes.new("ShaderNodeShaderToRGB")
    links.new(diffuse.outputs[0], rgb.inputs[0])
    ramp = nodes.new("ShaderNodeValToRGB")
    links.new(rgb.outputs["Color"], ramp.inputs[0])
    ramp.color_ramp.interpolation = "LINEAR"
    palette = [(0.03, 0.28), (0.20, 0.65), (0.48, 1.0), (0.95, 1.35)]
    for item in list(ramp.color_ramp.elements)[2:]:
        ramp.color_ramp.elements.remove(item)
    for index, (position, factor) in enumerate(palette):
        element = (ramp.color_ramp.elements[index] if index < 2
                   else ramp.color_ramp.elements.new(position))
        element.position = position
        element.color = (*[min(1, channel*factor) for channel in colour], 1)
        if metal and index == 3:
            element.color = (0.65, 0.78, 0.80, 1)
    coordinates = nodes.new("ShaderNodeTexCoord")
    stretch = nodes.new("ShaderNodeVectorMath")
    stretch.operation = "MULTIPLY"
    stretch.inputs[1].default_value = (1, 2.5, 13 if metal else 3)
    links.new(coordinates.outputs["Object"], stretch.inputs[0])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 110 if metal else 240
    noise.inputs["Detail"].default_value = 2
    links.new(stretch.outputs[0], noise.inputs["Vector"])
    brush = nodes.new("ShaderNodeMapRange")
    brush.inputs["To Min"].default_value = 0.72
    brush.inputs["To Max"].default_value = 1.05
    links.new(noise.outputs["Fac"], brush.inputs["Value"])
    multiply = nodes.new("ShaderNodeMixRGB")
    multiply.blend_type = "MULTIPLY"
    multiply.inputs[0].default_value = 1
    links.new(ramp.outputs["Color"], multiply.inputs[1])
    links.new(brush.outputs["Result"], multiply.inputs[2])
    fresnel = nodes.new("ShaderNodeFresnel")
    fresnel.inputs["IOR"].default_value = 1.35
    ink = nodes.new("ShaderNodeMixRGB")
    ink.blend_type = "MIX"
    links.new(fresnel.outputs[0], ink.inputs[0])
    links.new(multiply.outputs[0], ink.inputs[1])
    ink.inputs[2].default_value = (0.008, 0.018, 0.035, 1)
    emission = nodes.new("ShaderNodeEmission")
    links.new(ink.outputs[0], emission.inputs["Color"])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs[0], output.inputs["Surface"])
    return mat


def mesh_object(name, vertices, faces, material, parent=None):
    mesh = bpy.data.meshes.new(PREFIX + name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    collection.objects.link(obj)
    obj.parent = parent
    mesh.materials.append(material)
    for face in mesh.polygons:
        face.use_smooth = True
    return obj


def periodic_shapes(obj, displacements):
    basis = obj.shape_key_add(name="Basis")
    for name, expression, offsets in displacements:
        key = obj.shape_key_add(name=name)
        key.slider_min = -1
        key.slider_max = 1
        for vertex, source, offset in zip(key.data, basis.data, offsets):
            vertex.co = source.co + Vector(offset)
        drive(key, "value", expression)


metal = painted("Painted_Steel", (0.10, 0.22, 0.29), True)
blue = painted("Navy_Cloth", (0.07, 0.20, 0.42))
pale = painted("Blue_Cloth", (0.22, 0.48, 0.60))
ivory = painted("Ivory_Cloth", (0.88, 0.83, 0.66))
water_mat = painted("Turquoise_Water", (0.035, 0.48, 0.53))
# Broad moving highlights, drawn in the shader rather than simulated as liquid.
nodes, links = water_mat.node_tree.nodes, water_mat.node_tree.links
coords = nodes.new("ShaderNodeTexCoord")
separate = nodes.new("ShaderNodeSeparateXYZ")
links.new(coords.outputs["Object"], separate.inputs[0])
axis_x = nodes.new("ShaderNodeMath"); axis_x.operation = "MULTIPLY"
axis_z = nodes.new("ShaderNodeMath"); axis_z.operation = "MULTIPLY"
axis_x.inputs[1].default_value = 80
axis_z.inputs[1].default_value = 60
links.new(separate.outputs["X"], axis_x.inputs[0])
links.new(separate.outputs["Z"], axis_z.inputs[0])
total = nodes.new("ShaderNodeMath"); total.operation = "ADD"
links.new(axis_x.outputs[0], total.inputs[0])
links.new(axis_z.outputs[0], total.inputs[1])
phase_node = nodes.new("ShaderNodeMath"); phase_node.operation = "ADD"
links.new(total.outputs[0], phase_node.inputs[0])
drive(phase_node.inputs[1], "default_value", PHASE)
wave = nodes.new("ShaderNodeMath"); wave.operation = "SINE"
links.new(phase_node.outputs[0], wave.inputs[0])
mask = nodes.new("ShaderNodeValToRGB")
mask.color_ramp.elements[0].position = 0.82
mask.color_ramp.elements[1].position = 0.99
links.new(wave.outputs[0], mask.inputs[0])
emission = next(node for node in nodes if node.type == "EMISSION")
base_link = emission.inputs["Color"].links[0].from_socket
highlight = nodes.new("ShaderNodeMixRGB")
links.new(mask.outputs["Color"], highlight.inputs[0])
links.new(base_link, highlight.inputs[1])
highlight.inputs[2].default_value = (0.30, 0.65, 0.68, 1)
links.new(highlight.outputs[0], emission.inputs["Color"])
foam_mat = painted("Foam", (0.80, 0.88, 0.82))
hem_mat = painted("Cloth_Hems", (0.035, 0.07, 0.12))

drum = empty("Drum")
drive(drum, "rotation_euler", f"0.18*sin({PHASE})", 2)
for name in required:
    source = bpy.data.objects[name]
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = PREFIX + name
    obj.data.name = PREFIX + name + "_Mesh"
    collection.objects.link(obj)
    obj.parent = drum
    obj.hide_render = False
    obj.hide_set(False)
    obj.data.materials.clear()
    obj.data.materials.append(metal)

fabric_root = empty("Fabric_Motion")
drive(fabric_root, "rotation_euler", f"0.055*sin({PHASE}-0.35)", 2)


# A settled cloth pose from the validated simulation, with authored periodic motion.
script_file = globals().get("__file__")
if not script_file and bpy.context.area and bpy.context.area.type == "TEXT_EDITOR":
    script_file = bpy.context.space_data.text.filepath
if not script_file:
    raise RuntimeError("Open build_loop.py from its downloaded folder; keep towel-pose.json beside it.")
pose_path = Path(script_file).resolve().with_name("towel-pose.json")
pose = json.loads(pose_path.read_text(encoding="utf-8"))
vertices, sine, cosine = [], [], []
for x, y, z in pose["vertices"]:
    x, y, z = x*0.88, y*0.88+0.025, (z-0.03)*0.92+0.140
    vertices.append((x, y, z))
    sine.append((0.002*math.sin(z*25), 0.003*math.cos(x*20+z*15), 0))
    cosine.append((0, 0.003*math.sin(x*20+z*15), 0.002*math.sin(x*15)))
load = mesh_object("Towel_Load", vertices, pose["faces"], blue, fabric_root)
load.data.materials.append(pale)
load.data.materials.append(ivory)
for face, material_index in zip(load.data.polygons, pose["materials"]):
    face.material_index = material_index
periodic_shapes(load, [("Sway_Sin", f"sin({PHASE})", sine),
                       ("Sway_Cos", f"cos({PHASE})", cosine)])
sub = load.modifiers.new("Soft_Folds", "SUBSURF")
sub.levels = sub.render_levels = 1
solid = load.modifiers.new("Towel_Thickness", "SOLIDIFY")
solid.thickness = 0.003


vertices, faces, sine, cosine = [], [], [], []
nx, nz = 40, 36
for row in range(nz+1):
    z = -0.005 + row/nz*0.505
    for col in range(nx+1):
        x = (col/nx-0.5)*0.35
        vertices.append((x, WATER_LEVEL, z))
        sine.append((0, 0.0035*math.cos(x*32+z*24), 0))
        cosine.append((0, 0.0035*math.sin(x*32+z*24), 0))
for row in range(nz):
    for col in range(nx):
        a = row*(nx+1)+col
        faces.append((a, a+nx+1, a+nx+2, a+1))
water = mesh_object("Water_Surface", vertices, faces, water_mat)
periodic_shapes(water, [
    ("Wave_Sin", f"sin({PHASE})", sine),
    ("Wave_Cos", f"cos({PHASE})", cosine),
])

# Painted wave strokes share the same periodic displacement as the water.
for index, z_base in enumerate((0.29, 0.35, 0.405, 0.46)):
    vertices, faces, sine, cosine = [], [], [], []
    for point in range(36):
        t = point/35
        x = -0.15 + t*0.30
        centre_z = z_base + 0.015*math.sin(t*math.pi*2+index)
        for side in (-1, 1):
            z = centre_z + side*0.0011
            vertices.append((x, WATER_LEVEL+0.001, z))
            sine.append((0, 0.0035*math.cos(x*32+z*24), 0))
            cosine.append((0, 0.0035*math.sin(x*32+z*24), 0))
        if point:
            a = (point-1)*2
            faces.append((a, a+2, a+3, a+1))
    stroke = mesh_object(f"Water_Stroke_{index}", vertices, faces, foam_mat)
    periodic_shapes(stroke, [("Sin", f"sin({PHASE})", sine),
                             ("Cos", f"cos({PHASE})", cosine)])

# Graphic seams make the pressed rear plate readable in the painted material.
for index in range(3):
    vertices, faces = [], []
    for point in range(48):
        t = point/47
        r = 0.047 + t*0.185
        a = index*2*math.pi/3 + 0.18*math.sin(math.pi*t)
        for side in (-1, 1):
            angle = a + side*0.004
            z = 0.004 + 0.018*math.sin(math.pi*r/0.27)**2*(0.5+0.5*math.cos(3*angle))**3
            z += 0.004*math.exp(-((r/0.27-0.91)/0.025)**2)
            z += 0.003*math.exp(-((r/0.27-0.76)/0.025)**2)
            vertices.append((r*math.cos(angle), r*math.sin(angle), z+0.001))
        if point:
            a0 = (point-1)*2
            faces.append((a0, a0+1, a0+3, a0+2))
    mesh_object(f"Rear_Painted_Seam_{index}", vertices, faces, foam_mat, drum)

# A few readable foam shapes instead of hundreds of tiny droplets.
rng = random.Random(22)
for i in range(18):
    x = -0.145 + i/17*0.29
    z = 0.405 + rng.uniform(-0.012, 0.012)
    radius = rng.uniform(0.006, 0.014)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=radius)
    obj = bpy.context.object
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)
    obj.name = PREFIX + f"Foam_{i}"
    obj.data.name = PREFIX + f"Foam_{i}_Mesh"
    obj.location = (x, WATER_LEVEL+0.002, z)
    obj.scale = (1.2, 0.5, 1)
    obj.data.materials.append(foam_mat)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    drive(obj, "location", f"{WATER_LEVEL+0.002}+0.002*sin({PHASE}+{i*0.4})", 1)


def light(name, position, watts, size, colour):
    data = bpy.data.lights.new(PREFIX + name, "AREA")
    data.energy, data.size, data.color = watts, size, colour
    obj = bpy.data.objects.new(PREFIX + name, data)
    collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector((0, -0.10, 0.16))-obj.location).to_track_quat("-Z", "Y").to_euler()


light("Key", (-0.18, 0.15, 0.48), 5, 0.28, (0.75, 0.88, 1))
light("Warm_Rim", (0.20, 0.06, 0.48), 3, 0.18, (1, 0.85, 0.64))
light("Fill", (0, -0.13, 0.48), 1.2, 0.22, (0.55, 0.88, 1))
camera_data = bpy.data.cameras.new(PREFIX + "Camera")
camera = bpy.data.objects.new(PREFIX + "Camera", camera_data)
collection.objects.link(camera)
camera.location = (0.015, 0.0, 0.61)
direction = (Vector((0, -0.17, 0.08))-camera.location).normalized()
right = direction.cross(Vector((0, 1, 0))).normalized()
up = right.cross(direction).normalized()
camera.rotation_euler = Matrix((right, up, -direction)).transposed().to_euler()
camera_data.lens = 22
camera_data.clip_start = 0.005
scene.camera = camera
world = bpy.data.worlds.get(PREFIX + "World") or bpy.data.worlds.new(PREFIX + "World")
world.use_nodes = True
world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.008, 0.018, 0.028, 1)
scene.world = world
scene.render.engine = "BLENDER_EEVEE" if bpy.app.version >= (5, 0, 0) else "BLENDER_EEVEE_NEXT"
if hasattr(scene.eevee, "taa_render_samples"):
    scene.eevee.taa_render_samples = 32
scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
scene.render.resolution_percentage = 100
scene.render.fps, scene.render.fps_base = FPS, 1
scene.frame_start, scene.frame_end = 1, FRAMES
scene.view_settings.view_transform = "Standard"
scene.view_settings.exposure = 0
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.ffmpeg.audio_codec = "NONE"
scene.render.filepath = "//byttech-loop.mp4"
scene.frame_set(1)
bpy.context.view_layer.update()
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.region_3d.view_perspective = "CAMERA"
print(f"BT_Film ready: {SECONDS}s, {FPS}fps. F12 still; Ctrl+F12 MP4. Original physics scene preserved.")
