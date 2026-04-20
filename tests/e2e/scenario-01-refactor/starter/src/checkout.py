from src.cart import Cart


def checkout(cart: Cart) -> dict:
    amount = cart.total()
    return {"status": "charged", "amount": amount}
