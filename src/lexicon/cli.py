"""
命令行接口模块
"""

import argparse
from .labeler import FFXIVAutoLabeler


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='FFXIV装备自动标注工具'
    )
    parser.add_argument('--dir', type=str, required=True, dest='image_dir', help='图片目录路径（包含"装备名称_装备ID"子目录）')
    parser.add_argument('--key', type=str, default=None, dest='api_key', help='API密钥（Ollama不需要，可省略）')
    parser.add_argument('--api', type=str, default='http://localhost:11434/v1', dest='base_url', help='API基础URL（默认: http://localhost:11434/v1）')
    parser.add_argument('--model', type=str, default='qwen3-vl:8b-thinking', help='模型名称（默认: qwen3-vl:8b-thinking）')
    parser.add_argument('--output', type=str, default='equipment_labels.csv', dest='output_csv', help='输出CSV文件路径')
    
    args = parser.parse_args()
    
    labeler = FFXIVAutoLabeler(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        output_csv=args.output_csv
    )
    
    labeler.label_directory(
        image_directory=args.image_dir
    )


def cli_main():
    """同步入口点，供setuptools使用"""
    main()


if __name__ == '__main__':
    cli_main()

