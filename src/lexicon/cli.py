"""
命令行接口模块
"""

import asyncio
import argparse
from .labeler import FFXIVAutoLabeler


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='FFXIV装备自动标注工具')
    parser.add_argument('--image_dir', type=str, required=True, help='图片目录路径（包含"装备名称_装备ID"子目录）')
    parser.add_argument('--equipment_type', type=str, required=True, help='装备类型（如：上装、大剑等）')
    parser.add_argument('--api_key', type=str, default=None, help='API密钥（Ollama不需要，可省略）')
    parser.add_argument('--base_url', type=str, default='http://localhost:11434/v1', help='API基础URL（默认: http://localhost:11434/v1）')
    parser.add_argument('--model', type=str, default='qwen3-vl-thinking:8b', help='模型名称（默认: qwen3-vl-thinking:8b）')
    parser.add_argument('--max_concurrent', type=int, default=10, help='最大并发数（本地运行建议20-30）')
    parser.add_argument('--output_csv', type=str, default='equipment_labels.csv', help='输出CSV文件路径')
    parser.add_argument('--batch_size', type=int, default=50, help='批量保存大小')
    
    args = parser.parse_args()
    
    labeler = FFXIVAutoLabeler(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        max_concurrent=args.max_concurrent,
        output_csv=args.output_csv
    )
    
    await labeler.label_directory(
        image_directory=args.image_dir,
        equipment_type=args.equipment_type,
        batch_size=args.batch_size
    )


def cli_main():
    """同步入口点，供setuptools使用"""
    asyncio.run(main())


if __name__ == '__main__':
    cli_main()

