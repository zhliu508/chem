import os
import json
import csv

# === 路径设置 ===
BASE_DIR = os.path.dirname(__file__)          # 当前脚本所在目录
INPUT_DIR = os.path.join(BASE_DIR, "data")    # data 文件夹
CHEMISTRY_FILE = os.path.join(BASE_DIR, "chemistry_data.csv")
ZWELITE_FILE = os.path.join(BASE_DIR, "zwelite_data.csv")
REACTION_FILE = os.path.join(BASE_DIR, "reaction.csv")

# === 初始化数据集合 ===
chemistry_set = set()
zwelite_set = set()
reaction_rows = []

# === 扫描所有 JSON 文件 ===
if not os.path.exists(INPUT_DIR):
    print(f"Error: 未找到 data 文件夹：{INPUT_DIR}")
    exit(1)

json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]
json_files.sort()

if not json_files:
    print(f"WARN: data 文件夹下未发现 JSON 文件")
    exit(0)

for idx, file_name in enumerate(json_files, start=1):
    path = os.path.join(INPUT_DIR, file_name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ 解析错误：{file_name} -> {e}")
        continue

    # 获取 zeolite 名称（安全处理）
    zeolite_name = ""
    zeolite = data.get("zeolite")
    if isinstance(zeolite, dict):
        zname = zeolite.get("name")
        if isinstance(zname, str):
            zeolite_name = zname.strip()
        elif zname is not None:
            zeolite_name = str(zname).strip()
    elif isinstance(zeolite, str):
        zeolite_name = zeolite.strip()

    if not zeolite_name:
        print(f"WARN: 文件 {file_name} 缺少 zeolite.name，已跳过该字段。")
    else:
        zwelite_set.add(zeolite_name)

    # elementary_steps
    steps = data.get("elementary_steps", [])
    if not isinstance(steps, list):
        print(f"WARN: 文件 {file_name} 的 elementary_steps 格式异常，已跳过。")
        continue

    for step in steps:
        step_id = step.get("step_id", "")
        step_label = f"[{idx}]{step_id}" if step_id else f"[{idx}]R?"

        reactants = step.get("reactants", []) or []
        products = step.get("products", []) or []
        site = step.get("site", "").strip() if isinstance(step.get("site"), str) else ""

        # chemistry_data.csv 内容
        chemistry_set.add(step_label)
        for r in reactants + products:
            if isinstance(r, str) and r.strip():
                chemistry_set.add(r.strip())

        # reaction.csv 行
        for r in reactants:
            if not isinstance(r, str) or not r.strip():
                continue
            for p in products:
                if not isinstance(p, str) or not p.strip():
                    continue
                reaction_rows.append([
                    r.strip(),
                    zeolite_name,
                    p.strip(),
                    step_label,
                    site  # relation 字段
                ])

print(f"Summary: 共处理 {len(json_files)} 个文件")

# === 输出 CSV ===
# chemistry_data.csv
with open(CHEMISTRY_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title"])
    for item in sorted(chemistry_set):
        writer.writerow([item])

# zwelite_data.csv
with open(ZWELITE_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title"])
    for item in sorted(zwelite_set):
        writer.writerow([item])

# reaction.csv
with open(REACTION_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["reactant", "zwelite", "product", "step", "relation"])
    for row in reaction_rows:
        writer.writerow(row)

print("\n Success: 已生成以下文件：")
print(f"  - {CHEMISTRY_FILE}")
print(f"  - {ZWELITE_FILE}")
print(f"  - {REACTION_FILE}")
