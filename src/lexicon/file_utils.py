"""
文件处理工具模块
处理文件路径、目录解析、CSV保存等功能
"""

import os
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import pandas as pd


def parse_equipment_info(directory_path: Path) -> Optional[Tuple[str, str]]:
    """
    从目录路径解析装备名称和ID
    格式：装备名称_装备ID
    
    Returns:
        (equipment_name, equipment_id) 或 None
    """
    dir_name = directory_path.name
    # 匹配格式：装备名称_装备ID
    match = re.match(r'^(.+?)_(\d+)$', dir_name)
    if match:
        equipment_name = match.group(1)
        equipment_id = match.group(2)
        return equipment_name, equipment_id
    return None


def find_equipment_images(equipment_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    在装备目录中查找正面图和背面图
    
    Returns:
        (front_image_path, back_image_path)
    """
    front_image = None
    back_image = None
    
    # 查找正面图 *h0_p0.png
    front_files = list(equipment_dir.glob("*h0_p0.png"))
    if front_files:
        front_image = str(front_files[0])
    
    # 查找背面图 *h180_p0.png
    back_files = list(equipment_dir.glob("*h180_p0.png"))
    if back_files:
        back_image = str(back_files[0])
    
    return front_image, back_image


def load_processed_equipment_ids(csv_path: str) -> Set[str]:
    """加载已处理的装备ID列表（用于断点续传）"""
    if not os.path.exists(csv_path):
        return set()
    
    try:
        df = pd.read_csv(csv_path)
        if 'equipment_id' in df.columns:
            equipment_ids = set(df['equipment_id'].dropna().astype(str).tolist())
            print(f"已加载 {len(equipment_ids)} 个已处理装备")
            return equipment_ids
    except Exception as e:
        print(f"加载已处理装备时出错: {e}")
    
    return set()


def get_equipment_directories(
    root_directory: str,
    processed_ids: Set[str]
) -> List[Tuple[Path, str, str]]:
    """
    获取所有装备目录
    
    Args:
        root_directory: 根目录路径
        processed_ids: 已处理的装备ID集合
    
    Returns:
        List of (equipment_dir, equipment_name, equipment_id)
    """
    root_path = Path(root_directory)
    equipment_dirs = []
    
    # 遍历所有子目录
    for item in root_path.iterdir():
        if item.is_dir():
            info = parse_equipment_info(item)
            if info:
                equipment_name, equipment_id = info
                # 检查是否已处理
                if equipment_id not in processed_ids:
                    equipment_dirs.append((item, equipment_name, equipment_id))
    
    return sorted(equipment_dirs, key=lambda x: x[2])  # 按装备ID排序


def flatten_labels(result: Dict) -> Dict:
    """将标签结果扁平化为CSV行"""
    row = {
        'equipment_id': result.get('equipment_id', ''),
        'equipment_name': result.get('equipment_name', ''),
        'front_image': result.get('front_image', ''),
        'back_image': result.get('back_image', ''),
        'timestamp': result.get('timestamp', ''),
    }
    
    labels = result.get('labels', {})
    
    # 扁平化各个标签类别
    row['colors'] = ', '.join(labels.get('colors', []))
    row['materials'] = ', '.join(labels.get('materials', []))
    row['shapes'] = ', '.join(labels.get('shapes', []))
    row['decorations'] = ', '.join(labels.get('decorations', []))
    row['styles'] = ', '.join(labels.get('styles', []))
    row['effects'] = ', '.join(labels.get('effects', []))
    # 处理 appearance_looks_like（可能是列表或字符串）
    looks_like = labels.get('appearance_looks_like', [])
    if isinstance(looks_like, list):
        row['appearance_looks_like'] = ', '.join(looks_like)
    elif isinstance(looks_like, str):
        row['appearance_looks_like'] = looks_like
    else:
        row['appearance_looks_like'] = ''
    row['appearance_description'] = labels.get('appearance_description', '')
    
    # 所有标签合并
    all_labels = []
    for category in ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects']:
        all_labels.extend(labels.get(category, []))
    row['all_labels'] = ', '.join(all_labels)
    
    # 错误信息
    if 'error' in result:
        row['error'] = result['error']
    else:
        row['error'] = ''
    
    return row


def save_results_to_csv(results: List[Dict], csv_path: str):
    """保存结果到CSV"""
    if not results:
        return
    
    # 扁平化结果
    rows = [flatten_labels(r) for r in results]
    
    # 写入CSV
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        fieldnames = [
            'equipment_id', 'equipment_name', 
            'front_image', 'back_image',
            'colors', 'materials', 'shapes', 'decorations', 
            'styles', 'effects', 'appearance_looks_like', 'appearance_description', 'all_labels',
            'error', 'timestamp'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(rows)

