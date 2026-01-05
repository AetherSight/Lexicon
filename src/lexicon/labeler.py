"""
核心标注器模块
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
    合并两个标签结果（取并集）
    
    Args:
        labels1: 第一个标签结果
        labels2: 第二个标签结果
    
    Returns:
        合并后的标签结果
    """
    merged = {}
    categories = ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects']
    
    for category in categories:
        set1 = set(labels1.get(category, []))
        set2 = set(labels2.get(category, []))
        merged[category] = sorted(list(set1 | set2))  # 取并集并排序
    
    # 合并外观类型（取并集，和其他标签一样）
    looks_like1 = labels1.get('appearance_looks_like', [])
    looks_like2 = labels2.get('appearance_looks_like', [])
    # 确保是列表格式
    if isinstance(looks_like1, str):
        looks_like1 = [looks_like1] if looks_like1 else []
    if isinstance(looks_like2, str):
        looks_like2 = [looks_like2] if looks_like2 else []
    set1 = set(looks_like1)
    set2 = set(looks_like2)
    merged['appearance_looks_like'] = sorted(list(set1 | set2))  # 取并集并排序
    
    # 合并外观描述（取两个描述的结合）
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
    
    # 合并自定义标签（取并集）
    custom1 = labels1.get('custom_tags', [])
    custom2 = labels2.get('custom_tags', [])
    if isinstance(custom1, str):
        custom1 = [custom1] if custom1 else []
    if isinstance(custom2, str):
        custom2 = [custom2] if custom2 else []
    set1 = set(custom1)
    set2 = set(custom2)
    merged['custom_tags'] = sorted(list(set1 | set2))  # 取并集并排序
    
    return merged


class FFXIVAutoLabeler:
    """FFXIV装备自动标注器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3-vl:8b-thinking",
        output_csv: str = "equipment_labels.csv"
    ):
        """
        初始化标注器
        
        Args:
            api_key: API密钥（Ollama不需要，设为None即可）
            base_url: API基础URL
            model: 模型名称（默认: qwen3-vl:8b-thinking）
            output_csv: 输出CSV文件路径
        """
        self.api_client = APIClient(api_key=api_key, base_url=base_url, model=model)
        self.output_csv = output_csv
        self.processed_equipment_ids: Set[str] = set()
        
        # 加载已处理装备（断点续传，固定启用）
        if output_csv:
            self.processed_equipment_ids = load_processed_equipment_ids(output_csv)
    
    def _label_single_image(
        self,
        image_path: str
    ) -> Optional[Dict]:
        """
        标注单张图片
        
        Args:
            image_path: 图片路径
        
        Returns:
            标注结果字典，失败返回None
        """
        prompt = get_prompt_template()
        result = self.api_client.label_image(image_path, prompt)
        
        if result.get('error'):
            print(f"处理 {image_path} 时出错: {result['error']}")
            if result.get('raw_response'):
                # 总是输出原始响应以便调试
                raw = result['raw_response']
                print(f"[DEBUG] 原始响应 :\n{raw}")
        
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
        批量标注目录下的所有装备
        每个装备选择正面图和背面图，标注后合并标签
        
        Args:
            image_directory: 图片目录路径（包含多个"装备名称_装备ID"子目录）
        """
        equipment_dirs = get_equipment_directories(image_directory, self.processed_equipment_ids)
        
        if not equipment_dirs:
            print(f"在 {image_directory} 中未找到需要处理的装备目录")
            return
        
        # 检查测试模式
        is_debug = os.getenv('DEBUG', '').lower() == 'true'
        if is_debug:
            original_count = len(equipment_dirs)
            equipment_dirs = equipment_dirs[:10]  # 只处理前10个装备
            print(f"[测试模式] 找到 {original_count} 个装备，仅处理前 {len(equipment_dirs)} 个")
        else:
            print(f"找到 {len(equipment_dirs)} 个装备需要处理")
        
        def process_equipment(equipment_dir, equipment_name: str, equipment_id: str) -> Optional[Dict]:
            """处理单个装备"""
            # 查找正面图和背面图
            front_image, back_image = find_equipment_images(equipment_dir)
            
            if not front_image and not back_image:
                print(f"警告: 装备 {equipment_name}_{equipment_id} 未找到正反面图片，跳过")
                return None
            
            # 标注两张图片（顺序处理）
            labels_front = {}
            labels_back = {}
            error_msg = ""
            
            # 处理正面图
            if front_image:
                try:
                    result = self._label_single_image(front_image)
                    if result and result.get('labels'):
                        labels_front = result['labels']
                    elif result and result.get('error'):
                        error_msg += f"正面图错误: {result['error']}; "
                except Exception as e:
                    error_msg += f"正面图异常: {str(e)}; "
            
            # 处理背面图
            if back_image:
                try:
                    result = self._label_single_image(back_image)
                    if result and result.get('labels'):
                        labels_back = result['labels']
                    elif result and result.get('error'):
                        error_msg += f"背面图错误: {result['error']}; "
                except Exception as e:
                    error_msg += f"背面图异常: {str(e)}; "
            
            # 合并标签（取并集）
            merged_labels = merge_labels(labels_front, labels_back)
            
            # 构建结果
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
        
        # 顺序处理所有装备，处理一个保存一个
        with tqdm(total=len(equipment_dirs), desc="标注进度") as pbar:
            for equipment_dir, equipment_name, equipment_id in equipment_dirs:
                try:
                    result = process_equipment(equipment_dir, equipment_name, equipment_id)
                    if result:
                        # 每处理完一个装备就立即保存
                        save_results_to_csv([result], self.output_csv)
                    pbar.update(1)
                except Exception as e:
                    print(f"处理装备时出错: {e}")
                    pbar.update(1)
        
        print(f"\n标注完成！结果已保存到 {self.output_csv}")
