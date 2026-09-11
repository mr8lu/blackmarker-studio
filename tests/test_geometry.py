from pathlib import Path
from redact_gov.config import settings
from redact_gov.core.geometry import find_text_bounding_boxes, get_document_page_count


def test_bounding_box_extraction():
    test_pdf = settings.SYNTHETIC_DIR / "police_incident_narrative.pdf"
    assert test_pdf.is_file(), "Synthetic PDF must exist."

    pages = get_document_page_count(test_pdf)
    assert pages >= 2

    # Find bounding box for known text
    boxes = find_text_bounding_boxes(test_pdf, page_number=1, target_text="Marcus Vance")
    assert len(boxes) >= 1
    bbox = boxes[0]
    assert bbox.page == 1
    assert bbox.width > 0
    assert bbox.height > 0
    assert bbox.x0 > 0
    assert bbox.y0 > 0
