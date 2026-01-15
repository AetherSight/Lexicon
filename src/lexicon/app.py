"""
FastAPI Application: Equipment Search Service
Provides API endpoints to search equipment by tags
"""

import os
import csv
from pathlib import Path
from typing import List, Dict, Optional, Set
from collections import defaultdict
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from .file_utils import parse_label_string

# Load environment variables from .env file
load_dotenv()


app = FastAPI(title="FFXIV Equipment Matcher", version="1.0.0")

# Global variables
equipment_df: Optional[pd.DataFrame] = None
all_tags_cache: Set[str] = set()
gear_model_data: Optional[Dict[str, Dict]] = None
model_groups: Optional[Dict[str, List[str]]] = None




def load_equipment_data(csv_path: str) -> pd.DataFrame:
    """Load equipment data from CSV file"""
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Equipment data file not found: {csv_path}")
    
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df)} equipment records from {csv_path}")
    return df


def calculate_label_similarity(
    query_labels: List[str],
    equipment_labels: str
) -> float:
    """Calculate similarity between query labels and equipment labels"""
    if not equipment_labels or pd.isna(equipment_labels):
        return 0.0
    
    equipment_label_set = parse_label_string(str(equipment_labels))
    
    if not equipment_label_set:
        return 0.0
    
    query_set = set(query_labels)
    intersection = query_set & equipment_label_set
    
    union = query_set | equipment_label_set
    if not union:
        return 0.0
    
    similarity = len(intersection) / len(union)
    return similarity


def match_equipment(
    query_labels: List[str],
    top_k: int = 10
) -> List[Dict]:
    """Match the most suitable equipment based on query labels"""
    global equipment_df
    
    if equipment_df is None or equipment_df.empty:
        raise HTTPException(status_code=500, detail="Equipment data not loaded")
    
    results = []
    for idx, row in equipment_df.iterrows():
        equipment_id = row.get('equipment_id', '')
        equipment_name = row.get('equipment_name', '')
        all_labels = row.get('all_labels', '')
        
        similarity = calculate_label_similarity(query_labels, all_labels)
        
        results.append({
            'equipment_id': str(equipment_id),
            'equipment_name': str(equipment_name),
            'similarity': similarity,
            'matched_labels': list(set(query_labels) & parse_label_string(str(all_labels)))
        })
    
    results.sort(key=lambda x: x['similarity'], reverse=True)
    top_results = results[:top_k]
    
    return top_results


def build_tags_cache(df: pd.DataFrame) -> Set[str]:
    """Extract all tags from CSV and build cache"""
    tags = set()
    
    # Extract from all_labels column
    if 'all_labels' in df.columns:
        for idx, row in df.iterrows():
            all_labels_str = row.get('all_labels', '')
            if all_labels_str and pd.notna(all_labels_str):
                labels = parse_label_string(str(all_labels_str))
                tags.update(labels)
    
    # Extract from custom_tags column
    if 'custom_tags' in df.columns:
        for idx, row in df.iterrows():
            custom_tags_str = row.get('custom_tags', '')
            if custom_tags_str and pd.notna(custom_tags_str):
                labels = parse_label_string(str(custom_tags_str))
                tags.update(labels)
    
    return tags


def load_gear_model_info(csv_path: str = None):
    """Load gear model info CSV file"""
    global gear_model_data, model_groups
    
    if csv_path is None:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        csv_path = str(PROJECT_ROOT / "csv" / "gear_model_info.csv")
    
    if not os.path.exists(csv_path):
        gear_model_data = {}
        model_groups = defaultdict(list)
        return
    
    gear_model_data = {}
    model_groups = defaultdict(list)
    
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                item_id = row.get('物品ID', '')
                item_name = row.get('物品名称', '').strip('"')
                model_path = row.get('模型路径', '')
                
                if not item_id or not item_name or not model_path:
                    continue
                
                gear_model_data[item_id] = {
                    'id': item_id,
                    'name': item_name,
                    'model_path': model_path
                }
                
                model_groups[model_path].append(item_id)
    except Exception as e:
        print(f"Warning: Failed to load gear model info: {e}")
        gear_model_data = {}
        model_groups = defaultdict(list)


