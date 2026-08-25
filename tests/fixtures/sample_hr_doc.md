---
okf_version: "1.0"
document:
  id: "HR-2026-00142"
  title: "Q3 Compensation Review"
  classification: "CONFIDENTIAL"
  department: "Human Resources"
  author: "jane.doe@acme.corp"
  created: "2026-07-15"
privacy:
  entity_categories:
    - PERSON
    - SALARY
    - SSN
    - EMAIL
    - PHONE
  redaction_policy: "TOKENIZE"
  min_confidence: 0.85
access_control:
  allowed_roles:
    - hr_manager
    - cfo
    - compliance_officer
  denied_roles:
    - intern
    - contractor
graph:
  namespace: "hr.compensation"
  link_strategy: "cross_document"
  max_traversal_depth: 3
---

# Q3 Compensation Review

John Smith (SSN: 123-45-6789) is a Senior Engineer earning $185,000/year.
He manages a team budget of $2.3M and reports to Sarah Johnson (VP Engineering).
Contact: john.smith@acme.corp, +1-555-0142.
