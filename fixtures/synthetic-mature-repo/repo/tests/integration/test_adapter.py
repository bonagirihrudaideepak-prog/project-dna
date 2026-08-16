import pytest

from src.db.adapter import get_outfits


def test_get_outfits_returns_rows():
    outfits = get_outfits(wardrobe_id=1)
    assert isinstance(outfits, list)


def test_adapter_supports_joins():
    result = get_outfits(wardrobe_id=1, include_owner=True)
    assert "owner" in result