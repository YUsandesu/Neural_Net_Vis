import sys
import re
import ast
import pprint
import subprocess
import json
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QInputDialog, QLabel, QFileDialog, QMenu, QAbstractItemView)
from PyQt6.QtCore import Qt, QPoint

class NetworkFlowEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.source_file = "visual_torch.py" 
        self.network_flow = {}
        self.template_content = ""
        self.init_ui()
        self.load_data_from_source()

    def init_ui(self):
        self.setWindowTitle("Network Flow Advanced Editor (Drag & Drop + Node Duplication)")
        self.resize(950, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        header = QLabel(f"Template: {self.source_file}\nRight-click layer or group to [Duplicate]. Drag layers to reorder.")
        header.setStyleSheet("font-size: 13px; font-weight: bold; background-color: #f0f7ff; padding: 10px; border: 1px solid #cce5ff; border-radius: 4px;")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key / Layer / Group", "Value"])
        self.tree.setColumnWidth(0, 380)
        
        # Enable drag-and-drop reordering
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        self.tree.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.tree)

        # JSON operations area
        json_layout = QHBoxLayout()
        self.btn_load_json = QPushButton("📁 Load JSON")
        self.btn_load_json.clicked.connect(self.load_json)
        self.btn_save_json = QPushButton("📄 Export JSON")
        self.btn_save_json.clicked.connect(self.save_json)
        json_layout.addWidget(self.btn_load_json)
        json_layout.addWidget(self.btn_save_json)
        layout.addLayout(json_layout)

        # Run area
        run_layout = QHBoxLayout()
        self.btn_reload = QPushButton("🔄 Reset to Original")
        self.btn_reload.clicked.connect(self.load_data_from_source)
        
        self.btn_run_memory = QPushButton("🚀 Inject Parameters & Preview Render")
        self.btn_run_memory.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_memory.clicked.connect(self.run_from_memory)

        run_layout.addWidget(self.btn_reload)
        run_layout.addWidget(self.btn_run_memory)
        layout.addLayout(run_layout)

    def show_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        menu = QMenu()

        if item is None:
            # Blank area: add layer
            add_layer_act = menu.addAction("➕ Add New Layer")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == add_layer_act:
                self.handle_layer_op(None, "add")
        
        elif item.parent() is None:
            # Layer level right-click
            copy_layer_act = menu.addAction("👯 Duplicate Layer")
            rename_act = menu.addAction("✏️ Rename Layer")
            del_act = menu.addAction("❌ Delete Layer")
            menu.addSeparator()
            add_group_act = menu.addAction("📦 Add New Group")
            
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == copy_layer_act:
                self.duplicate_layer(item)
            elif action == rename_act:
                self.handle_layer_op(item, "rename")
            elif action == del_act:
                self.handle_layer_op(item, "delete")
            elif action == add_group_act:
                self.handle_group_op(item, "add")

        elif "Group" in item.text(0):
            # Group level right-click
            copy_group_act = menu.addAction("📋 Duplicate Group")
            add_attr_act = menu.addAction("➕ Add Attribute")
            del_group_act = menu.addAction("🗑️ Delete Group")
            
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == copy_group_act:
                self.duplicate_group(item)
            elif action == add_attr_act:
                self.handle_attribute_op(item, "add")
            elif action == del_group_act:
                item.parent().removeChild(item)
        
        else:
            # Attribute level right-click
            del_attr_act = menu.addAction("⚠️ Delete Attribute")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == del_attr_act:
                item.parent().removeChild(item)

    # --- New: Duplicate/Clone Logic ---

    def duplicate_layer(self, source_layer):
        """Clone entire layer, including all Groups and attributes underneath"""
        new_name = source_layer.text(0) + "_copy"
        new_layer = QTreeWidgetItem(self.tree, [new_name, ""])
        # Inherit drag flags
        new_layer.setFlags(new_layer.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        
        # Iterate through source layer's Groups
        for i in range(source_layer.childCount()):
            source_group = source_layer.child(i)
            self.clone_group_to_layer(source_group, new_layer)
        
        new_layer.setExpanded(True)

    def duplicate_group(self, source_group):
        """Clone specified Group within current layer"""
        parent_layer = source_group.parent()
        self.clone_group_to_layer(source_group, parent_layer)

    def clone_group_to_layer(self, source_group, target_layer):
        """Generic Group cloning helper function"""
        new_group_name = f"Group {target_layer.childCount() + 1}"
        new_group = QTreeWidgetItem(target_layer, [new_group_name, ""])
        
        # Copy all attributes (Leaves) under Group
        for i in range(source_group.childCount()):
            source_leaf = source_group.child(i)
            leaf_copy = QTreeWidgetItem(new_group, [source_leaf.text(0), source_leaf.text(1)])
            leaf_copy.setForeground(1, Qt.GlobalColor.blue)
        
        target_layer.setExpanded(True)

    # --- Original Logic Preserved ---

    def handle_layer_op(self, item, op):
        if op == "add":
            name, ok = QInputDialog.getText(self, "New Layer", "Enter layer name:")
            if ok and name:
                new_item = QTreeWidgetItem(self.tree, [name, ""])
                new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        elif op == "rename":
            name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=item.text(0))
            if ok and name: item.setText(0, name)
        elif op == "delete":
            if QMessageBox.question(self, "Confirm", f"Are you sure you want to delete layer {item.text(0)}?") == QMessageBox.StandardButton.Yes:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    def handle_group_op(self, layer_item, op):
        if op == "add":
            # Define available shape options
            shape_options = ["rect", "circle", "rect_grid"]
            
            # Show dialog with dropdown list for user selection
            selected_shape, ok = QInputDialog.getItem(
                self, "Create New Group", "Select shape to create:", shape_options, 0, False
            )
            
            if ok and selected_shape:
                new_group = QTreeWidgetItem(layer_item, [f"Group {layer_item.childCount() + 1}", ""])
                
                # Define generic base default attribute template (note: string types need quotes for ast.literal_eval)
                default_attrs = {
                    "shape": f"'{selected_shape}'",
                    "color": "(200, 200, 200)",
                    "count": "1",
                    "draw_size": "20",
                    "num": "1",
                    "link": "'auto'"
                }
                
                # Override or append specific attributes based on different shapes
                if selected_shape == "rect_grid":
                    default_attrs["draw_size"] = "100"
                    default_attrs["patch_size"] = "16"
                elif selected_shape == "rect":
                    default_attrs["draw_size"] = "[20, 20]" # Rectangles may use aspect ratio more often
                elif selected_shape == "circle":
                    default_attrs["draw_size"] = "20"
                
                # Iterate through dictionary, automatically generate all attribute nodes
                for key, val_str in default_attrs.items():
                    leaf = QTreeWidgetItem(new_group, [key, val_str])
                    leaf.setForeground(1, Qt.GlobalColor.blue)
                
                layer_item.setExpanded(True)

    def handle_attribute_op(self, group_item, op):
        key, ok1 = QInputDialog.getText(self, "Add Attribute", "Key (e.g., num):")
        if ok1 and key:
            val, ok2 = QInputDialog.getText(self, "Value", f"Enter value for {key}:")
            if ok2:
                leaf = QTreeWidgetItem(group_item, [key, val])
                leaf.setForeground(1, Qt.GlobalColor.blue)
                group_item.setExpanded(True)

    def load_data_from_source(self):
        try:
            with open(self.source_file, "r", encoding="utf-8") as f:
                self.template_content = f.read()
            pattern = r"(network_flow\s*=\s*)(\{.*?\})(\n+layers_data\s*=)"
            match = re.search(pattern, self.template_content, re.DOTALL)
            if match:
                self.network_flow = ast.literal_eval(match.group(2))
                self.populate_tree()
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    def populate_tree(self):
        self.tree.clear()
        for layer_name, groups in self.network_flow.items():
            layer_item = QTreeWidgetItem(self.tree, [layer_name, ""])
            layer_item.setFlags(layer_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
            for i, group in enumerate(groups):
                group_item = QTreeWidgetItem(layer_item, [f"Group {i+1}", ""])
                for key, val in group.items():
                    leaf = QTreeWidgetItem(group_item, [key, repr(val)])
                    leaf.setForeground(1, Qt.GlobalColor.blue)
        self.tree.expandAll()

    def edit_item(self, item, column):
        if column != 1 or item.childCount() > 0: return
        old_val = item.text(1)
        new_val, ok = QInputDialog.getText(self, "Edit", f"Edit {item.text(0)}:", text=old_val)
        if ok: item.setText(1, new_val)

    def get_current_tree_data(self):
        new_flow = {}
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            layer_item = root.child(i)
            layer_name = layer_item.text(0)
            groups = []
            for j in range(layer_item.childCount()):
                group_item = layer_item.child(j)
                group_dict = {}
                for k in range(group_item.childCount()):
                    leaf = group_item.child(k)
                    key, val_s = leaf.text(0), leaf.text(1)
                    try:
                        group_dict[key] = ast.literal_eval(val_s)
                    except:
                        group_dict[key] = val_s.strip("'").strip('"')
                groups.append(group_dict)
            new_flow[layer_name] = groups
        return new_flow

    def load_json(self):
        f_name, _ = QFileDialog.getOpenFileName(self, "Load JSON", "", "JSON Files (*.json)")
        if f_name:
            with open(f_name, 'r', encoding='utf-8') as f:
                self.network_flow = json.load(f)
            self.populate_tree()

    def save_json(self):
        f_name, _ = QFileDialog.getSaveFileName(self, "Save JSON", "config.json", "JSON Files (*.json)")
        if f_name:
            with open(f_name, 'w', encoding='utf-8') as f:
                json.dump(self.get_current_tree_data(), f, indent=4)

    def run_from_memory(self):
        if not self.template_content: return
        new_flow = self.get_current_tree_data()
        pretty_dict = pprint.pformat(new_flow, sort_dicts=False, indent=4)
        pattern = r"(network_flow\s*=\s*)(\{.*?\})(\n+layers_data\s*=)"
        executable_content = re.sub(pattern, f"\\1{pretty_dict}\\3", self.template_content, flags=re.DOTALL)
        
        temp_filename = ".temp_visual_torch_run.py"
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(executable_content)
        subprocess.Popen([sys.executable, temp_filename])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NetworkFlowEditor()
    window.show()
    sys.exit(app.exec())