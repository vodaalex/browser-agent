class AgentError(Exception):
    """Base error for the browser agent."""


class BrowserError(AgentError):
    """Error originating from browser / Playwright operations."""


class LLMError(AgentError):
    """Error originating from the LLM API."""


class ToolError(AgentError):
    """Error originating from tool execution."""

