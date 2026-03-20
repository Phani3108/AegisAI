from __future__ import annotations

from aegisai.dlp.scan import scan_request_text


def test_scan_empty() -> None:
    assert not scan_request_text("").has_findings
    assert not scan_request_text("   ").has_findings


def test_scan_ssn() -> None:
    r = scan_request_text("reach me at 123-45-6789 please")
    assert r.has_findings
    assert "ssn_like" in r.kinds


def test_scan_credit_card_like() -> None:
    r = scan_request_text("card 4111-1111-1111-1111 ok")
    assert r.has_findings
    assert "credit_card_like" in r.kinds


def test_scan_clean() -> None:
    r = scan_request_text("summarize the quarterly report")
    assert not r.has_findings
