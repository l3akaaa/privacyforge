from privacyforge.detection.deterministic import (
    DeterministicDetector,
    luhn_valid,
    ssn_plausible,
)
from privacyforge.models import Category


def test_email_detected():
    det = DeterministicDetector()
    f = det.detect_text("contact me at jane.doe@example.edu please")
    assert any(x.entity_type == "EMAIL" for x in f)


def test_credit_card_luhn_filters_false_positives():
    # Valid Luhn (test Visa) vs invalid number.
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")
    det = DeterministicDetector()
    good = det.detect_text("card 4111 1111 1111 1111")
    bad = det.detect_text("code 1234 5678 9012 3456")
    assert any(x.entity_type == "CREDIT_CARD" for x in good)
    assert not any(x.entity_type == "CREDIT_CARD" for x in bad)


def test_ssn_validator():
    assert ssn_plausible("123-45-6789")
    assert not ssn_plausible("000-45-6789")
    det = DeterministicDetector()
    f = det.detect_text("ssn 123-45-6789")
    assert any(x.entity_type == "US_SSN" for x in f)


def test_preview_is_masked():
    det = DeterministicDetector()
    f = det.detect_text("email bob@test.com")
    emails = [x for x in f if x.entity_type == "EMAIL"]
    assert emails and "bob@test.com" not in emails[0].value_preview


def test_phone_flagged_for_review():
    det = DeterministicDetector()
    f = det.detect_text("call 415-555-0199")
    phones = [x for x in f if x.entity_type == "PHONE"]
    assert phones and phones[0].review_needed
    assert phones[0].category == Category.PII
