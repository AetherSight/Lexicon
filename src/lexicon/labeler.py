"""
核心标注器模块
"""

import asyncio
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
    categories = ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects', 'type_specific']
    
    for category in categories:
        set1 = set(labels1.get(category, []))
        set2 = set(labels2.get(category, []))
        merged[category] = sorted(list(set1 | set2))  # 取并集并排序
    
    return merged


class FFXIVAutoLabeler:
    """FFXIV装备自动标注器"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3-vl-thinking:8b",
        max_concurrent: int = 10,
        output_csv: str = "equipment_labels.csv"
    ):
        """
        初始化标注器
        
        Args:
            api_key: API密钥（Ollama不需要，设为None即可）
            base_url: API基础URL
            model: 模型名称（默认: qwen3-vl-thinking:8b）
            max_concurrent: 最大并发数（本地运行可以设置更高，如20-30）
            output_csv: 输出CSV文件路径
        """
        self.api_client = APIClient(api_key=api_key, base_url=base_url, model=model)
        self.max_concurrent = max_concurrent
        self.output_csv = output_csv
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.processed_equipment_ids: Set[str] = set()
        
        # 加载已处理装备（断点续传，固定启用）
        if output_csv:
            self.processed_equipment_ids = load_processed_equipment_ids(output_csv)
    
    async def _label_single_image(
        self,
        image_path: str,
        equipment_type: str
    ) -> Optional[Dict]:
        """
        标注单张图片
        
        Args:
            image_path: 图片路径
            equipment_type: 装备类型（如"上装"、"大剑"等）
        
        Returns:
            标注结果字典，失败返回None
        """
        async with self.semaphore:
            prompt = get_prompt_template(equipment_type)
            result = await self.api_client.label_image(image_path, prompt)
            
            if result.get('error'):
                print(f"处理 {image_path} 时出错: {result['error']}")
            
            return {
                'image_path': image_path,
                'equipment_type': equipment_type,
                'labels': result.get('labels', {}),
                'raw_response': result.get('raw_response', ''),
                'error': result.get('error'),
                'timestamp': datetime.now().isoformat()
            }
    
    async def label_directory(
        self,
        image_directory: str,
        equipment_type: str,
        batch_size: int = 50
    ):
        """
        批量标注目录下的所有装备
        每个装备选择正面图和背面图，标注后合并标签
        
        Args:
            image_directory: 图片目录路径（包含多个"装备名称_装备ID"子目录）
            equipment_type: 装备类型
            batch_size: 每批保存的结果数量
        """
        equipment_dirs = get_equipment_directories(image_directory, self.processed_equipment_ids)
        
        if not equipment_dirs:
            print(f"在 {image_directory} 中未找到需要处理的装备目录")
            return
        
        print(f"找到 {len(equipment_dirs)} 个装备需要处理")
        
        async def process_equipment(equipment_dir, equipment_name: str, equipment_id: str) -> Optional[Dict]:
            """处理单个装备"""
            # 查找正面图和背面图
            front_image, back_image = find_equipment_images(equipment_dir)
            
            if not front_image and not back_image:
                print(f"警告: 装备 {equipment_name}_{equipment_id} 未找到正反面图片，跳过")
                return None
            
            # 标注两张图片（并发处理）
            labels_front = {}
            labels_back = {}
            error_msg = ""
            
            tasks = []
            if front_image:
                tasks.append(('front', self._label_single_image(front_image, equipment_type)))
            if back_image:
                tasks.append(('back', self._label_single_image(back_image, equipment_type)))
            
            # 并发执行标注任务
            if tasks:
                results_dict = {}
                for name, task in tasks:
                    try:
                        result = await task
                        results_dict[name] = result
                    except Exception as e:
                        error_msg += f"{name}图异常: {str(e)}; "
                
                # 处理正面图结果
                if 'front' in results_dict:
                    result_front = results_dict['front']
                    if result_front and result_front.get('labels'):
                        labels_front = result_front['labels']
                    elif result_front and result_front.get('error'):
                        error_msg += f"正面图错误: {result_front['error']}; "
                
                # 处理背面图结果
                if 'back' in results_dict:
                    result_back = results_dict['back']
                    if result_back and result_back.get('labels'):
                        labels_back = result_back['labels']
                    elif result_back and result_back.get('error'):
                        error_msg += f"背面图错误: {result_back['error']}; "
            
            # 合并标签（取并集）
            merged_labels = merge_labels(labels_front, labels_back)
            
            # 构建结果
            result = {
                'equipment_id': equipment_id,
                'equipment_name': equipment_name,
                'equipment_type': equipment_type,
                'front_image': front_image or '',
                'back_image': back_image or '',
                'labels': merged_labels,
                'timestamp': datetime.now().isoformat()
            }
            
            if error_msg:
                result['error'] = error_msg.strip()
            
            self.processed_equipment_ids.add(equipment_id)
            return result
        
        # 创建所有装备的处理任务
        tasks = [
            process_equipment(equipment_dir, equipment_name, equipment_id)
            for equipment_dir, equipment_name, equipment_id in equipment_dirs
        ]
        
        # 批量处理（使用tqdm显示进度）
        results = []
        with tqdm(total=len(tasks), desc="标注进度") as pbar:
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    results.append(result)
                
                pbar.update(1)
                
                # 批量保存
                if len(results) >= batch_size:
                    save_results_to_csv(results, self.output_csv)
                    results = []
        
        # 保存剩余结果
        if results:
            save_results_to_csv(results, self.output_csv)
        
        print(f"\n标注完成！结果已保存到 {self.output_csv}")

