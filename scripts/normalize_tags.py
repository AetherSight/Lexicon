#!/usr/bin/env python3
import csv
import pandas as pd
from pathlib import Path

csv_path = "csv/equipment_labels_epoch_1.csv"
output_path = csv_path.replace(".csv", "_new.csv")

df = pd.read_csv(csv_path, encoding='utf-8-sig')

tag_columns = ['colors', 'materials', 'shapes', 'decorations', 'styles', 'effects', 'custom_tags', 'all_labels']

def filter_tags(tag_str):
    if pd.isna(tag_str) or not str(tag_str).strip():
        return ''
    tags = [t.strip() for t in str(tag_str).replace('，', ',').split(',')]
    filtered = [t for t in tags if t and len(t) > 1]
    return ', '.join(filtered)

for col in tag_columns:
    if col in df.columns:
        df[col] = df[col].apply(filter_tags)

df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"Saved to {output_path}")
