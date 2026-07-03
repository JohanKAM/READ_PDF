"""
read_pdf.py – Čtení a extrakce dat z PDF faktur.
Read and extract data from PDF invoices.

Usage:
    python read_pdf.py invoice.pdf
    python read_pdf.py invoice.pdf --output result.json
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    print("Chyba: knihovna pdfplumber není nainstalována.", file=sys.stderr)
    print("Spusťte: pip install pdfplumber", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Regex patterns for common invoice fields (Czech + international formats)
# ---------------------------------------------------------------------------

PATTERNS = {
    "invoice_number": re.compile(
        r"(?:faktura|invoice|fa[ck]tura|číslo faktury|invoice\s*no\.?|inv\.?\s*no\.?)[:\s#]*([A-Z0-9/_\-]+)",
        re.IGNORECASE,
    ),
    "date_issued": re.compile(
        r"(?:datum\s+vystavení|datum\s+vystavení|date\s+issued?|issue\s+date|datum)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        re.IGNORECASE,
    ),
    "due_date": re.compile(
        r"(?:datum\s+splatnosti|due\s+date|splatnost|pay(?:ment)?\s+due)[:\s]+(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})",
        re.IGNORECASE,
    ),
    "supplier": re.compile(
        r"(?:dodavatel|supplier|vendor|from|od)[:\s]+(.+)",
        re.IGNORECASE,
    ),
    "customer": re.compile(
        r"(?:odběratel|zákazník|customer|buyer|bill\s+to|to)[:\s]+(.+)",
        re.IGNORECASE,
    ),
    "ic": re.compile(
        r"(?:IČ|IČO|ico|reg\.?\s*no\.?)[:\s]+(\d{6,10})",
        re.IGNORECASE,
    ),
    "dic": re.compile(
        r"(?:DIČ|dic|VAT\s*ID|VAT\s*no\.?)[:\s]+(CZ\d{8,10}|\w{2}\d{8,12})",
        re.IGNORECASE,
    ),
    "total_with_vat": re.compile(
        r"(?:celkem\s+s\s+DPH|total\s+(?:incl\.?\s+VAT|with\s+VAT)|k\s+úhradě|amount\s+due)[:\s]*([\d\s.,]+)\s*(?:Kč|CZK|EUR|USD|€|\$)?",
        re.IGNORECASE,
    ),
    "total_without_vat": re.compile(
        r"(?:celkem\s+bez\s+DPH|subtotal|total\s+excl\.?\s+VAT)[:\s]*([\d\s.,]+)\s*(?:Kč|CZK|EUR|USD|€|\$)?",
        re.IGNORECASE,
    ),
    "vat_amount": re.compile(
        r"(?m)^\s*(?:DPH|VAT)(?!\s*ID)(?:\s+\d{1,2}\s*%)?[:\s]+([\d\s.,]+)\s*(?:Kč|CZK|EUR|USD|€|\$)?",
        re.IGNORECASE,
    ),
    "currency": re.compile(
        r"\b(Kč|CZK|EUR|USD|GBP|€|\$)\b",
        re.IGNORECASE,
    ),
    "bank_account": re.compile(
        r"(?:číslo\s+účtu|bank\s+account|IBAN|účet)[:\s]+([A-Z]{0,2}\d[\d\s\-/]{6,30})",
        re.IGNORECASE,
    ),
    "variable_symbol": re.compile(
        r"(?:variabilní\s+symbol|var\.?\s+sym\.?|variable\s+symbol)[:\s]+(\d+)",
        re.IGNORECASE,
    ),
}


def extract_text_from_pdf(pdf_path: str) -> tuple[str, list[dict]]:
    """
    Extract full text and per-page data (including tables) from a PDF file.

    Returns:
        full_text: concatenated text from all pages
        pages: list of dicts with 'page', 'text', and 'tables' keys
    """
    pages = []
    full_text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            tables = page.extract_tables() or []
            pages.append({"page": i, "text": page_text, "tables": tables})
            full_text_parts.append(page_text)

    return "\n".join(full_text_parts), pages


def _first_match(pattern: re.Pattern, text: str) -> Optional[str]:
    """Return the first captured group of the first regex match, stripped."""
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return None


def extract_invoice_fields(text: str) -> dict:
    """
    Parse common invoice fields from raw text using regex patterns.

    Returns a dict with extracted fields (None when not found).
    """
    fields = {}
    for field_name, pattern in PATTERNS.items():
        fields[field_name] = _first_match(pattern, text)
    return fields


def parse_tables(pages: list[dict]) -> list[list[list]]:
    """Collect all tables from all pages."""
    all_tables = []
    for page in pages:
        for table in page.get("tables", []):
            if table:
                all_tables.append(table)
    return all_tables


def format_result(pdf_path: str, fields: dict, tables: list, pages: list) -> dict:
    """Build the structured result dictionary."""
    return {
        "source_file": str(pdf_path),
        "pages": len(pages),
        "fields": fields,
        "tables": tables,
    }


def print_result(result: dict) -> None:
    """Print result in a human-readable format."""
    print(f"\n{'='*60}")
    print(f"  Soubor / File : {result['source_file']}")
    print(f"  Stránek / Pages: {result['pages']}")
    print(f"{'='*60}")

    fields = result["fields"]
    field_labels = {
        "invoice_number":     "Číslo faktury     / Invoice No.",
        "date_issued":        "Datum vystavení   / Issue Date",
        "due_date":           "Datum splatnosti  / Due Date",
        "supplier":           "Dodavatel         / Supplier",
        "customer":           "Odběratel         / Customer",
        "ic":                 "IČ / Reg. No.",
        "dic":                "DIČ / VAT ID",
        "bank_account":       "Číslo účtu        / Bank Account",
        "variable_symbol":    "Variabilní symbol / Var. Symbol",
        "currency":           "Měna              / Currency",
        "total_without_vat":  "Bez DPH           / Excl. VAT",
        "vat_amount":         "DPH               / VAT",
        "total_with_vat":     "K úhradě          / Total Due",
    }

    print("\n  Extrahovaná pole / Extracted Fields:")
    print(f"  {'-'*56}")
    for key, label in field_labels.items():
        value = fields.get(key)
        if value:
            print(f"  {label}: {value}")

    tables = result.get("tables", [])
    if tables:
        print(f"\n  Nalezené tabulky / Tables found: {len(tables)}")
        for t_idx, table in enumerate(tables, start=1):
            print(f"\n  Tabulka {t_idx} / Table {t_idx}:")
            for row in table:
                if row:
                    cells = [str(c).strip() if c is not None else "" for c in row]
                    print("    | " + " | ".join(cells) + " |")

    print(f"\n{'='*60}\n")


def process_invoice(pdf_path: str, output_json: Optional[str] = None) -> dict:
    """
    Main processing function: extract and return invoice data from a PDF file.

    Args:
        pdf_path: path to the PDF invoice file
        output_json: optional path to write JSON output

    Returns:
        Structured dict with all extracted data
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Soubor nenalezen / File not found: {pdf_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Soubor musí být PDF / File must be a PDF: {pdf_path}")

    full_text, pages = extract_text_from_pdf(pdf_path)
    fields = extract_invoice_fields(full_text)
    tables = parse_tables(pages)
    result = format_result(pdf_path, fields, tables, pages)

    print_result(result)

    if output_json:
        out_path = Path(output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  JSON uložen do / JSON saved to: {output_json}\n")

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Čtení a extrakce dat z PDF faktur / Read and extract data from PDF invoices."
    )
    parser.add_argument("pdf_file", help="Cesta k PDF souboru / Path to PDF file")
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Uložit výsledek jako JSON / Save result as JSON",
    )
    args = parser.parse_args()

    try:
        process_invoice(args.pdf_file, args.output)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Chyba / Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