def get_same_model_gears(equipment_id: str) -> List[Dict[str, str]]:
    """Get same model gears by equipment ID"""
    global gear_model_data, model_groups
    
    if not gear_model_data or not model_groups:
        return []
    
    gear_info = gear_model_data.get(str(equipment_id))
    if not gear_info:
        return []
    
    model_path = gear_info.get('model_path')
    if not model_path:
        return []
    
    same_model_gear_ids = model_groups.get(model_path, [])
    
    same_model_gears = []
    for gid in same_model_gear_ids:
        if gid != str(equipment_id):
            gear_info_item = gear_model_data.get(gid)
            if gear_info_item:
                same_model_gears.append({
                    'id': gear_info_item['id'],
                    'name': gear_info_item['name']
                })
    
    return same_model_gears


@app.on_event("startup")
async def startup_event():
    """Load data when application starts"""
    global equipment_df, all_tags_cache
    
    csv_path = os.getenv("CSV_PATH")
    if not csv_path:
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        csv_path = str(PROJECT_ROOT / "csv" / "equipment_labels_epoch_1.csv")
        print(f"CSV_PATH not specified in .env, using default: {csv_path}")
    
    try:
        equipment_df = load_equipment_data(csv_path)
        all_tags_cache = build_tags_cache(equipment_df)
        print(f"Application started successfully, loaded {len(equipment_df)} equipment records")
        print(f"Loaded {len(all_tags_cache)} unique tags from CSV")
    except FileNotFoundError as e:
        print(f"Warning: {e}")
        equipment_df = pd.DataFrame()
        all_tags_cache = set()
    
    load_gear_model_info()
    if gear_model_data:
        print(f"Loaded {len(gear_model_data)} gear model records")


@app.get("/tags")
async def get_all_tags():
    """Get all available tags for autocomplete and search filtering"""
    global all_tags_cache
    
    if not all_tags_cache:
        raise HTTPException(status_code=500, detail="Tags cache not loaded")
    
    all_tags = sorted(list(all_tags_cache))
    
    return JSONResponse({
        "tags": all_tags,
        "count": len(all_tags)
    })


@app.get("/equipment/{equipment_id}")
async def get_equipment_by_id(equipment_id: str):
    """Get equipment details by ID"""
    global equipment_df
    
    if equipment_df is None or equipment_df.empty:
        raise HTTPException(status_code=500, detail="Equipment data not loaded")
    
    # Find equipment by ID
    matching_rows = equipment_df[equipment_df['equipment_id'].astype(str) == str(equipment_id)]
    
    if matching_rows.empty:
        raise HTTPException(status_code=404, detail=f"Equipment with ID {equipment_id} not found")
    
    row = matching_rows.iloc[0]
    
    # Parse all label columns
    equipment_id_str = str(row.get('equipment_id', ''))
    same_model_gears = get_same_model_gears(equipment_id_str)
    
    result = {
        'equipment_id': equipment_id_str,
        'equipment_name': str(row.get('equipment_name', '')),
        'colors': list(parse_label_string(str(row.get('colors', '')))),
        'materials': list(parse_label_string(str(row.get('materials', '')))),
        'shapes': list(parse_label_string(str(row.get('shapes', '')))),
        'decorations': list(parse_label_string(str(row.get('decorations', '')))),
        'styles': list(parse_label_string(str(row.get('styles', '')))),
        'effects': list(parse_label_string(str(row.get('effects', '')))),
        'custom_tags': list(parse_label_string(str(row.get('custom_tags', '')))),
        'appearance_looks_like': list(parse_label_string(str(row.get('appearance_looks_like', '')))),
        'appearance_description': str(row.get('appearance_description', '')) if pd.notna(row.get('appearance_description')) else '',
        'same_model_gears': same_model_gears
    }
    
    # Add optional fields if they exist
    if 'front_image' in row:
        result['front_image'] = str(row.get('front_image', '')) if pd.notna(row.get('front_image')) else ''
    if 'back_image' in row:
        result['back_image'] = str(row.get('back_image', '')) if pd.notna(row.get('back_image')) else ''
    
    return JSONResponse(result)


