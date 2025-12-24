class DrDrillError(RuntimeError):
    """Raised when the disaster recovery drill encounters a fatal error."""


class PolicyViolation(DrDrillError):
    """Raised when an RPO/RTO policy threshold is breached."""
