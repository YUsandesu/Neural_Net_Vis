import os
import math

# 1. Configure Java environment BEFORE importing py5
java_home_path = r"C:\Users\admin\anaconda3\envs\Processing\Library\lib\jvm"
os.environ["JAVA_HOME"] = java_home_path

import py5

network_flow = {   'Input Image (128x128 Grayscale)': [   {   'shape': 'rect_grid',
                                               'color': [210, 210, 210],
                                               'count': 1,
                                               'draw_size': 200,
                                               'patch_size': 128,
                                               'num': 1,
                                               'link': 'auto'}],
    'Patch Unfold (Feature Detection)': [   {   'left_dis': 150,
                                                'up_dis': 40,
                                                'shape': 'rect_grid',
                                                'color': [255, 204, 0],
                                                'count': 8,
                                                'draw_size': 80,
                                                'patch_size': 16,
                                                'num': 8,
                                                'link': 'auto'}],
    'Patch Mapper (2nd Detection)': [   {   'left_dis': 100,
                                            'up_dis': 40,
                                            'shape': 'rect_grid',
                                            'color': [200, 150, 255],
                                            'count': 8,
                                            'draw_size': 80,
                                            'patch_size': 16,
                                            'num': 8,
                                            'link': 'auto'}],
    'Pool Concat (1D Feature)': [   {   'left_dis': 100,
                                        'up_dis': 30,
                                        'shape': 'rect',
                                        'color': [255, 100, 100],
                                        'count': 8,
                                        'draw_size': 22,
                                        'num': 8,
                                        'link': 'auto'},
                                    {   'shape': 'rect',
                                        'color': [100, 180, 255],
                                        'count': 8,
                                        'draw_size': 22,
                                        'num': 8,
                                        'link': 'auto'}],
    'MLP Layer 1': [   {   'left_dis': 100,
                           'up_dis': 25,
                           'shape': 'circle',
                           'color': [100, 160, 240],
                           'count': 12,
                           'draw_size': 20,
                           'num': 2,
                           'link': 'fc'}],
    'Output (Sigmoid)': [   {   'left_dis': 100,
                                'up_dis': 40,
                                'shape': 'circle',
                                'color': [130, 200, 150],
                                'count': 1,
                                'draw_size': 30,
                                'link': 'auto'}]}

layers_data = []

def get_wh(d_size):
    if isinstance(d_size, (list, tuple)) and len(d_size) >= 2:
        return d_size[0], d_size[1]
    return d_size, d_size

def settings():
    max_h_needed = 0
    max_layer_width = 0
    
    for name, groups in network_flow.items():
        layer_max_node_w = 0
        total_count = sum(g["count"] for g in groups)
        u_dis = groups[0].get("up_dis", 40)
        
        layer_total_h = (total_count - 1) * u_dis
        max_node_h = 0
        
        for g in groups:
            w, h = get_wh(g.get("draw_size", 20))
            num = g.get("num", 1)
            
            off_x = max(2, w * 0.08)
            off_y = max(2, h * 0.08) 
            
            node_actual_w = w + (num - 1) * off_x
            node_actual_h = h + (num - 1) * off_y
            
            if node_actual_w > layer_max_node_w:
                layer_max_node_w = node_actual_w
            if node_actual_h > max_node_h:
                max_node_h = node_actual_h
                
        layer_total_h += max_node_h
        
        if layer_max_node_w > max_layer_width:
            max_layer_width = layer_max_node_w
            
        if layer_total_h > max_h_needed:
            max_h_needed = layer_total_h
            
    default_x_spacing = max(180.0, float(max_layer_width * 1.8))
    
    total_width = default_x_spacing / 2.0  
    for i, (name, groups) in enumerate(network_flow.items()):
        l_dis = groups[0].get("left_dis", default_x_spacing)
        if i == 0 and "left_dis" in groups[0]:
            total_width = l_dis
        elif i > 0:
            total_width += l_dis
    total_width += default_x_spacing 
    
    calc_width = int(max(1000, total_width))
    calc_height = int(max(500, max_h_needed + 150))
    
    py5.size(calc_width, calc_height)

def setup():
    py5.background(250)
    py5.no_loop()
    calculate_coordinates()

def calculate_coordinates():
    global layers_data
    
    max_layer_w = 0
    for name, groups in network_flow.items():
        for g in groups:
            w, _ = get_wh(g.get("draw_size", 20))
            num = g.get("num", 1)
            node_w = w + (num - 1) * max(2, w * 0.08)
            if node_w > max_layer_w: max_layer_w = node_w
    default_x_spacing = max(180.0, float(max_layer_w * 1.8))
    
    current_x = default_x_spacing / 2.0  
    
    for i, (name, groups) in enumerate(network_flow.items()):
        l_dis = groups[0].get("left_dis", default_x_spacing)
        u_dis = groups[0].get("up_dis", 40)
        
        if i == 0 and "left_dis" in groups[0]:
            current_x = l_dis
        elif i > 0:
            current_x += l_dis
            
        layer_nodes = []
        total_count = sum(g["count"] for g in groups)
        
        total_h = (total_count - 1) * u_dis
        start_y = (py5.height - total_h) / 2.0
        
        node_ptr = 0
        for group in groups:
            g_count = group["count"]
            for idx in range(g_count):
                y = start_y + node_ptr * u_dis
                layer_nodes.append({
                    "x": current_x, "y": y,
                    "shape": group["shape"],
                    "color": group["color"],
                    "draw_size": group["draw_size"],
                    "link": group.get("link", "auto"),
                    "step_size": group.get("step_size", 9),       
                    "branch_count": group.get("branch_count", 2), 
                    "heads": group.get("heads", 0),               
                    "num": group.get("num", 1),
                    "patch_size": group.get("patch_size", 1),
                    "g_idx": idx,          
                    "g_count": g_count,    
                    "l_idx": node_ptr      
                })
                node_ptr += 1
        layers_data.append(layer_nodes)

