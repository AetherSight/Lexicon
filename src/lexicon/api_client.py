"""
API客户端模块
处理与AI模型的API交互
"""

import os
import json
import re
from typing import Dict, Optional
from ollama import chat


def extract_json(text: str) -> Optional[str]:
    """从文本中提取JSON"""
    # 尝试直接解析
    try:
        json.loads(text)
        return text
    except:
        pass
    
    # 尝试提取代码块中的JSON
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    
    # 尝试提取大括号中的内容
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    
    return None


class APIClient:
    """API客户端封装"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434/v1",
        model: str = "gemma3"
    ):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥（Ollama不需要，设为None即可）
            base_url: API基础URL（保留用于兼容性，ollama chat 不使用此参数）
            model: 模型名称（默认: gemma3）
        """
        self.model = model
    
    def label_image(
        self,
        image_path: str,
        prompt: str
    ) -> Dict:
        """
        标注单张图片
        
        Args:
            image_path: 图片路径
            prompt: 提示词
        
        Returns:
            标注结果字典
        """
        max_attempts = 3
        last_error: Optional[str] = None
        last_content: str = ""
        is_debug = os.getenv('DEBUG', '').lower() == 'true'

        for attempt in range(1, max_attempts + 1):
            try:
                # 直接调用 ollama chat
                response = chat(
                    model=self.model,
                    messages=[
                        {
                            'role': 'user',
                            'content': prompt,
                            'images': [image_path],
                        }
                    ],
                )
                content = response.message.content.strip()
                last_content = content
                
                # 尝试提取JSON
                json_str = extract_json(content)
                if json_str:
                    try:
                        labels = json.loads(json_str)
                        return {
                            'labels': labels,
                            'raw_response': content,
                            'error': None
                        }
                    except json.JSONDecodeError as e:
                        # JSON解析失败，记录错误并重试
                        last_error = f'JSON解析失败: {str(e)}'
                        if is_debug:
                            print(f"\n[DEBUG] 第 {attempt} 次解析 JSON 失败: {e}")
                            print(f"[DEBUG] 提取的JSON字符串: {json_str[:500]}...")  # 只显示前500字符
                        # 继续下一次循环重试
                        continue
                else:
                    # 无法提取JSON，记录错误并重试
                    last_error = 'JSON解析失败: 无法从响应中提取JSON'
                    if is_debug:
                        print(f"\n[DEBUG] 第 {attempt} 次解析失败：无法从响应中提取JSON")
                        print(f"[DEBUG] 原始响应内容:\n{content}")
                    continue
                    
            except Exception as e:
                # 调用接口本身出错，记录错误并重试
                last_error = str(e)
                if is_debug:
                    print(f"\n[DEBUG] 第 {attempt} 次调用模型出错: {e}")
                continue

        # 多次重试仍然失败，返回最后一次错误与最后一次响应内容（如果有）
        return {
            'labels': {},
            'raw_response': last_content,
            'error': last_error or '未知错误'
        }

