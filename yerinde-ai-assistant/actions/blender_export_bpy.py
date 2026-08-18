"""
actions/blender_export_bpy.py — 3B Tasarım Stüdyosu sahnesinden Blender
Python (bpy) kodu üretir.

Üretilen kod core/blender_bridge.py aracılığıyla çalışan (ya da başlatılan)
Blender'a gönderilir — bkz. actions/tasarim_studyosu.py: blendere_aktar_command.

Neden ayrı dosya? bpy kodu üretimi saf bir metin/string inşası olduğundan,
bunu ses komutu / WebSocket köprüsü mantığından ayrı tutmak okunabilirliği
artırıyor ve test etmeyi kolaylaştırıyor.

Koordinat sistemi notu: gelen pos/rot/scale değerleri tarayıcı tarafında
(Three.js Y-yukarı) zaten Blender'ın Z-yukarı düzenine ÇEVRİLMİŞ olarak
gelir (bkz. app.js: toBlenderTransform). Burada ek bir dönüşüm YAPILMAZ.
"""

from __future__ import annotations

FPS = 24

SHAPE_TO_BPY_OP = {
    "box": "primitive_cube_add",
    "cylinder": "primitive_cylinder_add",
    "sphere": "primitive_uv_sphere_add",
    "cone": "primitive_cone_add",
    "pyramid": "primitive_cone_add",
    "torus": "primitive_torus_add",
}

# 3B Tasarım Stüdyosu'ndaki SHAPE_DEFS ile birebir eşleşen taban ölçüler
# (nesnenin scale=1 iken gerçek boyutu budur; JS tarafından gelen 'scale'
# bu taban boyutun üzerine uygulanır).
SHAPE_BASE_ARGS = {
    "box": {"size": 4},
    "cylinder": {"radius": 2, "depth": 4},
    "sphere": {"radius": 2.2},
    "cone": {"radius1": 2.2, "radius2": 0, "depth": 4},
    "pyramid": {"radius1": 2.6, "radius2": 0, "depth": 4, "vertices": 4},
    "torus": {"major_radius": 2, "minor_radius": 0.7},
}

MATERIAL_PRESET_VALUES = {
    "duz": {"roughness": 0.55, "metallic": 0.08, "alpha": 1.0},
    "ahsap": {"roughness": 0.85, "metallic": 0.0, "alpha": 1.0},
    "metal": {"roughness": 0.25, "metallic": 0.9, "alpha": 1.0},
    "plastik": {"roughness": 0.35, "metallic": 0.05, "alpha": 1.0},
    "cam": {"roughness": 0.05, "metallic": 0.0, "alpha": 0.35},
}


def _hex_to_rgb(hexcolor: str):
    h = (hexcolor or "#5ec8e8").lstrip("#")
    if len(h) != 6:
        h = "5ec8e8"
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return r, g, b


