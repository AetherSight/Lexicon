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
    --dir "path/to/equipment/images" \
    --output "equipment_labels.csv"
```

### Test Mode

Set environment variable `DEBUG=true` to process only the first 10 equipment items:

```bash
DEBUG=true poetry run python -m lexicon \
    --dir "path/to/equipment/images"
```

### Parameters

- `--dir`: Image directory path (required), containing subdirectories in format "equipment_name_equipment_id"
- `--api`: API base URL (default: http://localhost:11434/v1)
- `--model`: Model name (default: qwen3-vl:8b-thinking)
- `--output`: Output CSV file path (default: equipment_labels.csv)

### Python Code Usage

```python
from lexicon import FFXIVAutoLabeler

labeler = FFXIVAutoLabeler(
    api_key=None,  # Not required for Ollama
    base_url="http://localhost:11434/v1",
    model="qwen3-vl:8b-thinking",
    output_csv="equipment_labels.csv"
)

labeler.label_directory(
    image_directory="path/to/images"
)
```

## License

AGPL-3.0
