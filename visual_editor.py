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
        self.setWindowTitle("Network Flow 高级编辑器 (支持拖拽与节点复制)")
        self.resize(950, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        header = QLabel(f"模板: {self.source_file}\n右键层或组执行【复制/Duplicate】。拖拽层可排序。")
        header.setStyleSheet("font-size: 13px; font-weight: bold; background-color: #f0f7ff; padding: 10px; border: 1px solid #cce5ff; border-radius: 4px;")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key / Layer / Group", "Value"])
        self.tree.setColumnWidth(0, 380)
        
        # 启用拖拽排序
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        self.tree.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.tree)

        # JSON 操作区
        json_layout = QHBoxLayout()
        self.btn_load_json = QPushButton("📁 加载 JSON")
        self.btn_load_json.clicked.connect(self.load_json)
        self.btn_save_json = QPushButton("📄 导出 JSON")
        self.btn_save_json.clicked.connect(self.save_json)
        json_layout.addWidget(self.btn_load_json)
        json_layout.addWidget(self.btn_save_json)
        layout.addLayout(json_layout)

        # 运行区
        run_layout = QHBoxLayout()
        self.btn_reload = QPushButton("🔄 原始重置")
        self.btn_reload.clicked.connect(self.load_data_from_source)
        
        self.btn_run_memory = QPushButton("🚀 注入参数并预览渲染")
        self.btn_run_memory.setStyleSheet("background-color: #28a745; color: white; font-weight: bold; padding: 10px;")
        self.btn_run_memory.clicked.connect(self.run_from_memory)

        run_layout.addWidget(self.btn_reload)
        run_layout.addWidget(self.btn_run_memory)
        layout.addLayout(run_layout)

    def show_context_menu(self, pos: QPoint):
        item = self.tree.itemAt(pos)
        menu = QMenu()

        if item is None:
            # 空白区域：添加层
            add_layer_act = menu.addAction("➕ 添加新层")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == add_layer_act:
                self.handle_layer_op(None, "add")
        
        elif item.parent() is None:
            # Layer 级别右键
            copy_layer_act = menu.addAction("👯 复制整层 (Duplicate Layer)")
            rename_act = menu.addAction("✏️ 重命名层")
            del_act = menu.addAction("❌ 删除层")
            menu.addSeparator()
            add_group_act = menu.addAction("📦 添加新 Group")
            
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
            # Group 级别右键
            copy_group_act = menu.addAction("📋 复制该组 (Duplicate Group)")
            add_attr_act = menu.addAction("➕ 添加属性")
            del_group_act = menu.addAction("🗑️ 删除该组")
            
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == copy_group_act:
                self.duplicate_group(item)
            elif action == add_attr_act:
                self.handle_attribute_op(item, "add")
            elif action == del_group_act:
                item.parent().removeChild(item)
        
        else:
            # 属性级别右键
            del_attr_act = menu.addAction("⚠️ 删除此属性")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == del_attr_act:
                item.parent().removeChild(item)

    # --- 新增：复制/克隆逻辑 ---

    def duplicate_layer(self, source_layer):
        """克隆整个层，包括其下的所有 Group 和属性"""
        new_name = source_layer.text(0) + "_copy"
        new_layer = QTreeWidgetItem(self.tree, [new_name, ""])
        # 继承拖拽标志
        new_layer.setFlags(new_layer.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        
        # 遍历源层的 Group
        for i in range(source_layer.childCount()):
            source_group = source_layer.child(i)
            self.clone_group_to_layer(source_group, new_layer)
        
        new_layer.setExpanded(True)

    def duplicate_group(self, source_group):
        """在当前层内克隆指定的 Group"""
        parent_layer = source_group.parent()
        self.clone_group_to_layer(source_group, parent_layer)

    def clone_group_to_layer(self, source_group, target_layer):
        """通用的 Group 克隆辅助函数"""
        new_group_name = f"Group {target_layer.childCount() + 1}"
        new_group = QTreeWidgetItem(target_layer, [new_group_name, ""])
        
        # 复制 Group 下的所有属性 (Leaves)
        for i in range(source_group.childCount()):
            source_leaf = source_group.child(i)
            leaf_copy = QTreeWidgetItem(new_group, [source_leaf.text(0), source_leaf.text(1)])
            leaf_copy.setForeground(1, Qt.GlobalColor.blue)
        
        target_layer.setExpanded(True)

    # --- 原有逻辑保留 ---

    def handle_layer_op(self, item, op):
        if op == "add":
            name, ok = QInputDialog.getText(self, "新层", "输入层名称:")
            if ok and name:
                new_item = QTreeWidgetItem(self.tree, [name, ""])
                new_item.setFlags(new_item.flags() | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)
        elif op == "rename":
            name, ok = QInputDialog.getText(self, "重命名", "输入新名称:", text=item.text(0))
            if ok and name: item.setText(0, name)
        elif op == "delete":
            if QMessageBox.question(self, "确认", f"确定删除层 {item.text(0)}？") == QMessageBox.StandardButton.Yes:
                self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    def handle_group_op(self, layer_item, op):
        if op == "add":
            # 定义可供选择的形状列表
            shape_options = ["rect", "circle", "rect_grid"]
            
            # 弹出一个带下拉列表的对话框让用户选择
            selected_shape, ok = QInputDialog.getItem(
                self, "新建 Group", "请选择要创建的形状 (Shape):", shape_options, 0, False
            )
            
            if ok and selected_shape:
                new_group = QTreeWidgetItem(layer_item, [f"Group {layer_item.childCount() + 1}", ""])
                
                # 定义通用的基础默认属性模板（注意字符串类型需带引号以配合 ast.literal_eval）
                default_attrs = {
                    "shape": f"'{selected_shape}'",
                    "color": "(200, 200, 200)",
                    "count": "1",
                    "draw_size": "20",
                    "num": "1",
                    "link": "'auto'"
                }
                
                # 根据不同形状，覆盖或追加特定的专属属性
                if selected_shape == "rect_grid":
                    default_attrs["draw_size"] = "100"
                    default_attrs["patch_size"] = "16"
                elif selected_shape == "rect":
                    default_attrs["draw_size"] = "[20, 20]" # 矩形可能更常使用长宽比
                elif selected_shape == "circle":
                    default_attrs["draw_size"] = "20"
                
                # 遍历字典，自动生成所有属性节点
                for key, val_str in default_attrs.items():
                    leaf = QTreeWidgetItem(new_group, [key, val_str])
                    leaf.setForeground(1, Qt.GlobalColor.blue)
                
                layer_item.setExpanded(True)

    def handle_attribute_op(self, group_item, op):
        key, ok1 = QInputDialog.getText(self, "添加属性", "键 (如 num):")
        if ok1 and key:
            val, ok2 = QInputDialog.getText(self, "值", f"输入 {key} 的值:")
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
            QMessageBox.critical(self, "加载错误", str(e))

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
        new_val, ok = QInputDialog.getText(self, "修改", f"编辑 {item.text(0)}:", text=old_val)
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
        f_name, _ = QFileDialog.getOpenFileName(self, "加载 JSON", "", "JSON Files (*.json)")
        if f_name:
            with open(f_name, 'r', encoding='utf-8') as f:
                self.network_flow = json.load(f)
            self.populate_tree()

    def save_json(self):
        f_name, _ = QFileDialog.getSaveFileName(self, "保存 JSON", "config.json", "JSON Files (*.json)")
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