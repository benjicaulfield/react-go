import json
import sys
from pathlib import Path

def merge_files(paths, output_path="merged_files.json"):
    merged = []
    for file in paths:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            merged.extend(data)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

paths = [
    'annotations.json',
    'annotations (1).json',
    'annotations (2).json',
    'annotations (3).json',
]

if __name__ == "__main__":
    merge_files(paths)
    