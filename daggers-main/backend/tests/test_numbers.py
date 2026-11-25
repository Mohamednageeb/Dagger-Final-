from __future__ import annotations

from backend.app.core import numbers, scorer


def test_pattern_catalog_has_200_deterministic_signatures():
    assert numbers.pattern_catalog_size() == 200


def test_reported_premium_number_is_malicious():
    result = numbers.check_number("+971 9000 00042")
    assert result.verdict == "MALICIOUS"
    assert result.score >= 0.85
    assert any("deterministic reported-number pattern" in reason for reason in result.reasons)
    assert result.offline_capable is True


def test_premium_prefix_without_report_is_suspicious():
    result = numbers.check_number("+9001234567")
    assert result.verdict == "SUSPICIOUS"
    assert any("premium-rate" in reason for reason in result.reasons)


def test_voip_callback_pattern_is_suspicious():
    result = numbers.check_number("+445612345678")
    assert result.verdict == "SUSPICIOUS"
    assert result.scam_type == "callback-voip-pattern"


def test_same_digit_repeat_is_suspicious():
    result = numbers.check_number("1111111111")
    assert result.verdict == "SUSPICIOUS"
    assert any("same-digit repeat" in reason for reason in result.reasons)


def test_clean_uae_landline_has_no_signs():
    result = numbers.check_number("+971 4 123 4567")
    assert result.verdict == "UNKNOWN"
    assert result.score == 0.0
    assert result.reasons == ["no signs found in the deterministic number patterns"]


def test_arabic_indic_digits_normalize_to_pattern_catalog():
    assert numbers.normalize_number("+٩٧١٩٠٠٠٠٠٠٤٢") == "971900000042"
    result = numbers.check_number("+٩٧١٩٠٠٠٠٠٠٤٢")
    assert result.verdict == "MALICIOUS"


def test_phone_numbers_are_not_a_checker_input(scoring_kwargs):
    """Phone-number checking is not part of the Checker/scan engine (Maps listings only)."""
    import pytest

    with pytest.raises(ValueError):
        scorer.score_request("number", "+971900000042", "en", **scoring_kwargs)


# ------------------------------------------------------------------ POST /api/number (public, nothing stored)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def number_client(tmp_path, monkeypatch):
    from backend.tests.test_integration import make_settings
    from backend.app.main import create_app

    monkeypatch.setenv("AI_PROVIDER", "template")
    app = create_app(make_settings(tmp_path))
    with TestClient(app) as client:
        yield client, app


def test_number_endpoint_flags_premium_and_never_says_safe(number_client):
    client, app = number_client
    bad = client.post("/api/number", json={"input": "+971 9000 00042"}).json()
    assert bad["tag"] == "FAKE" and bad["verdict"] == "MALICIOUS" and bad["warning_signs"] is True
    assert bad["number"] == "+971900000042" and bad["stored"] is False
    assert {s["code"] for s in bad["signs"]} == {"pattern_catalogue", "premium_rate"}
    warn = client.post("/api/number", json={"input": "+9001234567"}).json()
    assert warn["tag"] == "WARNING" and warn["warning_signs"] is True
    clean = client.post("/api/number", json={"input": "+971 4 123 4567"}).json()
    assert clean["tag"] == "WARNING" and clean["warning_signs"] is False      # not verified ≠ safe
    assert clean["signs"] == []
    arabic = client.post("/api/number", json={"input": "+٩٧١ ٩٠٠٠ ٠٠٠٤٢"}).json()
    assert arabic["digits"] == "971900000042"
    # nothing stored: no finding, no report
    assert app.state.runtime.repo.get_findings(50, "live", include_restricted=True) == []


def test_number_endpoint_rejects_non_numbers(number_client):
    client, _ = number_client
    for value in ("hello", "12345", "+1234567890123456789", "https://x.ae"):
        r = client.post("/api/number", json={"input": value})
        assert r.status_code == 422 and r.json()["detail"]["code"] == "invalid_number", value
