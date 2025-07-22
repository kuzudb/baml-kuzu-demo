import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple


def load_json_file(file_path: str) -> List[dict]:
    """Load JSON data from a file."""
    with open(file_path, "r") as f:
        return json.load(f)


def extract_all_strings(data: List[dict]) -> Set[str]:
    """Extract all string values from nested JSON structure."""
    all_strings = set()

    for item in data:
        # Add condition
        all_strings.add(item["condition"])
        
        # Add drug names (generic and brand)
        for drug in item["drug"]:
            all_strings.add(drug["generic_name"])
            all_strings.update(brand for brand in drug["brand_names"] if brand)
        
        # Add side effects
        all_strings.update(effect for effect in item["side_effects"] if effect)

    return all_strings


def extract_mappings(human_data: List[dict], extracted_data: List[dict]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """
    Extract mappings between corresponding elements in human and extracted data.
    Returns a dictionary of mappings and a list of mismatches.
    """
    mappings = {}
    mismatches = []
    
    # Create dictionaries to map conditions to their data
    human_conditions = {item["condition"]: item for item in human_data}
    extracted_conditions = {item["condition"]: item for item in extracted_data}
    
    # Find common conditions to compare
    common_conditions = set(human_conditions.keys()) & set(extracted_conditions.keys())
    
    for condition in common_conditions:
        human_item = human_conditions[condition]
        extracted_item = extracted_conditions[condition]
        
        # Compare drug generic names
        human_drugs = {drug["generic_name"]: drug for drug in human_item["drug"]}
        extracted_drugs = {drug["generic_name"]: drug for drug in extracted_item["drug"]}
        
        common_drugs = set(human_drugs.keys()) & set(extracted_drugs.keys())
        
        for drug_name in common_drugs:
            human_drug = human_drugs[drug_name]
            extracted_drug = extracted_drugs[drug_name]
            
            # Compare brand names
            human_brands = set(human_drug["brand_names"])
            extracted_brands = set(extracted_drug["brand_names"])
            
            # Add exact matches to mappings
            for brand in human_brands & extracted_brands:
                if brand:  # Skip empty strings
                    mappings[brand] = brand
            
            # Find mismatches (brands that exist in both but are different)
            # This is a simplification - in reality, determining mismatches would require more context
            # For now, we'll just note that this is a placeholder for the mismatch logic
            
            # Example placeholder for mismatch detection:
            if len(human_brands) == len(extracted_brands) and human_brands != extracted_brands:
                for h_brand, e_brand in zip(sorted(human_brands), sorted(extracted_brands)):
                    if h_brand != e_brand and h_brand and e_brand:
                        mismatches.append((h_brand, e_brand))
        
        # Compare side effects
        human_effects = set(human_item["side_effects"])
        extracted_effects = set(extracted_item["side_effects"])
        
        # Add exact matches to mappings
        for effect in human_effects & extracted_effects:
            if effect:  # Skip empty strings
                mappings[effect] = effect
        
        # Find potential mismatches in side effects
        # Again, this is a simplification
        if len(human_effects) == len(extracted_effects) and human_effects != extracted_effects:
            for h_effect, e_effect in zip(sorted(human_effects), sorted(extracted_effects)):
                if h_effect != e_effect and h_effect and e_effect:
                    mismatches.append((h_effect, e_effect))
    
    return mappings, mismatches


def evaluate_extraction(human_path: str, extracted_path: str) -> Dict[str, Any]:
    """Compare human annotated data with extracted data and return metrics."""
    human_data = load_json_file(human_path)
    extracted_data = load_json_file(extracted_path)

    exact_matches = set()
    missing_items = set()
    hallucinations = set()
    mismatches = []
    
    # Helper function to process items with the same structure
    def compare_items(human_items, extracted_items, find_similar=False):
        for h_item in human_items:
            if not h_item:  # Skip empty strings
                continue
                
            if h_item in extracted_items:
                exact_matches.add(h_item)
            elif find_similar:
                # Look for similar but not identical items
                similar = [e for e in extracted_items if e and e != h_item]
                if similar:
                    mismatches.append((h_item, similar[0]))
                else:
                    missing_items.add(h_item)
            else:
                missing_items.add(h_item)
                
        for e_item in extracted_items:
            if not e_item:  # Skip empty strings
                continue
                
            if e_item not in human_items and e_item not in [m[1] for m in mismatches]:
                hallucinations.add(e_item)

    # Process conditions
    human_conditions = {item["condition"] for item in human_data}
    extracted_conditions = {item["condition"] for item in extracted_data}
    compare_items(human_conditions, extracted_conditions)
    
    # Create lookup maps
    human_map = {item["condition"]: item for item in human_data}
    extracted_map = {item["condition"]: item for item in extracted_data}
    
    # Process matching conditions
    for condition in human_conditions & extracted_conditions:
        human_item = human_map[condition]
        extracted_item = extracted_map[condition]
        
        # Process drug generic names
        human_drugs = {drug["generic_name"] for drug in human_item["drug"]}
        extracted_drugs = {drug["generic_name"] for drug in extracted_item["drug"]}
        compare_items(human_drugs, extracted_drugs)
        
        # Process brand names for matching drugs
        h_drug_map = {drug["generic_name"]: drug for drug in human_item["drug"]}
        e_drug_map = {drug["generic_name"]: drug for drug in extracted_item["drug"]}
        
        for drug in human_drugs & extracted_drugs:
            human_brands = set(h_drug_map[drug]["brand_names"])
            extracted_brands = set(e_drug_map[drug]["brand_names"])
            compare_items(human_brands, extracted_brands, find_similar=True)
        
        # Process side effects
        human_effects = set(human_item["side_effects"])
        extracted_effects = set(extracted_item["side_effects"])
        compare_items(human_effects, extracted_effects, find_similar=True)

    metrics = {
        "exact_match": len(exact_matches),
        "missing": len(missing_items),
        "potential_hallucination": len(hallucinations),
        "mismatch": len(mismatches),
        "hallucination_items": hallucinations,
        "missing_item_details": missing_items,
        "exact_match_items": exact_matches,
        "mismatch_pairs": mismatches
    }

    return metrics


def run_evaluation(
    human_dir: Path = Path("data/human_annotated_data"),
    extracted_dir: Path = Path("data/extracted_data"),
) -> Dict[str, Dict[str, Any]]:
    """Run evaluation on all matching files in human_annotated_data and extracted_data."""
    results = {}

    # Find all JSON files with the prefix "drugs" in human_annotated_data
    for human_file in human_dir.glob("drugs_and_side_effects*.json"):
        filename = human_file.name
        
        # Map human annotated filename to extracted filename
        if filename.endswith("_human_annotated.json"):
            extracted_filename = filename.replace("_human_annotated.json", ".json")
        else:
            extracted_filename = filename
            
        extracted_file = extracted_dir / extracted_filename

        # Check if corresponding file exists in extracted_data
        if extracted_file.exists():
            results[filename] = evaluate_extraction(str(human_file), str(extracted_file))

    return results


def inspect_hallucinations(results: Dict[str, Dict[str, Any]]) -> None:
    """Display detailed information about potential hallucinations."""
    print("\nPotential hallucination details:")
    print("================================")
    
    for filename, metrics in results.items():
        if "hallucination_items" in metrics and metrics["hallucination_items"]:
            print(f"\nFile: {filename}")
            print("  Potentially hallucinated items in extracted data (please verify):")
            for item in sorted(metrics["hallucination_items"]):
                print(f"    <Missing> (human annotated) --- '{item}' (extracted)")
        else:
            print(f"\nFile: {filename}")
            print("  No potential hallucinations detected.")


def inspect_missing_items(results: Dict[str, Dict[str, Any]]) -> None:
    """Display detailed information about missing items."""
    print("\nMissing items details:")
    print("=====================")
    
    for filename, metrics in results.items():
        if "missing_item_details" in metrics and metrics["missing_item_details"]:
            print(f"\nFile: {filename}")
            print("  Items missing from extracted data:")
            for item in sorted(metrics["missing_item_details"]):
                print(f"    '{item}' (human annotated) --- <Missing> (extracted)")
        else:
            print(f"\nFile: {filename}")
            print("  No missing items detected.")


def inspect_mismatches(results: Dict[str, Dict[str, Any]]) -> None:
    """Display detailed information about mismatched items."""
    print("\nMismatch details:")
    print("================")
    
    for filename, metrics in results.items():
        if "mismatch_pairs" in metrics and metrics["mismatch_pairs"]:
            print(f"\nFile: {filename}")
            print("  Mismatched items (different values for corresponding elements):")
            for human_item, extracted_item in metrics["mismatch_pairs"]:
                print(f"    '{human_item}' (human annotated) --- '{extracted_item}' (extracted)")
        else:
            print(f"\nFile: {filename}")
            print("  No mismatches detected.")


def main() -> Dict[str, Dict[str, Any]]:
    """Main function to run evaluation and print results."""
    results = run_evaluation()

    # Print results
    print("Evaluation results:")
    print("===================")

    if not results:
        print("No files found to evaluate. Check that the data directories exist and contain matching files.")
        return results

    for filename, metrics in results.items():
        total = metrics["exact_match"] + metrics["missing"] + metrics["potential_hallucination"] + metrics["mismatch"]
        print(f"\nFile: {filename}")
        print(f"  Exact matches: {metrics['exact_match']} ({metrics['exact_match']/total:.1%})")
        print(f"  Missing items: {metrics['missing']} ({metrics['missing']/total:.1%})")
        print(f"  Potential hallucinations: {metrics['potential_hallucination']} ({metrics['potential_hallucination']/total:.1%})")
        print(f"  Mismatches: {metrics['mismatch']} ({metrics['mismatch']/total:.1%})")

    # Calculate totals - only include count metrics, not the set objects
    totals = defaultdict(int)
    count_metrics = ["exact_match", "missing", "potential_hallucination", "mismatch"]
    for metrics in results.values():
        for metric in count_metrics:
            totals[metric] += metrics[metric]
    
    grand_total = sum(totals[metric] for metric in count_metrics)
    
    if grand_total == 0:
        print("\nNo data found to evaluate.")
        return results
    
    print("\nTotals across all files:")
    print(f"  Total exact matches: {totals['exact_match']} ({totals['exact_match']/grand_total:.1%})")
    print(f"  Total missing items: {totals['missing']} ({totals['missing']/grand_total:.1%})")
    print(f"  Total potential hallucinations: {totals['potential_hallucination']} ({totals['potential_hallucination']/grand_total:.1%})")
    print(f"  Total mismatches: {totals['mismatch']} ({totals['mismatch']/grand_total:.1%})")

    # Call inspect functions within main
    inspect_hallucinations(results)
    inspect_missing_items(results)
    inspect_mismatches(results)
    
    return results


if __name__ == "__main__":
    main()