@app.get("/search")
async def search_equipment(
    tags: List[str] = Query(..., description="Array of tags to search for"),
    top_k: int = Query(10, ge=1, le=100, description="Maximum number of results to return")
):
    """Search equipment by tags in all_labels, appearance_description, and equipment_name"""
    global equipment_df
    
    if equipment_df is None or equipment_df.empty:
        raise HTTPException(status_code=500, detail="Equipment data not loaded")
    
    # Filter out empty tags and strip whitespace
    search_tags = {tag.strip() for tag in tags if tag and tag.strip()}
    if not search_tags:
        raise HTTPException(status_code=400, detail="No valid tags provided")
    
    results = []
    
    for idx, row in equipment_df.iterrows():
        equipment_id = row.get('equipment_id', '')
        equipment_name = row.get('equipment_name', '')
        all_labels = row.get('all_labels', '')
        appearance_description = row.get('appearance_description', '')
        custom_tags = row.get('custom_tags', '')
        
        # Search in all_labels
        equipment_labels = parse_label_string(str(all_labels)) if all_labels and pd.notna(all_labels) else set()
        
        # Search in custom_tags
        custom_tags_set = parse_label_string(str(custom_tags)) if custom_tags and pd.notna(custom_tags) else set()
        
        # Search in appearance_description (case-insensitive)
        description_text = str(appearance_description).lower() if appearance_description and pd.notna(appearance_description) else ""
        
        # Search in equipment_name (case-insensitive)
        name_text = str(equipment_name).lower() if equipment_name and pd.notna(equipment_name) else ""
        
        # Search in all_labels
        matched_labels = search_tags & equipment_labels
        
        # Search in custom_tags
        matched_custom_tags = search_tags & custom_tags_set
        
        # Check if any tag appears in description
        description_matches = []
        for tag in search_tags:
            if tag.lower() in description_text:
                description_matches.append(tag)
        
        # Check if any tag appears in equipment name
        name_matches = []
        for tag in search_tags:
            if tag.lower() in name_text:
                name_matches.append(tag)
        
        # Check if all tags are matched (in labels, custom_tags, description, or name)
        all_matched_tags = matched_labels | matched_custom_tags | set(description_matches) | set(name_matches)
        all_tags_matched = len(all_matched_tags) == len(search_tags)
        
        # Only include if all tags are matched
        if all_tags_matched:
            match_score = len(all_matched_tags) / len(search_tags) if search_tags else 0
            same_model_gears = get_same_model_gears(str(equipment_id))
            results.append({
                'equipment_id': str(equipment_id),
                'equipment_name': str(equipment_name),
                'all_labels': str(all_labels) if all_labels and pd.notna(all_labels) else '',
                'appearance_description': str(appearance_description) if appearance_description and pd.notna(appearance_description) else '',
                'match_score': match_score,
                'matched_labels': list(matched_labels),
                'matched_custom_tags': list(matched_custom_tags),
                'description_matches': description_matches,
                'name_matches': name_matches,
                'same_model_gears': same_model_gears
            })
    
    # Sort by match score (descending)
    results.sort(key=lambda x: x['match_score'], reverse=True)
    top_results = results[:top_k]
    
    return JSONResponse({
        "query_tags": list(search_tags),
        "total_matches": len(results),
        "results": top_results
    })


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9000"))
    
    uvicorn.run(
        "lexicon.app:app",
        host=host,
        port=port,
        reload=True
    )
