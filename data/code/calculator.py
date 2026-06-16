class Calculator:
    """A simple calculator class for testing SOTA AST parsing."""

    def __init__(self, precision: int = 2):
        self.precision = precision

    def add(self, a: float, b: float) -> float:
        """Add two numbers and return the result."""
        return round(a + b, self.precision)

    def subtract(self, a: float, b: float) -> float:
        """Subtract b from a and return the result."""
        return round(a - b, self.precision)

def calculate_average(numbers: list[float]) -> float:
    """Calculate the average of a list of numbers."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
