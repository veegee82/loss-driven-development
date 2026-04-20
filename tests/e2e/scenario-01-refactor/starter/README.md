# mini-cart

A minimal cart / checkout example.

## Usage

```python
from src.cart import Cart
from src.checkout import checkout

cart = Cart()
cart.add_item(100.0)
cart.apply_discount(10.0)  # 10% off
result = checkout(cart)  # discounts are applied at checkout
print(result)  # {"status": "charged", "amount": 90.0}
```
