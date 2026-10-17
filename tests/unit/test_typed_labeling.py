"""Typed entity labeling for CSV/XLSX tables (companies must not become PERSON)."""

import io

from app.detection.hint_merge import merge_hints
from app.detection.presidio_engine import FallbackPIIDetector
from app.ingestion.csv_converter import CSVToOKFConverter
from app.ingestion.table_parser import PLAIN, infer_column_type
from app.tokenization.tokenizer import DeterministicTokenizer

COMPANY_CSV = (
    "Name of company,Rating,Website,Category\n"
    "Devsync IT Solutions,5.0,https://maps.app.goo.gl/y5uFcU,Computer support\n"
    "Acme Labs,4.9,https://maps.app.goo.gl/abc123,Software company\n"
).encode()

EMPLOYEE_CSV = (
    "Employee,Salary,Email\n"
    "Harold Mbeki,\"$85,000\",h@x.com\n"
    "Jane Doe,\"$90,000\",jane@x.com\n"
).encode()


def _tokenize_doc(doc):
    detector = FallbackPIIDetector()
    tokenizer = DeterministicTokenizer(secret_key=b"test-key")
    cats = ["PERSON", "EMAIL_ADDRESS", "SALARY", "LOCATION", "ORGANIZATION", "PHONE_NUMBER"]
    out = []
    for i, s in enumerate(doc.sentences):
        ents = detector.detect(s, entity_categories=cats, min_confidence=0.85)
        ents = merge_hints(s, ents, doc.sentence_hints[i], allowed_types=cats)
        out.append(tokenizer.tokenize_text(s, ents)[0])
    return out


def test_column_inference():
    assert infer_column_type("Name of company", ["Devsync IT Solutions"]) == "ORGANIZATION"
    assert infer_column_type("Rating", ["5.0", "4.9"]) == PLAIN
    assert infer_column_type("col3", ["https://a.com/x", "https://b.com/y"]) == PLAIN
    assert infer_column_type("Email", ["a@b.com"]) == "EMAIL_ADDRESS"
    assert infer_column_type("Name", ["Harold Mbeki", "Jane Doe"]) == "PERSON"
    assert infer_column_type("Notes", ["something odd"]) is None


def test_company_csv_has_no_person_tokens():
    doc = CSVToOKFConverter().convert(COMPANY_CSV, "companies.csv")
    joined = "\n".join(_tokenize_doc(doc))
    assert "_PERSON_" not in joined
    assert "_ORGANIZATION_" in joined
    assert "Devsync" not in joined
    # Non-sensitive attributes stay readable
    assert "5.0" in joined and "Computer support" in joined


def test_employee_csv_still_person():
    doc = CSVToOKFConverter().convert(EMPLOYEE_CSV, "employees.csv")
    joined = "\n".join(_tokenize_doc(doc))
    assert "_PERSON_" in joined
    assert "Harold" not in joined
    assert "_SALARY_" in joined
    assert "_EMAIL_ADDRESS_" in joined


def test_xlsx_company_sheet():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Name of company", "Rating", "Category"])
    ws.append(["Devsync IT Solutions", 5.0, "Computer support"])
    buf = io.BytesIO()
    wb.save(buf)
    doc = CSVToOKFConverter().convert(buf.getvalue(), "companies.xlsx")
    joined = "\n".join(_tokenize_doc(doc))
    assert "_ORGANIZATION_" in joined and "_PERSON_" not in joined


def test_same_company_same_token_across_documents():
    a = _tokenize_doc(CSVToOKFConverter().convert(COMPANY_CSV, "a.csv"))
    b = _tokenize_doc(CSVToOKFConverter().convert(COMPANY_CSV, "b.csv"))
    assert a == b


def test_free_text_company_not_person():
    ents = FallbackPIIDetector().detect(
        "We signed with Devsync IT Solutions.",
        entity_categories=["PERSON", "ORGANIZATION"],
    )
    assert all(e.entity_type != "PERSON" for e in ents)
    assert any(e.entity_type == "ORGANIZATION" for e in ents)
