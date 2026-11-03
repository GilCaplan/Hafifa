class ValidationError(Exception):
    """Invalid input, e.g. not a CSV, missing columns or a malformed city name. Returns 400."""


class NotFoundError(Exception):
    """Valid input with no matching data, e.g. an unknown city or dates outside the data. Returns 404."""
