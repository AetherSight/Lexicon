"""
使用示例：演示如何使用FFXIV自动标注工具

目录结构示例：
images/
  ├── 上装_10001/
  │   ├── xxx_h0_p0.png    (正面图)
  │   ├── xxx_h180_p0.png   (背面图)
  │   └── ...
  ├── 上装_10002/
  │   ├── xxx_h0_p0.png
  │   ├── xxx_h180_p0.png
  │   └── ...
  └── ...
"""

import asyncio
from lexicon import FFXIVAutoLabeler

async def example_local_ollama():
    """示例1：使用本地Ollama（推荐4090显卡）"""
    
    # 本地Ollama配置（推荐）
    # api_key设为None，Ollama不需要key
    labeler = FFXIVAutoLabeler(
        api_key=None,  # Ollama不需要key
        base_url="http://localhost:11434/v1",  # Ollama本地地址
        model="qwen3-vl-thinking:8b",  # 默认8b模型
        max_concurrent=20,  # 本地运行可以设置更高并发
        output_csv="equipment_labels.csv"
    )
    
    # 图片目录应包含多个"装备名称_装备ID"子目录
    # 每个子目录中会自动选择*h0_p0.png和*h180_p0.png进行标注
    await labeler.label_directory(
        image_directory="path/to/your/images",  # 包含多个装备子目录的根目录
        equipment_type="上装",
        batch_size=100  # 本地运行可以设置更大批量
    )


async def example_remote_api():
    """示例2：使用远程API"""
    
    # 远程API配置
    labeler = FFXIVAutoLabeler(
        api_key="your-api-key-here",  # 替换为你的API密钥
        base_url="https://api.openai.com/v1",  # 远程API地址
        model="qwen/qwen3-vl-thinking",
        max_concurrent=10,  # 远程API建议较低并发
        output_csv="equipment_labels.csv"
    )
    
    await labeler.label_directory(
        image_directory="path/to/your/images",
        equipment_type="上装",
        batch_size=50
    )


async def example():
    """主示例：默认使用本地Ollama"""
    await example_local_ollama()

if __name__ == '__main__':
    asyncio.run(example())

