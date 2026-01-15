"""
Training module for equipment labeling
"""

import os
import argparse
from dotenv import load_dotenv
from .labeler import FFXIVAutoLabeler

# Load environment variables from .env file
load_dotenv()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='FFXIV Equipment Auto-labeling Tool'
    )
    parser.add_argument('--dir', type=str, required=True, dest='image_dir', help='Image directory path')
    parser.add_argument('--output', type=str, default='equipment_labels.csv', dest='output_csv', help='Output CSV file path')
    
    args = parser.parse_args()
    
    ollama_host = os.getenv("OLLAMA_HOST")
    if ollama_host:
        os.environ["OLLAMA_HOST"] = ollama_host
        print(f"Ollama host set to: {ollama_host}")
    else:
        print("Ollama host not specified, using default: http://localhost:11434")
    
    model = os.getenv("OLLAMA_MODEL", "qwen3-vl:8b-thinking")
    print(f"Using model: {model}")
    
    api_key = os.getenv("API_KEY", None)
    base_url = "http://localhost:11434/v1"
    
    labeler = FFXIVAutoLabeler(
        api_key=api_key,
        base_url=base_url,
        model=model,
        output_csv=args.output_csv
    )
    
    labeler.label_directory(
        image_directory=args.image_dir
    )


def train_main():
    """Entry point for setuptools"""
    main()


if __name__ == '__main__':
    train_main()
