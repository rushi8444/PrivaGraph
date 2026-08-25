"""OKF Document and header models."""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Classification(str, Enum):
    """Document security classification levels."""

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


class RedactionPolicy(str, Enum):
    """How detected entities should be handled."""

    TOKENIZE = "TOKENIZE"
    REDACT = "REDACT"
    PASSTHROUGH = "PASSTHROUGH"


class LinkStrategy(str, Enum):
    """Graph linking strategy between documents."""

    ISOLATED = "ISOLATED"
    CROSS_DOCUMENT = "cross_document"


class DocumentMeta(BaseModel):
    """Core document metadata from OKF header."""

    id: str
    title: str
    classification: Classification
    department: str
    author: str
    created: date


class PrivacyConfig(BaseModel):
    """Privacy scanning configuration from OKF header."""

    entity_categories: list[str]
    redaction_policy: RedactionPolicy = RedactionPolicy.TOKENIZE
    min_confidence: float = Field(default=0.85, ge=0.0, le=1.0)


class AccessControl(BaseModel):
    """RBAC access control from OKF header."""

    allowed_roles: list[str] = []
    denied_roles: list[str] = []


class GraphConfig(BaseModel):
    """Knowledge graph configuration from OKF header."""

    namespace: str
    link_strategy: LinkStrategy = LinkStrategy.CROSS_DOCUMENT
    max_traversal_depth: int = Field(default=3, ge=1, le=10)


class OKFHeader(BaseModel):
    """Complete OKF YAML frontmatter header."""

    okf_version: str = "1.0"
    document: DocumentMeta
    privacy: PrivacyConfig
    access_control: AccessControl = AccessControl()
    graph: GraphConfig


class OKFDocument(BaseModel):
    """Parsed OKF document with header and body text."""

    source_path: str
    header: OKFHeader
    body: str
    sentences: list[str]
