"""BytTech: empty drum study. Paste the entire script into Blender Text Editor.
Rebuilds only the dedicated BT_Drum collection. No external assets required.
"""
import bpy
import math
from mathutils import Vector

# SETTINGS: metres; the opening faces +Z, camera looks toward -Z.
RADIUS = 0.27
DEPTH = 0.40
HOLE_COLUMNS = 112
HOLE_ROWS = 25
HOLE_RADIUS = 0.0035
ANGLE_DEGREES = 0.0  # Positive = clockwise as seen by the camera.
PREVIEW_SAMPLES = 32
COLLECTION = "BT_Drum"
PREFIX = "BT_"


def reset_collection():
    old = bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for item in list(datablocks):
            if item.name.startswith(PREFIX) and item.users == 0:
                datablocks.remove(item)
    result = bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(result)
    return result


def mesh_object(name, vertices, faces, material, smooth=True):
    mesh = bpy.data.meshes.new(PREFIX + name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(PREFIX + name, mesh)
    collection.objects.link(obj)
    obj.parent = rotor
    mesh.materials.append(material)
    for face in mesh.polygons:
        face.use_smooth = smooth
    return obj


def make_steel():
    mat = bpy.data.materials.new(PREFIX + "Stainless")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (0.38, 0.43, 0.48, 1)
    shader.inputs["Metallic"].default_value = 1.0
    shader.inputs["Roughness"].default_value = 0.26
    coords = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeVectorMath")
    mapping.operation = "MULTIPLY"
    mapping.inputs[1].default_value = (1, 1, 65)
    links.new(coords.outputs["Object"], mapping.inputs[0])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 180
    noise.inputs["Detail"].default_value = 2
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.16
    bump.inputs["Distance"].default_value = 0.000025
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def perforated_shell():
    vertices, faces, lookup = [], [], {}
    pitch = (DEPTH - 0.028) / HOLE_ROWS
    step = 2 * math.pi / HOLE_COLUMNS
    sides = 16

    def vertex(angle, z, radius):
        point = (radius * math.cos(angle), radius * math.sin(angle), z)
        key = tuple(round(value, 8) for value in point)
        if key not in lookup:
            lookup[key] = len(vertices)
            vertices.append(point)
        return lookup[key]

    for row in range(HOLE_ROWS):
        z = 0.014 + (row + 0.5) * pitch
        for column in range(HOLE_COLUMNS):
            angle = (column + 0.5) * step
            loops = [[], [], [], []]
            for i in range(sides):
                a = 2 * math.pi * i / sides
                x, y = math.cos(a), math.sin(a)
                edge = max(abs(x), abs(y))
                loops[0].append(vertex(
                    angle + x / edge * step / 2,
                    z + y / edge * pitch / 2, RADIUS))
                # A shallow pressed lip, then the actual open hole tunnel.
                for ring, hole_r, radius in (
                    (1, HOLE_RADIUS + 0.0007, RADIUS),
                    (2, HOLE_RADIUS, RADIUS + 0.0007),
                    (3, HOLE_RADIUS, RADIUS + 0.0017),
                ):
                    loops[ring].append(vertex(
                        angle + x * hole_r / RADIUS,
                        z + y * hole_r, radius))
            for ring in range(3):
                for i in range(sides):
                    j = (i + 1) % sides
                    faces.append((loops[ring][j], loops[ring][i],
                                  loops[ring + 1][i], loops[ring + 1][j]))
    return mesh_object("Perforated_Shell", vertices, faces, steel)


def lathe(name, profile, material, segments=192):
    vertices, faces = [], []
    for radius, z in profile:
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            vertices.append((radius * math.cos(angle),
                             radius * math.sin(angle), z))
    for row in range(len(profile) - 1):
        for i in range(segments):
            j = (i + 1) % segments
            a, b = row * segments, (row + 1) * segments
            faces.append((a + i, a + j, b + j, b + i))
    return mesh_object(name, vertices, faces, material)


def back_plate():
    vertices, faces = [(0, 0, 0.010)], []
    segments, rings = 192, 64
    for row in range(1, rings + 1):
        r = RADIUS * row / rings
        for i in range(segments):
            a = 2 * math.pi * i / segments
            # Three stamped lobes and concentric ribs in the steel sheet.
            envelope = math.sin(math.pi * r / RADIUS) ** 2
            z = 0.004 + 0.018 * envelope * (0.5 + 0.5 * math.cos(3*a))**3
            z += 0.004 * math.exp(-((r / RADIUS - 0.91) / 0.025)**2)
            z += 0.003 * math.exp(-((r / RADIUS - 0.76) / 0.025)**2)
            vertices.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(segments):
        faces.append((0, 1 + i, 1 + (i + 1) % segments))
    for row in range(rings - 1):
        for i in range(segments):
            j = (i + 1) % segments
            a, b = 1 + row * segments, 1 + (row + 1) * segments
            faces.append((a+i, b+i, b+j, a+j))
    mesh_object("Pressed_Back", vertices, faces, steel)
    lathe("Centre_Cap", [(0.00001, 0.023), (0.038, 0.023),
                        (0.042, 0.020), (0.044, 0.010)], steel)


def lifters():
    for index in range(3):
        a = 2 * math.pi * index / 3 + math.radians(30)
        vertices, faces = [], []
        count = 24
        for row in range(9):
            t = row / 8
            # Rounded tapered ends, broad attachment, domed crown.
            taper = 0.58 + 0.42 * math.sin(math.pi * t)**0.4
            for i in range(count):
                b = 2 * math.pi * i / count
                radial = RADIUS - 0.016 + 0.022 * math.cos(b) * taper
                tangent = 0.021 * math.sin(b) * taper
                vertices.append((
                    radial * math.cos(a) - tangent * math.sin(a),
                    radial * math.sin(a) + tangent * math.cos(a),
                    0.047 + t * (DEPTH - 0.094)))
        for row in range(8):
            for i in range(count):
                j = (i + 1) % count
                faces.append((row*count+i, row*count+j,
                              (row+1)*count+j, (row+1)*count+i))
        faces.extend([tuple(reversed(range(count))),
                      tuple(8*count+i for i in range(count))])
        obj = mesh_object(f"Lifter_{index+1}", vertices, faces, steel)
        sub = obj.modifiers.new("Rounded_Profile", "SUBSURF")
        sub.levels = sub.render_levels = 2


def panel(name, position, target, watts, size, color, width=None):
    data = bpy.data.lights.new(PREFIX + name, "AREA")
    data.energy, data.color = watts, color
    data.shape = "RECTANGLE"
    data.size, data.size_y = size, width or size
    obj = bpy.data.objects.new(PREFIX + name, data)
    collection.objects.link(obj)
    obj.location = position
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat("-Z", "Y").to_euler()


def setup_scene():
    scene = bpy.context.scene
    data = bpy.data.cameras.new(PREFIX + "Camera")
    camera = bpy.data.objects.new(PREFIX + "Camera", data)
    collection.objects.link(camera)
    camera.location = (0.012, -0.015, 0.61)
    camera.rotation_euler = (Vector((0, 0.015, 0.05)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    data.lens, data.clip_start, data.clip_end = 21, 0.005, 100
    scene.camera = camera
    world = bpy.data.worlds.get(PREFIX + "World") or bpy.data.worlds.new(PREFIX + "World")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (0.025, 0.038, 0.065, 1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = 0.2
    scene.world = world
    panel("Key", (-0.17, 0.18, 0.48), (0.06, -0.05, 0.10),
          3, 0.30, (0.76, 0.86, 1.0), 0.055)
    panel("Rim", (0.21, 0.10, 0.44), (-0.08, -0.02, 0.16),
          3, 0.24, (0.48, 0.70, 1.0), 0.035)
    panel("Fill", (-0.07, -0.16, 0.49), (0, 0.08, 0.04),
          0.25, 0.20, (0.92, 0.96, 1.0), 0.08)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = PREVIEW_SAMPLES
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = -2.5
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
    return scene


# A dedicated scene keeps the previous study and unrelated objects intact.
preview = bpy.data.scenes.get(PREFIX + "Preview") or bpy.data.scenes.new(PREFIX + "Preview")
bpy.context.window.scene = preview
collection = reset_collection()
rotor = bpy.data.objects.new(PREFIX + "Rotor", None)
collection.objects.link(rotor)
steel = make_steel()
perforated_shell()
back_plate()
lifters()
lathe("Front_Rolled_Lip", [
    (RADIUS, DEPTH-0.014), (RADIUS+0.003, DEPTH-0.006),
    (RADIUS+0.002, DEPTH+0.001), (RADIUS-0.003, DEPTH+0.004),
    (RADIUS-0.007, DEPTH), (RADIUS-0.004, DEPTH-0.008)], steel)
lathe("Rear_Seam", [(RADIUS, 0.014), (RADIUS-0.004, 0.008),
                    (RADIUS-0.008, 0.006)], steel)
rotor.rotation_euler.z = -math.radians(ANGLE_DEGREES)
scene = setup_scene()
print(f"BytTech: {HOLE_COLUMNS * HOLE_ROWS} holes. F12 for preview.")
