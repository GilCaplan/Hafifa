"""The app's own errors. Code raises them with a message for the user; handlers.py logs them and picks the response."""


class ValidationError(Exception):
    """The input is invalid, e.g. not a CSV, missing columns or a malformed city name."""


class NotFoundError(Exception):
    """The input is valid, but there's no matching data, e.g. an unknown city or dates outside the data."""
