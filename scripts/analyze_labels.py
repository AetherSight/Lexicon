#!/usr/bin/env python3
"""
分析 equipment_labels.csv 中的标签使用情况

功能：
1. 获取 CSV 里各列标签（colors/materials/shapes/decorations/styles/effects），去重整理，
   对比定义的标签列表，找出「从未出现过的标签」并输出。
   （不涉及 APPEARANCE_TYPES，因为这次只训练了衣服）
2. 整理 custom_tags，去重输出。
"""

import csv
from pathlib import Path
from typing import Set, Dict

from src.lexicon.label_system import (
    COLOR_LABELS,
    MATERIAL_LABELS,
    SHAPE_LABELS,
    DECORATION_LABELS,
    STYLE_LABELS,
    EFFECT_LABELS,
)


def parse_label_string(label_str: str) -> Set[str]:
    """解析单元格中的标签字符串，按逗号分割并去掉空格，返回集合。"""
    if not label_str:
        return set()
    # 兼容空字符串、None 等
    text = str(label_str).strip()
    if not text:
        return set()

    # 逗号分割，中英逗号都考虑一下（但主数据是半角逗号）
    # 优先按半角逗号，再粗暴替换全角逗号
    text = text.replace("，", ",")
    parts = [p.strip() for p in text.split(",")]
    return {p for p in parts if p}


def analyze_csv(csv_path: str) -> None:
    """分析 CSV 文件中的标签使用情况。"""

    # 预定义的标签集合（不包含 APPEARANCE_TYPES）
    defined_labels: Dict[str, Set[str]] = {
        "colors": set(COLOR_LABELS),
        "materials": set(MATERIAL_LABELS),
        "shapes": set(SHAPE_LABELS),
        "decorations": set(DECORATION_LABELS),
        "styles": set(STYLE_LABELS),
        "effects": set(EFFECT_LABELS),
    }

    # 实际在 CSV 中用到的标签
    used_labels: Dict[str, Set[str]] = {
        "colors": set(),
        "materials": set(),
        "shapes": set(),
        "decorations": set(),
        "styles": set(),
        "effects": set(),
    }

    # 所有 custom_tags（去重）
    all_custom_tags: Set[str] = set()

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"错误：文件 {csv_path} 不存在")
        return

    print(f"正在分析 {csv_file} ...")
    print("-" * 80)

    with csv_file.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        row_count = 0

        for row in reader:
            row_count += 1

            # 六大标签列
            for col in ["colors", "materials", "shapes", "decorations", "styles", "effects"]:
                if col in row:
                    labels = parse_label_string(row[col])
                    used_labels[col].update(labels)

            # custom_tags
            if "custom_tags" in row and row["custom_tags"]:
                tags = parse_label_string(row["custom_tags"])
                all_custom_tags.update(tags)

    print(f"共处理 {row_count} 行数据\n")

    # 1. 未出现过的标签
    print("=" * 80)
    print("1. 未出现的标签（按类别，不含 APPEARANCE_TYPES）")
    print("=" * 80)

    total_unused = 0
    for col in ["colors", "materials", "shapes", "decorations", "styles", "effects"]:
        defined = defined_labels[col]
        used = used_labels[col]
        unused = defined - used

        print(f"\n【{col.upper()}】")
        print(f"  定义总数: {len(defined)}")
        print(f"  使用数量: {len(used)}")
        print(f"  未使用数量: {len(unused)}")

        if unused:
            print("  未使用的标签：")
            for label in sorted(unused):
                print(f"    - {label}")
            total_unused += len(unused)
        else:
            print("  ✓ 所有定义标签都在数据中出现过")

    print(f"\n总计未使用标签数: {total_unused}")

    # 2. custom_tags 汇总
    print("\n" + "=" * 80)
    print("2. 自定义标签 custom_tags（去重后）")
    print("=" * 80)
    print(f"总计: {len(all_custom_tags)} 个\n")

    if all_custom_tags:
        for idx, tag in enumerate(sorted(all_custom_tags), 1):
            print(f"  {idx:3d}. {tag}")
    else:
        print("  （没有任何 custom_tags）")

    # 3. 安全检查：是否有「出现在 CSV 六大列里，但不在定义列表中的标签」——可能是拼写/规范问题
    print("\n" + "=" * 80)
    print("3. 检查：CSV 中使用但未在定义列表中的标签（可能是错误或未登记的新标签）")
    print("=" * 80)

    has_unknown = False
    for col in ["colors", "materials", "shapes", "decorations", "styles", "effects"]:
        defined = defined_labels[col]
        used = used_labels[col]
        unknown = used - defined
        if unknown:
            has_unknown = True
            print(f"\n【{col.Upper() if hasattr(col, 'Upper') else col.upper()}】中的未登记标签：")
            for label in sorted(unknown):
                print(f"  - {label}")

    if not has_unknown:
        print("\n✓ 所有六大列里的标签都在定义列表中，无未知标签")


if __name__ == "__main__":
    import sys

    path = "equipment_labels.csv"
    if len(sys.argv) > 1:
        path = sys.argv[1]

    analyze_csv(path)


