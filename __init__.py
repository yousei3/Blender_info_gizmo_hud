bl_info = {
    "name": "Info Gizmo HUD",
    "author": "Yousei3D",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "3D View > Sidebar > Gizmo HUD",
    "description": "Show horizontal toolbar with customizable UI and JSON config",
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

ICON_DIR = os.path.join(_addon_dir, "icons")
CONFIG_FILE = os.path.join(_addon_dir, "hud_config.json")

_draw_handler = None
_icon_cache = {}
_ui_bboxes = []
_is_loading = False

ORI_ITEMS = [
    ("GLOBAL", "Global"),
    ("LOCAL", "Local"),
    ("NORMAL", "Normal"),
    ("VIEW", "View")
]

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

# 絵文字を使って短縮したモード名
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

# --- 設定の保存と読み込み ---
def save_config_callback(self, context):
    global _is_loading
    if _is_loading:
        return
        
    config = {
        "hud_offset_x": self.hud_offset_x,
        "hud_offset_y": self.hud_offset_y,
        "show_hud_mode": self.show_hud_mode,
        "show_hud_orientation": self.show_hud_orientation,
        "show_hud_snap": self.show_hud_snap,
        "show_hud_automerge": self.show_hud_automerge,
        "show_snap_increment": self.show_snap_increment,
        "show_snap_grid": self.show_snap_grid,
        "show_snap_vertex": self.show_snap_vertex,
        "show_snap_edge": self.show_snap_edge,
        "show_snap_face": self.show_snap_face,
        "show_snap_volume": self.show_snap_volume,
        "show_snap_edge_midpoint": self.show_snap_edge_midpoint,
        "show_snap_edge_perpendicular": self.show_snap_edge_perpendicular,
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
            for key, value in config.items():
                if hasattr(wm, key):
                    setattr(wm, key, value)
    except Exception as e:
        print(f"Failed to load HUD config: {e}")
    finally:
        _is_loading = False
# ----------------------------

def hex_to_rgba(hex_str, alpha=1.0):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return (r, g, b, alpha)
    return (1.0, 1.0, 1.0, alpha)

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

def draw_icon(texture, x, y, width=20, height=20):
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

    shader = gpu.shader.from_builtin('IMAGE')
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices, "texCoord": uvs}, indices=indices)

    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_sampler("image", texture)
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
    area = context.area
    region = context.region
    space = context.space_data

    if area is None or area.type != "VIEW_3D": return
    if region is None or region.type != "WINDOW": return
    if space is None or space.type != "VIEW_3D": return

    scene = context.scene
    wm = context.window_manager
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

    font_size = 17
    
    x = screen_pos.x + font_size * 2 + wm.hud_offset_x
    y = screen_pos.y + font_size * 5 + wm.hud_offset_y
    
    font_id = 0
    current_y = y
    start_x = x
    
    theme = context.preferences.themes[0]
    wcol_toggle = theme.user_interface.wcol_toggle
    
    color_off = wcol_toggle.inner[:]
    color_on = wcol_toggle.inner_sel[:]
    text_color_on = wcol_toggle.text_sel[:]
    text_color_off = wcol_toggle.text[:]

    icon_size = 32
    icon_w = icon_size
    icon_h = icon_size
    icon_spacing = 0

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

    fixed_bar_w = len(SNAP_ITEMS) * icon_w + icon_spacing * (len(SNAP_ITEMS) - 1)

    # --- Mode ---
    if wm.show_hud_mode:
        active_obj = context.active_object
        mode_items = get_available_modes(active_obj)
        
        mode_btn_h = 24
        mode_row_y = current_y - mode_btn_h
        btn_x = start_x
        
        current_ctx_mode = bpy.context.mode

        for setter_mode, disp_name, ctx_prefix in mode_items:
            blf.size(font_id, 14)
            text_w, text_h = blf.dimensions(font_id, disp_name)
            current_btn_w = int(text_w + 20)
            
            is_active = (current_ctx_mode == ctx_prefix) or (current_ctx_mode.startswith(ctx_prefix) and ctx_prefix != "OBJECT")
            
            bg_color = color_on if is_active else color_off
            txt_color = text_color_on if is_active else text_color_off

            draw_rect(btn_x, mode_row_y, current_btn_w, mode_btn_h, bg_color)
            
            txt_x = btn_x + (current_btn_w - text_w) / 2
            txt_y = mode_row_y + (mode_btn_h - 14) / 2 + 2
            
            blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], 1.0)
            blf.position(font_id, txt_x, txt_y, 0)
            blf.draw(font_id, disp_name)
            
            win_x = btn_x + region.x
            win_y = mode_row_y + region.y
            _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + mode_btn_h, "MODE", setter_mode))
            
            btn_x += current_btn_w + 1

        current_y = mode_row_y - 4

    # --- Orientation ---
    if wm.show_hud_orientation:
        ori_btn_h = 22
        ori_row_y = current_y - ori_btn_h
        ori_spacing = 1
        num_oris = len(ORI_ITEMS)
        
        base_ori_w = (fixed_bar_w - ori_spacing * (num_oris - 1)) // num_oris
        ori_remainder = (fixed_bar_w - ori_spacing * (num_oris - 1)) % num_oris

        btn_x = start_x
        current_ori = scene.transform_orientation_slots[0].type

        for i, (ori_val, ori_name) in enumerate(ORI_ITEMS):
            current_btn_w = base_ori_w + (1 if i < ori_remainder else 0)
            
            is_active = (current_ori == ori_val)
            bg_color = color_on if is_active else color_off
            txt_color = text_color_on if is_active else text_color_off

            draw_rect(btn_x, ori_row_y, current_btn_w, ori_btn_h, bg_color)

            target_font_size = 13
            blf.size(font_id, target_font_size)
            text_w, text_h = blf.dimensions(font_id, ori_name)
            txt_x = btn_x + (current_btn_w - text_w) / 2
            txt_y = ori_row_y + (ori_btn_h - target_font_size) / 2 + 2
            
            blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], 1.0)
            blf.position(font_id, txt_x, txt_y, 0)
            blf.draw(font_id, ori_name)

            win_x = btn_x + region.x
            win_y = ori_row_y + region.y
            _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + ori_btn_h, "ORIENTATION", ori_val))

            btn_x += current_btn_w + ori_spacing

        current_y = ori_row_y - 2

    # --- Snap & AutoMerge ---
    if (wm.show_hud_snap and visible_snap_items) or wm.show_hud_automerge:
        icon_row_y = current_y - icon_h
        current_icon_x = start_x

        # Snap
        if wm.show_hud_snap and visible_snap_items:
            snap_elements = tool_settings.snap_elements
            current_snap = next(iter(snap_elements)) if snap_elements else ""

            for i, item in enumerate(visible_snap_items):
                item_x = current_icon_x + i * (icon_w + icon_spacing)
                
                if snap_on and item == current_snap:
                    bg_color = color_on
                else:
                    bg_color = color_off
                    
                draw_rect(item_x, icon_row_y, icon_w, icon_h, bg_color)

                icon_filename = f"icon_snap_{item.lower()}.png"
                icon_path = os.path.join(ICON_DIR, icon_filename)
                tex = get_or_create_texture(icon_path)

                if tex:
                    draw_icon(tex, item_x, icon_row_y, width=icon_w, height=icon_h)

                win_x = item_x + region.x
                win_y = icon_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "ELEMENT", item))

            current_icon_x += len(visible_snap_items) * (icon_w + icon_spacing)

            # Snap Target
            target_btn_h = 22
            target_row_y = icon_row_y - target_btn_h - 1
            target_spacing = 1
            num_targets = len(SNAP_TARGETS)
            
            base_w = (fixed_bar_w - target_spacing * (num_targets - 1)) // num_targets
            remainder = (fixed_bar_w - target_spacing * (num_targets - 1)) % num_targets

            btn_x = start_x
            current_target = tool_settings.snap_target

            for i, (target_val, target_name) in enumerate(SNAP_TARGETS):
                current_btn_w = base_w + (1 if i < remainder else 0)
                
                is_active = (current_target == target_val)
                bg_color = color_on if is_active else color_off
                txt_color = text_color_on if is_active else text_color_off

                draw_rect(btn_x, target_row_y, current_btn_w, target_btn_h, bg_color)

                target_font_size = 13
                blf.size(font_id, target_font_size)
                text_w, text_h = blf.dimensions(font_id, target_name)
                txt_x = btn_x + (current_btn_w - text_w) / 2
                txt_y = target_row_y + (target_btn_h - target_font_size) / 2 + 2
                
                blf.color(font_id, txt_color[0], txt_color[1], txt_color[2], 1.0)
                blf.position(font_id, txt_x, txt_y, 0)
                blf.draw(font_id, target_name)

                win_x = btn_x + region.x
                win_y = target_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + current_btn_w, win_y + target_btn_h, "TARGET", target_val))

                btn_x += current_btn_w + target_spacing

        # AutoMerge
        if wm.show_hud_automerge:
            if hasattr(tool_settings, "use_mesh_automerge"):
                if wm.show_hud_snap and visible_snap_items:
                    current_icon_x += 4
                
                am_bg_color = color_on if automerge_on else color_off
                draw_rect(current_icon_x, icon_row_y, icon_w, icon_h, am_bg_color)
                
                am_icon_path = os.path.join(ICON_DIR, "icon_automerge.png")
                am_tex = get_or_create_texture(am_icon_path)
                if am_tex:
                    draw_icon(am_tex, current_icon_x, icon_row_y, width=icon_w, height=icon_h)
                    
                win_x = current_icon_x + region.x
                win_y = icon_row_y + region.y
                _ui_bboxes.append((win_x, win_y, win_x + icon_w, win_y + icon_h, "AUTOMERGE", "AUTOMERGE"))

    blf.size(font_id, font_size)


