"""
API客户端模块
处理与AI模型的API交互
"""

import json
import re
import base64
from pathlib import Path
from typing import Dict, Optional
from openai import AsyncOpenAI


def encode_image(image_path: str) -> str:
    """将图片编码为base64"""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def get_image_format(image_path: str) -> str:
    """获取图片格式"""
    ext = Path(image_path).suffix.lower()
    if ext == '.jpg' or ext == '.jpeg':
        return 'image/jpeg'
    elif ext == '.png':
        return 'image/png'
    elif ext == '.webp':
        return 'image/webp'
    elif ext == '.bmp':
        return 'image/bmp'
    return 'image/jpeg'


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
        model: str = "qwen3-vl-thinking:8b"
    ):
        """
        初始化API客户端
        
        Args:
            api_key: API密钥（Ollama不需要，设为None即可）
            base_url: API基础URL
            model: 模型名称
        """
        self.client = AsyncOpenAI(api_key=api_key or "ollama", base_url=base_url)
        self.model = model
    
    async def label_image(
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
        try:
            # 读取并编码图片
            base64_image = encode_image(image_path)
            image_format = get_image_format(image_path)
            
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_format};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,  # 降低温度以获得更一致的结果
                max_tokens=2000
            )
            
            # 解析响应
            content = response.choices[0].message.content.strip()
            
            # 尝试提取JSON
            json_str = extract_json(content)
            if json_str:
                labels = json.loads(json_str)
                return {
                    'labels': labels,
                    'raw_response': content,
                    'error': None
                }
            else:
                return {
                    'labels': {},
                    'raw_response': content,
                    'error': 'JSON解析失败'
                }
                
        except Exception as e:
            return {
                'labels': {},
                'raw_response': '',
                'error': str(e)
            }