def _num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def generate_scene_code(objects: list, save_path: str) -> tuple[str, int]:
    """Sahne nesnelerinden bpy kodu üretir. (kod, atlanan_stl_sayisi) döner."""
    lines: list[str] = []
    lines.append("import bpy")
    lines.append("import math")
    lines.append("")
    lines.append("# --- YERİNDE 3B Tasarım Stüdyosu -> Blender aktarımı ---")
    lines.append("bpy.ops.object.select_all(action='SELECT')")
    lines.append("bpy.ops.object.delete(use_global=False)")
    lines.append("for _b in list(bpy.data.meshes):")
    lines.append("    if _b.users == 0: bpy.data.meshes.remove(_b)")
    lines.append("")
    lines.append("_scene = bpy.context.scene")
    lines.append(f"_scene.render.fps = {FPS}")
    lines.append("")

    id_to_varname: dict = {}
    skipped_stl = 0

    for i, obj in enumerate(objects):
        otype = obj.get("type")
        if otype == "stl" or otype not in SHAPE_TO_BPY_OP:
            skipped_stl += 1
            continue
        varname = f"obj_{i}"
        id_to_varname[obj.get("id")] = varname
        bpy_op = SHAPE_TO_BPY_OP[otype]
        base_args = dict(SHAPE_BASE_ARGS[otype])
        pos = obj.get("pos") or {}
        rot = obj.get("rot") or {}
        scale = obj.get("scale") or {}
        px, py, pz = _num(pos.get("x")), _num(pos.get("y")), _num(pos.get("z"))
        rx, ry, rz = _num(rot.get("x")), _num(rot.get("y")), _num(rot.get("z"))
        sx, sy, sz = _num(scale.get("x"), 1), _num(scale.get("y"), 1), _num(scale.get("z"), 1)

        arg_str = ", ".join(f"{k}={v}" for k, v in base_args.items())
        lines.append(
            f"bpy.ops.mesh.{bpy_op}({arg_str}, "
            f"location=({px:.5f}, {py:.5f}, {pz:.5f}), "
            f"rotation=({rx:.6f}, {ry:.6f}, {rz:.6f}))"
        )
        lines.append(f"{varname} = bpy.context.active_object")
        lines.append(f"{varname}.scale = ({sx:.5f}, {sy:.5f}, {sz:.5f})")

        preset = obj.get("materialPreset", "duz")
        preset_vals = MATERIAL_PRESET_VALUES.get(preset, MATERIAL_PRESET_VALUES["duz"])
        is_hole = bool(obj.get("isHole"))
        if is_hole:
            r, g, b, alpha = 1.0, 0.33, 0.27, 0.4
        else:
            r, g, b = _hex_to_rgb(obj.get("color"))
            alpha = preset_vals["alpha"]

        lines.append(f"_mat = bpy.data.materials.new(name='YerindeMat_{i}')")
        lines.append("_mat.use_nodes = True")
        lines.append("_bsdf = _mat.node_tree.nodes.get('Principled BSDF')")
        lines.append("if _bsdf is not None:")
        lines.append(f"    _bsdf.inputs['Base Color'].default_value = ({r:.4f}, {g:.4f}, {b:.4f}, 1.0)")
        lines.append(f"    _bsdf.inputs['Roughness'].default_value = {preset_vals['roughness']}")
        lines.append("    if 'Metallic' in _bsdf.inputs:")
        lines.append(f"        _bsdf.inputs['Metallic'].default_value = {preset_vals['metallic']}")
        if alpha < 1.0:
            lines.append("    if 'Alpha' in _bsdf.inputs:")
            lines.append(f"        _bsdf.inputs['Alpha'].default_value = {alpha}")
            lines.append("_mat.blend_method = 'BLEND'")
        lines.append(f"{varname}.data.materials.append(_mat)")
        if is_hole:
            lines.append(f"{varname}.name = 'Delik_{varname}'")
        lines.append("")

    max_frame = FPS * 4
    for i, obj in enumerate(objects):
        varname = id_to_varname.get(obj.get("id"))
        if not varname:
            continue

        # Three.js (Y-yukari) ekseni -> Blender (Z-yukari) rotation_euler
        # indeksi eslemesi: three_x->blender X(0), three_y->blender Z(2),
        # three_z->blender Y(1). Boylece web aracinda "Y ekseninde don"
        # secilirse (dikey/yukari eksen), Blender'da da DOGRU sekilde
        # dikey eksen (Z) etrafinda doner.
        AXIS_AD = {"X": (0, "spinAxisX", "orbitAxisX"), "Y": (2, "spinAxisY", "orbitAxisY"), "Z": (1, "spinAxisZ", "orbitAxisZ")}

        spin_enabled = bool(obj.get("spinEnabled"))
        spin_speed = _num(obj.get("spinSpeedDeg"), 0)
        if spin_enabled and spin_speed:
            period_sec = abs(360.0 / spin_speed)
            frame_count = max(2, round(period_sec * FPS))
            direction = 1 if spin_speed >= 0 else -1
            end_frame = frame_count + 1
            max_frame = max(max_frame, end_frame)
            lines.append(f"{varname}.rotation_mode = 'XYZ'")
            for _letter, (b_idx, spin_field, _orbit_field) in AXIS_AD.items():
                if not obj.get(spin_field):
                    continue
                lines.append(f"{varname}.keyframe_insert(data_path='rotation_euler', index={b_idx}, frame=1)")
                lines.append(f"{varname}.rotation_euler[{b_idx}] += {direction} * 2 * math.pi")
                lines.append(f"{varname}.keyframe_insert(data_path='rotation_euler', index={b_idx}, frame={end_frame})")
                lines.append(f"_fc = {varname}.animation_data.action.fcurves.find('rotation_euler', index={b_idx})")
                lines.append("if _fc is not None:")
                lines.append("    for _kp in _fc.keyframe_points: _kp.interpolation = 'LINEAR'")
                lines.append("    _fc.modifiers.new(type='CYCLES')")
            lines.append("")

        orbit_enabled = bool(obj.get("orbitEnabled"))
        orbit_speed = _num(obj.get("orbitSpeedDeg"), 0)
        orbit_offset = obj.get("orbitOffsetBlender")
        if orbit_enabled and orbit_speed and orbit_offset and obj.get("orbitTargetId") in id_to_varname:
            # NOT: ayni nesnede yukaridaki KENDI EKSEN keyframe'i de olsa bile
            # bu blok bagimsiz calisir - Blender'da ebeveynleme (parenting),
            # cocugun KENDI rotation_euler keyframe'lerini etkilemez; boylece
            # bir nesne AYNI ANDA hem kendi ekseninde donebilir hem de burada
            # kurulan pivot etrafinda yorungeye girebilir (orn. bir gezegen).
            # Pivot, HEDEFIN konumunda degil, nesnenin (baslangictaki ofsetle
            # hesaplanan) dunya konumunda olusturulur - boylece cocuk pivot'a
            # baglaninca ZIPLAMA olmaz (attach mantigina benzer sekilde,
            # pivotu hedefin konumuna koyup cocugu oraya "attach" ediyoruz).
            target_var = id_to_varname[obj.get("orbitTargetId")]
            empty_var = f"pivot_{i}"
            period_sec = abs(360.0 / orbit_speed)
            frame_count = max(2, round(period_sec * FPS))
            direction = 1 if orbit_speed >= 0 else -1
            end_frame = frame_count + 1
            max_frame = max(max_frame, end_frame)
            lines.append(f"bpy.ops.object.empty_add(type='PLAIN_AXES', location={target_var}.location)")
            lines.append(f"{empty_var} = bpy.context.active_object")
            lines.append(f"{empty_var}.name = 'YorungeMerkezi_{i}'")
            lines.append(f"{varname}.parent = {empty_var}")
            lines.append(f"{varname}.matrix_parent_inverse = {empty_var}.matrix_world.inverted()")
            lines.append(f"{empty_var}.rotation_mode = 'XYZ'")
            for _letter, (b_idx, _spin_field, orbit_field) in AXIS_AD.items():
                if not obj.get(orbit_field):
                    continue
                lines.append(f"{empty_var}.keyframe_insert(data_path='rotation_euler', index={b_idx}, frame=1)")
                lines.append(f"{empty_var}.rotation_euler[{b_idx}] += {direction} * 2 * math.pi")
                lines.append(f"{empty_var}.keyframe_insert(data_path='rotation_euler', index={b_idx}, frame={end_frame})")
                lines.append(f"_fc = {empty_var}.animation_data.action.fcurves.find('rotation_euler', index={b_idx})")
                lines.append("if _fc is not None:")
                lines.append("    for _kp in _fc.keyframe_points: _kp.interpolation = 'LINEAR'")
                lines.append("    _fc.modifiers.new(type='CYCLES')")
            lines.append("")
            lines.append("    _fc.modifiers.new(type='CYCLES')")
            lines.append("")

    lines.append(f"_scene.frame_end = {max_frame}")
    lines.append("bpy.context.view_layer.update()")
    lines.append("")
    lines.append(f"bpy.ops.wm.save_as_mainfile(filepath=r'{save_path}')")
    lines.append("")

    return "\n".join(lines), skipped_stl
