import json
import os
from pathlib import Path

# Updated imports using the src package
from baml_py import Pdf
from dotenv import load_dotenv

from baml_client import b, types

load_dotenv()
os.environ["BAML_LOG"] = "WARN"


def extract_from_base64(
    base64_str: str, mime_type: str = "application/pdf"
) -> list[types.ConditionAndDrug]:
    """Extract entities from a base64-encoded PDF"""
    baml_pdf = Pdf.from_base64(mime_type, base64_str)
    result = b.ExtractFromPdf(baml_pdf)
    return result


def extract_from_pdf(file_path: Path) -> list[types.ConditionAndDrug]:
    """Extract entities from a PDF file"""
    with open(file_path, "rb") as f:
        pdf_bytes = f.read()
    import base64

    base64_str = base64.b64encode(pdf_bytes).decode()
    # Determine mime type based on file extension or use default
    import mimetypes

    mime_type = mimetypes.guess_type(file_path)[0] or "application/pdf"
    baml_pdf = Pdf.from_base64(mime_type, base64_str)
    result = b.ExtractFromPdf(baml_pdf)
    return result


def extract_from_bytes(
    pdf_bytes: bytes, mime_type: str = "application/pdf"
) -> list[types.ConditionAndDrug]:
    """Extract entities from a bytes object"""
    import base64

    base64_str = base64.b64encode(pdf_bytes).decode()
    baml_pdf = Pdf.from_base64(mime_type, base64_str)
    result = b.ExtractFromPdf(baml_pdf)
    return result


if __name__ == "__main__":
    input_dir = Path("../data/pdf")
    output_dir = Path("../data/extracted_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = list(input_dir.glob("*.pdf"))
    for file in files:
        # We are working with PDF files, so we can pass in the file path directly
        result = extract_from_pdf(file)
        output_path = output_dir / file.with_suffix(".json").name

        with output_path.open("w") as f:
            json.dump([item.model_dump() for item in result], f, indent=4)

        print(f"Results written to {output_path}")
