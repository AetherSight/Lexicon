# Lexicon

FFXIV Equipment Auto-labeling Tool

## Installation

```bash
git clone https://github.com/AetherSight/Lexicon.git
cd Lexicon

poetry install
```

## Usage

```bash
poetry run python -m lexicon \
    --image_dir "path/to/equipment/images" \
    --equipment_type "上装" \
    --max_concurrent 20 \
    --output_csv "equipment_labels.csv"
```

### Parameters

- `--image_dir`: Image directory path (required), containing subdirectories in format "equipment_name_equipment_id"
- `--equipment_type`: Equipment type (required), e.g., "上装", "大剑", "单手剑", etc.
- `--base_url`: API base URL (default: http://localhost:11434/v1)
- `--model`: Model name (default: qwen3-vl-thinking:8b)
- `--max_concurrent`: Maximum concurrency (default: 10, recommended 20-30 for local execution)
- `--output_csv`: Output CSV file path (default: equipment_labels.csv)
- `--batch_size`: Batch save size (default: 50)

### Python Code Usage

```python
import asyncio
from lexicon import FFXIVAutoLabeler

async def main():
    labeler = FFXIVAutoLabeler(
        api_key=None,  # Not required for Ollama
        base_url="http://localhost:11434/v1",
        model="qwen3-vl-thinking:8b",
        max_concurrent=20,
        output_csv="equipment_labels.csv"
    )
    
    await labeler.label_directory(
        image_directory="path/to/images",
        equipment_type="上装",
        batch_size=50
    )

asyncio.run(main())
```

## License

AGPL-3.0