def get_layer_points(layer):
    """提取真正的独立连线坐标点，现在对所有图形计算偏移"""
    pts = []
    for node in layer:
        w, h = get_wh(node["draw_size"])
        num = node.get("num", 1)
        
        # 为所有形状统一设置深度拉伸偏移量
        off_x = max(2, w * 0.08)
        off_y = -max(2, h * 0.08)
            
        for d in range(num):
            pts.append({
                "x": node["x"] + d * off_x,
                "y": node["y"] + d * off_y,
                "node": node
            })
    return pts

def draw():
    draw_connections()
    draw_nodes()
    draw_layer_labels()

def draw_connections():
    py5.stroke_weight(1.0)
    
    for i in range(len(layers_data) - 1):
        curr_l = layers_data[i]
        next_l = layers_data[i+1]
        
        curr_pts = get_layer_points(curr_l)
        next_pts = get_layer_points(next_l)
        
        for n_idx, n_pt in enumerate(next_pts):
            link_mode = n_pt["node"]["link"]
            
            if link_mode == "fc": 
                py5.stroke(100, 160, 240, 60)
                for c_pt in curr_pts:
                    py5.line(c_pt["x"], c_pt["y"], n_pt["x"], n_pt["y"])
                    
            elif link_mode == "auto":
                py5.stroke(180, 100)
                if len(next_pts) == 0: continue
                ratio = len(curr_pts) / len(next_pts)
                start_idx = int(math.floor(n_idx * ratio))
                end_idx = int(math.ceil((n_idx + 1) * ratio))
                for c_idx in range(start_idx, min(end_idx, len(curr_pts))):
                    py5.line(curr_pts[c_idx]["x"], curr_pts[c_idx]["y"], n_pt["x"], n_pt["y"])
            
            elif link_mode == "step":
                py5.stroke(180, 100)
                step_val = n_pt["node"].get("step_size", 9)
                branch_val = n_pt["node"].get("branch_count", 2)
                
                for b in range(branch_val):
                    target_idx = n_idx + b * step_val
                    if target_idx < len(curr_pts):
                        py5.line(curr_pts[target_idx]["x"], curr_pts[target_idx]["y"], n_pt["x"], n_pt["y"])

def draw_nodes():
    py5.rect_mode(py5.CENTER)
    
    for layer in layers_data:
        for node in reversed(layer):
            x, y, shape = node["x"], node["y"], node["shape"]
            w, h = get_wh(node["draw_size"]) 
            c = node["color"]
            num = node.get("num", 1)
            
            if shape == "rect_grid":
                draw_cube(x, y, node["patch_size"], num, c, w, h)
            else:
                # 给 rect 和 circle 也加入景深绘制循环
                off_x = max(2, w * 0.08)
                off_y = -max(2, h * 0.08)
                
                for d in range(num - 1, -1, -1):
                    ox = x + d * off_x
                    oy = y + d * off_y
                    
                    # 颜色逐渐加深以体现层次感
                    fill_c = [max(v - d*25, 0) for v in c]
                    py5.fill(*fill_c)
                    py5.stroke(50)
                    
                    if shape == "rect":
                        py5.rect(ox, oy, w, h)
                        
                        # Heads 逻辑（如果是多层，我们只在最外面那一层 d==0 的时候画 heads，防止重叠污染）
                        if d == 0:
                            heads = node.get("heads", 0)
                            if heads > 0:
                                head_h = 8  
                                head_w = w / heads  
                                head_c = (min(255, c[0] + 40), min(255, c[1] + 40), min(255, c[2] + 40))
                                py5.fill(*head_c)
                                for h_idx in range(heads):
                                    hx = ox - w/2 + head_w/2 + h_idx * head_w
                                    hy = oy - h/2 - head_h/2 
                                    py5.rect(hx, hy, head_w, head_h)
                                    
                    elif shape == "circle":
                        py5.circle(ox, oy, w)

def draw_cube(x, y, p_size, num, c, w, h):
    off_x = max(2, w * 0.08)
    off_y = -max(2, h * 0.08)
    
    for d in range(num-1, -1, -1):
        ox = x + d * off_x
        oy = y + d * off_y
        fill_c = [max(v - d*25, 0) for v in c]
        py5.fill(*fill_c)
        py5.stroke(50)
        py5.rect(ox, oy, w, h)
        
        if p_size > 1:
            py5.stroke(255, 60) if c[0] < 180 else py5.stroke(100, 60)
            step_x = w / p_size
            step_y = h / p_size
            for i in range(1, p_size):
                py5.line(ox - w/2 + i*step_x, oy - h/2, ox - w/2 + i*step_x, oy + h/2)
                py5.line(ox - w/2, oy - h/2 + i*step_y, ox + w/2, oy - h/2 + i*step_y)

def draw_layer_labels():
    py5.fill(50)
    py5.text_align(py5.CENTER, py5.TOP)
    py5.text_size(14)
    names = list(network_flow.keys())

if __name__ == '__main__':
    py5.run_sketch()