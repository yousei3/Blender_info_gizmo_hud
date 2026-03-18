bl_info = {
    "name": "--Info Gizmo: Snap / AutoMerge HUD--",
    "author": "Yousei3D",
    "version": (2, 7, 0),
    "blender": (5, 0, 0),
    "location": "3D View > Sidebar > Gizmo HUD",
    "description": "Show horizontal toolbar with smart auto-resizing buttons, Orientations, Multi-Snap, Scale, Opacity, and Persistent State",
    "category": "3D View",
}

import bpy
import bmesh
import gpu
import blf
import os
import json

from mathutils import Vector
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

try:
    _addon_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _addon_dir = "/home/sei/BlenderIcons"

ICON_DIR = os.path.join(_addon_dir, "info_gizmo_hud_icons")
CONFIG_FILE = os.path.join(_addon_dir, "hud_config.json")

_draw_handler = None
_icon_cache = {}
_ui_bboxes = []
_is_loading = False

SNAP_ITEMS = [
    "INCREMENT", "GRID", "VERTEX", "EDGE", "FACE", "VOLUME",
    "EDGE_MIDPOINT", "EDGE_PERPENDICULAR"
]

SNAP_TARGETS = [
    ("CLOSEST", "Closest"),
    ("CENTER", "Center"),
    ("MEDIAN", "Median"),
    ("ACTIVE", "Active")
]

def get_available_modes(obj):
    if not obj:
        return [("OBJECT", "Object", "OBJECT")]

    t = obj.type
    if t == 'MESH':
        return [
            ("OBJECT", "Object", "OBJECT"),
            ("EDIT", "Edit", "EDIT_"),
            ("SCULPT", "Sculpt", "SCULPT"),
            ("VERTEX_PAINT", "Vert🖌️", "PAINT_VERTEX"),
            ("WEIGHT_PAINT", "Weight🖌️", "PAINT_WEIGHT"),
            ("TEXTURE_PAINT", "Tex🖌️", "PAINT_TEXTURE")
        ]
    elif t in {'CURVE', 'SURFACE', 'META', 'FONT'}:
        return [
            ("OBJECT", "Object", "OBJECT"),
            ("EDIT", "Edit", "EDIT_")
        ]
    elif t == 'ARMATURE':
        return [
            ("OBJECT", "Object", "OBJECT"),
            ("EDIT", "Edit", "EDIT_"),
            ("POSE", "Pose", "POSE")
        ]
    elif t in {'GPENCIL', 'GREASEPENCIL'}:
        return [
            ("OBJECT", "Object", "OBJECT"),
            ("EDIT", "Edit", "EDIT_"),
            ("SCULPT", "Sculpt", "SCULPT"),
            ("PAINT_GPENCIL", "Draw", "PAINT_GPENCIL"),
            ("WEIGHT_GPENCIL", "Weight", "WEIGHT_GPENCIL"),
            ("VERTEX_GPENCIL", "Vertex", "VERTEX_GPENCIL")
        ]
    else:
        return [("OBJECT", "Object", "OBJECT")]

