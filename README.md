
# Info Gizmo: Snap / AutoMerge HUD (v2.0.0)

3Dビューポート上に、カスタマイズ可能でクリック操作ができる水平ツールバー（HUD）を表示するBlenderアドオンです。
オブジェクト/編集モード、トランスフォーム座標系、スナップオプション、オートマージ、および「選択物のみ（選択不可を除外）」の切り替えに素早くアクセスできます。
<img width="1150" height="732" alt="image" src="https://github.com/user-attachments/assets/31008cde-729e-4ce3-8c9e-82d61b7d5c12" />


## ✨ 主な機能

* **インタラクティブなビューポートHUD:** 画面上のボタンを直接クリックして、メニューを開かずにモードや設定を変更できます。
* **スマートリサイズ:** 表示されているアイテムの数に合わせてボタンの幅が自動的に調整され、テキストの重なりを防ぎます。
* **マルチスナップ対応:** 専用の「マスタースナップ」トグルボタンにより、複数のスナップ要素を同時にシームレスに切り替えられます。
* **状態の保存（Persistent State）:** HUDのレイアウト、スケール、透明度、および現在のスナップ/座標系の設定をJSONファイルに保存します。Blenderを再起動しても、前回の状態が自動的に復元されます。
* **高度なUIカスタマイズ:** Nパネルから、UIスケール、テキストスケール、透明度、X/Yの表示位置オフセットを個別に調整可能です。
* **表示項目のカスタマイズ:** 使用しないモード、座標系、または個別のスナップ要素を非表示にして、画面をすっきりさせることができます。
* **視覚的なフィードバック:** マスタースナップ、オートマージ、選択物のみ（選択不可を除外）のON/OFF状態が、専用の切り替えアイコンで分かりやすく表示されます。

## 📥 インストール方法

1. アドオンのフォルダまたはZIPファイルをダウンロードします。
2. フォルダ内にPythonスクリプト（`__init__.py`）と、必要なPNGアイコンが入った `info_gizmo_hud_icons` という名前のサブフォルダが含まれていることを確認してください。
3. Blenderを開き、**編集 > プリファレンス > アドオン** に移動します。
4. 右上の **インストール...** をクリックし、ZIPファイルを選択してインストールします。
5. **3D View: --Info Gizmo: Snap / AutoMerge HUD--** のチェックボックスをオンにして有効化します。

## 🚀 使い方

1. 3Dビューポートを開きます。
2. `N` キーを押してサイドバーを開き、**Gizmo HUD** タブに移動します。
3. **Enable HUD Toolbar** ボタンをクリックすると、ビューポートにHUDが表示されます。
4. **カスタマイズ:** Nパネルを使用して、スケール、テキストサイズ、透明度、表示位置を調整します。特定の座標系やスナップアイコンの表示/非表示も切り替えられます。
5. **マルチスナップモード:** Nパネルの「Enable Multi-Snap Mode」にチェックを入れると、HUDにマスタースナップボタンが表示されます。これにより、複数のスナップ要素（頂点＋辺など）を選択し、ワンクリックで全体のON/OFFを切り替えることができます。

## 📁 アイコンフォルダの構成

アドオンが正しく機能するには、特定のアイコン画像が必要です。スクリプト本体と同じ場所にある `info_gizmo_hud_icons` フォルダ内に配置してください：

* `icon_snap_increment.png` ... `icon_snap_perpendicular.png`
* `icon_snap_master_on.png` / `icon_snap_master_off.png`
* `icon_automerge_on.png` / `icon_automerge_off.png`
* `icon_only_selected_on.png` / `icon_only_selected_off.png`

*（注意： `_on` / `_off` の専用画像がない場合でもエラーにはならず、安全装置が働いて標準のアイコンで代用されます。その際、色はBlenderのテーマカラーに合わせて変化します。）*

## 💻 動作環境
* Blender 5.0 で動作確認済み（Blender 4.x / 5.x 系と互換性あり）。

## 📄 ライセンス
このプロジェクトは GNU General Public License (GPL) のもとで公開されています。

# Info Gizmo: Snap / AutoMerge HUD (v2.0.0)

A Blender add-on that displays a highly customizable, interactive, and clickable horizontal toolbar (HUD) directly in the 3D Viewport. It provides quick access to Object/Edit Modes, Transform Orientations, Snapping options, AutoMerge, and the "Only Selected" (Exclude Non-Selectable) toggle.
<img width="1150" height="732" alt="image" src="https://github.com/user-attachments/assets/2ffd83e5-8b39-4477-8ac8-95dd93bbd940" />


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


