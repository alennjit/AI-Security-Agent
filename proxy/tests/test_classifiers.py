from ai_security_agent.dlp.classifiers import scan


def test_clean_text_is_not_flagged():
    result = scan("What's a good recipe for banana bread?")
    assert not result.flagged
    assert result.risk_score == 1


def test_aws_key_is_detected_and_redacted():
    text = "Here's my key: AKIAABCDEFGHIJKLMNOP use it to debug the S3 upload"
    result = scan(text)
    assert result.flagged
    assert "credential" in result.categories
    finding = next(f for f in result.findings if f.rule_name == "aws_access_key")
    assert "AKIAABCDEFGHIJKLMNOP" not in finding.masked_snippet
    assert finding.masked_snippet.startswith("AKIA")
    assert result.risk_score >= 8


def test_github_token_is_detected():
    text = "export GH_TOKEN=ghp_" + "a" * 36
    result = scan(text)
    assert any(f.rule_name == "github_token" for f in result.findings)


def test_private_key_block_is_detected():
    text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----"
    result = scan(text)
    assert any(f.rule_name == "private_key_block" for f in result.findings)
    assert result.risk_score == 10


def test_ssn_is_detected():
    result = scan("His SSN is 219-09-9999 if you need it for the form")
    assert any(f.rule_name == "ssn" for f in result.findings)


def test_credit_card_luhn_validation_rejects_random_digit_runs():
    # Valid test Luhn number
    valid = scan("Card number: 4111 1111 1111 1111")
    assert any(f.rule_name == "credit_card_candidate" for f in valid.findings)

    # Same length, fails Luhn checksum -> should NOT be flagged as a card
    invalid = scan("Order reference: 1234 5678 9012 3456")
    assert not any(
        f.rule_name == "credit_card_candidate" for f in invalid.findings
    )


def test_confidential_keyword_marker_detected():
    result = scan("This document is CONFIDENTIAL and for internal use only.")
    assert any(f.category == "confidential_marker" for f in result.findings)


def test_extra_keywords_are_layered_in():
    result = scan("Don't share anything about Project Nightowl externally.", extra_keywords=("project nightowl",))
    assert any(f.rule_name == "keyword_match" for f in result.findings)


def test_multiple_categories_raise_score_above_single_finding():
    single = scan("AKIAABCDEFGHIJKLMNOP")
    combined = scan("AKIAABCDEFGHIJKLMNOP and my SSN is 219-09-9999, this is confidential")
    assert combined.risk_score >= single.risk_score


def test_rationale_is_human_readable_and_present():
    result = scan("AKIAABCDEFGHIJKLMNOP")
    assert "Risk" in result.rationale
    assert "/10" in result.rationale
