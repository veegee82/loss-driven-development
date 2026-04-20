from src.cart import Cart
from src.checkout import checkout


def test_checkout_no_discount():
    c = Cart()
    c.add_item(100.0)
    result = checkout(c)
    assert result["amount"] == 100.0


def test_checkout_applies_discount():
    c = Cart()
    c.add_item(100.0)
    c.apply_discount(10.0)  # 10 percent off
    result = checkout(c)
    assert result["amount"] == 90.0
