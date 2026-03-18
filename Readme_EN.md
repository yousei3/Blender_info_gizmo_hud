# Info Gizmo: Snap / AutoMerge HUD (v2.0.0)

A Blender add-on that displays a highly customizable, interactive, and clickable horizontal toolbar (HUD) directly in the 3D Viewport. It provides quick access to Object/Edit Modes, Transform Orientations, Snapping options, AutoMerge, and the "Only Selected" (Exclude Non-Selectable) toggle.

## ✨ Key Features

* **Interactive Viewport HUD:** Click directly on the on-screen buttons to change modes and settings without opening menus.
* **Smart Auto-Resizing:** Buttons automatically adjust their widths based on the number of visible items to prevent text overlapping.
* **Multi-Snap Support:** Seamlessly toggle multiple snap elements simultaneously with a dedicated "Master Snap" toggle button.
* **Persistent State:** Saves your HUD layout, scale, opacity, and your current snap/orientation settings into a JSON config file. Your setup is automatically restored exactly as you left it when you restart Blender.
* **Highly Customizable UI:** Independently adjust the UI Scale, Text Scale, Opacity, and X/Y screen offsets from the N-Panel.
* **Modular Visibility:** Declutter your screen by hiding individual modes, orientations, or snap elements that you don't use.
* **Visual Feedback:** Dedicated ON/OFF icon states for Master Snap, AutoMerge, and Only Selected (Exclude Non-Selectable).

## 📥 Installation

1. Download the add-on folder/ZIP file.
2. Ensure the folder contains the Python script (`__init__.py`) and a subfolder named exactly `info_gizmo_hud_icons` containing the required PNG icons.
3. Open Blender and go to **Edit > Preferences > Add-ons**.
4. Click **Install...**, select the ZIP file, and install it.
5. Check the box to enable **3D View: --Info Gizmo: Snap / AutoMerge HUD--**.

## 🚀 How to Use

1. Open the 3D Viewport.
2. Press `N` to open the Sidebar and navigate to the **Gizmo HUD** tab.
3. Click the **Enable HUD Toolbar** button to display the HUD in the viewport.
4. **Customize:** Use the N-Panel to adjust the scale, text size, opacity, and position offset. You can also check/uncheck the visibility of any specific orientation or snap icon.
5. **Multi-Snap Mode:** Check "Enable Multi-Snap Mode" in the N-Panel to reveal the Master Snap toggle on the HUD. This allows you to select multiple snap elements (like Vertex + Edge) and toggle them all ON/OFF with a single click.

## 📁 Icon Folder Structure

The add-on requires specific icons to function correctly. Place them in the `info_gizmo_hud_icons` folder alongside the script:

* `icon_snap_increment.png` ... `icon_snap_perpendicular.png`
* `icon_snap_master_on.png` / `icon_snap_master_off.png`
* `icon_automerge_on.png` / `icon_automerge_off.png`
* `icon_only_selected_on.png` / `icon_only_selected_off.png`

*(Note: If the `_on` / `_off` versions are missing, the add-on will safely fallback to standard icons, but their colors will change based on your Blender theme).*

## 💻 Compatibility
* Tested on Blender 5.0 (Compatible with Blender 4.x/5.x series).

## 📄 License
This project is licensed under the GNU General Public License (GPL).
