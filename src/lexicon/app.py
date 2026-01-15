"""
FastAPI Application: Equipment Search Service
Provides API endpoints to search equipment by tags
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Set
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
    result = {
        'equipment_id': str(row.get('equipment_id', '')),
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
        
        # Search in all_labels
        equipment_labels = parse_label_string(str(all_labels)) if all_labels and pd.notna(all_labels) else set()
        
        # Search in appearance_description (case-insensitive)
        description_text = str(appearance_description).lower() if appearance_description and pd.notna(appearance_description) else ""
        
        # Search in equipment_name (case-insensitive)
        name_text = str(equipment_name).lower() if equipment_name and pd.notna(equipment_name) else ""
        
        # Search in all_labels
        matched_labels = search_tags & equipment_labels
        
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
        
        # Check if all tags are matched (in labels, description, or name)
        all_matched_tags = matched_labels | set(description_matches) | set(name_matches)
        all_tags_matched = len(all_matched_tags) == len(search_tags)
        
        # Only include if all tags are matched
        if all_tags_matched:
            match_score = len(all_matched_tags) / len(search_tags) if search_tags else 0
            results.append({
                'equipment_id': str(equipment_id),
                'equipment_name': str(equipment_name),
                'all_labels': str(all_labels) if all_labels and pd.notna(all_labels) else '',
                'appearance_description': str(appearance_description) if appearance_description and pd.notna(appearance_description) else '',
                'match_score': match_score,
                'matched_labels': list(matched_labels),
                'description_matches': description_matches,
                'name_matches': name_matches
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
