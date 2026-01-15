# Lexicon

FFXIV Equipment Auto-labeling Tool

## Installation

```bash
git clone https://github.com/AetherSight/Lexicon.git
cd Lexicon

poetry install
```

## Usage

### Training (Labeling Equipment Images)

To train/label equipment images, use the `lexicon` command:

```bash
poetry run lexicon \
    --dir "path/to/equipment/images" \
    --output "equipment_labels.csv"
```

Or use the module directly:

```bash
poetry run python -m lexicon.train \
    --dir "path/to/equipment/images" \
    --output "equipment_labels.csv"
```

### Test Mode

Set environment variable `DEBUG=true` to process only the first 10 equipment items:

```bash
DEBUG=true poetry run lexicon \
    --dir "path/to/equipment/images"
```

### Parameters

- `--dir`: Image directory path (required), containing subdirectories in format "equipment_name_equipment_id"
- `--output`: Output CSV file path (default: equipment_labels.csv)

Note: `OLLAMA_HOST` and `OLLAMA_MODEL` are read from environment variables (`.env` file). See the FastAPI setup section for configuration details.

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

## FastAPI Web Service

The project includes a FastAPI web service for equipment tag-based search.

### Setup

1. Create a `.env` file in the project root (you can copy from `env.example`):

```bash
cp env.example .env
```

Or manually create `.env` with the following content:

```bash
# Equipment Data CSV Path (required)
# Can be absolute path or relative to project root
CSV_PATH=csv/equipment_labels_epoch_1.csv

# Server Configuration (optional)
HOST=0.0.0.0
PORT=9000
```

2. Run the FastAPI application:

```bash
poetry run python -m lexicon
```

Or using uvicorn directly:

```bash
poetry run uvicorn lexicon.app:app --host 0.0.0.0 --port 9000
```

### API Endpoints

- `GET /tags`: Get all available tags for autocomplete and search filtering
- `GET /search`: Search equipment by tags

### API Examples

#### Get All Tags

```bash
curl "http://localhost:9000/tags"
```

Response:
```json
{
  "tags": ["金色", "金属", "铠甲", ...],
  "count": 1234
}
```

#### Search Equipment

```bash
curl "http://localhost:9000/search?tags=金色&tags=金属&top_k=10"
```

Or with array syntax:
```bash
curl "http://localhost:9000/search?tags[]=金色&tags[]=金属&top_k=10"
```

Response:
```json
{
  "query_tags": ["金色", "金属"],
  "total_matches": 45,
  "results": [
    {
      "equipment_id": "12345",
      "equipment_name": "装备名称",
      "all_labels": "金色, 金属, 铠甲, ...",
      "appearance_description": "详细描述...",
      "match_score": 0.8,
      "matched_labels": ["金色", "金属"],
      "description_matches": [],
      "name_matches": []
    },
    ...
  ]
}
```

The search matches tags in:
- `all_labels`: Exact tag matching
- `appearance_description`: Text contains matching (case-insensitive)
- `equipment_name`: Text contains matching (case-insensitive)

## License

AGPL-3.0
