def calculator(operation: str, a: float, b: float) -> float:
    """Perform basic arithmetic operations.

    Args:
        operation: The operation to perform (+, -, *, /)
        a: First operand
        b: Second operand

    Returns:
        Result of the arithmetic operation

    Raises:
        ValueError: If operation is not supported or division by zero
    """
    if operation == '+':
        return a + b
    elif operation == '-':
        return a - b
    elif operation == '*':
        return a * b
    elif operation == '/':
        if b == 0:
            raise ValueError("Division by zero is not allowed")
        return a / b
    else:
        raise ValueError(f"Unsupported operation: {operation}")