class FleetControllerError(Exception):
    """Base exception for Node Fleet Controller domain errors."""


class RequestNotFoundError(FleetControllerError):
    """Raised when a durable fleet request does not exist."""


class UnsupportedRequestTypeError(FleetControllerError):
    """Raised when workflow planning receives an unsupported request type."""


class NodeNotFoundError(FleetControllerError):
    """Raised when a durable node record does not exist."""


class NodePoolNotFoundError(FleetControllerError):
    """Raised when a durable node-pool record does not exist."""


class FailoverPolicyNotFoundError(FleetControllerError):
    """Raised when a required durable failover policy scope does not exist."""
