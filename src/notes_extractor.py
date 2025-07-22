import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Import directly from src package
from baml_client import b, types

load_dotenv()
os.environ["BAML_LOG"] = "WARN"


def extract_notes(notes: str) -> list[types.PatientInfo]:
    return b.ExtractMedicationInfo(notes)


if __name__ == "__main__":
    notes = Path("../data/text/notes_1.txt").read_text()
    # Model dump the result into a json file
    result = extract_notes(notes)
    output_path = Path("../data/extracted_data")
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "notes.json", "w") as f:
        json.dump([item.model_dump() for item in result], f, indent=4)
