from pathlib import Path
from redact_gov.certificates.generator import CertificateGenerator
from redact_gov.core.models import RedactionEntity


def test_certificate_generation(tmp_path: Path):
    generator = CertificateGenerator()
    entities = [
        RedactionEntity(
            text="123-45-6789",
            category="ssn",
            statute_code="VA-2.2-3705.1(10)",
            confidence=0.99,
            page_number=1,
            tier="tier1_deterministic",
        ),
        RedactionEntity(
            text="Brandon Miller",
            category="juvenile",
            statute_code="VA-16.1-301",
            confidence=0.95,
            page_number=1,
            tier="tier2_gemma",
        ),
    ]

    out_cert = tmp_path / "test_certificate.pdf"
    res = generator.generate_certificate(
        document_name="sample_case.pdf",
        entities=entities,
        output_path=out_cert,
        reviewer_name="Officer Jane Doe",
    )

    assert res.is_file()
    assert res.stat().st_size > 1000
