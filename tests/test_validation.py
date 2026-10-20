
import pytest

from inventory import validate_inventory


def test_negative_quantity_is_rejected():
    inventory = {
        "SKU-201": {"product_name": "Test Product", "quantity": -1}
    }

    with pytest.raises(ValueError, match="cannot be negative"):
        validate_inventory(inventory)


def test_string_quantity_is_rejected():
    inventory = {
        "SKU-201": {"product_name": "Test Product", "quantity": "five"}
    }

    with pytest.raises(ValueError, match="must be an integer"):
        validate_inventory(inventory)


def test_boolean_quantity_is_rejected():
    inventory = {
        "SKU-201": {"product_name": "Test Product", "quantity": True}
    }

    with pytest.raises(ValueError, match="must be an integer"):
        validate_inventory(inventory)