def save_config_callback(self=None, context=None):
    global _is_loading
    if _is_loading:
        return
        
    ctx = context if context is not None else bpy.context
    if getattr(ctx, "window_manager", None) is None or getattr(ctx, "scene", None) is None:
        return
        
    wm = ctx.window_manager
    scene = ctx.scene
    ts = scene.tool_settings
    
    config = {
        "hud_offset_x": wm.hud_offset_x,
        "hud_offset_y": wm.hud_offset_y,
        "hud_scale": wm.hud_scale,
        "hud_font_scale": wm.hud_font_scale,
        "hud_opacity": wm.hud_opacity,
        "show_hud_mode": wm.show_hud_mode,
        "show_hud_orientation": wm.show_hud_orientation,
        "show_hud_snap": wm.show_hud_snap,
        "show_hud_automerge": wm.show_hud_automerge,
        "show_hud_only_selected": wm.show_hud_only_selected,
        
        "use_multi_snap": wm.use_multi_snap,
        "use_only_selected": wm.use_only_selected,
        
        "show_ori_global": wm.show_ori_global,
        "show_ori_local": wm.show_ori_local,
        "show_ori_normal": wm.show_ori_normal,
        "show_ori_gimbal": wm.show_ori_gimbal,
        "show_ori_view": wm.show_ori_view,
        "show_ori_cursor": wm.show_ori_cursor,
        "show_ori_parent": wm.show_ori_parent,

        "show_snap_increment": wm.show_snap_increment,
        "show_snap_grid": wm.show_snap_grid,
        "show_snap_vertex": wm.show_snap_vertex,
        "show_snap_edge": wm.show_snap_edge,
        "show_snap_face": wm.show_snap_face,
        "show_snap_volume": wm.show_snap_volume,
        "show_snap_edge_midpoint": wm.show_snap_edge_midpoint,
        "show_snap_edge_perpendicular": wm.show_snap_edge_perpendicular,
        
        "current_orientation": scene.transform_orientation_slots[0].type if scene.transform_orientation_slots else "GLOBAL",
        "current_snap_target": ts.snap_target,
        "current_snap_elements": list(ts.snap_elements),
        "use_snap": ts.use_snap,
        "use_automerge": getattr(ts, "use_mesh_automerge", False),
        
        "current_only_selected": getattr(ts, "use_snap_selectable", getattr(ts, "use_snap_non_selected", False))
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Failed to save HUD config: {e}")

@bpy.app.handlers.persistent
def load_config_handler(dummy=None):
    global _is_loading
    if not os.path.exists(CONFIG_FILE):
        return
        
    _is_loading = True
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if bpy.data.window_managers:
            wm = bpy.data.window_managers[0]
            ui_keys = [
                "hud_offset_x", "hud_offset_y", "hud_scale", "hud_font_scale", "hud_opacity",
                "show_hud_mode", "show_hud_orientation", "show_hud_snap", "show_hud_automerge", "show_hud_only_selected",
                "use_multi_snap", "use_only_selected", "show_ori_global", "show_ori_local", "show_ori_normal",
                "show_ori_gimbal", "show_ori_view", "show_ori_cursor", "show_ori_parent",
                "show_snap_increment", "show_snap_grid", "show_snap_vertex", "show_snap_edge",
                "show_snap_face", "show_snap_volume", "show_snap_edge_midpoint", "show_snap_edge_perpendicular"
            ]
            for key in ui_keys:
                if key in config and hasattr(wm, key):
                    setattr(wm, key, config[key])
                    
        scene = bpy.context.scene if hasattr(bpy.context, "scene") else (bpy.data.scenes[0] if bpy.data.scenes else None)
        if scene:
            ts = scene.tool_settings
            if "current_orientation" in config and scene.transform_orientation_slots:
                try: scene.transform_orientation_slots[0].type = config["current_orientation"]
                except: pass
            if "current_snap_target" in config:
                try: ts.snap_target = config["current_snap_target"]
                except: pass
            if "current_snap_elements" in config:
                try: ts.snap_elements = set(config["current_snap_elements"])
                except: pass
            if "use_snap" in config:
                try: ts.use_snap = config["use_snap"]
                except: pass
            if "use_automerge" in config and hasattr(ts, "use_mesh_automerge"):
                try: ts.use_mesh_automerge = config["use_automerge"]
                except: pass
            if "current_only_selected" in config:
                if hasattr(ts, "use_snap_selectable"):
                    try: ts.use_snap_selectable = config["current_only_selected"]
                    except: pass
                elif hasattr(ts, "use_snap_non_selected"):
                    try: ts.use_snap_non_selected = config["current_only_selected"]
                    except: pass

    except Exception as e:
        print(f"Failed to load HUD config: {e}")
    finally:
        _is_loading = False

def get_or_create_texture(image_path):
    if image_path in _icon_cache:
        return _icon_cache[image_path]
    if not os.path.exists(image_path):
        return None
    try:
        image = bpy.data.images.load(image_path, check_existing=True)
        texture = gpu.texture.from_image(image)
        _icon_cache[image_path] = texture
        return texture
    except Exception as e:
        print(f"Failed to load image: {image_path} - {e}")
        return None

def draw_rect(x, y, w, h, color):
    vertices = ((x, y), (x + w, y), (x, y + h), (x + w, y + h))
    indices = ((0, 1, 2), (2, 1, 3))
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_icon(texture, x, y, width=20, height=20, opacity=1.0):
    if texture is None:
        return

    vertices = (
        (x, y),
        (x + width, y),
        (x, y + height),
        (x + width, y + height)
    )
    uvs = ((0, 0), (1, 0), (0, 1), (1, 1))
    indices = ((0, 1, 2), (2, 1, 3))

    shader = gpu.shader.from_builtin('IMAGE_COLOR')
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices, "texCoord": uvs}, indices=indices)

    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_sampler("image", texture)
    shader.uniform_float("color", (1.0, 1.0, 1.0, opacity))
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def get_pivot_world_location(scene, view_layer, area):
    active = view_layer.objects.active
    if active is None:
        return None

    if active.mode != "EDIT" or active.type != "MESH":
        return active.matrix_world.translation.copy()

    mesh = active.data
    bm = bmesh.from_edit_mesh(mesh)

    total = Vector((0.0, 0.0, 0.0))
    count = 0

    for v in bm.verts:
        if v.select:
            total += v.co
            count += 1

    if count == 0:
        return active.matrix_world.translation.copy()

    avg_local = total / float(count)
    avg_world = active.matrix_world @ avg_local
    return avg_world