class VIEW3D_OT_interactive_hud_click(bpy.types.Operator):
    bl_idname = "view3d.interactive_hud_click"
    bl_label = "Interactive HUD"
    bl_description = "Toggle clickable HUD icons"

    def modal(self, context, event):
        if not context.window_manager.use_interactive_hud:
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
                        current_snap = next(iter(ts.snap_elements)) if ts.snap_elements else ""
                        if ts.use_snap and current_snap == item_value:
                            ts.use_snap = False
                        else:
                            ts.use_snap = True
                            ts.snap_elements = {item_value}
                            
                    elif ui_type == "TARGET":
                        ts.snap_target = item_value
                        
                    elif ui_type == "ORIENTATION":
                        context.scene.transform_orientation_slots[0].type = item_value
                        
                    elif ui_type == "AUTOMERGE":
                        if hasattr(ts, "use_mesh_automerge"):
                            ts.use_mesh_automerge = not ts.use_mesh_automerge
                    
                    for window in context.window_manager.windows:
                        for area in window.screen.areas:
                            if area.type == 'VIEW_3D':
                                area.tag_redraw()
                    
                    return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def execute(self, context):
        if context.window_manager.use_interactive_hud:
            context.window_manager.use_interactive_hud = False
            self.report({'INFO'}, "Clickable Toolbar Disabled")
            return {'FINISHED'}
        else:
            context.window_manager.use_interactive_hud = True
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, "Clickable Toolbar Enabled")
            return {'RUNNING_MODAL'}


