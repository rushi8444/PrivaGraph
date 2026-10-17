"""Tests for the dataset-agnostic CompositeCellDecomposer."""

from app.ingestion.composite_unpacker import CompositeCellDecomposer


def test_google_maps_composite_cell():
    decomposer = CompositeCellDecomposer()
    text = (
        "Xenmate India Pvt Ltd | Xenmate India Pvt Ltd | 5.0(2) | Software company · "
        "73/9, Purandar Colony Rd | Open · Closes 12 am · 087094 92410 | \ue80b | Website | Directions"
    )
    assert decomposer.is_composite(text)
    facts = decomposer.decompose(text, subject_name="Xenmate India Pvt Ltd")

    preds = {f.predicate: f.value for f in facts}
    assert "HAS_PHONE" in preds
    assert "087094 92410" in preds["HAS_PHONE"]
    assert "HAS_HOURS" in preds
    assert "12 am" in preds["HAS_HOURS"]
    assert "HAS_ADDRESS" in preds
    assert "Purandar Colony" in preds["HAS_ADDRESS"]
    assert "HAS_CATEGORY" in preds
    assert "Software company" in preds["HAS_CATEGORY"]


def test_hr_employee_notes_composite():
    decomposer = CompositeCellDecomposer()
    text = (
        "Role: Staff Engineer; Department: Engineering; "
        "Office: 450 Market St, Suite 200; Base: $145,000; "
        "Emergency Contact: +1 (555) 234-5678; email: engineer@tech.io"
    )
    assert decomposer.is_composite(text)
    facts = decomposer.decompose(text, subject_name="Alice Smith")

    preds = {f.predicate: f.value for f in facts}
    assert "HAS_ROLE" in preds
    assert preds["HAS_ROLE"] == "Staff Engineer"
    assert "IN_DEPARTMENT" in preds
    assert preds["IN_DEPARTMENT"] == "Engineering"
    assert "HAS_OFFICE" in preds
    assert "450 Market St" in preds["HAS_OFFICE"]
    assert "HAS_SALARY" in preds
    assert "$145,000" in preds["HAS_SALARY"]
    assert "HAS_EMERGENCY_CONTACT" in preds
    assert "555" in preds["HAS_EMERGENCY_CONTACT"]
    assert "HAS_EMAIL" in preds
    assert preds["HAS_EMAIL"] == "engineer@tech.io"


def test_healthcare_patient_notes_composite():
    decomposer = CompositeCellDecomposer()
    text = (
        "Allergies: Penicillin, Peanuts; "
        "Emergency Phone: 09876543210; "
        "Room: Ward 4, Room 402B; "
        "Status: Stable"
    )
    assert decomposer.is_composite(text)
    facts = decomposer.decompose(text, subject_name="Patient 102")

    preds = {f.predicate: f.value for f in facts}
    assert "HAS_ALLERGIES" in preds
    assert "Penicillin" in preds["HAS_ALLERGIES"]
    assert "HAS_EMERGENCY_PHONE" in preds
    assert "09876543210" in preds["HAS_EMERGENCY_PHONE"]
    assert "HAS_STATUS" in preds
    assert preds["HAS_STATUS"] == "Stable"


def test_vendor_directory_composite():
    decomposer = CompositeCellDecomposer()
    text = (
        "Apex Supplies Ltd | VAT: GB123456789 | support@apex.co.uk | "
        "Mon-Fri 9am-5pm | London, 14 Baker St"
    )
    assert decomposer.is_composite(text)
    facts = decomposer.decompose(text, subject_name="Apex Supplies Ltd")

    preds = {f.predicate: f.value for f in facts}
    assert "HAS_VAT" in preds
    assert preds["HAS_VAT"] == "GB123456789"
    assert "HAS_EMAIL" in preds
    assert preds["HAS_EMAIL"] == "support@apex.co.uk"
    assert "HAS_HOURS" in preds
    assert "9am-5pm" in preds["HAS_HOURS"]
    assert "HAS_ADDRESS" in preds
    assert "Baker St" in preds["HAS_ADDRESS"]


def test_simple_atomic_cell_not_composite():
    decomposer = CompositeCellDecomposer()
    # Simple atomic cells should NOT be considered composite
    assert not decomposer.is_composite("Software Engineer")
    assert not decomposer.is_composite("5.0")
    assert not decomposer.is_composite("Engineering")
    assert not decomposer.is_composite("912-04-7731")