def draw_snap_automerge_hud():
    global _ui_bboxes
    _ui_bboxes.clear()

    context = bpy.context
    wm = context.window_manager
    
    if not wm.use_interactive_hud:
        return

    area = context.area
    region = context.region
    space = context.space_data

    if area is None or area.type != "VIEW_3D": return
    if region is None or region.type != "WINDOW": return
    if space is None or space.type != "VIEW_3D": return

    scene = context.scene
    view_layer = context.view_layer
    tool_settings = scene.tool_settings

    snap_on = tool_settings.use_snap
    automerge_on = getattr(tool_settings, "use_mesh_automerge", False)

    pivot_world = get_pivot_world_location(scene, view_layer, area)
    if pivot_world is None:
        return

    rv3d = space.region_3d
    screen_pos = location_3d_to_region_2d(region, rv3d, pivot_world)
    if screen_pos is None:
        return

    scale = wm.hud_scale
    f_scale = wm.hud_font_scale
    opacity = wm.hud_opacity

    font_size = int(17 * scale * f_scale)
    mode_font_size = int(14 * scale * f_scale)
    target_font_size = int(13 * scale * f_scale)
    
    icon_size = int(32 * scale)
    icon_w = icon_h = icon_size
    icon_spacing = 0
    
    mode_btn_h = int(24 * scale * f_scale)
    ori_btn_h = int(22 * scale * f_scale)
    target_btn_h = int(22 * scale * f_scale)
    
    pad_20 = int(20 * scale * f_scale)
    pad_16 = int(16 * scale * f_scale)
    gap_8 = int(8 * scale)
    gap_4 = int(4 * scale)
    gap_2 = int(2 * scale)
    gap_1 = int(1 * scale)

    x = screen_pos.x + (17 * 2) + wm.hud_offset_x
    y = screen_pos.y + (17 * 5) + wm.hud_offset_y
    
    font_id = 0
    current_y = y
    start_x = x
    
    theme = context.preferences.themes[0]
    wcol_toggle = theme.user_interface.wcol_toggle
    
    color_off = (wcol_toggle.inner[0], wcol_toggle.inner[1], wcol_toggle.inner[2], opacity)
    color_on = (wcol_toggle.inner_sel[0], wcol_toggle.inner_sel[1], wcol_toggle.inner_sel[2], opacity)
    text_color_on = (wcol_toggle.text_sel[0], wcol_toggle.text_sel[1], wcol_toggle.text_sel[2], opacity)
    text_color_off = (wcol_toggle.text[0], wcol_toggle.text[1], wcol_toggle.text[2], opacity)

    visible_snap_items = []
    if wm.show_hud_snap:
        if wm.show_snap_increment: visible_snap_items.append("INCREMENT")
        if wm.show_snap_grid: visible_snap_items.append("GRID")
        if wm.show_snap_vertex: visible_snap_items.append("VERTEX")
        if wm.show_snap_edge: visible_snap_items.append("EDGE")
        if wm.show_snap_face: visible_snap_items.append("FACE")
        if wm.show_snap_volume: visible_snap_items.append("VOLUME")
        if wm.show_snap_edge_midpoint: visible_snap_items.append("EDGE_MIDPOINT")
        if wm.show_snap_edge_perpendicular: visible_snap_items.append("EDGE_PERPENDICULAR")

    visible_ori_items = []
    if wm.show_hud_orientation:
        if wm.show_ori_global: visible_ori_items.append(("GLOBAL", "Global"))
        if wm.show_ori_local: visible_ori_items.append(("LOCAL", "Local"))
        if wm.show_ori_normal: visible_ori_items.append(("NORMAL", "Normal"))
        if wm.show_ori_gimbal: visible_ori_items.append(("GIMBAL", "Gimbal"))
        if wm.show_ori_view: visible_ori_items.append(("VIEW", "View"))
        if wm.show_ori_cursor: visible_ori_items.append(("CURSOR", "Cursor"))
        if wm.show_ori_parent: visible_ori_items.append(("PARENT", "Parent"))

    snap_cols = len(SNAP_ITEMS)
    extra_gap = 0
    if wm.show_hud_snap and wm.use_multi_snap:
        snap_cols += 1
        extra_gap = gap_4 # マスターと要素の間の少しの隙間
    
    fixed_bar_w = snap_cols * icon_w + icon_spacing * (snap_cols - 1) + extra_gap

    # --- Mode ---
    if wm.show_hud_mode:
        active_obj = context.active_object
        mode_items = get_available_modes(active_obj)
        
        mode_row_y = current_y - mode_btn_h
        btn_x = start_x
        current_ctx_mode = bpy.context.mode

        for setter_mode, disp_name, ctx_prefix in mode_items:
            blf.size(font_id, mode_font_size)
            text_w, text_h = blf.dimensions(font_id, disp_name)
            current_btn_w = int(text_w + pad_20)
            
            is_active = (current_ctx_mode == ctx_prefix) or (current_ctx_mode.startswith(ctx_prefix) and ctx_prefix != "OBJECT")
            
            bg_color = color_on if is_active else color_off
            txt_color = text_color_on if is_active else text_color_off

            draw_rect(btn_x, mode_row_y, current_btn_w, mode_btn_h, bg_color)
            
            txt_x = btn_x + (current_btn_w - text_w) / 2
            txt_y = mode_row_y + (mode_btn_h - mode_font_size) / 2 + gap_2
            
            blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], txt_color[3])
            blf.position(font_id, txt_x, txt_y, 0)
            blf.draw(font_id, disp_name)
            
            win_x = btn_x + region.x
            win_y = mode_row_y + region.y
            _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + mode_btn_h, "MODE", setter_mode))
            
            btn_x += current_btn_w + gap_1

        current_y = mode_row_y - gap_4

    # --- Orientation ---
    if wm.show_hud_orientation and visible_ori_items:
        ori_row_y = current_y - ori_btn_h
        num_oris = len(visible_ori_items)
        
        req_widths = []
        total_req_w = 0
        for ori_val, ori_name in visible_ori_items:
            blf.size(font_id, target_font_size)
            text_w, text_h = blf.dimensions(font_id, ori_name)
            rw = int(text_w + pad_16)
            req_widths.append(rw)
            total_req_w += rw
            
        total_req_w += gap_1 * (num_oris - 1)
        
        if total_req_w <= fixed_bar_w:
            base_ori_w = (fixed_bar_w - gap_1 * (num_oris - 1)) // num_oris
            ori_remainder = (fixed_bar_w - gap_1 * (num_oris - 1)) % num_oris
            btn_widths = [base_ori_w + (1 if i < ori_remainder else 0) for i in range(num_oris)]
        else:
            btn_widths = req_widths

        btn_x = start_x
        current_ori = scene.transform_orientation_slots[0].type

        for i, (ori_val, ori_name) in enumerate(visible_ori_items):
            current_btn_w = btn_widths[i]
            
            is_active = (current_ori == ori_val)
            bg_color = color_on if is_active else color_off
            txt_color = text_color_on if is_active else text_color_off

            draw_rect(btn_x, ori_row_y, current_btn_w, ori_btn_h, bg_color)

            blf.size(font_id, target_font_size)
            text_w, text_h = blf.dimensions(font_id, ori_name)
            txt_x = btn_x + (current_btn_w - text_w) / 2
            txt_y = ori_row_y + (ori_btn_h - target_font_size) / 2 + gap_2
            
            blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], txt_color[3])
            blf.position(font_id, txt_x, txt_y, 0)
            blf.draw(font_id, ori_name)

            win_x = btn_x + region.x
            win_y = ori_row_y + region.y
            _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + ori_btn_h, "ORIENTATION", ori_val))

            btn_x += current_btn_w + gap_1

        current_y = ori_row_y - gap_2

    # --- Snap, AutoMerge & Only Selected ---
    if (wm.show_hud_snap and visible_snap_items) or wm.show_hud_automerge or wm.show_hud_only_selected:
        icon_row_y = current_y - icon_h
        current_icon_x = start_x

        # Snap
        if wm.show_hud_snap and visible_snap_items:
            snap_elements = set(tool_settings.snap_elements)
            current_snap = next(iter(snap_elements)) if snap_elements else ""

            if wm.use_multi_snap:
                master_bg = color_on if snap_on else color_off
                draw_rect(current_icon_x, icon_row_y, icon_w, icon_h, master_bg)
                
                master_file = "icon_snap_master_on.png" if snap_on else "icon_snap_master_off.png"
                master_tex = get_or_create_texture(os.path.join(ICON_DIR, master_file))
                if not master_tex:
                    master_tex = get_or_create_texture(os.path.join(ICON_DIR, "icon_snap_master.png"))
                
                if master_tex:
                    draw_icon(master_tex, current_icon_x, icon_row_y, width=icon_w, height=icon_h, opacity=opacity)
                
                win_x = current_icon_x + region.x
                win_y = icon_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "MASTER_SNAP", "MASTER"))
                
                current_icon_x += (icon_w + icon_spacing + gap_4) # 少しの隙間を追加

            for i, item in enumerate(visible_snap_items):
                item_x = current_icon_x + i * (icon_w + icon_spacing)
                
                if wm.use_multi_snap:
                    bg_color = color_on if (snap_on and item in snap_elements) else color_off
                else:
                    bg_color = color_on if (snap_on and item == current_snap) else color_off
                    
                draw_rect(item_x, icon_row_y, icon_w, icon_h, bg_color)

                icon_filename = f"icon_snap_{item.lower()}.png"
                icon_path = os.path.join(ICON_DIR, icon_filename)
                tex = get_or_create_texture(icon_path)

                if tex:
                    draw_icon(tex, item_x, icon_row_y, width=icon_w, height=icon_h, opacity=opacity)

                win_x = item_x + region.x
                win_y = icon_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "ELEMENT", item))

            current_icon_x += len(visible_snap_items) * (icon_w + icon_spacing)

            # Snap Target
            target_row_y = icon_row_y - target_btn_h - gap_1
            num_targets = len(SNAP_TARGETS)
            
            req_widths_tgt = []
            total_req_w_tgt = 0
            for tgt_val, tgt_name in SNAP_TARGETS:
                blf.size(font_id, target_font_size)
                text_w, text_h = blf.dimensions(font_id, tgt_name)
                rw = int(text_w + pad_16)
                req_widths_tgt.append(rw)
                total_req_w_tgt += rw
            
            total_req_w_tgt += gap_1 * (num_targets - 1)
            
            if total_req_w_tgt <= fixed_bar_w:
                base_w = (fixed_bar_w - gap_1 * (num_targets - 1)) // num_targets
                remainder = (fixed_bar_w - gap_1 * (num_targets - 1)) % num_targets
                btn_widths_tgt = [base_w + (1 if i < remainder else 0) for i in range(num_targets)]
            else:
                btn_widths_tgt = req_widths_tgt

            btn_x = start_x
            current_target = tool_settings.snap_target

            for i, (target_val, target_name) in enumerate(SNAP_TARGETS):
                current_btn_w = btn_widths_tgt[i]
                
                is_active = (current_target == target_val)
                bg_color = color_on if is_active else color_off
                txt_color = text_color_on if is_active else text_color_off

                draw_rect(btn_x, target_row_y, current_btn_w, target_btn_h, bg_color)

                blf.size(font_id, target_font_size)
                text_w, text_h = blf.dimensions(font_id, target_name)
                txt_x = btn_x + (current_btn_w - text_w) / 2
                txt_y = target_row_y + (target_btn_h - target_font_size) / 2 + gap_2
                
                blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], txt_color[3])
                blf.position(font_id, txt_x, txt_y, 0)
                blf.draw(font_id, target_name)

                win_x = btn_x + region.x
                win_y = target_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + target_btn_h, "TARGET", target_val))

                btn_x += current_btn_w + gap_1

        # AutoMerge & Only Selected
        if wm.show_hud_automerge or wm.show_hud_only_selected:
            if wm.show_hud_snap and visible_snap_items:
                current_icon_x += gap_8
            
            # AutoMerge
            if wm.show_hud_automerge:
                if hasattr(tool_settings, "use_mesh_automerge"):
                    am_bg_color = color_on if automerge_on else color_off
                    draw_rect(current_icon_x, icon_row_y, icon_w, icon_h, am_bg_color)
                    
                    am_file = "icon_automerge_on.png" if automerge_on else "icon_automerge_off.png"
                    am_tex = get_or_create_texture(os.path.join(ICON_DIR, am_file))
                    if not am_tex:
                        am_tex = get_or_create_texture(os.path.join(ICON_DIR, "icon_automerge.png"))
                        
                    if am_tex:
                        draw_icon(am_tex, current_icon_x, icon_row_y, width=icon_w, height=icon_h, opacity=opacity)
                        
                    win_x = current_icon_x + region.x
                    win_y = icon_row_y + region.y
                    _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "AUTOMERGE", "AUTOMERGE"))
                    
                    current_icon_x += icon_w

            # Only Selected
            if wm.show_hud_only_selected:
                if wm.show_hud_automerge and hasattr(tool_settings, "use_mesh_automerge"):
                    current_icon_x += gap_1
                
                os_on = getattr(tool_settings, "use_snap_selectable", getattr(tool_settings, "use_snap_non_selected", False))
                    
                os_bg_color = color_on if os_on else color_off
                draw_rect(current_icon_x, icon_row_y, icon_w, icon_h, os_bg_color)
                
                os_file = "icon_only_selected_on.png" if os_on else "icon_only_selected_off.png"
                os_tex = get_or_create_texture(os.path.join(ICON_DIR, os_file))
                    
                if os_tex:
                    draw_icon(os_tex, current_icon_x, icon_row_y, width=icon_w, height=icon_h, opacity=opacity)
                    
                win_x = current_icon_x + region.x
                win_y = icon_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "ONLY_SELECTED", "ONLY_SELECTED"))
                
                current_icon_x += icon_w

    blf.size(font_id, font_size)