class VIEW3D_PT_snap_automerge_hud(bpy.types.Panel):
    bl_label = "Gizmo HUD: Config"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Gizmo HUD"

    def draw(self, context):
        layout = self.layout
        ts = context.scene.tool_settings
        wm = context.window_manager

        col = layout.column()
        is_active = wm.use_interactive_hud
        icon = 'CHECKBOX_HLT' if is_active else 'CHECKBOX_DEHLT'
        col.operator(VIEW3D_OT_interactive_hud_click.bl_idname, text="Enable Clickable Toolbar", icon=icon, depress=is_active)

        col.separator()
        
        col.label(text="HUD Elements Visibility:")
        row = col.row()
        row.prop(wm, "show_hud_mode", text="Mode")
        row.prop(wm, "show_hud_orientation", text="Orientation")
        row = col.row()
        row.prop(wm, "show_hud_snap", text="Snap")
        row.prop(wm, "show_hud_automerge", text="AutoMerge")

        if wm.show_hud_snap:
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
    wm = bpy.context.window_manager
    if getattr(wm, "use_interactive_hud", False):
        return None

    for window in wm.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                with bpy.context.temp_override(window=window, area=area):
                    bpy.ops.view3d.interactive_hud_click('EXEC_DEFAULT')
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
    
    # --- WindowManagerのプロパティとして再定義し、updateコールバックを設定 ---
    bpy.types.WindowManager.hud_offset_x = bpy.props.IntProperty(
        name="Offset X", default=50, update=save_config_callback
    )
    bpy.types.WindowManager.hud_offset_y = bpy.props.IntProperty(
        name="Offset Y", default=50, update=save_config_callback
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
        
    # スクリプトを直接実行した直後にもJSONを読み込む
    load_config_handler()


def unregister():
    global _draw_handler

    if _draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handler, "WINDOW")
        _draw_handler = None

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.WindowManager.use_interactive_hud
    del bpy.types.WindowManager.hud_offset_x
    del bpy.types.WindowManager.hud_offset_y
    del bpy.types.WindowManager.show_hud_mode
    del bpy.types.WindowManager.show_hud_orientation
    del bpy.types.WindowManager.show_hud_snap
    del bpy.types.WindowManager.show_hud_automerge
    
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