"""Typed errors raised at the service boundaries."""


class AgentServiceError(Exception):
    """Base class for expected agent-service failures."""


class NestUnavailableError(AgentServiceError):
    """Nest could not be reached or returned a server error."""


class WebSearchError(AgentServiceError):
    """Web search failed in live mode."""


class IngestError(AgentServiceError):
    """The knowledge corpus could not be indexed."""


class InsufficientFundsError(AgentServiceError):
    """The requested withdrawal exceeds the portfolio total value."""


class UnknownTickerError(AgentServiceError):
    """A hypothetical sale names a ticker the portfolio does not hold."""


class ChatServiceError(AgentServiceError):
    """The chat runner finished without producing an answer."""
