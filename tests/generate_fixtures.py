"""Helper script to generate PDF test fixtures."""

from pathlib import Path
import pymupdf

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

def generate_sample_employee_pdf():
    doc = pymupdf.open()
    page = doc.new_page()

    text = (
        "Engineering Department Payroll Summary\n\n"
        "Alice Williams (SSN: 987-65-4321) is a Principal Architect earning $210,000/year.\n"
        "She leads the Cloud Infrastructure group and reports to Robert Taylor (CTO).\n"
        "Contact information: alice.williams@acme.corp, +1-555-0199.\n"
    )

    page.insert_text((50, 72), text, fontsize=12)

    doc.set_metadata({
        "title": "Engineering Department Payroll Summary",
        "author": "hr-department@acme.corp",
        "subject": "Payroll and compensation review",
        "creationDate": "D:20260715120000",
    })

    target_path = FIXTURES_DIR / "sample_employee_record.pdf"
    doc.save(str(target_path))
    doc.close()
    print(f"Saved {target_path}")

def generate_sample_payroll_table_pdf():
    doc = pymupdf.open()
    page = doc.new_page()

    text = (
        "Q3 Engineering Payroll Table\n\n"
        "| Name | SSN | Salary | Department | Reason |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| Priya Nandakumar | 912-04-7731 | $142,500 | Engineering | Merit Raise |\n"
        "| David Okonkwo | 927-18-3364 | $118,000 | Engineering | Annual Raise |\n"
        "| Marcus Feldstein | 905-62-1187 | $196,000 | Engineering | Promotion |\n"
    )

    page.insert_text((50, 72), text, fontsize=11)

    doc.set_metadata({
        "title": "Q3 Engineering Payroll Table",
        "author": "hr-department@acme.corp",
        "subject": "Compensation Review Table",
        "creationDate": "D:20260715120000",
    })

    target_path = FIXTURES_DIR / "sample_payroll_table.pdf"
    doc.save(str(target_path))
    doc.close()
    print(f"Saved {target_path}")

if __name__ == "__main__":
    generate_sample_employee_pdf()
    generate_sample_payroll_table_pdf()
