import pytest

from app.services.pin_utils import normalize_india_pin, normalize_pin_list


def test_normalize_india_pin_valid():
    assert normalize_india_pin("110001") == "110001"
    assert normalize_india_pin("PIN 560001") == "560001"


def test_normalize_india_pin_invalid():
    with pytest.raises(ValueError):
        normalize_india_pin("12345")


def test_normalize_pin_list_dedupes():
    assert normalize_pin_list(["110001", "110 001", "560001"]) == ["110001", "560001"]
