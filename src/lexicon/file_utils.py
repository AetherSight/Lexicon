"""
File utility module for path parsing, directory handling, and CSV operations
"""

import os
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
import pandas as pd


def parse_label_string(label_str: str) -> Set[str]:
    """
    Parse label string from CSV cell, split by comma and return as set
    
    Args:
        label_str: Label string (comma-separated)
    
    Returns:
        Set of labels
    """
    if not label_str:
        return set()
    # Handle empty string, None, etc.
    text = str(label_str).strip()
    if not text:
        return set()
    
    # Split by comma (support both English and Chinese commas)
    text = text.replace("，", ",")
    parts = [p.strip() for p in text.split(",")]
    return {p for p in parts if p}


def parse_equipment_info(directory_path: Path) -> Optional[Tuple[str, str]]:
    """
    Parse equipment name and ID from directory path
    Format: equipment_name_equipment_id
    
    Returns:
        (equipment_name, equipment_id) or None
    """
    dir_name = directory_path.name
    match = re.match(r'^(.+?)_(\d+)$', dir_name)
    if match:
        equipment_name = match.group(1)
        equipment_id = match.group(2)
        return equipment_name, equipment_id
    return None


def find_equipment_images(equipment_dir: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Find front and back images in equipment directory
    
    Returns:
        (front_image_path, back_image_path)
    """
    front_image = None
    back_image = None
    
    front_files = list(equipment_dir.glob("*h0_p0.png"))
    if front_files:
        front_image = str(front_files[0])
    
    back_files = list(equipment_dir.glob("*h180_p0.png"))
    if back_files:
        back_image = str(back_files[0])
    
    return front_image, back_image


def load_processed_equipment_ids(csv_path: str) -> Set[str]:
    """Load processed equipment IDs for resume support"""
    if not os.path.exists(csv_path):
        return set()
    
    try:
        df = pd.read_csv(csv_path)
        if 'equipment_id' in df.columns:
            equipment_ids = set(df['equipment_id'].dropna().astype(str).tolist())
            print(f"Loaded {len(equipment_ids)} processed equipment")
            return equipment_ids
    except Exception as e:
        print(f"Error loading processed equipment: {e}")
    
    return set()


def get_equipment_directories(
    root_directory: str,
    processed_ids: Set[str]
) -> List[Tuple[Path, str, str]]:
    """
    Get all equipment directories
    
    Args:
        root_directory: Root directory path
        processed_ids: Set of processed equipment IDs
    
    Returns:
        List of (equipment_dir, equipment_name, equipment_id)
    """
    root_path = Path(root_directory)
    equipment_dirs = []
    
    for item in root_path.iterdir():
        if item.is_dir():
            info = parse_equipment_info(item)
            if info:
                equipment_name, equipment_id = info
                if equipment_id not in processed_ids:
                    equipment_dirs.append((item, equipment_name, equipment_id))
    
    return sorted(equipment_dirs, key=lambda x: x[2])


def flatten_labels(result: Dict) -> Dict:
    """Flatten label result to CSV row"""
    row = {
        'equipment_id': result.get('equipment_id', ''),
        'equipment_name': result.get('equipment_name', ''),
        'front_image': result.get('front_image', ''),
        'back_image': result.get('back_image', ''),
        'timestamp': result.get('timestamp', ''),
    }
    
    labels = result.get('labels', {})
    
    row['colors'] = ', '.join(labels.get('colors', []))
    row['materials'] = ', '.join(labels.get('materials', []))
    row['shapes'] = ', '.join(labels.get('shapes', []))
    row['decorations'] = ', '.join(labels.get('decorations', []))
    row['styles'] = ', '.join(labels.get('styles', []))
    row['effects'] = ', '.join(labels.get('effects', []))
    
    looks_like = labels.get('appearance_looks_like', [])
    if isinstance(looks_like, list):
        row['appearance_looks_like'] = ', '.join(looks_like)
    elif isinstance(looks_like, str):
        row['appearance_looks_like'] = looks_like
    else:
        row['appearance_looks_like'] = ''
    row['appearance_description'] = labels.get('appearance_description', '')
    
    custom_tags = labels.get('custom_tags', [])
    if isinstance(custom_tags, list):
        row['custom_tags'] = ', '.join(custom_tags)
    elif isinstance(custom_tags, str):
        row['custom_tags'] = custom_tags
    else:
        row['custom_tags'] = ''
    
    all_labels = []
    for category in ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects']:
        all_labels.extend(labels.get(category, []))
    row['all_labels'] = ', '.join(all_labels)
    
    if 'error' in result:
        row['error'] = result['error']
    else:
        row['error'] = ''
    
    return row


def save_results_to_csv(results: List[Dict], csv_path: str):
    """Save results to CSV"""
    if not results:
        return
    
    rows = [flatten_labels(r) for r in results]
    
    file_exists = os.path.exists(csv_path)
    with open(csv_path, 'a', newline='', encoding='utf-8-sig') as f:
        fieldnames = [
            'equipment_id', 'equipment_name', 
            'front_image', 'back_image',
            'colors', 'materials', 'shapes', 'decorations', 
            'styles', 'effects', 'appearance_looks_like', 'appearance_description', 'custom_tags', 'all_labels',
            'error', 'timestamp'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerows(rows)

