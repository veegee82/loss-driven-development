class Cart:
    def __init__(self):
        self.items = []
        self.discount = 0.0

    def add_item(self, price: float) -> None:
        self.items.append(price)

    def apply_discount(self, percent: float) -> None:
        """Record a discount percentage (0-100) to apply at total()."""
        self.discount = percent

    def total(self) -> float:
        subtotal = sum(self.items)
        return subtotal
