"""
Unit tests for read_pdf.py
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure the project root is on the path so read_pdf can be imported directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import read_pdf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_INVOICE_TEXT = """
FAKTURA 2024/001

Dodavatel: ACME s.r.o.
IČ: 12345678
DIČ: CZ12345678

Odběratel: Zákazník a.s.
IČ: 87654321

Datum vystavení: 01.06.2024
Datum splatnosti: 15.06.2024
Variabilní symbol: 20240001

Číslo účtu: 1234567890/0100

Položky:
Konzultace     10 hod   1 500 Kč   15 000 Kč
Cestovné        1 km     200 Kč      200 Kč

Celkem bez DPH: 15 200 Kč
DPH: 3 192 Kč
Celkem s DPH: 18 392 Kč
"""


# ---------------------------------------------------------------------------
# Tests for extract_invoice_fields
# ---------------------------------------------------------------------------

class TestExtractInvoiceFields(unittest.TestCase):

    def setUp(self):
        self.fields = read_pdf.extract_invoice_fields(SAMPLE_INVOICE_TEXT)

    def test_invoice_number(self):
        self.assertEqual(self.fields["invoice_number"], "2024/001")

    def test_date_issued(self):
        self.assertEqual(self.fields["date_issued"], "01.06.2024")

    def test_due_date(self):
        self.assertEqual(self.fields["due_date"], "15.06.2024")

    def test_supplier(self):
        self.assertIn("ACME", self.fields["supplier"])

    def test_customer(self):
        self.assertIn("Zákazník", self.fields["customer"])

    def test_ic(self):
        self.assertEqual(self.fields["ic"], "12345678")

    def test_dic(self):
        self.assertEqual(self.fields["dic"], "CZ12345678")

    def test_variable_symbol(self):
        self.assertEqual(self.fields["variable_symbol"], "20240001")

    def test_bank_account(self):
        self.assertIsNotNone(self.fields["bank_account"])

    def test_total_without_vat(self):
        self.assertIsNotNone(self.fields["total_without_vat"])

    def test_total_with_vat(self):
        self.assertIsNotNone(self.fields["total_with_vat"])

    def test_vat_amount(self):
        self.assertIsNotNone(self.fields["vat_amount"])

    def test_missing_field_returns_none(self):
        fields = read_pdf.extract_invoice_fields("")
        for value in fields.values():
            self.assertIsNone(value)


# ---------------------------------------------------------------------------
# Tests for _first_match
# ---------------------------------------------------------------------------

class TestFirstMatch(unittest.TestCase):

    def test_returns_first_group(self):
        import re
        pattern = re.compile(r"foo:(\w+)")
        result = read_pdf._first_match(pattern, "foo:bar")
        self.assertEqual(result, "bar")

    def test_returns_none_when_no_match(self):
        import re
        pattern = re.compile(r"foo:(\w+)")
        result = read_pdf._first_match(pattern, "nothing here")
        self.assertIsNone(result)

    def test_strips_whitespace(self):
        import re
        pattern = re.compile(r"foo:\s*(\w+)")
        result = read_pdf._first_match(pattern, "foo:   bar")
        self.assertEqual(result, "bar")


# ---------------------------------------------------------------------------
# Tests for parse_tables
# ---------------------------------------------------------------------------

class TestParseTables(unittest.TestCase):

    def test_collects_tables_from_pages(self):
        pages = [
            {"page": 1, "text": "...", "tables": [[["A", "B"], ["1", "2"]]]},
            {"page": 2, "text": "...", "tables": [[["C", "D"]]]},
        ]
        tables = read_pdf.parse_tables(pages)
        self.assertEqual(len(tables), 2)

    def test_empty_tables_skipped(self):
        pages = [{"page": 1, "text": "...", "tables": [[], [["X"]]]}]
        tables = read_pdf.parse_tables(pages)
        self.assertEqual(len(tables), 1)

    def test_no_tables(self):
        pages = [{"page": 1, "text": "...", "tables": []}]
        tables = read_pdf.parse_tables(pages)
        self.assertEqual(tables, [])


# ---------------------------------------------------------------------------
# Tests for format_result
# ---------------------------------------------------------------------------

class TestFormatResult(unittest.TestCase):

    def test_structure(self):
        fields = {"invoice_number": "001"}
        pages = [{"page": 1, "text": "x", "tables": []}]
        tables: list = []
        result = read_pdf.format_result("test.pdf", fields, tables, pages)
        self.assertEqual(result["source_file"], "test.pdf")
        self.assertEqual(result["pages"], 1)
        self.assertEqual(result["fields"]["invoice_number"], "001")
        self.assertEqual(result["tables"], [])


# ---------------------------------------------------------------------------
# Tests for process_invoice (with mocking)
# ---------------------------------------------------------------------------

class TestProcessInvoice(unittest.TestCase):

    def _make_mock_pages(self):
        return [{"page": 1, "text": SAMPLE_INVOICE_TEXT, "tables": []}]

    def test_raises_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            read_pdf.process_invoice("/nonexistent/path/invoice.pdf")

    def test_raises_value_error_for_non_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"not a pdf")
            tmp = f.name
        try:
            with self.assertRaises(ValueError):
                read_pdf.process_invoice(tmp)
        finally:
            os.unlink(tmp)

    @patch("read_pdf.extract_text_from_pdf")
    def test_returns_structured_result(self, mock_extract):
        mock_extract.return_value = (SAMPLE_INVOICE_TEXT, self._make_mock_pages())

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            tmp = f.name
        try:
            result = read_pdf.process_invoice(tmp)
            self.assertIn("fields", result)
            self.assertIn("tables", result)
            self.assertIn("pages", result)
            self.assertIn("source_file", result)
        finally:
            os.unlink(tmp)

    @patch("read_pdf.extract_text_from_pdf")
    def test_json_output(self, mock_extract):
        mock_extract.return_value = (SAMPLE_INVOICE_TEXT, self._make_mock_pages())

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake")
            pdf_tmp = f.name

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            json_tmp = f.name

        try:
            read_pdf.process_invoice(pdf_tmp, output_json=json_tmp)
            with open(json_tmp, encoding="utf-8") as jf:
                data = json.load(jf)
            self.assertIn("fields", data)
        finally:
            os.unlink(pdf_tmp)
            os.unlink(json_tmp)


if __name__ == "__main__":
    unittest.main()
