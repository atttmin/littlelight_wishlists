#!/usr/bin/env python3
"""
将 virpyre 的 LittleLight 格式 JSON 转换为 DIM Wish List (.txt) 格式
"""

import json, re, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ========== 1. 从旧 DIM 文件提取武器名映射 ==========
old_dim_path = os.path.join(BASE_DIR, "curators/virpyre/dim/DIMseasonal.txt")
try:
    with open(old_dim_path) as f:
        old_dim = f.read()
    
    weapon_name_map = {}
    cur_weapon = None
    for line in old_dim.split('\n'):
        m = re.match(r'^//\s*(.+?)\s*\((god-pve|god-pvp|pve|pvp)\)$', line)
        if m:
            cur_weapon = m.group(1).strip()
            continue
        m2 = re.match(r'dimwishlist:item=(\d+)', line)
        if m2 and cur_weapon:
            weapon_name_map[int(m2.group(1))] = cur_weapon
    
    print(f"从旧 DIM 提取了 {len(weapon_name_map)} 个武器名映射")
except FileNotFoundError:
    print("注意: 未找到旧 DIM 文件，武器名将显示为 hash")
    weapon_name_map = {}

# ========== 2. 标签映射 ==========
TAG_MAP = {
    "GodPVE": "god-pve",
    "PVE": "pve",
    "GodPVP": "god-pvp",
    "PVP": "pvp",
}

# ========== 3. 加载所有 Season 数据（MNK 和 Controller）==========
mnk_files = [
    "Season28.json",
]
controller_files = mnk_files[:]  # 同样文件名

def process_season_files(file_list, input_dir, platform_label):
    """处理一系列 season 文件，生成 DIM 格式条目"""
    lines = []
    # 先按 season 排序
    seasons = {}
    for fname in file_list:
        path = os.path.join(input_dir, fname)
        if not os.path.exists(path):
            print(f"  跳过: {path}")
            continue
        with open(path) as f:
            season = json.load(f)
        # 提取赛季编号
        m = re.match(r'Season(\d+)(?:-(\d+))?', fname.replace('.json', ''))
        season_num = m.group(1) if m else "?"
        seasons[season_num] = season
    
    entry_count = 0
    for season_num in sorted(seasons.keys(), key=lambda x: int(x)):
        season = seasons[season_num]
        season_label = f"Season {season_num}"
        
        for entry in season['data']:
            w_hash = entry['hash']
            tags = entry.get('tags', [])
            
            # 确定主标签
            tag_str = "unknown"
            for t in tags:
                if t in TAG_MAP:
                    tag_str = TAG_MAP[t]
                    break
            
            # 获取武器名
            w_name = weapon_name_map.get(w_hash, f"Hash_{w_hash}")
            
            # 生成每个 perk 组合
            for plug_group in entry['plugs']:
                perks_str = ",".join(str(p) for p in plug_group)
                line = f"dimwishlist:item={w_hash}&perks={perks_str}#notes:tags={tag_str}|src={platform_label}-{season_label}"
                lines.append((w_name, tag_str, line))
                entry_count += 1
    
    return lines, entry_count

# ========== 4. 处理 MNK ==========
print("\n处理 MNK（键鼠）数据...")
mnk_dir = os.path.join(BASE_DIR, "curators/virpyre/mnk")
mnk_lines, mnk_count = process_season_files(mnk_files, mnk_dir, "mnk")
print(f"  MNK: {mnk_count} 条条目")

# ========== 5. 处理 Controller ==========
print("\n处理 Controller（手柄）数据...")
ctrl_dir = os.path.join(BASE_DIR, "curators/virpyre/controller")
ctrl_lines, ctrl_count = process_season_files(controller_files, ctrl_dir, "controller")
print(f"  Controller: {ctrl_count} 条条目")

# ========== 6. 生成 DIM 文件 ==========
def write_dim_file(lines, output_path, title, description):
    """写入 DIM 格式的 .txt 文件"""
    # 按武器名排序，组内按标签排序
    # 定义标签优先级
    tag_order = {"god-pve": 0, "pve": 1, "god-pvp": 2, "pvp": 3}
    
    # 分组：先按武器名，再按标签
    groups = {}
    for w_name, tag, line in lines:
        key = (w_name, tag_order.get(tag, 99))
        if key not in groups:
            groups[key] = {"weapon": w_name, "tag": tag, "lines": []}
        groups[key]["lines"].append(line)
    
    # 排序
    sorted_keys = sorted(groups.keys(), key=lambda k: (k[0].lower(), k[1]))
    
    with open(output_path, 'w') as f:
        f.write(f"title:{title}\n")
        f.write(f"description:{description}\n\n")
        
        current_weapon = None
        for key in sorted_keys:
            g = groups[key]
            w_name = g["weapon"]
            tag = g["tag"]
            
            if w_name != current_weapon:
                f.write(f"\n// {w_name}\n")
                current_weapon = w_name
            
            f.write(f"//notes: tags:{tag}\n")
            for line in g["lines"]:
                f.write(f"\n{line}\n")
    
    total = sum(len(g["lines"]) for g in groups.values())
    print(f"\n写入 {output_path}")
    print(f"  共 {total} 条条目，{len(groups)} 个武器/标签组合")

# MNK 版本
write_dim_file(
    mnk_lines,
    os.path.join(BASE_DIR, "deliverables/virpyre-dim-mnk.txt"),
    "virpyre's DIM Wishlist (MNK)",
    "virpyre's recommendations for Season 28 (Mouse/Keyboard)."
)

# Controller 版本
write_dim_file(
    ctrl_lines,
    os.path.join(BASE_DIR, "deliverables/virpyre-dim-controller.txt"),
    "virpyre's DIM Wishlist (Controller)",
    "virpyre's recommendations for Season 28 (Controller)."
)

# 合并版
all_lines = mnk_lines + ctrl_lines
write_dim_file(
    all_lines,
    os.path.join(BASE_DIR, "deliverables/virpyre-dim-all.txt"),
    "virpyre's DIM Wishlist (All)",
    "virpyre's recommendations for Season 28 (MNK + Controller)."
)

print("\n✅ 转换完成！")