class VIEW3D_OT_interactive_hud_click(bpy.types.Operator):
    bl_idname = "view3d.interactive_hud_click"
    bl_label = "Interactive HUD"
    bl_description = "Toggle clickable HUD icons"

    def modal(self, context, event):
        wm = context.window_manager
        if not wm.use_interactive_hud:
            return {'FINISHED'}

        global _ui_bboxes

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            mx = event.mouse_x
            my = event.mouse_y

            for bbox in _ui_bboxes:
                xmin, ymin, xmax, ymax, ui_type, item_value = bbox
                
                if xmin <= mx <= xmax and ymin <= my <= ymax:
                    ts = context.scene.tool_settings
                    
                    if ui_type == "MODE":
                        try:
                            bpy.ops.object.mode_set(mode=item_value)
                        except Exception as e:
                            print(f"Failed to switch mode: {e}")

                    elif ui_type == "ELEMENT":
                        if wm.use_multi_snap:
                            current_elements = set(ts.snap_elements)
                            
                            if not ts.use_snap:
                                ts.use_snap = True
                                current_elements.add(item_value)
                                ts.snap_elements = current_elements
                            else:
                                if item_value in current_elements:
                                    if len(current_elements) > 1:
                                        current_elements.discard(item_value)
                                        ts.snap_elements = current_elements
                                    else:
                                        ts.use_snap = False
                                else:
                                    current_elements.add(item_value)
                                    ts.snap_elements = current_elements
                        else:
                            current_snap = next(iter(ts.snap_elements)) if ts.snap_elements else ""
                            if ts.use_snap and current_snap == item_value:
                                ts.use_snap = False
                            else:
                                ts.use_snap = True
                                ts.snap_elements = {item_value}
                                
                    elif ui_type == "MASTER_SNAP":
                        ts.use_snap = not ts.use_snap
                            
                    elif ui_type == "TARGET":
                        ts.snap_target = item_value
                        
                    elif ui_type == "ORIENTATION":
                        context.scene.transform_orientation_slots[0].type = item_value
                        
                    elif ui_type == "AUTOMERGE":
                        if hasattr(ts, "use_mesh_automerge"):
                            ts.use_mesh_automerge = not ts.use_mesh_automerge

                    elif ui_type == "ONLY_SELECTED":
                        if hasattr(ts, "use_snap_selectable"):
                            ts.use_snap_selectable = not ts.use_snap_selectable
                        elif hasattr(ts, "use_snap_non_selected"):
                            ts.use_snap_non_selected = not ts.use_snap_non_selected
                    
                    for window in wm.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()
                    
                    save_config_callback(None, context)
                    
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        if context.window_manager.use_interactive_hud:
            context.window_manager.use_interactive_hud = False
            self.report({'INFO'}, "Gizmo HUD Disabled")
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return {'FINISHED'}
        else:
            context.window_manager.use_interactive_hud = True
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, "Gizmo HUD Enabled")
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
            return {'RUNNING_MODAL'}


