#!/usr/bin/env python3
"""
Script to merge drugs_1.json and drugs_2.json into a single JSON file.
"""

import json
from pathlib import Path


def merge_drug_files():
    """Merge drugs_1.json and drugs_2.json into a single file."""
    
    # Define paths
    data_dir = Path(".")
    drugs_1_path = data_dir / "drugs_1.json"
    drugs_2_path = data_dir / "drugs_2.json"
    output_path = data_dir / "drugs_and_side_effects_human_annotated.json"
    
    # Check if input files exist
    if not drugs_1_path.exists():
        raise FileNotFoundError(f"File not found: {drugs_1_path}")
    if not drugs_2_path.exists():
        raise FileNotFoundError(f"File not found: {drugs_2_path}")
    
    # Read the first file
    print(f"Reading {drugs_1_path}...")
    with open(drugs_1_path, "r", encoding="utf-8") as f:
        drugs_1_data = json.load(f)
    
    # Read the second file
    print(f"Reading {drugs_2_path}...")
    with open(drugs_2_path, "r", encoding="utf-8") as f:
        drugs_2_data = json.load(f)
    
    # Merge the data
    print("Merging data...")
    merged_data = drugs_1_data + drugs_2_data
    
    # Write the merged data to output file
    print(f"Writing merged data to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=4, ensure_ascii=False)
    
    print(f"Successfully merged {len(drugs_1_data)} + {len(drugs_2_data)} = {len(merged_data)} conditions")
    print(f"Output file: {output_path}")
    
    return output_path


if __name__ == "__main__":
    try:
        output_file = merge_drug_files()
        print("\n✅ Merge completed successfully!")
        print(f"📁 Output file: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)