"""Data models and schemas for RedactGov."""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class BoundingBox(BaseModel):
    """Spatial bounding box in PDF points (origin at bottom-left or top-left standard)."""
    page: int = Field(description="1-based page index")
    x0: float = Field(description="Left horizontal coordinate")
    y0: float = Field(description="Bottom / Top coordinate depending on convention")
    x1: float = Field(description="Right horizontal coordinate")
    y1: float = Field(description="Top / Bottom coordinate depending on convention")

    @property
    def width(self) -> float:
        return abs(self.x1 - self.x0)

    @property
    def height(self) -> float:
        return abs(self.y1 - self.y0)


class RedactionEntity(BaseModel):
    """An individual token or string target identified for redaction."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    text: str = Field(description="Verbatim text string to redact")
    category: str = Field(description="Categorical entity type (e.g. ssn, juvenile, informant)")
    statute_code: str = Field(description="Mapped Virginia statutory code")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    page_number: int = Field(default=1, description="1-based page index")
    bounding_boxes: List[BoundingBox] = Field(default_factory=list)
    tier: str = Field(default="tier1_deterministic", description="Engine tier (tier1_deterministic or tier2_gemma)")
    approved: bool = Field(default=True, description="Approval state for human-in-the-loop review")


class AuditRecord(BaseModel):
    """Auditable log entry for a performed redaction."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    page: int
    verbatim_text: str
    statute_code: str
    statute_title: str
    category: str
    confidence: float
    bbox: Optional[BoundingBox] = None


class RedactionPlan(BaseModel):
    """Complete redaction plan for a document before execution."""
    document_name: str
    total_pages: int
    entities: List[RedactionEntity] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RedactionResult(BaseModel):
    """Output summary of document sanitization."""
    success: bool
    input_path: str
    output_path: str
    certificate_path: Optional[str] = None
    redacted_count: int
    total_pages: int
    execution_time_seconds: float
    verification_passed: bool