class VIEW3D_PT_snap_automerge_hud(bpy.types.Panel):
    bl_label = "Gizmo HUD: Config"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gizmo HUD"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        col = layout.column()
        is_active = wm.use_interactive_hud
        icon = 'CHECKBOX_HLT' if is_active else 'CHECKBOX_DEHLT'
        col.operator(VIEW3D_OT_interactive_hud_click.bl_idname, text="Enable HUD Toolbar", icon=icon, depress=is_active)

        col.separator()
        
        col.label(text="HUD Elements Visibility:")
        row = col.row()
        row.prop(wm, "show_hud_mode", text="Mode")
        row.prop(wm, "show_hud_orientation", text="Orientation")
        row = col.row()
        row.prop(wm, "show_hud_snap", text="Snap")
        row.prop(wm, "show_hud_automerge", text="AutoMerge")
        row = col.row()
        row.prop(wm, "show_hud_only_selected", text="Only Selected")

        if wm.show_hud_orientation:
            col.label(text="Orientation Visibility:")
            box = col.box()
            flow = box.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
            flow.prop(wm, "show_ori_global")
            flow.prop(wm, "show_ori_local")
            flow.prop(wm, "show_ori_normal")
            flow.prop(wm, "show_ori_gimbal")
            flow.prop(wm, "show_ori_view")
            flow.prop(wm, "show_ori_cursor")
            flow.prop(wm, "show_ori_parent")

        if wm.show_hud_snap:
            col.prop(wm, "use_multi_snap", text="Enable Multi-Snap Mode")
            col.label(text="Snap Icons Visibility:")
            box = col.box()
            flow = box.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
            flow.prop(wm, "show_snap_increment")
            flow.prop(wm, "show_snap_grid")
            flow.prop(wm, "show_snap_vertex")
            flow.prop(wm, "show_snap_edge")
            flow.prop(wm, "show_snap_face")
            flow.prop(wm, "show_snap_volume")
            flow.prop(wm, "show_snap_edge_midpoint")
            flow.prop(wm, "show_snap_edge_perpendicular")
        
        col.separator()
        
        col.label(text="HUD Position Offset:")
        row = col.row(align=True)
        row.prop(wm, "hud_offset_x", text="X")
        row.prop(wm, "hud_offset_y", text="Y")
        
        col.separator()
        
        col.label(text="HUD Appearance:")
        col.prop(wm, "hud_scale", text="UI Scale")
        col.prop(wm, "hud_font_scale", text="Text Scale")
        col.prop(wm, "hud_opacity", text="Opacity")


