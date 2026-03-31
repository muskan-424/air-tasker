import pytest
from pydantic import ValidationError

from app.schemas.kyc import KycSubmitRequest, pan_to_last4


def test_pan_to_last4_ok():
    assert pan_to_last4("ABCDE1234F") == "1234"


def test_pan_to_last4_invalid():
    with pytest.raises(ValueError, match="invalid_pan_format"):
        pan_to_last4("INVALID")


def test_kyc_submit_request_valid_pan():
    body = KycSubmitRequest(full_name="Test User", pan="ABCDE1234F", aadhaar_last4="1234")
    assert body.pan == "ABCDE1234F"


def test_kyc_submit_request_rejects_bad_pan():
    with pytest.raises(ValidationError):
        KycSubmitRequest(full_name="Test User", pan="XXXXXXXXXX", aadhaar_last4=None)
