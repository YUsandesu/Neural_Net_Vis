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
        # 源文件仅作为只读模板
        self.source_file = "visual_torch.py" 
        self.network_flow = {}
        self.template_content = ""
        self.init_ui()
        self.load_data_from_source()

    def init_ui(self):
        self.setWindowTitle("Network Flow 可视化编辑器 (增强版)")
        self.resize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        header = QLabel(f"正在加载: {self.source_file}\n右键层可【重命名/删除/添加组】，右键组可【添加属性】，拖动层可【排序】")
        header.setStyleSheet("font-size: 13px; font-weight: bold; background-color: #f0f7ff; padding: 8px; border: 1px solid #cce5ff;")
        layout.addWidget(header)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key / Layer / Group", "Value"])
        self.tree.setColumnWidth(0, 350)
        
        # --- 修复拖拽排序功能 ---
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        # 使用 InternalMove 代替不存在的 setInternalMoveEnabled
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # 启用右键菜单
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        
        self.tree.itemDoubleClicked.connect(self.edit_item)
        layout.addWidget(self.tree)

        # JSON 文件操作
        json_layout = QHBoxLayout()
        self.btn_load_json = QPushButton("📁 加载本地 JSON")
        self.btn_load_json.clicked.connect(self.load_json)
        self.btn_save_json = QPushButton("📄 导出为 JSON")
        self.btn_save_json.clicked.connect(self.save_json)
        json_layout.addWidget(self.btn_load_json)
        json_layout.addWidget(self.btn_save_json)
        layout.addLayout(json_layout)

        # 运行操作
        run_layout = QHBoxLayout()
        self.btn_reload = QPushButton("🔄 从源文件重置参数")
        self.btn_reload.clicked.connect(self.load_data_from_source)
        
        self.btn_run_memory = QPushButton("🚀 注入参数并运行 (不修改源文件)")
        self.btn_run_memory.setStyleSheet("background-color: #008CBA; color: white; font-weight: bold; padding: 8px;")
        self.btn_run_memory.clicked.connect(self.run_from_memory)

        run_layout.addWidget(self.btn_reload)
        run_layout.addWidget(self.btn_run_memory)
        layout.addLayout(run_layout)

    def show_context_menu(self, pos: QPoint):
        """核心修复：右键菜单管理层、组和属性"""
        item = self.tree.itemAt(pos)
        menu = QMenu()

        if item is None:
            # 点击空白处：创建新层
            add_layer_act = menu.addAction("➕ 添加新层")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == add_layer_act:
                self.handle_layer_op(None, "add")
        
        elif item.parent() is None:
            # 点击的是 Layer (顶层节点)
            rename_act = menu.addAction("✏️ 重命名层")
            del_act = menu.addAction("❌ 删除该层")
            menu.addSeparator()
            add_group_act = menu.addAction("📦 添加新 Group")
            
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == rename_act:
                self.handle_layer_op(item, "rename")
            elif action == del_act:
                self.handle_layer_op(item, "delete")
            elif action == add_group_act:
                self.handle_group_op(item, "add")

        elif "Group" in item.text(0):
            # 点击的是 Group 节点
            add_attr_act = menu.addAction("➕ 添加属性 (num, step_size 等)")
            del_group_act = menu.addAction("🗑️ 删除该 Group")
            
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == add_attr_act:
                self.handle_attribute_op(item, "add")
            elif action == del_group_act:
                item.parent().removeChild(item)
        
        else:
            # 点击的是具体的属性
            del_attr_act = menu.addAction("⚠️ 删除此属性")
            action = menu.exec(self.tree.mapToGlobal(pos))
            if action == del_attr_act:
                item.parent().removeChild(item)

    # --- 功能操作逻辑 ---

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
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

    def handle_group_op(self, layer_item, op):
        if op == "add":
            new_group = QTreeWidgetItem(layer_item, [f"Group {layer_item.childCount() + 1}", ""])
            # 默认添加一个 shape 以便识别
            QTreeWidgetItem(new_group, ["shape", "rect"])
            layer_item.setExpanded(True)

    def handle_attribute_op(self, group_item, op):
        key, ok1 = QInputDialog.getText(self, "添加属性", "键 (如 num, step_size):")
        if ok1 and key:
            val, ok2 = QInputDialog.getText(self, "值", f"输入 {key} 的初始值:")
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
            # 允许拖拽
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