classes = (
    VIEW3D_OT_interactive_hud_click,
    VIEW3D_PT_snap_automerge_hud,
)


def _force_redraw():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    return 1.0


def auto_start_hud():
    context = bpy.context
    wm = context.window_manager
    if getattr(wm, "use_interactive_hud", False):
        return None

    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'WINDOW':
                        with context.temp_override(window=window, area=area, region=region):
                            try:
                                bpy.ops.view3d.interactive_hud_click('EXEC_DEFAULT')
                            except Exception as e:
                                print(f"Failed to auto-start HUD: {e}")
                            return None
    return 0.5


@bpy.app.handlers.persistent
def auto_start_on_load_hud(dummy):
    if not bpy.app.timers.is_registered(auto_start_hud):
        bpy.app.timers.register(auto_start_hud, first_interval=0.5)


def register():
    global _draw_handler

    bpy.types.WindowManager.use_interactive_hud = bpy.props.BoolProperty(
        name="Use Interactive HUD",
        description="Internal state for clickable HUD",
        default=False
    )
    
    bpy.types.WindowManager.hud_scale = bpy.props.FloatProperty(
        name="UI Scale", default=1.0, min=0.5, max=3.0, update=save_config_callback
    )
    bpy.types.WindowManager.hud_font_scale = bpy.props.FloatProperty(
        name="Text Scale", default=1.0, min=0.5, max=3.0, update=save_config_callback
    )
    bpy.types.WindowManager.hud_opacity = bpy.props.FloatProperty(
        name="Opacity", default=1.0, min=0.1, max=1.0, update=save_config_callback
    )
    
    bpy.types.WindowManager.hud_offset_x = bpy.props.IntProperty(
        name="Offset X", default=0, update=save_config_callback
    )
    bpy.types.WindowManager.hud_offset_y = bpy.props.IntProperty(
        name="Offset Y", default=0, update=save_config_callback
    )
    bpy.types.WindowManager.show_hud_mode = bpy.props.BoolProperty(
        name="Show Mode", default=True, update=save_config_callback
    )
    bpy.types.WindowManager.show_hud_orientation = bpy.props.BoolProperty(
        name="Show Orientation", default=True, update=save_config_callback
    )
    bpy.types.WindowManager.show_hud_snap = bpy.props.BoolProperty(
        name="Show Snap", default=True, update=save_config_callback
    )
    bpy.types.WindowManager.show_hud_automerge = bpy.props.BoolProperty(
        name="Show AutoMerge", default=True, update=save_config_callback
    )
    bpy.types.WindowManager.show_hud_only_selected = bpy.props.BoolProperty(
        name="Show Only Selected", default=True, update=save_config_callback
    )
    
    bpy.types.WindowManager.use_multi_snap = bpy.props.BoolProperty(
        name="Multi-Snap", default=False, update=save_config_callback
    )
    bpy.types.WindowManager.use_only_selected = bpy.props.BoolProperty(
        name="Only Selected", default=False, update=save_config_callback
    )

    bpy.types.WindowManager.show_ori_global = bpy.props.BoolProperty(name="Global", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_ori_local = bpy.props.BoolProperty(name="Local", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_ori_normal = bpy.props.BoolProperty(name="Normal", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_ori_gimbal = bpy.props.BoolProperty(name="Gimbal", default=False, update=save_config_callback)
    bpy.types.WindowManager.show_ori_view = bpy.props.BoolProperty(name="View", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_ori_cursor = bpy.props.BoolProperty(name="Cursor", default=False, update=save_config_callback)
    bpy.types.WindowManager.show_ori_parent = bpy.props.BoolProperty(name="Parent", default=False, update=save_config_callback)

    bpy.types.WindowManager.show_snap_increment = bpy.props.BoolProperty(name="Increment", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_grid = bpy.props.BoolProperty(name="Grid", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_vertex = bpy.props.BoolProperty(name="Vertex", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_edge = bpy.props.BoolProperty(name="Edge", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_face = bpy.props.BoolProperty(name="Face", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_volume = bpy.props.BoolProperty(name="Volume", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_edge_midpoint = bpy.props.BoolProperty(name="Edge Midpoint", default=True, update=save_config_callback)
    bpy.types.WindowManager.show_snap_edge_perpendicular = bpy.props.BoolProperty(name="Edge Perpendicular", default=True, update=save_config_callback)

    for cls in classes:
        bpy.utils.register_class(cls)

    if _draw_handler is None:
        _draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            draw_snap_automerge_hud,
            (),
            "WINDOW",
            "POST_PIXEL",
        )

    bpy.app.timers.register(_force_redraw, persistent=True)
    
    bpy.app.handlers.load_post.append(auto_start_on_load_hud)
    bpy.app.handlers.load_post.append(load_config_handler)
    
    if not bpy.app.timers.is_registered(auto_start_hud):
        bpy.app.timers.register(auto_start_hud, first_interval=0.5)
        
    load_config_handler()


def unregister():
    global _draw_handler

    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, "WINDOW")
        _draw_handler = None

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.WindowManager.use_interactive_hud
    del bpy.types.WindowManager.hud_scale
    del bpy.types.WindowManager.hud_font_scale
    del bpy.types.WindowManager.hud_opacity
    del bpy.types.WindowManager.hud_offset_x
    del bpy.types.WindowManager.hud_offset_y
    del bpy.types.WindowManager.show_hud_mode
    del bpy.types.WindowManager.show_hud_orientation
    del bpy.types.WindowManager.show_hud_snap
    del bpy.types.WindowManager.show_hud_automerge
    del bpy.types.WindowManager.show_hud_only_selected
    
    del bpy.types.WindowManager.use_multi_snap
    del bpy.types.WindowManager.use_only_selected
    
    del bpy.types.WindowManager.show_ori_global
    del bpy.types.WindowManager.show_ori_local
    del bpy.types.WindowManager.show_ori_normal
    del bpy.types.WindowManager.show_ori_gimbal
    del bpy.types.WindowManager.show_ori_view
    del bpy.types.WindowManager.show_ori_cursor
    del bpy.types.WindowManager.show_ori_parent

    del bpy.types.WindowManager.show_snap_increment
    del bpy.types.WindowManager.show_snap_grid
    del bpy.types.WindowManager.show_snap_vertex
    del bpy.types.WindowManager.show_snap_edge
    del bpy.types.WindowManager.show_snap_face
    del bpy.types.WindowManager.show_snap_volume
    del bpy.types.WindowManager.show_snap_edge_midpoint
    del bpy.types.WindowManager.show_snap_edge_perpendicular

    if auto_start_on_load_hud in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(auto_start_on_load_hud)
    if load_config_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_config_handler)
    if bpy.app.timers.is_registered(auto_start_hud):
        bpy.app.timers.unregister(auto_start_hud)


if __name__ == "__main__":
    register()