"""
Core labeling module
"""

import os
from typing import Dict, List, Optional, Set
from datetime import datetime
from tqdm import tqdm

from .api_client import APIClient
from .file_utils import (
    find_equipment_images,
    get_equipment_directories,
    load_processed_equipment_ids,
    save_results_to_csv
)
from .label_system import get_prompt_template


def merge_labels(labels1: Dict, labels2: Dict) -> Dict:
    """
    Merge two label results (union)
    
    Args:
        labels1: First label result
        labels2: Second label result
    
    Returns:
        Merged label result
    """
    merged = {}
    categories = ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects']
    
    for category in categories:
        set1 = set(labels1.get(category, []))
        set2 = set(labels2.get(category, []))
        merged[category] = sorted(list(set1 | set2))
    
    looks_like1 = labels1.get('appearance_looks_like', [])
    looks_like2 = labels2.get('appearance_looks_like', [])
    if isinstance(looks_like1, str):
        looks_like1 = [looks_like1] if looks_like1 else []
    if isinstance(looks_like2, str):
        looks_like2 = [looks_like2] if looks_like2 else []
    set1 = set(looks_like1)
    set2 = set(looks_like2)
    merged['appearance_looks_like'] = sorted(list(set1 | set2))
    
    desc1 = labels1.get('appearance_description', '')
    desc2 = labels2.get('appearance_description', '')
    if desc1 and desc2:
        merged['appearance_description'] = f"{desc1}；{desc2}"
    elif desc1:
        merged['appearance_description'] = desc1
    elif desc2:
        merged['appearance_description'] = desc2
    else:
        merged['appearance_description'] = ''
    
    custom1 = labels1.get('custom_tags', [])
    custom2 = labels2.get('custom_tags', [])
    if isinstance(custom1, str):
        custom1 = [custom1] if custom1 else []
    if isinstance(custom2, str):
        custom2 = [custom2] if custom2 else []
    set1 = set(custom1)
    set2 = set(custom2)
    merged['custom_tags'] = sorted(list(set1 | set2))
    
    return merged


class FFXIVAutoLabeler:
    """FFXIV equipment auto-labeler"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3-vl:8b-thinking",
        output_csv: str = "equipment_labels.csv"
    ):
        """
        Initialize labeler
        
        Args:
            api_key: API key (not required for Ollama, set to None)
            base_url: API base URL
            model: Model name (default: qwen3-vl:8b-thinking)
            output_csv: Output CSV file path
        """
        self.api_client = APIClient(api_key=api_key, base_url=base_url, model=model)
        self.output_csv = output_csv
        self.processed_equipment_ids: Set[str] = set()
        
        if output_csv:
            self.processed_equipment_ids = load_processed_equipment_ids(output_csv)
    
    def _label_single_image(
        self,
        image_path: str
    ) -> Optional[Dict]:
        """
        Label a single image
        
        Args:
            image_path: Image file path
        
        Returns:
            Label result dictionary, None on failure
        """
        prompt = get_prompt_template()
        result = self.api_client.label_image(image_path, prompt)
        
        if result.get('error'):
            print(f"Error processing {image_path}: {result['error']}")
            if result.get('raw_response'):
                raw = result['raw_response']
                print(f"[DEBUG] Raw response:\n{raw}")
        
        return {
            'image_path': image_path,
            'labels': result.get('labels', {}),
            'raw_response': result.get('raw_response', ''),
            'error': result.get('error'),
            'timestamp': datetime.now().isoformat()
        }
    
    def label_directory(
        self,
        image_directory: str
    ):
        """
        Batch label all equipment in directory
        Each equipment uses front and back images, labels are merged after labeling
        
        Args:
            image_directory: Image directory path (containing "equipment_name_equipment_id" subdirectories)
        """
        equipment_dirs = get_equipment_directories(image_directory, self.processed_equipment_ids)
        
        if not equipment_dirs:
            print(f"No equipment directories found in {image_directory}")
            return
        
        is_debug = os.getenv('DEBUG', '').lower() == 'true'
        if is_debug:
            original_count = len(equipment_dirs)
            equipment_dirs = equipment_dirs[:10]
            print(f"[Test Mode] Found {original_count} equipment, processing first {len(equipment_dirs)}")
        else:
            print(f"Found {len(equipment_dirs)} equipment to process")
        
        def process_equipment(equipment_dir, equipment_name: str, equipment_id: str) -> Optional[Dict]:
            """Process single equipment"""
            front_image, back_image = find_equipment_images(equipment_dir)
            
            if not front_image and not back_image:
                print(f"Warning: Equipment {equipment_name}_{equipment_id} has no front/back images, skipping")
                return None
            
            labels_front = {}
            labels_back = {}
            error_msg = ""
            
            if front_image:
                try:
                    result = self._label_single_image(front_image)
                    if result and result.get('labels'):
                        labels_front = result['labels']
                    elif result and result.get('error'):
                        error_msg += f"Front image error: {result['error']}; "
                except Exception as e:
                    error_msg += f"Front image exception: {str(e)}; "
            
            if back_image:
                try:
                    result = self._label_single_image(back_image)
                    if result and result.get('labels'):
                        labels_back = result['labels']
                    elif result and result.get('error'):
                        error_msg += f"Back image error: {result['error']}; "
                except Exception as e:
                    error_msg += f"Back image exception: {str(e)}; "
            
            merged_labels = merge_labels(labels_front, labels_back)
            
            result = {
                'equipment_id': equipment_id,
                'equipment_name': equipment_name,
                'front_image': front_image or '',
                'back_image': back_image or '',
                'labels': merged_labels,
                'timestamp': datetime.now().isoformat()
            }
            
            if error_msg:
                result['error'] = error_msg.strip()
            
            self.processed_equipment_ids.add(equipment_id)
            return result
        
        with tqdm(total=len(equipment_dirs), desc="Labeling progress") as pbar:
            for equipment_dir, equipment_name, equipment_id in equipment_dirs:
                try:
                    result = process_equipment(equipment_dir, equipment_name, equipment_id)
                    if result:
                        save_results_to_csv([result], self.output_csv)
                    pbar.update(1)
                except Exception as e:
                    print(f"Error processing equipment: {e}")
                    pbar.update(1)
        
        print(f"\nLabeling completed! Results saved to {self.output_csv}")
