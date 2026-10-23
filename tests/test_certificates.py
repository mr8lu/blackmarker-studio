from pathlib import Path
import pdfplumber
from redact_gov.certificates.generator import CertificateGenerator, get_certificate_preset
from redact_gov.core.models import CertificateConfig, RedactionEntity


def test_certificate_generation(tmp_path: Path):
    generator = CertificateGenerator()
    entities = [
        RedactionEntity(
            text="123-45-6789",
            category="ssn",
            data_domain="PII",
            statute_code="VA-2.2-3705.1(10)",
            confidence=0.99,
            page_number=1,
            tier="tier1_deterministic",
        ),
        RedactionEntity(
            text="Brandon Miller",
            category="juvenile",
            data_domain="PII",
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


def test_customizable_hipaa_and_banking_certificate_templates(tmp_path: Path):
    generator = CertificateGenerator()
    entities = [
        RedactionEntity(
            text="MRN-84920144",
            category="mrn",
            data_domain="PHI",
            statute_code="45 CFR § 164.514(b)(2)(i)(B)",
            confidence=0.99,
            page_number=1,
            tier="tier1_deterministic",
        ),
        RedactionEntity(
            text="4532-0151-1283-0366",
            category="credit_card",
            data_domain="PPI",
            statute_code="PCI DSS v4.0 Req. 3.4",
            confidence=0.99,
            page_number=1,
            tier="tier1_deterministic",
        ),
    ]

    custom_cfg = CertificateConfig(
        template_id="hipaa_custom",
        jurisdiction_banner="ST. MARY CLINICAL HEALTH SYSTEM",
        framework_subtitle="HIPAA Privacy Rule Safe Harbor (45 CFR § 164.514) & PCI DSS v4.0",
        certificate_title="CLINICAL & BILLING DE-IDENTIFICATION CERTIFICATE",
        agency_name="St. Mary Health Privacy Office",
        reviewer_name="Dr. Evelyn Vance, Chief Privacy Officer",
        attestation_statement="Certified de-identified under 45 CFR § 164.514(b)(2) and PCI DSS v4.0 Req. 3.4.",
    )

    out_cert = tmp_path / "custom_hipaa_certificate.pdf"
    res = generator.generate_certificate(
        document_name="patient_billing_record.pdf",
        entities=entities,
        output_path=out_cert,
        certificate_config=custom_cfg,
    )

    assert res.is_file()
    with pdfplumber.open(res) as pdf:
        extracted = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "ST. MARY CLINICAL HEALTH SYSTEM" in extracted
    assert "CLINICAL & BILLING DE-IDENTIFICATION CERTIFICATE" in extracted
    assert "St. Mary Health Privacy Office" in extracted
    assert "Dr. Evelyn Vance" in extracted
    assert "PHI" in extracted
    assert "PPI" in extracted

    banking_preset = get_certificate_preset("banking_glba_pci")
    assert "PCI DSS" in banking_preset.framework_subtitle
