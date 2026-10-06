class HarnessException(Exception):
    """Base exception for all harness domain errors."""

    pass


class ConfigurationError(HarnessException):
    pass


class SchemaValidationError(HarnessException):
    pass


class GuardrailViolationException(HarnessException):
    pass


class PromptInjectionDetected(GuardrailViolationException):
    pass


class PIIContentDetected(GuardrailViolationException):
    pass


class HITLInterruptException(HarnessException):
    def __init__(self, approval_id: str, message: str = "HITL approval required"):
        super().__init__(message)
        self.approval_id = approval_id


class BudgetLimitExceededException(HarnessException):
    pass


class MaxIterationsReachedException(HarnessException):
    pass


class AuditIntegrityException(HarnessException):
    def __init__(self, message: str, step_index: int):
        super().__init__(message)
        self.step_index = step_index


class ProviderException(HarnessException):
    pass


class ProviderUnavailableException(ProviderException):
    pass


class ProviderTimeoutException(ProviderException):
    pass


class ProviderRateLimitException(ProviderException):
    pass
