from redact_gov.engines.deterministic import DeterministicRedactionEngine, luhn_checksum_valid


def test_deterministic_patterns():
    engine = DeterministicRedactionEngine()
    sample = (
        "Subject details: SSN 123-45-6789, Virginia Driver's License T98765432. "
        "Contact phone (804) 555-1234, DOB: 05/12/1984. "
        "Email address test.user@richmondgov.org."
    )

    entities = engine.scan_text(sample, page_number=1)
    categories = {e.category: e.text for e in entities}

    assert "ssn" in categories
    assert categories["ssn"] == "123-45-6789"

    assert "driver_license" in categories
    assert categories["driver_license"] == "T98765432"

    assert "phone" in categories
    assert "(804) 555-1234" in categories["phone"]

    assert "dob" in categories
    assert categories["dob"] == "05/12/1984"

    assert "email" in categories
    assert categories["email"] == "test.user@richmondgov.org"


def test_luhn_checksum():
    # Valid test visa card
    assert luhn_checksum_valid("4532015112830366") is True
    # Invalid card
    assert luhn_checksum_valid("4532015112830367") is False
