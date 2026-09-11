from redact_gov.core.statutes import VIRGINIA_STATUTES, get_statute, get_statute_by_category, list_statutes


def test_statutes_catalog():
    statutes = list_statutes()
    assert len(statutes) >= 6

    juvenile = get_statute("VA-16.1-301")
    assert juvenile is not None
    assert juvenile.legal_citation == "Va. Code § 16.1-301"
    assert "juvenile" in juvenile.short_title.lower()

    pii = get_statute("VA-2.2-3705.1(10)")
    assert pii is not None
    assert "Privacy" in pii.category


def test_statute_by_category():
    assert get_statute_by_category("ssn").code == "VA-2.2-3705.1(10)"
    assert get_statute_by_category("driver_license").code == "VA-2.2-3705.1(10)"
    assert get_statute_by_category("juvenile").code == "VA-16.1-301"
    assert get_statute_by_category("victim_witness").code == "VA-19.2-11.2"
    assert get_statute_by_category("informant").code == "VA-2.2-3705.2(1)"
    assert get_statute_by_category("scholastic").code == "VA-2.2-3705.4(1)"
