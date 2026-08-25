"""OKF schema registry — provides default entity categories and validation helpers."""

from __future__ import annotations

# Supported entity categories across the system
BUILTIN_ENTITY_CATEGORIES: list[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "DATE_OF_BIRTH",
    "IP_ADDRESS",
    "LOCATION",
    "ORGANIZATION",
    # Custom domain entities
    "SALARY",
    "PROJECT_CODE",
    "EMPLOYEE_ID",
]


def validate_entity_categories(categories: list[str]) -> list[str]:
    """Map user-friendly category names to Presidio-compatible entity types.

    Handles common aliases (e.g., 'SSN' → 'US_SSN', 'EMAIL' → 'EMAIL_ADDRESS').
    """
    alias_map = {
        "SSN": "US_SSN",
        "EMAIL": "EMAIL_ADDRESS",
        "PHONE": "PHONE_NUMBER",
    }
    return [alias_map.get(c, c) for c in categories]
