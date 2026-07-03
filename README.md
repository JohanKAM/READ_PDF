# READ_PDF

Python projekt pro čtení a extrakci dat z PDF faktur.  
Python project for reading and extracting data from PDF invoices.

---

## Požadavky / Requirements

- Python 3.10+
- [pdfplumber](https://github.com/jsvine/pdfplumber)

```bash
pip install -r requirements.txt
```

---

## Použití / Usage

```bash
python read_pdf.py <cesta_k_faktuře.pdf>
```

Volitelně uložit výsledek jako JSON:

```bash
python read_pdf.py faktura.pdf --output vysledek.json
```

### Příklad výstupu / Example output

```
============================================================
  Soubor / File : faktura.pdf
  Stránek / Pages: 1
============================================================

  Extrahovaná pole / Extracted Fields:
  --------------------------------------------------------
  Číslo faktury     / Invoice No.: 2024/001
  Datum vystavení   / Issue Date: 01.06.2024
  Datum splatnosti  / Due Date: 15.06.2024
  Dodavatel         / Supplier: ACME s.r.o.
  Odběratel         / Customer: Zákazník a.s.
  IČ / Reg. No.: 12345678
  DIČ / VAT ID: CZ12345678
  Číslo účtu        / Bank Account: 1234567890/0100
  Variabilní symbol / Var. Symbol: 20240001
  Bez DPH           / Excl. VAT: 15 200
  DPH               / VAT: 3 192
  K úhradě          / Total Due: 18 392

============================================================
```

---

## Extrahovaná pole / Extracted Fields

| Pole / Field | Popis / Description |
|---|---|
| `invoice_number` | Číslo faktury / Invoice number |
| `date_issued` | Datum vystavení / Issue date |
| `due_date` | Datum splatnosti / Due date |
| `supplier` | Dodavatel / Supplier name |
| `customer` | Odběratel / Customer name |
| `ic` | IČ / Company registration number |
| `dic` | DIČ / VAT identification number |
| `bank_account` | Číslo bankovního účtu / Bank account number |
| `variable_symbol` | Variabilní symbol / Variable payment symbol |
| `currency` | Měna / Currency |
| `total_without_vat` | Celkem bez DPH / Subtotal excl. VAT |
| `vat_amount` | Výše DPH / VAT amount |
| `total_with_vat` | Celkem s DPH / Total incl. VAT |

---

## Testy / Tests

```bash
python -m pytest tests/
```

---

## Struktura projektu / Project Structure

```
READ_PDF/
├── read_pdf.py        # Hlavní skript / Main script
├── requirements.txt   # Závislosti / Dependencies
├── tests/
│   └── test_read_pdf.py
└── README.md
```
