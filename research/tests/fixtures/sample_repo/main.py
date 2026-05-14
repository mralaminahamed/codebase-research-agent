"""Sample module for testing code exploration tools."""


def greet(name: str) -> str:
    """Return a personalised greeting string.

    Args:
        name: The recipient's name.

    Returns:
        Greeting string.
    """
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two integers and return their sum.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        Sum of a and b.
    """
    return a + b


class Calculator:
    """Minimal arithmetic helper for demonstration purposes."""

    def multiply(self, a: int, b: int) -> int:
        """Return the product of two integers.

        Args:
            a: First factor.
            b: Second factor.

        Returns:
            Product of a and b.
        """
        return a * b
