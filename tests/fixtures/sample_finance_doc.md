---
okf_version: "1.0"
document:
  id: "FIN-2026-00089"
  title: "Q3 Revenue Forecast"
  classification: "RESTRICTED"
  department: "Finance"
  author: "cfo@acme.corp"
  created: "2026-08-01"
privacy:
  entity_categories:
    - PERSON
    - SALARY
    - ORGANIZATION
  redaction_policy: "TOKENIZE"
  min_confidence: 0.80
access_control:
  allowed_roles:
    - cfo
    - board_member
  denied_roles:
    - intern
    - contractor
    - hr_manager
graph:
  namespace: "finance.revenue"
  link_strategy: "cross_document"
  max_traversal_depth: 2
---

# Q3 Revenue Forecast

Acme Corp projects $45M in Q3 revenue.
The deal with Globex Corporation is worth $12M and is managed by Michael Chen.
Operating expenses are forecasted at $28M under CFO Lisa Park.
