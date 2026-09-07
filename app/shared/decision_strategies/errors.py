class StrategyConfigurationError(ValueError):
    """A decision strategy or its evaluator is configured incorrectly."""


class StrategySelectionError(Exception):
    """No strategy, or multiple equally preferred strategies, apply."""


class StrategyExecutionError(Exception):
    """A criterion failed while a strategy was being evaluated."""
