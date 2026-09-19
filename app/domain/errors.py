class ValidationConfigurationError(ValueError):
    """The configured validation process is invalid."""


class ValidationExecutionError(Exception):
    """A technical failure prevented validation."""


class ProductResolutionError(Exception):
    """A technical failure prevented product resolution."""
